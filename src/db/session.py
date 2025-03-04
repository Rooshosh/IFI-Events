"""Database session management with context support."""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
import os
from pathlib import Path

from .model import Base

# Database configuration
DB_PATH = Path(__file__).parent.parent.parent / 'events.db'

def get_db_url():
    """Get database URL based on environment."""
    # Check if we're in test environment
    if os.environ.get('TESTING') == 'true':
        return "sqlite:///:memory:"
    
    # Check if we're using PostgreSQL (Docker environment)
    if os.environ.get('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    
    # Default to SQLite for local development
    return f"sqlite:///{DB_PATH}"

class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.engine = None
        self.session_factory = sessionmaker()
        self.Session = scoped_session(self.session_factory)
    
    def init_app(self, app=None):
        """Initialize database with Flask app (optional)."""
        self.setup_engine()
        if app:
            # Ensure db session is removed when the request ends
            @app.teardown_appcontext
            def shutdown_session(exception=None):
                self.Session.remove()
    
    def setup_engine(self):
        """Set up SQLAlchemy engine."""
        if not self.engine:
            db_url = get_db_url()
            connect_args = {}
            
            # Add SQLite-specific arguments if using SQLite
            if db_url.startswith('sqlite'):
                connect_args = {
                    "check_same_thread": False,
                    "detect_types": 3
                }
            
            self.engine = create_engine(
                db_url,
                echo=False,
                connect_args=connect_args,
                poolclass=StaticPool if db_url.startswith('sqlite') else None
            )
            self.session_factory.configure(bind=self.engine)
    
    def init_db(self):
        """Initialize database, creating all tables."""
        self.setup_engine()
        # Import models to ensure they're registered
        from ..models.event import Event  # noqa
        Base.metadata.create_all(self.engine)
    
    @contextmanager
    def session(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session(self):
        """Get a new database session (for compatibility with existing code)."""
        if not self.Session.registry.has():
            self.Session.configure(bind=self.engine)
        return self.Session()
    
    def close_session(self):
        """Remove the current session (for compatibility with existing code)."""
        self.Session.remove()
    
    def cleanup_test_db(self):
        """Clean up test database. Only for test environment."""
        if os.environ.get('TESTING') == 'true':
            self.Session.remove()
            Base.metadata.drop_all(self.engine)
            self.engine = None
            self.setup_engine()
            Base.metadata.create_all(self.engine)
        else:
            raise RuntimeError("cleanup_test_db() should only be called in test environment")

# Create global instance
db_manager = DatabaseManager() 