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
"""

import importlib
import logging
import sys
from pathlib import Path
from typing import List, Type, Dict, Tuple
from datetime import datetime

# Add src to Python path when running directly
if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parent.parent))

# Now we can use absolute imports
from src.models.event import Event
from src.scrapers.base import BaseScraper, SyncScraper, AsyncScraper
from src.config.data_sources import get_enabled_sources, ScraperRegistration

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
    def _get_scraper_type(scraper_class: Type[BaseScraper]) -> str:
        """
        Determine if a scraper is synchronous or asynchronous.
        
        Args:
            scraper_class: The scraper class to check
            
        Returns:
            str: Either 'sync' or 'async'
        """
        if issubclass(scraper_class, AsyncScraper):
            return 'async'
        elif issubclass(scraper_class, SyncScraper):
            return 'sync'
        else:
            raise TypeError(f"Scraper class {scraper_class.__name__} must implement either SyncScraper or AsyncScraper")
    
    @staticmethod
    def _group_scrapers_by_type(enabled_sources: Dict[str, ScraperRegistration]) -> Tuple[List[Tuple[str, ScraperRegistration]], List[Tuple[str, ScraperRegistration]]]:
        """
        Group scrapers by their type (sync or async).
        
        Args:
            enabled_sources: Dictionary of enabled source IDs and their registrations
            
        Returns:
            Tuple containing:
            - List of (source_id, registration) tuples for async scrapers
            - List of (source_id, registration) tuples for sync scrapers
        """
        async_scrapers = []
        sync_scrapers = []
        
        for source_id, registration in enabled_sources.items():
            try:
                scraper_class = SourceManager.get_scraper_class(registration)
                scraper_type = SourceManager._get_scraper_type(scraper_class)
                
                if scraper_type == 'async':
                    async_scrapers.append((source_id, registration))
                else:
                    sync_scrapers.append((source_id, registration))
                    
            except Exception as e:
                logger.error(f"Failed to determine type for scraper {source_id}: {e}")
                continue
        
        return async_scrapers, sync_scrapers
    
    @staticmethod
    def initialize_async_scrapers() -> bool:
        """
        Initialize all asynchronous scrapers.
        
        This method:
        1. Gets the list of enabled scrapers
        2. Identifies async scrapers
        3. Initializes each async scraper
        
        Returns:
            bool: True if all async scrapers were initialized successfully
        """
        enabled_sources = get_enabled_sources()
        async_scrapers, _ = SourceManager._group_scrapers_by_type(enabled_sources)
        
        if not async_scrapers:
            logger.info("No async scrapers to initialize")
            return True
            
        logger.info(f"Initializing {len(async_scrapers)} async scrapers")
        all_success = True
        
        for source_id, registration in async_scrapers:
            try:
                scraper_class = SourceManager.get_scraper_class(registration)
                scraper = scraper_class()
                logger.info(f"Initializing async scraper: {scraper.name()}")
                
                success = scraper.initialize_data_fetch()
                if not success:
                    logger.error(f"Failed to initialize async scraper {source_id}")
                    all_success = False
                    
            except Exception as e:
                logger.error(f"Error initializing async scraper {source_id}: {e}")
                all_success = False
        
        return all_success
    
    @staticmethod
    def get_events_from_sync_source(source_id: str, registration: ScraperRegistration) -> List[Event]:
        """
        Get events from a single synchronous source.
        
        Args:
            source_id: Identifier for the source (for logging)
            registration: Registration info for the scraper
        
        Returns:
            List[Event]: List of events from the source, or empty list if failed
        """
        try:
            scraper_class = SourceManager.get_scraper_class(registration)
            if not issubclass(scraper_class, SyncScraper):
                logger.error(f"Scraper {source_id} is not a synchronous scraper")
                return []
                
            scraper = scraper_class()
            logger.info(f"Fetching events from {scraper.name()}")
            events = scraper.get_events()
            logger.info(f"Found {len(events)} events from {scraper.name()}")
            return events
        except Exception as e:
            logger.error(f"Error fetching events from {source_id}: {e}")
            return []
    
    @staticmethod
    def fetch_and_parse_single_source(source_id: str, registration: ScraperRegistration) -> List[Event]:
        """
        Fetch events from a single source, handling both sync and async scrapers.
        
        Args:
            source_id: Identifier for the source
            registration: Registration info for the scraper
            
        Returns:
            List[Event]: List of events from the source, or empty list if failed
            
        Raises:
            Exception: If there's an error fetching from the source
        """
        try:
            scraper_class = SourceManager.get_scraper_class(registration)
            scraper_type = SourceManager._get_scraper_type(scraper_class)
            
            if scraper_type == 'async':
                # For async scrapers, we just initialize them
                # They will handle their own data processing through webhooks
                scraper = scraper_class()
                success = scraper.initialize_data_fetch()
                if not success:
                    logger.error(f"Failed to initialize async scraper {source_id}")
                    return []
                return []  # Async scrapers handle their own processing
            else:
                # For sync scrapers, we fetch events directly
                return SourceManager.get_events_from_sync_source(source_id, registration)
                
        except Exception as e:
            logger.error(f"Error fetching from source {source_id}: {e}")
            return [] 