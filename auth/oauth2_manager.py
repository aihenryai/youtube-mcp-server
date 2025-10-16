"""
OAuth2 Authentication Manager for YouTube MCP Server
Handles OAuth2 flow, token management, and auto-refresh
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import google.auth.exceptions

from .token_storage import TokenStorage

logger = logging.getLogger(__name__)


class OAuth2Manager:
    """
    Manages OAuth2 authentication for YouTube Data API
    
    Features:
    - Authorization Code Flow with local server
    - Encrypted token storage
    - Automatic token refresh
    - Multiple scope support
    - Session management
    """
    
    # YouTube API Scopes
    SCOPES = {
        'readonly': [
            'https://www.googleapis.com/auth/youtube.readonly'
        ],
        'upload': [
            'https://www.googleapis.com/auth/youtube.upload'
        ],
        'full': [
            'https://www.googleapis.com/auth/youtube',
            'https://www.googleapis.com/auth/youtube.force-ssl'
        ]
    }
    
    def __init__(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "token.json",
        scopes: List[str] = None,
        auto_refresh: bool = True
    ):
        """
        Initialize OAuth2 Manager
        
        Args:
            credentials_file: Path to OAuth2 client credentials (from Google Cloud Console)
            token_file: Path to store user tokens
            scopes: List of OAuth2 scopes (default: full access)
            auto_refresh: Auto-refresh expired tokens
        """
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.scopes = scopes or self.SCOPES['full']
        self.auto_refresh = auto_refresh
        
        # Initialize token storage
        self.token_storage = TokenStorage(str(self.token_file))
        
        # Current credentials
        self.creds: Optional[Credentials] = None
        
        # Validate credentials file exists
        if not self.credentials_file.exists():
            raise FileNotFoundError(
                f"OAuth2 credentials file not found: {self.credentials_file}\n"
                "Please download it from Google Cloud Console:\n"
                "1. Go to https://console.cloud.google.com/apis/credentials\n"
                "2. Create OAuth 2.0 Client ID (Desktop app)\n"
                "3. Download JSON and save as credentials.json"
            )
    
    def authorize(self, force_reauth: bool = False) -> Credentials:
        """
        Authorize user and get credentials
        
        Args:
            force_reauth: Force re-authentication even if valid token exists
        
        Returns:
            Valid OAuth2 credentials
        """
        # Load existing token if available
        if not force_reauth and self.token_file.exists():
            try:
                self.creds = self._load_credentials()
                
                # Check if credentials are valid
                if self.creds and self.creds.valid:
                    logger.info("Using existing valid credentials")
                    return self.creds
                
                # Try to refresh expired credentials
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("Refreshing expired credentials")
                    try:
                        self.creds.refresh(Request())
                        self._save_credentials(self.creds)
                        logger.info("✅ Credentials refreshed successfully")
                        return self.creds
                    except google.auth.exceptions.RefreshError as e:
                        logger.warning(f"Refresh failed: {e}. Need to re-authenticate.")
            
            except Exception as e:
                logger.warning(f"Failed to load existing credentials: {e}")
        
        # Need new authorization
        logger.info("🔐 Starting OAuth2 authorization flow...")
        return self._run_oauth_flow()
    
    def _run_oauth_flow(self) -> Credentials:
        """
        Run OAuth2 authorization flow
        Opens browser for user consent
        """
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_file),
                scopes=self.scopes
            )
            
            # Run local server on random port
            # User will be redirected to browser for consent
            self.creds = flow.run_local_server(
                port=0,
                success_message='✅ Authorization successful! You can close this window.',
                open_browser=True
            )
            
            # Save credentials
            self._save_credentials(self.creds)
            
            logger.info("✅ OAuth2 authorization completed successfully")
            return self.creds
            
        except Exception as e:
            logger.error(f"❌ OAuth2 authorization failed: {e}")
            raise RuntimeError(
                f"Failed to complete OAuth2 authorization: {e}\n"
                "Please ensure:\n"
                "1. credentials.json is valid\n"
                "2. OAuth consent screen is configured\n"
                "3. Your app is not in testing mode with unauthorized email"
            )
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from encrypted storage"""
        try:
            token_data = self.token_storage.load()
            if not token_data:
                return None
            
            creds = Credentials.from_authorized_user_info(
                token_data,
                scopes=self.scopes
            )
            
            return creds
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return None
    
    def _save_credentials(self, creds: Credentials):
        """Save credentials to encrypted storage"""
        try:
            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'expiry': creds.expiry.isoformat() if creds.expiry else None
            }
            
            self.token_storage.save(token_data)
            logger.info("✅ Credentials saved securely")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            raise
    
    def get_authenticated_service(
        self,
        service_name: str = 'youtube',
        version: str = 'v3'
    ):
        """
        Get authenticated YouTube API service
        
        Args:
            service_name: API service name (default: youtube)
            version: API version (default: v3)
        
        Returns:
            Authenticated googleapiclient service
        """
        if not self.creds:
            self.authorize()
        
        # Check if token needs refresh
        if self.auto_refresh and self.creds.expired and self.creds.refresh_token:
            logger.info("Token expired, refreshing...")
            try:
                self.creds.refresh(Request())
                self._save_credentials(self.creds)
                logger.info("✅ Token refreshed")
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                # Force re-authentication
                self.authorize(force_reauth=True)
        
        return build(
            service_name,
            version,
            credentials=self.creds,
            cache_discovery=False
        )
    
    def revoke_credentials(self):
        """Revoke current credentials and delete token"""
        if self.creds and self.creds.token:
            try:
                self.creds.revoke(Request())
                logger.info("✅ Credentials revoked")
            except Exception as e:
                logger.warning(f"Failed to revoke credentials: {e}")
        
        # Delete token file
        if self.token_file.exists():
            self.token_file.unlink()
            logger.info("✅ Token file deleted")
        
        self.creds = None
    
    def get_token_info(self) -> Dict[str, Any]:
        """
        Get current token information
        
        Returns:
            Dictionary with token status and metadata
        """
        if not self.creds:
            return {
                'authenticated': False,
                'message': 'No credentials available'
            }
        
        expiry_str = None
        time_until_expiry = None
        
        if self.creds.expiry:
            expiry_str = self.creds.expiry.isoformat()
            time_until_expiry = (self.creds.expiry - datetime.utcnow()).total_seconds()
        
        return {
            'authenticated': True,
            'valid': self.creds.valid,
            'expired': self.creds.expired,
            'has_refresh_token': bool(self.creds.refresh_token),
            'expiry': expiry_str,
            'time_until_expiry_seconds': time_until_expiry,
            'scopes': self.creds.scopes
        }
    
    def check_scopes(self, required_scopes: List[str]) -> bool:
        """
        Check if current credentials have required scopes
        
        Args:
            required_scopes: List of required scope URLs
        
        Returns:
            True if all required scopes are present
        """
        if not self.creds:
            return False
        
        current_scopes = set(self.creds.scopes or [])
        required = set(required_scopes)
        
        return required.issubset(current_scopes)
