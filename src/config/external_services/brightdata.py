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

    # Webhook configuration
    'webhook_base_url': 'https://api.ifi.events' if IS_PRODUCTION_ENVIRONMENT else 'http://localhost:8000',
    'webhook_endpoint': '/webhook/brightdata/facebook-group/results',
    'webhook_format': 'json',
    'webhook_uncompressed': True,

    # Dataset configuration
    'dataset_id': 'gd_lz11l67o2cb3r0lkj3',  # Facebook - Posts by group URL dataset
    'group_url': 'https://www.facebook.com/groups/ifistudenter',
    'include_errors': True,

    # Fetch parameters
    'days_to_fetch': 30,
    'num_of_posts': 100,
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
    if not BRIGHTDATA_CONFIG['group_url']:
        raise ValueError("group_url is required")
    if not BRIGHTDATA_CONFIG['webhook_base_url']:
        raise ValueError("webhook_base_url is required")
    if not BRIGHTDATA_CONFIG['webhook_endpoint']:
        raise ValueError("webhook_endpoint is required")
    if BRIGHTDATA_CONFIG['days_to_fetch'] < 1:
        raise ValueError("days_to_fetch must be at least 1")
    if BRIGHTDATA_CONFIG['num_of_posts'] < 1:
        raise ValueError("num_of_posts must be at least 1")
    
    return True

def verify_brightdata_auth(auth_header: str) -> bool:
    """Verify BrightData webhook authorization header."""
    return bool(auth_header and auth_header == BRIGHTDATA_CONFIG['webhook_auth']) 