"""
Extended models for session-based activity management.
These models complement the existing Activity/Attempt system with:
1. Temporary sessions with TTL for ongoing activities
2. Permanent completion records for analytics
3. Continue/restart functionality
"""

import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Timestamped, Activity, ActivityVersion, Attempt

User = get_user_model()


class ActivitySession(Timestamped):
    """
    Temporary session for ongoing activity participation.
    Auto-expires after TTL to encourage completion and manage storage.

    Key Features:
    - 24-hour default TTL (configurable)
    - One active session per user per activity
    - Temporary response storage
    - Progress tracking with page navigation
    - Auto-cleanup of expired sessions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_sessions")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="active_sessions")
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT)

    # Navigation state
    current_page = models.PositiveIntegerField(default=0)
    total_pages = models.PositiveIntegerField(null=True, blank=True)  # Cached for performance

    # Session management
    expires_at = models.DateTimeField()  # TTL (default 24 hours from creation)
    is_active = models.BooleanField(default=True)

    # Progress tracking (optimized for fast access)
    responses_data = models.JSONField(default=dict)  # {question_id: value} for temp storage
    pages_visited = models.JSONField(default=list)   # [0, 1, 2] - pages user has seen
    pages_completed = models.JSONField(default=list) # [0, 1] - pages with all required responses

    # Session metadata
    started_from = models.CharField(max_length=50, default='map')  # map, direct_link, shared_link
    user_agent = models.TextField(blank=True)  # For analytics/debugging
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)  # device_info, referrer, etc.

    class Meta:
        unique_together = [("user", "activity")]  # One active session per user per activity
        indexes = [
            models.Index(fields=['expires_at', 'is_active']),  # Cleanup queries
            models.Index(fields=['user', 'is_active']),        # User session lookup
            models.Index(fields=['activity', 'is_active']),    # Activity analytics
        ]

    def save(self, *args, **kwargs):
        # Set default expiration if not provided
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if session has expired."""
        return timezone.now() > self.expires_at

    @property
    def time_remaining(self):
        """Get remaining time as timedelta."""
        if self.is_expired:
            return timedelta(0)
        return self.expires_at - timezone.now()

    @property
    def completion_percentage(self):
        """Calculate completion percentage based on pages."""
        if not self.total_pages:
            return 0.0
        return (len(self.pages_completed) / self.total_pages) * 100

    def extend_session(self, hours=24):
        """Extend session expiration time."""
        self.expires_at = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=['expires_at'])

    def mark_page_visited(self, page_index):
        """Mark a page as visited."""
        if page_index not in self.pages_visited:
            self.pages_visited.append(page_index)
            self.save(update_fields=['pages_visited'])

    def mark_page_completed(self, page_index):
        """Mark a page as completed (all required responses given)."""
        if page_index not in self.pages_completed:
            self.pages_completed.append(page_index)
            self.save(update_fields=['pages_completed'])

    def update_response(self, question_id, value):
        """Update a response in temporary storage."""
        self.responses_data[question_id] = value
        self.save(update_fields=['responses_data'])

    def get_response(self, question_id):
        """Get a response from temporary storage."""
        return self.responses_data.get(question_id)

    def __str__(self):
        status = "expired" if self.is_expired else "active"
        return f"Session: {self.user.username} - {self.activity.title} ({status})"


