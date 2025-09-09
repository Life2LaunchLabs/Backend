import os
import json
import requests
import re
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from apps.courses.models import Course


def parse_ai_response(response):
    """Parse AI response from JSON format"""
    if not response or not isinstance(response, str):
        return {
            'emote': 'idle',
            'message': 'Sorry, I had trouble processing that response.',
            'quickInputs': [],
            'system': {'active_item': 1, 'completed_item': None}
        }

    try:
        # Try to parse as JSON first - handle multiline strings properly
        response_cleaned = response.strip()
        parsed_json = json.loads(response_cleaned)
        
        # Extract the required fields
        result = {
            'emote': parsed_json.get('emote', 'idle'),
            'message': parsed_json.get('message', 'Hello! How can I help you?'),
            'system': parsed_json.get('system', {'active_item': 1, 'completed_item': None})
        }
        
        # Handle the inputs field - convert to quickInputs format for frontend compatibility
        inputs = parsed_json.get('inputs', {})
        if isinstance(inputs, dict) and 'options' in inputs:
            result['quickInputs'] = inputs['options']
        else:
            result['quickInputs'] = []
            
        return result
        
    except json.JSONDecodeError:
        # Fallback for non-JSON responses
        return {
            'emote': 'confused',
            'message': 'I had trouble understanding that. Could you try rephrasing?',
            'quickInputs': ['Try again', 'Help'],
            'system': {'active_item': 1, 'completed_item': None}
        }
    except Exception as e:
        print(f'Error parsing AI response: {e}')
        return {
            'emote': 'confused',
            'message': 'I had trouble understanding that. Could you try rephrasing?',
            'quickInputs': ['Try again', 'Help'],
            'system': {'active_item': 1, 'completed_item': None}
        }


# save_section function removed - no longer needed with JSON parsing


def get_system_prompt(character, course_id=None):
    """Dynamically compose system prompt from character, instructions, and course agenda"""
    try:
        # Get the base directory (project root)
        base_dir = Path(__file__).parent.parent.parent
        prompts_dir = base_dir / 'prompts'
        
        # Load character description
        character_file = prompts_dir / 'characters' / f'{character}.md'
        if not character_file.exists():
            raise FileNotFoundError(f"Character file not found: {character_file}")
        character_desc = character_file.read_text(encoding='utf-8')
        
        # Load universal chat instructions
        instructions_file = prompts_dir / 'chat_instructions.md'
        if not instructions_file.exists():
            raise FileNotFoundError(f"Instructions file not found: {instructions_file}")
        instructions = instructions_file.read_text(encoding='utf-8')
        
        # Load course-specific agenda from database
        agenda = get_course_agenda(course_id)
        
        # Compose the full system prompt
        system_prompt = f"{character_desc}\n\n{instructions}"
        if agenda:
            system_prompt += f"\n\n{agenda}"
            
        return system_prompt
        
    except Exception as e:
        print(f"Error loading system prompt for {character}: {e}")
        # Fallback to basic prompt if files can't be loaded
        return f"You are {character}, a helpful AI assistant. Respond with emote, message, and quick inputs sections."


def get_course_agenda(course_id=None):
    """Get agenda content from course database or fallback to inner_world"""
    try:
        # If no course_id provided, use inner_world as default
        if not course_id:
            course_id = 'inner_world'
        
        course = Course.objects.get(id=course_id)
        return course.agenda if course.agenda else ""
        
    except Course.DoesNotExist:
        print(f"Course {course_id} not found, falling back to inner_world")
        try:
            # Fallback to inner_world course
            course = Course.objects.get(id='inner_world')
            return course.agenda if course.agenda else ""
        except Course.DoesNotExist:
            print("Inner world course not found, falling back to mock agenda file")
            # Final fallback to file system
            base_dir = Path(__file__).parent.parent.parent
            agenda_file = base_dir / 'prompts' / 'mock_agenda.md'
            if agenda_file.exists():
                return agenda_file.read_text(encoding='utf-8')
            return ""
    except Exception as e:
        print(f"Error loading course agenda: {e}")
        return ""


