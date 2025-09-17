"""
API Views for the new enrollment-based quest system (V2).
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import QuestTemplate, QuestEnrollment, MilestoneProgress
from .serializers_v2 import (
    QuestTemplateSerializer,
    QuestEnrollmentListSerializer,
    QuestEnrollmentDetailSerializer,
    UpcomingMilestoneSerializer,
    MilestoneProgressUpdateSerializer,
    MilestoneProgressSerializer
)


class QuestTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for browsing available quest templates.
    Users can view shared templates and enroll in them.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = QuestTemplateSerializer

    def get_queryset(self):
        """Return active quest templates that user can enroll in"""
        return QuestTemplate.objects.filter(
            is_active=True,
            is_shared=True
        ).prefetch_related('milestone_templates')

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        """Enroll the current user in this quest template"""
        quest_template = self.get_object()

        # Check if user is already enrolled
        existing_enrollment = QuestEnrollment.objects.filter(
            user=request.user,
            quest_template=quest_template
        ).first()

        if existing_enrollment:
            return Response(
                {'detail': 'You are already enrolled in this quest'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Import here to avoid circular imports
        from .default_quests_v2 import enroll_user_in_quest_template

        enrollment = enroll_user_in_quest_template(request.user, quest_template)
        serializer = QuestEnrollmentDetailSerializer(enrollment)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuestEnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user's quest enrollments.
    This replaces the old Quest ViewSet.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return user's quest enrollments"""
        return QuestEnrollment.objects.filter(
            user=self.request.user
        ).select_related('quest_template', 'quest_template__created_by')

    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'list':
            return QuestEnrollmentListSerializer
        return QuestEnrollmentDetailSerializer

    @action(detail=False, methods=['get'])
    def personal(self, request):
        """Get user's personal quest enrollments (created by themselves)"""
        enrollments = self.get_queryset().filter(
            quest_template__created_by=request.user
        )
        serializer = self.get_serializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def shared(self, request):
        """Get user's shared quest enrollments (created by others)"""
        enrollments = self.get_queryset().exclude(
            quest_template__created_by=request.user
        )
        serializer = self.get_serializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause this quest enrollment"""
        enrollment = self.get_object()
        enrollment.status = 'paused'
        enrollment.save()

        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume this quest enrollment"""
        enrollment = self.get_object()
        enrollment.status = 'active'
        enrollment.save()

        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)


class MilestoneProgressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing milestone progress within quest enrollments.
    This replaces the old Milestone ViewSet.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MilestoneProgressSerializer

    def get_queryset(self):
        """Return user's milestone progress"""
        return MilestoneProgress.objects.filter(
            enrollment__user=self.request.user
        ).select_related(
            'milestone_template',
            'enrollment',
            'enrollment__quest_template'
        )

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming milestones for dashboard - 5 earliest non-completed milestones"""
        queryset = self.get_queryset().filter(
            status__in=['not_started', 'in_progress'],
            enrollment__status='active'
        ).order_by('finish_date')[:5]

        serializer = UpcomingMilestoneSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def in_progress(self, request):
        """Get all in-progress milestones"""
        queryset = self.get_queryset().filter(
            status='in_progress',
            enrollment__status='active'
        ).order_by('finish_date')

        serializer = UpcomingMilestoneSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_in_progress(self, request, pk=None):
        """Mark milestone as in progress"""
        milestone_progress = self.get_object()

        if not milestone_progress.can_be_started():
            return Response(
                {'detail': 'Cannot start this milestone. Prerequisites not completed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        milestone_progress.status = 'in_progress'
        if not milestone_progress.started_at:
            milestone_progress.started_at = timezone.now()
        milestone_progress.save()

        serializer = self.get_serializer(milestone_progress)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_complete(self, request, pk=None):
        """Mark milestone as complete"""
        milestone_progress = self.get_object()

        milestone_progress.status = 'completed'
        if not milestone_progress.completed_at:
            milestone_progress.completed_at = timezone.now()
        milestone_progress.save()

        # Check if quest is now complete
        enrollment = milestone_progress.enrollment
        if not enrollment.milestone_progress.exclude(status='completed').exists():
            enrollment.status = 'completed'
            enrollment.completed_at = timezone.now()
            enrollment.save()

        serializer = self.get_serializer(milestone_progress)
        return Response(serializer.data)

    def get_serializer_class(self):
        """Use update serializer for PATCH/PUT requests"""
        if self.action in ['partial_update', 'update']:
            return MilestoneProgressUpdateSerializer
        return MilestoneProgressSerializer