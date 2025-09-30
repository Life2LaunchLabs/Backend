from django.contrib import admin
from .models import (
    MediaAsset, QuestionPackage, Activity, ActivityVersion,
    Page, Block, QuestDefinition, QuestInstance, Attempt,
    PageProgress, Response
)


class BlockInline(admin.TabularInline):
    model = Block
    extra = 1
    ordering = ['index']


class PageInline(admin.TabularInline):
    model = Page
    extra = 1
    ordering = ['index']


class ActivityVersionInline(admin.TabularInline):
    model = ActivityVersion
    extra = 0
    readonly_fields = ['version', 'created_at']


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ['storage_key', 'mime_type', 'width', 'height', 'created_at']
    list_filter = ['mime_type', 'created_at']
    search_fields = ['storage_key']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(QuestionPackage)
class QuestionPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'created_at']
    list_filter = ['version', 'created_at']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['slug']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [ActivityVersionInline]

    def title(self, obj):
        """Display title from latest version"""
        return obj.title
    title.short_description = 'Title'


@admin.register(ActivityVersion)
class ActivityVersionAdmin(admin.ModelAdmin):
    list_display = ['title', 'activity', 'version', 'is_published', 'created_at']
    list_filter = ['is_published', 'created_at']
    search_fields = ['title', 'activity__slug']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [PageInline]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ['title', 'activity_version', 'index', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'activity_version__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [BlockInline]
    ordering = ['activity_version', 'index']


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    list_display = ['block_type', 'page', 'index', 'created_at']
    list_filter = ['block_type', 'created_at']
    search_fields = ['block_type', 'page__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['page', 'index']


@admin.register(QuestDefinition)
class QuestDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(QuestInstance)
class QuestInstanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'quest_definition', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__email', 'quest_definition__name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_version', 'status', 'started_at', 'completed_at']
    list_filter = ['status', 'started_at']
    search_fields = ['user__email', 'activity_version__title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(PageProgress)
class PageProgressAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'page', 'reached', 'last_seen_at']
    list_filter = ['reached', 'last_seen_at']
    search_fields = ['attempt__user__email', 'page__title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question_id', 'question_type', 'valid', 'created_at']
    list_filter = ['question_type', 'valid', 'created_at']
    search_fields = ['attempt__user__email', 'question_id']
    readonly_fields = ['id', 'created_at', 'updated_at']