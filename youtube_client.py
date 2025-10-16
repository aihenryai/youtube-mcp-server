"""
YouTube API Client Manager
Handles both API Key (read-only) and OAuth2 (full access) authentication
"""

import os
import logging
from typing import Optional
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Try to import OAuth2 (optional)
try:
    from auth import OAuth2Manager
    OAUTH2_AVAILABLE = True
except ImportError:
    OAUTH2_AVAILABLE = False
    OAuth2Manager = None

load_dotenv()
logger = logging.getLogger(__name__)


class YouTubeClient:
    """
    Unified YouTube API client supporting both authentication methods
    
    Modes:
    1. API Key (read-only) - for get operations
    2. OAuth2 (full access) - for write operations
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        use_oauth: bool = False,
        oauth_credentials_file: str = "credentials.json"
    ):
        """
        Initialize YouTube API client
        
        Args:
            api_key: YouTube Data API key (for read-only)
            use_oauth: Use OAuth2 for authenticated operations
            oauth_credentials_file: Path to OAuth2 credentials
        """
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.use_oauth = use_oauth
        self.oauth_manager = None
        self.youtube = None
        self.youtube_oauth = None
        
        # Initialize API key client (always available for read operations)
        if self.api_key:
            try:
                self.youtube = build(
                    "youtube",
                    "v3",
                    developerKey=self.api_key,
                    cache_discovery=False
                )
                logger.info("✅ YouTube API client (API key) initialized")
            except Exception as e:
                logger.error(f"Failed to initialize API key client: {e}")
        
        # Initialize OAuth2 if requested
        if use_oauth:
            if not OAUTH2_AVAILABLE:
                logger.warning(
                    "⚠️  OAuth2 requested but not available. "
                    "Install with: pip install cryptography"
                )
            else:
                try:
                    self.oauth_manager = OAuth2Manager(
                        credentials_file=oauth_credentials_file
                    )
                    # Don't authorize yet - lazy load
                    logger.info("✅ OAuth2 manager initialized (not yet authorized)")
                except Exception as e:
                    logger.warning(f"OAuth2 initialization failed: {e}")
    
    def get_client(self, require_oauth: bool = False):
        """
        Get YouTube API client
        
        Args:
            require_oauth: If True, ensures OAuth2 client is used
        
        Returns:
            Authenticated YouTube API client
        """
        # If OAuth2 is required and available
        if require_oauth:
            if not self.oauth_manager:
                raise RuntimeError(
                    "OAuth2 authentication required but not configured.\n"
                    "Please run: python authenticate.py auth"
                )
            
            # Lazy load OAuth2 client
            if not self.youtube_oauth:
                try:
                    self.youtube_oauth = self.oauth_manager.get_authenticated_service()
                    logger.info("✅ OAuth2 client authenticated")
                except Exception as e:
                    raise RuntimeError(
                        f"OAuth2 authentication failed: {e}\n"
                        "Please run: python authenticate.py auth"
                    )
            
            return self.youtube_oauth
        
        # For read-only operations, prefer API key
        if self.youtube:
            return self.youtube
        
        # Fallback to OAuth2 if available
        if self.oauth_manager:
            return self.get_client(require_oauth=True)
        
        raise RuntimeError(
            "No authentication method available.\n"
            "Provide YOUTUBE_API_KEY or configure OAuth2."
        )
    
    def is_oauth_available(self) -> bool:
        """Check if OAuth2 is configured and ready"""
        return self.oauth_manager is not None
    
    def get_oauth_status(self) -> dict:
        """Get OAuth2 authentication status"""
        if not self.oauth_manager:
            return {
                'available': False,
                'message': 'OAuth2 not configured'
            }
        
        return {
            'available': True,
            **self.oauth_manager.get_token_info()
        }
