import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class ChatSession(models.Model):
    """
    Ephemeral chat session with TTL for secure session management
    Stores dynamic model configuration and context settings
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.CharField(max_length=255, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    
    # Dynamic configuration stored as JSON
    model_config = models.JSONField(
        default=dict, 
        help_text="Provider, model, and parameter configuration"
    )
    context_config = models.JSONField(
        default=dict,
        help_text="System prompt and context configuration"
    )
    
    # Session lifecycle management
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Optional metadata
    title = models.CharField(max_length=255, blank=True, default="New Chat")
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['session_id']),
            models.Index(fields=['expires_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.session_id:
            # Generate secure session ID
            self.session_id = self._generate_session_id()
        
        if not self.expires_at:
            # Default TTL of 24 hours
            self.expires_at = timezone.now() + timedelta(hours=24)
            
        super().save(*args, **kwargs)
    
    def _generate_session_id(self):
        """Generate cryptographically secure session ID"""
        import secrets
        import hashlib
        
        # Combine timestamp, user ID, and random bytes
        timestamp = str(timezone.now().timestamp())
        user_id = str(self.user.id)
        random_bytes = secrets.token_hex(16)
        
        # Create HMAC-style session ID
        raw_data = f"{timestamp}:{user_id}:{random_bytes}"
        session_hash = hashlib.sha256(raw_data.encode()).hexdigest()[:32]
        
        return f"chat_session_{session_hash}"
    
    def is_expired(self):
        """Check if session has expired"""
        return timezone.now() > self.expires_at
    
    def extend_ttl(self, hours=24):
        """Extend session TTL"""
        self.expires_at = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=['expires_at'])
    
    def get_message_count(self):
        """Get total message count for this session"""
        return self.messages.count()
    
    def __str__(self):
        return f"Session {self.session_id[:16]}... ({self.user.username})"


class ChatMessage(models.Model):
    """
    Individual messages within a chat session
    Supports user, assistant, and system message types
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    
    # Store provider response metadata (tokens used, model version, etc.)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Provider response metadata and metrics"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.role}: {content_preview}"