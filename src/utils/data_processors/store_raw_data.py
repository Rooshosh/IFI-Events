"""Handler for storing raw scrape data in the database."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.models.raw_scrape_data import RawScrapeData
from src.db.session import DatabaseManager

logger = logging.getLogger(__name__)

class RawDataHandler:
    """
    Handles storage of raw scrape data in the database.
    
    This class is responsible for:
    1. Storing raw data from scrapers
    2. Adding processing status information
    3. Managing database transactions
    """
    
    def __init__(self, db_manager: DatabaseManager = None):
        """
        Initialize the handler.
        
        Args:
            db_manager: Optional database manager instance. If not provided,
                       a new one will be created.
        """
        self.db_manager = db_manager or DatabaseManager()
        self.db_manager.init_db()
    
    def store_raw_data(
        self,
        source: str,
        raw_data: Dict[str, Any],
        processing_status: str = 'pending',
        processed: bool = False,
        created_at: Optional[datetime] = None
    ) -> Optional[int]:
        """
        Store raw data in the database.
        
        Args:
            source: Source of the raw data (e.g., 'brightdata_facebook_group')
            raw_data: The raw data to store
            processing_status: Status of processing ('pending', 'success', 'failed', 'not_an_event')
            processed: Whether the data has been processed
            created_at: The creation date of the raw data
            
        Returns:
            Optional[int]: ID of the stored entry if successful, None otherwise
        """
        try:
            # Get the post's creation date from raw data if available
            if created_at is None:
                created_at = datetime.now(timezone.utc)
            
            # Create new raw data entry
            raw_data_entry = RawScrapeData(
                source=source,
                raw_data=raw_data,
                created_at=created_at,
                processed=processed,
                processed_at=datetime.now(timezone.utc) if processed else None,
                processing_status=processing_status
            )
            
            # Add to database
            with self.db_manager.session() as db:
                db.add(raw_data_entry)
                db.commit()
            
            logger.info(f"Successfully stored raw data with ID: {raw_data_entry.id}")
            return raw_data_entry.id
            
        except Exception as e:
            logger.error(f"Failed to store entry: {str(e)}")
            if 'db' in locals():
                db.rollback()
            return None
    
    def store_batch(
        self,
        source: str,
        entries: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Store multiple raw data entries in a batch.
        
        Args:
            source: Name of the data source
            entries: List of dictionaries containing raw_data, processing_status, and created_at
            
        Returns:
            List[int]: List of IDs of stored entries
        """
        stored_ids = []
        
        for entry in entries:
            try:
                entry_id = self.store_raw_data(
                    source=source,
                    raw_data=entry['raw_data'],
                    processing_status=entry['processing_status'],
                    created_at=entry.get('created_at')
                )
                if entry_id:
                    stored_ids.append(entry_id)
            except Exception as e:
                logger.error(f"Failed to store entry: {e}")
                continue
        
        return stored_ids 