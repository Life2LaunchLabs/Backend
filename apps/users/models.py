import uuid
import os
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone


def user_profile_photo_path(instance, filename):
    """
    Generate anonymized file path for user profile photos
    Uses anonymous UUID instead of user ID or username
    """
    ext = filename.split('.')[-1] if '.' in filename else 'png'
    return f'profile_photos/{instance.anonymous_id}/avatar.{ext}'


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""

    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    # Use email as the primary identifier instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # Remove username field entirely - we only use email
    username = None

    # Make email unique and required
    email = models.EmailField(unique=True)

    # Use our custom manager
    objects = UserManager()

    # Privacy-first identifiers
    anonymous_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, null=True)
    
    # Extended profile fields (consider encryption for PII)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    tagline = models.CharField(max_length=200, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    profile_photo = models.ImageField(upload_to=user_profile_photo_path, blank=True, null=True)
    account_created = models.DateTimeField(default=timezone.now)
    
    # Encrypted storage for sensitive PII (future expansion)
    _encrypted_pii = models.TextField(blank=True, null=True, help_text="Encrypted sensitive personal data")

    # Organization admin relationship - default organization for admin access
    default_organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_admin_users',
        help_text="Default organization when user accesses admin features"
    )
    
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
            'email': self.email,
            'bio': self.bio,
            'anonymous_id': str(self.anonymous_id),
            'account_created': self.account_created,
            'profile_photo_url': self.profile_photo.url if self.profile_photo else None,
        }

    def is_organization_admin(self):
        """Check if user is an admin of any organization"""
        return self.admin_organizations.filter(is_active=True).exists()

    def get_admin_organizations(self):
        """Get all organizations this user is an admin of"""
        return self.admin_organizations.filter(is_active=True).order_by('name')

    def set_default_organization(self, organization):
        """Set the default organization for admin access"""
        if organization in self.admin_organizations.all():
            self.default_organization = organization
            self.save(update_fields=['default_organization'])
            return True
        return False

    def get_default_admin_organization(self):
        """Get default organization, or first admin org if none set"""
        if self.default_organization and self.default_organization.is_active:
            return self.default_organization

        first_admin_org = self.get_admin_organizations().first()
        if first_admin_org:
            self.set_default_organization(first_admin_org)
            return first_admin_org

        return None

    def __str__(self):
        return self.email