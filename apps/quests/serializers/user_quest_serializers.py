"""
Serializers for user-facing quest endpoints (unified system)
"""
from rest_framework import serializers
from apps.quests.models import (
    QuestTemplate, QuestEnrollment, QuestItemDefinition,
    QuestTemplateItem, QuestItemProgress, Activity
)


class ActivityBasicSerializer(serializers.ModelSerializer):
    """Basic activity information for quest items"""
    class Meta:
        model = Activity
        fields = ['id', 'slug', 'status']


class QuestItemDefinitionSerializer(serializers.ModelSerializer):
    """Quest item definition (activity or milestone)"""
    activity = ActivityBasicSerializer(read_only=True)

    class Meta:
        model = QuestItemDefinition
        fields = [
            'id', 'item_type', 'title', 'description',
            'estimated_duration_days', 'activity'
        ]


class QuestItemProgressSerializer(serializers.ModelSerializer):
    """User progress on a quest item"""
    item_definition = QuestItemDefinitionSerializer(source='template_item.item_definition', read_only=True)
    template_item_id = serializers.UUIDField(source='template_item.id', read_only=True)
    order = serializers.IntegerField(source='template_item.order', read_only=True)

    class Meta:
        model = QuestItemProgress
        fields = [
            'id', 'template_item_id', 'item_definition', 'status',
            'started_at', 'completed_at', 'order', 'notes'
        ]


class QuestTemplateBasicSerializer(serializers.ModelSerializer):
    """Basic quest template info"""
    class Meta:
        model = QuestTemplate
        fields = ['id', 'title', 'description', 'color', 'category']


class QuestEnrollmentListSerializer(serializers.ModelSerializer):
    """Quest enrollment for list view"""
    quest_template = QuestTemplateBasicSerializer(read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)
    completed_items = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = QuestEnrollment
        fields = [
            'id', 'quest_template', 'status', 'enrolled_at',
            'completed_at', 'progress_percentage', 'completed_items', 'total_items'
        ]

    def get_completed_items(self, obj):
        return obj.item_progress.filter(status='completed').count()

    def get_total_items(self, obj):
        return obj.item_progress.count()


class QuestEnrollmentDetailSerializer(serializers.ModelSerializer):
    """Quest enrollment with full item progress"""
    quest_template = QuestTemplateBasicSerializer(read_only=True)
    items = serializers.SerializerMethodField()
    progress_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = QuestEnrollment
        fields = [
            'id', 'quest_template', 'status', 'enrolled_at',
            'completed_at', 'progress_percentage', 'items'
        ]

    def get_items(self, obj):
        """Get all quest items with progress, ordered by template order"""
        items = obj.item_progress.all().select_related(
            'template_item', 'template_item__item_definition',
            'template_item__item_definition__activity'
        ).order_by('template_item__order')
        return QuestItemProgressSerializer(items, many=True).data


class UpcomingQuestItemSerializer(serializers.ModelSerializer):
    """Quest item for dashboard upcoming list"""
    quest_title = serializers.CharField(source='enrollment.quest_template.title', read_only=True)
    quest_color = serializers.CharField(source='enrollment.quest_template.color', read_only=True)
    item_definition = QuestItemDefinitionSerializer(source='template_item.item_definition', read_only=True)
    finish_date = serializers.SerializerMethodField()

    class Meta:
        model = QuestItemProgress
        fields = [
            'id', 'quest_title', 'quest_color', 'item_definition',
            'status', 'started_at', 'finish_date', 'notes'
        ]

    def get_finish_date(self, obj):
        """Calculate estimated finish date based on enrollment date + item order"""
        if obj.completed_at:
            return obj.completed_at.date()

        # Estimate based on enrollment date + sum of previous items' durations
        enrollment = obj.enrollment
        template_item = obj.template_item

        # Get all items before this one in the quest
        previous_items = enrollment.quest_template.template_items.filter(
            order__lt=template_item.order
        ).select_related('item_definition')

        # Sum up durations
        days_offset = sum(
            item.effective_duration_days
            for item in previous_items
        )

        # Add this item's duration
        days_offset += template_item.effective_duration_days

        # Calculate from enrollment date
        from datetime import timedelta
        estimated_date = enrollment.enrolled_at.date() + timedelta(days=days_offset)

        return estimated_date
