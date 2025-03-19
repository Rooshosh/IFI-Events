"""OpenAI service configuration."""

import os
from typing import Dict, Any, Optional
import httpx
from openai import OpenAI
from dataclasses import dataclass

@dataclass
class OpenAIConfig:
    """OpenAI configuration settings."""
    
    # API configuration
    api_key: str = ""
    model: str = 'gpt-4-turbo-preview'
    temperature: float = 0.3
    max_tokens: int = 500
    timeout: float = 30.0
    
    def __post_init__(self):
        """Load API key from environment if not provided."""
        if not self.api_key:
            self.api_key = os.environ.get('OPENAI_API_KEY', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            'api_key': self.api_key,
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'timeout': self.timeout
        }
    
    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return True

# Module-level singleton instance
_openai: Optional[OpenAI] = None

def get_openai_config() -> Dict[str, Any]:
    """Get OpenAI configuration with validation."""
    config = OpenAIConfig()
    config.validate()
    return config.to_dict()

def init_openai_client() -> OpenAI:
    """Initialize OpenAI client with API key and custom configuration.
    
    Returns:
        OpenAI: Configured OpenAI client instance
    
    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
    """
    global _openai
    
    if _openai is None:
        config = OpenAIConfig()
        config.validate()
        
        # Create a custom httpx client without any proxy settings
        http_client = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=config.timeout
        )
        _openai = OpenAI(api_key=config.api_key, http_client=http_client)
    
    return _openai
 