"""Core database functionality and configuration.

This module provides a clean, modern implementation of database management
with proper configuration, connection pooling, and session handling.
"""

from contextlib import contextmanager
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Generator
import os

from sqlalchemy import create_engine, Engine, inspect
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from ..models import Base
from ..models.event import Event  # noqa
from ..models.raw_scrape_data import RawScrapeData  # noqa
from ..config.environment import IS_PRODUCTION_ENVIRONMENT

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration settings."""
    
    def __init__(
        self,
        sqlite_path: Optional[Path] = None,
        postgres_url: Optional[str] = None,
        echo: bool = False,
        pool_size: int = 3,
        max_overflow: int = 4,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True
    ):
        """
        Initialize database configuration.

        In production environment, DATABASE_URL must be set in environment variables
        or provided explicitly via postgres_url parameter.

        Args:
            sqlite_path: Path to SQLite database file (for development)
            postgres_url: PostgreSQL connection URL (for production)
                        If not provided, will use DATABASE_URL env variable
            echo: Whether to echo SQL statements
            pool_size: Size of the connection pool (permanent connections)
            max_overflow: Maximum number of extra connections to allow temporarily
                        (total connections = pool_size + max_overflow)
            pool_timeout: Seconds to wait for an available connection
            pool_recycle: Seconds before connections are recycled (prevent stale)
            pool_pre_ping: Whether to ping connections before using them
                         (helps prevent using stale connections)

        Raises:
            ValueError: If in production environment and no database URL is provided
                      either via postgres_url parameter or DATABASE_URL env variable
        """
        # Handle database URLs based on environment
        if IS_PRODUCTION_ENVIRONMENT:
            # For production, get URL from parameter or env variable
            self.postgres_url = postgres_url or os.environ.get('DATABASE_URL')
            if not self.postgres_url:
                raise ValueError(
                    "Database URL must be provided either via postgres_url parameter "
                    "or DATABASE_URL environment variable when in production environment"
                )
            self.sqlite_path = None
        else:
            # For development, handle SQLite path
            self.postgres_url = None
            self.sqlite_path = sqlite_path or Path(__file__).parent.parent.parent / 'data' / 'events.db'
        
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
    
    @property
    def connection_url(self) -> str:
        """Get the database connection URL based on environment."""
        if not IS_PRODUCTION_ENVIRONMENT:
            if not self.sqlite_path:
                raise ValueError("SQLite path not configured")
            return f"sqlite:///{self.sqlite_path}"
        else:
            if not self.postgres_url:
                raise ValueError("PostgreSQL URL not configured")
            return self.postgres_url
    
    def get_engine_args(self) -> Dict[str, Any]:
        """Get SQLAlchemy engine arguments based on configuration."""
        args = {"echo": self.echo}
        
        # SQLite-specific configuration
        if not IS_PRODUCTION_ENVIRONMENT:
            args["connect_args"] = {
                "check_same_thread": False,
                "detect_types": 3
            }
            args["poolclass"] = StaticPool
        
        # PostgreSQL-specific configuration
        else:
            args.update({
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
                "pool_pre_ping": self.pool_pre_ping
            })
        
        return args

class DatabaseError(Exception):
    """Base exception for database-related errors."""
    pass

class ConnectionError(DatabaseError):
    """Raised when there are issues connecting to the database."""
    pass

class SessionError(DatabaseError):
    """Raised when there are issues with database sessions."""
    pass

class Database:
    """Core database management class implementing the singleton pattern."""
    
    _instance = None
    _tables_checked = False
    
    def __new__(cls, config: Optional[DatabaseConfig] = None):
        """Ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """Initialize the database manager if not already initialized."""
        if self._initialized:
            return
        
        self.config = config or DatabaseConfig()
        self.engine: Optional[Engine] = None
        self._session_factory = sessionmaker()
        self._scoped_session = scoped_session(self._session_factory)
        self._initialized = True
        
        # Initialize engine on creation
        self._setup_engine()
    
    def _setup_engine(self) -> None:
        """Set up the SQLAlchemy engine."""
        try:
            self.engine = create_engine(
                self.config.connection_url,
                **self.config.get_engine_args()
            )
            self._session_factory.configure(bind=self.engine)
        except Exception as e:
            raise ConnectionError(f"Failed to create database engine: {e}") from e
    
    def init_db(self) -> None:
        """Initialize the database schema."""
        if not self.engine:
            raise ConnectionError("Database engine not initialized")
        
        try:
            # Create all tables
            with self.engine.connect() as conn:
                Base.metadata.create_all(conn)
            logger.info("Database schema initialized successfully")
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database schema: {e}") from e
    
    def ensure_tables_exist(self) -> None:
        """Ensure all required database tables exist."""
        if not self._tables_checked:
            if not self.engine:
                raise ConnectionError("Database engine not initialized")
            
            try:
                inspector = inspect(self.engine)
                existing_tables = inspector.get_table_names()
                required_tables = {table.__tablename__ for table in Base.__subclasses__()}
                
                if not all(table in existing_tables for table in required_tables):
                    logger.info("Some tables missing, initializing database schema")
                    with self.engine.connect() as conn:
                        Base.metadata.create_all(conn)
                    logger.info("Database schema initialized successfully")
                
                self._tables_checked = True
                
            except Exception as e:
                raise DatabaseError(f"Failed to verify/create database schema: {e}") from e
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        
        This is the preferred way to get a database session. It handles
        commit/rollback automatically and ensures proper cleanup.
        
        Example:
            with db.session() as session:
                user = session.query(User).first()
                user.name = "New Name"
                # No need to call commit - it's handled automatically
        
        Raises:
            SessionError: If there are issues with the session
            DatabaseError: If database schema verification fails
        """
        # Ensure tables exist before providing a session
        self.ensure_tables_exist()
        
        session = self._scoped_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise SessionError(f"Database session error: {e}") from e
        finally:
            session.close()
            self._scoped_session.remove()

# Create the global database instance with default configuration
db = Database() 