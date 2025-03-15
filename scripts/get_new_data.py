#!/usr/bin/env python3
"""Script to fetch and store new events from various sources."""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src to Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.source_manager import SourceManager
from src.config.data_sources import get_enabled_sources
from src.new_event_handler import process_new_events

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# TODO: Verify functionality after changing flow logic
## Explanation: moved process_new_events() to this file instead of source_manager.py


def main():
    """Fetch and store events from all configured sources sequentially."""
    try:
        # Get enabled sources
        enabled_sources = get_enabled_sources()
        if not enabled_sources:
            logger.warning("No enabled sources found")
            return
            
        logger.info(f"Processing {len(enabled_sources)} enabled sources")
        
        # Process each source sequentially
        total_new = 0
        total_updated = 0
        
        for source_id, registration in enabled_sources.items():
            logger.info(f"Processing source: {source_id}")
            
            # Fetch events from the source
            events = SourceManager.fetch_and_parse_single_source(source_id, registration)
            if not events:
                logger.info(f"No events found from source: {source_id}")
                continue
                
            # Process the events
            new_count, updated_count = process_new_events(events, source_id)
            
            total_new += new_count
            total_updated += updated_count
            
            logger.info(f"Completed source {source_id}: {new_count} new, {updated_count} updated")
        
        logger.info(f"Completed all sources. Total: {total_new} new, {total_updated} updated")
        
    except Exception as e:
        logger.error(f"Error in main process: {e}")
        raise

if __name__ == "__main__":
    main() 