"""OpenAI service configuration."""

import os
from typing import Dict, Any, Optional
import httpx
from openai import OpenAI

# Default OpenAI configuration
OPENAI_CONFIG = {
    'api_key': os.environ.get('OPENAI_API_KEY'),
    'model': 'gpt-4-turbo-preview',
    'temperature': 0.3,
    'max_tokens': 500,
    'timeout': 30.0
}

_client: Optional[OpenAI] = None

def get_openai_config() -> Dict[str, Any]:
    """Get OpenAI configuration with validation."""
    if not OPENAI_CONFIG['api_key']:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return OPENAI_CONFIG.copy()

def init_openai_client() -> OpenAI:
    """Initialize OpenAI client with API key and custom configuration.
    
    Returns:
        OpenAI: Configured OpenAI client instance
    
    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
    """
    global _client
    
    config = get_openai_config()
    
    if _client is None:
        # Create a custom httpx client without any proxy settings
        http_client = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {config['api_key']}"},
            timeout=config['timeout']
        )
        _client = OpenAI(api_key=config['api_key'], http_client=http_client)
 