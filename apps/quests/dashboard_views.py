from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from .models import Milestone
from .serializers import MilestoneWithQuestSerializer


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def upcoming_milestones(request):
    """
    Get the 5 earliest non-completed milestones for the user's dashboard todo list.
    Returns milestones sorted by finish_date, excluding completed ones.
    """
    # Get non-completed milestones for user's quests, ordered by finish date
    milestones = Milestone.objects.filter(
        quest__user=request.user,
        status__in=['not_started', 'in_progress']
    ).select_related('quest').order_by('finish_date')[:5]

    serializer = MilestoneWithQuestSerializer(milestones, many=True)

    return Response({
        'upcoming_milestones': serializer.data
    })