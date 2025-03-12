"""CORS configuration for the FastAPI application."""

from .environment import IS_PRODUCTION_ENVIRONMENT

# CORS Origins configuration
ALLOWED_ORIGINS = {
    False: ["*"],  # Development - allow all
    True: [        # Production - restricted
        "https://ifi.events",          # Main frontend
        "https://www.ifi.events",      # With www
        "https://api.ifi.events",      # API domain
    ]
}

# CORS Methods configuration
ALLOWED_METHODS = [
    "GET",      # For fetching events
    "POST",     # For webhooks and admin endpoints
    "OPTIONS"   # Required for CORS preflight
]

# CORS Headers configuration
ALLOWED_HEADERS = [
    "Authorization",  # For admin endpoints
    "Content-Type",   # For request bodies
    "Accept",        # For content negotiation
]

# Additional CORS settings
CORS_CONFIG = {
    "allow_origins": ALLOWED_ORIGINS[IS_PRODUCTION_ENVIRONMENT],
    "allow_credentials": True,
    "allow_methods": ALLOWED_METHODS,
    "allow_headers": ALLOWED_HEADERS,
    "expose_headers": [],
    "max_age": 3600,
} 