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
            key="claude_balanced",
            name="Claude Balanced",
            description="Balanced Claude 3.5 Sonnet for general conversations",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
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
            key="claude_creative",
            name="Claude Creative", 
            description="More creative Claude 3.5 Sonnet for brainstorming",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "parameters": {
                    "max_tokens": 4096,
                    "temperature": 0.9,
                    "top_p": 0.95
                }
            },
            context_config={
                "context_id": "creative"
            },
            category="creative"
        ),
        
        ConfigPreset(
            key="claude_coding",
            name="Claude Coding",
            description="Claude 3.5 Sonnet optimized for programming tasks",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022", 
                "parameters": {
                    "max_tokens": 8192,
                    "temperature": 0.3,
                    "top_p": 1.0
                }
            },
            context_config={
                "context_id": "coding"
            },
            category="coding"
        ),
        
        ConfigPreset(
            key="claude_fast",
            name="Claude Fast",
            description="Fast Claude 3.5 Haiku for quick responses",
            model_config={
                "provider": "anthropic",
                "model": "claude-3-5-haiku-20241022",
                "parameters": {
                    "max_tokens": 2048,
                    "temperature": 0.7,
                    "top_p": 1.0
                }
            },
            context_config={
                "context_id": "general"
            },
            category="general"
        ),
        
        # OpenAI GPT Presets
        ConfigPreset(
            key="gpt4_balanced",
            name="GPT-4 Balanced",
            description="Balanced GPT-4 for general conversations",
            model_config={
                "provider": "openai",
                "model": "gpt-4o",
                "parameters": {
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "top_p": 1.0,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
                }
            },
            context_config={
                "context_id": "general"
            },
            category="general"
        ),
        
        ConfigPreset(
            key="gpt4_creative",
            name="GPT-4 Creative",
            description="Creative GPT-4 for writing and brainstorming", 
            model_config={
                "provider": "openai",
                "model": "gpt-4o",
                "parameters": {
                    "max_tokens": 4096,
                    "temperature": 0.9,
                    "top_p": 0.95,
                    "frequency_penalty": 0.1,
                    "presence_penalty": 0.1
                }
            },
            context_config={
                "context_id": "creative"
            },
            category="creative"
        ),
        
        ConfigPreset(
            key="gpt4_coding",
            name="GPT-4 Coding",
            description="GPT-4 optimized for programming tasks",
            model_config={
                "provider": "openai",
                "model": "gpt-4o",
                "parameters": {
                    "max_tokens": 8192,
                    "temperature": 0.2,
                    "top_p": 1.0,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
                }
            },
            context_config={
                "context_id": "coding"
            },
            category="coding"
        ),
        
        ConfigPreset(
            key="gpt4_mini",
            name="GPT-4 Mini",
            description="Fast and cost-effective GPT-4 mini for simple tasks",
            model_config={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "parameters": {
                    "max_tokens": 2048,
                    "temperature": 0.7,
                    "top_p": 1.0,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
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
            name="GPT Control",
            description="Specialized control model for emotes and quick responses",
            model_config={
                "provider": "openai",
                "model": "gpt-4o",  # Will try gpt-5 if available, fallback to gpt-4o
                "parameters": {
                    "max_tokens": 1024,
                    "temperature": 0.1,  # Very low temperature for consistent control output
                    "top_p": 1.0,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
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
        """Get the default preset"""
        for preset in cls.PRESETS:
            if preset.is_default:
                return preset
        # Fallback to first preset if no default is marked
        return cls.PRESETS[0]
    
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