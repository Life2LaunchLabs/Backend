from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import QuestViewSet, MilestoneViewSet
from .views_v2 import QuestTemplateViewSet, QuestEnrollmentViewSet, MilestoneProgressViewSet
from .dashboard_views import upcoming_milestones
from .v2_bridge import v2_quests_as_v1, v2_upcoming_milestones_as_v1

# V1 API (Legacy - for backward compatibility)
router_v1 = DefaultRouter()
router_v1.register(r'quests', QuestViewSet, basename='quest')

# Nested router for milestones under quests (V1)
quests_router_v1 = routers.NestedDefaultRouter(router_v1, r'quests', lookup='quest')
quests_router_v1.register(r'milestones', MilestoneViewSet, basename='quest-milestones')

# Standalone milestones router (V1)
router_v1.register(r'milestones', MilestoneViewSet, basename='milestone')

# V2 API (New enrollment-based system)
router_v2 = DefaultRouter()
router_v2.register(r'quest-templates', QuestTemplateViewSet, basename='quest-template')
router_v2.register(r'enrollments', QuestEnrollmentViewSet, basename='quest-enrollment')
router_v2.register(r'milestone-progress', MilestoneProgressViewSet, basename='milestone-progress')

urlpatterns = [
    # V1 API (legacy)
    path('', include(router_v1.urls)),
    path('', include(quests_router_v1.urls)),
    path('dashboard/upcoming-milestones/', upcoming_milestones, name='upcoming_milestones'),

    # V2 API (new enrollment system)
    path('quests/v2/', include(router_v2.urls)),

    # V2 Bridge APIs (V2 data in V1 format for dashboard compatibility)
    path('v2/quests/', v2_quests_as_v1, name='v2_quests_as_v1'),
    path('v2/milestones/upcoming/', v2_upcoming_milestones_as_v1, name='v2_upcoming_milestones_as_v1'),
]