import os
from src.web import app

if __name__ == '__main__':
    """
    Development vs Production Configuration:
    
    Development:
        - Set FLASK_ENV=development to enable:
            * Debug mode with detailed error pages
            * Interactive debugger
            * Auto-reload on code changes
        - Uses localhost (127.0.0.1) by default
        Example: FLASK_ENV=development flask run --port=5001
    
    Production:
        - Never enable debug mode
        - Use a production WSGI server (e.g., Gunicorn, uWSGI)
        - Set FLASK_ENV=production or don't set it at all
        - Uses 0.0.0.0 to accept external connections
        - Remove or disable test routes (like test-500)
        Example: gunicorn 'src.web:app'
        
    Note: The current setup is intended for development. 
    For production deployment, additional security measures should be implemented.
    """
    # Set configuration based on environment variables
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    host = 'localhost' if debug_mode else '0.0.0.0'
    port = int(os.environ.get('PORT', 5001))
    
    # Run the app
    app.run(host=host, debug=debug_mode, port=port) 