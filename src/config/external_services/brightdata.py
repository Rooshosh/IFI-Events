"""BrightData service configuration."""

import os
from typing import Dict, Any
from dataclasses import dataclass

from ..environment import IS_PRODUCTION_ENVIRONMENT

@dataclass
class BrightDataConfig:
    """BrightData configuration settings."""
    
    # API configuration
    base_url: str = "https://api.brightdata.com/datasets/v3"
    content_type: str = "application/json"
    
    # Authentication
    api_key: str = ""
    webhook_auth: str = ""
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.api_key:
            self.api_key = os.environ.get('BRIGHTDATA_API_KEY', '')
        if not self.webhook_auth:
            self.webhook_auth = os.environ.get('BRIGHTDATA_AUTHORIZATION_HEADER', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary format."""
        return {
            'base_url': self.base_url,
            'content_type': self.content_type,
            'api_key': self.api_key,
            'webhook_auth': self.webhook_auth,
        }
    
    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.api_key:
            raise ValueError("BRIGHTDATA_API_KEY environment variable is required")
        if not self.webhook_auth:
            raise ValueError("BRIGHTDATA_AUTHORIZATION_HEADER environment variable is required")
        return True

def get_brightdata_config() -> Dict[str, Any]:
    """Get BrightData configuration with validation."""
    config = BrightDataConfig()
    config.validate()
    return config.to_dict()

def verify_brightdata_auth(auth_header: str) -> bool:
    """Verify BrightData webhook authorization header."""
    config = BrightDataConfig()
    return bool(auth_header and auth_header == config.webhook_auth) 