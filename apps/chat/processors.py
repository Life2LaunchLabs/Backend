"""
Advanced Message Processing Pipeline for Phase 3
Handles pre-processing, post-processing, and structured data extraction
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
import re
import json
import hashlib
from datetime import datetime
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from .models import ChatSession, ChatMessage


@dataclass
class ProcessingContext:
    """Context data passed through the processing pipeline"""
    user_id: int
    session_id: str
    session_config: Dict[str, Any]
    message_history: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    processing_metadata: Dict[str, Any]


@dataclass
class ProcessedMessage:
    """Result of message processing"""
    content: str
    structured_data: Dict[str, Any]
    enhancements: Dict[str, Any]
    processing_notes: List[str]
    cache_key: Optional[str] = None


class BaseProcessor(ABC):
    """Abstract base class for all message processors"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    @abstractmethod
    def process(self, content: str, context: ProcessingContext) -> ProcessedMessage:
        """Process message content and return enhanced result"""
        pass
    
    def is_applicable(self, content: str, context: ProcessingContext) -> bool:
        """Check if this processor should be applied to the given content"""
        return True


class MessagePreProcessor:
    """Handles pre-processing of user messages before sending to LLM"""
    
    def __init__(self):
        self.processors = [
            ContentFilterProcessor(),
            ContextEnhancementProcessor(), 
            PersonalizationProcessor(),
            FormattingProcessor()
        ]
    
    def process(self, message: str, context: ProcessingContext) -> ProcessedMessage:
        """Apply all pre-processors to user message"""
        processed = ProcessedMessage(
            content=message,
            structured_data={},
            enhancements={},
            processing_notes=[]
        )
        
        for processor in self.processors:
            if processor.is_applicable(processed.content, context):
                try:
                    processed = processor.process(processed.content, context)
                    processed.processing_notes.append(f"Applied {processor.__class__.__name__}")
                except Exception as e:
                    processed.processing_notes.append(f"Error in {processor.__class__.__name__}: {str(e)}")
                    continue
        
        return processed


class MessagePostProcessor:
    """Handles post-processing of LLM responses"""
    
    def __init__(self):
        self.processors = [
            StructuredDataExtractor(),
            CodeHighlightProcessor(),
            MarkdownEnhancementProcessor(),
            LinkDetectionProcessor(),
            ContentSafetyProcessor()
        ]
    
    def process(self, response: str, context: ProcessingContext) -> ProcessedMessage:
        """Apply all post-processors to LLM response"""
        processed = ProcessedMessage(
            content=response,
            structured_data={},
            enhancements={},
            processing_notes=[]
        )
        
        for processor in self.processors:
            if processor.is_applicable(processed.content, context):
                try:
                    result = processor.process(processed.content, context)
                    processed.content = result.content
                    processed.structured_data.update(result.structured_data)
                    processed.enhancements.update(result.enhancements)
                    processed.processing_notes.extend(result.processing_notes)
                except Exception as e:
                    processed.processing_notes.append(f"Error in {processor.__class__.__name__}: {str(e)}")
                    continue
        
        return processed


# Pre-Processing Components
class ContentFilterProcessor(BaseProcessor):
    """Filters and moderates user input"""
    
    def process(self, content: str, context: ProcessingContext) -> ProcessedMessage:
        # Basic content filtering (extend with ML-based moderation)
        filtered_content = content.strip()
        
        # Remove excessive whitespace
        filtered_content = re.sub(r'\s+', ' ', filtered_content)
        
        # Basic profanity filtering (replace with proper content moderation service)
        profanity_patterns = [r'\b(spam|test123)\b']  # Example patterns
        for pattern in profanity_patterns:
            filtered_content = re.sub(pattern, '[filtered]', filtered_content, flags=re.IGNORECASE)
        
        notes = []
        if filtered_content != content:
            notes.append("Content filtered")
        
        return ProcessedMessage(
            content=filtered_content,
            structured_data={},
            enhancements={'filtered': filtered_content != content},
            processing_notes=notes
        )


class ContextEnhancementProcessor(BaseProcessor):
    """Adds relevant context to user messages"""
    
    def process(self, content: str, context: ProcessingContext) -> ProcessedMessage:
        enhanced_content = content
        structured_data = {}
        
        # Add session context if relevant
        if len(context.message_history) > 0:
            structured_data['conversation_length'] = len(context.message_history)
            
        # Add time context
        current_time = datetime.now()
        structured_data['timestamp'] = current_time.isoformat()
        structured_data['time_context'] = {
            'hour': current_time.hour,
            'day_of_week': current_time.weekday(),
            'is_weekend': current_time.weekday() >= 5
        }
        
        return ProcessedMessage(
            content=enhanced_content,
            structured_data=structured_data,
            enhancements={'context_added': True},
            processing_notes=['Added temporal and session context']
        )


