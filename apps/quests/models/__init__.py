"""
Quest models - unified system for quests, activities, and progress tracking.
"""

# Activity models (moved from apps.activities)
from .activity_models import (
    Timestamped,
    MediaAsset,
    QuestionPackage,
    Activity,
    ActivityVersion,
    Page,
    Block,
    # Legacy models (kept temporarily for reference)
    QuestDefinition,
    QuestInstance,
    # Activity progress tracking
    Attempt,
    PageProgress,
    Response,
    ActivitySession,
    ActivitySubmission,
    SubmissionResponse,
)

# Quest item models (new unified system)
from .quest_item_models import (
    QuestItemDefinition,
    QuestTemplateItem,
)

# Quest template and enrollment models (NEW unified system)
from .quest_models import (
    QuestTemplate,
    QuestEnrollment,
)

# Progress tracking
from .progress_models import (
    QuestItemProgress,
)

# V2 legacy models removed - using unified system now


__all__ = [
    # Activity models
    'Timestamped',
    'MediaAsset',
    'QuestionPackage',
    'Activity',
    'ActivityVersion',
    'Page',
    'Block',
    'QuestDefinition',  # Legacy
    'QuestInstance',  # Legacy
    'Attempt',
    'PageProgress',
    'Response',
    'ActivitySession',
    'ActivitySubmission',
    'SubmissionResponse',
    # Quest item models
    'QuestItemDefinition',
    'QuestTemplateItem',
    # Quest models (NEW unified system)
    'QuestTemplate',
    'QuestEnrollment',
    # Progress tracking
    'QuestItemProgress',
]