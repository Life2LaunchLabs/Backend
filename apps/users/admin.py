from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Extended Profile', {'fields': ('anonymous_id', 'middle_name', 'bio', 'birth_date', 'account_created')}),
    )
    readonly_fields = ('anonymous_id', 'account_created')
