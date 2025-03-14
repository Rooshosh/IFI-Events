import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.web.api import EventAPIClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_connection():
    """Test basic API connection and data retrieval."""
    client = EventAPIClient(
        base_url="https://ifi-events-data-service.up.railway.app",
        timeout=30
    )
    
    try:
        # Test events endpoint
        events = client.get_events()
        logger.info(f"Successfully retrieved {len(events)} events")
        
        # Print first event details if available
        if events:
            event = events[0]
            logger.info("\nFirst event details:")
            logger.info(f"Title: {event.title}")
            logger.info(f"Start time: {event.start_time}")
            logger.info(f"Location: {event.location}")
            logger.info(f"Description: {event.description[:100]}...")  # First 100 chars
        else:
            logger.warning("No events returned from API")
            
    except Exception as e:
        logger.error(f"Error testing API: {e}")
        raise

if __name__ == "__main__":
    test_api_connection() 