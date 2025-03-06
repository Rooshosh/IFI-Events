"""Raw scrape data model for storing webhook responses."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from ..db.model import Base
from ..utils.timezone import ensure_oslo_timezone, now_oslo

class RawScrapeData(Base):
    """
    Model for storing raw data received from scrapers via webhooks.
    
    This model stores the complete, unmodified data as received from 
    webhook endpoints for later processing. The data is stored as JSON
    and can be processed asynchronously.
    
    Fields:
        id: Unique identifier (auto-generated)
        source: Source of the data (e.g., 'facebook', 'brightdata')
        raw_data: Complete JSON response as received
        created_at: When the data was received
        processed: Whether the data has been processed
        processed_at: When the data was processed (if it has been)
        processing_status: Status of processing (e.g., 'pending', 'success', 'failed')
        event_id: Foreign key to related Event (if any)
    """
    __tablename__ = 'raw_scrape_data'
    
    # Required fields
    id = Column(Integer, primary_key=True)
    source = Column(String, nullable=False)
    raw_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_oslo)
    
    # Processing status
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime(timezone=True))
    processing_status = Column(String, default='pending')
    
    # Relationship to Event (optional)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=True)
    event = relationship("Event", backref="raw_data_sources")
    
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
            'processing_status': self.processing_status,
            'event_id': self.event_id
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"RawScrapeData(id={self.id}, source={self.source}, processed={self.processed})" 