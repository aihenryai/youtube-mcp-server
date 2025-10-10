"""
YouTube MCP Server - Playlist Manager
====================================

Manages adding and removing videos from playlists.

Features:
- Add single or multiple videos
- Remove videos by ID or position
- Batch operations with progress tracking
- Duplicate detection
- Position management

Part of Phase 2.3: Playlist Management
"""

from typing import Dict, Any, List, Optional, Callable
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
import logging
import time

logger = logging.getLogger(__name__)


class PlaylistManager:
    """
    Manages videos within YouTube playlists.
    
    This class provides methods to add and remove videos from playlists,
    including batch operations with progress tracking.
    """
    
    def __init__(self, youtube: Resource):
        """
        Initialize PlaylistManager.
        
        Args:
            youtube: Authenticated YouTube API resource
        """
        self.youtube = youtube
        logger.info("PlaylistManager initialized")
    
    def add_video(
        self,
        playlist_id: str,
        video_id: str,
        position: Optional[int] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a video to a playlist.
        
        Args:
            playlist_id: Target playlist ID
            video_id: Video ID to add
            position: Position in playlist (0-based, None = end)
            note: Optional note about the video
        
        Returns:
            Dictionary containing:
            - playlist_item_id: ID of the added item
            - video_id: Added video ID
            - position: Position in playlist
            - playlist_id: Parent playlist ID
            - added_at: Timestamp when added
        
        Raises:
            ValueError: If validation fails
            HttpError: If API request fails
        
        Example:
            ```python
            manager = PlaylistManager(youtube)
            
            # Add video to end of playlist
            result = manager.add_video(
                playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                video_id="dQw4w9WgXcQ"
            )
            
            # Add video at specific position
            result = manager.add_video(
                playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                video_id="dQw4w9WgXcQ",
                position=0  # Add at beginning
            )
            ```
        
        Quota Cost: 50 units
        """
        self._validate_playlist_id(playlist_id)
        self._validate_video_id(video_id)
        
        if position is not None and position < 0:
            raise ValueError("Position must be non-negative")
        
        logger.info(f"Adding video {video_id} to playlist {playlist_id}")
        
        # Prepare request body
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
        
        # Add position if specified
        if position is not None:
            body["snippet"]["position"] = position
        
        # Add note if provided
        if note:
            body["snippet"]["note"] = note
        
        try:
            response = self.youtube.playlistItems().insert(
                part="snippet",
                body=body
            ).execute()
            
            result = {
                "playlist_item_id": response["id"],
                "video_id": response["snippet"]["resourceId"]["videoId"],
                "position": response["snippet"]["position"],
                "playlist_id": response["snippet"]["playlistId"],
                "added_at": response["snippet"]["publishedAt"]
            }
            
            logger.info(f"✅ Video added successfully: {video_id} at position {result['position']}")
            return result
            
        except HttpError as e:
            if "videoNotFound" in str(e) or e.resp.status == 404:
                error_msg = f"Video not found or unavailable: {video_id}"
            elif "forbidden" in str(e).lower():
                error_msg = "Video cannot be added (private/restricted)"
            elif "duplicate" in str(e).lower():
                error_msg = f"Video already exists in playlist: {video_id}"
            else:
                error_msg = f"Failed to add video: {str(e)}"
            
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def add_videos_batch(
        self,
        playlist_id: str,
        video_ids: List[str],
        skip_duplicates: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Add multiple videos to a playlist.
        
        Args:
            playlist_id: Target playlist ID
            video_ids: List of video IDs to add
            skip_duplicates: Skip videos already in playlist
            progress_callback: Function(current, total, video_id) called for each video
        
        Returns:
            Dictionary containing:
            - added: List of successfully added video IDs
            - failed: List of failed video IDs with error messages
            - skipped: List of skipped (duplicate) video IDs
            - total: Total videos processed
        
        Example:
            ```python
            def progress(current, total, video_id):
                print(f"Adding {current}/{total}: {video_id}")
            
            manager = PlaylistManager(youtube)
            result = manager.add_videos_batch(
                playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                video_ids=["video1", "video2", "video3"],
                progress_callback=progress
            )
            
            print(f"Added: {len(result['added'])}")
            print(f"Failed: {len(result['failed'])}")
            ```
        
        Quota Cost: 50 units per video
        """
        self._validate_playlist_id(playlist_id)
        
        if not video_ids:
            raise ValueError("video_ids list cannot be empty")
        
        added = []
        failed = []
        skipped = []
        
        # Get existing videos if skip_duplicates is enabled
        existing_videos = set()
        if skip_duplicates:
            try:
                existing_videos = self._get_playlist_video_ids(playlist_id)
            except Exception as e:
                logger.warning(f"Could not fetch existing videos: {e}")
        
        total = len(video_ids)
        logger.info(f"Adding {total} videos to playlist {playlist_id}")
        
        for idx, video_id in enumerate(video_ids, 1):
            # Progress callback
            if progress_callback:
                progress_callback(idx, total, video_id)
            
            # Skip duplicates
            if skip_duplicates and video_id in existing_videos:
                logger.info(f"Skipping duplicate: {video_id}")
                skipped.append(video_id)
                continue
            
            # Attempt to add video
            try:
                self.add_video(playlist_id, video_id)
                added.append(video_id)
                
                # Rate limiting - wait between requests
                if idx < total:
                    time.sleep(0.5)  # 500ms delay
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to add {video_id}: {error_msg}")
                failed.append({
                    "video_id": video_id,
                    "error": error_msg
                })
        
        result = {
            "added": added,
            "failed": failed,
            "skipped": skipped,
            "total": total
        }
        
        logger.info(
            f"✅ Batch complete: {len(added)} added, "
            f"{len(failed)} failed, {len(skipped)} skipped"
        )
        
        return result
    
    def remove_video(
        self,
        playlist_item_id: str
    ) -> Dict[str, Any]:
        """
        Remove a video from a playlist using playlist item ID.
        
        Args:
            playlist_item_id: ID of the playlist item to remove
        
        Returns:
            Dictionary with removal confirmation
        
        Raises:
            ValueError: If playlist_item_id is invalid
            HttpError: If removal fails
        
        Example:
            ```python
            manager = PlaylistManager(youtube)
            result = manager.remove_video("UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxW1FVGVZQllGQU4")
            print(result["message"])
            ```
        
        Quota Cost: 50 units
        """
        if not playlist_item_id or not playlist_item_id.strip():
            raise ValueError("Playlist item ID cannot be empty")
        
        logger.info(f"Removing playlist item: {playlist_item_id}")
        
        try:
            self.youtube.playlistItems().delete(
                id=playlist_item_id
            ).execute()
            
            logger.info(f"✅ Playlist item removed: {playlist_item_id}")
            return {
                "success": True,
                "message": "Video removed from playlist successfully",
                "playlist_item_id": playlist_item_id
            }
            
        except HttpError as e:
            if e.resp.status == 404:
                error_msg = f"Playlist item not found: {playlist_item_id}"
            else:
                error_msg = f"Failed to remove video: {str(e)}"
            
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def remove_videos_batch(
        self,
        playlist_item_ids: List[str],
        continue_on_error: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Remove multiple videos from playlists.
        
        Args:
            playlist_item_ids: List of playlist item IDs to remove
            continue_on_error: Continue if individual removals fail
            progress_callback: Function(current, total, item_id) called for each video
        
        Returns:
            Dictionary containing:
            - removed: List of successfully removed item IDs
            - failed: List of failed item IDs with error messages
            - total: Total items processed
        
        Quota Cost: 50 units per video
        """
        if not playlist_item_ids:
            raise ValueError("playlist_item_ids list cannot be empty")
        
        removed = []
        failed = []
        total = len(playlist_item_ids)
        
        logger.info(f"Removing {total} videos from playlists")
        
        for idx, item_id in enumerate(playlist_item_ids, 1):
            if progress_callback:
                progress_callback(idx, total, item_id)
            
            try:
                self.remove_video(item_id)
                removed.append(item_id)
                
                # Rate limiting
                if idx < total:
                    time.sleep(0.5)
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to remove {item_id}: {error_msg}")
                failed.append({
                    "playlist_item_id": item_id,
                    "error": error_msg
                })
                
                if not continue_on_error:
                    raise
        
        result = {
            "removed": removed,
            "failed": failed,
            "total": total
        }
        
        logger.info(f"✅ Batch removal complete: {len(removed)} removed, {len(failed)} failed")
        return result
    
    def _get_playlist_video_ids(self, playlist_id: str) -> set:
        """Get set of video IDs currently in playlist."""
        video_ids = set()
        next_page_token = None
        
        try:
            while True:
                response = self.youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                for item in response.get("items", []):
                    video_id = item["snippet"]["resourceId"]["videoId"]
                    video_ids.add(video_id)
                
                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break
            
            return video_ids
            
        except HttpError as e:
            logger.error(f"Failed to get playlist videos: {e}")
            raise
    
    def _validate_playlist_id(self, playlist_id: str) -> None:
        """Validate playlist ID format."""
        if not playlist_id or not playlist_id.strip():
            raise ValueError("Playlist ID cannot be empty")
    
    def _validate_video_id(self, video_id: str) -> None:
        """Validate video ID format."""
        if not video_id or not video_id.strip():
            raise ValueError("Video ID cannot be empty")
