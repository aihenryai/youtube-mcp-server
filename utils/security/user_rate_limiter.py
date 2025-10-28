"""
Enhanced Rate Limiter - User and Token Based
Supports both IP-based and user/token-based rate limiting

Features:
- Per-IP rate limiting
- Per-user rate limiting (via OAuth token)
- Per-API-key rate limiting
- Configurable limits per entity
- Time-window based (sliding window)
- Threadsafe
- Redis-compatible (optional)
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiter"""
    max_per_minute: int = 60
    max_per_hour: int = 1000
    max_per_day: int = 10000
    enabled: bool = True
    

@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    reason: Optional[str] = None
    retry_after_seconds: Optional[int] = None
    remaining_minute: Optional[int] = None
    remaining_hour: Optional[int] = None
    remaining_day: Optional[int] = None
    

class EnhancedRateLimiter:
    """
    Enhanced rate limiter supporting multiple entity types
    
    Supports:
    - IP-based rate limiting
    - User-based rate limiting (OAuth)
    - API-key based rate limiting
    - Per-endpoint rate limiting
    """
    
    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter
        
        Args:
            config: Rate limit configuration
        """
        self.config = config
        
        # Storage for rate limit data
        # Format: {entity_id: {window: [timestamps]}}
        self.minute_requests: Dict[str, List[datetime]] = defaultdict(list)
        self.hour_requests: Dict[str, List[datetime]] = defaultdict(list)
        self.day_requests: Dict[str, List[datetime]] = defaultdict(list)
        
        # Thread safety
        self.lock = Lock()
        
        logger.info(
            f"Enhanced Rate Limiter initialized: "
            f"{config.max_per_minute}/min, "
            f"{config.max_per_hour}/hour, "
            f"{config.max_per_day}/day"
        )
    
    def check_rate_limit(
        self,
        ip: Optional[str] = None,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> RateLimitResult:
        """
        Check rate limit for multiple entity types
        
        Priority order:
        1. user_id (from OAuth token) - most specific
        2. api_key (if provided)
        3. ip (fallback)
        
        Args:
            ip: Client IP address
            user_id: User ID from OAuth token
            api_key: API key (hashed)
            endpoint: Optional endpoint name for per-endpoint limits
        
        Returns:
            RateLimitResult with decision and metadata
        
        Example:
            >>> result = limiter.check_rate_limit(
            ...     user_id="user_12345",
            ...     ip="192.168.1.1",
            ...     endpoint="create_playlist"
            ... )
            >>> if not result.allowed:
            ...     return 429, {"error": result.reason}
        """
        if not self.config.enabled:
            return RateLimitResult(allowed=True)
        
        # Determine entity ID (priority: user > api_key > ip)
        entity_id = self._get_entity_id(user_id, api_key, ip)
        
        if not entity_id:
            # No identifier available - allow but log
            logger.warning("No rate limit identifier available")
            return RateLimitResult(allowed=True)
        
        # Add endpoint to entity ID if specified
        if endpoint:
            entity_id = f"{entity_id}:{endpoint}"
        
        with self.lock:
            now = datetime.now()
            
            # Cleanup old requests
            self._cleanup(entity_id, now)
            
            # Check limits
            minute_count = len(self.minute_requests[entity_id])
            hour_count = len(self.hour_requests[entity_id])
            day_count = len(self.day_requests[entity_id])
            
            # Check minute limit
            if minute_count >= self.config.max_per_minute:
                oldest = self.minute_requests[entity_id][0]
                retry_after = 60 - (now - oldest).seconds
                
                return RateLimitResult(
                    allowed=False,
                    reason=f"Rate limit exceeded: {minute_count}/{self.config.max_per_minute} per minute",
                    retry_after_seconds=retry_after,
                    remaining_minute=0,
                    remaining_hour=self.config.max_per_hour - hour_count,
                    remaining_day=self.config.max_per_day - day_count
                )
            
            # Check hour limit
            if hour_count >= self.config.max_per_hour:
                oldest = self.hour_requests[entity_id][0]
                retry_after = 3600 - (now - oldest).seconds
                
                return RateLimitResult(
                    allowed=False,
                    reason=f"Rate limit exceeded: {hour_count}/{self.config.max_per_hour} per hour",
                    retry_after_seconds=retry_after,
                    remaining_minute=self.config.max_per_minute - minute_count,
                    remaining_hour=0,
                    remaining_day=self.config.max_per_day - day_count
                )
            
            # Check day limit
            if day_count >= self.config.max_per_day:
                oldest = self.day_requests[entity_id][0]
                retry_after = 86400 - (now - oldest).seconds
                
                return RateLimitResult(
                    allowed=False,
                    reason=f"Rate limit exceeded: {day_count}/{self.config.max_per_day} per day",
                    retry_after_seconds=retry_after,
                    remaining_minute=self.config.max_per_minute - minute_count,
                    remaining_hour=self.config.max_per_hour - hour_count,
                    remaining_day=0
                )
            
            # Record request
            self.minute_requests[entity_id].append(now)
            self.hour_requests[entity_id].append(now)
            self.day_requests[entity_id].append(now)
            
            return RateLimitResult(
                allowed=True,
                remaining_minute=self.config.max_per_minute - minute_count - 1,
                remaining_hour=self.config.max_per_hour - hour_count - 1,
                remaining_day=self.config.max_per_day - day_count - 1
            )
    
    def _get_entity_id(
        self,
        user_id: Optional[str],
        api_key: Optional[str],
        ip: Optional[str]
    ) -> Optional[str]:
        """
        Get entity ID with priority
        
        Priority: user_id > api_key > ip
        """
        if user_id:
            return f"user:{user_id}"
        
        if api_key:
            # Hash API key for privacy
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"key:{key_hash}"
        
        if ip:
            return f"ip:{ip}"
        
        return None
    
    def _cleanup(self, entity_id: str, now: datetime):
        """Remove old requests outside time windows"""
        minute_cutoff = now - timedelta(minutes=1)
        hour_cutoff = now - timedelta(hours=1)
        day_cutoff = now - timedelta(days=1)
        
        self.minute_requests[entity_id] = [
            ts for ts in self.minute_requests[entity_id]
            if ts > minute_cutoff
        ]
        
        self.hour_requests[entity_id] = [
            ts for ts in self.hour_requests[entity_id]
            if ts > hour_cutoff
        ]
        
        self.day_requests[entity_id] = [
            ts for ts in self.day_requests[entity_id]
            if ts > day_cutoff
        ]
    
    def get_stats(
        self,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
        ip: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get current rate limit statistics for an entity
        
        Args:
            user_id: User ID
            api_key: API key
            ip: IP address
        
        Returns:
            Dictionary with current usage statistics
        """
        entity_id = self._get_entity_id(user_id, api_key, ip)
        
        if not entity_id:
            return {
                "error": "No entity identifier provided"
            }
        
        with self.lock:
            now = datetime.now()
            self._cleanup(entity_id, now)
            
            minute_count = len(self.minute_requests[entity_id])
            hour_count = len(self.hour_requests[entity_id])
            day_count = len(self.day_requests[entity_id])
            
            return {
                "entity_id": entity_id.split(':')[0],  # Don't expose full ID
                "current_usage": {
                    "per_minute": minute_count,
                    "per_hour": hour_count,
                    "per_day": day_count
                },
                "limits": {
                    "per_minute": self.config.max_per_minute,
                    "per_hour": self.config.max_per_hour,
                    "per_day": self.config.max_per_day
                },
                "remaining": {
                    "per_minute": self.config.max_per_minute - minute_count,
                    "per_hour": self.config.max_per_hour - hour_count,
                    "per_day": self.config.max_per_day - day_count
                }
            }
    
    def reset(
        self,
        user_id: Optional[str] = None,
        api_key: Optional[str] = None,
        ip: Optional[str] = None
    ):
        """
        Reset rate limit for an entity (admin only)
        
        Args:
            user_id: User ID to reset
            api_key: API key to reset
            ip: IP to reset
        """
        entity_id = self._get_entity_id(user_id, api_key, ip)
        
        if not entity_id:
            logger.warning("Cannot reset rate limit: no entity identifier")
            return
        
        with self.lock:
            if entity_id in self.minute_requests:
                del self.minute_requests[entity_id]
            if entity_id in self.hour_requests:
                del self.hour_requests[entity_id]
            if entity_id in self.day_requests:
                del self.day_requests[entity_id]
        
        logger.info(f"Rate limit reset for {entity_id}")


