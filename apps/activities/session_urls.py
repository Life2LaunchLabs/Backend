"""
URL routing for session-based activity system.
Supports the new /activities/active/{id}/{page} pattern.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .session_views import (
    ActivitySessionViewSet,
    ActivityPageView,
    ActivityCompletionViewSet,
    SessionAnalyticsView,
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'sessions', ActivitySessionViewSet, basename='activitysession')
router.register(r'completions', ActivityCompletionViewSet, basename='activitycompletion')

# Define URL patterns
urlpatterns = [
    # Session management endpoints
    path('', include(router.urls)),

    # Direct page access for /activities/active/{id}/{page}
    path('active/<uuid:activity_id>/<int:page_index>/',
         ActivityPageView.as_view(),
         name='activity-page'),

    # Analytics and admin endpoints
    path('analytics/sessions/',
         SessionAnalyticsView.as_view(),
         name='session-analytics'),
]

"""
Complete API endpoint structure:

Session Management:
- POST /api/activities/sessions/start_or_continue/ - Start new or get existing session
- GET  /api/activities/sessions/ - List user's active sessions
- POST /api/activities/sessions/{id}/continue_session/ - Continue existing session
- POST /api/activities/sessions/{id}/navigate/ - Navigate to page
- POST /api/activities/sessions/{id}/save_response/ - Save response
- POST /api/activities/sessions/{id}/complete/ - Complete session

Page Access:
- GET  /api/activities/active/{activity_id}/{page_index}/ - Get page content with session

Completion Tracking:
- GET  /api/activities/completions/ - List user's completions
- GET  /api/activities/completions/{id}/ - Get completion details

Analytics (Admin):
- GET  /api/activities/analytics/sessions/ - Session analytics
- POST /api/activities/analytics/sessions/ - Trigger cleanup

Frontend URL Pattern:
/activities/active/{activity_id}/{page_index}

This maps to backend:
GET /api/activities/active/{activity_id}/{page_index}/

The backend will:
1. Get or create session for user + activity
2. Navigate to requested page
3. Return page content + session context
4. Handle continue/restart decision logic
"""