"""
WebSocket consumers for streaming chat responses
Handles real-time message delivery and streaming LLM responses
"""
import json
import asyncio
from typing import Dict, Any, Optional
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import DenyConnection
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .conversation_service import conversation_service
from .services import ChatSessionService


class ChatStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for streaming chat responses
    Handles authentication, session management, and real-time message streaming
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Extract session ID and token from URL
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        self.user = None
        self.session_config = None
        
        # Authenticate user via JWT token from query params
        token = self.scope.get('query_string', b'').decode('utf-8')
        if token.startswith('token='):
            token = token[6:]  # Remove 'token=' prefix
            
        if not await self.authenticate_user(token):
            await self.close(code=4001)  # Authentication failed
            return
            
        # Validate session access
        if not await self.validate_session_access():
            await self.close(code=4003)  # Forbidden
            return
            
        # Join session group for potential multi-client support
        self.session_group_name = f'chat_session_{self.session_id}'
        await self.channel_layer.group_add(
            self.session_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection success message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': self.session_id,
            'user_id': self.user.id,
            'timestamp': asyncio.get_event_loop().time()
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'session_group_name'):
            await self.channel_layer.group_discard(
                self.session_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'send_message':
                await self.handle_send_message(data)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            else:
                await self.send_error('Unknown message type', 'INVALID_MESSAGE_TYPE')
                
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format', 'JSON_DECODE_ERROR')
        except Exception as e:
            await self.send_error(f'Message processing error: {str(e)}', 'PROCESSING_ERROR')
    
    async def handle_send_message(self, data: Dict[str, Any]):
        """Handle message sending with staged response pipeline (emote → stream → quick responses)"""
        message = data.get('message', '').strip()
        if not message:
            await self.send_error('Message cannot be empty', 'EMPTY_MESSAGE')
            return

        # Extract control feature flags from the message
        request_emote = data.get('request_emote', False)
        request_quick_responses = data.get('request_quick_responses', False)
            
        # Send message received acknowledgment
        await self.send(text_data=json.dumps({
            'type': 'message_received',
            'message': message,
            'timestamp': asyncio.get_event_loop().time()
        }))
        
        # Send typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'status': 'typing',
            'timestamp': asyncio.get_event_loop().time()
        }))
        
        try:
            # Process message through conversation service with control features
            response_data, errors = await conversation_service.send_message(
                session_id=self.session_id,
                user_message=message,
                user_id=self.user.id,
                request_emote=request_emote,
                request_quick_responses=request_quick_responses
            )

            if errors:
                await self.send_error('; '.join(errors), 'CONVERSATION_ERROR')
                return

            # Implement staged response pipeline
            await self._send_staged_response(response_data, request_emote, request_quick_responses)
            
        except Exception as e:
            await self.send_error(f'Failed to process message: {str(e)}', 'MESSAGE_PROCESSING_ERROR')
        
        finally:
            # Clear typing indicator
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator', 
                'status': 'idle',
                'timestamp': asyncio.get_event_loop().time()
            }))
    
    async def _send_staged_response(
        self,
        response_data: Dict[str, Any],
        request_emote: bool,
        request_quick_responses: bool
    ):
        """Send staged response: emote → stream → quick responses"""
        # Stage 1: Send emote first if requested
        control_data = response_data.get('control_data', {})
        print(f"🎭 WebSocket - control_data: {control_data}")
        if request_emote and control_data.get('emote'):
            emote_message = {
                'type': 'emote',
                'emote': control_data.get('emote'),
                'emote_glyph': control_data.get('emote_glyph'),
                'timestamp': asyncio.get_event_loop().time()
            }
            print(f"🎭 Sending emote message: {emote_message}")
            await self.send(text_data=json.dumps(emote_message))

            # Small delay to ensure emote is processed before streaming starts
            await asyncio.sleep(0.1)

        # Stage 2: Stream the main response (simulate streaming for now)
        assistant_message = response_data['assistant_message']
        await self.send(text_data=json.dumps({
            'type': 'stream_start',
            'session_id': response_data['session_id'],
            'timestamp': asyncio.get_event_loop().time()
        }))

        # Stream the content in chunks (simulated streaming for now)
        content = assistant_message['content']
        chunk_size = 20
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            await self.send(text_data=json.dumps({
                'type': 'stream_chunk',
                'chunk': chunk,
                'chunk_index': i // chunk_size,
                'timestamp': asyncio.get_event_loop().time()
            }))
            await asyncio.sleep(0.05)  # Small delay between chunks for streaming effect

        # Send stream complete
        await self.send(text_data=json.dumps({
            'type': 'stream_complete',
            'assistant_message': assistant_message,
            'user_message': response_data['user_message'],
            'session_id': response_data['session_id'],
            'usage_stats': response_data.get('usage_stats'),
            'processing_info': response_data.get('processing_info'),
            'timestamp': asyncio.get_event_loop().time()
        }))

        # Stage 3: Send quick responses last if requested
        if request_quick_responses and control_data.get('quick_replies'):
            await self.send(text_data=json.dumps({
                'type': 'quick_responses',
                'quick_replies': control_data.get('quick_replies', []),
                'timestamp': asyncio.get_event_loop().time()
            }))

    async def send_error(self, message: str, error_code: str):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'error_code': error_code,
            'timestamp': asyncio.get_event_loop().time()
        }))
    
    async def authenticate_user(self, token: str) -> bool:
        """Authenticate user using JWT token"""
        if not token:
            return False
            
        try:
            # Validate JWT token
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            
            # Get user from database
            from django.contrib.auth import get_user_model
            User = get_user_model()
            self.user = await User.objects.aget(id=user_id)
            
            return True
            
        except (TokenError, InvalidToken, User.DoesNotExist):
            return False
    
    async def validate_session_access(self) -> bool:
        """Validate user has access to the session"""
        if not self.session_id or not self.user:
            return False
            
        try:
            # Get session configuration
            from asgiref.sync import sync_to_async
            session_config = await sync_to_async(ChatSessionService.get_session_config)(self.session_id)
            
            if not session_config:
                return False
                
            # Check if user owns the session
            if session_config['user_id'] != self.user.id:
                return False
                
            self.session_config = session_config
            return True
            
        except Exception:
            return False


