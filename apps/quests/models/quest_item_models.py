"""
Quest item models - unified system for milestones and activities.
Uses join table pattern for ordering integrity.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class QuestItemDefinition(models.Model):
    """
    Base definition for any type of item that can be added to quests.
    This is the 'library' of available items.
    Future-proof for multiple item types.
    """
    ITEM_TYPE_CHOICES = [
        ('milestone', 'Milestone'),
        ('activity', 'Activity'),
        # Future: ('assignment', 'Assignment'),
        # Future: ('assessment', 'Assessment'),
        # Future: ('resource', 'Resource'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)

    # Common metadata for all item types
    title = models.CharField(max_length=255)
    description = models.TextField()
    estimated_duration_days = models.PositiveIntegerField(
        help_text="Estimated time to complete in days"
    )

    # Polymorphic references - only one should be set based on item_type
    milestone_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Milestone-specific data (e.g., checklist, notes)"
    )
    activity = models.ForeignKey(
        'Activity',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='item_definitions',
        help_text="Reference to Activity if item_type is 'activity'"
    )
    # Future: assignment = models.ForeignKey('Assignment', null=True, blank=True, on_delete=models.SET_NULL)

    # Organization scope (null = available to all, but we'll enforce org-scoped for now)
    organization = models.ForeignKey(
        'organizations.Organization',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='quest_item_definitions',
        help_text="Organization this item belongs to"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['item_type']),
            models.Index(fields=['organization']),
            models.Index(fields=['item_type', 'organization']),
        ]

    def __str__(self):
        return f"{self.get_item_type_display()}: {self.title}"

    def clean(self):
        """Validate that the correct reference is set for item_type."""
        from django.core.exceptions import ValidationError

        if self.item_type == 'milestone' and self.activity:
            raise ValidationError("Milestone items cannot have an activity reference")
        if self.item_type == 'activity' and not self.activity:
            raise ValidationError("Activity items must have an activity reference")
        if self.item_type == 'activity' and self.milestone_data:
            raise ValidationError("Activity items should not have milestone_data")


class QuestTemplateItem(models.Model):
    """
    Join table that connects QuestItemDefinitions to QuestTemplates.
    This is where ordering lives - ensures ordering integrity and atomic updates.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quest_template = models.ForeignKey(
        'QuestTemplate',
        on_delete=models.CASCADE,
        related_name='template_items'
    )
    item_definition = models.ForeignKey(
        'QuestItemDefinition',
        on_delete=models.CASCADE,
        related_name='quest_usages'
    )

    # Ordering is managed here, not in QuestItemDefinition
    order = models.PositiveIntegerField()

    # Prerequisites reference other QuestTemplateItem instances (items within THIS quest)
    prerequisites = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='dependent_items',
        help_text="Items that must be completed before this one"
    )

    # Optional: Override estimated duration for this specific quest
    override_duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Override the item's default duration for this quest"
    )

    # Quest-specific notes/customization
    notes = models.TextField(blank=True, help_text="Admin notes for this item in this quest")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['quest_template', 'order']
        unique_together = [
            ('quest_template', 'order'),  # Ensures no duplicate orders within a quest
            ('quest_template', 'item_definition'),  # Same item can't be added twice to same quest
        ]
        indexes = [
            models.Index(fields=['quest_template', 'order']),
        ]

    def __str__(self):
        return f"{self.quest_template.title} - {self.order}. {self.item_definition.title}"

    @property
    def effective_duration_days(self):
        """Get duration, preferring override if set."""
        return self.override_duration_days or self.item_definition.estimated_duration_days

    def clean(self):
        """Validate prerequisites are within the same quest."""
        from django.core.exceptions import ValidationError

        # This validation only works after save (when prerequisites can be accessed)
        if self.pk:
            for prereq in self.prerequisites.all():
                if prereq.quest_template != self.quest_template:
                    raise ValidationError(
                        f"Prerequisite '{prereq.item_definition.title}' must be in the same quest"
                    )

    def can_be_started(self, enrollment=None):
        """
        Check if this item can be started based on prerequisites.

        Args:
            enrollment: QuestEnrollment instance to check progress against.
                       If None, just checks if prerequisites exist.

        Returns:
            bool: True if item can be started
        """
        if not self.prerequisites.exists():
            return True

        if enrollment is None:
            # No enrollment provided, just check if prerequisites exist
            return False

        # Check if all prerequisites are completed in this enrollment
        from .progress_models import QuestItemProgress

        prerequisite_items = self.prerequisites.all()
        prerequisite_progress = QuestItemProgress.objects.filter(
            enrollment=enrollment,
            template_item__in=prerequisite_items
        )

        # All prerequisites must be completed
        incomplete_count = prerequisite_progress.exclude(status='completed').count()
        return incomplete_count == 0