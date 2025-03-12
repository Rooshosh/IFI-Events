"""Database package initialization.

This module exposes the public interface of the database package.
"""

from .db_core import (
    Database,
    DatabaseConfig,
    DatabaseError,
    ConnectionError,
    SessionError,
    db
)
from .operations import with_retry, execute_in_transaction

__all__ = [
    # Core database classes
    'Database',
    'DatabaseConfig',
    
    # Exceptions
    'DatabaseError',
    'ConnectionError',
    'SessionError',
    
    # Global instance
    'db',
    
    # Utilities
    'with_retry',
    'execute_in_transaction',
] 