"""
Chat session management services
Handles session lifecycle, configuration, and message storage
"""
from typing import Dict, Any, List, Optional, Tuple
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import timedelta

from .models import ChatSession, ChatMessage
from .providers import ProviderConfig, ContextConfig, SessionConfigValidator
from .presets import PresetManager

User = get_user_model()


class ChatSessionService:
    """
    Core service for managing chat sessions
    """
    
    @staticmethod
    def create_session(
        user_id: int,
        preset_key: str,
        title: str = "New Chat",
        ttl_hours: int = 24
    ) -> Tuple[str, List[str]]:
        """
        Create a new chat session using a configuration preset
        
        Args:
            user_id: User ID for session ownership
            preset_key: Key identifying the configuration preset to use
            title: Optional session title
            ttl_hours: Session TTL in hours
            
        Returns:
            Tuple of (session_id, errors_list)
            session_id is None if validation fails
        """
        # Get preset configuration
        preset = PresetManager.get_preset(preset_key)
        if not preset:
            return None, [f"Unknown preset key: {preset_key}"]
        
        # Validate complete configuration
        full_config = {
            'model_config': preset.model_config,
            'context_config': preset.context_config,
            'user_id': user_id
        }
        
        validation_result = SessionConfigValidator.validate_session_config(full_config)
        if validation_result['errors']:
            return None, validation_result['errors']
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None, [f"User with id {user_id} does not exist"]
        
        # Normalize configuration with defaults
        normalized_model_config = ProviderConfig.normalize_model_config(preset.model_config)
        
        # Create session with transaction safety
        with transaction.atomic():
            session = ChatSession.objects.create(
                user=user,
                model_config=normalized_model_config,
                context_config=preset.context_config,
                title=title,
                expires_at=timezone.now() + timedelta(hours=ttl_hours),
                is_active=True
            )
        
        return session.session_id, []
    
    @staticmethod
    def get_session_config(session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session configuration by session ID
        Returns None if session not found or expired
        """
        try:
            session = ChatSession.objects.get(
                session_id=session_id,
                is_active=True
            )
            
            if session.is_expired():
                # Mark as inactive and return None
                session.is_active = False
                session.save(update_fields=['is_active'])
                return None
            
            return {
                'session_id': session.session_id,
                'model_config': session.model_config,
                'context_config': session.context_config,
                'user_id': session.user.id,
                'created_at': session.created_at.isoformat(),
                'expires_at': session.expires_at.isoformat(),
                'message_count': session.get_message_count(),
                'title': session.title
            }
            
        except ChatSession.DoesNotExist:
            return None
    
    @staticmethod
    def update_session_config(
        session_id: str,
        preset_key: Optional[str] = None,
        title: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
        custom_control_instructions: Optional[List[str]] = None,
        quick_input_generation_instructions: Optional[str] = None,
        context_id: Optional[str] = None,
        quick_input_min_items: Optional[int] = None,
        quick_input_max_items: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Update session configuration with new settings

        Returns:
            Tuple of (success, errors_list)
        """

        try:
            session = ChatSession.objects.get(
                session_id=session_id,
                is_active=True
            )
            
            if session.is_expired():
                return False, ["Session has expired"]
            
            # Get new configuration
            new_model_config = session.model_config
            new_context_config = session.context_config.copy() if session.context_config else {}

            # Apply preset if specified
            if preset_key:
                preset = PresetManager.get_preset(preset_key)
                if not preset:
                    return False, [f"Unknown preset key: {preset_key}"]

                # Preserve custom settings before overwriting with preset
                preserved_quick_input = new_context_config.get('quick_input_generation_instructions')
                preserved_min_items = new_context_config.get('quick_input_min_items')
                preserved_max_items = new_context_config.get('quick_input_max_items')

                new_model_config = preset.model_config
                new_context_config = preset.context_config.copy()

                # Restore preserved custom settings
                if preserved_quick_input:
                    new_context_config['quick_input_generation_instructions'] = preserved_quick_input
                if preserved_min_items is not None:
                    new_context_config['quick_input_min_items'] = preserved_min_items
                if preserved_max_items is not None:
                    new_context_config['quick_input_max_items'] = preserved_max_items

            # Apply custom settings (these override preset settings)
            if custom_system_prompt is not None:
                if custom_system_prompt.strip():  # Non-empty custom prompt
                    new_context_config['custom_system_prompt'] = custom_system_prompt
                    # Remove preset context_id if custom prompt is provided
                    if 'context_id' in new_context_config:
                        del new_context_config['context_id']
                else:  # Empty string - clear custom prompt, keep context_id
                    # Remove custom prompt to fall back to context_id
                    if 'custom_system_prompt' in new_context_config:
                        del new_context_config['custom_system_prompt']

            # Set specific context_id if provided (for system prompt presets)
            if context_id is not None:
                new_context_config['context_id'] = context_id
                # Remove custom system prompt if context_id is specified
                if 'custom_system_prompt' in new_context_config:
                    del new_context_config['custom_system_prompt']

            if custom_control_instructions is not None:
                # Filter out empty instructions
                filtered_instructions = [instr.strip() for instr in custom_control_instructions if instr.strip()]
                if filtered_instructions:
                    new_context_config['custom_control_instructions'] = filtered_instructions
                elif 'custom_control_instructions' in new_context_config:
                    del new_context_config['custom_control_instructions']

            if quick_input_generation_instructions is not None:
                if quick_input_generation_instructions.strip():
                    new_context_config['quick_input_generation_instructions'] = quick_input_generation_instructions.strip()
                else:
                    if 'quick_input_generation_instructions' in new_context_config:
                        del new_context_config['quick_input_generation_instructions']

            # Handle min/max items
            if quick_input_min_items is not None:
                new_context_config['quick_input_min_items'] = max(2, min(5, quick_input_min_items))

            if quick_input_max_items is not None:
                new_context_config['quick_input_max_items'] = max(2, min(5, quick_input_max_items))

            # Build validation config
            validation_config = {
                'user_id': session.user.id,
                'model_config': new_model_config,
                'context_config': new_context_config
            }
            
            # Validate new configuration
            validation_result = SessionConfigValidator.validate_session_config(validation_config)
            if validation_result['errors']:
                return False, validation_result['errors']
            
            # Update session
            with transaction.atomic():
                if preset_key:
                    session.model_config = ProviderConfig.normalize_model_config(new_model_config)
                    session.context_config = new_context_config
                
                if title:
                    session.title = title
                
                session.save()
            
            return True, []
            
        except ChatSession.DoesNotExist:
            return False, ["Session not found"]
    
    @staticmethod
    def extend_session_ttl(session_id: str, hours: int = 24) -> bool:
        """Extend session TTL"""
        try:
            session = ChatSession.objects.get(
                session_id=session_id,
                is_active=True
            )
            session.extend_ttl(hours)
            return True
        except ChatSession.DoesNotExist:
            return False
    
    @staticmethod
    def deactivate_session(session_id: str) -> bool:
        """Deactivate a session"""
        try:
            session = ChatSession.objects.get(session_id=session_id)
            session.is_active = False
            session.save(update_fields=['is_active'])
            return True
        except ChatSession.DoesNotExist:
            return False
    
    @staticmethod
    def get_user_sessions(user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        try:
            user = User.objects.get(id=user_id)
            queryset = user.chat_sessions.all()
            
            if active_only:
                queryset = queryset.filter(is_active=True)
            
            sessions = []
            for session in queryset:
                if active_only and session.is_expired():
                    # Mark expired sessions as inactive
                    session.is_active = False
                    session.save(update_fields=['is_active'])
                    continue
                
                sessions.append({
                    'session_id': session.session_id,
                    'title': session.title,
                    'created_at': session.created_at.isoformat(),
                    'updated_at': session.updated_at.isoformat(),
                    'expires_at': session.expires_at.isoformat(),
                    'message_count': session.get_message_count(),
                    'is_active': session.is_active,
                    'model_config': session.model_config,
                    'context_config': session.context_config
                })
            
            return sessions
            
        except User.DoesNotExist:
            return []


class ChatMessageService:
    """
    Service for managing chat messages within sessions
    """
    
    @staticmethod
    def add_message(
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Add a message to a chat session
        
        Args:
            session_id: Target session
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            metadata: Optional metadata (provider response data, etc.)
            
        Returns:
            Message data dict or None if session not found
        """
        try:
            session = ChatSession.objects.get(
                session_id=session_id,
                is_active=True
            )
            
            if session.is_expired():
                return None
            
            message = ChatMessage.objects.create(
                session=session,
                role=role,
                content=content,
                metadata=metadata or {}
            )
            
            # Update session timestamp
            session.save(update_fields=['updated_at'])
            
            return {
                'id': str(message.id),
                'session_id': session_id,
                'role': message.role,
                'content': message.content,
                'metadata': message.metadata,
                'created_at': message.created_at.isoformat()
            }
            
        except ChatSession.DoesNotExist:
            return None
    
    @staticmethod
    def get_message_history(
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Get paginated message history for a session
        
        Returns:
            Dict with messages, total_count, has_more, or None if session not found
        """
        try:
            session = ChatSession.objects.get(
                session_id=session_id,
                is_active=True
            )
            
            if session.is_expired():
                return None
            
            queryset = session.messages.all()[offset:]
            total_count = session.messages.count()
            
            if limit:
                messages_page = queryset[:limit]
                has_more = offset + limit < total_count
            else:
                messages_page = queryset
                has_more = False
            
            messages = []
            for message in messages_page:
                messages.append({
                    'id': str(message.id),
                    'session_id': session_id,
                    'role': message.role,
                    'content': message.content,
                    'metadata': message.metadata,
                    'created_at': message.created_at.isoformat()
                })
            
            return {
                'messages': messages,
                'session_id': session_id,
                'total_count': total_count,
                'has_more': has_more,
                'offset': offset,
                'limit': limit
            }
            
        except ChatSession.DoesNotExist:
            return None
    
    @staticmethod
    def get_conversation_context(session_id: str, max_messages: int = 20) -> Optional[List[Dict[str, str]]]:
        """
        Get recent conversation history formatted for LLM context
        
        Returns:
            List of message dicts with 'role' and 'content', or None if session not found
        """
        try:
            session = ChatSession.objects.get(
                session_id=session_id,
                is_active=True
            )
            
            if session.is_expired():
                return None
            
            # Get recent messages, excluding system messages for context
            recent_messages = session.messages.exclude(role='system').order_by('-created_at')[:max_messages]
            
            # Reverse to get chronological order
            messages = []
            for message in reversed(recent_messages):
                messages.append({
                    'role': message.role,
                    'content': message.content
                })
            
            return messages
            
        except ChatSession.DoesNotExist:
            return None


class SessionCleanupService:
    """
    Service for cleaning up expired sessions
    """
    
    @staticmethod
    def cleanup_expired_sessions() -> int:
        """
        Mark expired sessions as inactive and optionally delete old data
        Returns count of cleaned up sessions
        """
        expired_sessions = ChatSession.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )
        
        count = expired_sessions.count()
        expired_sessions.update(is_active=False)
        
        return count
    
    @staticmethod
    def delete_old_inactive_sessions(days_old: int = 7) -> int:
        """
        Permanently delete inactive sessions older than specified days
        Returns count of deleted sessions
        """
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        old_sessions = ChatSession.objects.filter(
            updated_at__lt=cutoff_date,
            is_active=False
        )
        
        count = old_sessions.count()
        old_sessions.delete()
        
        return count