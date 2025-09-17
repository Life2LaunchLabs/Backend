from django.contrib import admin
from .models import Quest, Milestone


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'created_by', 'category', 'editable', 'created_at']
    list_filter = ['editable', 'created_at', 'created_by']
    search_fields = ['title', 'description', 'user__username', 'created_by__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'category']
    fieldsets = (
        (None, {
            'fields': ('id', 'title', 'description', 'color')
        }),
        ('Ownership', {
            'fields': ('user', 'created_by', 'template_id', 'editable')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ['title', 'quest', 'status', 'finish_date', 'order', 'created_at']
    list_filter = ['status', 'finish_date', 'quest__title']
    search_fields = ['title', 'description', 'quest__title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['prerequisites']
    fieldsets = (
        (None, {
            'fields': ('id', 'quest', 'title', 'description', 'finish_date', 'status', 'order')
        }),
        ('Dependencies', {
            'fields': ('prerequisites',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )