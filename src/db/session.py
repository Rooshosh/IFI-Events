"""Database session management with context support."""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
import os
from pathlib import Path

from .model import Base

# Database configuration
DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'events.db'

def get_db_url():
    """Get database URL based on environment."""
    # Check if we're in test environment
    if os.environ.get('TESTING') == 'true':
        return "sqlite:///:memory:"
    
    # Get environment setting, default to production if not set
    environment = os.environ.get('ENVIRONMENT', 'production').strip()
    
    if environment.lower() == 'development':
        # Use SQLite for development
        return f"sqlite:///{DB_PATH}"
    elif environment.lower() == 'production':
        # Production mode - use PostgreSQL
        if not os.environ.get('DATABASE_URL'):
            raise ValueError("DATABASE_URL environment variable is required for production mode")
        return os.environ['DATABASE_URL']
    else:
        raise ValueError(f"Invalid environment setting: {environment}. Must be 'development' or 'production'")

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
        from ..models.raw_scrape_data import RawScrapeData  # noqa
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

# Compatibility functions for simpler database access
def init_db():
    """Initialize database, creating all tables."""
    db_manager.init_db()

def get_db():
    """Get a new database session."""
    return db_manager.get_session()

def close_db():
    """Remove the current session."""
    db_manager.close_session()

def cleanup_test_db():
    """Clean up test database. Should only be called in test environment."""
    db_manager.cleanup_test_db() 