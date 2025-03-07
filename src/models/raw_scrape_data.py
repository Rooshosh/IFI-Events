"""Raw scrape data model for storing webhook responses."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship

from .base import Base
from ..utils.timezone import ensure_oslo_timezone, now_oslo

class RawScrapeData(Base):
    """
    Model for storing raw data received from scrapers via webhooks.
    
    This model stores the complete data received from webhook endpoints
    along with its processing status. The data can be processed either
    immediately when received or later in a separate step.
    
    Fields:
        id: Unique identifier (auto-generated)
        source: Source of the data (e.g., 'brightdata_facebook_group')
        raw_data: Complete JSON response as received from the webhook
        created_at: When the data was received from the webhook
        processed: Whether the data has been processed (true/false)
        processed_at: When the data was processed (null if not processed)
        processing_status: Status of processing (e.g., 'success', 'not_an_event', 'failed', 'pending')
    """
    __tablename__ = 'raw_scrape_data'
    
    # Required fields
    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    raw_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_oslo)
    
    # Processing status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_status = Column(String, default='pending')
    
    def __init__(self, **kwargs):
        """Initialize RawScrapeData with the given attributes."""
        # Ensure timezone-aware datetimes
        for field in ['created_at', 'processed_at']:
            if field in kwargs and kwargs[field] is not None:
                kwargs[field] = ensure_oslo_timezone(kwargs[field])
        
        super().__init__(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'source': self.source,
            'raw_data': self.raw_data,
            'created_at': self.created_at,
            'processed': self.processed,
            'processed_at': self.processed_at,
            'processing_status': self.processing_status
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"RawScrapeData(id={self.id}, source={self.source}, processed={self.processed})" 