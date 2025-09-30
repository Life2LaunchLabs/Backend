"""
API views for session-based activity system.
Supports the new /activities/active/{id}/{page} routing with:
- Session management (continue/restart)
- Page-based navigation
- Response submission
- Completion tracking
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response as DRFResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from .models import Activity, ActivityVersion
from .session_models import ActivitySession, ActivityCompletion
from .session_services import ActivitySessionService, SessionCleanupService
from .serializers import ActivitySerializer  # Use existing serializers


class ActivitySessionViewSet(ViewSet):
    """
    ViewSet for session-based activity management.
    Handles the complete flow from session creation to completion.
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get user's active sessions."""
        sessions = ActivitySession.objects.active_sessions().filter(user=request.user)

        session_data = []
        for session in sessions:
            session_data.append({
                'id': str(session.id),
                'activity': {
                    'id': str(session.activity.id),
                    'title': session.activity.title,
                    'slug': session.activity.slug,
                },
                'current_page': session.current_page,
                'total_pages': session.total_pages,
                'completion_percentage': session.completion_percentage,
                'time_remaining_hours': session.time_remaining.total_seconds() / 3600,
                'expires_at': session.expires_at,
                'started_from': session.started_from,
                'created_at': session.created_at,
            })

        return DRFResponse({
            'sessions': session_data,
            'count': len(session_data)
        })

    @action(detail=False, methods=['post'])
    def start_or_continue(self, request):
        """
        Start new session or get existing one for an activity.
        Handles continue/restart decision logic.

        POST /api/activities/sessions/start_or_continue/
        {
            "activity_id": "uuid",
            "started_from": "map|direct_link|shared",
            "force_restart": false
        }
        """
        activity_id = request.data.get('activity_id')
        started_from = request.data.get('started_from', 'map')
        force_restart = request.data.get('force_restart', False)

        if not activity_id:
            return DRFResponse(
                {'error': 'activity_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if force_restart:
                # User explicitly chose to restart
                session = ActivitySessionService.restart_activity(
                    user=request.user,
                    activity_id=activity_id,
                    started_from=started_from
                )
                context = {'action': 'restarted'}
            else:
                # Normal flow - get existing or create new
                session, created, context = ActivitySessionService.get_or_create_session(
                    user=request.user,
                    activity_id=activity_id,
                    started_from=started_from
                )

            # Prepare response data
            response_data = {
                'session': {
                    'id': str(session.id),
                    'activity_id': str(session.activity.id),
                    'current_page': session.current_page,
                    'total_pages': session.total_pages,
                    'completion_percentage': session.completion_percentage,
                    'time_remaining_hours': session.time_remaining.total_seconds() / 3600,
                    'expires_at': session.expires_at,
                },
                'context': context,
                'activity': {
                    'id': str(session.activity.id),
                    'title': session.activity.title,
                    'slug': session.activity.slug,
                    'description': session.activity.description,
                }
            }

            # If user needs to make continue/restart decision, return context
            if context.get('action') in ['continue', 'restart'] and not force_restart:
                response_data['requires_decision'] = True

            return DRFResponse(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return DRFResponse(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def continue_session(self, request, pk=None):
        """Continue an existing session."""
        try:
            session = get_object_or_404(
                ActivitySession.objects.active_sessions(),
                id=pk,
                user=request.user
            )

            # Extend session and update
            session = ActivitySessionService.continue_session(
                user=request.user,
                activity_id=str(session.activity.id)
            )

            return DRFResponse({
                'session': {
                    'id': str(session.id),
                    'current_page': session.current_page,
                    'time_remaining_hours': session.time_remaining.total_seconds() / 3600,
                    'expires_at': session.expires_at,
                },
                'action': 'continued'
            })

        except Exception as e:
            return DRFResponse(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def navigate(self, request, pk=None):
        """
        Navigate to a specific page in the session.

        POST /api/activities/sessions/{session_id}/navigate/
        {
            "page_index": 2
        }
        """
        session = get_object_or_404(
            ActivitySession.objects.active_sessions(),
            id=pk,
            user=request.user
        )

        page_index = request.data.get('page_index')
        if page_index is None:
            return DRFResponse(
                {'error': 'page_index is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            nav_result = ActivitySessionService.navigate_to_page(session, page_index)
            return DRFResponse(nav_result)

        except Exception as e:
            return DRFResponse(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def save_response(self, request, pk=None):
        """
        Save a response to the session.

        POST /api/activities/sessions/{session_id}/save_response/
        {
            "question_id": "q1",
            "value": "answer",
            "page_index": 1
        }
        """
        session = get_object_or_404(
            ActivitySession.objects.active_sessions(),
            id=pk,
            user=request.user
        )

        question_id = request.data.get('question_id')
        value = request.data.get('value')
        page_index = request.data.get('page_index')

        if not question_id:
            return DRFResponse(
                {'error': 'question_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            save_result = ActivitySessionService.save_response(
                session=session,
                question_id=question_id,
                value=value,
                page_index=page_index
            )
            return DRFResponse(save_result)

        except Exception as e:
            return DRFResponse(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a session and create permanent records."""
        session = get_object_or_404(
            ActivitySession.objects.active_sessions(),
            id=pk,
            user=request.user
        )

        try:
            completion = ActivitySessionService.complete_session(session)

            return DRFResponse({
                'completion': {
                    'id': str(completion.id),
                    'completed_at': completion.completed_at,
                    'completion_rate': completion.completion_rate,
                    'total_time_hours': completion.completion_time_hours,
                    'pages_visited': completion.pages_visited,
                    'total_responses': completion.total_responses,
                },
                'attempt': {
                    'id': str(completion.final_attempt.id),
                    'status': completion.final_attempt.status,
                },
                'message': 'Activity completed successfully!'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return DRFResponse(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ActivityPageView(APIView):
    """
    Get page content for session-based activities.
    Supports the /activities/active/{id}/{page} URL pattern.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, activity_id, page_index):
        """
        Get page content with session context.

        GET /api/activities/active/{activity_id}/{page_index}/
        """
        try:
            page_index = int(page_index)
        except (ValueError, TypeError):
            return DRFResponse(
                {'error': 'Invalid page index'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get or create session for this activity
        try:
            session, created, context = ActivitySessionService.get_or_create_session(
                user=request.user,
                activity_id=activity_id
            )
        except Exception as e:
            return DRFResponse(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Navigate to requested page
        try:
            nav_result = ActivitySessionService.navigate_to_page(session, page_index)
        except Exception as e:
            return DRFResponse(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get page content (reuse existing logic from activities views)
        try:
            activity = session.activity
            latest_version = session.activity_version

            # Get page data
            page = latest_version.pages.get(index=page_index)
            blocks = page.blocks.all().order_by('index')

            # Get responses for this page from session
            page_responses = {
                qid: value for qid, value in session.responses_data.items()
            }

            response_data = {
                'session': {
                    'id': str(session.id),
                    'current_page': session.current_page,
                    'total_pages': session.total_pages,
                    'completion_percentage': session.completion_percentage,
                    'time_remaining_hours': session.time_remaining.total_seconds() / 3600,
                },
                'activity': {
                    'id': str(activity.id),
                    'title': activity.title,
                    'slug': activity.slug,
                    'description': activity.description,
                },
                'activity_version': {
                    'id': str(latest_version.id),
                    'version': latest_version.version,
                    'title': latest_version.title,
                    'meta': latest_version.meta,
                },
                'page': {
                    'id': str(page.id),
                    'index': page.index,
                    'title': page.title,
                    'meta': page.meta,
                },
                'blocks': [
                    {
                        'id': str(block.id),
                        'type': block.block_type,
                        'config': block.config,
                        'index': block.index,
                    }
                    for block in blocks
                ],
                'responses': page_responses,
                'navigation': nav_result,
                'context': context if created else None,
            }

            return DRFResponse(response_data)

        except Exception as e:
            return DRFResponse(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )


class ActivityCompletionViewSet(ViewSet):
    """ViewSet for activity completion records."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get user's activity completions."""
        completions = ActivityCompletion.objects.filter(user=request.user).order_by('-completed_at')

        completion_data = []
        for completion in completions:
            completion_data.append({
                'id': str(completion.id),
                'activity': {
                    'id': str(completion.activity.id),
                    'title': completion.activity.title,
                    'slug': completion.activity.slug,
                },
                'completed_at': completion.completed_at,
                'completion_rate': completion.completion_rate,
                'total_time_hours': completion.completion_time_hours,
                'pages_visited': completion.pages_visited,
                'total_responses': completion.total_responses,
                'sessions_count': completion.sessions_count,
                'attempts_count': completion.attempts_count,
            })

        return DRFResponse({
            'completions': completion_data,
            'count': len(completion_data)
        })

    def retrieve(self, request, pk=None):
        """Get detailed completion information."""
        completion = get_object_or_404(
            ActivityCompletion.objects.filter(user=request.user),
            id=pk
        )

        return DRFResponse({
            'id': str(completion.id),
            'activity': {
                'id': str(completion.activity.id),
                'title': completion.activity.title,
                'slug': completion.activity.slug,
            },
            'completed_at': completion.completed_at,
            'first_started_at': completion.first_started_at,
            'completion_rate': completion.completion_rate,
            'total_time_hours': completion.completion_time_hours,
            'active_time_hours': completion.active_time_seconds / 3600 if completion.active_time_seconds else None,
            'pages_visited': completion.pages_visited,
            'total_responses': completion.total_responses,
            'valid_responses': completion.valid_responses,
            'accuracy_rate': completion.accuracy_rate,
            'sessions_count': completion.sessions_count,
            'attempts_count': completion.attempts_count,
            'insights': completion.insights,
            'meta': completion.meta,
        })


class SessionAnalyticsView(APIView):
    """Analytics endpoint for session system."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get session analytics for admin/debugging."""
        if not request.user.is_staff:
            return DRFResponse(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        analytics = SessionCleanupService.get_session_analytics()
        return DRFResponse(analytics)

    def post(self, request):
        """Trigger session cleanup (admin only)."""
        if not request.user.is_staff:
            return DRFResponse(
                {'error': 'Admin access required'},
                status=status.HTTP_403_FORBIDDEN
            )

        cleanup_result = SessionCleanupService.cleanup_expired_sessions()
        return DRFResponse(cleanup_result)