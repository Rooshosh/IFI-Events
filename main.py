"""Main application entry point."""

from src.config.environment import IS_PRODUCTION_ENVIRONMENT
from src.api.app import app

if __name__ == "__main__":
    if not IS_PRODUCTION_ENVIRONMENT:
        # Development mode - use FastAPI's built-in server
        import uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug"
        )
    else:
        # Production mode - use uvicorn with production settings
        import uvicorn
        uvicorn.run(
            "src.api.app:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            workers=4,
            log_level="info",
            proxy_headers=True,
            forwarded_allow_ips="*"
        ) 