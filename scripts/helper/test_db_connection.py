#!/usr/bin/env python3
import os
import sys
import logging
from sqlalchemy import create_engine, text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    # Check if DATABASE_URL is set
    postgres_url = os.environ.get('DATABASE_URL')
    if not postgres_url:
        logger.error("DATABASE_URL environment variable is not set")
        return False
    
    logger.info("DATABASE_URL is set")
    
    try:
        # Create engine with a short timeout
        engine = create_engine(
            postgres_url,
            connect_args={
                "connect_timeout": 5,
                "application_name": "test_connection"
            }
        )
        
        # Try to connect and run a simple query
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            logger.info("Successfully connected to database")
            logger.info(f"Test query result: {result}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        return False
    finally:
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1) 