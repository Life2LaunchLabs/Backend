"""
Conversation service for processing chat messages and managing LLM interactions
Handles conversation context, system prompts, and message chain management
"""
from typing import Dict, List, Any, Optional, Tuple
import asyncio
from django.db import transaction
from asgiref.sync import sync_to_async

from .models import ChatSession, ChatMessage
from .llm_clients import LLMRouter, LLMMessage, LLMResponse, llm_router
from .providers import ContextConfig
from .services import ChatSessionService, ChatMessageService
from .processors import message_pipeline, ResponseCacheManager
from .control_service import control_service


class ConversationService:
    """
    Service for managing conversations between users and LLMs
    Handles message processing, context building, and response generation
    """
    
    def __init__(self):
        self.llm_router = llm_router
    
    async def send_message(
        self,
        session_id: str,
        user_message: str,
        user_id: int,
        request_emote: bool = False,
        request_quick_responses: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Send a user message and get LLM response with optional control features

        Args:
            session_id: Chat session identifier
            user_message: User's message content
            user_id: User ID for ownership verification
            request_emote: Whether to generate emote via parallel control request
            request_quick_responses: Whether to generate quick responses via parallel control request

        Returns:
            Tuple of (response_data, errors_list)
            response_data is None if there are errors
            response_data includes control_data with emotes and quick_responses when requested
        """
        try:
            # 1. Validate session and get configuration
            session_config = await sync_to_async(ChatSessionService.get_session_config)(session_id)
            if not session_config:
                return None, ["Session not found or expired"]
            
            # Verify user ownership
            if session_config['user_id'] != user_id:
                return None, ["Access denied to this session"]
            
            # 2. Get conversation history for processing context
            conversation_context = await sync_to_async(ChatMessageService.get_conversation_context)(
                session_id=session_id,
                max_messages=10
            )
            message_history = conversation_context or []
            
            # 3. Check response cache first
            cache_key = ResponseCacheManager.generate_cache_key(
                user_message,
                message_pipeline._create_context(user_id, session_id, session_config, message_history)
            )
            cached_response = ResponseCacheManager.get_cached_response(cache_key)
            
            if cached_response:
                # Handle cached response, but still generate control data if requested
                user_msg_data = await sync_to_async(ChatMessageService.add_message)(
                    session_id=session_id,
                    role='user',
                    content=user_message
                )

                assistant_msg_data = await sync_to_async(ChatMessageService.add_message)(
                    session_id=session_id,
                    role='assistant',
                    content=cached_response['content'],
                    metadata={
                        **cached_response['metadata'],
                        'cached': True,
                        'cache_key': cache_key
                    }
                )

                # Generate control data if requested (even for cached responses)
                control_data = None
                control_errors = []
                if request_emote or request_quick_responses:
                    # Convert message history for control service
                    conversation_context = []
                    if message_history:
                        for msg in message_history:
                            conversation_context.append({"role": msg["role"], "content": msg["content"]})

                    control_data, control_errors = await control_service.generate_control_data(
                        user_message=user_message,
                        conversation_context=conversation_context,
                        session_config=session_config,
                        request_emote=request_emote,
                        request_quick_responses=request_quick_responses
                    )

                # Build cached response data
                cached_response_data = {
                    'user_message': user_msg_data,
                    'assistant_message': assistant_msg_data,
                    'session_id': session_id,
                    'provider_metadata': cached_response['metadata'],
                    'processing_info': {'cached': True}
                }

                # Add control data if requested
                if request_emote or request_quick_responses:
                    cached_response_data['control_data'] = control_data or {
                        'emote': None,
                        'emote_glyph': None,
                        'quick_replies': []
                    }

                return cached_response_data, control_errors
            
            # 4. Process user message through pipeline
            processed_user_message = await sync_to_async(message_pipeline.process_user_message)(
                user_message, session_id, user_id, session_config, message_history
            )
            
            # 5. Store user message with processing metadata
            user_msg_data = await sync_to_async(ChatMessageService.add_message)(
                session_id=session_id,
                role='user',
                content=user_message,  # Store original message
                metadata={
                    'processed_content': processed_user_message.content,
                    'processing_notes': processed_user_message.processing_notes,
                    'structured_data': processed_user_message.structured_data,
                    'enhancements': processed_user_message.enhancements
                }
            )
            
            if not user_msg_data:
                return None, ["Failed to store user message"]
            
            # 6. Build conversation context using processed message
            conversation_messages = await self._build_conversation_context(session_id)
            if conversation_messages is None:
                return None, ["Failed to build conversation context"]
            
            # Use processed content for LLM
            if conversation_messages and conversation_messages[-1].role == 'user':
                conversation_messages[-1].content = processed_user_message.content
            
            # 7. Get system prompt
            context_config = session_config['context_config']
            system_prompt = self._get_system_prompt(context_config)
            
            # 8. Make parallel requests: main LLM response + control data (if requested)
            model_config = session_config['model_config']

            # Create tasks for parallel execution
            tasks = []

            # Main LLM response (always needed)
            main_task = self._send_to_llm(
                messages=conversation_messages,
                model_config=model_config,
                system_prompt=system_prompt
            )
            tasks.append(main_task)

            # Control request (optional)
            control_task = None
            if request_emote or request_quick_responses:
                # Convert message history for control service
                conversation_context = []
                if message_history:
                    for msg in message_history:
                        conversation_context.append({"role": msg["role"], "content": msg["content"]})

                control_task = control_service.generate_control_data(
                    user_message=user_message,
                    conversation_context=conversation_context,
                    session_config=session_config,
                    request_emote=request_emote,
                    request_quick_responses=request_quick_responses
                )
                tasks.append(control_task)

            # Execute tasks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            llm_response = results[0]

            # Handle control response
            control_data = None
            control_errors = []
            if control_task is not None:
                control_result = results[1]
                if isinstance(control_result, Exception):
                    control_errors.append(f"Control request failed: {str(control_result)}")
                elif isinstance(control_result, tuple):
                    control_data, control_errors = control_result
                    if control_data is None and control_errors:
                        # Control failed but main response might succeed
                        pass

            # Check for main LLM response errors
            if isinstance(llm_response, Exception):
                return None, [f"LLM request failed: {str(llm_response)}"]
            
            # 9. Handle LLM response
            if llm_response.success:
                # Process LLM response through pipeline
                processed_response = await sync_to_async(message_pipeline.process_llm_response)(
                    llm_response.content, session_id, user_id, session_config, message_history
                )
                
                # Store assistant response with processing data
                assistant_msg_data = await sync_to_async(ChatMessageService.add_message)(
                    session_id=session_id,
                    role='assistant',
                    content=processed_response.content,
                    metadata={
                        'llm_metadata': llm_response.metadata,
                        'provider': llm_response.provider,
                        'model': llm_response.model,
                        'original_content': llm_response.content,
                        'processing_notes': processed_response.processing_notes,
                        'structured_data': processed_response.structured_data,
                        'enhancements': processed_response.enhancements
                    }
                )
                
                if not assistant_msg_data:
                    return None, ["Failed to store assistant response"]
                
                # Cache the response for future use
                cache_data = {
                    'content': processed_response.content,
                    'metadata': {
                        'llm_metadata': llm_response.metadata,
                        'provider': llm_response.provider,
                        'model': llm_response.model,
                        'structured_data': processed_response.structured_data,
                        'enhancements': processed_response.enhancements
                    }
                }
                ResponseCacheManager.cache_response(cache_key, cache_data, timeout=1800)  # 30 minutes
                
                # Build response data with control features
                response_data = {
                    'user_message': user_msg_data,
                    'assistant_message': assistant_msg_data,
                    'session_id': session_id,
                    'provider_metadata': llm_response.metadata,
                    'processing_info': {
                        'processed': True,
                        'enhancements': processed_response.enhancements,
                        'structured_data': processed_response.structured_data,
                        'cache_key': cache_key
                    }
                }

                # Add control data if requested
                if request_emote or request_quick_responses:
                    response_data['control_data'] = control_data or {
                        'emote': None,
                        'emote_glyph': None,
                        'quick_replies': []
                    }

                # Return enhanced response data (include control errors as warnings if any)
                return response_data, control_errors
            
            else:
                # LLM request failed
                error_msg = llm_response.error or "Unknown LLM error"
                
                # Store error message for debugging
                error_msg_data = await sync_to_async(ChatMessageService.add_message)(
                    session_id=session_id,
                    role='system',
                    content=f"Error: {error_msg}",
                    metadata={
                        'error': True,
                        'provider': llm_response.provider,
                        'model': llm_response.model,
                        'llm_metadata': llm_response.metadata
                    }
                )
                
                return None, [f"LLM request failed: {error_msg}"]
        
        except Exception as e:
            return None, [f"Conversation service error: {str(e)}"]
    
    async def _build_conversation_context(
        self, 
        session_id: str, 
        max_messages: int = 20
    ) -> Optional[List[LLMMessage]]:
        """
        Build conversation context from recent messages
        Excludes system/error messages, keeps only user/assistant dialogue
        """
        try:
            # Get recent conversation messages
            conversation_context = await sync_to_async(ChatMessageService.get_conversation_context)(
                session_id=session_id,
                max_messages=max_messages
            )
            
            if conversation_context is None:
                return None
            
            # Convert to LLMMessage format
            llm_messages = []
            for msg in conversation_context:
                if msg['role'] in ['user', 'assistant']:  # Exclude system messages
                    llm_messages.append(LLMMessage(
                        role=msg['role'],
                        content=msg['content']
                    ))
            
            return llm_messages
            
        except Exception as e:
            print(f"Error building conversation context: {e}")
            return None
    
    def _get_system_prompt(self, context_config: Dict[str, Any]) -> Optional[str]:
        """Get system prompt based on context configuration"""
        try:
            # Use the effective system prompt which handles both presets and custom prompts
            return ContextConfig.get_effective_system_prompt(context_config)

        except Exception as e:
            print(f"Error getting system prompt: {e}")
            return None
    
    async def _send_to_llm(
        self,
        messages: List[LLMMessage],
        model_config: Dict[str, Any],
        system_prompt: Optional[str]
    ) -> LLMResponse:
        """Send messages to appropriate LLM provider"""
        try:
            provider = model_config.get('provider')
            model = model_config.get('model')
            parameters = model_config.get('parameters', {})
            
            if not provider or not model:
                return LLMResponse(
                    content="",
                    metadata={},
                    provider=provider or "unknown",
                    model=model or "unknown",
                    success=False,
                    error="Missing provider or model configuration"
                )
            
            # Send to LLM router
            return await self.llm_router.send_message(
                messages=messages,
                provider=provider,
                model=model,
                parameters=parameters,
                system_prompt=system_prompt
            )
            
        except Exception as e:
            return LLMResponse(
                content="",
                metadata={},
                provider=model_config.get('provider', 'unknown'),
                model=model_config.get('model', 'unknown'),
                success=False,
                error=f"LLM routing error: {str(e)}"
            )
    
    def get_available_providers(self) -> List[str]:
        """Get list of available LLM providers"""
        return self.llm_router.get_available_providers()
    
    def is_provider_available(self, provider: str) -> bool:
        """Check if a provider is available"""
        return self.llm_router.is_provider_available(provider)
    
    async def close(self):
        """Close LLM router connections"""
        await self.llm_router.close_all()


# Global conversation service instance
conversation_service = ConversationService()


class ConversationUtils:
    """Utility functions for conversation management"""
    
    @staticmethod
    def format_message_for_display(message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format message data for frontend display"""
        return {
            'id': message_data['id'],
            'role': message_data['role'],
            'content': message_data['content'],
            'timestamp': message_data['created_at'],
            'metadata': message_data.get('metadata', {})
        }
    
    @staticmethod
    def extract_usage_stats(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract usage statistics from LLM response"""
        try:
            assistant_msg = response_data.get('assistant_message', {})
            metadata = assistant_msg.get('metadata', {})
            llm_metadata = metadata.get('llm_metadata', {})
            usage = llm_metadata.get('usage', {})
            
            return {
                'provider': metadata.get('provider'),
                'model': metadata.get('model'),
                'input_tokens': usage.get('input_tokens') or usage.get('prompt_tokens', 0),
                'output_tokens': usage.get('output_tokens') or usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            }
            
        except Exception as e:
            return {'error': f'Failed to extract usage stats: {str(e)}'}
    
    @staticmethod
    def is_conversation_empty(session_id: str) -> bool:
        """Check if conversation has any messages"""
        try:
            history = ChatMessageService.get_message_history(session_id, limit=1)
            return history is None or len(history.get('messages', [])) == 0
        except:
            return True