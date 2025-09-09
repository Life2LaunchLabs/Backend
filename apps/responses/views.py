import json
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.courses.models import Course
from .models import CourseSession, QuestionResponse, ConversationTurn
from .utils import parse_agenda_items, extract_question_details


class CourseSessionSerializer(serializers.ModelSerializer):
    """Serializer for CourseSession model"""
    course_title = serializers.CharField(source='course.title', read_only=True)
    
    class Meta:
        model = CourseSession
        fields = [
            'id', 'course_id', 'course_title', 'character_used', 'status',
            'completion_percentage', 'total_questions', 'answered_questions',
            'started_at', 'last_activity_at', 'completed_at'
        ]


class CourseSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing course sessions - user attempts at completing courses.
    """
    serializer_class = CourseSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Users can only see their own sessions
        return CourseSession.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def get_or_create_active(self, request):
        """
        Get or create an active session for a specific course and character.
        This ensures only one active session per user/course/character combination.
        """
        course_id = request.data.get('course_id')
        character = request.data.get('character', 'minu')
        
        if not course_id:
            return Response(
                {'error': 'course_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the course
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response(
                {'error': f'Course {course_id} not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check for existing active session for this user/course/character
        active_session = CourseSession.objects.filter(
            user=request.user,
            course=course,
            character_used=character,
            status='active'
        ).first()
        
        if active_session:
            # Return existing session with current progress
            session_data = self._serialize_session_with_progress(active_session)
            return Response({
                'session': session_data,
                'created': False
            })
        
        # Create new session
        session = CourseSession.objects.create(
            user=request.user,
            course=course,
            character_used=character,
            status='active'
        )
        
        session_data = self._serialize_session_with_progress(session)
        return Response({
            'session': session_data,
            'created': True
        }, status=status.HTTP_201_CREATED)
    
    def _serialize_session_with_progress(self, session):
        """Serialize session data with progress information"""
        completed_responses = session.responses.filter(status='complete')
        
        # Build completion map by question number
        completed_items = {}
        for response in completed_responses:
            completed_items[str(response.question_number)] = response.processed_response
        
        return {
            'id': str(session.id),
            'course_id': session.course.id,
            'course_title': session.course.title if hasattr(session, 'course') else session.course.id,
            'character_used': session.character_used,
            'status': session.status,
            'completion_percentage': session.completion_percentage,
            'total_questions': session.total_questions,
            'answered_questions': session.answered_questions,
            'started_at': session.started_at.isoformat(),
            'last_activity_at': session.last_activity_at.isoformat(),
            'completed_at': session.completed_at.isoformat() if session.completed_at else None,
            'agenda_items': session.agenda_snapshot.get('items', []),
            'completed_items': completed_items
        }
    
    def retrieve(self, request, pk=None):
        """Get a specific session with full details for results view"""
        session = self.get_object()
        session_data = self._serialize_session_with_progress(session)
        return Response(session_data)
    
    @action(detail=True, methods=['post'])
    def log_response(self, request, pk=None):
        """
        Log a question response for this session.
        Called when the AI marks a question as complete.
        """
        session = self.get_object()
        
        question_number = request.data.get('question_number')
        question_id = request.data.get('question_id')
        raw_response = request.data.get('raw_response', '')
        processed_response = request.data.get('processed_response', '')
        
        if not question_number or not question_id:
            return Response(
                {'error': 'question_number and question_id are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get question details from agenda
        question_details = extract_question_details(
            session.course.agenda, 
            question_number
        )
        
        # Create or update question response
        response_obj, created = QuestionResponse.objects.update_or_create(
            session=session,
            question_number=question_number,
            defaults={
                'question_id': question_id,
                'question_text': question_details.get('title', f'Question {question_number}'),
                'raw_response': raw_response,
                'processed_response': processed_response,
                'status': 'complete',
                'response_metadata': {
                    'question_details': question_details,
                    'completed_at_timestamp': timezone.now().isoformat()
                }
            }
        )
        
        # Session progress is automatically updated via the model's save method
        
        return Response({
            'response_id': str(response_obj.id),
            'created': created,
            'session_progress': {
                'completion_percentage': session.completion_percentage,
                'answered_questions': session.answered_questions,
                'total_questions': session.total_questions
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def log_conversation_turn(self, request, pk=None):
        """
        Log a conversation turn (user message or AI response) for this session.
        """
        session = self.get_object()
        
        role = request.data.get('role')  # 'user' or 'assistant'
        content = request.data.get('content', '')
        turn_number = request.data.get('turn_number')
        
        # AI response metadata (only for assistant messages)
        emote = request.data.get('emote', '')
        quick_inputs = request.data.get('quick_inputs', [])
        system_data = request.data.get('system_data', {})
        question_context_number = request.data.get('question_context_number')
        
        if not role or not content:
            return Response(
                {'error': 'role and content are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find question context if provided
        question_context = None
        if question_context_number:
            question_context = session.responses.filter(
                question_number=question_context_number
            ).first()
        
        # Auto-increment turn number if not provided
        if turn_number is None:
            last_turn = session.conversation.order_by('-turn_number').first()
            turn_number = (last_turn.turn_number + 1) if last_turn else 1
        
        # Create conversation turn
        turn = ConversationTurn.objects.create(
            session=session,
            turn_number=turn_number,
            role=role,
            content=content,
            emote=emote,
            quick_inputs=quick_inputs,
            system_data=system_data,
            question_context=question_context
        )
        
        return Response({
            'turn_id': str(turn.id),
            'turn_number': turn.turn_number
        }, status=status.HTTP_201_CREATED)