"""BrightData service configuration."""

import os
from typing import Dict, Any

from ..environment import IS_PRODUCTION_ENVIRONMENT

# BrightData configuration
BRIGHTDATA_CONFIG = {
    # API configuration
    'base_url': "https://api.brightdata.com/datasets/v3",
    'content_type': "application/json",

    # Authentication
    'api_key': os.environ.get('BRIGHTDATA_API_KEY'),
    'webhook_auth': os.environ.get('BRIGHTDATA_AUTHORIZATION_HEADER'),
}

def get_brightdata_config() -> Dict[str, Any]:
    """Get BrightData configuration with validation."""
    verify_brightdata_config()
    return BRIGHTDATA_CONFIG.copy()

def verify_brightdata_config() -> bool:
    """Verify BrightData configuration."""
    if not BRIGHTDATA_CONFIG['api_key']:
        raise ValueError("BRIGHTDATA_API_KEY environment variable is required")
    if not BRIGHTDATA_CONFIG['webhook_auth']:
        raise ValueError("BRIGHTDATA_AUTHORIZATION_HEADER environment variable is required")
    return True

def verify_brightdata_auth(auth_header: str) -> bool:
    """Verify BrightData webhook authorization header."""
    return bool(auth_header and auth_header == BRIGHTDATA_CONFIG['webhook_auth']) 