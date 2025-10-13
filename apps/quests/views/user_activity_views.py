"""
User-facing activity views for engaging with activities.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta

from ..models import Activity, ActivityVersion, Attempt, PageProgress, Response as ActivityResponse
from ..serializers import ActivityDetailSerializer


class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User-facing activity endpoints for viewing and engaging with activities.
    Read-only - users cannot create/edit activities, only view published ones.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ActivityDetailSerializer

    def get_queryset(self):
        """Return all published activities (users don't belong to organizations)."""
        return Activity.objects.filter(
            status='published'
        ).prefetch_related(
            'versions__pages__blocks'
        ).select_related('organization')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_attempt(request):
    """Create a new attempt for an activity."""
    activity_version_id = request.data.get('activity_version_id')
    quest_instance_id = request.data.get('quest_instance_id')

    if not activity_version_id:
        return Response(
            {'error': 'activity_version_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        activity_version = ActivityVersion.objects.get(id=activity_version_id)
    except ActivityVersion.DoesNotExist:
        return Response(
            {'error': 'Activity version not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Create attempt
    attempt = Attempt.objects.create(
        user=request.user,
        activity_version=activity_version,
        quest_instance_id=quest_instance_id,
        status='in_progress',
        meta=request.data.get('meta', {})
    )

    return Response({
        'id': str(attempt.id),
        'user': attempt.user.id,
        'activity_version': str(attempt.activity_version.id),
        'status': attempt.status,
        'started_at': attempt.started_at.isoformat(),
        'meta': attempt.meta
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_attempt(request, attempt_id):
    """Get attempt details."""
    try:
        attempt = Attempt.objects.get(id=attempt_id, user=request.user)
    except Attempt.DoesNotExist:
        return Response(
            {'error': 'Attempt not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response({
        'id': str(attempt.id),
        'user': attempt.user.id,
        'activity_version': str(attempt.activity_version.id),
        'status': attempt.status,
        'started_at': attempt.started_at.isoformat(),
        'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
        'meta': attempt.meta
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_attempt(request, attempt_id):
    """Complete an attempt."""
    try:
        attempt = Attempt.objects.get(id=attempt_id, user=request.user)
    except Attempt.DoesNotExist:
        return Response(
            {'error': 'Attempt not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if attempt.status != 'in_progress':
        return Response(
            {'error': 'Attempt is not in progress'},
            status=status.HTTP_400_BAD_REQUEST
        )

    attempt.status = 'completed'
    attempt.completed_at = timezone.now()
    attempt.save()

    return Response({
        'id': str(attempt.id),
        'status': attempt.status,
        'completed_at': attempt.completed_at.isoformat()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_response(request, attempt_id):
    """Submit a response to a question."""
    try:
        attempt = Attempt.objects.get(id=attempt_id, user=request.user)
    except Attempt.DoesNotExist:
        return Response(
            {'error': 'Attempt not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    question_id = request.data.get('question_id')
    question_type = request.data.get('question_type')
    page_id = request.data.get('page_id')
    value = request.data.get('value')
    valid = request.data.get('valid', True)

    if not all([question_id, question_type, page_id, value is not None]):
        return Response(
            {'error': 'Missing required fields'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create or update response
    from ..models import Page
    try:
        page = Page.objects.get(id=page_id)
    except Page.DoesNotExist:
        return Response(
            {'error': 'Page not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    response_obj, created = ActivityResponse.objects.update_or_create(
        attempt=attempt,
        question_id=question_id,
        defaults={
            'question_type': question_type,
            'page': page,
            'value': value,
            'valid': valid,
            'meta': request.data.get('meta', {})
        }
    )

    return Response({
        'id': str(response_obj.id),
        'question_id': response_obj.question_id,
        'question_type': response_obj.question_type,
        'value': response_obj.value,
        'valid': response_obj.valid,
        'created': created
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_page_progress(request, attempt_id):
    """Update page progress for an attempt."""
    try:
        attempt = Attempt.objects.get(id=attempt_id, user=request.user)
    except Attempt.DoesNotExist:
        return Response(
            {'error': 'Attempt not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    page_id = request.data.get('page_id')
    reached = request.data.get('reached', True)
    data = request.data.get('data', {})

    if not page_id:
        return Response(
            {'error': 'page_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    from ..models import Page
    try:
        page = Page.objects.get(id=page_id)
    except Page.DoesNotExist:
        return Response(
            {'error': 'Page not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    progress, created = PageProgress.objects.update_or_create(
        attempt=attempt,
        page=page,
        defaults={
            'reached': reached,
            'data': data
        }
    )

    return Response({
        'page_id': str(page.id),
        'reached': progress.reached,
        'last_seen_at': progress.last_seen_at.isoformat(),
        'data': progress.data
    }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def has_completed_activity(request, activity_id):
    """Check if user has completed this activity at least once."""
    from ..models import Activity, ActivitySubmission

    try:
        activity = Activity.objects.get(id=activity_id)
    except Activity.DoesNotExist:
        return Response(
            {'error': 'Activity not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check if user has any completed attempts for this activity
    has_completed = Attempt.objects.filter(
        user=request.user,
        activity_version__activity=activity,
        status='completed'
    ).exists()

    return Response({
        'has_completed': has_completed
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_activity_submissions(request, activity_id):
    """Get all submissions for an activity by the current user."""
    from ..models import Activity, ActivitySubmission

    try:
        activity = Activity.objects.get(id=activity_id)
    except Activity.DoesNotExist:
        return Response(
            {'error': 'Activity not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get all completed attempts for this user and activity
    attempts = Attempt.objects.filter(
        user=request.user,
        activity_version__activity=activity,
        status='completed'
    ).select_related('activity_version').order_by('-completed_at')

    submissions = []
    for attempt in attempts:
        submissions.append({
            'id': str(attempt.id),
            'activity_version': {
                'id': str(attempt.activity_version.id),
                'version': attempt.activity_version.version,
                'title': attempt.activity_version.title,
                'description': attempt.activity_version.description,
                'meta': attempt.activity_version.meta,
                'is_published': attempt.activity_version.is_published,
                'created_at': attempt.activity_version.created_at.isoformat(),
            },
            'started_at': attempt.started_at.isoformat(),
            'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
            'time_taken': str(attempt.completed_at - attempt.started_at) if attempt.completed_at else None,
            'meta': attempt.meta
        })

    return Response(submissions)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_submission_details(request, submission_id):
    """Get details of a specific submission including responses."""
    try:
        attempt = Attempt.objects.get(id=submission_id, user=request.user)
    except Attempt.DoesNotExist:
        return Response(
            {'error': 'Submission not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get all responses for this attempt
    from ..models import Response as ActivityResponse
    responses = ActivityResponse.objects.filter(attempt=attempt).order_by('created_at')

    submission_data = {
        'id': str(attempt.id),
        'activity_version': {
            'id': str(attempt.activity_version.id),
            'version': attempt.activity_version.version,
            'title': attempt.activity_version.title,
            'description': attempt.activity_version.description,
            'meta': attempt.activity_version.meta,
            'is_published': attempt.activity_version.is_published,
            'created_at': attempt.activity_version.created_at.isoformat(),
        },
        'started_at': attempt.started_at.isoformat(),
        'completed_at': attempt.completed_at.isoformat() if attempt.completed_at else None,
        'time_taken': str(attempt.completed_at - attempt.started_at) if attempt.completed_at else None,
        'meta': attempt.meta,
        'responses': [
            {
                'id': str(response.id),
                'question_id': response.question_id,
                'question_type': response.question_type,
                'value': response.value,
                'valid': response.valid,
                'meta': response.meta,
                'created_at': response.created_at.isoformat()
            }
            for response in responses
        ]
    }

    return Response(submission_data)
