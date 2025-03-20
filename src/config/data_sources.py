"""Configuration for event sources and their scrapers."""

from dataclasses import dataclass
from typing import Dict, Optional
import os

# Internal imports - environment must be first
from .environment import IS_PRODUCTION_ENVIRONMENT

@dataclass
class ScraperRegistration:
    """
    Registration of a scraper with the source manager.
    
    This class defines:
    1. Whether the scraper is currently enabled
    2. Where to find its implementation
    3. Priority of the source (higher number = higher priority)
    4. Display name of the source
    
    Fields:
        enabled: Whether this scraper is enabled
        scraper_class: Full path to scraper class (e.g., 'src.scrapers.peoply.PeoplyScraper')
        priority: Priority of this source (higher number = higher priority)
        name: Display name of the source (e.g., 'Facebook Post')
    """
    enabled: bool
    scraper_class: str
    priority: int
    name: str

# Registry of available scrapers for fetching new data
SOURCES = {
    'peoply': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.peoply.PeoplyScraper',
        priority=100,
        name='Peoply'
    ),
    'navet': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.navet.NavetScraper',
        priority=90,
        name='Navet'
    ),
    'facebook-post': ScraperRegistration(
        enabled=True,
        scraper_class='src.scrapers.facebook_post.FacebookGroupScraper',
        priority=10,
        name='Facebook Post'
    ),
    'facebook-event': ScraperRegistration(
        enabled=False,
        scraper_class='src.scrapers.facebook_event.FacebookEventScraper',
        priority=70,
        name='Facebook Event'
    )
}

def get_enabled_sources() -> Dict[str, ScraperRegistration]:
    """
    Get all enabled scrapers.
    
    Returns:
        Dict[str, ScraperRegistration]: Dictionary of source_id -> registration for all enabled scrapers
    """
    return {k: v for k, v in SOURCES.items() if v.enabled}

def get_source_display_name(source_id: str) -> str:
    """
    Get the display name for a given source ID.
    
    Args:
        source_id: The source identifier (e.g., 'facebook-post')
        
    Returns:
        str: The source display name (e.g., 'Facebook Post')
        
    Raises:
        ValueError: If no source is found with the given ID
    """
    registration = SOURCES.get(source_id)
    if not registration:
        raise ValueError(f"No source found with ID: {source_id}")
    return registration.name

def get_source_id_by_display_name(display_name: str) -> str:
    """
    Get the source ID for a given display name.
    
    Args:
        display_name: The display name to look up (e.g., 'Facebook Post')
        
    Returns:
        str: The source ID (e.g., 'facebook-post')
        
    Raises:
        ValueError: If no source is found with the given display name
    """
    for source_id, registration in SOURCES.items():
        if registration.name == display_name:
            return source_id
    raise ValueError(f"No source found with display name: {display_name}")

def compare_source_priorities(name1: str, name2: str) -> int:
    """
    Compare the priorities of two sources by their display names.
    
    Args:
        name1: Display name of first source (e.g., 'Facebook Post')
        name2: Display name of second source (e.g., 'Peoply')
        
    Returns:
        int: 1 if source1 has higher priority, -1 if source2 has higher priority, 0 if equal
        
    Raises:
        ValueError: If either display name is not found
    """
    source1 = get_source_id_by_display_name(name1)
    source2 = get_source_id_by_display_name(name2)
    priority1 = SOURCES[source1].priority
    priority2 = SOURCES[source2].priority
    return 1 if priority1 > priority2 else (-1 if priority1 < priority2 else 0) 