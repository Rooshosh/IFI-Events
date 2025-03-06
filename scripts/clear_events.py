#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.db import db_manager
from src.models.event import Event

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_all_events():
    """Clear all events from the database"""
    # Initialize database
    db_manager.init_db()
    
    with db_manager.session() as db:
        # Delete all events
        count = db.query(Event).delete()
        logger.info(f"Cleared {count} events from database")

if __name__ == "__main__":
    clear_all_events() 