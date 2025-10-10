#!/usr/bin/env python3
"""
Cache management for YouTube MCP Server
Implements hybrid caching strategy with memory and disk layers
"""

import json
import hashlib
import logging
from typing import Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta

from cachetools import TTLCache
from diskcache import Cache
from config import config

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages two-tier caching: memory (fast) + disk (persistent)"""
    
    def __init__(self):
        """Initialize cache manager with memory and disk caches"""
        self.enabled = config.cache.enabled
        
        if self.enabled:
            # Memory cache - fast, limited size
            self.memory_cache = TTLCache(
                maxsize=config.cache.max_memory_items,
                ttl=config.cache.ttl_seconds
            )
            
            # Disk cache - slower, larger capacity
            self.disk_cache = Cache(config.cache.cache_dir)
            
            logger.info(
                f"Cache initialized: memory={config.cache.max_memory_items} items, "
                f"disk={config.cache.cache_dir}, ttl={config.cache.ttl_seconds}s"
            )
        else:
            logger.info("Cache disabled")
    
    def _generate_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate unique cache key from function name and arguments"""
        # Create deterministic string from arguments
        key_parts = [func_name]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        key_string = ":".join(key_parts)
        
        # Hash for consistent length
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (checks memory first, then disk)"""
        if not self.enabled:
            return None
        
        # Try memory cache first (fastest)
        value = self.memory_cache.get(key)
        if value is not None:
            logger.debug(f"Cache HIT (memory): {key[:16]}...")
            return value
        
        # Try disk cache
        value = self.disk_cache.get(key)
        if value is not None:
            logger.debug(f"Cache HIT (disk): {key[:16]}...")
            # Promote to memory cache
            self.memory_cache[key] = value
            return value
        
        logger.debug(f"Cache MISS: {key[:16]}...")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in both memory and disk caches"""
        if not self.enabled:
            return
        
        ttl = ttl or config.cache.ttl_seconds
        
        # Store in both caches
        self.memory_cache[key] = value
        self.disk_cache.set(key, value, expire=ttl)
        
        logger.debug(f"Cache SET: {key[:16]}... (ttl={ttl}s)")
    
    def delete(self, key: str) -> None:
        """Delete value from both caches"""
        if not self.enabled:
            return
        
        self.memory_cache.pop(key, None)
        self.disk_cache.delete(key)
        
        logger.debug(f"Cache DELETE: {key[:16]}...")
    
    def clear(self) -> None:
        """Clear all caches"""
        if not self.enabled:
            return
        
        self.memory_cache.clear()
        self.disk_cache.clear()
        
        logger.info("Cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.enabled:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "memory_size": len(self.memory_cache),
            "memory_maxsize": self.memory_cache.maxsize,
            "disk_size": len(self.disk_cache),
            "ttl_seconds": config.cache.ttl_seconds
        }


# Global cache manager instance
cache_manager = CacheManager()


def cached(ttl: Optional[int] = None):
    """
    Decorator to cache function results
    
    Usage:
        @cached(ttl=3600)
        def expensive_function(arg1, arg2):
            # ... do work
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager._generate_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result if successful
            if result and isinstance(result, dict) and result.get("success"):
                cache_manager.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_key(*args, **kwargs) -> str:
    """Generate cache key for manual cache operations"""
    return cache_manager._generate_key("manual", *args, **kwargs)


# Convenience functions
def get_cached(key: str) -> Optional[Any]:
    """Get value from cache"""
    return cache_manager.get(key)


def set_cached(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """Set value in cache"""
    cache_manager.set(key, value, ttl)


def delete_cached(key: str) -> None:
    """Delete value from cache"""
    cache_manager.delete(key)


def clear_cache() -> None:
    """Clear all caches"""
    cache_manager.clear()


def cache_stats() -> dict:
    """Get cache statistics"""
    return cache_manager.get_stats()
