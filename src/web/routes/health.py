"""Health check endpoints."""

from flask import Blueprint, jsonify
from sqlalchemy import text
from ...db import db_manager

bp = Blueprint('health', __name__)

@bp.route('/health')
def health_check():
    """Check if the application and database are healthy."""
    try:
        # Test database connection
        with db_manager.session() as db:
            db.execute(text('SELECT 1'))
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': str(e)
        }), 500 