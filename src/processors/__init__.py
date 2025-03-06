"""Data processors for various event sources."""

from src.processors.base import DataProcessor
from src.processors.facebook import FacebookProcessor

__all__ = [
    'DataProcessor',
    'FacebookProcessor'
] 