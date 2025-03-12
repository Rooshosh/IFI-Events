"""Database operations and utilities.

This module provides common database operations and utilities,
including retry logic for transient failures.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from sqlalchemy.exc import OperationalError, IntegrityError

from .db_core import db, DatabaseError, SessionError

logger = logging.getLogger(__name__)

# Type variable for generic return type
T = TypeVar('T')

def with_retry(
    max_attempts: int = 3,
    delay: float = 0.1,
    backoff: float = 2,
    exceptions: tuple = (OperationalError,)
) -> Callable:
    """
    Decorator that implements retry logic for database operations.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay between retries
        exceptions: Tuple of exceptions to catch and retry
    
    Example:
        @with_retry(max_attempts=3)
        def get_user(user_id: int) -> User:
            with db.session() as session:
                return session.query(User).get(user_id)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return cast(T, func(*args, **kwargs))
                except exceptions as e:
                    last_exception = e
                    if attempt + 1 == max_attempts:
                        logger.error(
                            f"Final attempt failed for {func.__name__}: {str(e)}"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for "
                        f"{func.__name__}: {str(e)}. Retrying in {current_delay}s..."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # This should never happen due to the raise in the loop
            raise last_exception or DatabaseError("Unknown error in retry logic")
        
        return wrapper
    return decorator

@with_retry()
def execute_in_transaction(operation: Callable[[Any], T], *args: Any, **kwargs: Any) -> T:
    """
    Execute a database operation within a transaction with retry logic.
    
    Args:
        operation: Callable that performs the database operation
        *args: Positional arguments to pass to the operation
        **kwargs: Keyword arguments to pass to the operation
    
    Returns:
        The result of the operation
    
    Example:
        def update_user(session, user_id: int, name: str):
            user = session.query(User).get(user_id)
            user.name = name
            return user
        
        updated_user = execute_in_transaction(
            update_user, user_id=123, name="New Name"
        )
    """
    with db.session() as session:
        try:
            result = operation(session, *args, **kwargs)
            return result
        except IntegrityError as e:
            raise DatabaseError(f"Integrity error in transaction: {e}") from e
        except Exception as e:
            raise SessionError(f"Error executing transaction: {e}") from e 