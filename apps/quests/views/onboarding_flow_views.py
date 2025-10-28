"""
Onboarding flow views for managing multi-activity onboarding sequences.
These endpoints manage flow state in session and coordinate multiple guest attempts.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

# Default onboarding flow configuration
DEFAULT_FLOW_CONFIG = {
    'flow_id': 'user-onboarding-v1',
    'steps': [
        {
            'id': 'welcome',
            'type': 'activity',
            'activitySlug': 'welcome',
            'title': 'Welcome to Launchpad'
        },
        {
            'id': 'pathways',
            'type': 'activity',
            'activitySlug': 'pathways-assessment',
            'title': 'Career Pathways Assessment'
        }
    ]
}


@api_view(['POST'])
@permission_classes([AllowAny])
def initialize_flow(request):
    """
    Initialize a new onboarding flow in the session.
    Creates the flow structure and returns the first step.
    """
    # Ensure session exists for anonymous users
    if not request.session.session_key:
        request.session.create()

    flow_id = request.data.get('flow_id', DEFAULT_FLOW_CONFIG['flow_id'])

    # For now, we only support the default flow
    # In the future, this could support multiple flow types
    if flow_id != DEFAULT_FLOW_CONFIG['flow_id']:
        return Response(
            {'error': f'Flow {flow_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Initialize flow state in session
    request.session['onboarding_flow'] = {
        'flow_id': flow_id,
        'current_step_index': 0,
        'completed_steps': [],
        'attempt_ids': {},
        'started_at': timezone.now().isoformat(),
        'metadata': request.data.get('metadata', {})
    }
    request.session.modified = True

    logger.info(f"Initialized flow {flow_id} in session {request.session.session_key}")

    return Response({
        'flow_id': flow_id,
        'current_step_index': 0,
        'current_step': DEFAULT_FLOW_CONFIG['steps'][0],
        'total_steps': len(DEFAULT_FLOW_CONFIG['steps']),
        'flow_config': DEFAULT_FLOW_CONFIG
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_flow_state(request):
    """
    Get the current state of the onboarding flow from session.
    Returns flow progress, current step, and completed steps.
    """
    if 'onboarding_flow' not in request.session:
        return Response(
            {'error': 'No active onboarding flow found'},
            status=status.HTTP_404_NOT_FOUND
        )

    flow_state = request.session['onboarding_flow']
    current_step_index = flow_state['current_step_index']

    # Ensure step index is valid
    if current_step_index >= len(DEFAULT_FLOW_CONFIG['steps']):
        return Response(
            {'error': 'Flow completed or invalid step index'},
            status=status.HTTP_400_BAD_REQUEST
        )

    return Response({
        'flow_id': flow_state['flow_id'],
        'current_step_index': current_step_index,
        'current_step': DEFAULT_FLOW_CONFIG['steps'][current_step_index],
        'completed_steps': flow_state['completed_steps'],
        'attempt_ids': flow_state['attempt_ids'],
        'total_steps': len(DEFAULT_FLOW_CONFIG['steps']),
        'started_at': flow_state['started_at'],
        'metadata': flow_state.get('metadata', {}),
        'flow_config': DEFAULT_FLOW_CONFIG
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def update_flow_progress(request):
    """
    Update the flow progress when a step is completed.
    Associates the completed attempt with the step and advances to next step.
    """
    if 'onboarding_flow' not in request.session:
        return Response(
            {'error': 'No active onboarding flow found'},
            status=status.HTTP_404_NOT_FOUND
        )

    step_id = request.data.get('step_id')
    attempt_id = request.data.get('attempt_id')
    action = request.data.get('action', 'complete')  # 'complete', 'next', 'previous'

    if not step_id:
        return Response(
            {'error': 'step_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    flow_state = request.session['onboarding_flow']
    current_step_index = flow_state['current_step_index']

    # Verify the step_id matches current step
    if current_step_index >= len(DEFAULT_FLOW_CONFIG['steps']):
        return Response(
            {'error': 'Already at end of flow'},
            status=status.HTTP_400_BAD_REQUEST
        )

    current_step = DEFAULT_FLOW_CONFIG['steps'][current_step_index]
    if current_step['id'] != step_id:
        return Response(
            {'error': f'Step mismatch. Expected {current_step["id"]}, got {step_id}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Handle different actions
    if action == 'complete':
        # Store attempt ID for this step
        if attempt_id:
            flow_state['attempt_ids'][step_id] = attempt_id

        # Mark step as completed
        if step_id not in flow_state['completed_steps']:
            flow_state['completed_steps'].append(step_id)

        # Advance to next step
        flow_state['current_step_index'] = current_step_index + 1

    elif action == 'next':
        # Move to next step without marking complete
        flow_state['current_step_index'] = min(
            current_step_index + 1,
            len(DEFAULT_FLOW_CONFIG['steps'])
        )

    elif action == 'previous':
        # Move to previous step
        flow_state['current_step_index'] = max(current_step_index - 1, 0)

    request.session.modified = True

    # Check if flow is complete
    is_complete = flow_state['current_step_index'] >= len(DEFAULT_FLOW_CONFIG['steps'])

    response_data = {
        'flow_id': flow_state['flow_id'],
        'current_step_index': flow_state['current_step_index'],
        'completed_steps': flow_state['completed_steps'],
        'attempt_ids': flow_state['attempt_ids'],
        'is_complete': is_complete
    }

    # Add next step info if not complete
    if not is_complete:
        response_data['current_step'] = DEFAULT_FLOW_CONFIG['steps'][flow_state['current_step_index']]

    logger.info(f"Updated flow progress: step={step_id}, action={action}, new_index={flow_state['current_step_index']}")

    return Response(response_data)


@api_view(['POST'])
@permission_classes([AllowAny])
def complete_flow(request):
    """
    Mark the entire onboarding flow as complete.
    This should be called before redirecting to registration.
    """
    if 'onboarding_flow' not in request.session:
        return Response(
            {'error': 'No active onboarding flow found'},
            status=status.HTTP_404_NOT_FOUND
        )

    flow_state = request.session['onboarding_flow']

    # Mark as completed
    flow_state['completed_at'] = timezone.now().isoformat()
    flow_state['status'] = 'completed'
    request.session.modified = True

    logger.info(f"Completed flow {flow_state['flow_id']} with {len(flow_state['attempt_ids'])} attempts")

    return Response({
        'flow_id': flow_state['flow_id'],
        'completed_steps': flow_state['completed_steps'],
        'attempt_ids': flow_state['attempt_ids'],
        'started_at': flow_state['started_at'],
        'completed_at': flow_state['completed_at']
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_flow_config(request):
    """
    Get the flow configuration (for frontend to understand flow structure).
    """
    return Response(DEFAULT_FLOW_CONFIG)
