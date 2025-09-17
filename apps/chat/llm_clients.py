"""
LLM Provider Client Implementations
Handles communication with Anthropic Claude and OpenAI GPT APIs
"""
import os
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import httpx
from django.conf import settings


@dataclass
class LLMMessage:
    """Standardized message format for LLM communication"""
    role: str  # 'user', 'assistant', 'system'
    content: str


@dataclass 
class LLMResponse:
    """Standardized response from LLM providers"""
    content: str
    metadata: Dict[str, Any]
    provider: str
    model: str
    success: bool
    error: Optional[str] = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM provider clients"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    @abstractmethod
    async def send_message(
        self, 
        messages: List[LLMMessage],
        model: str,
        parameters: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Send messages to LLM provider and get response"""
        pass
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


class AnthropicClient(BaseLLMClient):
    """Client for Anthropic Claude API"""
    
    BASE_URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
        super().__init__(api_key)
    
    async def send_message(
        self, 
        messages: List[LLMMessage],
        model: str,
        parameters: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Send message to Anthropic Claude API"""
        try:
            # Convert messages to Anthropic format
            claude_messages = []
            for msg in messages:
                if msg.role != 'system':  # System prompts handled separately in Anthropic
                    claude_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Build request payload
            payload = {
                "model": model,
                "messages": claude_messages,
                **parameters  # Include all preset parameters (max_tokens, temperature, etc.)
            }
            
            # Add system prompt if provided
            if system_prompt:
                payload["system"] = system_prompt
            
            # Make API request
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": self.API_VERSION
            }
            
            response = await self.client.post(
                self.BASE_URL,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("content", [])
                
                # Extract text content (Claude returns array of content blocks)
                text_content = ""
                if content and len(content) > 0:
                    text_content = content[0].get("text", "")
                
                # Extract metadata
                metadata = {
                    "usage": data.get("usage", {}),
                    "model": data.get("model", model),
                    "stop_reason": data.get("stop_reason"),
                    "id": data.get("id"),
                    "type": data.get("type")
                }
                
                return LLMResponse(
                    content=text_content,
                    metadata=metadata,
                    provider="anthropic", 
                    model=model,
                    success=True
                )
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                
                return LLMResponse(
                    content="",
                    metadata={"status_code": response.status_code, "error_data": error_data},
                    provider="anthropic",
                    model=model, 
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            return LLMResponse(
                content="",
                metadata={},
                provider="anthropic",
                model=model,
                success=False,
                error=f"Anthropic API error: {str(e)}"
            )


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI GPT API"""
    
    BASE_URL = "https://api.openai.com/v1/chat/completions"
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        super().__init__(api_key)
    
    async def send_message(
        self, 
        messages: List[LLMMessage],
        model: str,
        parameters: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Send message to OpenAI GPT API"""
        try:
            # Convert messages to OpenAI format
            openai_messages = []
            
            # Add system prompt as first message if provided
            if system_prompt:
                openai_messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add conversation messages
            for msg in messages:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Build request payload
            payload = {
                "model": model,
                "messages": openai_messages,
                **parameters  # Include all preset parameters
            }

            # Debug logging
            print(f"🚀 OpenAI API Request:")
            print(f"   Model: {model}")
            print(f"   Parameters: {parameters}")
            print(f"   Full payload model: {payload.get('model')}")
            print(f"   Full payload keys: {list(payload.keys())}")
            
            # Make API request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = await self.client.post(
                self.BASE_URL,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract content from first choice
                choices = data.get("choices", [])
                content = ""
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content", "")
                
                # Extract metadata
                metadata = {
                    "usage": data.get("usage", {}),
                    "model": data.get("model", model),
                    "finish_reason": choices[0].get("finish_reason") if choices else None,
                    "id": data.get("id"),
                    "object": data.get("object"),
                    "created": data.get("created")
                }
                
                return LLMResponse(
                    content=content,
                    metadata=metadata,
                    provider="openai",
                    model=model,
                    success=True
                )
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                
                return LLMResponse(
                    content="",
                    metadata={"status_code": response.status_code, "error_data": error_data},
                    provider="openai",
                    model=model,
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            return LLMResponse(
                content="",
                metadata={},
                provider="openai",
                model=model,
                success=False,
                error=f"OpenAI API error: {str(e)}"
            )


class LLMRouter:
    """
    Routes messages to appropriate LLM provider based on configuration
    Handles provider selection, failover, and response standardization
    """
    
    def __init__(self):
        self.clients = {
            "anthropic": None,
            "openai": None
        }
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize LLM clients with available API keys"""
        try:
            if os.getenv('ANTHROPIC_API_KEY'):
                self.clients["anthropic"] = AnthropicClient()
        except Exception as e:
            print(f"Warning: Could not initialize Anthropic client: {e}")
        
        try:
            if os.getenv('OPENAI_API_KEY'):
                self.clients["openai"] = OpenAIClient()
        except Exception as e:
            print(f"Warning: Could not initialize OpenAI client: {e}")
    
    async def send_message(
        self,
        messages: List[LLMMessage],
        provider: str,
        model: str,
        parameters: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Route message to appropriate provider"""
        
        # Check if provider client is available
        client = self.clients.get(provider)
        if not client:
            return LLMResponse(
                content="",
                metadata={},
                provider=provider,
                model=model,
                success=False,
                error=f"Provider '{provider}' not available. Check API key configuration."
            )
        
        # Send message to provider
        return await client.send_message(messages, model, parameters, system_prompt)
    
    def is_provider_available(self, provider: str) -> bool:
        """Check if a provider is available"""
        return self.clients.get(provider) is not None
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return [provider for provider, client in self.clients.items() if client is not None]
    
    async def close_all(self):
        """Close all client connections"""
        for client in self.clients.values():
            if client:
                await client.close()


# Global router instance
llm_router = LLMRouter()