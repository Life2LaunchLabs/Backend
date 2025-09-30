"""
Quest item progress tracking models.
Tracks user progress on individual quest items within an enrollment.
"""
import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone


class QuestItemProgress(models.Model):
    """
    Tracks user progress on individual quest items within an enrollment.
    Created automatically when user enrolls in a quest.
    """
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        'QuestEnrollment',
        on_delete=models.CASCADE,
        related_name='item_progress'
    )
    template_item = models.ForeignKey(
        'QuestTemplateItem',
        on_delete=models.CASCADE,
        related_name='user_progress'
    )

    # Progress status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started'
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Target completion date (calculated from enrollment + duration)
    target_date = models.DateField(
        help_text="Target completion date based on enrollment date + estimated duration"
    )

    # For activities: link to activity submission
    activity_submission = models.ForeignKey(
        'ActivitySubmission',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='quest_progress',
        help_text="Link to completed activity submission"
    )

    # User notes
    notes = models.TextField(blank=True, help_text="User's personal notes for this item")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['enrollment', 'template_item']
        ordering = ['enrollment', 'template_item__order']
        indexes = [
            models.Index(fields=['enrollment', 'status']),
            models.Index(fields=['template_item', 'status']),
            models.Index(fields=['target_date']),
            models.Index(fields=['status', 'target_date']),
        ]

    def __str__(self):
        return f"{self.enrollment.user.username} - {self.template_item.item_definition.title} ({self.status})"

    @property
    def is_overdue(self):
        """Check if item is overdue based on target date."""
        if self.status == 'completed':
            return False
        return timezone.now().date() > self.target_date

    @property
    def days_until_due(self):
        """Calculate days until target date (negative if overdue)."""
        if self.status == 'completed':
            return None
        delta = self.target_date - timezone.now().date()
        return delta.days

    @property
    def can_be_started(self):
        """Check if this item can be started based on prerequisites."""
        return self.template_item.can_be_started(enrollment=self.enrollment)

    def mark_started(self):
        """Mark item as started."""
        if self.status == 'not_started':
            self.status = 'in_progress'
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at', 'updated_at'])

    def mark_completed(self, activity_submission=None):
        """
        Mark item as completed.

        Args:
            activity_submission: Optional ActivitySubmission if this is an activity item
        """
        if self.status != 'completed':
            self.status = 'completed'
            self.completed_at = timezone.now()
            if activity_submission:
                self.activity_submission = activity_submission
            self.save(update_fields=['status', 'completed_at', 'activity_submission', 'updated_at'])

            # Check if quest is now complete
            self.enrollment.check_completion()

    @staticmethod
    def create_for_enrollment(enrollment):
        """
        Create QuestItemProgress records for all items in a quest enrollment.

        Args:
            enrollment: QuestEnrollment instance

        Returns:
            List of created QuestItemProgress instances
        """
        template_items = enrollment.quest_template.template_items.all().order_by('order')

        progress_records = []
        for template_item in template_items:
            # Calculate target date based on enrollment date + duration
            target_date = enrollment.enrolled_at.date() + timedelta(
                days=template_item.effective_duration_days
            )

            progress = QuestItemProgress.objects.create(
                enrollment=enrollment,
                template_item=template_item,
                target_date=target_date,
                status='not_started'
            )
            progress_records.append(progress)

        return progress_records