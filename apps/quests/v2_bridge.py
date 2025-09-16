"""
Bridge API views that expose V2 enrollment data in V1 format for the dashboard.
This allows us to use the new V2 system while keeping the existing frontend working.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import QuestEnrollment, MilestoneProgress


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def v2_quests_as_v1(request):
    """
    Return V2 quest enrollments in V1 quest format for the dashboard.
    """
    enrollments = QuestEnrollment.objects.filter(user=request.user).select_related(
        'quest_template', 'quest_template__created_by'
    )

    quests = []
    for enrollment in enrollments:
        template = enrollment.quest_template

        # Format as V1 quest for compatibility
        quest_data = {
            'id': str(enrollment.id),  # Use enrollment ID as quest ID
            'title': template.title,
            'description': template.description,
            'color': template.color,
            'category': template.category,
            'completed_milestones_count': enrollment.completed_milestones_count,
            'milestones_count': enrollment.milestones_count,
            'created_at': enrollment.enrolled_at.isoformat(),
            'updated_at': enrollment.enrolled_at.isoformat(),
        }
        quests.append(quest_data)

    return Response(quests)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def v2_upcoming_milestones_as_v1(request):
    """
    Return V2 upcoming milestones in V1 milestone format for the dashboard.
    """
    upcoming_milestones = MilestoneProgress.objects.filter(
        enrollment__user=request.user,
        status__in=['not_started', 'in_progress'],
        enrollment__status='active'
    ).select_related(
        'milestone_template',
        'enrollment',
        'enrollment__quest_template'
    ).order_by('finish_date')[:5]

    milestones = []
    for milestone_progress in upcoming_milestones:
        template = milestone_progress.milestone_template
        enrollment = milestone_progress.enrollment
        quest_template = enrollment.quest_template

        # Format as V1 milestone for compatibility
        milestone_data = {
            'id': str(milestone_progress.id),
            'title': template.title,
            'description': template.description,
            'finish_date': milestone_progress.finish_date.isoformat(),
            'status': milestone_progress.status,
            'order': template.order,
            'quest': {
                'id': str(enrollment.id),
                'title': quest_template.title,
                'color': quest_template.color,
                'category': quest_template.category,
            },
            'created_at': milestone_progress.enrollment.enrolled_at.isoformat(),
            'updated_at': milestone_progress.enrollment.enrolled_at.isoformat(),
        }
        milestones.append(milestone_data)

    return Response(milestones)