class ChatStreamConsumerWithChunking(ChatStreamConsumer):
    """
    Enhanced WebSocket consumer with streaming response chunking
    Simulates streaming by sending response in chunks for better UX
    """
    
    async def handle_send_message(self, data: Dict[str, Any]):
        """Handle message sending with chunked streaming response and staged control features"""
        message = data.get('message', '').strip()
        if not message:
            await self.send_error('Message cannot be empty', 'EMPTY_MESSAGE')
            return

        # Extract control feature flags from the message
        request_emote = data.get('request_emote', False)
        request_quick_responses = data.get('request_quick_responses', False)
            
        # Send message received acknowledgment
        await self.send(text_data=json.dumps({
            'type': 'message_received',
            'message': message,
            'timestamp': asyncio.get_event_loop().time()
        }))
        
        # Send typing indicator
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'status': 'typing',
            'timestamp': asyncio.get_event_loop().time()
        }))
        
        try:
            # Process message through conversation service with control features
            response_data, errors = await conversation_service.send_message(
                session_id=self.session_id,
                user_message=message,
                user_id=self.user.id,
                request_emote=request_emote,
                request_quick_responses=request_quick_responses
            )

            if errors:
                await self.send_error('; '.join(errors), 'CONVERSATION_ERROR')
                return

            # Send user message confirmation
            await self.send(text_data=json.dumps({
                'type': 'user_message_stored',
                'user_message': response_data['user_message'],
                'timestamp': asyncio.get_event_loop().time()
            }))

            # Implement enhanced staged response pipeline
            await self._send_enhanced_staged_response(response_data, request_emote, request_quick_responses)
            
        except Exception as e:
            await self.send_error(f'Failed to process message: {str(e)}', 'MESSAGE_PROCESSING_ERROR')
        
        finally:
            # Clear typing indicator
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'status': 'idle',
                'timestamp': asyncio.get_event_loop().time()
            }))

    async def _send_enhanced_staged_response(
        self,
        response_data: Dict[str, Any],
        request_emote: bool,
        request_quick_responses: bool
    ):
        """Send enhanced staged response with improved chunking: emote → stream → quick responses"""
        # Stage 1: Send emote first if requested
        control_data = response_data.get('control_data', {})
        print(f"🎭 WebSocket - control_data: {control_data}")
        if request_emote and control_data.get('emote'):
            emote_message = {
                'type': 'emote',
                'emote': control_data.get('emote'),
                'emote_glyph': control_data.get('emote_glyph'),
                'timestamp': asyncio.get_event_loop().time()
            }
            print(f"🎭 Sending emote message: {emote_message}")
            await self.send(text_data=json.dumps(emote_message))

            # Small delay to ensure emote is processed before streaming starts
            await asyncio.sleep(0.1)

        # Stage 2: Stream assistant response in chunks
        assistant_content = response_data['assistant_message']['content']
        chunk_size = 20  # Characters per chunk

        # Send streaming start
        await self.send(text_data=json.dumps({
            'type': 'stream_start',
            'message_id': response_data['assistant_message']['id'],
            'timestamp': asyncio.get_event_loop().time()
        }))

        # Send content in chunks
        for i in range(0, len(assistant_content), chunk_size):
            chunk = assistant_content[i:i + chunk_size]
            await self.send(text_data=json.dumps({
                'type': 'stream_chunk',
                'chunk': chunk,
                'chunk_index': i // chunk_size,
                'timestamp': asyncio.get_event_loop().time()
            }))

            # Small delay to simulate real streaming
            await asyncio.sleep(0.05)

        # Send streaming complete
        await self.send(text_data=json.dumps({
            'type': 'stream_complete',
            'assistant_message': response_data['assistant_message'],
            'session_id': response_data['session_id'],
            'usage_stats': response_data.get('usage_stats'),
            'processing_info': response_data.get('processing_info'),
            'timestamp': asyncio.get_event_loop().time()
        }))

        # Stage 3: Send quick responses last if requested
        if request_quick_responses and control_data.get('quick_replies'):
            await self.send(text_data=json.dumps({
                'type': 'quick_responses',
                'quick_replies': control_data.get('quick_replies', []),
                'timestamp': asyncio.get_event_loop().time()
            }))


class ChatAnalyticsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat analytics
    Provides live metrics and conversation insights
    """
    
    async def connect(self):
        """Handle WebSocket connection for analytics"""
        # Similar authentication as ChatStreamConsumer
        token = self.scope.get('query_string', b'').decode('utf-8')
        if token.startswith('token='):
            token = token[6:]
            
        if not await self.authenticate_user(token):
            await self.close(code=4001)
            return
            
        await self.accept()
        
        # Send initial analytics data
        await self.send_analytics_update()
    
    async def receive(self, text_data):
        """Handle analytics requests"""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'request_analytics':
                await self.send_analytics_update()
        except json.JSONDecodeError:
            pass
    
    async def send_analytics_update(self):
        """Send current analytics data"""
        try:
            from asgiref.sync import sync_to_async
            
            # Get user sessions
            sessions = await sync_to_async(ChatSessionService.get_user_sessions)(
                user_id=self.user.id,
                active_only=True
            )
            
            # Calculate basic analytics
            total_sessions = len(sessions)
            total_messages = sum(session.get('message_count', 0) for session in sessions)
            
            # Send analytics data
            await self.send(text_data=json.dumps({
                'type': 'analytics_update',
                'data': {
                    'total_sessions': total_sessions,
                    'total_messages': total_messages,
                    'active_sessions': total_sessions,
                    'recent_activity': True if total_messages > 0 else False
                },
                'timestamp': asyncio.get_event_loop().time()
            }))
            
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'analytics_error',
                'error': str(e),
                'timestamp': asyncio.get_event_loop().time()
            }))
    
    async def authenticate_user(self, token: str) -> bool:
        """Authenticate user using JWT token"""
        if not token:
            return False
            
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            self.user = await User.objects.aget(id=user_id)
            
            return True
            
        except Exception:
            return False