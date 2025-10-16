"""
YouTube MCP Server - Captions Manager
====================================

Manages YouTube caption tracks - list, upload, update, download, delete.

Features:
- List caption tracks for a video
- Upload new caption tracks (SRT, VTT, TTML formats)
- Update existing caption tracks
- Download caption tracks
- Delete caption tracks
- Format conversion
- Language detection

Part of Phase 2.4: Captions Management
"""

from typing import Dict, Any, List, Optional, BinaryIO
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import logging
import io
import re

logger = logging.getLogger(__name__)


class CaptionsManager:
    """
    Manages caption tracks for YouTube videos.
    
    Provides methods to list, upload, update, download, and delete
    caption tracks with support for multiple formats and languages.
    """
    
    # Supported caption formats
    SUPPORTED_FORMATS = ['srt', 'vtt', 'ttml', 'sbv', 'sub']
    
    # Caption track kinds
    TRACK_KINDS = ['standard', 'ASR', 'forced']
    
    def __init__(self, youtube: Resource):
        """
        Initialize CaptionsManager.
        
        Args:
            youtube: Authenticated YouTube API resource with captions scope
        """
        self.youtube = youtube
        logger.info("CaptionsManager initialized")
    
    def list_captions(
        self,
        video_id: str,
        include_auto_generated: bool = True
    ) -> Dict[str, Any]:
        """
        List all caption tracks for a video.
        
        Args:
            video_id: YouTube video ID
            include_auto_generated: Include auto-generated captions
        
        Returns:
            Dictionary containing:
            - video_id: The video ID
            - tracks: List of caption tracks
            - total_count: Number of tracks
        
        Example:
            ```python
            manager = CaptionsManager(youtube)
            
            tracks = manager.list_captions("dQw4w9WgXcQ")
            for track in tracks['tracks']:
                print(f"{track['language']}: {track['name']}")
            ```
        
        Quota Cost: 50 units
        """
        self._validate_video_id(video_id)
        
        logger.info(f"Listing captions for video: {video_id}")
        
        try:
            response = self.youtube.captions().list(
                part='snippet',
                videoId=video_id
            ).execute()
            
            tracks = []
            for item in response.get('items', []):
                snippet = item['snippet']
                
                # Filter auto-generated if requested
                if not include_auto_generated and snippet['trackKind'] == 'ASR':
                    continue
                
                track_info = {
                    'id': item['id'],
                    'language': snippet['language'],
                    'name': snippet.get('name', ''),
                    'track_kind': snippet['trackKind'],
                    'is_auto_generated': snippet['trackKind'] == 'ASR',
                    'is_cc': snippet.get('isCC', False),
                    'is_draft': snippet.get('isDraft', False),
                    'is_easy_reader': snippet.get('isEasyReader', False),
                    'is_large': snippet.get('isLarge', False),
                    'status': snippet.get('status', 'unknown'),
                    'audio_track_type': snippet.get('audioTrackType', 'primary'),
                    'last_updated': snippet.get('lastUpdated', '')
                }
                
                tracks.append(track_info)
            
            result = {
                'video_id': video_id,
                'tracks': tracks,
                'total_count': len(tracks),
                'has_auto_generated': any(t['is_auto_generated'] for t in tracks),
                'languages': list(set(t['language'] for t in tracks))
            }
            
            logger.info(f"✅ Found {len(tracks)} caption tracks")
            return result
            
        except HttpError as e:
            if e.resp.status == 404:
                error_msg = f"Video not found: {video_id}"
            else:
                error_msg = f"Failed to list captions: {str(e)}"
            
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def upload_caption(
        self,
        video_id: str,
        caption_file: str,
        language: str,
        name: Optional[str] = None,
        is_draft: bool = False
    ) -> Dict[str, Any]:
        """
        Upload a new caption track to a video.
        
        Args:
            video_id: YouTube video ID
            caption_file: Path to caption file (SRT, VTT, TTML, etc.)
            language: ISO 639-1 language code (e.g., 'en', 'he', 'es')
            name: Display name for the caption track
            is_draft: Upload as draft (not visible to viewers)
        
        Returns:
            Dictionary containing:
            - caption_id: ID of uploaded caption track
            - video_id: Video ID
            - language: Language code
            - name: Track name
            - status: Upload status
        
        Example:
            ```python
            manager = CaptionsManager(youtube)
            
            # Upload Hebrew captions
            result = manager.upload_caption(
                video_id="dQw4w9WgXcQ",
                caption_file="/path/to/captions_he.srt",
                language="he",
                name="Hebrew Subtitles"
            )
            
            print(f"Caption ID: {result['caption_id']}")
            ```
        
        Quota Cost: 400 units (expensive!)
        
        Note:
            Requires OAuth2 authentication with youtube.force-ssl scope.
            Caption file must be in a supported format (SRT, VTT, TTML, SBV, SUB).
        """
        self._validate_video_id(video_id)
        self._validate_language_code(language)
        
        # Detect file format
        file_format = self._detect_format(caption_file)
        if not file_format:
            raise ValueError(
                f"Unsupported caption format. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        logger.info(f"Uploading {file_format.upper()} captions for video {video_id} (language: {language})")
        
        # Prepare request body
        body = {
            'snippet': {
                'videoId': video_id,
                'language': language,
                'name': name or f"{language} captions",
                'isDraft': is_draft
            }
        }
        
        # Prepare media upload
        media = MediaFileUpload(
            caption_file,
            mimetype='text/plain',
            resumable=True
        )
        
        try:
            response = self.youtube.captions().insert(
                part='snippet',
                body=body,
                media_body=media
            ).execute()
            
            result = {
                'caption_id': response['id'],
                'video_id': video_id,
                'language': response['snippet']['language'],
                'name': response['snippet']['name'],
                'track_kind': response['snippet']['trackKind'],
                'is_draft': response['snippet']['isDraft'],
                'status': 'uploaded',
                'format': file_format
            }
            
            logger.info(f"✅ Caption uploaded successfully: {result['caption_id']}")
            return result
            
        except HttpError as e:
            if 'duplicate' in str(e).lower():
                error_msg = f"Caption track already exists for language: {language}"
            elif 'invalidCaptionFile' in str(e):
                error_msg = "Invalid caption file format or content"
            elif 'forbidden' in str(e).lower():
                error_msg = "Permission denied - requires video owner authentication"
            else:
                error_msg = f"Failed to upload caption: {str(e)}"
            
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def download_caption(
        self,
        caption_id: str,
        output_file: Optional[str] = None,
        format: str = 'srt'
    ) -> Dict[str, Any]:
        """
        Download a caption track.
        
        Args:
            caption_id: Caption track ID
            output_file: Path to save caption file (optional)
            format: Output format - 'srt', 'vtt', 'ttml', 'sbv'
        
        Returns:
            Dictionary containing:
            - caption_id: Caption ID
            - format: Output format
            - content: Caption content (if no output_file)
            - file_path: Saved file path (if output_file provided)
            - size_bytes: File size
        
        Example:
            ```python
            manager = CaptionsManager(youtube)
            
            # Download to file
            result = manager.download_caption(
                caption_id="SwPG123abc",
                output_file="/path/to/save.srt",
                format="srt"
            )
            
            # Or get content directly
            result = manager.download_caption("SwPG123abc")
            print(result['content'])
            ```
        
        Quota Cost: 200 units
        """
        if format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format: {format}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        logger.info(f"Downloading caption {caption_id} (format: {format})")
        
        try:
            # Download caption
            request = self.youtube.captions().download(
                id=caption_id,
                tfmt=format
            )
            
            # Download to memory or file
            if output_file:
                with open(output_file, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        if status:
                            logger.info(f"Download progress: {int(status.progress() * 100)}%")
                
                # Get file size
                import os
                file_size = os.path.getsize(output_file)
                
                result = {
                    'caption_id': caption_id,
                    'format': format,
                    'file_path': output_file,
                    'size_bytes': file_size
                }
                
                logger.info(f"✅ Caption downloaded to: {output_file}")
            else:
                # Download to memory
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                
                content = fh.getvalue().decode('utf-8')
                
                result = {
                    'caption_id': caption_id,
                    'format': format,
                    'content': content,
                    'size_bytes': len(content.encode('utf-8'))
                }
                
                logger.info(f"✅ Caption downloaded to memory")
            
            return result
            
        except HttpError as e:
            if e.resp.status == 404:
                error_msg = f"Caption track not found: {caption_id}"
            else:
                error_msg = f"Failed to download caption: {str(e)}"
            
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def update_caption(
        self,
        caption_id: str,
        caption_file: Optional[str] = None,
        name: Optional[str] = None,
        is_draft: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update an existing caption track.
        
        Args:
            caption_id: Caption track ID to update
            caption_file: New caption file (optional)
            name: New display name (optional)
            is_draft: Change draft status (optional)
        
        Returns:
            Dictionary with update confirmation
        
        Example:
            ```python
            manager = CaptionsManager(youtube)
            
            # Update caption content
            result = manager.update_caption(
                caption_id="SwPG123abc",
                caption_file="/path/to/updated_captions.srt"
            )
            
            # Update only metadata
            result = manager.update_caption(
                caption_id="SwPG123abc",
                name="Updated Caption Name",
                is_draft=False  # Publish caption
            )
            ```
        
        Quota Cost: 450 units (very expensive!)
        """
        if not caption_id:
            raise ValueError("Caption ID is required")
        
        if not any([caption_file, name is not None, is_draft is not None]):
            raise ValueError("At least one update parameter must be provided")
        
        logger.info(f"Updating caption: {caption_id}")
        
        # Build update body
        body = {
            'id': caption_id,
            'snippet': {}
        }
        
        if name is not None:
            body['snippet']['name'] = name
        
        if is_draft is not None:
            body['snippet']['isDraft'] = is_draft
        
        # Prepare media if updating content
        media = None
        if caption_file:
            media = MediaFileUpload(
                caption_file,
                mimetype='text/plain',
                resumable=True
            )
        
        try:
            response = self.youtube.captions().update(
                part='snippet',
                body=body,
                media_body=media
            ).execute()
            
            result = {
                'caption_id': response['id'],
                'language': response['snippet']['language'],
                'name': response['snippet']['name'],
                'is_draft': response['snippet']['isDraft'],
                'status': 'updated',
                'updated_content': caption_file is not None
            }
            
            logger.info(f"✅ Caption updated successfully")
            return result
            
        except HttpError as e:
            if e.resp.status == 404:
                error_msg = f"Caption track not found: {caption_id}"
            elif 'forbidden' in str(e).lower():
                error_msg = "Permission denied - requires video owner authentication"
            else:
                error_msg = f"Failed to update caption: {str(e)}"
            
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def delete_caption(self, caption_id: str) -> Dict[str, Any]:
        """
        Delete a caption track.
        
        Args:
            caption_id: Caption track ID to delete
        
        Returns:
            Dictionary with deletion confirmation
        
        Example:
            ```python
            manager = CaptionsManager(youtube)
            result = manager.delete_caption("SwPG123abc")
            print(result['message'])  # "Caption deleted successfully"
            ```
        
        Quota Cost: 50 units
        
        Note:
            Cannot delete auto-generated captions (ASR tracks).
        """
        if not caption_id:
            raise ValueError("Caption ID is required")
        
        logger.info(f"Deleting caption: {caption_id}")
        
        try:
            self.youtube.captions().delete(id=caption_id).execute()
            
            logger.info(f"✅ Caption deleted successfully")
            return {
                'success': True,
                'message': 'Caption deleted successfully',
                'caption_id': caption_id
            }
            
        except HttpError as e:
            if e.resp.status == 404:
                error_msg = f"Caption track not found: {caption_id}"
            elif 'cannotDeleteAutoCaption' in str(e):
                error_msg = "Cannot delete auto-generated captions"
            elif 'forbidden' in str(e).lower():
                error_msg = "Permission denied - requires video owner authentication"
            else:
                error_msg = f"Failed to delete caption: {str(e)}"
            
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def _validate_video_id(self, video_id: str) -> None:
        """Validate video ID format."""
        if not video_id or not re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
            raise ValueError(f"Invalid video ID: {video_id}")
    
    def _validate_language_code(self, language: str) -> None:
        """Validate ISO 639-1 language code."""
        if not language or len(language) != 2 or not language.isalpha():
            raise ValueError(
                f"Invalid language code: {language}. "
                "Must be ISO 639-1 (2-letter code, e.g., 'en', 'he')"
            )
    
    def _detect_format(self, file_path: str) -> Optional[str]:
        """Detect caption file format from extension."""
        extension = file_path.rsplit('.', 1)[-1].lower()
        return extension if extension in self.SUPPORTED_FORMATS else None
