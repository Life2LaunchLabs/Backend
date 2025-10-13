"""
Django admin configuration for quests app (unified system).
"""
from django.contrib import admin
from .models import (
    # New unified quest system
    QuestTemplate,
    QuestEnrollment,
    QuestItemDefinition,
    QuestTemplateItem,
    QuestItemProgress,
    # Activities
    Activity,
    ActivityVersion,
    Page,
    Block,
    MediaAsset,
    QuestionPackage,
    # Activity progress tracking
    Attempt,
    ActivitySubmission,
)


# Quest Template Admin

@admin.register(QuestTemplate)
class QuestTemplateAdmin(admin.ModelAdmin):
    list_display = ['title', 'organization', 'created_by', 'status', 'is_public', 'items_count', 'created_at']
    list_filter = ['status', 'is_public', 'organization', 'created_at']
    search_fields = ['title', 'description', 'created_by__email', 'organization__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'estimated_total_days']
    fieldsets = (
        (None, {
            'fields': ('id', 'title', 'description', 'color', 'category')
        }),
        ('Organization & Ownership', {
            'fields': ('organization', 'created_by')
        }),
        ('Visibility', {
            'fields': ('status', 'is_public', 'is_template')
        }),
        ('Metadata', {
            'fields': ('estimated_total_days', 'meta')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(QuestEnrollment)
class QuestEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'quest_template', 'status', 'progress_percentage', 'enrolled_at', 'completed_at']
    list_filter = ['status', 'enrolled_at']
    search_fields = ['user__email', 'quest_template__title']
    readonly_fields = ['id', 'enrolled_at', 'completed_at', 'progress_percentage', 'completed_items_count', 'items_count']
    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'quest_template', 'status')
        }),
        ('Progress', {
            'fields': ('progress_percentage', 'completed_items_count', 'items_count')
        }),
        ('Timestamps', {
            'fields': ('enrolled_at', 'completed_at'),
        }),
    )


# Quest Item Admin

@admin.register(QuestItemDefinition)
class QuestItemDefinitionAdmin(admin.ModelAdmin):
    list_display = ['title', 'item_type', 'organization', 'estimated_duration_days', 'created_at']
    list_filter = ['item_type', 'organization', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('id', 'item_type', 'title', 'description', 'estimated_duration_days')
        }),
        ('References', {
            'fields': ('activity', 'milestone_data')
        }),
        ('Organization', {
            'fields': ('organization',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(QuestTemplateItem)
class QuestTemplateItemAdmin(admin.ModelAdmin):
    list_display = ['quest_template', 'order', 'item_definition', 'effective_duration_days']
    list_filter = ['quest_template']
    search_fields = ['quest_template__title', 'item_definition__title']
    readonly_fields = ['id', 'created_at', 'effective_duration_days']
    filter_horizontal = ['prerequisites']
    fieldsets = (
        (None, {
            'fields': ('id', 'quest_template', 'item_definition', 'order')
        }),
        ('Customization', {
            'fields': ('override_duration_days', 'effective_duration_days', 'notes')
        }),
        ('Dependencies', {
            'fields': ('prerequisites',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(QuestItemProgress)
class QuestItemProgressAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'template_item', 'status', 'target_date', 'is_overdue']
    list_filter = ['status', 'target_date']
    search_fields = ['enrollment__user__email', 'template_item__item_definition__title']
    readonly_fields = ['id', 'created_at', 'updated_at', 'is_overdue', 'days_until_due', 'can_be_started']
    fieldsets = (
        (None, {
            'fields': ('id', 'enrollment', 'template_item', 'status')
        }),
        ('Timeline', {
            'fields': ('target_date', 'started_at', 'completed_at', 'is_overdue', 'days_until_due')
        }),
        ('Activity Link', {
            'fields': ('activity_submission',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Activity Admin

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'status', 'organization', 'created_at']
    list_filter = ['status', 'organization', 'created_at']
    search_fields = ['slug', 'versions__title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ActivityVersion)
class ActivityVersionAdmin(admin.ModelAdmin):
    list_display = ['title', 'activity', 'version', 'is_published', 'created_at']
    list_filter = ['is_published', 'created_at']
    search_fields = ['title', 'activity__slug']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ['title', 'activity_version', 'index', 'created_at']
    list_filter = ['activity_version']
    search_fields = ['title', 'activity_version__title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ['page', 'index', 'block_type', 'created_at']
    list_filter = ['block_type']
    search_fields = ['page__title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ['storage_key', 'mime_type', 'width', 'height', 'created_at']
    list_filter = ['mime_type', 'created_at']
    search_fields = ['storage_key']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(QuestionPackage)
class QuestionPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_version', 'status', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at']
    search_fields = ['user__email', 'activity_version__title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ActivitySubmission)
class ActivitySubmissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_version', 'completed_at', 'time_taken']
    list_filter = ['completed_at']
    search_fields = ['user__email', 'activity_version__title']
    readonly_fields = ['id', 'created_at', 'updated_at', 'completed_at', 'time_taken']