def create_rate_limiter(
    max_per_minute: int = 60,
    max_per_hour: int = 1000,
    max_per_day: int = 10000,
    enabled: bool = True
) -> EnhancedRateLimiter:
    """
    Factory function to create rate limiter
    
    Args:
        max_per_minute: Maximum requests per minute
        max_per_hour: Maximum requests per hour
        max_per_day: Maximum requests per day
        enabled: Whether rate limiting is enabled
    
    Returns:
        Configured EnhancedRateLimiter instance
    
    Example:
        >>> limiter = create_rate_limiter(
        ...     max_per_minute=60,
        ...     max_per_hour=1000,
        ...     max_per_day=10000
        ... )
    """
    config = RateLimitConfig(
        max_per_minute=max_per_minute,
        max_per_hour=max_per_hour,
        max_per_day=max_per_day,
        enabled=enabled
    )
    
    return EnhancedRateLimiter(config)


# Helper function to extract user ID from OAuth token
def extract_user_id_from_token(
    authorization_header: Optional[str]
) -> Optional[str]:
    """
    Extract user ID from OAuth Bearer token
    
    Args:
        authorization_header: Authorization header value
    
    Returns:
        User ID if found, None otherwise
    
    Note:
        This should be used in conjunction with OAuth2ResourceServer
        for actual token validation
    """
    if not authorization_header:
        return None
    
    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    token = parts[1]
    
    try:
        # Decode without verification (validation happens elsewhere)
        import jwt
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload.get('sub')  # 'sub' claim is user ID
    except:
        return None
