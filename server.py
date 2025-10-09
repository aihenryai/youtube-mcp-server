#!/usr/bin/env python3
"""
YouTube MCP Server
A comprehensive Model Context Protocol server for YouTube data extraction.

Provides tools for:
- Video transcripts
- Video metadata
- Channel information
- Comments
- Video analytics
"""

import os
import re
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs

from fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize MCP server
mcp = FastMCP("YouTube MCP Server")

# YouTube API setup
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY environment variable is required")

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_video_id(url_or_id: str) -> str:
    """
    Extract video ID from various YouTube URL formats or return as-is if already an ID.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    - VIDEO_ID (direct)
    """
    # If it's already a video ID (11 characters, alphanumeric with - and _)
    if re.match(r'^[A-Za-z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # Parse URL
    parsed = urlparse(url_or_id)
    
    # youtube.com/watch?v=...
    if parsed.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        query_params = parse_qs(parsed.query)
        if 'v' in query_params:
            return query_params['v'][0]
    
    # youtu.be/...
    if parsed.hostname == 'youtu.be':
        return parsed.path.lstrip('/')
    
    raise ValueError(f"Could not extract video ID from: {url_or_id}")


def extract_channel_id(url_or_id: str) -> str:
    """
    Extract channel ID from YouTube channel URL or return as-is if already an ID.
    
    Supports:
    - https://www.youtube.com/channel/CHANNEL_ID
    - https://www.youtube.com/@username
    - CHANNEL_ID (direct)
    """
    # If it looks like a channel ID (starts with UC and is 24 chars)
    if url_or_id.startswith('UC') and len(url_or_id) == 24:
        return url_or_id
    
    # Parse URL
    parsed = urlparse(url_or_id)
    
    # youtube.com/channel/...
    if '/channel/' in url_or_id:
        return url_or_id.split('/channel/')[-1].split('?')[0].split('/')[0]
    
    # youtube.com/@username - need to resolve via API
    if '/@' in url_or_id or url_or_id.startswith('@'):
        username = url_or_id.split('/@')[-1].split('?')[0].split('/')[0]
        if username.startswith('@'):
            username = username[1:]
        
        try:
            response = youtube.channels().list(
                part='id',
                forHandle=username
            ).execute()
            
            if response['items']:
                return response['items'][0]['id']
        except HttpError:
            pass
    
    raise ValueError(f"Could not extract channel ID from: {url_or_id}")


# ============================================================================
# MCP TOOLS
# ============================================================================

@mcp.tool()
def get_video_transcript(
    video_url: str,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Extract video transcript/subtitles from a YouTube video.
    
    Args:
        video_url: YouTube video URL or video ID
        language: Language code (e.g., 'en', 'es', 'fr', 'he'). Default is 'en'
    
    Returns:
        Dictionary containing:
        - video_id: The video ID
        - language: Language of the transcript
        - transcript: List of transcript segments with text and timestamps
        - full_text: Complete transcript as a single string
    
    Example:
        get_video_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    """
    try:
        video_id = extract_video_id(video_url)
        
        # Get transcript
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get transcript in requested language
        try:
            transcript = transcript_list.find_transcript([language])
        except:
            # Fallback to first available transcript
            transcript = transcript_list.find_generated_transcript(['en'])
        
        # Fetch the transcript
        transcript_data = transcript.fetch()
        
        # Create full text
        full_text = " ".join([entry['text'] for entry in transcript_data])
        
        return {
            "success": True,
            "video_id": video_id,
            "language": transcript.language_code,
            "is_generated": transcript.is_generated,
            "transcript": transcript_data,
            "full_text": full_text,
            "segment_count": len(transcript_data)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve transcript. The video may not have captions available."
        }


@mcp.tool()
def get_video_info(video_url: str) -> Dict[str, Any]:
    """
    Get comprehensive metadata for a YouTube video.
    
    Args:
        video_url: YouTube video URL or video ID
    
    Returns:
        Dictionary containing:
        - video_id: Video ID
        - title: Video title
        - description: Full video description
        - channel_id: Channel ID
        - channel_title: Channel name
        - publish_date: Publication date
        - duration: Video duration
        - view_count: Number of views
        - like_count: Number of likes
        - comment_count: Number of comments
        - tags: Video tags
        - thumbnails: Available thumbnail URLs
        - category_id: Video category
    
    Example:
        get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    """
    try:
        video_id = extract_video_id(video_url)
        
        # Request video details
        response = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
        ).execute()
        
        if not response['items']:
            return {
                "success": False,
                "error": "Video not found",
                "video_id": video_id
            }
        
        video = response['items'][0]
        snippet = video['snippet']
        statistics = video['statistics']
        content_details = video['contentDetails']
        
        return {
            "success": True,
            "video_id": video_id,
            "title": snippet['title'],
            "description": snippet['description'],
            "channel_id": snippet['channelId'],
            "channel_title": snippet['channelTitle'],
            "publish_date": snippet['publishedAt'],
            "duration": content_details['duration'],
            "view_count": int(statistics.get('viewCount', 0)),
            "like_count": int(statistics.get('likeCount', 0)),
            "comment_count": int(statistics.get('commentCount', 0)),
            "tags": snippet.get('tags', []),
            "thumbnails": snippet['thumbnails'],
            "category_id": snippet['categoryId'],
            "default_language": snippet.get('defaultLanguage'),
            "default_audio_language": snippet.get('defaultAudioLanguage')
        }
        
    except HttpError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve video information"
        }


@mcp.tool()
def get_channel_info(channel_id: str) -> Dict[str, Any]:
    """
    Get information and statistics for a YouTube channel.
    
    Args:
        channel_id: YouTube channel ID, channel URL, or @username
    
    Returns:
        Dictionary containing:
        - channel_id: Channel ID
        - title: Channel name
        - description: Channel description
        - custom_url: Custom channel URL (if available)
        - published_at: Channel creation date
        - subscriber_count: Number of subscribers
        - video_count: Total videos published
        - view_count: Total channel views
        - thumbnails: Channel thumbnail URLs
        - country: Channel's country (if specified)
    
    Example:
        get_channel_info("UC_x5XG1OV2P6uZZ5FSM9Ttw")
        get_channel_info("@googledev")
    """
    try:
        resolved_channel_id = extract_channel_id(channel_id)
        
        # Request channel details
        response = youtube.channels().list(
            part='snippet,statistics,contentDetails',
            id=resolved_channel_id
        ).execute()
        
        if not response['items']:
            return {
                "success": False,
                "error": "Channel not found",
                "channel_id": channel_id
            }
        
        channel = response['items'][0]
        snippet = channel['snippet']
        statistics = channel['statistics']
        
        return {
            "success": True,
            "channel_id": channel['id'],
            "title": snippet['title'],
            "description": snippet['description'],
            "custom_url": snippet.get('customUrl'),
            "published_at": snippet['publishedAt'],
            "subscriber_count": int(statistics.get('subscriberCount', 0)),
            "video_count": int(statistics.get('videoCount', 0)),
            "view_count": int(statistics.get('viewCount', 0)),
            "thumbnails": snippet['thumbnails'],
            "country": snippet.get('country'),
            "hidden_subscriber_count": statistics.get('hiddenSubscriberCount', False)
        }
        
    except HttpError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve channel information"
        }


@mcp.tool()
def get_video_comments(
    video_url: str,
    max_results: int = 100,
    include_replies: bool = True
) -> Dict[str, Any]:
    """
    Fetch comments from a YouTube video.
    
    Args:
        video_url: YouTube video URL or video ID
        max_results: Maximum number of top-level comments to retrieve (default: 100, max: 100)
        include_replies: Whether to include replies to comments (default: True)
    
    Returns:
        Dictionary containing:
        - video_id: Video ID
        - comment_count: Total number of comments retrieved
        - comments: List of comment objects with:
            - id: Comment ID
            - author: Comment author name
            - text: Comment text
            - like_count: Number of likes
            - published_at: Publication date
            - updated_at: Last update date
            - reply_count: Number of replies
            - replies: List of reply objects (if include_replies=True)
    
    Example:
        get_video_comments("https://www.youtube.com/watch?v=dQw4w9WgXcQ", max_results=50)
    """
    try:
        video_id = extract_video_id(video_url)
        
        # Ensure max_results is within limits
        max_results = min(max_results, 100)
        
        comments = []
        
        # Request top-level comments
        response = youtube.commentThreads().list(
            part='snippet,replies',
            videoId=video_id,
            maxResults=max_results,
            textFormat='plainText',
            order='relevance'  # Can be 'time' or 'relevance'
        ).execute()
        
        for item in response['items']:
            top_comment = item['snippet']['topLevelComment']['snippet']
            
            comment_data = {
                "id": item['id'],
                "author": top_comment['authorDisplayName'],
                "text": top_comment['textDisplay'],
                "like_count": top_comment['likeCount'],
                "published_at": top_comment['publishedAt'],
                "updated_at": top_comment['updatedAt'],
                "reply_count": item['snippet']['totalReplyCount'],
                "replies": []
            }
            
            # Add replies if available and requested
            if include_replies and 'replies' in item:
                for reply in item['replies']['comments']:
                    reply_snippet = reply['snippet']
                    comment_data['replies'].append({
                        "id": reply['id'],
                        "author": reply_snippet['authorDisplayName'],
                        "text": reply_snippet['textDisplay'],
                        "like_count": reply_snippet['likeCount'],
                        "published_at": reply_snippet['publishedAt'],
                        "updated_at": reply_snippet['updatedAt']
                    })
            
            comments.append(comment_data)
        
        return {
            "success": True,
            "video_id": video_id,
            "comment_count": len(comments),
            "total_reply_count": sum(c['reply_count'] for c in comments),
            "comments": comments
        }
        
    except HttpError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve comments. Comments may be disabled for this video."
        }


@mcp.tool()
def search_videos(
    query: str,
    max_results: int = 10,
    order: str = "relevance"
) -> Dict[str, Any]:
    """
    Search for YouTube videos.
    
    Args:
        query: Search query string
        max_results: Maximum number of results (default: 10, max: 50)
        order: Sort order - 'relevance', 'date', 'viewCount', 'rating' (default: 'relevance')
    
    Returns:
        Dictionary containing:
        - query: The search query
        - result_count: Number of results found
        - videos: List of video objects with:
            - video_id: Video ID
            - title: Video title
            - description: Video description
            - channel_id: Channel ID
            - channel_title: Channel name
            - published_at: Publication date
            - thumbnails: Thumbnail URLs
    
    Example:
        search_videos("Python tutorial", max_results=20, order="viewCount")
    """
    try:
        # Ensure max_results is within limits
        max_results = min(max_results, 50)
        
        # Valid order values
        valid_orders = ['relevance', 'date', 'viewCount', 'rating', 'title']
        if order not in valid_orders:
            order = 'relevance'
        
        # Search for videos
        response = youtube.search().list(
            part='snippet',
            q=query,
            type='video',
            maxResults=max_results,
            order=order
        ).execute()
        
        videos = []
        for item in response['items']:
            snippet = item['snippet']
            videos.append({
                "video_id": item['id']['videoId'],
                "title": snippet['title'],
                "description": snippet['description'],
                "channel_id": snippet['channelId'],
                "channel_title": snippet['channelTitle'],
                "published_at": snippet['publishedAt'],
                "thumbnails": snippet['thumbnails']
            })
        
        return {
            "success": True,
            "query": query,
            "order": order,
            "result_count": len(videos),
            "videos": videos
        }
        
    except HttpError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to search videos"
        }


# ============================================================================
# SERVER INITIALIZATION
# ============================================================================

if __name__ == "__main__":
    # Determine transport mode
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    port = int(os.getenv("PORT", 8080))
    
    if transport == "http":
        # Cloud deployment - use streamable-http
        print(f"🚀 Starting YouTube MCP Server in HTTP mode on port {port}")
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    else:
        # Local deployment - use stdio
        print("🚀 Starting YouTube MCP Server in stdio mode")
        mcp.run()
