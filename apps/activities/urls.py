from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MediaAssetViewSet, QuestionPackageViewSet, ActivityViewSet,
    PageViewSet, BlockViewSet, ActivityVersionViewSet,
    QuestDefinitionViewSet, QuestInstanceViewSet, AttemptViewSet,
    HealthCheckView, DemoDataView, ActivitySubmissionViewSet, ActivityResultsViewSet
)

# Create the main router
router = DefaultRouter()
router.register(r'media', MediaAssetViewSet)
router.register(r'question-packages', QuestionPackageViewSet)
router.register(r'activities', ActivityViewSet)
router.register(r'pages', PageViewSet, basename='page')
router.register(r'blocks', BlockViewSet, basename='block')
router.register(r'activity_versions', ActivityVersionViewSet, basename='activityversion')
router.register(r'quest-definitions', QuestDefinitionViewSet)
router.register(r'quest-instances', QuestInstanceViewSet, basename='questinstance')
router.register(r'attempts', AttemptViewSet, basename='attempt')
# New submission-based endpoints (preferred for results page)
router.register(r'submissions', ActivitySubmissionViewSet, basename='submission')
router.register(r'results', ActivityResultsViewSet, basename='results')

urlpatterns = [
    # Health check
    path('health/', HealthCheckView.as_view(), name='activities-health'),

    # Demo data creation
    path('demo/create/', DemoDataView.as_view(), name='activities-demo-create'),

    # Include all the viewset routes
    path('', include(router.urls)),
]