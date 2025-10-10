"""
YouTube MCP Server - Playlist Updater
====================================

Handles updating metadata of existing YouTube playlists.

Features:
- Update title, description, tags
- Change privacy settings
- Modify default language
- Preserve existing data
- Batch update support

Part of Phase 2.3: Playlist Management
"""

from typing import Dict, Any, Optional, List
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)


class PlaylistUpdater:
    """
    Updates metadata for existing YouTube playlists.
    
    This class provides methods to update playlist information while
    preserving unchanged fields.
    """
    
    def __init__(self, youtube: Resource):
        """
        Initialize PlaylistUpdater.
        
        Args:
            youtube: Authenticated YouTube API resource
        """
        self.youtube = youtube
        logger.info("PlaylistUpdater initialized")
    
    def update_playlist(
        self,
        playlist_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        privacy_status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        default_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update playlist metadata.
        
        Only provided fields will be updated. Omitted fields remain unchanged.
        
        Args:
            playlist_id: ID of playlist to update
            title: New title (max 150 characters)
            description: New description (max 5000 characters)
            privacy_status: New privacy level - "public", "private", or "unlisted"
            tags: New list of tags
            default_language: New default language code
        
        Returns:
            Dictionary containing updated playlist information:
            - id: Playlist ID
            - title: Updated title
            - description: Updated description
            - privacy_status: Updated privacy status
            - url: Playlist URL
            - updated_at: Last update timestamp
            - changes_made: List of fields that were updated
        
        Raises:
            ValueError: If validation fails
            HttpError: If API request fails
        
        Example:
            ```python
            updater = PlaylistUpdater(youtube)
            
            # Update only title and privacy
            result = updater.update_playlist(
                playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                title="Updated Title",
                privacy_status="public"
            )
            
            print(f"Updated fields: {result['changes_made']}")
            ```
        
        Quota Cost: 50 units
        """
        if not playlist_id or not playlist_id.strip():
            raise ValueError("Playlist ID cannot be empty")
        
        # Get current playlist data
        try:
            current = self.youtube.playlists().list(
                part="snippet,status",
                id=playlist_id
            ).execute()
            
            if not current.get("items"):
                raise ValueError(f"Playlist not found: {playlist_id}")
            
            current_data = current["items"][0]
            
        except HttpError as e:
            logger.error(f"Failed to fetch playlist: {str(e)}")
            raise
        
        # Track changes
        changes_made = []
        
        # Prepare update body with current data
        update_body = {
            "id": playlist_id,
            "snippet": {
                "title": current_data["snippet"]["title"],
                "description": current_data["snippet"].get("description", ""),
            },
            "status": {
                "privacyStatus": current_data["status"]["privacyStatus"]
            }
        }
        
        # Update title if provided
        if title is not None:
            self._validate_title(title)
            update_body["snippet"]["title"] = title.strip()
            changes_made.append("title")
        
        # Update description if provided
        if description is not None:
            self._validate_description(description)
            update_body["snippet"]["description"] = description.strip()
            changes_made.append("description")
        
        # Update tags if provided
        if tags is not None:
            update_body["snippet"]["tags"] = [tag.strip() for tag in tags if tag.strip()]
            changes_made.append("tags")
        
        # Update default language if provided
        if default_language is not None:
            update_body["snippet"]["defaultLanguage"] = default_language
            changes_made.append("default_language")
        
        # Update privacy status if provided
        if privacy_status is not None:
            self._validate_privacy_status(privacy_status)
            update_body["status"]["privacyStatus"] = privacy_status
            changes_made.append("privacy_status")
        
        # If no changes, return current data
        if not changes_made:
            logger.warning(f"No changes specified for playlist: {playlist_id}")
            return {
                "id": playlist_id,
                "title": current_data["snippet"]["title"],
                "description": current_data["snippet"].get("description", ""),
                "privacy_status": current_data["status"]["privacyStatus"],
                "url": f"https://www.youtube.com/playlist?list={playlist_id}",
                "updated_at": current_data["snippet"].get("publishedAt"),
                "changes_made": []
            }
        
        logger.info(f"Updating playlist {playlist_id}: {', '.join(changes_made)}")
        
        # Perform update
        try:
            response = self.youtube.playlists().update(
                part="snippet,status",
                body=update_body
            ).execute()
            
            result = {
                "id": response["id"],
                "title": response["snippet"]["title"],
                "description": response["snippet"].get("description", ""),
                "privacy_status": response["status"]["privacyStatus"],
                "url": f"https://www.youtube.com/playlist?list={response['id']}",
                "updated_at": response["snippet"].get("publishedAt"),
                "changes_made": changes_made,
                "tags": response["snippet"].get("tags", [])
            }
            
            logger.info(f"✅ Playlist updated successfully: {playlist_id}")
            return result
            
        except HttpError as e:
            logger.error(f"Failed to update playlist: {str(e)}")
            raise
    
    def _validate_title(self, title: str) -> None:
        """Validate playlist title."""
        if not title or not title.strip():
            raise ValueError("Playlist title cannot be empty")
        
        if len(title) > 150:
            raise ValueError("Playlist title cannot exceed 150 characters")
    
    def _validate_description(self, description: str) -> None:
        """Validate playlist description."""
        if len(description) > 5000:
            raise ValueError("Playlist description cannot exceed 5000 characters")
    
    def _validate_privacy_status(self, privacy_status: str) -> None:
        """Validate privacy status."""
        valid_statuses = {"public", "private", "unlisted"}
        if privacy_status not in valid_statuses:
            raise ValueError(
                f"Invalid privacy status: {privacy_status}. "
                f"Must be one of: {', '.join(valid_statuses)}"
            )
    
    def get_playlist_info(self, playlist_id: str) -> Dict[str, Any]:
        """
        Get current playlist information.
        
        Args:
            playlist_id: Playlist ID
        
        Returns:
            Dictionary with playlist details
        
        Raises:
            ValueError: If playlist not found
            HttpError: If API request fails
        
        Example:
            ```python
            updater = PlaylistUpdater(youtube)
            info = updater.get_playlist_info("PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            print(f"Current title: {info['title']}")
            print(f"Privacy: {info['privacy_status']}")
            ```
        
        Quota Cost: 1 unit
        """
        if not playlist_id or not playlist_id.strip():
            raise ValueError("Playlist ID cannot be empty")
        
        try:
            response = self.youtube.playlists().list(
                part="snippet,status,contentDetails",
                id=playlist_id
            ).execute()
            
            if not response.get("items"):
                raise ValueError(f"Playlist not found: {playlist_id}")
            
            item = response["items"][0]
            
            return {
                "id": item["id"],
                "title": item["snippet"]["title"],
                "description": item["snippet"].get("description", ""),
                "privacy_status": item["status"]["privacyStatus"],
                "published_at": item["snippet"]["publishedAt"],
                "channel_id": item["snippet"]["channelId"],
                "channel_title": item["snippet"]["channelTitle"],
                "item_count": item["contentDetails"]["itemCount"],
                "url": f"https://www.youtube.com/playlist?list={item['id']}",
                "thumbnails": item["snippet"].get("thumbnails", {}),
                "tags": item["snippet"].get("tags", [])
            }
            
        except HttpError as e:
            logger.error(f"Failed to get playlist info: {str(e)}")
            raise
