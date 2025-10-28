#!/usr/bin/env python3
"""
Rate limiting for YouTube MCP Server
Protects against API quota exhaustion and abuse

Features:
- Global rate limiting (per-minute and per-hour)
- Per-IP rate limiting (NEW in v2.1)
- Thread-safe implementation
- Configurable limits
"""

import time
import logging
from typing import Callable, Optional, Dict, Tuple
from functools import wraps
from collections import defaultdict, deque
from threading import Lock

from config import config

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Enhanced token bucket rate limiter with global and per-IP limits
    Thread-safe implementation
    """
    
    def __init__(self):
        """Initialize rate limiter"""
        self.enabled = config.rate_limit.enabled
        
        if self.enabled:
            # Global limits
            self.calls_per_minute = config.rate_limit.calls_per_minute
            self.calls_per_hour = config.rate_limit.calls_per_hour
            
            # Per-IP limits (more restrictive)
            self.per_ip_enabled = config.rate_limit.get('per_ip_enabled', True)
            self.per_ip_calls_per_minute = config.rate_limit.get('per_ip_calls_per_minute', 10)
            self.per_ip_calls_per_hour = config.rate_limit.get('per_ip_calls_per_hour', 300)
            
            # Track call timestamps per endpoint (global)
            self.call_history = defaultdict(lambda: {
                'minute': deque(maxlen=self.calls_per_minute),
                'hour': deque(maxlen=self.calls_per_hour)
            })
            
            # Track call timestamps per IP per endpoint
            # Structure: {ip_address: {endpoint: {'minute': deque, 'hour': deque}}}
            self.ip_call_history = defaultdict(lambda: defaultdict(lambda: {
                'minute': deque(maxlen=self.per_ip_calls_per_minute),
                'hour': deque(maxlen=self.per_ip_calls_per_hour)
            }))
            
            # Track last cleanup time for IP entries
            self.last_cleanup = time.time()
            self.cleanup_interval = 3600  # Clean up stale IPs every hour
            
            # Thread safety
            self.lock = Lock()
            
            logger.info(
                f"Rate limiter initialized:\n"
                f"  Global: {self.calls_per_minute}/min, {self.calls_per_hour}/hour\n"
                f"  Per-IP: {self.per_ip_calls_per_minute}/min, {self.per_ip_calls_per_hour}/hour (enabled: {self.per_ip_enabled})"
            )
        else:
            logger.info("Rate limiting disabled")
    
    def _cleanup_old_calls(self, endpoint: str) -> None:
        """Remove calls older than the time window (global)"""
        current_time = time.time()
        history = self.call_history[endpoint]
        
        # Remove minute-old calls
        while history['minute'] and current_time - history['minute'][0] > 60:
            history['minute'].popleft()
        
        # Remove hour-old calls
        while history['hour'] and current_time - history['hour'][0] > 3600:
            history['hour'].popleft()
    
    def _cleanup_old_calls_for_ip(self, ip_address: str, endpoint: str) -> None:
        """Remove calls older than the time window for specific IP"""
        current_time = time.time()
        
        if ip_address not in self.ip_call_history:
            return
        
        history = self.ip_call_history[ip_address][endpoint]
        
        # Remove minute-old calls
        while history['minute'] and current_time - history['minute'][0] > 60:
            history['minute'].popleft()
        
        # Remove hour-old calls
        while history['hour'] and current_time - history['hour'][0] > 3600:
            history['hour'].popleft()
    
    def _cleanup_stale_ips(self) -> None:
        """Remove IP entries with no recent activity"""
        current_time = time.time()
        
        # Only cleanup once per interval
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = current_time
        stale_ips = []
        
        # Find IPs with no calls in the last hour
        for ip_address, endpoints in self.ip_call_history.items():
            all_empty = True
            for endpoint_data in endpoints.values():
                if endpoint_data['hour']:
                    all_empty = False
                    break
            
            if all_empty:
                stale_ips.append(ip_address)
        
        # Remove stale IPs
        for ip_address in stale_ips:
            del self.ip_call_history[ip_address]
        
        if stale_ips:
            logger.info(f"Cleaned up {len(stale_ips)} stale IP entries")
    
    def is_allowed(
        self,
        endpoint: str = "default",
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Check if a call is allowed under rate limits
        
        Args:
            endpoint: Endpoint name
            ip_address: Client IP address (optional, for per-IP limiting)
        
        Returns:
            (allowed: bool, wait_time: Optional[float], limit_type: Optional[str])
            - allowed: True if call is allowed
            - wait_time: Seconds to wait if call is not allowed
            - limit_type: Type of limit hit ('global' or 'per_ip')
        """
        if not self.enabled:
            return True, None, None
        
        with self.lock:
            # Periodic cleanup of stale IPs
            self._cleanup_stale_ips()
            
            # Check global limits first
            self._cleanup_old_calls(endpoint)
            history = self.call_history[endpoint]
            
            current_time = time.time()
            
            # Check global per-minute limit
            if len(history['minute']) >= self.calls_per_minute:
                oldest_call = history['minute'][0]
                wait_time = 60 - (current_time - oldest_call)
                logger.warning(
                    f"Global rate limit exceeded (per-minute) for {endpoint}: "
                    f"wait {wait_time:.1f}s"
                )
                return False, wait_time, 'global'
            
            # Check global per-hour limit
            if len(history['hour']) >= self.calls_per_hour:
                oldest_call = history['hour'][0]
                wait_time = 3600 - (current_time - oldest_call)
                logger.warning(
                    f"Global rate limit exceeded (per-hour) for {endpoint}: "
                    f"wait {wait_time:.1f}s"
                )
                return False, wait_time, 'global'
            
            # Check per-IP limits if enabled and IP provided
            if self.per_ip_enabled and ip_address:
                self._cleanup_old_calls_for_ip(ip_address, endpoint)
                ip_history = self.ip_call_history[ip_address][endpoint]
                
                # Check per-IP per-minute limit
                if len(ip_history['minute']) >= self.per_ip_calls_per_minute:
                    oldest_call = ip_history['minute'][0]
                    wait_time = 60 - (current_time - oldest_call)
                    logger.warning(
                        f"Per-IP rate limit exceeded (per-minute) for {endpoint} "
                        f"from {ip_address}: wait {wait_time:.1f}s"
                    )
                    return False, wait_time, 'per_ip'
                
                # Check per-IP per-hour limit
                if len(ip_history['hour']) >= self.per_ip_calls_per_hour:
                    oldest_call = ip_history['hour'][0]
                    wait_time = 3600 - (current_time - oldest_call)
                    logger.warning(
                        f"Per-IP rate limit exceeded (per-hour) for {endpoint} "
                        f"from {ip_address}: wait {wait_time:.1f}s"
                    )
                    return False, wait_time, 'per_ip'
            
            return True, None, None
    
    def record_call(
        self,
        endpoint: str = "default",
        ip_address: Optional[str] = None
    ) -> None:
        """
        Record a successful call
        
        Args:
            endpoint: Endpoint name
            ip_address: Client IP address (optional)
        """
        if not self.enabled:
            return
        
        with self.lock:
            current_time = time.time()
            
            # Record in global history
            history = self.call_history[endpoint]
            history['minute'].append(current_time)
            history['hour'].append(current_time)
            
            # Record in per-IP history if enabled
            if self.per_ip_enabled and ip_address:
                ip_history = self.ip_call_history[ip_address][endpoint]
                ip_history['minute'].append(current_time)
                ip_history['hour'].append(current_time)
                
                logger.debug(
                    f"Rate limit: {endpoint} from {ip_address} - "
                    f"Global: {len(history['minute'])}/{self.calls_per_minute} (min), "
                    f"Per-IP: {len(ip_history['minute'])}/{self.per_ip_calls_per_minute} (min)"
                )
            else:
                logger.debug(
                    f"Rate limit: {endpoint} - "
                    f"{len(history['minute'])}/{self.calls_per_minute} (minute), "
                    f"{len(history['hour'])}/{self.calls_per_hour} (hour)"
                )
    
    def get_stats(
        self,
        endpoint: str = "default",
        ip_address: Optional[str] = None
    ) -> Dict:
        """
        Get rate limit statistics
        
        Args:
            endpoint: Endpoint name
            ip_address: Client IP address (optional)
        """
        if not self.enabled:
            return {"enabled": False}
        
        with self.lock:
            self._cleanup_old_calls(endpoint)
            history = self.call_history[endpoint]
            
            stats = {
                "enabled": True,
                "endpoint": endpoint,
                "global": {
                    "calls_last_minute": len(history['minute']),
                    "calls_per_minute_limit": self.calls_per_minute,
                    "calls_last_hour": len(history['hour']),
                    "calls_per_hour_limit": self.calls_per_hour,
                    "minute_remaining": self.calls_per_minute - len(history['minute']),
                    "hour_remaining": self.calls_per_hour - len(history['hour'])
                }
            }
            
            # Add per-IP stats if requested
            if self.per_ip_enabled and ip_address:
                self._cleanup_old_calls_for_ip(ip_address, endpoint)
                ip_history = self.ip_call_history[ip_address][endpoint]
                
                stats["per_ip"] = {
                    "ip_address": ip_address,
                    "calls_last_minute": len(ip_history['minute']),
                    "calls_per_minute_limit": self.per_ip_calls_per_minute,
                    "calls_last_hour": len(ip_history['hour']),
                    "calls_per_hour_limit": self.per_ip_calls_per_hour,
                    "minute_remaining": self.per_ip_calls_per_minute - len(ip_history['minute']),
                    "hour_remaining": self.per_ip_calls_per_hour - len(ip_history['hour'])
                }
            
            # Add summary stats
            if self.per_ip_enabled:
                stats["summary"] = {
                    "total_ips_tracked": len(self.ip_call_history),
                    "per_ip_limiting_enabled": True
                }
            
            return stats
    
    def reset(self, endpoint: Optional[str] = None, ip_address: Optional[str] = None) -> None:
        """
        Reset rate limits
        
        Args:
            endpoint: Specific endpoint (None = all endpoints)
            ip_address: Specific IP (None = all IPs)
        """
        if not self.enabled:
            return
        
        with self.lock:
            if ip_address:
                # Reset specific IP
                if ip_address in self.ip_call_history:
                    if endpoint:
                        if endpoint in self.ip_call_history[ip_address]:
                            del self.ip_call_history[ip_address][endpoint]
                            logger.info(f"Rate limit reset for {endpoint} from {ip_address}")
                    else:
                        del self.ip_call_history[ip_address]
                        logger.info(f"Rate limits reset for all endpoints from {ip_address}")
            elif endpoint:
                # Reset specific endpoint (global + all IPs)
                if endpoint in self.call_history:
                    del self.call_history[endpoint]
                    logger.info(f"Global rate limit reset for {endpoint}")
                
                # Reset endpoint for all IPs
                for ip_data in self.ip_call_history.values():
                    if endpoint in ip_data:
                        del ip_data[endpoint]
            else:
                # Reset everything
                self.call_history.clear()
                self.ip_call_history.clear()
                logger.info("All rate limits reset")


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limited(endpoint: Optional[str] = None, wait: bool = False, check_ip: bool = True):
    """
    Decorator to apply rate limiting to functions
    
    Args:
        endpoint: Endpoint identifier (uses function name if None)
        wait: If True, wait when rate limited instead of raising error
        check_ip: If True, check per-IP rate limits (requires ip_address in kwargs)
    
    Usage:
        @rate_limited(endpoint="search", wait=True, check_ip=True)
        def search_videos(query, ip_address=None):
            # ... function code
    """
    def decorator(func: Callable) -> Callable:
        endpoint_name = endpoint or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract IP address from kwargs if available
            ip_address = kwargs.get('ip_address') if check_ip else None
            
            # Check rate limit
            allowed, wait_time, limit_type = rate_limiter.is_allowed(endpoint_name, ip_address)
            
            if not allowed:
                error_msg = f"Rate limit exceeded ({limit_type or 'global'})"
                if ip_address:
                    error_msg += f" for IP {ip_address}"
                
                if wait and wait_time:
                    logger.info(f"{error_msg}, waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                else:
                    return {
                        "success": False,
                        "error": "Rate limit exceeded",
                        "limit_type": limit_type,
                        "wait_time": wait_time,
                        "message": f"Please wait {wait_time:.1f} seconds before retrying"
                    }
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Record successful call
            if result and isinstance(result, dict) and result.get("success"):
                rate_limiter.record_call(endpoint_name, ip_address)
            
            return result
        
        return wrapper
    return decorator


# Convenience functions
def check_rate_limit(
    endpoint: str = "default",
    ip_address: Optional[str] = None
) -> Tuple[bool, Optional[float], Optional[str]]:
    """Check if endpoint is rate limited"""
    return rate_limiter.is_allowed(endpoint, ip_address)


def record_api_call(endpoint: str = "default", ip_address: Optional[str] = None) -> None:
    """Record an API call"""
    rate_limiter.record_call(endpoint, ip_address)


def get_rate_stats(endpoint: str = "default", ip_address: Optional[str] = None) -> Dict:
    """Get rate limit statistics"""
    return rate_limiter.get_stats(endpoint, ip_address)


def reset_rate_limits(endpoint: Optional[str] = None, ip_address: Optional[str] = None) -> None:
    """Reset rate limits"""
    rate_limiter.reset(endpoint, ip_address)
