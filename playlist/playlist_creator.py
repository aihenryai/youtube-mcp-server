"""
YouTube MCP Server - Playlist Creator
====================================

Handles creation of new YouTube playlists with comprehensive metadata.

Features:
- Create public, private, or unlisted playlists
- Set title, description, and tags
- Default language configuration
- Privacy status management
- Automatic validation

Part of Phase 2.3: Playlist Management
"""

from typing import Dict, Any, Optional, List
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)


class PlaylistCreator:
    """
    Creates and manages new YouTube playlists.
    
    This class provides methods to create playlists with full metadata control,
    including privacy settings, descriptions, and localization.
    """
    
    def __init__(self, youtube: Resource):
        """
        Initialize PlaylistCreator.
        
        Args:
            youtube: Authenticated YouTube API resource
        """
        self.youtube = youtube
        logger.info("PlaylistCreator initialized")
    
    def create_playlist(
        self,
        title: str,
        description: str = "",
        privacy_status: str = "private",
        default_language: str = "en",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new playlist with specified metadata.
        
        Args:
            title: Playlist title (required, max 150 characters)
            description: Playlist description (optional, max 5000 characters)
            privacy_status: Privacy level - "public", "private", or "unlisted"
            default_language: Default language code (ISO 639-1)
            tags: List of tags for the playlist (optional)
        
        Returns:
            Dictionary containing:
            - id: Playlist ID
            - title: Playlist title
            - description: Playlist description
            - privacy_status: Privacy setting
            - url: Direct URL to playlist
            - published_at: Creation timestamp
            - item_count: Number of items (initially 0)
        
        Raises:
            ValueError: If validation fails
            HttpError: If API request fails
        
        Example:
            ```python
            creator = PlaylistCreator(youtube)
            
            # Create a private playlist
            result = creator.create_playlist(
                title="My Favorite Videos",
                description="Collection of interesting content",
                privacy_status="private",
                tags=["favorites", "collection"]
            )
            
            print(f"Created playlist: {result['url']}")
            print(f"Playlist ID: {result['id']}")
            ```
        
        Quota Cost: 50 units
        """
        # Validate inputs
        self._validate_title(title)
        self._validate_description(description)
        self._validate_privacy_status(privacy_status)
        
        logger.info(f"Creating playlist: {title} (privacy: {privacy_status})")
        
        # Prepare request body
        playlist_body = {
            "snippet": {
                "title": title.strip(),
                "description": description.strip(),
                "defaultLanguage": default_language,
            },
            "status": {
                "privacyStatus": privacy_status
            }
        }
        
        # Add tags if provided
        if tags:
            playlist_body["snippet"]["tags"] = [tag.strip() for tag in tags if tag.strip()]
        
        try:
            # Create playlist
            response = self.youtube.playlists().insert(
                part="snippet,status",
                body=playlist_body
            ).execute()
            
            # Format response
            playlist_id = response["id"]
            result = {
                "id": playlist_id,
                "title": response["snippet"]["title"],
                "description": response["snippet"].get("description", ""),
                "privacy_status": response["status"]["privacyStatus"],
                "url": f"https://www.youtube.com/playlist?list={playlist_id}",
                "published_at": response["snippet"]["publishedAt"],
                "item_count": 0,
                "tags": response["snippet"].get("tags", [])
            }
            
            logger.info(f"✅ Playlist created successfully: {playlist_id}")
            return result
            
        except HttpError as e:
            error_msg = f"Failed to create playlist: {str(e)}"
            logger.error(error_msg)
            raise
    
    def _validate_title(self, title: str) -> None:
        """
        Validate playlist title.
        
        Args:
            title: Title to validate
        
        Raises:
            ValueError: If title is invalid
        """
        if not title or not title.strip():
            raise ValueError("Playlist title cannot be empty")
        
        if len(title) > 150:
            raise ValueError("Playlist title cannot exceed 150 characters")
    
    def _validate_description(self, description: str) -> None:
        """
        Validate playlist description.
        
        Args:
            description: Description to validate
        
        Raises:
            ValueError: If description is invalid
        """
        if len(description) > 5000:
            raise ValueError("Playlist description cannot exceed 5000 characters")
    
    def _validate_privacy_status(self, privacy_status: str) -> None:
        """
        Validate privacy status.
        
        Args:
            privacy_status: Privacy status to validate
        
        Raises:
            ValueError: If privacy status is invalid
        """
        valid_statuses = {"public", "private", "unlisted"}
        if privacy_status not in valid_statuses:
            raise ValueError(
                f"Invalid privacy status: {privacy_status}. "
                f"Must be one of: {', '.join(valid_statuses)}"
            )
    
    def delete_playlist(self, playlist_id: str) -> Dict[str, Any]:
        """
        Delete a playlist.
        
        Args:
            playlist_id: ID of playlist to delete
        
        Returns:
            Dictionary with deletion confirmation
        
        Raises:
            ValueError: If playlist_id is invalid
            HttpError: If deletion fails
        
        Example:
            ```python
            creator = PlaylistCreator(youtube)
            result = creator.delete_playlist("PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            print(result["message"])  # "Playlist deleted successfully"
            ```
        
        Quota Cost: 50 units
        """
        if not playlist_id or not playlist_id.strip():
            raise ValueError("Playlist ID cannot be empty")
        
        logger.info(f"Deleting playlist: {playlist_id}")
        
        try:
            self.youtube.playlists().delete(id=playlist_id).execute()
            
            logger.info(f"✅ Playlist deleted successfully: {playlist_id}")
            return {
                "success": True,
                "message": "Playlist deleted successfully",
                "playlist_id": playlist_id
            }
            
        except HttpError as e:
            if e.resp.status == 404:
                error_msg = f"Playlist not found: {playlist_id}"
            else:
                error_msg = f"Failed to delete playlist: {str(e)}"
            
            logger.error(error_msg)
            raise
