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


@api_view(['GET'])
@permission_classes([AllowAny])
def get_guest_attempt(request, attempt_id):
    """Get a guest attempt with all responses and activity details."""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"get_guest_attempt called with attempt_id: {attempt_id}")
    logger.info(f"Session key: {request.session.session_key}")
    logger.info(f"guest_attempts in session: {'guest_attempts' in request.session}")

    if 'guest_attempts' in request.session:
        logger.info(f"Available attempt IDs: {list(request.session['guest_attempts'].keys())}")

    if 'guest_attempts' not in request.session or attempt_id not in request.session['guest_attempts']:
        return Response(
            {'error': 'Attempt not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    attempt = request.session['guest_attempts'][attempt_id]

    # Get activity version details
    activity_version_id = attempt.get('activity_version_id')
    activity_data = None

    if activity_version_id:
        try:
            activity_version = ActivityVersion.objects.prefetch_related(
                'pages__blocks'
            ).select_related('activity').get(id=activity_version_id)

            # Get activity details
            serializer = ActivityDetailSerializer(activity_version.activity)
            activity_data = serializer.data
        except ActivityVersion.DoesNotExist:
            pass

    return Response({
        'id': attempt_id,
        'activity_version_id': attempt.get('activity_version_id'),
        'status': attempt.get('status'),
        'started_at': attempt.get('started_at'),
        'completed_at': attempt.get('completed_at'),
        'responses': attempt.get('responses', {}),
        'progress': attempt.get('progress', {}),
        'meta': attempt.get('meta', {}),
        'activity': activity_data
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_guest_attempt_results(request, attempt_id):
    """
    Get processed, display-ready results for a guest attempt.
    Returns formatted results with question text and answer text resolved.
    """
    import logging
    logger = logging.getLogger(__name__)

    if 'guest_attempts' not in request.session or attempt_id not in request.session['guest_attempts']:
        return Response(
            {'error': 'Attempt not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    attempt = request.session['guest_attempts'][attempt_id]
    responses = attempt.get('responses', {})
    activity_version_id = attempt.get('activity_version_id')

    if not activity_version_id:
        return Response(
            {'error': 'No activity version found for this attempt'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Load activity version with all related data
        activity_version = ActivityVersion.objects.prefetch_related(
            'pages__blocks'
        ).select_related('activity').get(id=activity_version_id)

        # Process results section by section (page by page)
        sections = []

        logger.info(f"Processing {activity_version.pages.count()} pages")
        logger.info(f"Total responses: {len(responses)}")
        logger.info(f"Response keys: {list(responses.keys())}")

        for page in activity_version.pages.all().order_by('index'):
            section_items = []
            logger.info(f"Processing page {page.id} - {page.title}, blocks count: {page.blocks.count()}")

            for block in page.blocks.all().order_by('index'):
                logger.info(f"Block type: {block.block_type}, has config: {bool(block.config)}")

                # Question types include: dropdown_input, text_input, multiple_choice, single_choice, a_or_b_input, etc.
                # Skip non-question blocks like 'text', 'media', 'divider'
                question_types = [
                    'dropdown_input', 'text_input', 'long_text_input',
                    'multiple_choice', 'single_choice', 'a_or_b_input'
                ]
                if block.block_type not in question_types or not block.config:
                    continue

                question_id = block.config.get('question_id')
                # Question title is in config.title
                question_title = block.config.get('title', 'Untitled Question')
                question_type = block.block_type  # The block_type IS the question type

                # Options/prompts can be in two places depending on question type:
                # - For dropdown: config.config.options (nested)
                # - For multiple_choice: config.options (direct)
                nested_config = block.config.get('config', {})
                options = block.config.get('options', []) or nested_config.get('options', [])
                prompts = nested_config.get('prompts', [])

                logger.info(f"Found question: {question_id} - {question_title}")
                logger.info(f"Block config keys: {list(block.config.keys())}")
                logger.info(f"Question type: {question_type}, Options count: {len(options)}")
                if len(options) > 0:
                    logger.info(f"First option structure: {options[0]}")

                # Find the response for this question
                response_key = None
                for key in responses.keys():
                    if responses[key].get('question_id') == question_id:
                        response_key = key
                        break

                if not response_key:
                    logger.info(f"No response found for question {question_id}")
                    continue

                response = responses[response_key]
                response_value = response.get('value')

                logger.info(f"Response for {question_id}: type={type(response_value)}, value={response_value}")

                # Format answer based on question type
                answer_data = {}

                if question_type in ['single_choice', 'dropdown_input']:
                    # Single selection - find the option text
                    selected_option = next(
                        (opt for opt in options if opt.get('id') == response_value),
                        None
                    )
                    answer_data = {
                        'type': 'single_choice',
                        'text': selected_option.get('title', response_value) if selected_option else response_value,
                        'value': response_value
                    }

                elif question_type == 'multiple_choice':
                    # Multiple selections - value is a dict like {option_id: true}
                    if isinstance(response_value, dict):
                        selected_ids = [k for k, v in response_value.items() if v is True]
                        logger.info(f"Multiple choice - selected IDs: {selected_ids}")

                        # Multiple choice options use 'value' and 'label' fields
                        selected_options = [
                            opt for opt in options
                            if opt.get('value') in selected_ids
                        ]
                        logger.info(f"Multiple choice - matched options: {len(selected_options)}")

                        answer_data = {
                            'type': 'multiple_choice',
                            'text': ', '.join([opt.get('label', '') for opt in selected_options]),
                            'values': selected_ids,
                            'items': [
                                {
                                    'id': opt.get('value'),
                                    'text': opt.get('label', ''),
                                    'icon_url': opt.get('icon_url')
                                }
                                for opt in selected_options
                            ]
                        }
                    else:
                        answer_data = {
                            'type': 'multiple_choice',
                            'text': str(response_value),
                            'values': []
                        }

                elif question_type == 'a_or_b_input':
                    # A or B comparison - value is a dict with prompt selections
                    if isinstance(response_value, dict):
                        # Find which prompts were selected (only True values)
                        selected_prompt_ids = [k for k, v in response_value.items() if v is True]
                        logger.info(f"Selected prompt IDs: {selected_prompt_ids}")
                        logger.info(f"Available prompts: {[p.get('id') for p in prompts]}")

                        selected_prompts = [
                            p for p in prompts
                            if p.get('id') in selected_prompt_ids
                        ]
                        logger.info(f"Matched prompts: {len(selected_prompts)}")

                        answer_data = {
                            'type': 'a_or_b',
                            'text': None,  # Will be formatted in frontend
                            'items': [
                                {
                                    'id': p.get('id'),
                                    'text': f"{p.get('title', '')} - {p.get('description', '')}",
                                    'title': p.get('title', ''),
                                    'description': p.get('description', '')
                                }
                                for p in selected_prompts
                            ]
                        }
                    else:
                        answer_data = {
                            'type': 'a_or_b',
                            'text': str(response_value)
                        }

                elif question_type in ['text_input', 'long_text_input']:
                    # Text input
                    answer_data = {
                        'type': 'text',
                        'text': str(response_value)
                    }

                else:
                    # Fallback for unknown types
                    answer_data = {
                        'type': 'unknown',
                        'text': str(response_value)
                    }

                section_items.append({
                    'question_id': question_id,
                    'question': question_title,
                    'answer': answer_data
                })

            # Only add sections that have items
            if section_items:
                sections.append({
                    'section_id': str(page.id),
                    'section_title': page.title or f'Section {page.index + 1}',
                    'items': section_items
                })

        return Response({
            'attempt_id': attempt_id,
            'activity_title': activity_version.activity.title,
            'activity_description': activity_version.activity.description,
            'completed_at': attempt.get('completed_at'),
            'started_at': attempt.get('started_at'),
            'sections': sections,
            'scores': {},  # Future: computed scores
            'insights': [],  # Future: AI-generated insights
            'recommendations': []  # Future: pathway recommendations
        })

    except ActivityVersion.DoesNotExist:
        return Response(
            {'error': 'Activity version not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error processing attempt results: {str(e)}")
        return Response(
            {'error': 'Failed to process results'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
