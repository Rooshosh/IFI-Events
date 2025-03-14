"""Event model definition."""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass

@dataclass
class Event:
    """
    Event model representing an event from any source.
    
    Fields:
        id: Unique identifier
        title: Event title
        description: Event description
        start_time: When the event starts
        end_time: When the event ends (optional)
        location: Where the event takes place (optional)
        source_url: URL to the event's source page (optional)
        source_name: Name of the source (e.g., 'peoply.app', 'ifinavet.no')
        created_at: When this event was first created in our database
        fetched_at: When this event's data was fetched from the source
        capacity: Total number of spots available (optional)
        spots_left: Number of spots still available (optional)
        registration_opens: When registration opens (optional)
        registration_url: URL for registration if different from source_url (optional)
        food: Description of food/refreshments if provided (optional)
        attachment: URL to the event's primary image/attachment
        author: Name of the student club or person that created the event (optional)
    """
    id: Optional[int]
    title: str
    description: Optional[str] = None
    start_time: datetime = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    created_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    capacity: Optional[int] = None
    spots_left: Optional[int] = None
    registration_opens: Optional[datetime] = None
    registration_url: Optional[str] = None
    food: Optional[str] = None
    attachment: Optional[str] = None
    author: Optional[str] = None 