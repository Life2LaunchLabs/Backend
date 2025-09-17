"""
Serializers for the new enrollment-based quest system (V2).
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import QuestTemplate, MilestoneTemplate, QuestEnrollment, MilestoneProgress

User = get_user_model()


class MilestoneTemplateSerializer(serializers.ModelSerializer):
    """Serializer for milestone templates (read-only for most users)"""

    class Meta:
        model = MilestoneTemplate
        fields = [
            'id', 'title', 'description', 'order', 'estimated_finish_days',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class QuestTemplateSerializer(serializers.ModelSerializer):
    """Serializer for quest templates"""
    milestone_templates = MilestoneTemplateSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    enrollment_count = serializers.SerializerMethodField()

    class Meta:
        model = QuestTemplate
        fields = [
            'id', 'title', 'description', 'color', 'category',
            'created_by', 'created_by_username', 'is_shared', 'is_active',
            'created_at', 'updated_at', 'milestone_templates', 'enrollment_count'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_enrollment_count(self, obj):
        """Get the number of users enrolled in this quest template"""
        return obj.enrollments.filter(status='active').count()


class MilestoneProgressSerializer(serializers.ModelSerializer):
    """Serializer for individual milestone progress"""
    milestone_title = serializers.CharField(source='milestone_template.title', read_only=True)
    milestone_description = serializers.CharField(source='milestone_template.description', read_only=True)
    milestone_order = serializers.IntegerField(source='milestone_template.order', read_only=True)
    can_be_started = serializers.SerializerMethodField()

    class Meta:
        model = MilestoneProgress
        fields = [
            'id', 'milestone_template', 'milestone_title', 'milestone_description',
            'milestone_order', 'status', 'started_at', 'completed_at', 'finish_date',
            'notes', 'can_be_started'
        ]
        read_only_fields = ['id', 'milestone_template', 'finish_date']

    def get_can_be_started(self, obj):
        """Check if this milestone can be started based on prerequisites"""
        return obj.can_be_started()


class QuestEnrollmentListSerializer(serializers.ModelSerializer):
    """Simplified serializer for quest enrollment lists (like dashboard)"""
    title = serializers.CharField(source='quest_template.title', read_only=True)
    description = serializers.CharField(source='quest_template.description', read_only=True)
    color = serializers.CharField(source='quest_template.color', read_only=True)
    category = serializers.CharField(source='quest_template.category', read_only=True)
    created_by_username = serializers.CharField(source='quest_template.created_by.username', read_only=True)

    class Meta:
        model = QuestEnrollment
        fields = [
            'id', 'title', 'description', 'color', 'category',
            'created_by_username', 'status', 'enrolled_at', 'completed_at',
            'completed_milestones_count', 'milestones_count', 'progress_percentage'
        ]
        read_only_fields = [
            'id', 'enrolled_at', 'completed_milestones_count',
            'milestones_count', 'progress_percentage'
        ]


class QuestEnrollmentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual quest enrollments"""
    quest_template = QuestTemplateSerializer(read_only=True)
    milestone_progress = MilestoneProgressSerializer(many=True, read_only=True)

    class Meta:
        model = QuestEnrollment
        fields = [
            'id', 'quest_template', 'status', 'enrolled_at', 'completed_at',
            'completed_milestones_count', 'milestones_count', 'progress_percentage',
            'milestone_progress'
        ]
        read_only_fields = [
            'id', 'enrolled_at', 'completed_milestones_count',
            'milestones_count', 'progress_percentage'
        ]


class UpcomingMilestoneSerializer(serializers.ModelSerializer):
    """Serializer for upcoming milestones (dashboard todo list)"""
    quest_title = serializers.CharField(source='enrollment.quest_template.title', read_only=True)
    quest_color = serializers.CharField(source='enrollment.quest_template.color', read_only=True)
    quest_category = serializers.CharField(source='enrollment.quest_template.category', read_only=True)
    milestone_title = serializers.CharField(source='milestone_template.title', read_only=True)
    milestone_description = serializers.CharField(source='milestone_template.description', read_only=True)

    class Meta:
        model = MilestoneProgress
        fields = [
            'id', 'quest_title', 'quest_color', 'quest_category',
            'milestone_title', 'milestone_description', 'status',
            'finish_date', 'started_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'quest_title', 'quest_color', 'quest_category',
            'milestone_title', 'milestone_description', 'finish_date'
        ]


class MilestoneProgressUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating milestone progress status"""

    class Meta:
        model = MilestoneProgress
        fields = ['status', 'notes']

    def update(self, instance, validated_data):
        """Update milestone progress with automatic timestamp handling"""
        new_status = validated_data.get('status', instance.status)

        # Handle status transitions
        if new_status != instance.status:
            if new_status == 'in_progress' and not instance.started_at:
                instance.started_at = timezone.now()
            elif new_status == 'completed' and not instance.completed_at:
                instance.completed_at = timezone.now()
                # Auto-complete the quest if all milestones are done
                enrollment = instance.enrollment
                if not enrollment.milestone_progress.exclude(status='completed').exists():
                    enrollment.status = 'completed'
                    enrollment.completed_at = timezone.now()
                    enrollment.save()

        return super().update(instance, validated_data)