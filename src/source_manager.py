"""
Central manager for event sources and their scrapers.

This module provides the SourceManager class which coordinates all event sources in the system.
It serves as the top-level coordinator for:
1. Loading and managing event sources from configuration
2. Initializing scrapers for enabled sources
3. Coordinating event fetching across all enabled sources

The manager uses the registry in sources.py to determine what scrapers exist
and which ones are enabled, then dynamically loads and manages them.
This allows scrapers to be added or removed by just updating the registry,
without needing to modify the manager itself.

When run directly, this module will fetch and print events from all enabled sources.
"""

import importlib
import logging
import sys
from pathlib import Path
from typing import List, Type, Dict
from datetime import datetime

# Add src to Python path when running directly
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent))

# Now we can use absolute imports
from src.models.event import Event
from src.scrapers.base import BaseScraper
from src.config.sources import get_enabled_sources, ScraperRegistration

logger = logging.getLogger(__name__)

class SourceManager:
    """
    Central manager for all event scrapers.
    
    This class is responsible for:
    1. Loading and initializing scrapers from their registration
    2. Managing which scrapers are enabled/disabled
    3. Coordinating event fetching from all enabled scrapers
    
    Each scraper is loaded dynamically from its registration in sources.py,
    allowing scrapers to be added or removed without modifying this class.
    """
    
    @staticmethod
    def get_scraper_class(registration: ScraperRegistration) -> Type[BaseScraper]:
        """
        Dynamically import and return a scraper class from its registration.
        
        Args:
            registration: Registration info for the scraper, including its class path
                        Example path: 'src.scrapers.peoply.PeoplyScraper'
        
        Returns:
            Type[BaseScraper]: The scraper class (not instance)
        
        Raises:
            ImportError: If the module cannot be imported
            AttributeError: If the class doesn't exist in the module
        """
        try:
            module_path, class_name = registration.scraper_class.rsplit('.', 1)
            module = importlib.import_module(module_path)
            scraper_class = getattr(module, class_name)
            
            # Verify the class implements the BaseScraper interface
            if not issubclass(scraper_class, BaseScraper):
                raise TypeError(f"Scraper class {class_name} must implement BaseScraper interface")
                
            return scraper_class
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load scraper class {registration.scraper_class}: {e}")
            raise
    
    @staticmethod
    def get_events_from_source(source_id: str, registration: ScraperRegistration) -> List[Event]:
        """
        Get events from a single source.
        
        Args:
            source_id: Identifier for the source (for logging)
            registration: Registration info for the scraper
        
        Returns:
            List[Event]: List of events from the source, or empty list if failed
        """
        try:
            scraper_class = SourceManager.get_scraper_class(registration)
            scraper = scraper_class()
            logger.info(f"Fetching events from {scraper.name()}")
            events = scraper.get_events()
            logger.info(f"Found {len(events)} events from {scraper.name()}")
            return events
        except Exception as e:
            logger.error(f"Error fetching events from {source_id}: {e}")
            return []
    
    @staticmethod
    def get_all_events() -> List[Event]:
        """
        Get events from all enabled scrapers.
        
        This method:
        1. Gets the list of enabled scrapers from the registry
        2. Initializes each enabled scraper
        3. Fetches events from each scraper
        4. Combines all events into a single list
        
        Returns:
            List[Event]: Combined list of events from all enabled scrapers
        """
        all_events = []
        enabled_sources = get_enabled_sources()
        logger.info(f"Fetching events from {len(enabled_sources)} enabled scrapers")
        
        for source_id, registration in enabled_sources.items():
            try:
                events = SourceManager.get_events_from_source(source_id, registration)
                all_events.extend(events)
            except Exception as e:
                logger.error(f"Failed to get events from {source_id}: {e}")
        
        logger.info(f"Found total of {len(all_events)} events from all sources")
        return all_events

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create manager and get events
    manager = SourceManager()
    events = manager.get_all_events()
    
    # Sort events by start time
    events.sort(key=lambda e: e.start_time)
    
    # Print results
    print(f"\nFound {len(events)} events from enabled sources:\n")
    
    for i, event in enumerate(events, 1):
        print(f"\n--- Event {i}/{len(events)} ---")
        print(event.to_detailed_string())
        print("-" * 40) 