import os
from src.web import app
import sys

if __name__ == '__main__':
    """
    Environment Configuration:
    
    Development (Local):
        - Set FLASK_ENV=development to enable:
            * Debug mode with detailed error pages
            * Interactive debugger
            * Auto-reload on code changes
        - Uses localhost (127.0.0.1) by default
        Example: FLASK_ENV=development python run.py
    
    Development (Replit):
        - Set FLASK_ENV=development
        - Uses 0.0.0.0 to make it accessible in Replit webview
        - Debug mode enabled
        Example: In .replit file: run = "FLASK_ENV=development python run.py"
    
    Production:
        - Uses Gunicorn WSGI server
        - Set FLASK_ENV=production or don't set it at all
        - Uses 0.0.0.0 to accept external connections
        - Production-ready error handling
        Example: FLASK_ENV=production python run.py
        
    Note: For production deployment, additional security measures should be implemented.
    """
    env = os.environ.get('FLASK_ENV', 'production')
    port = int(os.environ.get('PORT', 5001))
    
    if env == 'development':
        # Development mode - use Flask's built-in server
        # Use 0.0.0.0 if running in Replit, localhost otherwise
        host = '0.0.0.0' if os.environ.get('REPL_ID') else 'localhost'
        app.run(
            host=host,
            port=port,
            debug=True
        )
    else:
        # Production mode - use Gunicorn
        try:
            from gunicorn.app.base import BaseApplication

            class GunicornApp(BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def load_config(self):
                    for key, value in self.options.items():
                        self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application

            options = {
                'bind': f'0.0.0.0:{port}',
                'workers': os.environ.get('GUNICORN_WORKERS', '2'),
                'worker_class': 'sync',
                'timeout': 120
            }
            
            GunicornApp(app, options).run()
        except ImportError:
            print("Error: Gunicorn is required for production mode.")
            print("Please install it with: pip install gunicorn")
            sys.exit(1) 