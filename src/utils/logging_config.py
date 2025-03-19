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
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # Set higher log levels for noisy components
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    
    # Configure specific loggers
    loggers = [
        'src.webhooks.handlers.brightdata_facebook_group',
        'src.utils.data_processors.facebook_group_raw_data_processor',
        'src.utils.llm',
        'src.new_event_handler'
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        # Don't add handler here since it's already handled by root logger 