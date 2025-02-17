from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

def ensure_timezone(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware, converting to UTC if it isn't"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt

@dataclass
class Event:
    """Data class for events to ensure consistent handling"""
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    source_url: Optional[str]
    source_name: Optional[str]
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    # New fields
    capacity: Optional[int] = None  # Total number of spots available
    spots_left: Optional[int] = None  # Number of spots still available
    registration_opens: Optional[datetime] = None  # When registration opens
    registration_url: Optional[str] = None  # URL for registration if different from source_url
    food: Optional[str] = None  # Description of food/refreshments if provided
    
    def __post_init__(self):
        """Ensure all datetime fields are timezone-aware"""
        self.start_time = ensure_timezone(self.start_time)
        self.end_time = ensure_timezone(self.end_time) if self.end_time else None
        self.created_at = ensure_timezone(self.created_at) if self.created_at else None
        self.registration_opens = ensure_timezone(self.registration_opens) if self.registration_opens else None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create an Event from a dictionary"""
        return cls(
            title=data['title'],
            description=data['description'],
            start_time=ensure_timezone(data['start_time']),
            end_time=ensure_timezone(data['end_time']) if data['end_time'] else None,
            location=data.get('location'),
            source_url=data.get('source_url'),
            source_name=data.get('source_name'),
            id=data.get('id'),
            created_at=ensure_timezone(data['created_at']) if data.get('created_at') else None,
            capacity=data.get('capacity'),
            spots_left=data.get('spots_left'),
            registration_opens=ensure_timezone(data['registration_opens']) if data.get('registration_opens') else None,
            registration_url=data.get('registration_url'),
            food=data.get('food')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Event to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'location': self.location,
            'source_url': self.source_url,
            'source_name': self.source_name,
            'created_at': self.created_at,
            'capacity': self.capacity,
            'spots_left': self.spots_left,
            'registration_opens': self.registration_opens,
            'registration_url': self.registration_url,
            'food': self.food
        } 