class PersonalizationProcessor(BaseProcessor):
    """Personalizes messages based on user preferences"""
    
    def process(self, content: str, context: ProcessingContext) -> ProcessedMessage:
        # Get user preferences (would come from user profile in real implementation)
        user_prefs = context.user_preferences
        
        personalized_content = content
        enhancements = {}
        
        # Example: Add user's preferred tone instruction
        if user_prefs.get('tone') == 'formal':
            personalized_content = f"Please respond in a formal tone. {content}"
            enhancements['tone_instruction'] = 'formal'
        elif user_prefs.get('tone') == 'casual':
            personalized_content = f"Please respond in a casual, friendly tone. {content}"
            enhancements['tone_instruction'] = 'casual'
        
        return ProcessedMessage(
            content=personalized_content,
            structured_data={'user_preferences_applied': user_prefs},
            enhancements=enhancements,
            processing_notes=['Applied user personalization']
        )


class FormattingProcessor(BaseProcessor):
    """Handles message formatting and structure"""
    
    def process(self, content: str, context: ProcessingContext) -> ProcessedMessage:
        formatted_content = content
        
        # Ensure proper sentence structure
        if not content.endswith(('.', '!', '?')):
            formatted_content = content + '.'
        
        # Capitalize first letter
        if formatted_content and not formatted_content[0].isupper():
            formatted_content = formatted_content[0].upper() + formatted_content[1:]
        
        return ProcessedMessage(
            content=formatted_content,
            structured_data={},
            enhancements={'formatted': formatted_content != content},
            processing_notes=['Applied basic formatting']
        )


# Post-Processing Components
class StructuredDataExtractor(BaseProcessor):
    """Extracts structured data from LLM responses"""
    
    def process(self, content: str, context: ProcessingContext) -> ProcessedMessage:
        structured_data = {}
        
        # Extract code blocks
        code_blocks = re.findall(r'```(\w+)?\n(.*?)\n```', content, re.DOTALL)
        if code_blocks:
            structured_data['code_blocks'] = [
                {'language': lang or 'text', 'code': code.strip()}
                for lang, code in code_blocks
            ]
        
        # Extract lists
        lists = re.findall(r'(?:^|\n)(?:\d+\.|[\-\*])\s+(.+)', content, re.MULTILINE)
        if lists:
            structured_data['lists'] = lists
        
        # Extract questions
        questions = re.findall(r'([^.!?]*\?)', content)
        if questions:
            structured_data['questions'] = [q.strip() for q in questions]
        
        # Extract key-value pairs (basic)
        kv_pairs = re.findall(r'(\w+):\s*([^\n]+)', content)
        if kv_pairs:
            structured_data['key_value_pairs'] = dict(kv_pairs)
        
        return ProcessedMessage(
            content=content,
            structured_data=structured_data,
            enhancements={'extraction_performed': True},
            processing_notes=['Extracted structured data elements']
        )


class CodeHighlightProcessor(BaseProcessor):
    """Adds syntax highlighting hints to code blocks"""
    
    def process(self, content: str, context: ProcessingContext) -> ProcessedMessage:
        enhancements = {}
        
        # Find code blocks and add highlighting hints
        code_pattern = r'```(\w+)?\n(.*?)\n```'
        code_blocks = re.findall(code_pattern, content, re.DOTALL)
        
        if code_blocks:
            highlighting_info = []
            for lang, code in code_blocks:
                lang = lang or self._detect_language(code)
                highlighting_info.append({
                    'language': lang,
                    'line_count': len(code.strip().split('\n')),
                    'has_syntax_elements': bool(re.search(r'[{}();]', code))
                })
            
            enhancements['code_highlighting'] = highlighting_info
        
        return ProcessedMessage(
            content=content,
            structured_data={},
            enhancements=enhancements,
            processing_notes=['Processed code blocks for highlighting']
        )
    
    def _detect_language(self, code: str) -> str:
        """Basic language detection based on code patterns"""
        if 'def ' in code and 'import ' in code:
            return 'python'
        elif 'function ' in code and '{' in code:
            return 'javascript'
        elif 'public class' in code:
            return 'java'
        elif '#include' in code:
            return 'cpp'
        else:
            return 'text'


