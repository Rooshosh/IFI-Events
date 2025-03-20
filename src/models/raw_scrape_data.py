"""Model for storing scraped posts and their event status."""

from datetime import datetime
from typing import Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, BigInteger

from .base import Base
from ..utils.timezone import ensure_oslo_timezone, now_oslo

class ScrapedPost(Base):
    """
    Model for storing scraped posts and their event status.
    
    This model stores information about posts that have been scraped,
    including their URL and whether they were determined to be about events.
    
    Fields:
        id: Unique identifier (auto-generated)
        post_url: URL of the scraped post
        event_status: Status indicating if the post is about an event
                     ('contains-event', 'is-event-llm', 'not-event-llm')
        scraped_at: When the post was scraped
    """
    __tablename__ = 'scraped_posts'
    
    # Required fields
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    post_url = Column(String, nullable=False, unique=True)
    event_status = Column(String, nullable=False)
    scraped_at = Column(DateTime(timezone=True), default=now_oslo)
    
    def __init__(self, **kwargs):
        """Initialize ScrapedPost with the given attributes."""
        # Ensure timezone-aware datetimes
        if 'scraped_at' in kwargs and kwargs['scraped_at'] is not None:
            kwargs['scraped_at'] = ensure_oslo_timezone(kwargs['scraped_at'])
        
        super().__init__(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'post_url': self.post_url,
            'event_status': self.event_status,
            'scraped_at': self.scraped_at
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"ScrapedPost(id={self.id}, post_url={self.post_url}, event_status={self.event_status})" 