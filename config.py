#!/usr/bin/env python3
"""
Configuration management for YouTube MCP Server
Centralized settings for cache, rate limiting, security, and API configuration
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables from the correct location
# Find .env file in the same directory as this config.py file
config_dir = Path(__file__).parent
env_file = config_dir / ".env"
load_dotenv(dotenv_path=env_file)

logger = logging.getLogger(__name__)


class CacheConfig(BaseModel):
    """Cache configuration settings"""
    
    enabled: bool = Field(
        default=True,
        description="Enable/disable caching"
    )
    
    cache_dir: str = Field(
        default="cache",
        description="Directory for disk cache"
    )
    
    ttl_seconds: int = Field(
        default=3600,  # 1 hour
        description="Cache time-to-live in seconds"
    )
    
    max_memory_items: int = Field(
        default=100,
        description="Maximum items in memory cache"
    )
    
    max_disk_size_mb: int = Field(
        default=500,  # 500 MB
        description="Maximum disk cache size in megabytes"
    )
    
    cleanup_interval_hours: int = Field(
        default=24,
        description="How often to run cache cleanup (hours)"
    )
    
    # 🔐 NEW: Cache encryption (v2.1)
    encryption_enabled: bool = Field(
        default=True,
        description="Enable cache encryption (Fernet/AES-128)"
    )
    
    @validator('enabled', pre=True, always=True)
    def set_enabled(cls, v):
        env_val = os.getenv("CACHE_ENABLED", "true").lower()
        return env_val in ('true', '1', 'yes')
    
    @validator('encryption_enabled', pre=True, always=True)
    def set_encryption_enabled(cls, v):
        env_val = os.getenv("CACHE_ENCRYPTION_ENABLED", "true").lower()
        return env_val in ('true', '1', 'yes')


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    
    enabled: bool = Field(
        default=True,
        description="Enable/disable rate limiting"
    )
    
    # Global rate limits
    calls_per_minute: int = Field(
        default=30,
        description="Maximum API calls per minute (global)"
    )
    
    calls_per_hour: int = Field(
        default=1000,
        description="Maximum API calls per hour (global)"
    )
    
    # Per-IP rate limits (NEW in v2.1)
    per_ip_enabled: bool = Field(
        default=True,
        description="Enable per-IP rate limiting"
    )
    
    per_ip_calls_per_minute: int = Field(
        default=10,
        description="Maximum API calls per IP per minute"
    )
    
    per_ip_calls_per_hour: int = Field(
        default=300,
        description="Maximum API calls per IP per hour"
    )
    
    burst_size: int = Field(
        default=10,
        description="Maximum burst size for rate limiter"
    )
    
    persistent_state: bool = Field(
        default=True,
        description="Save rate limit state to disk"
    )
    
    state_file: str = Field(
        default="rate_limit_state.json",
        description="File to store rate limit state"
    )
    
    @validator('enabled', pre=True, always=True)
    def set_enabled(cls, v):
        env_val = os.getenv("RATE_LIMIT_ENABLED", "true").lower()
        return env_val in ('true', '1', 'yes')
    
    @validator('per_ip_enabled', pre=True, always=True)
    def set_per_ip_enabled(cls, v):
        env_val = os.getenv("PER_IP_RATE_LIMIT_ENABLED", "true").lower()
        return env_val in ('true', '1', 'yes')
    
    @validator('per_ip_calls_per_minute', pre=True, always=True)
    def set_per_ip_calls_per_minute(cls, v):
        return int(os.getenv("PER_IP_CALLS_PER_MINUTE", v or 10))
    
    @validator('per_ip_calls_per_hour', pre=True, always=True)
    def set_per_ip_calls_per_hour(cls, v):
        return int(os.getenv("PER_IP_CALLS_PER_HOUR", v or 300))


class SecurityConfig(BaseModel):
    """Security configuration for HTTP mode"""
    
    require_api_key: bool = Field(
        default=True,
        description="Require API key authentication in HTTP mode"
    )
    
    enable_prompt_injection_detection: bool = Field(
        default=True,
        description="Enable prompt injection detection"
    )
    
    prompt_injection_threshold: int = Field(
        default=30,
        description="Risk score threshold for prompt injection (0-100)"
    )
    
    server_api_key: Optional[str] = Field(
        default=None,
        description="Server API key for authentication"
    )
    
    allowed_origins: List[str] = Field(
        default=[],
        description="CORS allowed origins - MUST be configured for HTTP mode"
    )
    
    max_request_size: int = Field(
        default=1024 * 1024,  # 1MB
        description="Maximum request size in bytes"
    )
    
    enable_ip_rate_limiting: bool = Field(
        default=True,
        description="Enable per-IP rate limiting in HTTP mode"
    )
    
    max_requests_per_ip_minute: int = Field(
        default=10,
        description="Maximum requests per IP per minute"
    )
    
    # 🔐 NEW v2.1: CORS Configuration
    cors_enabled: bool = Field(
        default=True,
        description="Enable CORS validation"
    )
    
    cors_allowed_methods: List[str] = Field(
        default=["GET", "POST", "OPTIONS"],
        description="Allowed HTTP methods for CORS"
    )
    
    cors_allowed_headers: List[str] = Field(
        default=["Content-Type", "Authorization", "X-Request-ID"],
        description="Allowed headers for CORS"
    )
    
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials in CORS requests"
    )
    
    cors_max_age: int = Field(
        default=86400,  # 24 hours
        description="CORS preflight cache duration (seconds)"
    )
    
    # 🔐 NEW v2.1: Request Signing
    request_signing_enabled: bool = Field(
        default=False,  # Optional feature, disabled by default
        description="Enable HMAC request signature validation"
    )
    
    request_signing_secret: Optional[str] = Field(
        default=None,
        description="Secret key for HMAC request signing (min 32 chars)"
    )
    
    request_signing_algorithm: str = Field(
        default="sha256",
        description="HMAC algorithm: sha256 or sha512"
    )
    
    request_signing_timestamp_tolerance: int = Field(
        default=300,  # 5 minutes
        description="Timestamp tolerance for request signatures (seconds)"
    )
    
    request_signing_require_nonce: bool = Field(
        default=True,
        description="Require nonce for request signatures (replay protection)"
    )
    
    # 🔐 NEW v2.1: Security Logging
    security_logging_enabled: bool = Field(
        default=True,
        description="Enable security event logging"
    )
    
    security_log_file: str = Field(
        default="security.log",
        description="Security log file path"
    )
    
    security_log_level: str = Field(
        default="INFO",
        description="Security logging level"
    )
    
    @validator('cors_enabled', pre=True, always=True)
    def set_cors_enabled(cls, v):
        env_val = os.getenv("CORS_ENABLED", "true").lower()
        return env_val in ('true', '1', 'yes')
    
    @validator('request_signing_enabled', pre=True, always=True)
    def set_request_signing_enabled(cls, v):
        env_val = os.getenv("REQUEST_SIGNING_ENABLED", "false").lower()
        return env_val in ('true', '1', 'yes')
    
    @validator('request_signing_secret', pre=True, always=True)
    def set_request_signing_secret(cls, v):
        secret = v or os.getenv("REQUEST_SIGNING_SECRET")
        if secret and len(secret) < 32:
            logger.warning(
                "⚠️  Request signing secret should be at least 32 characters. "
                "Use utils/security/request_signer.py:generate_secure_secret() to generate one."
            )
        return secret
    
    @validator('security_logging_enabled', pre=True, always=True)
    def set_security_logging_enabled(cls, v):
        env_val = os.getenv("SECURITY_LOGGING_ENABLED", "true").lower()
        return env_val in ('true', '1', 'yes')
    
    # 🔐 NEW v2.2: OAuth 2.1 Metadata (RFC 9728)
    oauth_metadata_enabled: bool = Field(
        default=True,
        description="Enable OAuth 2.1 Protected Resource Metadata (RFC 9728)"
    )
    
    oauth_resource_uri: Optional[str] = Field(
        default=None,
        description="Resource URI for OAuth metadata (auto-detected if None)"
    )
    
    oauth_authorization_servers: List[str] = Field(
        default=["https://accounts.google.com"],
        description="List of OAuth 2.1 authorization server URLs"
    )
    
    oauth_require_authentication: bool = Field(
        default=False,
        description="Require OAuth authentication for all requests"
    )
    
    oauth_protected_tools: List[str] = Field(
        default=[
            "create_playlist",
            "add_video_to_playlist",
            "remove_video_from_playlist",
            "update_playlist",
            "reorder_playlist_video"
        ],
        description="List of tools requiring OAuth authentication"
    )
    
    @validator('oauth_metadata_enabled', pre=True, always=True)
    def set_oauth_metadata_enabled(cls, v):
        env_val = os.getenv("OAUTH_METADATA_ENABLED", "true").lower()
        return env_val in ('true', '1', 'yes')
    
    @validator('oauth_resource_uri', pre=True, always=True)
    def set_oauth_resource_uri(cls, v):
        return v or os.getenv("OAUTH_RESOURCE_URI")
    
    @validator('oauth_require_authentication', pre=True, always=True)
    def set_oauth_require_authentication(cls, v):
        env_val = os.getenv("OAUTH_REQUIRE_AUTHENTICATION", "false").lower()
        return env_val in ('true', '1', 'yes')
    
    @validator('server_api_key', pre=True, always=True)
    def set_server_api_key(cls, v):
        return v or os.getenv("SERVER_API_KEY")
    
    @validator('allowed_origins', pre=True, always=True)
    def set_allowed_origins(cls, v):
        # Read from environment variable
        env_origins = os.getenv("ALLOWED_ORIGINS", "")
        if env_origins:
            # Split by comma and strip whitespace
            return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
        return v if v else []
    
    @validator('allowed_origins')
    def validate_origins(cls, v, values):
        """Validate CORS origins - CRITICAL for HTTP mode"""
        # Check if HTTP mode is enabled
        transport = os.getenv('MCP_TRANSPORT', 'stdio')
        
        if transport == 'http':
            # HTTP mode REQUIRES proper CORS configuration
            if not v or v == ["*"]:
                raise ValueError(
                    "🔴 CRITICAL SECURITY ERROR: CORS must be configured for HTTP mode!\n"
                    "\n"
                    "Add to your .env file:\n"
                    "  ALLOWED_ORIGINS=https://your-app.com,https://other-app.com\n"
                    "\n"
                    "❌ NEVER use: ALLOWED_ORIGINS=*\n"
                    "\n"
                    "For Google Cloud Run:\n"
                    "  gcloud run deploy --set-env-vars ALLOWED_ORIGINS=https://your-domain.com\n"
                )
            
            # Validate each origin
            for origin in v:
                if not origin.startswith('https://') and not origin.startswith('http://localhost'):
                    logger.warning(
                        f"⚠️  Origin '{origin}' should use HTTPS in production"
                    )
            
            logger.info(f"✅ CORS configured for {len(v)} origin(s)")
        
        elif v and v != ["*"]:
            # stdio mode but CORS is configured - just log it
            logger.info(f"ℹ️  CORS configured but not needed in stdio mode")
        
        return v


class YouTubeAPIConfig(BaseModel):
    """YouTube API configuration"""
    
    api_key: str = Field(
        default="",
        description="YouTube Data API v3 key"
    )
    
    timeout_seconds: int = Field(
        default=30,
        description="API request timeout"
    )
    
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for failed requests"
    )
    
    retry_delay: float = Field(
        default=1.0,
        description="Initial delay between retries (seconds)"
    )
    
    quota_limit_daily: int = Field(
        default=10000,
        description="Daily quota limit (units)"
    )
    
    validate_on_startup: bool = Field(
        default=True,
        description="Validate API key on server startup"
    )
    
    @validator('api_key', pre=True, always=True)
    def validate_api_key(cls, v):
        api_key = v or os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError(
                "YOUTUBE_API_KEY is required. "
                "Please set it in your .env file or environment variables."
            )
        
        # Basic format validation
        if len(api_key) < 30:
            logger.warning(
                "⚠️  YouTube API key seems too short. "
                "Make sure you're using a valid API key from Google Cloud Console."
            )
        
        return api_key


class ValidationConfig(BaseModel):
    """Input validation configuration"""
    
    valid_languages: List[str] = Field(
        default=[
            "en", "he", "ar", "es", "fr", "de", "it", "pt", "ru", "ja", 
            "ko", "zh", "hi", "bn", "pa", "te", "mr", "ta", "ur", "tr"
        ],
        description="List of valid language codes"
    )
    
    max_query_length: int = Field(
        default=500,
        description="Maximum search query length"
    )
    
    max_results_limit: int = Field(
        default=50,
        description="Maximum results per request"
    )
    
    max_comments_limit: int = Field(
        default=100,
        description="Maximum comments per request"
    )


class ServerConfig(BaseModel):
    """Main server configuration"""
    
    transport: str = Field(
        default="stdio",
        description="Transport mode: stdio or http"
    )
    
    host: str = Field(
        default="0.0.0.0",
        description="Server host for HTTP mode"
    )
    
    port: int = Field(
        default=8080,
        description="Server port for HTTP mode"
    )
    
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    environment: str = Field(
        default="production",
        description="Environment: development, staging, or production"
    )
    
    @validator('transport', pre=True, always=True)
    def set_transport(cls, v):
        return v or os.getenv("MCP_TRANSPORT", "stdio")
    
    @validator('port', pre=True, always=True)
    def set_port(cls, v):
        return int(v or os.getenv("PORT", 8080))
    
    @validator('environment', pre=True, always=True)
    def set_environment(cls, v):
        return v or os.getenv("ENVIRONMENT", "production")


class ProxyConfig(BaseModel):
    """Proxy configuration"""
    
    enabled: bool = Field(
        default=False,
        description="Enable proxy for API requests"
    )
    
    http_proxy: Optional[str] = Field(
        default=None,
        description="HTTP proxy URL"
    )
    
    https_proxy: Optional[str] = Field(
        default=None,
        description="HTTPS proxy URL"
    )
    
    @validator('enabled', pre=True, always=True)
    def set_enabled(cls, v):
        env_val = os.getenv("PROXY_ENABLED", "false").lower()
        return env_val in ('true', '1', 'yes')
    
    @validator('http_proxy', pre=True, always=True)
    def set_http_proxy(cls, v):
        return v or os.getenv("HTTP_PROXY")
    
    @validator('https_proxy', pre=True, always=True)
    def set_https_proxy(cls, v):
        return v or os.getenv("HTTPS_PROXY")


class AppConfig(BaseModel):
    """Application-wide configuration"""
    
    cache: CacheConfig = Field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    youtube_api: YouTubeAPIConfig = Field(default_factory=YouTubeAPIConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    
    class Config:
        validate_assignment = True


# Global configuration instance
def get_config() -> AppConfig:
    """Get or create global configuration instance"""
    return AppConfig()


def validate_youtube_api_key(api_key: str) -> tuple[bool, Optional[str]]:
    """
    Validate YouTube API key by making a test request
    
    Args:
        api_key: YouTube API key to validate
        
    Returns:
        (is_valid: bool, error_message: Optional[str])
    """
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        
        # Try to build YouTube client and make a simple request
        youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
        
        # Make a minimal quota request (1 unit)
        youtube.videos().list(part="id", id="dQw4w9WgXcQ").execute()
        
        logger.info("✅ YouTube API key validated successfully")
        return True, None
        
    except HttpError as e:
        if e.status_code == 400:
            error_msg = "❌ Invalid YouTube API key format"
        elif e.status_code == 403:
            error_msg = "❌ YouTube API key is valid but lacks required permissions"
        else:
            error_msg = f"❌ YouTube API error: {e.status_code}"
        
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"❌ Failed to validate YouTube API key: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


# Export config for easy import
config = get_config()

# Validate API key on import if enabled (only if not in test mode)
if config.youtube_api.validate_on_startup and config.youtube_api.api_key != "test_api_key_for_testing":
    is_valid, error = validate_youtube_api_key(config.youtube_api.api_key)
    if not is_valid:
        logger.warning(
            f"{error}\n"
            "⚠️  Server will start but API calls may fail.\n"
            "Please check your YouTube API key in .env file."
        )
