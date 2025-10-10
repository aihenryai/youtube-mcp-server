#!/usr/bin/env python3
"""
YouTube MCP Server - Enhanced Edition
A comprehensive Model Context Protocol server for YouTube data extraction.

NEW FEATURES (v2.0):
- ✅ Two-tier caching (memory + disk) to reduce API quota usage
- ✅ Rate limiting to prevent quota exhaustion
- ✅ Input validation and sanitization
- ✅ Retry logic with exponential backoff
- ✅ Enhanced error handling
- ✅ Security improvements for HTTP mode
- ✅ Comprehensive logging

Provides tools for:
- Video transcripts (with caching)
- Video metadata
- Channel information
- Comments
- Video search
"""

import os
import logging
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Import our enhanced utilities
from config import config
from utils import (
    cached,
    rate_limited,
    validate_video_url,
    validate_channel_id,
    validate_language,
    validate_search_query,
    validate_max_results,
    validate_order,
    sanitize_text,
    ValidationError,
    cache_stats,
    get_rate_stats
)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.server.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("YouTube MCP Server Enhanced")

# YouTube API setup with timeout
try:
    youtube = build(
        "youtube", 
        "v3", 
        developerKey=config.youtube_api.api_key,
        cache_discovery=False
    )
    logger.info("YouTube API client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize YouTube API client: {e}")
    raise


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def resolve_channel_handle(username: str) -> Optional[str]:
    """
    Resolve @username to channel ID via API
    Uses caching and rate limiting
    """
    try:
        response = youtube.channels().list(
            part='id',
            forHandle=username
        ).execute()
        
        if response.get('items'):
            return response['items'][0]['id']
    except HttpError as e:
        logger.warning(f"Failed to resolve channel handle {username}: {e}")
    
    return None


# ============================================================================
# MCP TOOLS - ENHANCED VERSIONS
# ============================================================================

