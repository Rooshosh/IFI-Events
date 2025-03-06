#!/usr/bin/env python3
"""Script to fetch and store new events from all configured sources."""

import logging
import sys
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.source_manager import SourceManager
from src.handlers.new_event_handler import NewEventHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Fetch and store events from all configured sources."""
    try:
        # Create source manager and get events first
        logger.info("Fetching events from all sources...")
        manager = SourceManager()
        events = manager.get_all_events()
        logger.info(f"Found {len(events)} events from all sources")
        
        # Process events using the handler
        handler = NewEventHandler(skip_merging=True)  # Skip merging for now
        new_count, updated_count = handler.process_new_events(events, "all_sources")
        
        logger.info(f"Successfully processed events ({new_count} new, {updated_count} updated)")
        
    except Exception as e:
        logger.error(f"Error fetching or storing events: {e}")
        raise

if __name__ == "__main__":
    main() 