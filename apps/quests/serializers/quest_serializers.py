"""
Quest template and enrollment serializers.
"""
from rest_framework import serializers
from ..models import QuestTemplate, QuestEnrollment


class QuestTemplateSerializer(serializers.ModelSerializer):
    """List/summary view of quest templates."""
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    items_count = serializers.SerializerMethodField()
    milestones_count = serializers.SerializerMethodField()
    activities_count = serializers.SerializerMethodField()

    class Meta:
        model = QuestTemplate
        fields = [
            'id', 'title', 'description', 'color', 'category',
            'organization', 'organization_name',
            'created_by', 'created_by_email',
            'is_public', 'is_template', 'status',
            'estimated_total_days',
            'items_count', 'milestones_count', 'activities_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'estimated_total_days']

    def get_items_count(self, obj):
        return obj.items_count

    def get_milestones_count(self, obj):
        return obj.milestones_count

    def get_activities_count(self, obj):
        return obj.activities_count


class QuestTemplateDetailSerializer(serializers.ModelSerializer):
    """Detailed quest template with all items in order."""
    from .quest_item_serializers import QuestTemplateItemSerializer

    organization_name = serializers.CharField(source='organization.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    template_items = QuestTemplateItemSerializer(many=True, read_only=True)
    can_edit = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = QuestTemplate
        fields = [
            'id', 'title', 'description', 'color', 'category',
            'organization', 'organization_name',
            'created_by', 'created_by_email',
            'is_public', 'is_template', 'status',
            'estimated_total_days', 'items_count',
            'template_items', 'can_edit', 'meta',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'estimated_total_days']

    def get_items_count(self, obj):
        return obj.items_count

    def get_can_edit(self, obj):
        """Check if requesting user can edit this quest."""
        request = self.context.get('request')
        if not request or not request.user:
            return False

        # Check if user is admin of the quest's organization
        return request.user.admin_organizations.filter(id=obj.organization.id).exists()


class QuestTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new quest templates."""

    class Meta:
        model = QuestTemplate
        fields = [
            'title', 'description', 'color', 'category',
            'organization', 'is_public', 'is_template', 'status', 'meta'
        ]

    def create(self, validated_data):
        # Set created_by from request user
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class QuestEnrollmentSerializer(serializers.ModelSerializer):
    """Quest enrollment with progress information."""
    quest_template = QuestTemplateSerializer(read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)
    completed_items_count = serializers.IntegerField(read_only=True)
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = QuestEnrollment
        fields = [
            'id', 'user', 'user_email', 'quest_template',
            'status', 'enrolled_at', 'completed_at',
            'progress_percentage', 'completed_items_count', 'items_count'
        ]
        read_only_fields = ['id', 'enrolled_at', 'completed_at']