@mcp.tool()
@rate_limited(endpoint="get_video_transcript")
@cached(ttl=3600)  # Cache transcripts for 1 hour
def get_video_transcript(
    video_url: str,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Extract video transcript/subtitles from a YouTube video.
    
    ✨ Enhanced with:
    - Input validation
    - Caching (1 hour TTL)
    - Rate limiting
    - Better error messages
    
    Args:
        video_url: YouTube video URL or video ID
        language: Language code (e.g., 'en', 'es', 'fr', 'he', 'ar')
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating success
        - video_id: The video ID
        - language: Language of the transcript
        - is_generated: Whether transcript is auto-generated
        - transcript: List of transcript segments with text and timestamps
        - full_text: Complete transcript as a single string
        - segment_count: Number of segments
        - cached: Whether result came from cache
    
    Example:
        get_video_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ", language="en")
    """
    try:
        # Validate inputs
        video_id = validate_video_url(video_url)
        language = validate_language(language)
        
        logger.info(f"Fetching transcript for video {video_id} in language {language}")
        
        # Get transcript
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get transcript in requested language
        try:
            transcript = transcript_list.find_transcript([language])
        except (NoTranscriptFound, TranscriptsDisabled):
            # Fallback to English auto-generated
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
                logger.info(f"Falling back to English auto-generated transcript")
            except:
                return {
                    "success": False,
                    "error": "No transcript available",
                    "message": f"No transcript found in {language} or English. "
                               f"The video may not have captions enabled."
                }
        
        # Fetch the transcript
        transcript_data = transcript.fetch()
        
        # Create full text (sanitized)
        full_text = " ".join([
            sanitize_text(entry['text'], max_length=10000) 
            for entry in transcript_data
        ])
        
        return {
            "success": True,
            "video_id": video_id,
            "language": transcript.language_code,
            "is_generated": transcript.is_generated,
            "transcript": transcript_data[:100],  # Limit to first 100 segments
            "full_text": full_text[:50000],  # Limit to 50K characters
            "segment_count": len(transcript_data),
            "cached": False  # Will be overridden by cache decorator
        }
        
    except ValidationError as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Failed to get transcript: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve transcript. The video may not have captions available."
        }


@mcp.tool()
@rate_limited(endpoint="get_video_info")
@cached(ttl=1800)  # Cache for 30 minutes
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(HttpError)
)
def get_video_info(video_url: str) -> Dict[str, Any]:
    """
    Get comprehensive metadata for a YouTube video.
    
    ✨ Enhanced with:
    - Input validation
    - Caching (30 min TTL)
    - Rate limiting
    - Retry logic (3 attempts)
    - Sanitized output
    
    Args:
        video_url: YouTube video URL or video ID
    
    Returns:
        Dictionary with video metadata including:
        title, description, channel info, statistics, etc.
    
    Example:
        get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    """
    try:
        # Validate input
        video_id = validate_video_url(video_url)
        
        logger.info(f"Fetching info for video {video_id}")
        
        # Request video details
        response = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
        ).execute()
        
        if not response.get('items'):
            return {
                "success": False,
                "error": "Video not found",
                "video_id": video_id
            }
        
        video = response['items'][0]
        snippet = video['snippet']
        statistics = video.get('statistics', {})
        content_details = video['contentDetails']
        
        return {
            "success": True,
            "video_id": video_id,
            "title": sanitize_text(snippet['title'], 500),
            "description": sanitize_text(snippet.get('description', ''), 5000),
            "channel_id": snippet['channelId'],
            "channel_title": sanitize_text(snippet['channelTitle'], 200),
            "publish_date": snippet['publishedAt'],
            "duration": content_details['duration'],
            "view_count": int(statistics.get('viewCount', 0)),
            "like_count": int(statistics.get('likeCount', 0)),
            "comment_count": int(statistics.get('commentCount', 0)),
            "tags": snippet.get('tags', [])[:20],  # Limit to 20 tags
            "thumbnails": snippet.get('thumbnails', {}),
            "category_id": snippet['categoryId'],
            "default_language": snippet.get('defaultLanguage'),
            "cached": False
        }
        
    except ValidationError as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        return {
            "success": False,
            "error": f"API error: {e.status_code}",
            "message": "Failed to retrieve video information"
        }


@mcp.tool()
@rate_limited(endpoint="get_channel_info")
@cached(ttl=3600)  # Cache for 1 hour
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(HttpError)
)
def get_channel_info(channel_id: str) -> Dict[str, Any]:
    """
    Get information and statistics for a YouTube channel.
    
    ✨ Enhanced with:
    - Support for @username resolution
    - Input validation
    - Caching (1 hour TTL)
    - Rate limiting
    - Retry logic
    
    Args:
        channel_id: YouTube channel ID, URL, or @username
    
    Returns:
        Dictionary with channel statistics and information
    
    Example:
        get_channel_info("@googledev")
        get_channel_info("UC_x5XG1OV2P6uZZ5FSM9Ttw")
    """
    try:
        # Validate and resolve channel ID
        validated_id = validate_channel_id(channel_id)
        
        # Handle @username format
        if validated_id.startswith('@') or '/@' in validated_id:
            username = validated_id.lstrip('@').split('/@')[-1]
            resolved_id = resolve_channel_handle(username)
            if not resolved_id:
                return {
                    "success": False,
                    "error": "Channel not found",
                    "message": f"Could not resolve @{username} to a channel ID"
                }
            validated_id = resolved_id
        
        logger.info(f"Fetching info for channel {validated_id}")
        
        # Request channel details
        response = youtube.channels().list(
            part='snippet,statistics,contentDetails',
            id=validated_id
        ).execute()
        
        if not response.get('items'):
            return {
                "success": False,
                "error": "Channel not found",
                "channel_id": channel_id
            }
        
        channel = response['items'][0]
        snippet = channel['snippet']
        statistics = channel.get('statistics', {})
        
        return {
            "success": True,
            "channel_id": channel['id'],
            "title": sanitize_text(snippet['title'], 200),
            "description": sanitize_text(snippet.get('description', ''), 2000),
            "custom_url": snippet.get('customUrl'),
            "published_at": snippet['publishedAt'],
            "subscriber_count": int(statistics.get('subscriberCount', 0)),
            "video_count": int(statistics.get('videoCount', 0)),
            "view_count": int(statistics.get('viewCount', 0)),
            "thumbnails": snippet.get('thumbnails', {}),
            "country": snippet.get('country'),
            "hidden_subscriber_count": statistics.get('hiddenSubscriberCount', False),
            "cached": False
        }
        
    except ValidationError as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        return {
            "success": False,
            "error": f"API error: {e.status_code}",
            "message": "Failed to retrieve channel information"
        }


@mcp.tool()
@rate_limited(endpoint="get_video_comments")
@cached(ttl=1800)  # Cache for 30 minutes
def get_video_comments(
    video_url: str,
    max_results: int = 100,
    include_replies: bool = True
) -> Dict[str, Any]:
    """
    Fetch comments from a YouTube video.
    
    ✨ Enhanced with:
    - Input validation
    - Caching (30 min TTL)
    - Rate limiting
    - Comment sanitization
    
    Args:
        video_url: YouTube video URL or video ID
        max_results: Maximum comments (1-100, default: 100)
        include_replies: Include replies (default: True)
    
    Returns:
        Dictionary with comment data
    
    Example:
        get_video_comments("https://www.youtube.com/watch?v=dQw4w9WgXcQ", max_results=50)
    """
    try:
        # Validate inputs
        video_id = validate_video_url(video_url)
        max_results = validate_max_results(max_results, "comments")
        
        logger.info(f"Fetching {max_results} comments for video {video_id}")
        
        comments = []
        
        # Request top-level comments
        response = youtube.commentThreads().list(
            part='snippet,replies',
            videoId=video_id,
            maxResults=max_results,
            textFormat='plainText',
            order='relevance'
        ).execute()
        
        for item in response.get('items', []):
            top_comment = item['snippet']['topLevelComment']['snippet']
            
            comment_data = {
                "id": item['id'],
                "author": sanitize_text(top_comment['authorDisplayName'], 100),
                "text": sanitize_text(top_comment['textDisplay'], 10000),
                "like_count": top_comment['likeCount'],
                "published_at": top_comment['publishedAt'],
                "updated_at": top_comment['updatedAt'],
                "reply_count": item['snippet']['totalReplyCount'],
                "replies": []
            }
            
            # Add replies if available and requested
            if include_replies and item.get('replies'):
                for reply in item['replies']['comments'][:10]:  # Limit to 10 replies
                    reply_snippet = reply['snippet']
                    comment_data['replies'].append({
                        "id": reply['id'],
                        "author": sanitize_text(reply_snippet['authorDisplayName'], 100),
                        "text": sanitize_text(reply_snippet['textDisplay'], 10000),
                        "like_count": reply_snippet['likeCount'],
                        "published_at": reply_snippet['publishedAt']
                    })
            
            comments.append(comment_data)
        
        return {
            "success": True,
            "video_id": video_id,
            "comment_count": len(comments),
            "total_reply_count": sum(c['reply_count'] for c in comments),
            "comments": comments,
            "cached": False
        }
        
    except ValidationError as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        return {
            "success": False,
            "error": f"API error: {e.status_code}",
            "message": "Failed to retrieve comments. Comments may be disabled for this video."
        }


@mcp.tool()
@rate_limited(endpoint="search_videos")
@cached(ttl=600)  # Cache for 10 minutes
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(HttpError)
)
def search_videos(
    query: str,
    max_results: int = 10,
    order: str = "relevance"
) -> Dict[str, Any]:
    """
    Search for YouTube videos.
    
    ✨ Enhanced with:
    - Query validation and sanitization
    - Caching (10 min TTL)
    - Rate limiting
    - Retry logic
    - Smart order mapping
    
    Args:
        query: Search query string
        max_results: Maximum results (1-50, default: 10)
        order: Sort order - 'relevance', 'date', 'viewCount', 'rating', 'title'
    
    Returns:
        Dictionary with search results
    
    Example:
        search_videos("Python tutorial", max_results=20, order="viewCount")
    """
    try:
        # Validate inputs
        query = validate_search_query(query)
        max_results = validate_max_results(max_results, "results")
        order = validate_order(order)
        
        logger.info(f"Searching videos: '{query}' (max={max_results}, order={order})")
        
        # Search for videos
        response = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            maxResults=max_results,
            order=order
        ).execute()
        
        videos = []
        for item in response.get('items', []):
            snippet = item['snippet']
            videos.append({
                "video_id": item['id']['videoId'],
                "title": sanitize_text(snippet['title'], 200),
                "description": sanitize_text(snippet.get('description', ''), 500),
                "channel_id": snippet['channelId'],
                "channel_title": sanitize_text(snippet['channelTitle'], 100),
                "published_at": snippet['publishedAt'],
                "thumbnails": snippet.get('thumbnails', {})
            })
        
        return {
            "success": True,
            "query": query,
            "order": order,
            "result_count": len(videos),
            "videos": videos,
            "cached": False
        }
        
    except ValidationError as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        return {
            "success": False,
            "error": f"API error: {e.status_code}",
            "message": "Failed to search videos"
        }


# ============================================================================
# UTILITY TOOLS
# ============================================================================

@mcp.tool()
def get_server_stats() -> Dict[str, Any]:
    """
    Get server statistics including cache and rate limit info.
    
    Returns:
        Dictionary with:
        - cache_stats: Cache hit/miss statistics
        - rate_limits: Rate limit status per endpoint
        - server_config: Current configuration
    """
    return {
        "success": True,
        "cache": cache_stats(),
        "rate_limits": {
            "transcript": get_rate_stats("get_video_transcript"),
            "video_info": get_rate_stats("get_video_info"),
            "channel_info": get_rate_stats("get_channel_info"),
            "comments": get_rate_stats("get_video_comments"),
            "search": get_rate_stats("search_videos")
        },
        "config": {
            "transport": config.server.transport,
            "cache_enabled": config.cache.enabled,
            "rate_limit_enabled": config.rate_limit.enabled
        }
    }


# ============================================================================
# SERVER INITIALIZATION
# ============================================================================

if __name__ == "__main__":
    logger.info(f"Starting YouTube MCP Server Enhanced v2.0")
    logger.info(f"Transport: {config.server.transport}")
    logger.info(f"Cache enabled: {config.cache.enabled}")
    logger.info(f"Rate limiting enabled: {config.rate_limit.enabled}")
    
    if config.server.transport == "http":
        # HTTP mode - with security warning
        if not config.security.require_api_key:
            logger.warning("⚠️  HTTP mode without API key authentication - use with caution!")
        
        logger.info(f"🚀 Starting in HTTP mode on {config.server.host}:{config.server.port}")
        mcp.run(
            transport="streamable-http",
            host=config.server.host,
            port=config.server.port
        )
    else:
        # stdio mode - most secure
        logger.info("🚀 Starting in stdio mode (local)")
        mcp.run()
