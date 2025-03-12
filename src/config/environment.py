"""Environment configuration module.

This module MUST be imported before any other project modules that depend on environment variables.
It loads the .env file and sets up the environment configuration that will be used throughout the project,
both when running the FastAPI app and when running standalone scripts.

Usage:
    from src.config.environment import IS_PRODUCTION_ENVIRONMENT

Note:
    This module handles loading of environment variables via python-dotenv.
    In production (e.g. on Railway), environment variables should be set directly
    in the platform's environment configuration.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables - this must happen before any other imports
load_dotenv()

# Environment configuration
env_setting = os.environ.get('ENVIRONMENT', '').lower()
IS_PRODUCTION_ENVIRONMENT = env_setting == 'production'

if env_setting not in ['development', 'production']:
    logging.warning(
        f"Environment setting '{env_setting}' is invalid or not specified. "
        "Expected 'development' or 'production'. Defaulting to development environment."
    )

__all__ = ['IS_PRODUCTION_ENVIRONMENT'] 