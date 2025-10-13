"""
Quest views - unified system.
"""
from .admin_quest_views import (
    QuestTemplateViewSet,
    QuestItemDefinitionViewSet,
    QuestTemplateItemViewSet,
)
from .admin_activity_views import (
    ActivityViewSet,
    ActivityVersionViewSet,
)
from .admin_media_views import (
    MediaAssetViewSet,
)

__all__ = [
    'QuestTemplateViewSet',
    'QuestItemDefinitionViewSet',
    'QuestTemplateItemViewSet',
    'ActivityViewSet',
    'ActivityVersionViewSet',
    'MediaAssetViewSet',
]