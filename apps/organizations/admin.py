from django.contrib import admin
from .models import Organization, OrganizationAdmin as OrgAdmin


class OrganizationAdminInline(admin.TabularInline):
    model = OrgAdmin
    extra = 0
    verbose_name = "Admin User"
    verbose_name_plural = "Admin Users"


@admin.register(Organization)
class OrganizationModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [OrganizationAdminInline]


@admin.register(OrgAdmin)
class OrganizationAdminModelAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'created_at']
    list_filter = ['role', 'organization', 'created_at']
    search_fields = ['user__email', 'organization__name']
