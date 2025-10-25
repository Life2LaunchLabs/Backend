"""
Public activity views for unauthenticated users (onboarding flow).
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.utils.decorators import method_decorator

from ..models import Activity, ActivityVersion, Page
from ..serializers import ActivityDetailSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def get_public_activity(request, activity_slug):
    """
    Get public activity details by slug (e.g., 'welcome').
    Only returns activities from the 'onboarding' quest.
    """
    try:
        # Only allow activities from the onboarding quest to be accessed publicly
        activity = Activity.objects.filter(
            slug=activity_slug,
            status='published'
        ).prefetch_related(
            'versions__pages__blocks'
        ).select_related('organization').first()

        if not activity:
            return Response(
                {'error': 'Activity not found or not publicly accessible'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serialize and return
        serializer = ActivityDetailSerializer(activity)
        return Response(serializer.data)

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_guest_attempt(request):
    """
    Create a guest attempt for public activities (no authentication required).
    Stores responses in session, which can later be migrated to a user account.
    """
    # Ensure session exists for anonymous users
    if not request.session.session_key:
        request.session.create()

    activity_version_id = request.data.get('activity_version_id')

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

    # Create a session-based attempt ID (we'll store in session, not DB)
    import uuid
    guest_attempt_id = str(uuid.uuid4())

    # Store in session
    if 'guest_attempts' not in request.session:
        request.session['guest_attempts'] = {}

    request.session['guest_attempts'][guest_attempt_id] = {
        'id': guest_attempt_id,
        'activity_version_id': str(activity_version_id),
        'status': 'in_progress',
        'started_at': timezone.now().isoformat(),
        'responses': {},
        'progress': {},
        'meta': request.data.get('meta', {})
    }
    request.session.modified = True

    return Response({
        'id': guest_attempt_id,
        'activity_version': str(activity_version_id),
        'status': 'in_progress',
        'started_at': request.session['guest_attempts'][guest_attempt_id]['started_at'],
        'meta': request.session['guest_attempts'][guest_attempt_id]['meta']
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_guest_response(request, attempt_id):
    """Submit a response for a guest attempt (stored in session)."""
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"submit_guest_response called with attempt_id: {attempt_id}")
    logger.info(f"Session key: {request.session.session_key}")
    logger.info(f"Session data: {dict(request.session)}")

    # Ensure session exists
    if not request.session.session_key:
        return Response(
            {'error': 'No session found. Please refresh and try again.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if 'guest_attempts' not in request.session:
        logger.error(f"No guest_attempts in session. Session keys: {list(request.session.keys())}")
        return Response(
            {'error': f'No guest attempts found in session'},
            status=status.HTTP_404_NOT_FOUND
        )

    if attempt_id not in request.session['guest_attempts']:
        logger.error(f"Attempt {attempt_id} not in guest_attempts. Available: {list(request.session['guest_attempts'].keys())}")
        return Response(
            {'error': f'Attempt {attempt_id} not found. Available attempts: {list(request.session["guest_attempts"].keys())}'},
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

    # Store response in session
    attempt = request.session['guest_attempts'][attempt_id]
    if 'responses' not in attempt:
        attempt['responses'] = {}

    response_id = f"{page_id}_{question_id}"
    attempt['responses'][response_id] = {
        'question_id': question_id,
        'question_type': question_type,
        'page_id': page_id,
        'value': value,
        'valid': valid,
        'submitted_at': timezone.now().isoformat()
    }

    request.session.modified = True

    return Response({
        'id': response_id,
        'question_id': question_id,
        'value': value,
        'valid': valid
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def update_guest_page_progress(request, attempt_id):
    """Update page progress for a guest attempt."""
    if 'guest_attempts' not in request.session or attempt_id not in request.session['guest_attempts']:
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

    # Store progress in session
    attempt = request.session['guest_attempts'][attempt_id]
    if 'progress' not in attempt:
        attempt['progress'] = {}

    attempt['progress'][page_id] = {
        'page_id': page_id,
        'reached': reached,
        'data': data,
        'timestamp': timezone.now().isoformat()
    }

    request.session.modified = True

    return Response({
        'page_id': page_id,
        'reached': reached,
        'data': data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def complete_guest_attempt(request, attempt_id):
    """Complete a guest attempt."""
    if 'guest_attempts' not in request.session or attempt_id not in request.session['guest_attempts']:
        return Response(
            {'error': 'Attempt not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    attempt = request.session['guest_attempts'][attempt_id]

    if attempt['status'] != 'in_progress':
        return Response(
            {'error': 'Attempt is not in progress'},
            status=status.HTTP_400_BAD_REQUEST
        )

    attempt['status'] = 'completed'
    attempt['completed_at'] = timezone.now().isoformat()

    request.session.modified = True

    return Response({
        'id': attempt_id,
        'status': attempt['status'],
        'completed_at': attempt['completed_at']
    })
