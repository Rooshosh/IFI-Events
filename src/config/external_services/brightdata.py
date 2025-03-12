"""BrightData service configuration."""

import os
from typing import Dict, Any

from ..environment import IS_PRODUCTION_ENVIRONMENT

# BrightData configuration
BRIGHTDATA_CONFIG = {
    'api_key': os.environ.get('BRIGHTDATA_API_KEY'),
    'webhook_auth': os.environ.get('BRIGHTDATA_AUTHORIZATION_HEADER'),
    'webhook_base_url': 'https://api.ifi.events' if IS_PRODUCTION_ENVIRONMENT else 'http://localhost:8000',
    'webhook_endpoint': '/webhook/brightdata/facebook-group',
    'days_to_fetch': 30,
    'num_of_posts': 100,
    'group_url': 'https://www.facebook.com/groups/ifijobber'
}

def get_brightdata_config() -> Dict[str, Any]:
    """Get BrightData configuration with validation."""
    if not BRIGHTDATA_CONFIG['api_key']:
        raise ValueError("BRIGHTDATA_API_KEY environment variable is required")
    if not BRIGHTDATA_CONFIG['webhook_auth']:
        raise ValueError("BRIGHTDATA_AUTHORIZATION_HEADER environment variable is required")
    return BRIGHTDATA_CONFIG.copy()

def verify_brightdata_auth(auth_header: str) -> bool:
    """Verify BrightData webhook authorization header."""
    return bool(auth_header and auth_header == BRIGHTDATA_CONFIG['webhook_auth']) 