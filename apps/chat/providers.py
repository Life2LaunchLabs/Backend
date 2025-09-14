"""
Dynamic provider configuration system for multi-LLM support
Handles parameter mapping and validation for different providers
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class ProviderSpec:
    """Specification for an LLM provider"""
    name: str
    display_name: str
    supported_models: List[str]
    required_params: List[str]
    optional_params: List[str]
    param_defaults: Dict[str, Any]
    param_ranges: Dict[str, Dict[str, Any]]  # min/max/step for numeric params


class ProviderConfig:
    """
    Central configuration for all supported LLM providers
    Defines parameter schemas and validation rules
    """
    
    ANTHROPIC_SPEC = ProviderSpec(
        name="anthropic",
        display_name="Anthropic Claude",
        supported_models=[
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022", 
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ],
        required_params=["max_tokens"],
        optional_params=["temperature", "top_p", "top_k", "stop_sequences"],
        param_defaults={
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 1.0,
            "top_k": 0
        },
        param_ranges={
            "max_tokens": {"min": 1, "max": 8192},
            "temperature": {"min": 0.0, "max": 1.0, "step": 0.1},
            "top_p": {"min": 0.0, "max": 1.0, "step": 0.01},
            "top_k": {"min": 0, "max": 40}
        }
    )
    
    OPENAI_SPEC = ProviderSpec(
        name="openai",
        display_name="OpenAI GPT",
        supported_models=[
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo"
        ],
        required_params=["max_tokens"],
        optional_params=[
            "temperature", "top_p", "frequency_penalty", 
            "presence_penalty", "stop"
        ],
        param_defaults={
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        },
        param_ranges={
            "max_tokens": {"min": 1, "max": 32768},
            "temperature": {"min": 0.0, "max": 2.0, "step": 0.1},
            "top_p": {"min": 0.0, "max": 1.0, "step": 0.01},
            "frequency_penalty": {"min": -2.0, "max": 2.0, "step": 0.1},
            "presence_penalty": {"min": -2.0, "max": 2.0, "step": 0.1}
        }
    )
    
    PROVIDERS = {
        "anthropic": ANTHROPIC_SPEC,
        "openai": OPENAI_SPEC
    }
    
    @classmethod
    def get_provider_spec(cls, provider_name: str) -> Optional[ProviderSpec]:
        """Get provider specification by name"""
        return cls.PROVIDERS.get(provider_name)
    
    @classmethod
    def get_all_providers(cls) -> Dict[str, ProviderSpec]:
        """Get all available provider specifications"""
        return cls.PROVIDERS.copy()
    
    @classmethod
    def validate_model_config(cls, model_config: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate a model configuration
        Returns dict with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []
        
        # Check required fields
        if 'provider' not in model_config:
            errors.append("Missing required field: provider")
            return {"errors": errors, "warnings": warnings}
        
        if 'model' not in model_config:
            errors.append("Missing required field: model")
            
        provider_name = model_config.get('provider')
        spec = cls.get_provider_spec(provider_name)
        
        if not spec:
            errors.append(f"Unsupported provider: {provider_name}")
            return {"errors": errors, "warnings": warnings}
        
        # Validate model
        model_name = model_config.get('model')
        if model_name and model_name not in spec.supported_models:
            errors.append(f"Unsupported model '{model_name}' for provider '{provider_name}'")
        
        # Validate parameters
        params = model_config.get('parameters', {})
        
        # Check required parameters
        for required_param in spec.required_params:
            if required_param not in params:
                errors.append(f"Missing required parameter: {required_param}")
        
        # Validate parameter values
        for param_name, param_value in params.items():
            if param_name not in spec.required_params + spec.optional_params:
                warnings.append(f"Unknown parameter '{param_name}' for provider '{provider_name}'")
                continue
            
            # Check numeric ranges
            if param_name in spec.param_ranges:
                range_spec = spec.param_ranges[param_name]
                if isinstance(param_value, (int, float)):
                    if param_value < range_spec.get("min", float('-inf')):
                        errors.append(f"Parameter '{param_name}' below minimum: {range_spec['min']}")
                    if param_value > range_spec.get("max", float('inf')):
                        errors.append(f"Parameter '{param_name}' above maximum: {range_spec['max']}")
        
        return {"errors": errors, "warnings": warnings}
    
    @classmethod
    def normalize_model_config(cls, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize model configuration with defaults
        Returns a complete configuration with all defaults applied
        """
        provider_name = model_config.get('provider')
        spec = cls.get_provider_spec(provider_name)
        
        if not spec:
            return model_config
        
        normalized = model_config.copy()
        normalized.setdefault('parameters', {})
        
        # Apply defaults for missing parameters
        for param, default_value in spec.param_defaults.items():
            if param not in normalized['parameters']:
                normalized['parameters'][param] = default_value
        
        return normalized


