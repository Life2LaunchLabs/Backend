from rest_framework import serializers
from .models import Quest, Milestone


class MilestoneSerializer(serializers.ModelSerializer):
    prerequisites = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Milestone.objects.all(), 
        required=False
    )
    can_be_started = serializers.ReadOnlyField()
    
    class Meta:
        model = Milestone
        fields = [
            'id', 'title', 'description', 'finish_date', 'status', 
            'order', 'prerequisites', 'can_be_started', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MilestoneWithQuestSerializer(serializers.ModelSerializer):
    prerequisites = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Milestone.objects.all(), 
        required=False
    )
    can_be_started = serializers.ReadOnlyField()
    quest = serializers.SerializerMethodField()
    
    class Meta:
        model = Milestone
        fields = [
            'id', 'title', 'description', 'finish_date', 'status', 
            'order', 'prerequisites', 'can_be_started', 'quest', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'quest']
    
    def get_quest(self, obj):
        return {
            'id': obj.quest.id,
            'title': obj.quest.title,
            'color': obj.quest.color
        }


class QuestSerializer(serializers.ModelSerializer):
    milestones = MilestoneSerializer(many=True, read_only=True)
    category = serializers.ReadOnlyField()
    is_personal = serializers.ReadOnlyField()
    
    class Meta:
        model = Quest
        fields = [
            'id', 'title', 'description', 'color', 'editable', 'template_id',
            'category', 'is_personal', 'milestones', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'category', 'is_personal']
    
    def create(self, validated_data):
        # Set user and created_by to the requesting user
        user = self.context['request'].user
        validated_data['user'] = user
        validated_data['created_by'] = user
        return super().create(validated_data)


class QuestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for quest list views"""
    milestones_count = serializers.SerializerMethodField()
    completed_milestones_count = serializers.SerializerMethodField()
    in_progress_milestones_count = serializers.SerializerMethodField()
    category = serializers.ReadOnlyField()
    is_personal = serializers.ReadOnlyField()
    
    class Meta:
        model = Quest
        fields = [
            'id', 'title', 'description', 'color', 'category', 'is_personal',
            'milestones_count', 'completed_milestones_count', 'in_progress_milestones_count',
            'created_at', 'updated_at'
        ]
    
    def get_milestones_count(self, obj):
        return obj.milestones.count()
    
    def get_completed_milestones_count(self, obj):
        return obj.milestones.filter(status='complete').count()
    
    def get_in_progress_milestones_count(self, obj):
        return obj.milestones.filter(status='in_progress').count()


class MilestoneCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating milestones"""
    prerequisites = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Milestone.objects.all(), 
        required=False
    )
    
    class Meta:
        model = Milestone
        fields = [
            'title', 'description', 'finish_date', 'status', 
            'order', 'prerequisites'
        ]
    
    def validate_prerequisites(self, value):
        """Ensure prerequisites belong to the same quest"""
        if value and hasattr(self, 'instance') and self.instance:
            quest = self.instance.quest
            for prereq in value:
                if prereq.quest != quest:
                    raise serializers.ValidationError(
                        f"Prerequisite '{prereq.title}' must belong to the same quest."
                    )
        return value
    
    def validate(self, data):
        """Additional validation for milestone logic"""
        # Prevent circular dependencies (basic check)
        if 'prerequisites' in data and hasattr(self, 'instance') and self.instance:
            for prereq in data['prerequisites']:
                if prereq == self.instance:
                    raise serializers.ValidationError("A milestone cannot be a prerequisite of itself.")
        
        return data