from flask import Flask, render_template
from .routes import events_bp
from ..config import Config
import logging

# Module logger
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    # Initialize Flask app
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Register blueprints
    app.register_blueprint(events_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    return app 