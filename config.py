#!/usr/bin/env python3
"""
Configuration management for YouTube MCP Server
Centralized settings for cache, rate limiting, security, and API configuration
"""

import os
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""
    
    enabled: bool = Field(
        default=True,
        description="Enable/disable rate limiting"
    )
    
    calls_per_minute: int = Field(
        default=30,
        description="Maximum API calls per minute"
    )
    
    calls_per_hour: int = Field(
        default=1000,
        description="Maximum API calls per hour"
    )
    
    burst_size: int = Field(
        default=10,
        description="Maximum burst size for rate limiter"
    )


class SecurityConfig(BaseModel):
    """Security configuration for HTTP mode"""
    
    require_api_key: bool = Field(
        default=True,
        description="Require API key authentication in HTTP mode"
    )
    
    server_api_key: Optional[str] = Field(
        default=None,
        description="Server API key for authentication"
    )
    
    allowed_origins: List[str] = Field(
        default=["*"],
        description="CORS allowed origins"
    )
    
    max_request_size: int = Field(
        default=1024 * 1024,  # 1MB
        description="Maximum request size in bytes"
    )
    
    @validator('server_api_key', pre=True, always=True)
    def set_server_api_key(cls, v):
        return v or os.getenv("SERVER_API_KEY")


class YouTubeAPIConfig(BaseModel):
    """YouTube API configuration"""
    
    api_key: str = Field(
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
    
    @validator('api_key', pre=True, always=True)
    def validate_api_key(cls, v):
        api_key = v or os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY is required")
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
    
    @validator('transport', pre=True, always=True)
    def set_transport(cls, v):
        return v or os.getenv("MCP_TRANSPORT", "stdio")
    
    @validator('port', pre=True, always=True)
    def set_port(cls, v):
        return int(v or os.getenv("PORT", 8080))


class AppConfig(BaseModel):
    """Application-wide configuration"""
    
    cache: CacheConfig = Field(default_factory=CacheConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    youtube_api: YouTubeAPIConfig = Field(default_factory=YouTubeAPIConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    
    class Config:
        validate_assignment = True


# Global configuration instance
def get_config() -> AppConfig:
    """Get or create global configuration instance"""
    return AppConfig()


# Export config for easy import
config = get_config()
