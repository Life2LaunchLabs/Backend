import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class Quest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quests')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_quests')
    template_id = models.UUIDField(null=True, blank=True, help_text="Original template ID for tracking updates")
    editable = models.BooleanField(default=True, help_text="Can only be set by original creator")
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    color = models.CharField(max_length=7, help_text="Hex color code (e.g., #FF6B6B)")
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['created_by']),
            models.Index(fields=['template_id']),
        ]
    
    def __str__(self):
        return f"{self.title} (owned by {self.user.username})"
    
    @property
    def is_personal(self):
        """Returns True if this quest was created by the owner (Personal category)"""
        return self.user_id == self.created_by_id
    
    @property
    def category(self):
        """Returns 'Personal' if created by user, 'Other' if shared"""
        return 'Personal' if self.is_personal else 'Other'


class Milestone(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('complete', 'Complete'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='milestones')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    finish_date = models.DateField(help_text="Target completion date")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    order = models.PositiveIntegerField(help_text="Display order within quest")
    
    prerequisites = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='dependents')
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['quest', 'order']
        unique_together = ['quest', 'order']
        indexes = [
            models.Index(fields=['quest', 'order']),
            models.Index(fields=['status']),
            models.Index(fields=['finish_date']),
        ]
    
    def __str__(self):
        return f"{self.quest.title}: {self.title}"
    
    def can_be_started(self):
        """Check if all prerequisites are complete"""
        return not self.prerequisites.exclude(status='complete').exists()
    
    def get_blocked_dependents(self):
        """Get milestones that depend on this one and are blocked"""
        if self.status == 'complete':
            return Milestone.objects.none()
        return self.dependents.filter(status='not_started')


# ============================================================================
# NEW ENROLLMENT-BASED SCHEMA (V2)
# ============================================================================

class QuestTemplate(models.Model):
    """
    Quest templates that can be shared and enrolled in by multiple users.
    This replaces the old Quest model's dual role.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    color = models.CharField(max_length=7, help_text="Hex color code (e.g., #FF6B6B)")
    category = models.CharField(max_length=50, default='Other')

    # Template metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_quest_templates')
    is_shared = models.BooleanField(default=False, help_text="Can be enrolled in by other users")
    is_active = models.BooleanField(default=True, help_text="Available for new enrollments")

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['is_shared', 'is_active']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.title} (template by {self.created_by.username})"


class MilestoneTemplate(models.Model):
    """
    Milestone templates that belong to quest templates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quest_template = models.ForeignKey(QuestTemplate, on_delete=models.CASCADE, related_name='milestone_templates')

    title = models.CharField(max_length=255)
    description = models.TextField()
    order = models.PositiveIntegerField(help_text="Display order within quest")
    estimated_finish_days = models.PositiveIntegerField(help_text="Days from enrollment to complete")

    # Template relationships
    prerequisites = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='dependents')

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['quest_template', 'order']
        unique_together = ['quest_template', 'order']
        indexes = [
            models.Index(fields=['quest_template', 'order']),
        ]

    def __str__(self):
        return f"{self.quest_template.title}: {self.title} (template)"


class QuestEnrollment(models.Model):
    """
    User enrollment in a quest template. This tracks user-specific progress.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quest_enrollments')
    quest_template = models.ForeignKey(QuestTemplate, on_delete=models.CASCADE, related_name='enrollments')

    # Enrollment status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    enrolled_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'quest_template']  # User can only enroll once per quest template
        ordering = ['enrolled_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['quest_template', 'status']),
            models.Index(fields=['enrolled_at']),
        ]

    def __str__(self):
        return f"{self.user.username} enrolled in {self.quest_template.title}"

    @property
    def progress_percentage(self):
        """Calculate completion percentage based on completed milestones"""
        total_milestones = self.milestone_progress.count()
        if total_milestones == 0:
            return 0
        completed_milestones = self.milestone_progress.filter(status='completed').count()
        return int((completed_milestones / total_milestones) * 100)

    @property
    def completed_milestones_count(self):
        """Count of completed milestones"""
        return self.milestone_progress.filter(status='completed').count()

    @property
    def milestones_count(self):
        """Total milestone count"""
        return self.milestone_progress.count()


class MilestoneProgress(models.Model):
    """
    User progress on individual milestones within their quest enrollment.
    """
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(QuestEnrollment, on_delete=models.CASCADE, related_name='milestone_progress')
    milestone_template = models.ForeignKey(MilestoneTemplate, on_delete=models.CASCADE, related_name='user_progress')

    # Progress tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    finish_date = models.DateField(help_text="Target completion date (calculated from enrollment + estimated days)")

    # User notes/customization
    notes = models.TextField(blank=True, help_text="User's personal notes for this milestone")

    class Meta:
        unique_together = ['enrollment', 'milestone_template']
        ordering = ['enrollment', 'milestone_template__order']
        indexes = [
            models.Index(fields=['enrollment', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['finish_date']),
        ]

    def __str__(self):
        return f"{self.enrollment.user.username}: {self.milestone_template.title}"

    def can_be_started(self):
        """Check if all prerequisite milestones are completed"""
        prerequisite_templates = self.milestone_template.prerequisites.all()
        if not prerequisite_templates.exists():
            return True

        # Check if all prerequisite milestones are completed in this enrollment
        prerequisite_progress = MilestoneProgress.objects.filter(
            enrollment=self.enrollment,
            milestone_template__in=prerequisite_templates
        )

        return not prerequisite_progress.exclude(status='completed').exists()