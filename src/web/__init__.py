from flask import Flask, render_template
from ..db import db_manager
from .routes import events_bp, api_bp

# Initialize Flask app
app = Flask(__name__)

# Initialize database with app
db_manager.init_app(app)
db_manager.init_db()  # Create tables if they don't exist

# Register blueprints
app.register_blueprint(events_bp)
app.register_blueprint(api_bp)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db_manager.Session.remove()  # Ensure session is cleaned up on error
    return render_template('errors/500.html'), 500 