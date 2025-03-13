"""Main application entry point."""

from src.config.environment import IS_PRODUCTION_ENVIRONMENT
from src.api.app import app

if __name__ == "__main__":
    if not IS_PRODUCTION_ENVIRONMENT:
        # Development mode - use direct app instance for better debugging and hot-reload
        import uvicorn
        uvicorn.run(
            app,  # Direct app instance for development
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug"
        )
    else:
        # Production mode - use string reference for proper multi-worker support
        import uvicorn
        uvicorn.run(
            "src.api.app:app",  # String reference required for multiple workers
            host="0.0.0.0",
            port=8000,
            reload=False,
            workers=4,
            log_level="info",
            proxy_headers=True,
            forwarded_allow_ips="*"
        )