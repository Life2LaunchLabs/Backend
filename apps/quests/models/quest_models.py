"""
Quest template and enrollment models.
Updated to work with unified quest item system.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class QuestTemplate(models.Model):
    """
    Template for quests that can be created by admins and enrolled in by users.
    No distinction between user-created and admin-created at the model level.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Basic info
    title = models.CharField(max_length=255)
    description = models.TextField()
    color = models.CharField(max_length=7, default='#4CAF50', help_text="Hex color code (e.g., #4CAF50)")
    category = models.CharField(max_length=50, default='Other')

    # Organization & creator
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='quest_templates',
        help_text="Organization this quest belongs to"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_quests',
        help_text="User who created this quest"
    )

    # Sharing & visibility
    is_public = models.BooleanField(
        default=False,
        help_text="Visible in quest repository for all users to enroll"
    )
    is_template = models.BooleanField(
        default=True,
        help_text="Can be enrolled in by users (vs. one-time quest)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Metadata
    estimated_total_days = models.PositiveIntegerField(
        default=0,
        help_text="Total estimated duration (calculated from items)"
    )
    meta = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['is_public', 'status']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"

    def update_estimated_total_days(self):
        """Recalculate estimated total days from all items."""
        total = sum(
            item.effective_duration_days
            for item in self.template_items.all()
        )
        if self.estimated_total_days != total:
            self.estimated_total_days = total
            self.save(update_fields=['estimated_total_days'])

    @property
    def items_count(self):
        """Get total number of items in this quest."""
        return self.template_items.count()

    @property
    def milestones_count(self):
        """Get number of milestone items."""
        return self.template_items.filter(
            item_definition__item_type='milestone'
        ).count()

    @property
    def activities_count(self):
        """Get number of activity items."""
        return self.template_items.filter(
            item_definition__item_type='activity'
        ).count()


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
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='quest_enrollments'
    )
    quest_template = models.ForeignKey(
        QuestTemplate,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )

    # Enrollment status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
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
        """Calculate completion percentage based on completed items."""
        total_items = self.item_progress.count()
        if total_items == 0:
            return 0
        completed_items = self.item_progress.filter(status='completed').count()
        return int((completed_items / total_items) * 100)

    @property
    def completed_items_count(self):
        """Count of completed items."""
        return self.item_progress.filter(status='completed').count()

    @property
    def items_count(self):
        """Total item count."""
        return self.item_progress.count()

    def check_completion(self):
        """Check if all items are completed and update status accordingly."""
        if self.status == 'completed':
            return True

        # Check if all items are completed
        incomplete_items = self.item_progress.exclude(status='completed').exists()

        if not incomplete_items:
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at'])
            return True

        return False