class MarkdownEnhancementProcessor(BaseProcessor):
    """Enhances markdown formatting in responses"""
    
    def process(self, content: str, context: ProcessingContext) -> ProcessedMessage:
        enhancements = {}
        
        # Detect markdown elements
        markdown_elements = {
            'headers': len(re.findall(r'^#+\s+', content, re.MULTILINE)),
            'bold': len(re.findall(r'\*\*[^*]+\*\*', content)),
            'italic': len(re.findall(r'\*[^*]+\*', content)),
            'links': len(re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)),
            'tables': len(re.findall(r'\|[^|\n]+\|', content))
        }
        
        if any(markdown_elements.values()):
            enhancements['markdown_elements'] = markdown_elements
            enhancements['has_markdown'] = True
        
        return ProcessedMessage(
            content=content,
            structured_data={},
            enhancements=enhancements,
            processing_notes=['Analyzed markdown elements']
        )


class LinkDetectionProcessor(BaseProcessor):
    """Detects and processes links in responses"""
    
    def process(self, content: str, context: ProcessingContext) -> ProcessedMessage:
        # Find URLs
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, content)
        
        structured_data = {}
        if urls:
            structured_data['detected_urls'] = [
                {'url': url, 'domain': re.search(r'://([^/]+)', url).group(1) if '://' in url else 'unknown'}
                for url in urls
            ]
        
        return ProcessedMessage(
            content=content,
            structured_data=structured_data,
            enhancements={'url_detection_performed': True},
            processing_notes=['Detected and analyzed URLs']
        )


class ContentSafetyProcessor(BaseProcessor):
    """Final safety check on LLM responses"""
    
    def process(self, content: str, context: ProcessingContext) -> ProcessedMessage:
        safety_flags = []
        
        # Basic safety checks (extend with proper content moderation)
        if len(content) > 10000:  # Very long responses
            safety_flags.append('very_long_response')
        
        # Check for potential sensitive information patterns
        sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
            r'\b\d{16}\b',  # Credit card pattern
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, content):
                safety_flags.append('potential_sensitive_data')
        
        return ProcessedMessage(
            content=content,
            structured_data={'safety_flags': safety_flags},
            enhancements={'safety_checked': True},
            processing_notes=['Applied content safety checks']
        )


class ResponseCacheManager:
    """Manages caching of processed responses"""
    
    @staticmethod
    def generate_cache_key(message: str, context: ProcessingContext) -> str:
        """Generate a cache key for the message and context"""
        # Create a hash of the message and relevant context
        cache_data = {
            'message': message,
            'preset_key': context.session_config.get('preset_key'),
            'user_preferences': context.user_preferences
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return f"chat_response:{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    @staticmethod
    def get_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached response"""
        return cache.get(cache_key)
    
    @staticmethod
    def cache_response(cache_key: str, response_data: Dict[str, Any], timeout: int = 3600):
        """Cache response data"""
        cache.set(cache_key, response_data, timeout)


class MessageProcessingPipeline:
    """Main pipeline coordinator for message processing"""
    
    def __init__(self):
        self.pre_processor = MessagePreProcessor()
        self.post_processor = MessagePostProcessor()
        self.cache_manager = ResponseCacheManager()
    
    def process_user_message(
        self, 
        message: str, 
        session_id: str, 
        user_id: int,
        session_config: Dict[str, Any],
        message_history: List[Dict[str, Any]] = None
    ) -> ProcessedMessage:
        """Process user message before sending to LLM"""
        
        context = ProcessingContext(
            user_id=user_id,
            session_id=session_id,
            session_config=session_config,
            message_history=message_history or [],
            user_preferences=self._get_user_preferences(user_id),
            processing_metadata={}
        )
        
        return self.pre_processor.process(message, context)
    
    def process_llm_response(
        self,
        response: str,
        session_id: str,
        user_id: int,
        session_config: Dict[str, Any],
        message_history: List[Dict[str, Any]] = None
    ) -> ProcessedMessage:
        """Process LLM response after receiving"""
        
        context = ProcessingContext(
            user_id=user_id,
            session_id=session_id,
            session_config=session_config,
            message_history=message_history or [],
            user_preferences=self._get_user_preferences(user_id),
            processing_metadata={}
        )
        
        return self.post_processor.process(response, context)
    
    def _create_context(
        self,
        user_id: int,
        session_id: str,
        session_config: Dict[str, Any],
        message_history: List[Dict[str, Any]]
    ) -> ProcessingContext:
        """Create processing context for pipeline"""
        return ProcessingContext(
            user_id=user_id,
            session_id=session_id,
            session_config=session_config,
            message_history=message_history,
            user_preferences=self._get_user_preferences(user_id),
            processing_metadata={}
        )

    def _get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get user preferences (placeholder - would come from user profile service)"""
        # Default preferences
        return {
            'tone': 'balanced',
            'detail_level': 'medium',
            'code_highlighting': True,
            'markdown_rendering': True
        }


# Global pipeline instance
message_pipeline = MessageProcessingPipeline()