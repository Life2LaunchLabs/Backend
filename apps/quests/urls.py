"""
Quest and activity URL configuration - Admin + User-facing APIs.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    QuestTemplateViewSet,
    QuestItemDefinitionViewSet,
    QuestTemplateItemViewSet,
    ActivityViewSet,
    ActivityVersionViewSet,
    MediaAssetViewSet,
)

from .views.user_quest_views import (
    UserQuestEnrollmentViewSet,
    upcoming_quest_items,
    available_quest_templates,
    enroll_in_quest,
    update_item_progress,
)

from .views.user_activity_views import (
    UserActivityViewSet,
    create_attempt,
    get_attempt,
    complete_attempt,
    submit_response,
    update_page_progress,
    has_completed_activity,
    get_activity_submissions,
    get_submission_details,
)

# Admin router for quest/activity management
admin_router = DefaultRouter()
admin_router.register(r'admin/templates', QuestTemplateViewSet, basename='quest-template')
admin_router.register(r'admin/item-definitions', QuestItemDefinitionViewSet, basename='item-definition')
admin_router.register(r'admin/template-items', QuestTemplateItemViewSet, basename='template-item')
admin_router.register(r'admin/activities', ActivityViewSet, basename='activity')
admin_router.register(r'admin/activity-versions', ActivityVersionViewSet, basename='activity-version')
admin_router.register(r'admin/media', MediaAssetViewSet, basename='media-asset')

# User-facing router for quest enrollments and activities
user_router = DefaultRouter()
user_router.register(r'quests', UserQuestEnrollmentViewSet, basename='user-quest')
user_router.register(r'activities', UserActivityViewSet, basename='user-activity')

urlpatterns = [
    # Admin endpoints
    path('', include(admin_router.urls)),

    # User-facing quest endpoints
    path('', include(user_router.urls)),
    path('quest-items/upcoming/', upcoming_quest_items, name='upcoming-quest-items'),
    path('quest-templates/available/', available_quest_templates, name='available-quest-templates'),
    path('quest-templates/<uuid:template_id>/enroll/', enroll_in_quest, name='enroll-quest'),
    path('quest-items/<uuid:item_progress_id>/progress/', update_item_progress, name='update-item-progress'),

    # User-facing activity session endpoints
    path('attempts/', create_attempt, name='create-attempt'),
    path('attempts/<uuid:attempt_id>/', get_attempt, name='get-attempt'),
    path('attempts/<uuid:attempt_id>/complete/', complete_attempt, name='complete-attempt'),
    path('attempts/<uuid:attempt_id>/submit_response/', submit_response, name='submit-response'),
    path('attempts/<uuid:attempt_id>/update_progress/', update_page_progress, name='update-page-progress'),

    # User-facing activity results endpoints
    path('activities/results/has-completed/<uuid:activity_id>/', has_completed_activity, name='has-completed-activity'),
    path('activities/results/activity/<uuid:activity_id>/', get_activity_submissions, name='get-activity-submissions'),
    path('activities/submissions/<uuid:submission_id>/', get_submission_details, name='get-submission-details'),
]