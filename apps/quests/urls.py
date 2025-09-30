"""
Quest and activity URL configuration - Admin API.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    QuestTemplateViewSet,
    QuestItemDefinitionViewSet,
    QuestTemplateItemViewSet,
    ActivityViewSet,
    ActivityVersionViewSet,
)

# Main router for top-level resources
router = DefaultRouter()

# Admin quest management
router.register(r'admin/templates', QuestTemplateViewSet, basename='quest-template')
router.register(r'admin/item-definitions', QuestItemDefinitionViewSet, basename='item-definition')
router.register(r'admin/template-items', QuestTemplateItemViewSet, basename='template-item')

# Admin activity management
router.register(r'admin/activities', ActivityViewSet, basename='activity')
router.register(r'admin/activity-versions', ActivityVersionViewSet, basename='activity-version')

urlpatterns = [
    path('', include(router.urls)),
]