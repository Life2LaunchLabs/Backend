from django.contrib import admin
from .models import CourseSession, QuestionResponse, ConversationTurn


@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'course', 'status', 'completion_percentage', 
        'answered_questions', 'total_questions', 'character_used', 'started_at'
    ]
    list_filter = ['status', 'character_used', 'course', 'schema_outdated']
    search_fields = ['user__username', 'course__title', 'id']
    readonly_fields = [
        'id', 'agenda_version_hash', 'agenda_snapshot', 'started_at', 
        'completion_percentage', 'answered_questions'
    ]
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'course', 'status', 'character_used')
        }),
        ('Progress', {
            'fields': ('completion_percentage', 'answered_questions', 'total_questions')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'last_activity_at')
        }),
        ('Schema Tracking', {
            'fields': ('agenda_version_hash', 'schema_outdated', 'agenda_snapshot'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('session_notes',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'course')


@admin.register(QuestionResponse)
class QuestionResponseAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'question_number', 'question_id', 'status', 
        'response_quality_score', 'first_response_at', 'completed_at'
    ]
    list_filter = ['status', 'follow_up_needed', 'session__course']
    search_fields = ['question_id', 'question_text', 'session__id']
    readonly_fields = ['id', 'first_response_at', 'completed_at']
    fieldsets = (
        ('Question Info', {
            'fields': ('session', 'question_number', 'question_id', 'question_text')
        }),
        ('Response Data', {
            'fields': ('raw_response', 'processed_response', 'status')
        }),
        ('Analysis', {
            'fields': ('response_quality_score', 'ai_analysis', 'follow_up_needed'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('response_metadata', 'first_response_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session', 'session__user', 'session__course')


@admin.register(ConversationTurn)
class ConversationTurnAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'turn_number', 'role', 'content_preview', 
        'emote', 'question_context', 'timestamp'
    ]
    list_filter = ['role', 'session__course', 'emote']
    search_fields = ['content', 'session__id']
    readonly_fields = ['timestamp']
    fieldsets = (
        ('Message Info', {
            'fields': ('session', 'turn_number', 'role', 'content')
        }),
        ('AI Metadata', {
            'fields': ('emote', 'quick_inputs', 'system_data'),
            'classes': ('collapse',)
        }),
        ('Context', {
            'fields': ('question_context', 'timestamp'),
            'classes': ('collapse',)
        })
    )
    
    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
    content_preview.short_description = "Content Preview"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'session', 'session__user', 'session__course', 'question_context'
        )