import logging
from typing import List, Optional
import requests
from datetime import datetime
from ..models.event import Event

logger = logging.getLogger(__name__)

class EventAPIClient:
    """Client for fetching events from the API."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def get_events(self) -> List[Event]:
        """
        Fetch events from the API and convert them to Event objects.
        
        Returns:
            List[Event]: List of Event objects
            
        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the API response is invalid
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/events",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            events_data = response.json()
            if not isinstance(events_data, list):
                raise ValueError("API response must be a list of events")
            
            return [self._convert_to_event(event) for event in events_data]
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch events from API: {e}")
            raise
    
    def _convert_to_event(self, data: dict) -> Event:
        """
        Convert API event data to an Event object.
        
        Args:
            data: Dictionary containing event data from the API
            
        Returns:
            Event: Event object
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Ensure required fields are present
        required_fields = ['title', 'start_time']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Convert datetime strings to datetime objects
        datetime_fields = ['start_time', 'end_time', 'registration_opens', 'created_at', 'fetched_at']
        for field in datetime_fields:
            if field in data and data[field]:
                try:
                    data[field] = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                except ValueError as e:
                    logger.warning(f"Invalid datetime format for {field}: {e}")
                    data[field] = None
        
        # Create Event object
        return Event(
            id=data.get('id'),
            title=data['title'],
            description=data.get('description'),
            start_time=data['start_time'],
            end_time=data.get('end_time'),
            location=data.get('location'),
            source_url=data.get('source_url'),
            source_name=data.get('source_name'),
            created_at=data.get('created_at'),
            fetched_at=data.get('fetched_at'),
            capacity=data.get('capacity'),
            spots_left=data.get('spots_left'),
            registration_opens=data.get('registration_opens'),
            registration_url=data.get('registration_url'),
            food=data.get('food'),
            attachment=data.get('attachment'),
            author=data.get('author')
        ) 