"""Handler for processing new event data from scrapers."""

import logging
from typing import List, Optional, Tuple
from datetime import datetime

from .models.event import Event
from .db.database_manager import DatabaseManager, init_db
from .utils.deduplication import (
    check_duplicate_before_insert,
    DuplicateConfig,
    merge_events,
    are_events_duplicate
)

logger = logging.getLogger(__name__)

class NewEventHandler:
    """
    Handles new event data from scrapers.
    
    This class is responsible for:
    1. Processing new events from scrapers
    2. Checking for duplicates in the database (if enabled)
    3. Merging duplicate events (if enabled)
    4. Updating existing events or inserting new ones
    """
    
    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        config: Optional[DuplicateConfig] = None,
        skip_merging: bool = False
    ):
        """
        Initialize the handler.
        
        Args:
            db_manager: Optional database manager instance. If not provided,
                       a new one will be created.
            config: Optional configuration for duplicate detection. If not provided,
                   default settings will be used.
            skip_merging: If True, all events will be inserted as new entries without
                        checking for duplicates or merging.
        """
        # Initialize database first
        init_db()
        
        # Then set up the handler
        # TODO: leave db setup to db manager ?
        # -- shold only need to invokate a single db manager method, right ?
        self.db_manager = db_manager or DatabaseManager()
        self.db_manager.setup_engine()  # Ensure engine is set up
        self.config = config or DuplicateConfig()
        self.skip_merging = skip_merging
    
    def process_new_events(self, events: List[Event], source_name: str) -> Tuple[int, int]:
        """
        Process new events from a scraper.
        
        For each event:
        1. If skip_merging is True:
           - Insert event as new entry
        2. If skip_merging is False:
           - Check if it's a duplicate of an existing event
           - If duplicate, merge and update the existing event
           - If new, insert it into the database
        
        Args:
            events: List of new events from a scraper
            source_name: Name of the source (e.g., "Peoply", "ifinavet.no")
            
        Returns:
            Tuple of (new_events_count, updated_events_count)
        """
        new_count = 0
        updated_count = 0
        
        with self.db_manager.session() as db:
            for event in events:
                try:
                    if self.skip_merging:
                        # Skip deduplication/merging, insert all events as new
                        db.add(event)
                        new_count += 1
                        logger.debug(f"Added new event (merging disabled): {event.title}")
                    else:
                        # Check for duplicates
                        duplicate = check_duplicate_before_insert(event, self.config)
                        if duplicate:
                            # Merge and update existing event
                            merged_event = merge_events(duplicate, event)
                            self._update_existing_event(db, merged_event)
                            updated_count += 1
                            logger.debug(f"Updated existing event: {event.title}")
                        else:
                            # Insert new event
                            db.add(event)
                            new_count += 1
                            logger.debug(f"Added new event: {event.title}")
                except Exception as e:
                    logger.error(f"Error processing event {event.title}: {e}")
                    continue
        
        logger.info(f"Processed {len(events)} events from {source_name} "
                   f"({new_count} new, {updated_count} updated)"
                   + (" (merging disabled)" if self.skip_merging else ""))
        
        return new_count, updated_count
    
    def _update_existing_event(self, db, event: Event) -> None:
        """
        Update an existing event in the database.
        
        This method:
        1. Updates the fetched_at timestamp
        2. Merges the event into the database
        
        Args:
            db: Database session
            event: Event to update
        """
        # Update fetched_at timestamp
        event.fetched_at = datetime.now()
        
        # Merge changes into database
        db.merge(event) 