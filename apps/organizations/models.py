import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Organization(Timestamped):
    """
    Organization model for grouping users and managing admin access.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    meta = models.JSONField(default=dict, blank=True)

    # Many-to-many relationship with users who are admins of this organization
    admins = models.ManyToManyField(
        User,
        related_name='admin_organizations',
        through='OrganizationAdmin',
        blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class OrganizationAdmin(Timestamped):
    """
    Through model for user-organization admin relationships.
    Allows for additional metadata about the admin relationship.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, default='admin')  # Future: different admin roles
    permissions = models.JSONField(default=dict, blank=True)  # Future: granular permissions

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.role})"

    class Meta:
        unique_together = [('user', 'organization')]
        ordering = ['organization__name', 'user__email']
