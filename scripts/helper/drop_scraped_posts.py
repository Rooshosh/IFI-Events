#!/usr/bin/env python3
"""Helper script to drop the scraped_posts table."""

import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.db import db
from sqlalchemy import text

def drop_scraped_posts():
    """Drop the scraped_posts table."""
    try:
        with db.session() as session:
            # Drop the table
            session.execute(text('DROP TABLE IF EXISTS scraped_posts'))
            session.commit()
            logger.info("Successfully dropped scraped_posts table")
    except Exception as e:
        logger.error(f"Error dropping scraped_posts table: {e}")
        raise

if __name__ == '__main__':
    drop_scraped_posts() 