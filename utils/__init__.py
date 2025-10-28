#!/usr/bin/env python3
"""
Utils package for YouTube MCP Server
Provides caching, rate limiting, and validation utilities
"""

from .cache import (
    cache_manager,
    cached,
    cache_key,
    get_cached,
    set_cached,
    delete_cached,
    clear_cache,
    cache_stats
)

from .rate_limiter import (
    rate_limiter,
    rate_limited,
    check_rate_limit,
    record_api_call,
    get_rate_stats,
    reset_rate_limits
)

from .validators import (
    validator,
    ValidationError,
    validate_video_url,
    validate_channel_id,
    validate_language,
    validate_search_query,
    validate_max_results,
    validate_order,
    sanitize_text
)

from .oauth_metadata import (
    OAuthResourceMetadata,
    WWWAuthenticateChallenge,
    OAuthMetadataProvider,
    BearerTokenValidator,
    OAuthMiddleware,
    create_oauth_config
)

__all__ = [
    # Cache
    'cache_manager',
    'cached',
    'cache_key',
    'get_cached',
    'set_cached',
    'delete_cached',
    'clear_cache',
    'cache_stats',
    
    # Rate Limiter
    'rate_limiter',
    'rate_limited',
    'check_rate_limit',
    'record_api_call',
    'get_rate_stats',
    'reset_rate_limits',
    
    # Validators
    'validator',
    'ValidationError',
    'validate_video_url',
    'validate_channel_id',
    'validate_language',
    'validate_search_query',
    'validate_max_results',
    'validate_order',
    'sanitize_text',
    
    # OAuth Metadata (RFC 9728)
    'OAuthResourceMetadata',
    'WWWAuthenticateChallenge',
    'OAuthMetadataProvider',
    'BearerTokenValidator',
    'OAuthMiddleware',
    'create_oauth_config',
]
