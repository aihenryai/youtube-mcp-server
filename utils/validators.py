#!/usr/bin/env python3
"""
Input validation for YouTube MCP Server
Validates and sanitizes all user inputs
"""

import re
import logging
from typing import Optional, Union
from urllib.parse import urlparse, parse_qs

from config import config

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class InputValidator:
    """Validates and sanitizes user inputs"""
    
    def __init__(self):
        """Initialize validator with config"""
        self.valid_languages = set(config.validation.valid_languages)
        self.max_query_length = config.validation.max_query_length
        self.max_results_limit = config.validation.max_results_limit
        self.max_comments_limit = config.validation.max_comments_limit
    
    def validate_video_url(self, url_or_id: str) -> str:
        """
        Validate and extract video ID from URL or ID
        
        Args:
            url_or_id: YouTube video URL or ID
            
        Returns:
            Validated video ID
            
        Raises:
            ValidationError: If URL/ID is invalid
        """
        if not url_or_id or not isinstance(url_or_id, str):
            raise ValidationError("Video URL or ID is required")
        
        url_or_id = url_or_id.strip()
        
        # Check if it's already a valid video ID (11 chars, alphanumeric with - and _)
        if re.match(r'^[A-Za-z0-9_-]{11}$', url_or_id):
            return url_or_id
        
        # Parse as URL
        try:
            parsed = urlparse(url_or_id)
            
            # youtube.com/watch?v=...
            if parsed.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
                query_params = parse_qs(parsed.query)
                if 'v' in query_params and query_params['v']:
                    video_id = query_params['v'][0]
                    if re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
                        return video_id
            
            # youtu.be/...
            elif parsed.hostname == 'youtu.be':
                video_id = parsed.path.lstrip('/')
                if re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
                    return video_id
            
        except Exception as e:
            logger.warning(f"Failed to parse video URL: {e}")
        
        raise ValidationError(
            f"Invalid YouTube video URL or ID: {url_or_id[:50]}... "
            "Expected format: https://www.youtube.com/watch?v=VIDEO_ID or VIDEO_ID"
        )
    
    def validate_channel_id(self, url_or_id: str) -> str:
        """
        Validate channel ID or URL
        
        Args:
            url_or_id: YouTube channel URL, ID, or @username
            
        Returns:
            Validated channel identifier (might need API resolution for @usernames)
            
        Raises:
            ValidationError: If input is invalid
        """
        if not url_or_id or not isinstance(url_or_id, str):
            raise ValidationError("Channel URL or ID is required")
        
        url_or_id = url_or_id.strip()
        
        # Check if it's a channel ID (starts with UC and is 24 chars)
        if re.match(r'^UC[A-Za-z0-9_-]{22}$', url_or_id):
            return url_or_id
        
        # Check if it's @username format
        if url_or_id.startswith('@') or '/@' in url_or_id:
            # Extract username
            if '/@' in url_or_id:
                username = url_or_id.split('/@')[-1].split('?')[0].split('/')[0]
            else:
                username = url_or_id[1:]  # Remove @
            
            # Validate username format
            if re.match(r'^[A-Za-z0-9_-]{3,30}$', username):
                return url_or_id  # Return as-is for API resolution
        
        # Check if it's a channel URL
        if '/channel/' in url_or_id:
            channel_id = url_or_id.split('/channel/')[-1].split('?')[0].split('/')[0]
            if re.match(r'^UC[A-Za-z0-9_-]{22}$', channel_id):
                return channel_id
        
        raise ValidationError(
            f"Invalid YouTube channel URL or ID: {url_or_id[:50]}... "
            "Expected: channel ID (UC...), @username, or channel URL"
        )
    
    def validate_language(self, language: str) -> str:
        """
        Validate language code
        
        Args:
            language: ISO language code
            
        Returns:
            Validated language code
            
        Raises:
            ValidationError: If language is invalid
        """
        if not language or not isinstance(language, str):
            raise ValidationError("Language code is required")
        
        language = language.strip().lower()
        
        if language not in self.valid_languages:
            raise ValidationError(
                f"Invalid language code: {language}. "
                f"Supported languages: {', '.join(sorted(self.valid_languages)[:10])}..."
            )
        
        return language
    
    def validate_search_query(self, query: str) -> str:
        """
        Validate and sanitize search query
        
        Args:
            query: Search query string
            
        Returns:
            Sanitized query
            
        Raises:
            ValidationError: If query is invalid
        """
        if not query or not isinstance(query, str):
            raise ValidationError("Search query is required")
        
        query = query.strip()
        
        if len(query) < 1:
            raise ValidationError("Search query cannot be empty")
        
        if len(query) > self.max_query_length:
            raise ValidationError(
                f"Search query too long (max {self.max_query_length} characters)"
            )
        
        # Remove potentially dangerous characters
        # Allow alphanumeric, spaces, and common punctuation
        if not re.match(r'^[\w\s\-.,!?@#$%&()\[\]{}+=:;\'\"]*$', query, re.UNICODE):
            raise ValidationError(
                "Search query contains invalid characters"
            )
        
        return query
    
    def validate_max_results(
        self,
        max_results: Union[int, str],
        limit_type: str = "results"
    ) -> int:
        """
        Validate max_results parameter
        
        Args:
            max_results: Number of results to return
            limit_type: Type of limit ("results" or "comments")
            
        Returns:
            Validated integer value
            
        Raises:
            ValidationError: If value is invalid
        """
        try:
            max_results = int(max_results)
        except (TypeError, ValueError):
            raise ValidationError(
                f"max_results must be a number, got: {type(max_results).__name__}"
            )
        
        if max_results < 1:
            raise ValidationError("max_results must be at least 1")
        
        # Apply appropriate limit
        if limit_type == "comments":
            limit = self.max_comments_limit
        else:
            limit = self.max_results_limit
        
        if max_results > limit:
            logger.warning(
                f"max_results {max_results} exceeds limit {limit}, capping to {limit}"
            )
            max_results = limit
        
        return max_results
    
    def validate_order(self, order: str) -> str:
        """
        Validate sort order parameter
        
        Args:
            order: Sort order value
            
        Returns:
            Validated order
            
        Raises:
            ValidationError: If order is invalid
        """
        valid_orders = ['relevance', 'date', 'viewCount', 'rating', 'title']
        
        if not order or not isinstance(order, str):
            return 'relevance'  # Default
        
        order = order.strip().lower()
        
        # Map common variations to valid values
        order_map = {
            'views': 'viewCount',
            'view': 'viewCount',
            'recent': 'date',
            'newest': 'date',
            'oldest': 'date',
            'popular': 'viewCount',
            'top': 'rating'
        }
        
        order = order_map.get(order, order)
        
        # Check if order matches valid value (case-insensitive)
        for valid_order in valid_orders:
            if order.lower() == valid_order.lower():
                return valid_order
        
        raise ValidationError(
            f"Invalid order: {order}. "
            f"Valid options: {', '.join(valid_orders)}"
        )
    
    def sanitize_text(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize text input (remove control characters, limit length)
        
        Args:
            text: Text to sanitize
            max_length: Maximum length (optional)
            
        Returns:
            Sanitized text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit length if specified
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()


# Global validator instance
validator = InputValidator()


# Convenience functions for easy import
def validate_video_url(url_or_id: str) -> str:
    """Validate video URL or ID"""
    return validator.validate_video_url(url_or_id)


def validate_channel_id(url_or_id: str) -> str:
    """Validate channel URL or ID"""
    return validator.validate_channel_id(url_or_id)


def validate_language(language: str) -> str:
    """Validate language code"""
    return validator.validate_language(language)


def validate_search_query(query: str) -> str:
    """Validate search query"""
    return validator.validate_search_query(query)


def validate_max_results(max_results: Union[int, str], limit_type: str = "results") -> int:
    """Validate max results"""
    return validator.validate_max_results(max_results, limit_type)


def validate_order(order: str) -> str:
    """Validate sort order"""
    return validator.validate_order(order)


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize text"""
    return validator.sanitize_text(text, max_length)


def validate_playlist_title(title: str) -> str:
    """Validate playlist title"""
    if not title or not isinstance(title, str):
        raise ValidationError("Playlist title is required")
    
    title = title.strip()
    
    if len(title) < 1:
        raise ValidationError("Playlist title cannot be empty")
    
    if len(title) > 150:  # YouTube limit
        raise ValidationError("Playlist title too long (max 150 characters)")
    
    return sanitize_text(title, max_length=150)


def validate_playlist_description(description: str) -> str:
    """Validate playlist description"""
    if not description:
        return ""
    
    if not isinstance(description, str):
        raise ValidationError("Playlist description must be a string")
    
    if len(description) > 5000:  # YouTube limit
        logger.warning("Playlist description too long, truncating to 5000 chars")
        description = description[:5000]
    
    return sanitize_text(description, max_length=5000)


def validate_privacy_status(status: str) -> str:
    """Validate privacy status"""
    valid_statuses = ['public', 'private', 'unlisted']
    
    if not status or not isinstance(status, str):
        raise ValidationError("Privacy status is required")
    
    status = status.strip().lower()
    
    if status not in valid_statuses:
        raise ValidationError(
            f"Invalid privacy status: {status}. "
            f"Valid options: {', '.join(valid_statuses)}"
        )
    
    return status


def validate_playlist_tags(tags: list) -> list:
    """Validate playlist tags"""
    if not tags:
        return []
    
    if not isinstance(tags, list):
        raise ValidationError("Tags must be a list")
    
    if len(tags) > 500:  # YouTube limit
        logger.warning("Too many tags, limiting to 500")
        tags = tags[:500]
    
    validated_tags = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        
        tag = sanitize_text(tag.strip(), max_length=30)
        if tag and len(tag) > 0:
            validated_tags.append(tag)
    
    return validated_tags


def validate_api_key_format(api_key: str) -> bool:
    """Validate YouTube API key format"""
    if not api_key or not isinstance(api_key, str):
        return False
    
    # Google API keys start with AIzaSy and are 39 chars
    if not api_key.startswith("AIzaSy"):
        return False
    
    if len(api_key) != 39:
        return False
    
    # Should only contain alphanumeric, - and _
    if not re.match(r'^[A-Za-z0-9_-]{39}
, api_key):
        return False
    
    return True
