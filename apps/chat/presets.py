"""
Configuration presets for chat sessions
Frontend sends a single preset key, backend manages all configuration details
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ConfigPreset:
    """A complete configuration preset for chat sessions"""
    key: str
    name: str
    description: str
    model_config: Dict[str, Any]
    context_config: Dict[str, Any]
    category: str = "general"
    is_default: bool = False


class PresetManager:
    """
    Manages configuration presets for chat sessions
    Frontend only needs to send a preset key, backend handles all details
    """
    
    # Define all available presets
    PRESETS = [
        # Anthropic Claude Presets
        ConfigPreset(
            key="claude_sonnet_4_0",
            name="Claude",
            description="State of the art Claude conversation model (Sonnet 4)",
            model_config={
                "provider": "anthropic",
                "model": "claude-sonnet-4-20250514",
                "parameters": {
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "top_p": 1.0
                }
            },
            context_config={
                "context_id": "general"
            },
            category="general",
            is_default=True
        ),

        ConfigPreset(
            key="claude_haiku_3_5",
            name="Claude Lite",
            description="A smaller version of claude: cheaper and faster (Haiku 3.5)",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-5-haiku-20241022",
                "parameters": {
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "top_p": 1.0
                }
            },
            context_config={
                "context_id": "general"
            },
            category="general",
            is_default=False
        ),
        
        # OpenAI GPT Presets
        ConfigPreset(
            key="gpt5",
            name="GPT-5",
            description="State of the art OpenAI model (GPT5)",
            model_config={
                "provider": "openai",
                "model": "gpt-5",
                "parameters": {
                    "max_completion_tokens": 4096,  # Newer OpenAI models use max_completion_tokens instead of max_tokens
                }
            },
            context_config={
                "context_id": "general"
            },
            category="general"
        ),

        # Control Model for Chat Enhancement Features
        ConfigPreset(
            key="gpt_control",
            name="GPT lite",
            description="Smaller version of openai model: faster and cheaper. (GPT-5-nano)",
            model_config={
                "provider": "openai",
                "model": "gpt-5-nano",  
                "parameters": {
                    "max_completion_tokens": 1024,  # Newer OpenAI models use max_completion_tokens instead of max_tokens
                }
            },
            context_config={
                "context_id": "control"  # Specialized context for control requests
            },
            category="control"
        ),
    ]
    
    @classmethod
    def get_preset(cls, preset_key: str) -> Optional[ConfigPreset]:
        """Get a preset by its key"""
        for preset in cls.PRESETS:
            if preset.key == preset_key:
                return preset
        return None
    
    @classmethod
    def get_all_presets(cls) -> List[ConfigPreset]:
        """Get all available presets"""
        return cls.PRESETS.copy()
    
    @classmethod
    def get_presets_by_category(cls, category: str) -> List[ConfigPreset]:
        """Get all presets in a specific category"""
        return [preset for preset in cls.PRESETS if preset.category == category]
    
    @classmethod
    def get_default_preset(cls) -> ConfigPreset:
        """Get the default preset with robust fallback"""
        # Check for multiple defaults and warn
        defaults = [preset for preset in cls.PRESETS if preset.is_default]

        if len(defaults) > 1:
            # Multiple defaults found - use the first one but this should be fixed
            print(f"WARNING: Multiple default presets found: {[p.key for p in defaults]}. Using {defaults[0].key}")
            return defaults[0]
        elif len(defaults) == 1:
            return defaults[0]
        else:
            # No defaults found - find a suitable fallback
            # Prefer Claude Sonnet 4.0 if available, otherwise first preset
            for preset in cls.PRESETS:
                if preset.key == "claude_sonnet_4_0":
                    return preset

            if cls.PRESETS:
                print(f"WARNING: No default preset marked. Using fallback: {cls.PRESETS[0].key}")
                return cls.PRESETS[0]

            raise ValueError("No presets available")
    
    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all available categories"""
        categories = set(preset.category for preset in cls.PRESETS)
        return sorted(list(categories))
    
    @classmethod
    def validate_preset_key(cls, preset_key: str) -> bool:
        """Check if a preset key is valid"""
        return cls.get_preset(preset_key) is not None
    
    @classmethod
    def validate_presets_configuration(cls) -> Dict[str, List[str]]:
        """Validate the entire presets configuration and return issues"""
        errors = []
        warnings = []

        if not cls.PRESETS:
            errors.append("No presets defined")
            return {"errors": errors, "warnings": warnings}

        # Check for multiple defaults
        defaults = [preset for preset in cls.PRESETS if preset.is_default]
        if len(defaults) > 1:
            warnings.append(f"Multiple default presets found: {[p.key for p in defaults]}")
        elif len(defaults) == 0:
            warnings.append("No default preset marked")

        # Check for duplicate keys
        keys = [preset.key for preset in cls.PRESETS]
        duplicates = [key for key in set(keys) if keys.count(key) > 1]
        if duplicates:
            errors.append(f"Duplicate preset keys found: {duplicates}")

        # Validate each preset
        from .providers import SessionConfigValidator
        for preset in cls.PRESETS:
            try:
                validation = SessionConfigValidator.validate_session_config({
                    'model_config': preset.model_config,
                    'context_config': preset.context_config,
                    'user_id': 1  # dummy user_id for validation
                })
                if validation['errors']:
                    errors.append(f"Preset '{preset.key}' has validation errors: {validation['errors']}")
                if validation['warnings']:
                    warnings.append(f"Preset '{preset.key}' has warnings: {validation['warnings']}")
            except Exception as e:
                errors.append(f"Preset '{preset.key}' validation failed: {str(e)}")

        return {"errors": errors, "warnings": warnings}

    @classmethod
    def to_dict_list(cls) -> List[Dict[str, Any]]:
        """Convert presets to serializable format for API responses"""
        return [
            {
                "key": preset.key,
                "name": preset.name,
                "description": preset.description,
                "category": preset.category,
                "is_default": preset.is_default,
                "provider": preset.model_config["provider"],
                "model": preset.model_config["model"]
            }
            for preset in cls.PRESETS
        ]