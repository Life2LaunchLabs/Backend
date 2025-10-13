"""
User-facing quest views for the unified quest system.
These endpoints allow users to view their enrolled quests and track progress.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.quests.models import (
    QuestTemplate, QuestEnrollment, QuestItemProgress
)
from apps.quests.serializers.user_quest_serializers import (
    QuestEnrollmentListSerializer,
    QuestEnrollmentDetailSerializer,
    UpcomingQuestItemSerializer,
    QuestTemplateBasicSerializer,
)


class UserQuestEnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user's quest enrollments.
    List: Get all enrolled quests
    Retrieve: Get specific quest with full item details and progress
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return user's quest enrollments"""
        return QuestEnrollment.objects.filter(
            user=self.request.user
        ).select_related('quest_template').prefetch_related('item_progress')

    def get_serializer_class(self):
        """Use different serializers for list vs detail views"""
        if self.action == 'retrieve':
            return QuestEnrollmentDetailSerializer
        return QuestEnrollmentListSerializer

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active quest enrollments"""
        enrollments = self.get_queryset().filter(status='active')
        serializer = self.get_serializer(enrollments, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def upcoming_quest_items(request):
    """
    Get upcoming quest items for the dashboard.
    Returns the next 5 non-completed items from active quests, ordered by estimated finish date.
    """
    # Get non-completed items from active enrollments
    items = QuestItemProgress.objects.filter(
        enrollment__user=request.user,
        enrollment__status='active',
        status__in=['not_started', 'in_progress']
    ).select_related(
        'enrollment__quest_template',
        'template_item__item_definition',
        'template_item__item_definition__activity'
    ).order_by('template_item__order')[:5]

    serializer = UpcomingQuestItemSerializer(items, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_quest_templates(request):
    """
    Get available quest templates that user can enroll in.
    Returns public/published quest templates.
    """
    templates = QuestTemplate.objects.filter(
        is_public=True,
        status='published'
    )
    # TODO: Re-enable this to exclude already enrolled quests once we have more content
    # .exclude(
    #     enrollments__user=request.user  # Exclude already enrolled
    # )

    serializer = QuestTemplateBasicSerializer(templates, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enroll_in_quest(request, template_id):
    """
    Enroll user in a quest template.
    Creates QuestEnrollment and QuestItemProgress entries for all items.
    """
    try:
        template = QuestTemplate.objects.get(
            id=template_id,
            is_public=True,
            status='published'
        )
    except QuestTemplate.DoesNotExist:
        return Response(
            {'error': 'Quest template not found or not available'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check if already enrolled
    if QuestEnrollment.objects.filter(user=request.user, quest_template=template).exists():
        return Response(
            {'error': 'Already enrolled in this quest'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create enrollment
    enrollment = QuestEnrollment.objects.create(
        user=request.user,
        quest_template=template,
        status='active'
    )

    # Create progress entries for all quest items
    template_items = template.template_items.all().select_related('item_definition')
    for template_item in template_items:
        QuestItemProgress.objects.create(
            enrollment=enrollment,
            template_item=template_item,
            item_definition=template_item.item_definition,
            status='not_started'
        )

    serializer = QuestEnrollmentDetailSerializer(enrollment)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_item_progress(request, item_progress_id):
    """
    Update quest item progress status.
    Allowed transitions: not_started -> in_progress -> completed
    """
    try:
        item_progress = QuestItemProgress.objects.get(
            id=item_progress_id,
            enrollment__user=request.user
        )
    except QuestItemProgress.DoesNotExist:
        return Response(
            {'error': 'Quest item not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    new_status = request.data.get('status')
    if not new_status:
        return Response(
            {'error': 'Status is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Update status
    if new_status == 'in_progress' and item_progress.status == 'not_started':
        item_progress.status = 'in_progress'
        item_progress.started_at = timezone.now()
    elif new_status == 'completed':
        item_progress.status = 'completed'
        item_progress.completed_at = timezone.now()
    else:
        return Response(
            {'error': f'Invalid status transition from {item_progress.status} to {new_status}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    item_progress.save()

    # Check if quest is now complete
    enrollment = item_progress.enrollment
    if not enrollment.item_progress.exclude(status='completed').exists():
        enrollment.status = 'completed'
        enrollment.completed_at = timezone.now()
        enrollment.save()

    from apps.quests.serializers.user_quest_serializers import QuestItemProgressSerializer
    serializer = QuestItemProgressSerializer(item_progress)
    return Response(serializer.data)
