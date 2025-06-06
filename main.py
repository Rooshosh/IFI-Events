"""Main application entry point."""

from src.config.environment import IS_PRODUCTION_ENVIRONMENT
import uvicorn

if __name__ == "__main__":
    if not IS_PRODUCTION_ENVIRONMENT:
        # Development mode
        uvicorn.run(
            "src.api.app:app",  # Use import string for reload support
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug"
        )
    else:
        # Production mode
        uvicorn.run(
            "src.api.app:app",  # String reference required for multiple workers
            host="0.0.0.0",
            port=8000,
            reload=False,
            workers=2,  # Match Railway's configuration
            log_level="info"
        )