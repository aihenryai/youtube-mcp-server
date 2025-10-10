#!/usr/bin/env python3
"""
Rate limiting for YouTube MCP Server
Protects against API quota exhaustion and abuse
"""

import time
import logging
from typing import Callable, Optional
from functools import wraps
from collections import defaultdict, deque
from threading import Lock

from config import config

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with per-minute and per-hour limits
    Thread-safe implementation
    """
    
    def __init__(self):
        """Initialize rate limiter"""
        self.enabled = config.rate_limit.enabled
        
        if self.enabled:
            self.calls_per_minute = config.rate_limit.calls_per_minute
            self.calls_per_hour = config.rate_limit.calls_per_hour
            
            # Track call timestamps per endpoint
            self.call_history = defaultdict(lambda: {
                'minute': deque(maxlen=self.calls_per_minute),
                'hour': deque(maxlen=self.calls_per_hour)
            })
            
            # Thread safety
            self.lock = Lock()
            
            logger.info(
                f"Rate limiter initialized: "
                f"{self.calls_per_minute}/min, {self.calls_per_hour}/hour"
            )
        else:
            logger.info("Rate limiting disabled")
    
    def _cleanup_old_calls(self, endpoint: str) -> None:
        """Remove calls older than the time window"""
        current_time = time.time()
        history = self.call_history[endpoint]
        
        # Remove minute-old calls
        while history['minute'] and current_time - history['minute'][0] > 60:
            history['minute'].popleft()
        
        # Remove hour-old calls
        while history['hour'] and current_time - history['hour'][0] > 3600:
            history['hour'].popleft()
    
    def is_allowed(self, endpoint: str = "default") -> tuple[bool, Optional[float]]:
        """
        Check if a call is allowed under rate limits
        
        Returns:
            (allowed: bool, wait_time: Optional[float])
            - allowed: True if call is allowed
            - wait_time: Seconds to wait if call is not allowed
        """
        if not self.enabled:
            return True, None
        
        with self.lock:
            self._cleanup_old_calls(endpoint)
            history = self.call_history[endpoint]
            
            current_time = time.time()
            
            # Check per-minute limit
            if len(history['minute']) >= self.calls_per_minute:
                # Calculate wait time until oldest call expires
                oldest_call = history['minute'][0]
                wait_time = 60 - (current_time - oldest_call)
                logger.warning(
                    f"Rate limit exceeded (per-minute) for {endpoint}: "
                    f"wait {wait_time:.1f}s"
                )
                return False, wait_time
            
            # Check per-hour limit
            if len(history['hour']) >= self.calls_per_hour:
                # Calculate wait time until oldest call expires
                oldest_call = history['hour'][0]
                wait_time = 3600 - (current_time - oldest_call)
                logger.warning(
                    f"Rate limit exceeded (per-hour) for {endpoint}: "
                    f"wait {wait_time:.1f}s"
                )
                return False, wait_time
            
            return True, None
    
    def record_call(self, endpoint: str = "default") -> None:
        """Record a successful call"""
        if not self.enabled:
            return
        
        with self.lock:
            current_time = time.time()
            history = self.call_history[endpoint]
            
            history['minute'].append(current_time)
            history['hour'].append(current_time)
            
            logger.debug(
                f"Rate limit: {endpoint} - "
                f"{len(history['minute'])}/{self.calls_per_minute} (minute), "
                f"{len(history['hour'])}/{self.calls_per_hour} (hour)"
            )
    
    def get_stats(self, endpoint: str = "default") -> dict:
        """Get rate limit statistics for an endpoint"""
        if not self.enabled:
            return {"enabled": False}
        
        with self.lock:
            self._cleanup_old_calls(endpoint)
            history = self.call_history[endpoint]
            
            return {
                "enabled": True,
                "endpoint": endpoint,
                "calls_last_minute": len(history['minute']),
                "calls_per_minute_limit": self.calls_per_minute,
                "calls_last_hour": len(history['hour']),
                "calls_per_hour_limit": self.calls_per_hour,
                "minute_remaining": self.calls_per_minute - len(history['minute']),
                "hour_remaining": self.calls_per_hour - len(history['hour'])
            }
    
    def reset(self, endpoint: Optional[str] = None) -> None:
        """Reset rate limits (all or specific endpoint)"""
        if not self.enabled:
            return
        
        with self.lock:
            if endpoint:
                if endpoint in self.call_history:
                    del self.call_history[endpoint]
                    logger.info(f"Rate limit reset for {endpoint}")
            else:
                self.call_history.clear()
                logger.info("All rate limits reset")


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limited(endpoint: Optional[str] = None, wait: bool = False):
    """
    Decorator to apply rate limiting to functions
    
    Args:
        endpoint: Endpoint identifier (uses function name if None)
        wait: If True, wait when rate limited instead of raising error
    
    Usage:
        @rate_limited(endpoint="search", wait=True)
        def search_videos(query):
            # ... function code
    """
    def decorator(func: Callable) -> Callable:
        endpoint_name = endpoint or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check rate limit
            allowed, wait_time = rate_limiter.is_allowed(endpoint_name)
            
            if not allowed:
                if wait and wait_time:
                    logger.info(f"Rate limited, waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    return {
                        "success": False,
                        "error": "Rate limit exceeded",
                        "wait_time": wait_time,
                        "message": f"Please wait {wait_time:.1f} seconds before retrying"
                    }
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Record successful call
            if result and isinstance(result, dict) and result.get("success"):
                rate_limiter.record_call(endpoint_name)
            
            return result
        
        return wrapper
    return decorator


# Convenience functions
def check_rate_limit(endpoint: str = "default") -> tuple[bool, Optional[float]]:
    """Check if endpoint is rate limited"""
    return rate_limiter.is_allowed(endpoint)


def record_api_call(endpoint: str = "default") -> None:
    """Record an API call"""
    rate_limiter.record_call(endpoint)


def get_rate_stats(endpoint: str = "default") -> dict:
    """Get rate limit statistics"""
    return rate_limiter.get_stats(endpoint)


def reset_rate_limits(endpoint: Optional[str] = None) -> None:
    """Reset rate limits"""
    rate_limiter.reset(endpoint)
