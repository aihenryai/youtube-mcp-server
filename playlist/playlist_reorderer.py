"""
YouTube MCP Server - Playlist Reorderer
======================================

Handles reordering videos within playlists.

Features:
- Move video to specific position
- Swap two videos
- Move video to top/bottom
- Reverse playlist order
- Batch reorder operations

Part of Phase 2.3: Playlist Management
"""

from typing import Dict, Any, List, Optional
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
import logging
import time

logger = logging.getLogger(__name__)


class PlaylistReorderer:
    """
    Reorders videos within YouTube playlists.
    
    This class provides methods to change the position of videos in playlists,
    including moving, swapping, and batch reordering operations.
    """
    
    def __init__(self, youtube: Resource):
        """
        Initialize PlaylistReorderer.
        
        Args:
            youtube: Authenticated YouTube API resource
        """
        self.youtube = youtube
        logger.info("PlaylistReorderer initialized")
    
    def move_video(
        self,
        playlist_id: str,
        playlist_item_id: str,
        new_position: int
    ) -> Dict[str, Any]:
        """
        Move a video to a new position in the playlist.
        
        Args:
            playlist_id: Playlist ID containing the video
            playlist_item_id: ID of the playlist item to move
            new_position: New position (0-based index)
        
        Returns:
            Dictionary containing:
            - playlist_item_id: ID of moved item
            - old_position: Previous position
            - new_position: New position
            - video_id: ID of the moved video
        
        Raises:
            ValueError: If validation fails or position is invalid
            HttpError: If API request fails
        
        Example:
            ```python
            reorderer = PlaylistReorderer(youtube)
            
            # Move video to position 0 (top)
            result = reorderer.move_video(
                playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                playlist_item_id="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxW1FVGVZQllGQU4",
                new_position=0
            )
            
            print(f"Moved from position {result['old_position']} to {result['new_position']}")
            ```
        
        Quota Cost: 50 units
        """
        self._validate_playlist_id(playlist_id)
        
        if not playlist_item_id or not playlist_item_id.strip():
            raise ValueError("Playlist item ID cannot be empty")
        
        if new_position < 0:
            raise ValueError("Position must be non-negative")
        
        logger.info(f"Moving playlist item {playlist_item_id} to position {new_position}")
        
        # Get current item info
        try:
            item_response = self.youtube.playlistItems().list(
                part="snippet",
                id=playlist_item_id
            ).execute()
            
            if not item_response.get("items"):
                raise ValueError(f"Playlist item not found: {playlist_item_id}")
            
            current_item = item_response["items"][0]
            old_position = current_item["snippet"]["position"]
            video_id = current_item["snippet"]["resourceId"]["videoId"]
            
            # Check if already at target position
            if old_position == new_position:
                logger.info(f"Item already at position {new_position}")
                return {
                    "playlist_item_id": playlist_item_id,
                    "old_position": old_position,
                    "new_position": new_position,
                    "video_id": video_id,
                    "moved": False
                }
            
            # Update position
            update_body = {
                "id": playlist_item_id,
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    },
                    "position": new_position
                }
            }
            
            response = self.youtube.playlistItems().update(
                part="snippet",
                body=update_body
            ).execute()
            
            result = {
                "playlist_item_id": playlist_item_id,
                "old_position": old_position,
                "new_position": response["snippet"]["position"],
                "video_id": video_id,
                "moved": True
            }
            
            logger.info(
                f"✅ Video moved: position {old_position} → {result['new_position']}"
            )
            return result
            
        except HttpError as e:
            error_msg = f"Failed to move video: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def move_to_top(
        self,
        playlist_id: str,
        playlist_item_id: str
    ) -> Dict[str, Any]:
        """
        Move video to the top of the playlist (position 0).
        
        Args:
            playlist_id: Playlist ID
            playlist_item_id: Playlist item ID to move
        
        Returns:
            Move operation result
        
        Example:
            ```python
            reorderer = PlaylistReorderer(youtube)
            result = reorderer.move_to_top(
                playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                playlist_item_id="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxW1FVGVZQllGQU4"
            )
            ```
        
        Quota Cost: 50 units
        """
        return self.move_video(playlist_id, playlist_item_id, 0)
    
    def move_to_bottom(
        self,
        playlist_id: str,
        playlist_item_id: str
    ) -> Dict[str, Any]:
        """
        Move video to the bottom of the playlist.
        
        Args:
            playlist_id: Playlist ID
            playlist_item_id: Playlist item ID to move
        
        Returns:
            Move operation result
        
        Example:
            ```python
            reorderer = PlaylistReorderer(youtube)
            result = reorderer.move_to_bottom(
                playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                playlist_item_id="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxW1FVGVZQllGQU4"
            )
            ```
        
        Quota Cost: 51 units (1 to get count + 50 to move)
        """
        # Get playlist item count
        try:
            playlist_response = self.youtube.playlists().list(
                part="contentDetails",
                id=playlist_id
            ).execute()
            
            if not playlist_response.get("items"):
                raise ValueError(f"Playlist not found: {playlist_id}")
            
            item_count = playlist_response["items"][0]["contentDetails"]["itemCount"]
            last_position = max(0, item_count - 1)
            
            return self.move_video(playlist_id, playlist_item_id, last_position)
            
        except HttpError as e:
            error_msg = f"Failed to move video to bottom: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def swap_videos(
        self,
        playlist_id: str,
        item_id_1: str,
        item_id_2: str
    ) -> Dict[str, Any]:
        """
        Swap positions of two videos in a playlist.
        
        Args:
            playlist_id: Playlist ID
            item_id_1: First playlist item ID
            item_id_2: Second playlist item ID
        
        Returns:
            Dictionary containing swap results for both videos
        
        Example:
            ```python
            reorderer = PlaylistReorderer(youtube)
            result = reorderer.swap_videos(
                playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                item_id_1="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1",
                item_id_2="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx2"
            )
            ```
        
        Quota Cost: 102 units (2 units to fetch + 100 to swap)
        """
        # Get both items' positions
        try:
            items_response = self.youtube.playlistItems().list(
                part="snippet",
                id=f"{item_id_1},{item_id_2}"
            ).execute()
            
            items = items_response.get("items", [])
            if len(items) != 2:
                raise ValueError("Could not find both playlist items")
            
            # Extract positions
            item_1 = items[0]
            item_2 = items[1]
            pos_1 = item_1["snippet"]["position"]
            pos_2 = item_2["snippet"]["position"]
            
            logger.info(f"Swapping items at positions {pos_1} and {pos_2}")
            
            # Perform swaps (order matters - move to higher position first)
            if pos_1 > pos_2:
                result_1 = self.move_video(playlist_id, item_id_1, pos_2)
                time.sleep(0.5)  # Rate limiting
                result_2 = self.move_video(playlist_id, item_id_2, pos_1)
            else:
                result_2 = self.move_video(playlist_id, item_id_2, pos_1)
                time.sleep(0.5)  # Rate limiting
                result_1 = self.move_video(playlist_id, item_id_1, pos_2)
            
            logger.info(f"✅ Videos swapped successfully")
            return {
                "item_1": result_1,
                "item_2": result_2,
                "swapped": True
            }
            
        except HttpError as e:
            error_msg = f"Failed to swap videos: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def reverse_playlist(
        self,
        playlist_id: str
    ) -> Dict[str, Any]:
        """
        Reverse the order of all videos in a playlist.
        
        WARNING: This is quota-intensive for large playlists!
        
        Args:
            playlist_id: Playlist ID to reverse
        
        Returns:
            Dictionary containing:
            - total_items: Number of items processed
            - reversed: Number of items successfully reversed
            - failed: Number of items that failed
        
        Example:
            ```python
            reorderer = PlaylistReorderer(youtube)
            result = reorderer.reverse_playlist("PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            print(f"Reversed {result['reversed']} videos")
            ```
        
        Quota Cost: 1 unit (fetch) + 50 units per video
        """
        logger.info(f"Reversing playlist: {playlist_id}")
        
        # Get all items in current order
        items = self._get_all_playlist_items(playlist_id)
        total = len(items)
        
        if total == 0:
            return {
                "total_items": 0,
                "reversed": 0,
                "failed": 0,
                "message": "Playlist is empty"
            }
        
        logger.info(f"Found {total} items to reverse")
        
        # Reverse order
        reversed_count = 0
        failed_count = 0
        
        for idx, item in enumerate(reversed(items)):
            try:
                self.move_video(
                    playlist_id=playlist_id,
                    playlist_item_id=item["id"],
                    new_position=idx
                )
                reversed_count += 1
                
                # Rate limiting
                if idx < total - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Failed to move item {item['id']}: {e}")
                failed_count += 1
        
        result = {
            "total_items": total,
            "reversed": reversed_count,
            "failed": failed_count
        }
        
        logger.info(
            f"✅ Playlist reversed: {reversed_count}/{total} successful, "
            f"{failed_count} failed"
        )
        
        return result
    
    def _get_all_playlist_items(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get all items from a playlist."""
        items = []
        next_page_token = None
        
        try:
            while True:
                response = self.youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                items.extend(response.get("items", []))
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break
            
            return items
            
        except HttpError as e:
            logger.error(f"Failed to get playlist items: {e}")
            raise
    
    def _validate_playlist_id(self, playlist_id: str) -> None:
        """Validate playlist ID format."""
        if not playlist_id or not playlist_id.strip():
            raise ValueError("Playlist ID cannot be empty")
