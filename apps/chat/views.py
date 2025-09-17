"""
Chat API views for Phase 2 implementation
Handles real LLM conversations and session management
"""
import asyncio
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse

from .services import ChatSessionService, ChatMessageService
from .providers import ProviderConfig, ContextConfig
from .presets import PresetManager
from .conversation_service import conversation_service, ConversationUtils
from .analytics import conversation_analytics


class ChatView(APIView):
    """
    Main chat endpoint for sending messages to LLMs
    Phase 2 implementation with real LLM integration
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Send a message to the LLM and get a response"""
        try:
            data = request.data
            
            # Extract required fields
            message = data.get('message', '').strip()
            session_id = data.get('session_id')

            # Extract optional control feature flags
            request_emote = data.get('request_emote', False)
            request_quick_responses = data.get('request_quick_responses', False)

            if not message:
                return Response({
                    'error': 'Message is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not session_id:
                return Response({
                    'error': 'Session ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process message with conversation service (async)
            response_data, errors = asyncio.run(conversation_service.send_message(
                session_id=session_id,
                user_message=message,
                user_id=request.user.id,
                request_emote=request_emote,
                request_quick_responses=request_quick_responses
            ))
            
            if errors:
                return Response({
                    'errors': errors
                }, status=status.HTTP_400_BAD_REQUEST if 'Access denied' in str(errors) else status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Format response for frontend
            formatted_response = {
                'user_message': ConversationUtils.format_message_for_display(response_data['user_message']),
                'assistant_message': ConversationUtils.format_message_for_display(response_data['assistant_message']),
                'session_id': response_data['session_id'],
                'usage_stats': ConversationUtils.extract_usage_stats(response_data)
            }
            
            return Response(formatted_response, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Chat processing failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SessionCreateView(APIView):
    """Create new chat sessions with configuration"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create a new chat session using a preset"""
        print("DEBUG: SessionCreateView.post() called")
        try:
            data = request.data
            print(f"DEBUG: Session create request data: {data}")

            # Extract configuration
            preset_key = data.get('preset_key')
            if not preset_key:
                # Use default preset if none specified
                default_preset = PresetManager.get_default_preset()
                preset_key = default_preset.key
                print(f"DEBUG: Using default preset: {preset_key}")

            title = data.get('title', 'New Chat')
            ttl_hours = data.get('ttl_hours', 24)
            
            # Create session
            session_id, errors = ChatSessionService.create_session(
                user_id=request.user.id,
                preset_key=preset_key,
                title=title,
                ttl_hours=ttl_hours
            )
            
            if errors:
                print(f"DEBUG: Session creation errors: {errors}")
                return Response({
                    'errors': errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get full session data
            session_data = ChatSessionService.get_session_config(session_id)
            
            return Response({
                'session_id': session_id,
                'session': session_data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Failed to create session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SessionListView(APIView):
    """List user's chat sessions"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all sessions for the current user"""
        try:
            active_only = request.GET.get('active_only', 'true').lower() == 'true'
            sessions = ChatSessionService.get_user_sessions(
                user_id=request.user.id,
                active_only=active_only
            )
            
            return Response({
                'sessions': sessions,
                'total_count': len(sessions),
                'has_more': False
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to fetch sessions: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SessionDetailView(APIView):
    """Get, update, or delete a specific session"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        """Get session configuration"""
        session_data = ChatSessionService.get_session_config(session_id)
        
        if not session_data:
            return Response({
                'error': 'Session not found or expired'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify ownership
        if session_data['user_id'] != request.user.id:
            return Response({
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        return Response(session_data, status=status.HTTP_200_OK)
    
    def patch(self, request, session_id):
        """Update session configuration"""
        try:
            # Verify session exists and user owns it
            session_data = ChatSessionService.get_session_config(session_id)
            if not session_data or session_data['user_id'] != request.user.id:
                return Response({
                    'error': 'Session not found or access denied'
                }, status=status.HTTP_404_NOT_FOUND)
            
            data = request.data
            success, errors = ChatSessionService.update_session_config(
                session_id=session_id,
                preset_key=data.get('preset_key'),
                title=data.get('title'),
                custom_system_prompt=data.get('custom_system_prompt'),
                custom_control_instructions=data.get('custom_control_instructions'),
                quick_input_generation_instructions=data.get('quick_input_generation_instructions'),
                context_id=data.get('context_id'),
                quick_input_min_items=data.get('quick_input_min_items'),
                quick_input_max_items=data.get('quick_input_max_items')
            )
            
            if not success:
                return Response({
                    'errors': errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Return updated session data
            updated_session = ChatSessionService.get_session_config(session_id)
            return Response(updated_session, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to update session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, session_id):
        """Deactivate a session"""
        try:
            # Verify session exists and user owns it
            session_data = ChatSessionService.get_session_config(session_id)
            if not session_data or session_data['user_id'] != request.user.id:
                return Response({
                    'error': 'Session not found or access denied'
                }, status=status.HTTP_404_NOT_FOUND)
            
            success = ChatSessionService.deactivate_session(session_id)
            if success:
                return Response({
                    'message': 'Session deactivated successfully'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Failed to deactivate session'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response({
                'error': f'Failed to deactivate session: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MessageHistoryView(APIView):
    """Get message history for a session"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        """Get paginated message history"""
        try:
            # Verify session access
            session_data = ChatSessionService.get_session_config(session_id)
            if not session_data or session_data['user_id'] != request.user.id:
                return Response({
                    'error': 'Session not found or access denied'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get pagination parameters
            limit = request.GET.get('limit')
            offset = int(request.GET.get('offset', 0))
            
            if limit:
                limit = int(limit)
            
            # Get message history
            history_data = ChatMessageService.get_message_history(
                session_id=session_id,
                limit=limit,
                offset=offset
            )
            
            if history_data is None:
                return Response({
                    'error': 'Session not found or expired'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response(history_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'error': 'Invalid pagination parameters'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Failed to fetch message history: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PresetInfoView(APIView):
    """Get information about available configuration presets"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all available configuration presets"""
        try:
            presets = PresetManager.to_dict_list()
            categories = PresetManager.get_categories()
            default_preset = PresetManager.get_default_preset()
            
            return Response({
                'presets': presets,
                'categories': categories,
                'default_preset_key': default_preset.key
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to fetch preset info: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PresetValidationView(APIView):
    """Validate preset keys before session creation"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Validate a preset key and check provider availability"""
        try:
            data = request.data
            preset_key = data.get('preset_key')
            
            if not preset_key:
                return Response({
                    'valid': False,
                    'errors': ['Missing preset_key'],
                    'warnings': []
                }, status=status.HTTP_200_OK)
            
            # Check if preset exists
            preset = PresetManager.get_preset(preset_key)
            if not preset:
                return Response({
                    'valid': False,
                    'errors': [f'Unknown preset key: {preset_key}'],
                    'warnings': []
                }, status=status.HTTP_200_OK)
            
            # Validate the preset's configuration
            from .providers import SessionConfigValidator
            validation_result = SessionConfigValidator.validate_session_config({
                'model_config': preset.model_config,
                'context_config': preset.context_config,
                'user_id': request.user.id
            })
            
            # Check if provider is available (has API key)
            provider = preset.model_config['provider']
            provider_available = conversation_service.is_provider_available(provider)
            
            if not provider_available:
                validation_result['warnings'].append(
                    f"Provider '{provider}' is not available. Check API key configuration."
                )
            
            return Response({
                'valid': len(validation_result['errors']) == 0,
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings'],
                'preset_info': {
                    'key': preset.key,
                    'name': preset.name,
                    'description': preset.description,
                    'category': preset.category,
                    'provider': preset.model_config['provider'],
                    'model': preset.model_config['model']
                },
                'provider_available': provider_available
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Validation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProviderStatusView(APIView):
    """Check status of LLM providers"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get status of all LLM providers"""
        try:
            available_providers = conversation_service.get_available_providers()
            all_providers = ['anthropic', 'openai']
            
            provider_status = {}
            for provider in all_providers:
                provider_status[provider] = {
                    'available': provider in available_providers,
                    'api_key_configured': provider in available_providers
                }
            
            return Response({
                'providers': provider_status,
                'available_count': len(available_providers),
                'total_count': len(all_providers)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to get provider status: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConversationAnalyticsView(APIView):
    """Get conversation analytics for the current user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get conversation summary analytics"""
        try:
            days = int(request.GET.get('days', 30))
            summary = conversation_analytics.get_user_conversation_summary(
                user_id=request.user.id,
                days=days
            )
            
            return Response(summary, status=status.HTTP_200_OK)
            
        except ValueError:
            return Response({
                'error': 'Invalid days parameter'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Failed to get analytics: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SessionInsightsView(APIView):
    """Get detailed insights for a specific session"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        """Get insights for a specific session"""
        try:
            # Verify session ownership
            session_data = ChatSessionService.get_session_config(session_id)
            if not session_data or session_data['user_id'] != request.user.id:
                return Response({
                    'error': 'Session not found or access denied'
                }, status=status.HTTP_404_NOT_FOUND)
            
            insights = conversation_analytics.get_session_insights(session_id)
            
            return Response(insights, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to get session insights: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProviderComparisonView(APIView):
    """Compare LLM provider performance and usage"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get provider comparison data"""
        try:
            days = int(request.GET.get('days', 30))
            comparison = conversation_analytics.get_provider_comparison(
                user_id=request.user.id,
                days=days
            )
            
            return Response(comparison, status=status.HTTP_200_OK)
            
        except ValueError:
            return Response({
                'error': 'Invalid days parameter'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': f'Failed to get provider comparison: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)