import uuid
import hashlib
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.courses.models import Course

User = get_user_model()


def generate_agenda_hash(agenda_content):
    """Generate a hash for agenda content to track versions"""
    if not agenda_content:
        return ""
    return hashlib.sha256(agenda_content.encode('utf-8')).hexdigest()


class CourseSession(models.Model):
    """
    Represents a user's attempt at completing a course assessment.
    Each session tracks progress through the course questions and stores responses.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
        ('paused', 'Paused')
    ]
    
    # Primary identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_sessions')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions')
    
    # Session metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Timing & progress
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    
    # Versioning for schema evolution
    agenda_version_hash = models.CharField(max_length=64, help_text="Hash of agenda content when session started")
    agenda_snapshot = models.JSONField(help_text="Full agenda at time of session start")
    
    # Analytics & scoring
    completion_percentage = models.FloatField(default=0.0)
    total_questions = models.IntegerField()
    answered_questions = models.IntegerField(default=0)
    
    # Metadata
    character_used = models.CharField(max_length=50, default='minu')
    session_notes = models.TextField(blank=True, help_text="AI-generated summary")
    
    # Schema evolution tracking
    schema_outdated = models.BooleanField(default=False, help_text="True if agenda has changed since session start")
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'course', 'status']),
            models.Index(fields=['status', 'last_activity_at']),
            models.Index(fields=['user', 'status']),
        ]
        
    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Auto-generate agenda hash and snapshot on creation
        if not self.agenda_version_hash and self.course_id:
            self.agenda_version_hash = generate_agenda_hash(self.course.agenda)
            self.agenda_snapshot = self._parse_agenda_to_json()
            self.total_questions = len(self.agenda_snapshot.get('items', []))
        super().save(*args, **kwargs)
    
    def _parse_agenda_to_json(self):
        """Parse the course agenda markdown into structured JSON"""
        try:
            from .utils import parse_agenda_items
            return parse_agenda_items(self.course.agenda)
        except Exception:
            # Fallback if parsing fails
            return {"about": "", "items": []}
    
    def update_progress(self):
        """Recalculate completion percentage based on completed responses"""
        if self.total_questions == 0:
            self.completion_percentage = 0.0
        else:
            completed_responses = self.responses.filter(status='complete').count()
            self.completion_percentage = (completed_responses / self.total_questions) * 100
            self.answered_questions = completed_responses
        
        # Mark as completed if all questions answered
        if self.completion_percentage >= 100 and self.status == 'active':
            self.status = 'completed'
            self.completed_at = timezone.now()
            # Update UserCourseProgress when session is completed
            self._update_user_course_progress()
        
        self.save()
    
    def _update_user_course_progress(self):
        """Update UserCourseProgress and unlock child courses when session is completed"""
        from apps.courses.models import UserCourseProgress
        
        # Mark this course as complete for the user
        progress, created = UserCourseProgress.objects.get_or_create(
            user=self.user,
            course=self.course,
            defaults={'status': 'complete', 'completed_at': timezone.now()}
        )
        
        if not created and progress.status != 'complete':
            progress.status = 'complete'
            progress.completed_at = timezone.now()
            progress.save()
        
        # Unlock child courses
        for child_course in self.course.children.all():
            child_progress, child_created = UserCourseProgress.objects.get_or_create(
                user=self.user,
                course=child_course,
                defaults={'status': 'open'}
            )
            
            # Only update locked courses to open
            if not child_created and child_progress.status == 'locked':
                child_progress.status = 'open'
                child_progress.save()
    
    def check_schema_consistency(self):
        """Check if course agenda has changed since session start"""
        current_hash = generate_agenda_hash(self.course.agenda)
        if current_hash != self.agenda_version_hash:
            self.schema_outdated = True
            self.save()
            return False
        return True


class QuestionResponse(models.Model):
    """
    Stores individual question responses within a course session.
    """
    STATUS_CHOICES = [
        ('partial', 'Partial'),      # User started answering
        ('complete', 'Complete'),    # AI marked as complete
        ('skipped', 'Skipped'),
        ('invalid', 'Invalid')
    ]
    
    # Primary identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(CourseSession, on_delete=models.CASCADE, related_name='responses')
    
    # Question identification (flexible for schema changes)
    question_number = models.IntegerField(help_text="1, 2, 3, etc.")
    question_id = models.CharField(max_length=100, help_text="career_aspirations, goal_priorities, etc.")
    question_text = models.TextField(help_text="Store actual question asked")
    
    # Response data
    raw_response = models.TextField(help_text="User's raw input")
    processed_response = models.TextField(help_text="AI-processed/formatted response")
    response_metadata = models.JSONField(default=dict, help_text="Additional structured data")
    
    # Status & timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='partial')
    first_response_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Quality & analysis
    response_quality_score = models.FloatField(null=True, blank=True)
    ai_analysis = models.TextField(blank=True, help_text="AI insights about the response")
    follow_up_needed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['session', 'question_number']
        ordering = ['question_number']
        indexes = [
            models.Index(fields=['session', 'status']),
            models.Index(fields=['question_id', 'status']),
            models.Index(fields=['session', 'question_number']),
        ]
    
    def __str__(self):
        return f"Q{self.question_number}: {self.question_id} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Set completed_at when status changes to complete
        if self.status == 'complete' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)
        
        # Update session progress after saving
        self.session.update_progress()


class ConversationTurn(models.Model):
    """
    Stores the chat conversation history for a course session.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant')
    ]
    
    # Links to session
    session = models.ForeignKey(CourseSession, on_delete=models.CASCADE, related_name='conversation')
    
    # Message data
    turn_number = models.IntegerField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    
    # AI response metadata (for assistant messages)
    emote = models.CharField(max_length=50, blank=True)
    quick_inputs = models.JSONField(default=list)
    system_data = models.JSONField(default=dict, help_text="active_item, completed_item, etc.")
    
    # Context
    question_context = models.ForeignKey(
        QuestionResponse, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        help_text="Question this turn relates to"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['turn_number']
        unique_together = ['session', 'turn_number']
        indexes = [
            models.Index(fields=['session', 'turn_number']),
            models.Index(fields=['session', 'role']),
        ]
    
    def __str__(self):
        return f"Turn {self.turn_number}: {self.role} - {self.content[:50]}..."