from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Quest, Milestone
from .serializers import (
    QuestSerializer, QuestListSerializer, MilestoneSerializer, 
    MilestoneCreateUpdateSerializer, MilestoneWithQuestSerializer
)


class QuestViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return QuestListSerializer
        return QuestSerializer
    
    def get_queryset(self):
        return Quest.objects.filter(user=self.request.user).prefetch_related('milestones')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, created_by=self.request.user)
    
    def perform_update(self, serializer):
        quest = self.get_object()
        # Only allow updates if quest is editable
        if not quest.editable:
            raise permissions.PermissionDenied("This quest is not editable.")
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def personal(self, request):
        """Get quests created by the user (Personal category)"""
        queryset = self.get_queryset().filter(created_by=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def other(self, request):
        """Get quests created by others (Other category)"""
        queryset = self.get_queryset().exclude(created_by=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def in_progress_milestones(self, request, pk=None):
        """Get milestones that are currently in progress for this quest"""
        quest = self.get_object()
        milestones = quest.milestones.filter(status='in_progress').order_by('finish_date')
        serializer = MilestoneSerializer(milestones, many=True)
        return Response(serializer.data)


class MilestoneViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MilestoneCreateUpdateSerializer
        return MilestoneSerializer
    
    def get_queryset(self):
        quest_id = self.kwargs.get('quest_pk')
        if quest_id:
            # Nested under quest
            quest = get_object_or_404(Quest, id=quest_id, user=self.request.user)
            return Milestone.objects.filter(quest=quest)
        else:
            # All milestones for user's quests
            return Milestone.objects.filter(quest__user=self.request.user)
    
    def perform_create(self, serializer):
        quest_id = self.kwargs.get('quest_pk')
        quest = get_object_or_404(Quest, id=quest_id, user=self.request.user)
        
        # Check if quest is editable
        if not quest.editable:
            raise permissions.PermissionDenied("Cannot add milestones to a non-editable quest.")
        
        serializer.save(quest=quest)
    
    def perform_update(self, serializer):
        milestone = self.get_object()
        # Check if quest is editable
        if not milestone.quest.editable:
            raise permissions.PermissionDenied("Cannot modify milestones in a non-editable quest.")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Check if quest is editable
        if not instance.quest.editable:
            raise permissions.PermissionDenied("Cannot delete milestones from a non-editable quest.")
        super().perform_destroy(instance)
    
    @action(detail=True, methods=['post'])
    def mark_complete(self, request, pk=None, quest_pk=None):
        """Mark milestone as complete"""
        milestone = self.get_object()
        
        # Check if all prerequisites are complete
        if not milestone.can_be_started():
            incomplete_prereqs = milestone.prerequisites.exclude(status='complete')
            prereq_titles = [p.title for p in incomplete_prereqs]
            return Response(
                {'error': f'Cannot complete milestone. Prerequisites not met: {", ".join(prereq_titles)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        milestone.status = 'complete'
        milestone.save()
        serializer = MilestoneSerializer(milestone)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_in_progress(self, request, pk=None, quest_pk=None):
        """Mark milestone as in progress"""
        milestone = self.get_object()
        
        # Check if all prerequisites are complete
        if not milestone.can_be_started():
            incomplete_prereqs = milestone.prerequisites.exclude(status='complete')
            prereq_titles = [p.title for p in incomplete_prereqs]
            return Response(
                {'error': f'Cannot start milestone. Prerequisites not met: {", ".join(prereq_titles)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        milestone.status = 'in_progress'
        milestone.save()
        serializer = MilestoneSerializer(milestone)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_not_started(self, request, pk=None, quest_pk=None):
        """Mark milestone as not started"""
        milestone = self.get_object()
        milestone.status = 'not_started'
        milestone.save()
        serializer = MilestoneSerializer(milestone)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def in_progress(self, request, quest_pk=None):
        """Get all in-progress milestones across user's quests, sorted by date"""
        queryset = Milestone.objects.filter(
            quest__user=request.user,
            status='in_progress'
        ).select_related('quest').order_by('finish_date')
        
        serializer = MilestoneWithQuestSerializer(queryset, many=True)
        return Response(serializer.data)