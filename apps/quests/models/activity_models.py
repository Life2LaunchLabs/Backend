"""
Activity models moved from apps.activities to apps.quests.
Activities are now part of the unified quest system.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class MediaAsset(Timestamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage_key = models.CharField(max_length=512, unique=True)
    mime_type = models.CharField(max_length=128)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)  # videos/audio
    checksum = models.CharField(max_length=64, null=True, blank=True)  # for cache busting
    meta = models.JSONField(default=dict, blank=True)  # captions, alt text, etc.

    def __str__(self):
        return f"MediaAsset {self.storage_key} ({self.mime_type})"


class QuestionPackage(Timestamped):
    """
    A logical grouping/versioned source of questions authored elsewhere.
    The backend does not validate the semantics; it just stores metadata.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=50)  # e.g., "2025.09.1"
    meta = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.name} v{self.version}"


class Activity(Timestamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    status = models.CharField(max_length=20, default="draft")  # draft/published/archived
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities"
    )
    author_meta = models.JSONField(default=dict, blank=True)   # tags, owners, etc.

    def __str__(self):
        # Get title from latest version
        latest_version = self.versions.filter(is_published=True).order_by('-version').first()
        title = latest_version.title if latest_version else "Untitled Activity"
        return f"{title} ({self.status})"

    @property
    def title(self):
        """Get title from latest published version."""
        latest_version = self.versions.filter(is_published=True).order_by('-version').first()
        return latest_version.title if latest_version else "Untitled Activity"

    @property
    def description(self):
        """Get description from latest published version."""
        latest_version = self.versions.filter(is_published=True).order_by('-version').first()
        return latest_version.description if latest_version else ""


class ActivityVersion(Timestamped):
    """
    Immutable snapshot produced at publish time.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name="versions")
    version = models.IntegerField()  # monotonic per activity
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    meta = models.JSONField(default=dict, blank=True)  # publishing notes, localization, etc.
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = [("activity", "version")]

    def __str__(self):
        return f"{self.title} v{self.version}"


class Page(Timestamped):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.CASCADE, related_name="pages")
    index = models.PositiveIntegerField()  # ordering
    title = models.CharField(max_length=200, blank=True)
    meta = models.JSONField(default=dict, blank=True)  # e.g., progress label, layout hints

    class Meta:
        unique_together = [("activity_version", "index")]
        ordering = ["index"]

    def __str__(self):
        return f"Page {self.index}: {self.title}"


class Block(Timestamped):
    """
    Generic content block; flexible via type + config.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="blocks")
    index = models.PositiveIntegerField()  # ordering within the page
    block_type = models.CharField(max_length=50)  # "text" | "media" | "question" | "divider" | ...
    config = models.JSONField(default=dict)       # type-specific config

    class Meta:
        unique_together = [("page", "index")]
        ordering = ["index"]

    def __str__(self):
        return f"Block {self.index}: {self.block_type}"


# Legacy models that will be replaced by QuestTemplate/QuestEnrollment system
# Keeping temporarily for reference during migration

class QuestDefinition(Timestamped):
    """
    LEGACY: Rules/templates for assembling quests.
    Will be replaced by QuestTemplate system.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    rules = models.JSONField(default=dict)  # dynamic assembly logic (feature flags, user traits)

    def __str__(self):
        return self.name


class QuestInstance(Timestamped):
    """
    LEGACY: Materialized for a user at start time to freeze the activity lineup.
    Will be replaced by QuestEnrollment system.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quest_instances")
    quest_definition = models.ForeignKey(QuestDefinition, null=True, on_delete=models.SET_NULL)
    items = models.JSONField(default=list)  # ordered list of {"activity_version_id": "...", "meta": {...}}
    status = models.CharField(max_length=20, default="active")  # active|completed|expired

    def __str__(self):
        return f"Quest for {self.user.username}: {self.quest_definition.name if self.quest_definition else 'Unknown'}"


# Activity attempt and progress tracking models

class Attempt(Timestamped):
    """
    One run-through of an activity by a user.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_attempts")
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT)
    quest_instance = models.ForeignKey(QuestInstance, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, default="in_progress")  # in_progress|completed|abandoned
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)  # device info, scoring summary, etc.

    class Meta:
        indexes = [
            models.Index(fields=['user', 'started_at']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['activity_version', 'user', 'started_at']),
            models.Index(fields=['user', 'status', 'started_at']),
        ]
        ordering = ['-started_at']

    def __str__(self):
        return f"Attempt by {self.user.username} on {self.activity_version.title}"


class PageProgress(Timestamped):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="page_progress")
    page = models.ForeignKey(Page, on_delete=models.PROTECT)
    reached = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(auto_now=True)
    data = models.JSONField(default=dict, blank=True)  # autosave snapshot

    class Meta:
        unique_together = [("attempt", "page")]

    def __str__(self):
        return f"Progress on {self.page.title} for attempt {self.attempt.id}"


class Response(Timestamped):
    """
    Store per-question responses (agnostic to type).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="responses")
    question_id = models.CharField(max_length=128)
    question_type = models.CharField(max_length=50)
    page = models.ForeignKey(Page, on_delete=models.PROTECT)
    value = models.JSONField()
    valid = models.BooleanField(default=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['attempt', 'created_at']),
            models.Index(fields=['attempt', 'question_id']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"Response to {self.question_id} by {self.attempt.user.username}"


# New improved architecture: Separate sessions from submissions

class ActivitySession(Timestamped):
    """
    Temporary tracking for in-progress activity sessions.
    Automatically cleaned up after 24 hours if not completed.
    Used for session resume functionality only.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_sessions")
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT)
    quest_instance = models.ForeignKey(QuestInstance, null=True, blank=True, on_delete=models.SET_NULL)
    current_page_index = models.PositiveIntegerField(default=0)
    session_data = models.JSONField(default=dict, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['user', 'activity_version']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['user', 'last_activity']),
        ]
        unique_together = ['user', 'activity_version']
        ordering = ['-last_activity']

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.utils import timezone
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Session: {self.user.username} on {self.activity_version.title}"


class ActivitySubmission(Timestamped):
    """
    Permanent record of completed activity submissions.
    This is what gets displayed on the results page.
    Only created when user completes an activity.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_submissions")
    activity_version = models.ForeignKey(ActivityVersion, on_delete=models.PROTECT)
    quest_instance = models.ForeignKey(QuestInstance, null=True, blank=True, on_delete=models.SET_NULL)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(auto_now_add=True)
    time_taken = models.DurationField()
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'completed_at']),
            models.Index(fields=['activity_version', 'user', 'completed_at']),
            models.Index(fields=['user', 'activity_version', 'completed_at']),
        ]
        ordering = ['-completed_at']

    def __str__(self):
        return f"Submission: {self.user.username} completed {self.activity_version.title}"


class SubmissionResponse(Timestamped):
    """
    Permanent responses tied to completed submissions.
    Only created when a submission is finalized.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(ActivitySubmission, on_delete=models.CASCADE, related_name="responses")
    question_id = models.CharField(max_length=128)
    question_type = models.CharField(max_length=50)
    page = models.ForeignKey(Page, on_delete=models.PROTECT)
    value = models.JSONField()
    valid = models.BooleanField(default=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['submission', 'created_at']),
            models.Index(fields=['submission', 'question_id']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"Response: {self.question_id} in {self.submission.user.username}'s submission"