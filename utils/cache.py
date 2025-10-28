#!/usr/bin/env python3
"""
Cache management for YouTube MCP Server
Implements hybrid caching strategy with memory and disk layers
Includes automatic cleanup and size management
"""

import json
import hashlib
import logging
import os
import time
import threading
from typing import Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
from pathlib import Path

from cachetools import TTLCache
from diskcache import Cache
from config import config

# Import encrypted cache (v2.1)
try:
    from utils.cache.encrypted_cache import EncryptedDiskCache
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

logger = logging.getLogger(__name__)

if not ENCRYPTION_AVAILABLE:
    logger.warning("⚠️  Encrypted cache not available - install cryptography package")


class CacheManager:
    """Manages two-tier caching: memory (fast) + disk (persistent) with automatic cleanup"""
    
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
            # Use encrypted cache if enabled and available (v2.1)
            use_encryption = config.cache.encryption_enabled and ENCRYPTION_AVAILABLE
            
            if use_encryption:
                self.disk_cache = EncryptedDiskCache(
                    cache_dir=config.cache.cache_dir,
                    auto_cleanup=True
                )
                logger.info("🔐 Using encrypted disk cache (Fernet/AES-128)")
            else:
                self.disk_cache = Cache(config.cache.cache_dir)
                if config.cache.encryption_enabled:
                    logger.warning("⚠️  Encryption enabled but cryptography not installed")
            
            self.encryption_enabled = use_encryption
            
            # Cleanup configuration
            self.max_disk_size_bytes = config.cache.max_disk_size_mb * 1024 * 1024
            self.cleanup_interval_seconds = config.cache.cleanup_interval_hours * 3600
            self.last_cleanup_time = time.time()
            
            # Start background cleanup thread
            self._start_cleanup_thread()
            
            logger.info(
                f"Cache initialized: memory={config.cache.max_memory_items} items, "
                f"disk={config.cache.cache_dir}, ttl={config.cache.ttl_seconds}s, "
                f"max_size={config.cache.max_disk_size_mb}MB"
            )
        else:
            logger.info("Cache disabled")
    
    def _start_cleanup_thread(self):
        """Start background thread for automatic cache cleanup"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(self.cleanup_interval_seconds)
                    self.auto_cleanup()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("Cache cleanup thread started")
    
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
        
        # Encrypted cache uses different API
        if self.encryption_enabled:
            self.disk_cache.set(key, value, ttl=ttl)
        else:
            self.disk_cache.set(key, value, expire=ttl)
        
        logger.debug(f"Cache SET: {key[:16]}... (ttl={ttl}s)")
        
        # Check if cleanup is needed
        self._check_cleanup_needed()
    
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
    
    def _check_cleanup_needed(self) -> None:
        """Check if cleanup is needed based on size or time"""
        current_time = time.time()
        
        # Time-based cleanup check
        if current_time - self.last_cleanup_time < self.cleanup_interval_seconds:
            return
        
        # Size-based cleanup check
        try:
            disk_size = self.get_disk_cache_size()
            if disk_size > self.max_disk_size_bytes:
                logger.info(f"Cache size ({disk_size / 1024 / 1024:.2f}MB) exceeds limit, cleaning up...")
                self.auto_cleanup()
        except Exception as e:
            logger.warning(f"Failed to check cache size: {e}")
    
    def get_disk_cache_size(self) -> int:
        """
        Get total size of disk cache in bytes
        
        Returns:
            Total size in bytes
        """
        if not self.enabled:
            return 0
        
        try:
            cache_dir = Path(config.cache.cache_dir)
            if not cache_dir.exists():
                return 0
            
            total_size = 0
            for file in cache_dir.rglob('*'):
                if file.is_file():
                    total_size += file.stat().st_size
            
            return total_size
        except Exception as e:
            logger.warning(f"Failed to calculate cache size: {e}")
            return 0
    
    def auto_cleanup(self) -> dict:
        """
        Automatically clean up old and large cache entries
        
        Returns:
            Dictionary with cleanup statistics
        """
        if not self.enabled:
            return {"enabled": False}
        
        logger.info("Starting automatic cache cleanup...")
        
        initial_size = self.get_disk_cache_size()
        initial_count = len(self.disk_cache)
        
        # Disk cache cleanup (using diskcache's built-in methods)
        try:
            # Remove expired entries
            self.disk_cache.expire()
            
            # If still over limit, remove oldest entries
            current_size = self.get_disk_cache_size()
            if current_size > self.max_disk_size_bytes:
                # Calculate how much to remove
                target_size = self.max_disk_size_bytes * 0.8  # 80% of max
                
                # Remove oldest entries until under target
                removed = 0
                for key in list(self.disk_cache):
                    if self.get_disk_cache_size() <= target_size:
                        break
                    self.disk_cache.delete(key)
                    removed += 1
                
                logger.info(f"Removed {removed} old entries to stay under size limit")
        
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
        
        final_size = self.get_disk_cache_size()
        final_count = len(self.disk_cache)
        
        self.last_cleanup_time = time.time()
        
        stats = {
            "enabled": True,
            "initial_size_mb": initial_size / 1024 / 1024,
            "final_size_mb": final_size / 1024 / 1024,
            "freed_mb": (initial_size - final_size) / 1024 / 1024,
            "initial_count": initial_count,
            "final_count": final_count,
            "removed_count": initial_count - final_count,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(
            f"Cache cleanup completed: "
            f"freed {stats['freed_mb']:.2f}MB, "
            f"removed {stats['removed_count']} entries"
        )
        
        return stats
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.enabled:
            return {"enabled": False}
        
        disk_size_bytes = self.get_disk_cache_size()
        
        stats = {
            "enabled": True,
            "memory_size": len(self.memory_cache),
            "memory_maxsize": self.memory_cache.maxsize,
            "disk_size": len(self.disk_cache),
            "disk_size_mb": disk_size_bytes / 1024 / 1024,
            "disk_size_limit_mb": config.cache.max_disk_size_mb,
            "disk_usage_percent": (disk_size_bytes / self.max_disk_size_bytes) * 100 if self.max_disk_size_bytes > 0 else 0,
            "ttl_seconds": config.cache.ttl_seconds,
            "last_cleanup": datetime.fromtimestamp(self.last_cleanup_time).isoformat(),
            "encryption_enabled": self.encryption_enabled
        }
        
        # Add encrypted cache-specific stats if available
        if self.encryption_enabled and hasattr(self.disk_cache, 'stats'):
            stats["encrypted_cache_stats"] = self.disk_cache.stats()
        
        return stats


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


def cleanup_cache() -> dict:
    """Manually trigger cache cleanup"""
    return cache_manager.auto_cleanup()
