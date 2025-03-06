"""Base interface for data processors."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import logging

from src.models.event import Event

logger = logging.getLogger(__name__)

class DataProcessor(ABC):
    """
    Base interface for data processors.
    
    Each processor is responsible for:
    1. Converting source-specific data into our Event model
    2. Handling any source-specific data validation
    3. Managing source-specific error cases
    
    Required Methods:
        process_data(data: Dict[str, Any]) -> List[Event]: Convert data to events
    """
    
    @abstractmethod
    def process_data(self, data: Dict[str, Any]) -> List[Event]:
        """
        Process source data into events.
        
        Args:
            data: The source-specific data to process
            
        Returns:
            List[Event]: List of events created from the data
        """
        pass
    
    @abstractmethod
    def name(self) -> str:
        """
        Return the name/identifier of this processor.
        
        Returns:
            str: The processor's identifier (e.g., 'facebook')
        """
        pass 