from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import QuestViewSet, MilestoneViewSet

# Main router for quests
router = DefaultRouter()
router.register(r'quests', QuestViewSet, basename='quest')

# Nested router for milestones under quests
quests_router = routers.NestedDefaultRouter(router, r'quests', lookup='quest')
quests_router.register(r'milestones', MilestoneViewSet, basename='quest-milestones')

# Standalone milestones router (for cross-quest milestone operations)
router.register(r'milestones', MilestoneViewSet, basename='milestone')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(quests_router.urls)),
]