def get_agenda_items(course_id=None):
    """Extract agenda item titles from course agenda"""
    try:
        # Get agenda content from course database
        content = get_course_agenda(course_id)
        
        if not content:
            return []
            
        items = []
        
        # Parse lines that match "### N. Title" pattern
        lines = content.split('\n')
        for line in lines:
            match = re.match(r'^### (\d+)\. (.+)$', line)
            if match:
                number = int(match.group(1))
                title = match.group(2)
                items.append({'number': number, 'title': title})
        
        # Sort by number to ensure correct order
        items.sort(key=lambda x: x['number'])
        return [item['title'] for item in items]
        
    except Exception as e:
        print(f'Error parsing agenda items: {e}')
        return []


# CHARACTER_PROMPTS removed - now using dynamic file-based system prompts


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import get_authorization_header
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.responses.models import CourseSession, QuestionResponse, ConversationTurn
from apps.responses.utils import parse_agenda_items
from django.contrib.auth import get_user_model

User = get_user_model()

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(permission_classes([AllowAny]), name='dispatch')
class ChatView(View):
    def call_llm_api(self, messages, character, llm_config):
        """Call the appropriate LLM API based on configuration"""
        provider = llm_config.get('provider')
        model = llm_config.get('model')
        
        if not provider:
            raise ValueError("Provider is required in llm_config")
        if not model:
            raise ValueError("Model is required in llm_config")
        
        if provider == 'anthropic':
            return self.call_anthropic_api(messages, character, llm_config)
        elif provider == 'openai':
            return self.call_openai_api(messages, character, llm_config)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def call_anthropic_api(self, messages, character, llm_config):
        """Call Anthropic Claude API"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError('Anthropic API key not configured')

        # Prepare Anthropic API request
        anthropic_messages = [
            {'role': msg['role'], 'content': msg['content']} 
            for msg in messages 
            if msg['role'] in ['user', 'assistant']
        ]

        # Build request payload with required fields
        request_payload = {
            'model': llm_config['model'],
            'messages': anthropic_messages,
            'system': get_system_prompt(character, llm_config.get('course_id')),
        }

        # Pass through all config parameters except our internal ones
        internal_params = {'provider', 'model', 'course_id'}
        
        for key, value in llm_config.items():
            if key not in internal_params and value is not None:
                # Handle camelCase to snake_case mapping for common parameters
                if key == 'maxTokens':
                    request_payload['max_tokens'] = value
                else:
                    request_payload[key] = value

        # Set defaults only for essential parameters if not provided
        if 'max_tokens' not in request_payload:
            request_payload['max_tokens'] = 1000
        if 'temperature' not in request_payload:
            request_payload['temperature'] = 0.7

        return requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01'
            },
            json=request_payload
        )

    def call_openai_api(self, messages, character, llm_config):
        """Call OpenAI GPT API"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError('OpenAI API key not configured')

        # Prepare OpenAI API request - include system message in messages array
        system_prompt = get_system_prompt(character, llm_config.get('course_id')) + "\n\nIMPORTANT: Your response must be ONLY valid JSON. Do not include any text before or after the JSON object."
        openai_messages = [{'role': 'system', 'content': system_prompt}]
        openai_messages.extend([
            {'role': msg['role'], 'content': msg['content']} 
            for msg in messages 
            if msg['role'] in ['user', 'assistant']
        ])

        # Build request payload with required fields
        request_payload = {
            'model': llm_config['model'],
            'messages': openai_messages,
        }

        # Pass through all config parameters except our internal ones
        internal_params = {'provider', 'model', 'course_id'}
        
        # Handle GPT-5 specific parameter requirements
        is_gpt5 = 'gpt-5' in llm_config['model']
        
        for key, value in llm_config.items():
            if key not in internal_params and value is not None:
                # Handle camelCase to snake_case mapping for common parameters
                if key == 'maxTokens':
                    # GPT-5 uses max_completion_tokens instead of max_tokens
                    if is_gpt5:
                        request_payload['max_completion_tokens'] = value
                    else:
                        request_payload['max_tokens'] = value
                elif key == 'temperature' and is_gpt5:
                    # GPT-5 only supports temperature=1 (default), so skip custom values
                    continue
                else:
                    request_payload[key] = value

        # Set defaults only for essential parameters if not provided
        if is_gpt5:
            if 'max_completion_tokens' not in request_payload:
                request_payload['max_completion_tokens'] = 1000
            # Don't set temperature for GPT-5 - it only supports default (1)
        else:
            if 'max_tokens' not in request_payload:
                request_payload['max_tokens'] = 1000
            if 'temperature' not in request_payload:
                request_payload['temperature'] = 0.7

        # Use JSON mode only for models that support it
        # Note: GPT-5 and some other models may not support response_format parameter
        model = llm_config['model']
        if 'gpt-4-turbo' in model or 'gpt-4o' in model:
            request_payload['response_format'] = {"type": "json_object"}
        # Skip response_format for GPT-5 and other models that don't support it

        return requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            json=request_payload
        )

    def extract_ai_response(self, api_data, provider):
        """Extract AI response text from different provider response formats"""
        if provider == 'openai':
            return api_data.get('choices', [{}])[0].get('message', {}).get('content', '')
        else:  # anthropic
            return api_data.get('content', [{}])[0].get('text', '')

    def get_or_create_session(self, user, character, course_id):
        """Get or create an active session for the user/course/character combination"""
        if not user or not course_id:
            return None
            
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return None
        
        # Check for existing active session
        session = CourseSession.objects.filter(
            user=user,
            course=course,
            character_used=character,
            status='active'
        ).first()
        
        if not session:
            # Create new session
            session = CourseSession.objects.create(
                user=user,
                course=course,
                character_used=character,
                status='active'
            )
        
        return session
    
    def log_question_response(self, session, system_data, user_message):
        """Log question responses when AI marks them as complete"""
        if not session or not system_data:
            return
        
        completed_item = system_data.get('completed_item', {})
        if not completed_item:
            return
        
        # Process each completed item
        for question_number_str, answer in completed_item.items():
            try:
                question_number = int(question_number_str)
                
                # Get question details from agenda
                agenda_snapshot = session.agenda_snapshot
                items = agenda_snapshot.get('items', [])
                
                question_item = None
                for item in items:
                    if item.get('number') == question_number:
                        question_item = item
                        break
                
                if not question_item:
                    continue
                
                # Create or update question response
                QuestionResponse.objects.update_or_create(
                    session=session,
                    question_number=question_number,
                    defaults={
                        'question_id': question_item.get('question_id', f'question_{question_number}'),
                        'question_text': question_item.get('title', f'Question {question_number}'),
                        'raw_response': user_message,
                        'processed_response': str(answer) if answer else '',
                        'status': 'complete'
                    }
                )
            except (ValueError, KeyError):
                continue

    def authenticate_user(self, request):
        """Manually authenticate user using JWT if present"""
        try:
            jwt_authenticator = JWTAuthentication()
            # Try to authenticate using JWT
            auth_result = jwt_authenticator.authenticate(request)
            if auth_result:
                user, token = auth_result
                return user
        except Exception as e:
            print(f"JWT Authentication failed: {e}")
        
        return None

    def post(self, request):
        try:
            data = json.loads(request.body)
            character = data.get('character')
            message = data.get('message')
            messages = data.get('messages', [])
            llm_config = data.get('llm_config', {})
            session_id = data.get('session_id')  # Optional session ID from frontend

            if not character or not message:
                return JsonResponse({'error': 'Character and message are required'}, status=400)

            # Validate character exists (check if character file exists)
            base_dir = Path(__file__).parent.parent.parent
            character_file = base_dir / 'prompts' / 'characters' / f'{character}.md'
            if not character_file.exists():
                return JsonResponse({'error': f'Unknown character: {character}'}, status=400)

            # Try to authenticate user manually
            authenticated_user = self.authenticate_user(request)
            
            # Session management for authenticated users
            session = None
            course_id = llm_config.get('course_id')
            
            if authenticated_user and course_id:
                session = self.get_or_create_session(authenticated_user, character, course_id)
                if session:
                    # Log user message - calculate turn number from database
                    last_turn = session.conversation.order_by('-turn_number').first()
                    turn_number = (last_turn.turn_number + 1) if last_turn else 1
                    ConversationTurn.objects.create(
                        session=session,
                        turn_number=turn_number,
                        role='user',
                        content=message
                    )

            # Add current message to history
            messages.append({'role': 'user', 'content': message})

            # Call the appropriate API based on configuration
            try:
                response = self.call_llm_api(messages, character, llm_config)
            except ValueError as e:
                # Handle configuration errors (missing provider/model, unsupported provider)
                return JsonResponse({'error': str(e)}, status=400)

            if not response.ok:
                error_data = response.json() if response.content else {}
                provider = llm_config.get('provider', 'anthropic')
                if provider == 'openai':
                    error_msg = error_data.get('error', {}).get('message', response.text)
                else:
                    error_msg = error_data.get('error', {}).get('message', response.text)
                
                # Check if it's an "extra inputs" error that we should handle more gracefully
                if 'Extra inputs are not permitted' in str(error_msg) or 'not supported' in str(error_msg):
                    # Return a more helpful error message
                    return JsonResponse({
                        'error': f'{provider.title()} API rejected some parameters. Check your preset configuration.',
                        'details': error_msg
                    }, status=400)
                
                return JsonResponse({
                    'error': f'{provider.title()} API error: {error_msg}'
                }, status=response.status_code)

            api_data = response.json()
            ai_response = self.extract_ai_response(api_data, llm_config.get('provider', 'anthropic'))

            # Parse the AI response
            parsed = parse_ai_response(ai_response)

            # Add AI response to message history
            messages.append({'role': 'assistant', 'content': ai_response})

            # Handle response logging for authenticated users with sessions
            if session:
                # Log question responses if AI marked any as complete
                self.log_question_response(session, parsed['system'], message)
                
                # Log AI response turn - calculate turn number from database
                last_turn = session.conversation.order_by('-turn_number').first()
                turn_number = (last_turn.turn_number + 1) if last_turn else 1
                ConversationTurn.objects.create(
                    session=session,
                    turn_number=turn_number,
                    role='assistant',
                    content=ai_response,
                    emote=parsed['emote'],
                    quick_inputs=parsed['quickInputs'],
                    system_data=parsed['system']
                )

            # Get agenda items for progress tracking
            agenda_items = get_agenda_items(course_id)
            
            # Build completed items from session if available
            completed_items_map = {}
            if session:
                completed_responses = session.responses.filter(status='complete')
                for response in completed_responses:
                    completed_items_map[str(response.question_number)] = response.processed_response
            
            response_data = {
                'emote': parsed['emote'],
                'message': parsed['message'],
                'quickInputs': parsed['quickInputs'],
                'system': parsed['system'],
                'agendaItems': agenda_items,
                'messages': messages,
                'isLoading': False
            }
            
            # Include session info if available
            if session:
                response_data['session'] = {
                    'id': str(session.id),
                    'completion_percentage': session.completion_percentage,
                    'answered_questions': session.answered_questions,
                    'total_questions': session.total_questions,
                    'completed_items': completed_items_map
                }
            
            return JsonResponse(response_data)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f'Chat API error: {e}')
            return JsonResponse({
                'error': 'Internal server error',
                'emote': 'confused',
                'message': 'Sorry, I encountered an error. Please try again.',
                'quickInputs': ['Try again', 'Help'],
                'system': {'active_item': 1, 'completed_item': None},
                'isLoading': False
            }, status=500)