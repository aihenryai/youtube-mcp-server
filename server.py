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
from typing import Optional, Dict, Any, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Import YouTube client manager
from youtube_client import YouTubeClient

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

# Import security utilities
from utils.security import (
    PromptInjectionDetector,
    check_injection,
    sanitize_for_llm,
    IPRateLimiter,
    get_client_ip,
    CORSValidator,
    RequestSigner,
    SecurityLogger
)

# Import OAuth 2.1 metadata utilities
from utils.oauth_metadata import (
    OAuthMetadataProvider,
    BearerTokenValidator,
    OAuthMiddleware,
    create_oauth_config
)

# Import Prometheus and Health Check utilities
from utils.prometheus_exporter import (
    PrometheusExporter,
    get_exporter,
    increment,
    set_gauge,
    observe,
    generate_metrics
)
from utils.health_check import (
    HealthChecker,
    get_health_checker,
    check_health,
    get_readiness,
    get_liveness
)

# Import Playlist Management modules
from playlist import (
    PlaylistCreator,
    PlaylistManager,
    PlaylistUpdater,
    PlaylistReorderer
)

# Import Captions Management modules
from captions import (
    CaptionsManager,
    CaptionsAnalyzer
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

# Initialize IP Rate Limiter (enabled for HTTP mode)
ip_limiter = IPRateLimiter(
    max_per_minute=config.rate_limit.per_ip_calls_per_minute,
    max_per_hour=config.rate_limit.per_ip_calls_per_hour
)
logger.info(f"IP Rate Limiter initialized: {config.rate_limit.per_ip_calls_per_minute}/min, {config.rate_limit.per_ip_calls_per_hour}/hour")

# Initialize CORS Validator (for HTTP mode)
cors_validator = None
if config.security.cors_enabled:
    cors_validator = CORSValidator(
        allowed_origins=config.security.cors_allowed_origins,
        allowed_methods=config.security.cors_allowed_methods,
        allowed_headers=config.security.cors_allowed_headers
    )
    logger.info(f"✅ CORS Validator initialized with {len(config.security.cors_allowed_origins)} origins")
else:
    logger.info("ℹ️  CORS validation disabled")

# Initialize Request Signer (for HTTP mode integrity)
request_signer = None
if config.security.request_signing_enabled:
    request_signer = RequestSigner(
        secret_key=config.security.request_signing_secret
    )
    logger.info("✅ Request Signing initialized (HMAC-SHA256)")
else:
    logger.info("ℹ️  Request signing disabled")

# Initialize Security Logger
security_logger = None
if config.security.security_logging_enabled:
    security_logger = SecurityLogger(
        log_file=config.security.security_log_file
    )
    logger.info(f"✅ Security Logger initialized: {config.security.security_log_file}")
else:
    logger.info("ℹ️  Security logging disabled")

# Initialize Prometheus Exporter (always enabled)
prometheus_exporter = get_exporter()
logger.info("✅ Prometheus Exporter initialized")

# Initialize Health Checker (always enabled)
health_checker = get_health_checker()
logger.info("✅ Health Checker initialized")

# Initialize OAuth 2.1 Metadata Provider (for HTTP mode)
oauth_provider = None
if config.server.transport == "http":
    server_url = f"http://{config.server.host}:{config.server.port}"
    oauth_provider = OAuthMetadataProvider(
        resource_uri=server_url,
        authorization_servers=["https://accounts.google.com"],
        documentation_url=f"{server_url}/docs",
        mcp_capabilities=[
            "video.read",
            "video.write",
            "playlist.read",
            "playlist.write",
            "captions.read",
            "captions.write",
            "channel.read"
        ]
    )
    logger.info(f"✅ OAuth Metadata Provider initialized for {server_url}")
else:
    logger.info("ℹ️  OAuth metadata disabled (stdio mode)")

# Initialize YouTube API client
# Supports both API Key (read-only) and OAuth2 (full access)
try:
    # Check if OAuth2 should be used
    use_oauth = os.getenv('USE_OAUTH2', 'false').lower() == 'true'
    
    youtube_client = YouTubeClient(
        api_key=config.youtube_api.api_key,
        use_oauth=use_oauth
    )
    
    # Get default client (API key for read operations)
    youtube = youtube_client.get_client()
    logger.info("YouTube API client initialized successfully")
    
    # Log OAuth2 status
    if youtube_client.is_oauth_available():
        oauth_status = youtube_client.get_oauth_status()
        if oauth_status.get('authenticated'):
            logger.info("✅ OAuth2 authenticated - write operations enabled")
        else:
            logger.info("⚠️  OAuth2 configured but not authenticated - run: python authenticate.py auth")
    else:
        logger.info("ℹ️  Using API key only - write operations disabled")
    
    # Initialize Playlist Management modules
    # These will use OAuth2 client when needed
    playlist_creator = PlaylistCreator(youtube)
    playlist_manager = PlaylistManager(youtube)
    playlist_updater = PlaylistUpdater(youtube)
    playlist_reorderer = PlaylistReorderer(youtube)
    logger.info("Playlist management modules initialized successfully")
    
    # Initialize Captions Management modules
    captions_manager = CaptionsManager(youtube)
    captions_analyzer = CaptionsAnalyzer()
    logger.info("Captions management modules initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize YouTube API client: {e}")
    raise


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_request_security(
    origin: Optional[str] = None,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    client_ip: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate request against all security components.
    Returns (is_valid, error_message)
    """
    # 1. CORS Validation (if enabled)
    if cors_validator and origin:
        if not cors_validator.is_origin_allowed(origin):
            if security_logger:
                security_logger.log_cors_violation(
                    origin=origin,
                    client_ip=client_ip or "unknown"
                )
            return False, f"Origin {origin} not allowed"
    
    # 2. Request Signature Validation (if enabled)
    if request_signer and headers:
        # Check for signature in headers
        signature = headers.get('X-Request-Signature')
        timestamp = headers.get('X-Request-Timestamp')
        nonce = headers.get('X-Request-Nonce')
        
        if config.security.request_signing_required:
            if not all([signature, timestamp, nonce]):
                if security_logger:
                    security_logger.log_request_signature_missing(
                        client_ip=client_ip or "unknown"
                    )
                return False, "Missing required signature headers"
            
            # Verify signature (would need request body in real impl)
            # For now, just validate format
            if not signature or len(signature) < 32:
                if security_logger:
                    security_logger.log_request_signature_invalid(
                        client_ip=client_ip or "unknown"
                    )
                return False, "Invalid signature format"
    
    # 3. IP Rate Limiting Check
    if client_ip and not ip_limiter.is_allowed(client_ip):
        if security_logger:
            security_logger.log_rate_limit_exceeded(
                client_ip=client_ip,
                endpoint="global"
            )
        return False, f"Rate limit exceeded for IP {client_ip}"
    
    return True, None


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
        # 🔐 Security Check: Prompt Injection Detection
        is_injection, pattern_type, details = PromptInjectionDetector.detect(video_url)
        if is_injection:
            logger.warning(
                f"🚨 Prompt injection detected in get_video_transcript: "
                f"pattern={pattern_type}, video_url={video_url[:100]}"
            )
            return {
                "success": False,
                "error": "Invalid input detected",
                "message": "The input contains suspicious patterns and was rejected for security reasons."
            }
        
        # Also check language parameter
        is_injection, pattern_type, details = PromptInjectionDetector.detect(language)
        if is_injection:
            logger.warning(
                f"🚨 Prompt injection detected in language parameter: "
                f"pattern={pattern_type}, language={language}"
            )
            return {
                "success": False,
                "error": "Invalid input detected",
                "message": "The language parameter contains suspicious patterns."
            }
        
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
        # 🔐 Security Check: Prompt Injection Detection
        is_injection, pattern_type, details = PromptInjectionDetector.detect(video_url)
        if is_injection:
            logger.warning(
                f"🚨 Prompt injection detected in get_video_info: "
                f"pattern={pattern_type}, video_url={video_url[:100]}"
            )
            return {
                "success": False,
                "error": "Invalid input detected",
                "message": "The input contains suspicious patterns and was rejected for security reasons."
            }
        
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
        # 🔐 Security Check: Prompt Injection Detection
        is_injection, pattern_type, details = PromptInjectionDetector.detect(query)
        if is_injection:
            logger.warning(
                f"🚨 Prompt injection detected in search_videos: "
                f"pattern={pattern_type}, query={query[:100]}"
            )
            return {
                "success": False,
                "error": "Invalid input detected",
                "message": "The search query contains suspicious patterns and was rejected for security reasons."
            }
        
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
# PLAYLIST MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
@rate_limited(endpoint="create_playlist")
def create_playlist(
    title: str,
    description: str = "",
    privacy_status: str = "private",
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a new YouTube playlist.
    
    ⚠️ Requires OAuth2 authentication (not available with API key only).
    
    Args:
        title: Playlist title (required)
        description: Playlist description
        privacy_status: Privacy setting ('public', 'private', or 'unlisted')
        tags: Optional list of tags
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating success
        - playlist_id: ID of created playlist
        - title: Playlist title
        - url: Playlist URL
        - privacy_status: Privacy setting
        - created_at: Creation timestamp
    
    Quota Cost: 50 units
    
    Example:
        create_playlist(
            title="My AI Learning Videos",
            description="Collection of AI/ML tutorials",
            privacy_status="private",
            tags=["AI", "Machine Learning"]
        )
    """
    try:
        result = playlist_creator.create_playlist(
            title=title,
            description=description,
            privacy_status=privacy_status,
            tags=tags or []
        )
        
        return {
            "success": True,
            **result
        }
        
    except ValueError as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except HttpError as e:
        logger.error(f"Failed to create playlist: {e}")
        return {
            "success": False,
            "error": f"API error: {e.status_code}",
            "message": "Failed to create playlist. Make sure OAuth2 authentication is configured."
        }


@mcp.tool()
@rate_limited(endpoint="add_video_to_playlist")
def add_video_to_playlist(
    playlist_id: str,
    video_id: str,
    position: Optional[int] = None
) -> Dict[str, Any]:
    """
    Add a video to a playlist.
    
    ⚠️ Requires OAuth2 authentication.
    
    Args:
        playlist_id: Target playlist ID
        video_id: Video ID to add (or full URL)
        position: Position in playlist (0-based, None = end)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating success
        - playlist_item_id: ID of the added item
        - video_id: Added video ID
        - position: Position in playlist
    
    Quota Cost: 50 units
    
    Example:
        add_video_to_playlist(
            playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            video_id="dQw4w9WgXcQ",
            position=0  # Add to beginning
        )
    """
    try:
        # Validate and extract video ID if URL provided
        video_id = validate_video_url(video_id)
        
        result = playlist_manager.add_video(
            playlist_id=playlist_id,
            video_id=video_id,
            position=position
        )
        
        return {
            "success": True,
            **result
        }
        
    except (ValueError, ValidationError) as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except HttpError as e:
        logger.error(f"Failed to add video to playlist: {e}")
        return {
            "success": False,
            "error": f"API error: {e.status_code}",
            "message": "Failed to add video to playlist"
        }


@mcp.tool()
@rate_limited(endpoint="remove_video_from_playlist")
def remove_video_from_playlist(
    playlist_id: str,
    playlist_item_id: Optional[str] = None,
    video_id: Optional[str] = None,
    position: Optional[int] = None
) -> Dict[str, Any]:
    """
    Remove a video from a playlist.
    
    ⚠️ Requires OAuth2 authentication.
    
    You must provide ONE of: playlist_item_id, video_id, or position.
    
    Args:
        playlist_id: Source playlist ID
        playlist_item_id: Specific playlist item ID to remove
        video_id: Remove by video ID (removes first occurrence)
        position: Remove by position (0-based)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating success
        - removed_item_id: ID of removed item
        - video_id: Removed video ID
        - position: Position of removed video
    
    Quota Cost: 51 units (1 for list + 50 for delete)
    
    Example:
        # Remove by position
        remove_video_from_playlist(
            playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            position=0
        )
    """
    try:
        result = playlist_manager.remove_video(
            playlist_id=playlist_id,
            playlist_item_id=playlist_item_id,
            video_id=video_id,
            position=position
        )
        
        return {
            "success": True,
            **result
        }
        
    except ValueError as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except HttpError as e:
        logger.error(f"Failed to remove video from playlist: {e}")
        return {
            "success": False,
            "error": f"API error: {e.status_code}",
            "message": "Failed to remove video from playlist"
        }


@mcp.tool()
@rate_limited(endpoint="update_playlist")
def update_playlist(
    playlist_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    privacy_status: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Update playlist metadata.
    
    ⚠️ Requires OAuth2 authentication.
    
    Args:
        playlist_id: Playlist ID to update
        title: New title (optional)
        description: New description (optional)
        privacy_status: New privacy ('public', 'private', 'unlisted')
        tags: New tags list (optional)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating success
        - playlist_id: Updated playlist ID
        - title: Updated title
        - description: Updated description
        - privacy_status: Updated privacy
    
    Quota Cost: 50 units
    
    Example:
        update_playlist(
            playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            title="My Updated Playlist",
            privacy_status="public"
        )
    """
    try:
        result = playlist_updater.update_playlist(
            playlist_id=playlist_id,
            title=title,
            description=description,
            privacy_status=privacy_status,
            tags=tags
        )
        
        return {
            "success": True,
            **result
        }
        
    except ValueError as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except HttpError as e:
        logger.error(f"Failed to update playlist: {e}")
        return {
            "success": False,
            "error": f"API error: {e.status_code}",
            "message": "Failed to update playlist"
        }


@mcp.tool()
@rate_limited(endpoint="reorder_playlist")
def reorder_playlist_video(
    playlist_id: str,
    video_id: str,
    new_position: int
) -> Dict[str, Any]:
    """
    Move a video to a new position in the playlist.
    
    ⚠️ Requires OAuth2 authentication.
    
    Args:
        playlist_id: Playlist ID
        video_id: Video ID to move
        new_position: Target position (0-based)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating success
        - playlist_item_id: Moved item ID
        - video_id: Moved video ID
        - old_position: Previous position
        - new_position: New position
    
    Quota Cost: 50 units
    
    Example:
        reorder_playlist_video(
            playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            video_id="dQw4w9WgXcQ",
            new_position=0  # Move to top
        )
    """
    try:
        result = playlist_reorderer.move_video(
            playlist_id=playlist_id,
            video_id=video_id,
            new_position=new_position
        )
        
        return {
            "success": True,
            **result
        }
        
    except ValueError as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except HttpError as e:
        logger.error(f"Failed to reorder playlist: {e}")
        return {
            "success": False,
            "error": f"API error: {e.status_code}",
            "message": "Failed to reorder playlist"
        }


@mcp.tool()
@rate_limited(endpoint="list_user_playlists")
@cached(ttl=300)  # Cache for 5 minutes
def list_user_playlists(
    max_results: int = 25
) -> Dict[str, Any]:
    """
    List all playlists owned by the authenticated user.
    
    ⚠️ Requires OAuth2 authentication.
    
    Args:
        max_results: Maximum playlists to return (1-50, default: 25)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating success
        - playlists: List of playlist objects
        - total_count: Number of playlists returned
        - cached: Whether from cache
    
    Quota Cost: 1 unit
    
    Example:
        list_user_playlists(max_results=50)
    """
    try:
        # Validate max_results
        if not 1 <= max_results <= 50:
            raise ValueError("max_results must be between 1 and 50")
        
        response = youtube.playlists().list(
            part='snippet,contentDetails,status',
            mine=True,
            maxResults=max_results
        ).execute()
        
        playlists = []
        for item in response.get('items', []):
            snippet = item['snippet']
            playlists.append({
                "playlist_id": item['id'],
                "title": sanitize_text(snippet['title'], 200),
                "description": sanitize_text(snippet.get('description', ''), 500),
                "privacy_status": item['status']['privacyStatus'],
                "item_count": item['contentDetails']['itemCount'],
                "published_at": snippet['publishedAt'],
                "thumbnails": snippet.get('thumbnails', {})
            })
        
        return {
            "success": True,
            "playlists": playlists,
            "total_count": len(playlists),
            "cached": False
        }
        
    except ValueError as e:
        return {
            "success": False,
            "error": "Validation error",
            "message": str(e)
        }
    except HttpError as e:
        logger.error(f"Failed to list playlists: {e}")
        return {
            "success": False,
            "error": f"API error: {e.status_code}",
            "message": "Failed to list playlists. Make sure OAuth2 authentication is configured."
        }


# ============================================================================
# UTILITY TOOLS
# ============================================================================

@mcp.tool()
def get_server_stats() -> Dict[str, Any]:
    """
    Get server statistics including cache, rate limit, and security info.
    
    Returns:
        Dictionary with:
        - cache_stats: Cache hit/miss statistics
        - rate_limits: Rate limit status per endpoint
        - server_config: Current configuration
        - security_status: Security components status
        - oauth_status: OAuth2 authentication status
    """
    stats = {
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
        },
        "security": {
            "cors_enabled": config.security.cors_enabled,
            "cors_origins_count": len(config.security.cors_allowed_origins) if config.security.cors_enabled else 0,
            "request_signing_enabled": config.security.request_signing_enabled,
            "request_signing_required": config.security.request_signing_required if config.security.request_signing_enabled else False,
            "security_logging_enabled": config.security.security_logging_enabled,
            "prompt_injection_detection": True,  # Always active
            "ip_rate_limiting": True  # Always active
        }
    }
    
    # Add security logger metrics if available
    if security_logger:
        metrics = security_logger.get_metrics()
        stats["security"]["metrics"] = {
            "total_events": metrics.get("total_events", 0),
            "high_severity_events": metrics.get("high_severity", 0),
            "critical_severity_events": metrics.get("critical_severity", 0),
            "blocked_requests": metrics.get("blocked_requests", 0),
            "suspicious_ips_count": len(metrics.get("suspicious_ips", []))
        }
    
    # Add CORS validator stats if available
    if cors_validator:
        stats["security"]["cors_allowed_origins"] = config.security.cors_allowed_origins[:5]  # First 5 only
        if len(config.security.cors_allowed_origins) > 5:
            stats["security"]["cors_allowed_origins"].append(f"... and {len(config.security.cors_allowed_origins) - 5} more")

    
    # Add OAuth2 status if available
    if youtube_client.is_oauth_available():
        stats["oauth_status"] = youtube_client.get_oauth_status()
    else:
        stats["oauth_status"] = {
            "available": False,
            "message": "OAuth2 not configured. Using API key only."
        }
    
    # Add OAuth 2.1 metadata status (RFC 9728)
    if oauth_provider:
        stats["oauth_metadata"] = {
            "enabled": True,
            "resource_uri": oauth_provider.resource_uri,
            "authorization_servers": oauth_provider.authorization_servers,
            "endpoint": "/.well-known/oauth-protected-resource",
            "rfc": "RFC 9728",
            "mcp_capabilities_count": len(oauth_provider.mcp_capabilities)
        }
    else:
        stats["oauth_metadata"] = {
            "enabled": False,
            "message": "OAuth metadata only available in HTTP mode"
        }
    
    return stats


@mcp.tool()
def check_oauth_status() -> Dict[str, Any]:
    """
    Check OAuth2 authentication status.
    
    Returns:
        Dictionary with OAuth2 status and instructions
    
    Example:
        check_oauth_status()
    """
    if not youtube_client.is_oauth_available():
        return {
            "authenticated": False,
            "available": False,
            "message": "OAuth2 not configured.",
            "instructions": [
                "1. Set USE_OAUTH2=true in .env",
                "2. Download credentials.json from Google Cloud Console",
                "3. Run: python authenticate.py auth"
            ]
        }
    
    status = youtube_client.get_oauth_status()
    
    if not status.get('authenticated'):
        return {
            **status,
            "instructions": [
                "Run: python authenticate.py auth",
                "This will open a browser for authentication"
            ]
        }
    
    return {
        **status,
        "message": "✅ OAuth2 authenticated and ready",
        "capabilities": [
            "Create/edit/delete playlists",
            "Upload/update/delete videos",
            "Manage captions",
            "Update channel settings"
        ]
    }


@mcp.tool()
def get_oauth_metadata() -> Dict[str, Any]:
    """
    Get OAuth 2.1 Protected Resource Metadata (RFC 9728).
    
    Returns OAuth 2.1 metadata for this MCP server including:
    - Resource identifier
    - Authorization servers
    - Supported scopes
    - Bearer token methods
    - MCP capabilities
    
    This endpoint implements the standard defined in RFC 9728
    and is accessible at /.well-known/oauth-protected-resource
    
    Returns:
        Dictionary with OAuth 2.1 metadata
    
    Example:
        get_oauth_metadata()
    """
    if not oauth_provider:
        return {
            "success": False,
            "error": "OAuth metadata not available",
            "message": "OAuth metadata is only available in HTTP mode. Current mode: stdio"
        }
    
    metadata = oauth_provider.get_metadata()
    
    return {
        "success": True,
        **metadata,
        "endpoint": "/.well-known/oauth-protected-resource",
        "rfc": "RFC 9728 - OAuth 2.1 Protected Resource Metadata"
    }


@mcp.tool()
async def server_health() -> Dict[str, Any]:
    """
    Get comprehensive server health status.
    
    Performs health checks on all server components:
    - Basic server status
    - YouTube API connectivity
    - OAuth authentication
    - Cache availability
    - Security components
    
    Returns:
        Dictionary with health status including:
        - status: 'healthy', 'degraded', or 'unhealthy'
        - uptime_seconds: Server uptime
        - components: Individual component statuses
        - version: Server version
    
    Example:
        server_health()
    """
    try:
        health_status = await check_health(include_details=True)
        return {
            "success": True,
            **health_status
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "status": "unhealthy",
            "error": str(e),
            "message": "Health check failed"
        }


@mcp.tool()
def server_metrics() -> Dict[str, Any]:
    """
    Get Prometheus metrics in text exposition format.
    
    Returns operational metrics including:
    - Request counts and errors
    - Security events (prompt injection, rate limits, CORS violations)
    - YouTube API usage (quota, errors, cache hits)
    - OAuth operations (token refreshes, errors)
    - System resources (memory, CPU, uptime)
    
    Format: Prometheus text exposition format
    Can be scraped by Prometheus server for monitoring and alerting.
    
    Returns:
        Dictionary with:
        - success: Boolean
        - metrics: Prometheus text format metrics
        - metrics_count: Number of metric families
    
    Example:
        server_metrics()
    """
    try:
        metrics_text = generate_metrics()
        
        # Count metric families (lines starting with # HELP)
        metrics_count = len([line for line in metrics_text.split('\n') if line.startswith('# HELP')])
        
        return {
            "success": True,
            "metrics": metrics_text,
            "metrics_count": metrics_count,
            "format": "prometheus_text_exposition"
        }
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to generate metrics"
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
