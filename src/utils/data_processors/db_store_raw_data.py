"""Handler for storing raw data in the database.

This module provides functions for storing raw scrape data in the database.
Database initialization is handled automatically when using these functions.
Tables will be created if they don't exist.

Currently, only batch storage is implemented and used. Single entry storage
is reserved for future implementation if needed.

For FastAPI app:
    - Tables are checked/created when the app starts
    - These functions will work seamlessly

For standalone scripts:
    - Tables are checked/created on first database operation
    - No explicit initialization needed
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.models.raw_scrape_data import RawScrapeData
from src.db import db, DatabaseError, with_retry

logger = logging.getLogger(__name__)

@with_retry()
def db_store_raw_data(
    source: str,
    raw_data: Dict[str, Any],
    processing_status: str = 'pending',
    processed: bool = False,
    created_at: Optional[datetime] = None
) -> int:
    """
    [NOT IMPLEMENTED] Store a single raw data entry in the database.
    
    This method is reserved for future implementation if single-entry
    storage becomes necessary. Currently, all data storage is handled
    through the store_batch function.
    
    Args:
        source: Source of the raw data (e.g., 'brightdata_facebook_group')
        raw_data: The raw data to store
        processing_status: Status of processing ('pending', 'success', 'failed', 'not_an_event')
        processed: Whether the data has been processed
        created_at: The creation date of the raw data
        
    Raises:
        NotImplementedError: This method is not currently implemented
    """
    raise NotImplementedError(
        "Single entry storage is not implemented. "
        "Use store_batch() for storing raw data entries."
    )

@with_retry()
def db_store_batch(
    source: str,
    entries: List[Dict[str, Any]]
) -> List[int]:
    """
    Store multiple raw data entries in a single transaction with retry logic.
    
    Args:
        source: Name of the data source
        entries: List of dictionaries containing raw_data, processing_status, and created_at
        
    Returns:
        List[int]: List of IDs of stored entries
    """
    stored_ids = []
    
    try:
        with db.session() as session:
            for entry in entries:
                raw_data_entry = RawScrapeData(
                    source=source,
                    raw_data=entry['raw_data'],
                    processing_status=entry.get('processing_status', 'pending'),
                    created_at=entry.get('created_at') or datetime.now(timezone.utc),
                    processed=False
                )
                session.add(raw_data_entry)
                stored_ids.append(raw_data_entry.id)
            
            # All entries will be committed in a single transaction
        
        logger.info(f"Successfully stored {len(stored_ids)} entries in batch")
        return stored_ids
        
    except Exception as e:
        logger.error(f"Failed to store batch: {str(e)}")
        raise DatabaseError(f"Failed to store batch: {str(e)}") from e 