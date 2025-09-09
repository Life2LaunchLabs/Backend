import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# Create your models here.
class User(AbstractUser):
    # Privacy-first identifiers
    anonymous_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, null=True)
    
    # Extended profile fields (consider encryption for PII)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    account_created = models.DateTimeField(default=timezone.now)