class ActivityCompletion(Timestamped):
    """
    Permanent record of activity completion.
    Created when session is successfully completed, persists forever for analytics.

    Key Features:
    - One completion per user per activity (can be updated if user retakes)
    - Performance metrics and analytics data
    - Links to final attempt for detailed response data
    - Permanent historical record
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_completions")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="completions")
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT)

    # Completion timestamps
    completed_at = models.DateTimeField()
    first_started_at = models.DateTimeField()  # When user first began this activity

    # Performance metrics
    total_time_seconds = models.PositiveIntegerField()  # Total time from start to completion
    active_time_seconds = models.PositiveIntegerField(null=True)  # Time actively engaged
    pages_visited = models.PositiveIntegerField()
    total_responses = models.PositiveIntegerField()
    valid_responses = models.PositiveIntegerField()

    # Quality metrics
    completion_rate = models.FloatField()  # Percentage of required responses completed
    accuracy_rate = models.FloatField(null=True)  # Percentage of valid responses
    average_response_time = models.FloatField(null=True)  # Average time per response (seconds)

    # Session history
    sessions_count = models.PositiveIntegerField(default=1)  # Number of sessions to complete
    attempts_count = models.PositiveIntegerField(default=1)  # Number of attempts made

    # Final data references
    final_attempt = models.OneToOneField(
        Attempt,
        on_delete=models.PROTECT,
        related_name="completion_record",
        help_text="The attempt that resulted in completion"
    )
    final_session = models.ForeignKey(
        ActivitySession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completion_record",
        help_text="The session that resulted in completion (may be cleaned up)"
    )

    # Analytics and insights
    insights = models.JSONField(default=dict, blank=True)  # AI-generated insights
    meta = models.JSONField(default=dict, blank=True)  # device_info, score_breakdown, etc.

    class Meta:
        unique_together = [("user", "activity")]  # One completion per user per activity
        indexes = [
            models.Index(fields=['user', 'completed_at']),      # User completion history
            models.Index(fields=['activity', 'completed_at']), # Activity completion analytics
            models.Index(fields=['completed_at']),              # Global completion analytics
            models.Index(fields=['completion_rate']),           # Quality analytics
        ]

    @property
    def completion_time_hours(self):
        """Get completion time in hours."""
        return self.total_time_seconds / 3600

    @property
    def average_response_time_minutes(self):
        """Get average response time in minutes."""
        if self.average_response_time:
            return self.average_response_time / 60
        return None

    def __str__(self):
        return f"Completion: {self.user.username} - {self.activity.title} ({self.completion_rate:.1f}%)"


class SessionManager(models.Manager):
    """Custom manager for ActivitySession with common queries."""

    def active_sessions(self):
        """Get all active, non-expired sessions."""
        return self.filter(
            is_active=True,
            expires_at__gt=timezone.now()
        )

    def expired_sessions(self):
        """Get all expired sessions."""
        return self.filter(
            models.Q(is_active=False) | models.Q(expires_at__lte=timezone.now())
        )

    def cleanup_expired(self):
        """Mark expired sessions as inactive and return count."""
        expired_count = self.expired_sessions().update(is_active=False)
        return expired_count

    def get_or_create_session(self, user, activity, **kwargs):
        """Get existing active session or create new one."""
        # Check for existing active session
        existing = self.active_sessions().filter(user=user, activity=activity).first()
        if existing:
            return existing, False

        # Create new session
        activity_version = activity.versions.filter(is_published=True).order_by('-version').first()
        if not activity_version:
            raise ValueError(f"No published version found for activity {activity.slug}")

        session = self.create(
            user=user,
            activity=activity,
            activity_version=activity_version,
            **kwargs
        )
        return session, True


# Add custom manager to ActivitySession
ActivitySession.add_to_class('objects', SessionManager())


# Enhanced Attempt model (extends existing)
class SessionAttempt(Attempt):
    """
    Proxy model for Attempt with session-specific methods.
    Provides session-aware functionality without changing the base model.
    """
    class Meta:
        proxy = True

    @classmethod
    def create_from_session(cls, session):
        """Create an attempt linked to a session."""
        return cls.objects.create(
            user=session.user,
            activity_version=session.activity_version,
            meta={
                'session_id': str(session.id),
                'started_from': session.started_from,
                'session_source': 'session'
            }
        )

    def link_to_session(self, session):
        """Link this attempt to a session."""
        self.meta = self.meta or {}
        self.meta['session_id'] = str(session.id)
        self.meta['session_source'] = 'session'
        self.save(update_fields=['meta'])