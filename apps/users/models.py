import uuid
import os
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


def user_profile_photo_path(instance, filename):
    """
    Generate anonymized file path for user profile photos
    Uses anonymous UUID instead of user ID or username
    """
    ext = filename.split('.')[-1] if '.' in filename else 'png'
    return f'profile_photos/{instance.anonymous_id}/avatar.{ext}'


class User(AbstractUser):
    # Privacy-first identifiers
    anonymous_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, null=True)
    
    # Extended profile fields (consider encryption for PII)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    profile_photo = models.ImageField(upload_to=user_profile_photo_path, blank=True, null=True)
    account_created = models.DateTimeField(default=timezone.now)
    
    # Encrypted storage for sensitive PII (future expansion)
    _encrypted_pii = models.TextField(blank=True, null=True, help_text="Encrypted sensitive personal data")
    
    def get_full_name_with_middle(self):
        """Return the full name including middle name"""
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(filter(None, parts))
    
    def get_anonymous_display_name(self):
        """Get a safe display name that doesn't expose real identity"""
        return f"User_{str(self.anonymous_id)[:8]}"
    
    @property
    def safe_file_identifier(self):
        """Returns the anonymous ID for file operations"""
        return str(self.anonymous_id)
    
    def encrypt_sensitive_data(self, data_dict):
        """
        Store sensitive data in encrypted format
        Args:
            data_dict: Dictionary of sensitive user data to encrypt
        """
        from .encryption import user_encryption
        self._encrypted_pii = user_encryption.encrypt_user_pii(data_dict)
    
    def get_encrypted_data(self):
        """
        Retrieve and decrypt sensitive user data
        Returns:
            Dictionary of decrypted sensitive data
        """
        from .encryption import user_encryption
        return user_encryption.decrypt_user_pii(self._encrypted_pii)
    
    def get_safe_profile_data(self):
        """
        Return profile data safe for API responses
        Excludes sensitive information
        """
        return {
            'username': self.username,
            'bio': self.bio,
            'anonymous_id': str(self.anonymous_id),
            'account_created': self.account_created,
            'profile_photo_url': self.profile_photo.url if self.profile_photo else None,
        }
    
    def __str__(self):
        return self.username