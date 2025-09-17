"""
Conversation Analytics Service for Phase 3
Provides insights and metrics about chat conversations and user interactions
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone

from .models import ChatSession, ChatMessage
from .services import ChatSessionService, ChatMessageService


class ConversationAnalytics:
    """Service for analyzing conversation patterns and generating insights"""
    
    @staticmethod
    def get_user_conversation_summary(user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive conversation summary for a user"""
        
        # Date range for analysis
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get user sessions in date range
        sessions = ChatSession.objects.filter(
            user_id=user_id,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        # Basic session metrics
        session_stats = {
            'total_sessions': sessions.count(),
            'active_sessions': sessions.filter(is_active=True).count(),
            'average_session_duration': None,  # Would require session tracking
        }
        
        # Get messages in date range
        messages = ChatMessage.objects.filter(
            session__user_id=user_id,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        # Message statistics
        message_stats = {
            'total_messages': messages.count(),
            'user_messages': messages.filter(role='user').count(),
            'assistant_messages': messages.filter(role='assistant').count(),
            'system_messages': messages.filter(role='system').count(),
        }
        
        # Usage patterns by provider
        provider_usage = ConversationAnalytics._analyze_provider_usage(user_id, start_date, end_date)
        
        # Conversation topics (basic keyword analysis)
        conversation_topics = ConversationAnalytics._extract_conversation_topics(messages)
        
        # Time-based patterns
        time_patterns = ConversationAnalytics._analyze_time_patterns(messages)
        
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat(), 'days': days},
            'session_stats': session_stats,
            'message_stats': message_stats,
            'provider_usage': provider_usage,
            'conversation_topics': conversation_topics,
            'time_patterns': time_patterns,
            'generated_at': timezone.now().isoformat()
        }
    
    @staticmethod
    def get_session_insights(session_id: str) -> Dict[str, Any]:
        """Get detailed insights for a specific conversation session"""
        
        try:
            session = ChatSession.objects.get(session_id=session_id)
        except ChatSession.DoesNotExist:
            return {'error': 'Session not found'}
        
        # Get all messages for this session
        messages = ChatMessage.objects.filter(session=session).order_by('created_at')
        
        # Basic session info
        session_info = {
            'session_id': session_id,
            'created_at': session.created_at.isoformat(),
            'preset_key': session.model_config.get('preset_key'),
            'provider': session.model_config.get('provider'),
            'model': session.model_config.get('model'),
        }
        
        # Message analysis
        message_analysis = ConversationAnalytics._analyze_session_messages(messages)
        
        # Conversation flow analysis
        flow_analysis = ConversationAnalytics._analyze_conversation_flow(messages)
        
        # Response quality metrics
        quality_metrics = ConversationAnalytics._calculate_response_quality(messages)
        
        return {
            'session_info': session_info,
            'message_analysis': message_analysis,
            'flow_analysis': flow_analysis,
            'quality_metrics': quality_metrics,
            'generated_at': timezone.now().isoformat()
        }
    
    @staticmethod
    def get_provider_comparison(user_id: int, days: int = 30) -> Dict[str, Any]:
        """Compare performance and usage across different LLM providers"""
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get sessions grouped by provider
        sessions = ChatSession.objects.filter(
            user_id=user_id,
            created_at__gte=start_date
        )
        
        provider_stats = {}
        
        for session in sessions:
            provider = session.model_config.get('provider', 'unknown')
            model = session.model_config.get('model', 'unknown')
            
            if provider not in provider_stats:
                provider_stats[provider] = {
                    'sessions': 0,
                    'messages': 0,
                    'models': set(),
                    'total_tokens': 0,
                    'avg_response_time': [],
                    'user_satisfaction': []
                }
            
            provider_stats[provider]['sessions'] += 1
            provider_stats[provider]['models'].add(model)
            
            # Get messages for token counting
            messages = ChatMessage.objects.filter(session=session)
            provider_stats[provider]['messages'] += messages.count()
            
            # Extract token usage from metadata
            for message in messages:
                if message.role == 'assistant' and message.metadata:
                    tokens = message.metadata.get('llm_metadata', {}).get('usage', {})
                    total_tokens = tokens.get('total_tokens', 0)
                    provider_stats[provider]['total_tokens'] += total_tokens
        
        # Convert sets to lists for JSON serialization
        for provider, stats in provider_stats.items():
            stats['models'] = list(stats['models'])
            stats['avg_tokens_per_message'] = (
                stats['total_tokens'] / max(stats['messages'], 1)
            )
        
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'provider_comparison': provider_stats,
            'generated_at': timezone.now().isoformat()
        }
    
    @staticmethod
    def _analyze_provider_usage(user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze usage patterns by provider"""
        
        sessions = ChatSession.objects.filter(
            user_id=user_id,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        usage_by_provider = {}
        
        for session in sessions:
            provider = session.model_config.get('provider', 'unknown')
            if provider not in usage_by_provider:
                usage_by_provider[provider] = {'sessions': 0, 'messages': 0}
            
            usage_by_provider[provider]['sessions'] += 1
            # Calculate message count for this session
            message_count = ChatMessage.objects.filter(session=session).count()
            usage_by_provider[provider]['messages'] += message_count
        
        return usage_by_provider
    
    @staticmethod
    def _extract_conversation_topics(messages) -> List[Dict[str, Any]]:
        """Basic topic extraction from conversation messages"""
        
        # Simple keyword-based topic extraction
        topics = {}
        
        # Common topic keywords
        topic_keywords = {
            'programming': ['code', 'function', 'variable', 'programming', 'debug', 'error', 'syntax'],
            'writing': ['write', 'essay', 'article', 'content', 'draft', 'editing'],
            'analysis': ['analyze', 'data', 'research', 'study', 'examine', 'investigate'],
            'creative': ['creative', 'story', 'poem', 'design', 'art', 'imagination'],
            'technical': ['system', 'architecture', 'database', 'server', 'network', 'api'],
            'business': ['strategy', 'plan', 'market', 'business', 'revenue', 'profit']
        }
        
        for message in messages:
            if message.role in ['user', 'assistant']:
                content = message.content.lower()
                
                for topic, keywords in topic_keywords.items():
                    for keyword in keywords:
                        if keyword in content:
                            if topic not in topics:
                                topics[topic] = 0
                            topics[topic] += 1
        
        # Convert to list format with percentages
        total_mentions = sum(topics.values())
        topic_list = []
        
        if total_mentions > 0:
            for topic, count in sorted(topics.items(), key=lambda x: x[1], reverse=True):
                topic_list.append({
                    'topic': topic,
                    'mentions': count,
                    'percentage': round((count / total_mentions) * 100, 1)
                })
        
        return topic_list[:5]  # Top 5 topics
    
    @staticmethod
    def _analyze_time_patterns(messages) -> Dict[str, Any]:
        """Analyze conversation timing patterns"""
        
        if not messages:
            return {}
        
        # Group messages by hour of day
        hourly_distribution = {}
        daily_distribution = {}
        
        for message in messages:
            if message.role == 'user':  # Only count user messages for activity
                hour = message.created_at.hour
                day = message.created_at.strftime('%A')
                
                hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
                daily_distribution[day] = daily_distribution.get(day, 0) + 1
        
        # Find peak activity times
        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else None
        peak_day = max(daily_distribution.items(), key=lambda x: x[1])[0] if daily_distribution else None
        
        return {
            'hourly_distribution': hourly_distribution,
            'daily_distribution': daily_distribution,
            'peak_hour': peak_hour,
            'peak_day': peak_day,
            'most_active_period': ConversationAnalytics._categorize_time_period(peak_hour) if peak_hour else None
        }
    
    @staticmethod
    def _analyze_session_messages(messages) -> Dict[str, Any]:
        """Analyze messages within a specific session"""
        
        total_messages = messages.count()
        user_messages = messages.filter(role='user')
        assistant_messages = messages.filter(role='assistant')
        
        # Calculate average message lengths
        user_avg_length = 0
        assistant_avg_length = 0
        
        if user_messages:
            user_avg_length = sum(len(msg.content) for msg in user_messages) / user_messages.count()
        
        if assistant_messages:
            assistant_avg_length = sum(len(msg.content) for msg in assistant_messages) / assistant_messages.count()
        
        # Detect conversation phases
        phases = ConversationAnalytics._detect_conversation_phases(messages)
        
        return {
            'total_messages': total_messages,
            'user_messages': user_messages.count(),
            'assistant_messages': assistant_messages.count(),
            'avg_user_message_length': round(user_avg_length, 1),
            'avg_assistant_message_length': round(assistant_avg_length, 1),
            'conversation_phases': phases
        }
    
    @staticmethod
    def _analyze_conversation_flow(messages) -> Dict[str, Any]:
        """Analyze the flow and structure of conversation"""
        
        flow_patterns = {
            'question_answer_pairs': 0,
            'follow_up_questions': 0,
            'topic_changes': 0,
            'conversation_depth': 1
        }
        
        previous_user_msg = None
        
        for message in messages:
            if message.role == 'user':
                if previous_user_msg:
                    # Check for follow-up questions
                    if '?' in message.content and '?' in previous_user_msg.content:
                        flow_patterns['follow_up_questions'] += 1
                
                # Count questions
                if '?' in message.content:
                    flow_patterns['question_answer_pairs'] += 1
                
                previous_user_msg = message
        
        return flow_patterns
    
    @staticmethod
    def _calculate_response_quality(messages) -> Dict[str, Any]:
        """Calculate metrics for response quality assessment"""
        
        assistant_messages = messages.filter(role='assistant')
        
        quality_indicators = {
            'avg_response_length': 0,
            'structured_responses': 0,
            'code_examples': 0,
            'detailed_explanations': 0
        }
        
        if assistant_messages:
            total_length = sum(len(msg.content) for msg in assistant_messages)
            quality_indicators['avg_response_length'] = round(total_length / assistant_messages.count(), 1)
            
            for message in assistant_messages:
                content = message.content
                
                # Check for structured content
                if any(marker in content for marker in ['1.', '2.', '•', '-', '*']):
                    quality_indicators['structured_responses'] += 1
                
                # Check for code examples
                if '```' in content or '`' in content:
                    quality_indicators['code_examples'] += 1
                
                # Check for detailed explanations (longer responses)
                if len(content) > 500:
                    quality_indicators['detailed_explanations'] += 1
        
        return quality_indicators
    
    @staticmethod
    def _detect_conversation_phases(messages) -> List[str]:
        """Detect different phases in the conversation"""
        
        phases = []
        
        if messages.count() <= 2:
            phases.append('initial_greeting')
        elif messages.count() <= 5:
            phases.append('exploration')
        elif messages.count() <= 10:
            phases.append('deep_discussion')
        else:
            phases.append('extended_conversation')
        
        # Check for specific patterns
        user_messages = [msg.content.lower() for msg in messages if msg.role == 'user']
        
        if any('thank' in msg for msg in user_messages):
            phases.append('gratitude_expressed')
        
        if any('?' in msg for msg in user_messages):
            phases.append('inquiry_phase')
        
        return phases
    
    @staticmethod
    def _categorize_time_period(hour: int) -> str:
        """Categorize hour into time period"""
        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 21:
            return 'evening'
        else:
            return 'night'


# Global analytics service instance
conversation_analytics = ConversationAnalytics()