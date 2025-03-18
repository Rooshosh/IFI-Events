#!/usr/bin/env python3
"""Helper script to process cross-source duplicates in the existing database."""

import logging
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.models.event import Event
from src.db import db
from src.utils.deduplication import are_events_cross_source_duplicate
from src.config.data_sources import compare_source_priorities

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_cross_source_duplicate(event1: Event, event2: Event, session):
    """
    Process a duplicate event from another source by comparing source priorities.
    """
    higher_priority_event, lower_priority_event = compare_source_priority(event1, event2)
    
    # Find the topmost parent
    topmost_parent = higher_priority_event
    while topmost_parent.parent_id is not None:
        topmost_parent = session.query(Event).get(topmost_parent.parent_id)
    
    # Assign the topmost parent to the lower priority event
    lower_priority_event.parent_id = topmost_parent.id
    logger.info(
        f"Found duplicate events:\n"
        f"  Parent: {topmost_parent.title} (source: {topmost_parent.source_name}, id: {topmost_parent.id})\n"
        f"  Child:  {lower_priority_event.title} (source: {lower_priority_event.source_name}, id: {lower_priority_event.id})"
    )


def compare_source_priority(event1: Event, event2: Event):
    """
    Compare the priority of two event sources and return them in order of priority.
    """
    comparison = compare_source_priorities(event1.source_name, event2.source_name)
    return (event1, event2) if comparison >= 0 else (event2, event1)


def process_existing_events():
    """Process all existing events to find and handle cross-source duplicates."""
    try:
        with db.session() as session:
            # Get all events
            events = session.query(Event).all()
            total_events = len(events)
            logger.info(f"Processing {total_events} events...")
            
            processed_count = 0
            parent_set_count = 0
            
            for i, event in enumerate(events, 1):
                if i % 100 == 0:
                    logger.info(f"Processed {i}/{total_events} events...")
                
                # Skip events that already have a parent
                if event.parent_id is not None:
                    processed_count += 1
                    continue
                
                # Check against all other events
                for other_event in events:
                    if other_event.id == event.id:
                        continue
                        
                    if are_events_cross_source_duplicate(event, other_event):
                        process_cross_source_duplicate(event, other_event, session)
                        parent_set_count += 1
                
                processed_count += 1
            
            logger.info(f"Finished processing {processed_count} events")
            logger.info(f"Set parent_id for {parent_set_count} events")
            
    except Exception as e:
        logger.error(f"Error processing events: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    process_existing_events() 