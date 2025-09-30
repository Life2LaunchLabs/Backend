"""
Quest item serializers (definitions and template items).
"""
from rest_framework import serializers
from ..models import QuestItemDefinition, QuestTemplateItem, QuestItemProgress


class QuestItemDefinitionSerializer(serializers.ModelSerializer):
    """Serialize item definitions (the library of available items)."""
    activity_data = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = QuestItemDefinition
        fields = [
            'id', 'item_type', 'title', 'description',
            'estimated_duration_days', 'activity_data', 'milestone_data',
            'organization', 'organization_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_activity_data(self, obj):
        """Include activity details if this is an activity item."""
        if obj.item_type == 'activity' and obj.activity:
            latest_version = obj.activity.versions.filter(is_published=True).order_by('-version').first()
            return {
                'id': str(obj.activity.id),
                'slug': obj.activity.slug,
                'status': obj.activity.status,
                'title': obj.activity.title,
                'description': obj.activity.description,
                'version': latest_version.version if latest_version else None,
            }
        return None


class QuestItemDefinitionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new item definitions."""

    class Meta:
        model = QuestItemDefinition
        fields = [
            'item_type', 'title', 'description',
            'estimated_duration_days', 'milestone_data',
            'activity', 'organization'
        ]

    def validate(self, data):
        """Validate that the correct references are set for item_type."""
        item_type = data.get('item_type')
        activity = data.get('activity')
        milestone_data = data.get('milestone_data')

        if item_type == 'milestone' and activity:
            raise serializers.ValidationError("Milestone items cannot have an activity reference")
        if item_type == 'activity' and not activity:
            raise serializers.ValidationError("Activity items must have an activity reference")
        if item_type == 'activity' and milestone_data:
            raise serializers.ValidationError("Activity items should not have milestone_data")

        return data


class QuestTemplateItemSerializer(serializers.ModelSerializer):
    """Serialize items within a quest (with ordering and prerequisites)."""
    item_definition = QuestItemDefinitionSerializer(read_only=True)
    effective_duration_days = serializers.IntegerField(read_only=True)
    can_be_started = serializers.SerializerMethodField()

    class Meta:
        model = QuestTemplateItem
        fields = [
            'id', 'order', 'item_definition',
            'override_duration_days', 'effective_duration_days',
            'notes', 'prerequisites', 'can_be_started',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']

    def get_can_be_started(self, obj):
        """Check if this item can be started based on prerequisites."""
        # For admin view, just check if prerequisites exist
        return not obj.prerequisites.exists()


class QuestTemplateItemCreateSerializer(serializers.ModelSerializer):
    """Serializer for adding items to quests."""

    class Meta:
        model = QuestTemplateItem
        fields = [
            'quest_template', 'item_definition', 'order',
            'override_duration_days', 'notes', 'prerequisites'
        ]

    def validate(self, data):
        """Validate that item doesn't already exist in quest."""
        quest_template = data.get('quest_template')
        item_definition = data.get('item_definition')

        # Check if item already exists in quest
        if QuestTemplateItem.objects.filter(
            quest_template=quest_template,
            item_definition=item_definition
        ).exists():
            raise serializers.ValidationError(
                f"Item '{item_definition.title}' already exists in this quest"
            )

        # Validate prerequisites are in the same quest
        prerequisites = data.get('prerequisites', [])
        for prereq in prerequisites:
            if prereq.quest_template != quest_template:
                raise serializers.ValidationError(
                    f"Prerequisite '{prereq.item_definition.title}' must be in the same quest"
                )

        return data


class QuestItemProgressSerializer(serializers.ModelSerializer):
    """Quest item progress for enrolled users."""
    template_item = QuestTemplateItemSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    can_be_started = serializers.BooleanField(read_only=True)

    class Meta:
        model = QuestItemProgress
        fields = [
            'id', 'enrollment', 'template_item', 'status',
            'started_at', 'completed_at', 'target_date',
            'is_overdue', 'days_until_due', 'can_be_started',
            'activity_submission', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']