class ContextConfig:
    """
    Configuration for chat context and system prompts
    Supports different context types and dynamic prompt loading
    """
    
    DEFAULT_CONTEXTS = {
        "general": {
            "name": "General Assistant",
            "system_prompt": "You are a helpful, harmless, and honest AI assistant.",
            "description": "General purpose conversational AI"
        },
        "coding": {
            "name": "Coding Assistant", 
            "system_prompt": "You are an expert programmer and coding assistant. Help with code review, debugging, and implementation.",
            "description": "Specialized for programming tasks"
        },
        "creative": {
            "name": "Creative Assistant",
            "system_prompt": "You are a creative writing assistant. Help with storytelling, brainstorming, and creative projects.",
            "description": "Focused on creative tasks"
        }
    }
    
    @classmethod
    def get_context(cls, context_id: str) -> Optional[Dict[str, Any]]:
        """Get context configuration by ID"""
        return cls.DEFAULT_CONTEXTS.get(context_id)
    
    @classmethod
    def get_all_contexts(cls) -> Dict[str, Dict[str, Any]]:
        """Get all available contexts"""
        return cls.DEFAULT_CONTEXTS.copy()
    
    @classmethod
    def validate_context_config(cls, context_config: Dict[str, Any]) -> List[str]:
        """Validate context configuration, return list of errors"""
        errors = []

        # Support both preset context_id and custom context
        has_context_id = 'context_id' in context_config
        has_custom_prompt = 'custom_system_prompt' in context_config

        if not has_context_id and not has_custom_prompt:
            errors.append("Must provide either 'context_id' or 'custom_system_prompt'")
            return errors

        # If both are provided, custom takes precedence
        if has_context_id and has_custom_prompt:
            pass  # Custom will override preset
        elif has_context_id:
            context_id = context_config.get('context_id')
            if context_id not in cls.DEFAULT_CONTEXTS:
                errors.append(f"Unknown context_id: {context_id}")
        elif has_custom_prompt:
            custom_prompt = context_config.get('custom_system_prompt')
            if not isinstance(custom_prompt, str) or not custom_prompt.strip():
                errors.append("custom_system_prompt must be a non-empty string")

        # Validate custom_control_instructions if provided
        if 'custom_control_instructions' in context_config:
            instructions = context_config.get('custom_control_instructions')
            if not isinstance(instructions, list):
                errors.append("custom_control_instructions must be a list")
            else:
                for i, instruction in enumerate(instructions):
                    if not isinstance(instruction, str):
                        errors.append(f"custom_control_instructions[{i}] must be a string")
                    elif len(instruction.strip()) == 0:
                        errors.append(f"custom_control_instructions[{i}] cannot be empty")
                    elif len(instruction) > 40:
                        errors.append(f"custom_control_instructions[{i}] cannot exceed 40 characters")

        return errors

    @classmethod
    def get_effective_system_prompt(cls, context_config: Dict[str, Any]) -> str:
        """Get the effective system prompt from context config"""
        # Custom prompt takes precedence
        if 'custom_system_prompt' in context_config:
            return context_config['custom_system_prompt']

        # Fallback to preset
        context_id = context_config.get('context_id', 'general')
        context = cls.get_context(context_id)
        if context:
            return context['system_prompt']

        # Ultimate fallback
        return cls.DEFAULT_CONTEXTS['general']['system_prompt']

    @classmethod
    def get_effective_control_instructions(cls, context_config: Dict[str, Any]) -> Optional[List[str]]:
        """Get the effective control instructions from context config"""
        # Custom instructions take precedence
        if 'custom_control_instructions' in context_config:
            return context_config['custom_control_instructions']

        # Return None to use service defaults
        return None


class SessionConfigValidator:
    """
    Validates complete session configurations
    Combines model and context validation
    """
    
    @staticmethod
    def validate_session_config(config: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate complete session configuration
        Returns dict with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []
        
        # Validate model config
        if 'model_config' not in config:
            errors.append("Missing required field: model_config")
        else:
            model_validation = ProviderConfig.validate_model_config(config['model_config'])
            errors.extend(model_validation['errors'])
            warnings.extend(model_validation['warnings'])
        
        # Validate context config
        if 'context_config' not in config:
            errors.append("Missing required field: context_config")
        else:
            context_errors = ContextConfig.validate_context_config(config['context_config'])
            errors.extend(context_errors)
        
        # Validate user_id
        if 'user_id' not in config:
            errors.append("Missing required field: user_id")
        
        return {"errors": errors, "warnings": warnings}