"""Utility functions for interacting with LLMs (OpenAI).

This module provides functions for interacting with OpenAI's LLM models,
specifically for event detection and information extraction.
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from zoneinfo import ZoneInfo

from src.config.external_services.openai import OpenAIConfig, init_openai_client

logger = logging.getLogger(__name__)

def _extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from a response that might be wrapped in markdown code blocks."""
    # First try parsing as-is
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try extracting from markdown code block
    if "```" in response_text:
        try:
            # Find content between code blocks
            start = response_text.find("```") + 3
            end = response_text.rfind("```")
            # Skip language identifier if present
            if "json" in response_text[start:start+10]:
                start = response_text.find("\n", start) + 1
            json_str = response_text[start:end].strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
    
    return None

def is_event_post(
    content: str,
    post_date: Optional[str] = None,
    author: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    Use OpenAI to determine if a post is about an event.
    
    Args:
        content: The text content to analyze
        post_date: The original posting date of the content
        author: The author of the post
        config: Optional LLM configuration. If not provided, uses default config
    
    Returns:
        Tuple of (is_event: bool, explanation: str)
    """
    try:
        config = config or OpenAIConfig().to_dict()
        openai = init_openai_client()
        
        # Prepare content with metadata
        content_with_metadata = f"""Posted on: {post_date if post_date else 'Unknown date'}
Posted by: {author if author else 'Unknown author'}

{content}"""
        
        response = openai.chat.completions.create(
            model=config['model'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens'],
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that determines if a post is about an event. "
                        "The input will include the post's date and author. "
                        "Consider these factors when determining if something is an event:\n"
                        "1. The temporal context (when the post was made vs when the event is/was)\n"
                        "2. The author's role (official sources are more likely to post events)\n"
                        "3. The content structure and language used\n"
                        "Always respond with a valid JSON object."
                    )
                },
                {
                    "role": "user",
                    "content": f"Is this post about an event? Please respond with a JSON object containing 'is_event' (boolean) and 'explanation' (string). Post content:\n\n{content_with_metadata}"
                }
            ]
        )
        
        # Get the response content and ensure it's valid JSON
        response_text = response.choices[0].message.content.strip()
        result = _extract_json_from_response(response_text)
        if result and 'is_event' in result and 'explanation' in result:
            return result['is_event'], result['explanation']
        else:
            logger.error(f"Invalid response format: {response_text}")
            return False, "Error: Invalid response format"
        
    except Exception as e:
        logger.error(f"Error in is_event_post: {e}")
        return False, str(e)

def parse_event_details(
    content: str,
    url: str,
    post_date: Optional[str] = None,
    author: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Use OpenAI to parse event details from a post.
    
    Args:
        content: The text content to analyze
        url: The URL of the post
        post_date: The original posting date of the content
        author: The author of the post
        config: Optional LLM configuration. If not provided, uses default config
    
    Returns:
        Dictionary with event details or None if parsing fails
    """
    try:
        config = config or OpenAIConfig().to_dict()
        openai = init_openai_client()
        
        # Prepare content with metadata
        content_with_metadata = f"""Posted on: {post_date if post_date else 'Unknown date'}
Posted by: {author if author else 'Unknown author'}

{content}"""
        
        response = openai.chat.completions.create(
            model=config['model'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens'],
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that extracts event details from social media posts. "
                        "The input will include the post's date and author. "
                        "When interpreting dates in the post content:\n"
                        "1. If the post mentions 'today', 'i dag', 'tomorrow', 'imorgen', etc., use the post's date as reference\n"
                        "2. If a date is mentioned without a year, use the year from the post date\n"
                        "3. For explicit dates with years, use those exactly as specified\n"
                        "4. Consider the temporal context (when the post was made) when interpreting relative dates\n"
                        "5. If the post is about a past event, ensure the dates are in the past relative to the post date\n"
                        "6. If the post is about a future event, ensure the dates are in the future relative to the post date\n"
                        "Always respond with a valid JSON object."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Extract event details from this post. The input includes the post's original posting date "
                        f"followed by the content. Please respond with a JSON object containing:\n"
                        f"- 'title': The event title\n"
                        f"- 'description': Full event description\n"
                        f"- 'start_time': Start time in ISO format (YYYY-MM-DDTHH:MM:SS)\n"
                        f"- 'end_time': End time in ISO format (optional)\n"
                        f"- 'location': Event location (optional)\n"
                        f"- 'food': Food/refreshments info (optional)\n"
                        f"- 'registration_info': Registration details (optional)\n\n"
                        f"Post:\n\n{content_with_metadata}\n\nPost URL: {url}"
                    )
                }
            ]
        )
        
        # Get the response content and ensure it's valid JSON
        response_text = response.choices[0].message.content.strip()
        result = _extract_json_from_response(response_text)
        if result:
            return result
        else:
            logger.error(f"Invalid response format: {response_text}")
            return None
        
    except Exception as e:
        logger.error(f"Error in parse_event_details: {e}")
        return None 