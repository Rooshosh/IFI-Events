"""Logging configuration for the application."""

import logging
import sys

def setup_logging():
    """Configure logging for the application."""
    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    loggers = [
        'src.webhooks.handlers.brightdata_facebook_group',
        'src.utils.data_processors.facebook_group_raw_data_processor',
        'src.utils.llm',
        'src.new_event_handler'
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(console_handler) 