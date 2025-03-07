#!/usr/bin/env python3

import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.db.database import init_db, get_db, close_db
from src.source_manager import SourceManager
from src.utils.deduplication import check_duplicate_before_insert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Update events in database from all enabled sources"""
    # Initialize database
    init_db()
    db = get_db()
    
    try:
        # Initialize source manager
        manager = SourceManager()
        
        # Fetch and store events from each enabled source
        total_new = 0
        total_merged = 0
        
        # Get events from all enabled sources
        events = manager.get_all_events()
        
        # Store events in database with deduplication
        for event in events:
            try:
                # Check for duplicates
                duplicate = check_duplicate_before_insert(event)
                if duplicate:
                    # Use the merged event instead
                    db.merge(duplicate)
                    total_merged += 1
                else:
                    # Add new event
                    db.add(event)
                    total_new += 1
            except Exception as e:
                logger.error(f"Error storing event {event.title}: {e}")
                continue
        
        # Commit all changes
        db.commit()
        logger.info(f"Successfully updated all events "
                   f"({total_new} new, {total_merged} merged)")
    
    finally:
        # Always close the database session
        close_db()

if __name__ == "__main__":
    main() 