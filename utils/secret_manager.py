"""
Google Cloud Secret Manager Integration for YouTube MCP Server
Use this module for production deployments to fetch secrets securely
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Check if running on Google Cloud
IS_CLOUD = os.getenv("K_SERVICE") is not None  # Cloud Run sets this
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")


def is_cloud_environment() -> bool:
    """Check if running in Google Cloud environment"""
    return IS_CLOUD and PROJECT_ID is not None


@lru_cache(maxsize=10)
def get_secret(secret_id: str, version: str = "latest") -> Optional[str]:
    """
    Fetch secret from Google Cloud Secret Manager
    
    Args:
        secret_id: Secret identifier (e.g., "youtube-api-key")
        version: Secret version (default: "latest")
    
    Returns:
        Secret value as string, or None if not found
    """
    # If not in cloud, try environment variable fallback
    if not is_cloud_environment():
        logger.info(f"Not in cloud environment, checking ENV for {secret_id}")
        env_var = secret_id.upper().replace("-", "_")
        return os.getenv(env_var)
    
    try:
        from google.cloud import secretmanager
        
        # Create client
        client = secretmanager.SecretManagerServiceClient()
        
        # Build secret name
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/{version}"
        
        # Access secret
        response = client.access_secret_version(request={"name": name})
        
        # Decode and return payload
        payload = response.payload.data.decode("UTF-8")
        logger.info(f"✅ Retrieved secret: {secret_id}")
        return payload
        
    except Exception as e:
        logger.error(f"❌ Failed to retrieve secret {secret_id}: {e}")
        
        # Fallback to environment variable
        env_var = secret_id.upper().replace("-", "_")
        fallback = os.getenv(env_var)
        
        if fallback:
            logger.warning(f"⚠️ Using fallback ENV variable: {env_var}")
            return fallback
        
        return None


@lru_cache(maxsize=5)
def get_json_secret(secret_id: str, version: str = "latest") -> Optional[Dict[str, Any]]:
    """
    Fetch JSON secret from Secret Manager
    
    Args:
        secret_id: Secret identifier
        version: Secret version (default: "latest")
    
    Returns:
        Parsed JSON dict, or None if not found
    """
    try:
        secret_value = get_secret(secret_id, version)
        if secret_value:
            return json.loads(secret_value)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse JSON secret {secret_id}: {e}")
    
    return None


class SecretConfig:
    """
    Configuration class that prioritizes Secret Manager over environment variables
    
    Usage:
        config = SecretConfig()
        api_key = config.youtube_api_key
        server_key = config.server_api_key
    """
    
    def __init__(self):
        """Initialize secret configuration"""
        self._use_secret_manager = is_cloud_environment()
        
        if self._use_secret_manager:
            logger.info("🔐 Using Google Cloud Secret Manager")
        else:
            logger.info("🔧 Using local environment variables")
    
    @property
    def youtube_api_key(self) -> str:
        """Get YouTube API key from Secret Manager or ENV"""
        secret = get_secret("youtube-api-key")
        
        if not secret:
            raise ValueError(
                "YouTube API key not found. "
                "Please set YOUTUBE_API_KEY environment variable or create secret in Secret Manager"
            )
        
        return secret
    
    @property
    def server_api_key(self) -> Optional[str]:
        """Get server API key from Secret Manager or ENV"""
        return get_secret("server-api-key")
    
    @property
    def oauth2_credentials(self) -> Optional[Dict[str, Any]]:
        """Get OAuth2 credentials from Secret Manager or file"""
        # Try Secret Manager first
        if self._use_secret_manager:
            credentials = get_json_secret("oauth2-credentials")
            if credentials:
                return credentials
        
        # Fallback to local file
        credentials_path = os.getenv("OAUTH2_CREDENTIALS_FILE", "credentials.json")
        if os.path.exists(credentials_path):
            try:
                with open(credentials_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load OAuth2 credentials from file: {e}")
        
        return None
    
    @property
    def oauth2_token(self) -> Optional[Dict[str, Any]]:
        """Get OAuth2 token from Secret Manager or file"""
        # Try Secret Manager first
        if self._use_secret_manager:
            token = get_json_secret("oauth2-token")
            if token:
                return token
        
        # Fallback to local file
        token_path = os.getenv("OAUTH2_TOKEN_FILE", "token.json")
        if os.path.exists(token_path):
            try:
                with open(token_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load OAuth2 token from file: {e}")
        
        return None
    
    @property
    def allowed_origins(self) -> list[str]:
        """Get CORS allowed origins"""
        # Try Secret Manager
        if self._use_secret_manager:
            origins_str = get_secret("allowed-origins")
            if origins_str:
                return [o.strip() for o in origins_str.split(",") if o.strip()]
        
        # Fallback to ENV
        env_origins = os.getenv("ALLOWED_ORIGINS", "")
        if env_origins:
            return [o.strip() for o in env_origins.split(",") if o.strip()]
        
        return []


# Example usage in config.py:
"""
# In config.py, replace the validator:

from utils.secret_manager import SecretConfig

secret_config = SecretConfig()

class YouTubeAPIConfig(BaseModel):
    api_key: str = Field(default="", description="YouTube Data API v3 key")
    
    @validator('api_key', pre=True, always=True)
    def validate_api_key(cls, v):
        # Use Secret Manager if available
        try:
            return secret_config.youtube_api_key
        except Exception as e:
            logger.error(f"Failed to get API key from Secret Manager: {e}")
            # Fallback to ENV
            api_key = v or os.getenv("YOUTUBE_API_KEY")
            if not api_key:
                raise ValueError("YOUTUBE_API_KEY is required")
            return api_key
"""


# Health check for Secret Manager access
def test_secret_manager_access() -> bool:
    """
    Test Secret Manager connectivity
    
    Returns:
        True if Secret Manager is accessible
    """
    if not is_cloud_environment():
        logger.info("Not in cloud environment, skipping Secret Manager test")
        return True
    
    try:
        # Try to access a test secret or list secrets
        from google.cloud import secretmanager
        
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{PROJECT_ID}"
        
        # Just listing to verify access
        list(client.list_secrets(request={"parent": parent, "page_size": 1}))
        
        logger.info("✅ Secret Manager access verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Secret Manager access failed: {e}")
        return False


if __name__ == "__main__":
    # Test script
    print("Testing Secret Manager Integration...")
    print(f"Cloud environment: {is_cloud_environment()}")
    print(f"Project ID: {PROJECT_ID}")
    
    if test_secret_manager_access():
        print("✅ Secret Manager is accessible")
        
        # Try to get a test secret
        config = SecretConfig()
        try:
            api_key = config.youtube_api_key
            print(f"✅ YouTube API Key: {api_key[:10]}...")
        except Exception as e:
            print(f"❌ Failed to get API key: {e}")
    else:
        print("⚠️ Secret Manager not accessible (using ENV variables)")
