"""
Chat control service for generating emotes and quick responses
Implements parallel LLM requests using tool calling based on Chat_control_example.md
"""
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
import httpx

from .llm_clients import llm_router, LLMMessage
from .presets import PresetManager


class ChatControlService:
    """
    Service for generating chat control elements (emotes and quick responses)
    using parallel LLM requests with tool calling
    """

    # Control tool schema for structured output
    CONTROL_TOOL = {
        "type": "function",
        "function": {
            "name": "chat_orchestrator",
            "description": "Return control signals for a chat turn.",
            "strict": True,  # enforce JSON Schema
            "parameters": {
                "type": "object",
                "properties": {
                    "emote": {
                        "type": "string",
                        "enum": ["joy", "sad", "angry", "thinking", "neutral", "surprised", "confused", "excited"]
                    },
                    "quick_replies": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1, "maxLength": 40},
                        "minItems": 2,
                        "maxItems": 5
                    }
                },
                "additionalProperties": False,
                "required": ["emote", "quick_replies"]
            }
        }
    }

    # Emote mappings
    EMOTE_TO_GLYPH = {
        "joy": "😄",
        "sad": "😢",
        "angry": "😠",
        "thinking": "🤔",
        "neutral": "🙂",
        "surprised": "😲",
        "confused": "😕",
        "excited": "🎉"
    }

    def __init__(self):
        self.llm_router = llm_router

    async def generate_control_data(
        self,
        user_message: str,
        conversation_context: List[Dict[str, str]],
        session_config: Optional[Dict[str, Any]] = None,
        request_emote: bool = False,
        request_quick_responses: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Generate control data (emotes and quick responses) using tool calling

        Returns:
            Tuple of (control_data, errors)
        """
        # Skip if no control features requested
        if not request_emote and not request_quick_responses:
            return {
                "emote": None,
                "emote_glyph": None,
                "quick_replies": []
            }, []

        # Check for custom control instructions first
        custom_quick_replies = None
        if session_config and 'context_config' in session_config:
            from .providers import ContextConfig
            custom_quick_replies = ContextConfig.get_effective_control_instructions(
                session_config['context_config']
            )

        # If we have custom instructions and only quick responses are requested, return them directly
        if custom_quick_replies and request_quick_responses and not request_emote:
            return {
                "emote": None,
                "emote_glyph": None,
                "quick_replies": custom_quick_replies
            }, []

        try:
            # Get control preset
            control_preset = PresetManager.get_preset("gpt_control")
            if not control_preset:
                return None, ["Control preset not found"]

            # Check if OpenAI provider is available
            if not self.llm_router.is_provider_available("openai"):
                return None, ["OpenAI provider not available for control requests"]

            # Build context for control request
            context_messages = []
            if conversation_context:
                # Add recent conversation for context (last 3 exchanges)
                for msg in conversation_context[-6:]:  # 3 user + 3 assistant messages
                    context_messages.append(f"{msg['role']}: {msg['content']}")

            context_str = "\n".join(context_messages) if context_messages else "No prior context"

            # Get custom generation instructions if available
            generation_instructions = "Generate appropriate emotes and quick reply suggestions based on the conversation context."
            custom_min_items = 2  # Default min
            custom_max_items = 5  # Default max

            if session_config and 'context_config' in session_config:
                custom_instructions = session_config['context_config'].get('quick_input_generation_instructions')
                if custom_instructions:
                    generation_instructions = custom_instructions

                # Get custom min/max values if available
                custom_min_items = session_config['context_config'].get('quick_input_min_items', 2)
                custom_max_items = session_config['context_config'].get('quick_input_max_items', 5)

                # Ensure valid range
                custom_min_items = max(2, min(5, custom_min_items))
                custom_max_items = max(custom_min_items, min(5, custom_max_items))

            # Create dynamic tool schema with custom min/max items
            dynamic_tool = {
                "type": "function",
                "function": {
                    "name": "chat_orchestrator",
                    "description": "Return control signals for a chat turn.",
                    "strict": True,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "emote": {
                                "type": "string",
                                "enum": ["joy", "sad", "angry", "thinking", "neutral", "surprised", "confused", "excited"]
                            },
                            "quick_replies": {
                                "type": "array",
                                "items": {"type": "string", "minLength": 1, "maxLength": 40},
                                "minItems": custom_min_items,
                                "maxItems": custom_max_items
                            }
                        },
                        "additionalProperties": False,
                        "required": ["emote", "quick_replies"]
                    }
                }
            }

            # Create control request messages
            messages = [
                LLMMessage(
                    role="system",
                    content="You produce ONLY a function call that follows the schema exactly. "
                           f"{generation_instructions}"
                ),
                LLMMessage(
                    role="system",
                    content=f"CONVERSATION CONTEXT:\n{context_str}"
                ),
                LLMMessage(
                    role="user",
                    content=user_message
                )
            ]

            # Make control request with tool calling (using dynamic tool schema)
            control_response = await self._make_tool_call_request(
                messages=messages,
                model_config=control_preset.model_config,
                tools=[dynamic_tool],
                tool_choice={"type": "function", "function": {"name": "chat_orchestrator"}}
            )

            if not control_response.success:
                return None, [f"Control request failed: {control_response.error}"]

            # Parse tool call response
            control_data = self._parse_control_response(
                control_response,
                request_emote,
                request_quick_responses,
                custom_quick_replies
            )

            return control_data, []

        except Exception as e:
            return None, [f"Control service error: {str(e)}"]

    async def _make_tool_call_request(
        self,
        messages: List[LLMMessage],
        model_config: Dict[str, Any],
        tools: List[Dict[str, Any]],
        tool_choice: Dict[str, Any]
    ):
        """Make a tool calling request to OpenAI API"""
        try:
            # Get OpenAI client
            openai_client = self.llm_router.clients.get("openai")
            if not openai_client:
                raise Exception("OpenAI client not available")

            # Convert messages to OpenAI format
            openai_messages = []
            for msg in messages:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

            # Build request payload with tool calling
            payload = {
                "model": model_config["model"],
                "messages": openai_messages,
                "tools": tools,
                "tool_choice": tool_choice,
                "parallel_tool_calls": False,  # safer with strict schemas
                **model_config["parameters"]
            }

            # Make API request directly for tool calling support
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {openai_client.api_key}"
            }

            response = await openai_client.client.post(
                openai_client.BASE_URL,
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                return self._create_tool_response(data, model_config["model"])
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")

                from .llm_clients import LLMResponse
                return LLMResponse(
                    content="",
                    metadata={"status_code": response.status_code, "error_data": error_data},
                    provider="openai",
                    model=model_config["model"],
                    success=False,
                    error=error_msg
                )

        except Exception as e:
            from .llm_clients import LLMResponse
            return LLMResponse(
                content="",
                metadata={},
                provider="openai",
                model=model_config["model"],
                success=False,
                error=f"Tool call error: {str(e)}"
            )

    def _create_tool_response(self, data: Dict[str, Any], model: str):
        """Create LLMResponse from OpenAI tool call response"""
        from .llm_clients import LLMResponse

        choices = data.get("choices", [])

        # Extract tool calls from first choice
        tool_calls = []
        content = ""
        if choices:
            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls", [])
            content = message.get("content") or ""

        # Extract metadata
        metadata = {
            "usage": data.get("usage", {}),
            "model": data.get("model", model),
            "finish_reason": choices[0].get("finish_reason") if choices else None,
            "id": data.get("id"),
            "tool_calls": tool_calls
        }

        return LLMResponse(
            content=content,
            metadata=metadata,
            provider="openai",
            model=model,
            success=True
        )

    def _parse_control_response(
        self,
        response,
        request_emote: bool,
        request_quick_responses: bool,
        custom_quick_replies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Parse and validate control response from tool call"""
        # Extract tool call arguments
        tool_calls = response.metadata.get("tool_calls", [])
        control_args = {}

        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.get("function", {}).get("name") == "chat_orchestrator":
                    try:
                        args_str = tool_call.get("function", {}).get("arguments", "{}")
                        control_args = json.loads(args_str)
                        break
                    except json.JSONDecodeError:
                        control_args = {}

        # Apply safe fallbacks and feature flags
        result = {
            "emote": None,
            "emote_glyph": None,
            "quick_replies": []
        }

        if request_emote:
            emote = control_args.get("emote", "neutral")
            if emote in self.EMOTE_TO_GLYPH:
                result["emote"] = emote
                result["emote_glyph"] = self.EMOTE_TO_GLYPH[emote]
            else:
                result["emote"] = "neutral"
                result["emote_glyph"] = self.EMOTE_TO_GLYPH["neutral"]

        if request_quick_responses:
            if custom_quick_replies:
                # Use custom quick replies directly
                result["quick_replies"] = custom_quick_replies
            else:
                # Use LLM-generated quick replies
                quick_replies = control_args.get("quick_replies", [])
                if isinstance(quick_replies, list):
                    # Validate and limit quick replies
                    valid_replies = []
                    for reply in quick_replies[:5]:  # Max 5 replies
                        if isinstance(reply, str) and 1 <= len(reply) <= 40:
                            valid_replies.append(reply)
                    result["quick_replies"] = valid_replies

        return result


# Global control service instance
control_service = ChatControlService()