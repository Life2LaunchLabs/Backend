"""
Session management services for the new activity system.
Handles session lifecycle, completion tracking, and continue/restart logic.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from typing import Dict, List, Optional, Tuple

from .models import Activity, ActivityVersion, Attempt, Response, PageProgress
from .session_models import ActivitySession, ActivityCompletion, SessionAttempt

logger = logging.getLogger(__name__)


class ActivitySessionService:
    """
    Core service for managing activity sessions and the continue/restart flow.
    """

    @staticmethod
    def get_or_create_session(user, activity_id: str, started_from: str = 'map') -> Tuple[ActivitySession, bool, dict]:
        """
        Get existing session or create new one for user + activity.
        Returns (session, created, context) where context has continue/restart info.

        Returns:
            session: The ActivitySession instance
            created: True if new session was created
            context: Dict with 'action', 'previous_completion', 'time_remaining', etc.
        """
        try:
            activity = Activity.objects.get(id=activity_id, status='published')
        except Activity.DoesNotExist:
            raise ValidationError(f"Published activity {activity_id} not found")

        # Check for existing completion
        previous_completion = ActivityCompletion.objects.filter(
            user=user, activity=activity
        ).first()

        # Check for existing active session
        existing_session = ActivitySession.objects.active_sessions().filter(
            user=user, activity=activity
        ).first()

        context = {
            'action': None,
            'previous_completion': previous_completion,
            'time_remaining': None,
            'can_continue': False,
            'can_restart': False,
        }

        if existing_session:
            # User has an active session - they can continue
            context.update({
                'action': 'continue',
                'time_remaining': existing_session.time_remaining,
                'can_continue': True,
                'can_restart': True,
                'current_page': existing_session.current_page,
                'completion_percentage': existing_session.completion_percentage,
            })
            return existing_session, False, context

        elif previous_completion:
            # User completed before - they can restart
            context.update({
                'action': 'restart',
                'can_restart': True,
                'previous_score': previous_completion.completion_rate,
                'completed_at': previous_completion.completed_at,
            })

        # Create new session
        session, created = ActivitySession.objects.get_or_create_session(
            user=user,
            activity=activity,
            started_from=started_from,
        )

        if created:
            # Set total pages for progress tracking
            latest_version = activity.versions.filter(is_published=True).order_by('-version').first()
            if latest_version:
                total_pages = latest_version.pages.count()
                session.total_pages = total_pages
                session.save(update_fields=['total_pages'])

            context['action'] = 'start'

        return session, created, context

    @staticmethod
    def continue_session(user, activity_id: str) -> ActivitySession:
        """Continue an existing session."""
        session = ActivitySession.objects.active_sessions().filter(
            user=user, activity_id=activity_id
        ).first()

        if not session:
            raise ValidationError("No active session found to continue")

        if session.is_expired:
            session.is_active = False
            session.save()
            raise ValidationError("Session has expired")

        # Extend session on continue
        session.extend_session()
        logger.info(f"User {user.username} continued session {session.id}")
        return session

    @staticmethod
    def restart_activity(user, activity_id: str, started_from: str = 'restart') -> ActivitySession:
        """Restart activity by deactivating old session and creating new one."""
        activity = Activity.objects.get(id=activity_id)

        # Deactivate any existing sessions
        existing_sessions = ActivitySession.objects.filter(
            user=user, activity=activity, is_active=True
        )
        existing_sessions.update(is_active=False)

        # Create new session
        session, created = ActivitySession.objects.get_or_create_session(
            user=user,
            activity=activity,
            started_from=started_from,
        )

        logger.info(f"User {user.username} restarted activity {activity_id}")
        return session

    @staticmethod
    def navigate_to_page(session: ActivitySession, page_index: int) -> dict:
        """
        Navigate to a specific page in the session.
        Returns page data and validation info.
        """
        if page_index < 0:
            raise ValidationError("Page index cannot be negative")

        if session.total_pages and page_index >= session.total_pages:
            raise ValidationError(f"Page {page_index} exceeds total pages {session.total_pages}")

        # Update session navigation
        session.current_page = page_index
        session.mark_page_visited(page_index)

        # Check if this page can be completed (all required responses present)
        # This would need page structure analysis
        can_complete_page = ActivitySessionService._can_complete_page(session, page_index)

        if can_complete_page:
            session.mark_page_completed(page_index)

        return {
            'session_id': session.id,
            'current_page': page_index,
            'total_pages': session.total_pages,
            'can_navigate_forward': page_index < (session.total_pages - 1) if session.total_pages else True,
            'can_navigate_backward': page_index > 0,
            'completion_percentage': session.completion_percentage,
            'responses_on_page': ActivitySessionService._get_page_responses(session, page_index),
        }

    @staticmethod
    def save_response(session: ActivitySession, question_id: str, value, page_index: int = None) -> dict:
        """Save a response to the session's temporary storage."""
        if page_index is None:
            page_index = session.current_page

        # Update session response
        session.update_response(question_id, value)

        # Check if page is now complete
        can_complete_page = ActivitySessionService._can_complete_page(session, page_index)
        if can_complete_page:
            session.mark_page_completed(page_index)

        return {
            'saved': True,
            'question_id': question_id,
            'page_complete': can_complete_page,
            'session_completion': session.completion_percentage,
        }

    @staticmethod
    def complete_session(session: ActivitySession) -> ActivityCompletion:
        """
        Complete a session by creating permanent records.
        This creates an Attempt and ActivityCompletion.
        """
        with transaction.atomic():
            # Create final attempt with all responses
            attempt = SessionAttempt.create_from_session(session)
            attempt.status = 'completed'
            attempt.completed_at = timezone.now()
            attempt.save()

            # Transfer responses from session to permanent storage
            page_responses = ActivitySessionService._transfer_session_responses(session, attempt)

            # Calculate completion metrics
            metrics = ActivitySessionService._calculate_completion_metrics(session, attempt)

            # Check for existing completion (in case of retaking)
            completion, created = ActivityCompletion.objects.update_or_create(
                user=session.user,
                activity=session.activity,
                defaults={
                    'activity_version': session.activity_version,
                    'completed_at': timezone.now(),
                    'first_started_at': session.created_at,
                    'total_time_seconds': metrics['total_time_seconds'],
                    'pages_visited': len(session.pages_visited),
                    'total_responses': metrics['total_responses'],
                    'valid_responses': metrics['valid_responses'],
                    'completion_rate': metrics['completion_rate'],
                    'sessions_count': metrics['sessions_count'],
                    'attempts_count': metrics['attempts_count'],
                    'final_attempt': attempt,
                    'final_session': session,
                    'meta': {
                        'page_responses': page_responses,
                        'session_history': metrics['session_history'],
                    }
                }
            )

            # Deactivate session
            session.is_active = False
            session.save()

            logger.info(f"Completed session {session.id} for user {session.user.username}")
            return completion

    @staticmethod
    def _can_complete_page(session: ActivitySession, page_index: int) -> bool:
        """Check if a page has all required responses to be considered complete."""
        # This would analyze the page structure and check required questions
        # For now, simplified logic
        page_responses = ActivitySessionService._get_page_responses(session, page_index)
        return len(page_responses) > 0  # Simple: any response = complete

    @staticmethod
    def _get_page_responses(session: ActivitySession, page_index: int) -> dict:
        """Get all responses for a specific page from session storage."""
        # This would need page structure to identify which questions belong to which page
        # For now, return all responses (simplified)
        return {k: v for k, v in session.responses_data.items()}

    @staticmethod
    def _transfer_session_responses(session: ActivitySession, attempt: Attempt) -> dict:
        """Transfer responses from session storage to permanent Response records."""
        page_responses = {}

        # Get activity structure to map responses to pages
        activity_version = session.activity_version

        for page in activity_version.pages.all():
            page_response_count = 0
            for block in page.blocks.filter(block_type='question'):
                question_id = block.config.get('question_id')
                if question_id and question_id in session.responses_data:
                    # Create permanent Response record
                    Response.objects.create(
                        attempt=attempt,
                        question_id=question_id,
                        question_type=block.config.get('question_type', 'unknown'),
                        page=page,
                        value=session.responses_data[question_id],
                        valid=True,  # Assume valid for now
                        meta={'transferred_from_session': str(session.id)}
                    )
                    page_response_count += 1

            if page_response_count > 0:
                page_responses[page.index] = page_response_count

        return page_responses

    @staticmethod
    def _calculate_completion_metrics(session: ActivitySession, attempt: Attempt) -> dict:
        """Calculate completion metrics for ActivityCompletion."""
        total_time = (timezone.now() - session.created_at).total_seconds()
        total_responses = len(session.responses_data)

        # Count previous sessions/attempts for this user + activity
        previous_sessions = ActivitySession.objects.filter(
            user=session.user,
            activity=session.activity,
            created_at__lt=session.created_at
        ).count()

        previous_attempts = Attempt.objects.filter(
            user=session.user,
            activity_version__activity=session.activity,
            created_at__lt=attempt.created_at
        ).count()

        return {
            'total_time_seconds': int(total_time),
            'total_responses': total_responses,
            'valid_responses': total_responses,  # Simplified
            'completion_rate': session.completion_percentage,
            'sessions_count': previous_sessions + 1,
            'attempts_count': previous_attempts + 1,
            'session_history': {
                'pages_visited': session.pages_visited,
                'pages_completed': session.pages_completed,
                'final_page': session.current_page,
            }
        }


class SessionCleanupService:
    """Service for cleaning up expired sessions and managing storage."""

    @staticmethod
    def cleanup_expired_sessions() -> dict:
        """Clean up expired sessions and return statistics."""
        expired_count = ActivitySession.objects.cleanup_expired()

        # Optionally delete very old inactive sessions to manage storage
        very_old_cutoff = timezone.now() - timedelta(days=30)
        old_deleted = ActivitySession.objects.filter(
            is_active=False,
            updated_at__lt=very_old_cutoff
        ).delete()[0]

        return {
            'expired_sessions_marked_inactive': expired_count,
            'old_sessions_deleted': old_deleted,
            'cleanup_timestamp': timezone.now(),
        }

    @staticmethod
    def get_session_analytics() -> dict:
        """Get analytics about session usage."""
        now = timezone.now()

        active_sessions = ActivitySession.objects.active_sessions()
        total_completions = ActivityCompletion.objects.count()

        return {
            'active_sessions_count': active_sessions.count(),
            'total_completions': total_completions,
            'completion_rate': ActivitySessionService._calculate_global_completion_rate(),
            'average_session_duration': ActivitySessionService._calculate_average_session_duration(),
        }