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