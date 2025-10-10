#!/usr/bin/env python3
"""
Unit tests for YouTube MCP Server utilities
Tests for validation, caching, and rate limiting
"""

import pytest
import time
from unittest.mock import Mock, patch

# Import modules to test
from utils.validators import (
    validator,
    ValidationError,
    validate_video_url,
    validate_channel_id,
    validate_language,
    validate_search_query,
    validate_max_results,
    validate_order
)
from utils.cache import cache_manager, cached
from utils.rate_limiter import rate_limiter


# ============================================================================
# VALIDATOR TESTS
# ============================================================================

class TestValidators:
    """Test input validation functions"""
    
    def test_validate_video_url_with_id(self):
        """Test validation with direct video ID"""
        video_id = "dQw4w9WgXcQ"
        result = validate_video_url(video_id)
        assert result == video_id
    
    def test_validate_video_url_with_standard_url(self):
        """Test validation with standard YouTube URL"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = validate_video_url(url)
        assert result == "dQw4w9WgXcQ"
    
    def test_validate_video_url_with_short_url(self):
        """Test validation with youtu.be URL"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = validate_video_url(url)
        assert result == "dQw4w9WgXcQ"
    
    def test_validate_video_url_invalid(self):
        """Test validation with invalid URL"""
        with pytest.raises(ValidationError):
            validate_video_url("not-a-valid-url")
    
    def test_validate_video_url_empty(self):
        """Test validation with empty string"""
        with pytest.raises(ValidationError):
            validate_video_url("")
    
    def test_validate_channel_id_with_id(self):
        """Test channel ID validation with valid ID"""
        channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"
        result = validate_channel_id(channel_id)
        assert result == channel_id
    
    def test_validate_channel_id_with_username(self):
        """Test channel ID validation with @username"""
        username = "@googledev"
        result = validate_channel_id(username)
        assert result == username  # Returns as-is for API resolution
    
    def test_validate_language_valid(self):
        """Test language validation with valid codes"""
        assert validate_language("en") == "en"
        assert validate_language("he") == "he"
        assert validate_language("ES") == "es"  # Case insensitive
    
    def test_validate_language_invalid(self):
        """Test language validation with invalid code"""
        with pytest.raises(ValidationError):
            validate_language("xyz")
    
    def test_validate_search_query_valid(self):
        """Test search query validation"""
        query = "Python programming tutorial"
        result = validate_search_query(query)
        assert result == query
    
    def test_validate_search_query_too_long(self):
        """Test search query that's too long"""
        query = "a" * 600  # Exceeds max_query_length
        with pytest.raises(ValidationError):
            validate_search_query(query)
    
    def test_validate_search_query_empty(self):
        """Test empty search query"""
        with pytest.raises(ValidationError):
            validate_search_query("")
    
    def test_validate_max_results_valid(self):
        """Test max_results validation"""
        assert validate_max_results(10) == 10
        assert validate_max_results("20") == 20
    
    def test_validate_max_results_exceeds_limit(self):
        """Test max_results exceeding limit"""
        result = validate_max_results(200)
        assert result <= 50  # Should be capped
    
    def test_validate_max_results_negative(self):
        """Test negative max_results"""
        with pytest.raises(ValidationError):
            validate_max_results(-5)
    
    def test_validate_order_valid(self):
        """Test order validation with valid values"""
        assert validate_order("relevance") == "relevance"
        assert validate_order("date") == "date"
        assert validate_order("viewCount") == "viewCount"
    
    def test_validate_order_mapped(self):
        """Test order validation with mapped values"""
        assert validate_order("views") == "viewCount"
        assert validate_order("recent") == "date"
    
    def test_validate_order_invalid(self):
        """Test order validation with invalid value"""
        with pytest.raises(ValidationError):
            validate_order("invalid_order")


# ============================================================================
# CACHE TESTS
# ============================================================================

class TestCache:
    """Test caching functionality"""
    
    def setup_method(self):
        """Clear cache before each test"""
        cache_manager.clear()
    
    def test_cache_set_and_get(self):
        """Test basic cache operations"""
        key = "test_key"
        value = {"data": "test_value"}
        
        cache_manager.set(key, value)
        result = cache_manager.get(key)
        
        assert result == value
    
    def test_cache_miss(self):
        """Test cache miss"""
        result = cache_manager.get("nonexistent_key")
        assert result is None
    
    def test_cache_delete(self):
        """Test cache deletion"""
        key = "test_key"
        value = {"data": "test"}
        
        cache_manager.set(key, value)
        cache_manager.delete(key)
        result = cache_manager.get(key)
        
        assert result is None
    
    def test_cache_decorator(self):
        """Test cache decorator"""
        call_count = 0
        
        @cached(ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return {"success": True, "value": x * 2}
        
        # First call - should execute function
        result1 = expensive_function(5)
        assert result1["value"] == 10
        assert call_count == 1
        
        # Second call with same argument - should use cache
        result2 = expensive_function(5)
        assert result2["value"] == 10
        assert call_count == 1  # Should not increment
        
        # Call with different argument - should execute again
        result3 = expensive_function(10)
        assert result3["value"] == 20
        assert call_count == 2
    
    def test_cache_stats(self):
        """Test cache statistics"""
        stats = cache_manager.get_stats()
        
        assert "enabled" in stats
        if stats["enabled"]:
            assert "memory_size" in stats
            assert "disk_size" in stats


# ============================================================================
# RATE LIMITER TESTS
# ============================================================================

class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def setup_method(self):
        """Reset rate limiter before each test"""
        rate_limiter.reset()
    
    def test_rate_limiter_allows_calls(self):
        """Test that calls are allowed under limit"""
        endpoint = "test_endpoint"
        
        # Should allow call
        allowed, wait_time = rate_limiter.is_allowed(endpoint)
        assert allowed is True
        assert wait_time is None
    
    def test_rate_limiter_records_calls(self):
        """Test call recording"""
        endpoint = "test_endpoint"
        
        # Record some calls
        for _ in range(5):
            rate_limiter.record_call(endpoint)
        
        # Check stats
        stats = rate_limiter.get_stats(endpoint)
        if stats["enabled"]:
            assert stats["calls_last_minute"] == 5
    
    def test_rate_limiter_reset(self):
        """Test reset functionality"""
        endpoint = "test_endpoint"
        
        # Record calls
        rate_limiter.record_call(endpoint)
        rate_limiter.record_call(endpoint)
        
        # Reset
        rate_limiter.reset(endpoint)
        
        # Stats should show no calls
        stats = rate_limiter.get_stats(endpoint)
        if stats["enabled"]:
            assert stats["calls_last_minute"] == 0
    
    def test_rate_limiter_decorator(self):
        """Test rate limiter decorator"""
        from utils.rate_limiter import rate_limited
        
        call_count = 0
        
        @rate_limited(endpoint="test_func")
        def test_function():
            nonlocal call_count
            call_count += 1
            return {"success": True}
        
        # First call should succeed
        result = test_function()
        assert result["success"] is True
        assert call_count == 1


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Test integration of multiple components"""
    
    def test_cache_and_rate_limit_together(self):
        """Test that caching and rate limiting work together"""
        from utils import cached, rate_limited
        
        call_count = 0
        
        @rate_limited(endpoint="integrated_test")
        @cached(ttl=60)
        def integrated_function(x):
            nonlocal call_count
            call_count += 1
            return {"success": True, "result": x * 2}
        
        # First call - executes function and caches
        result1 = integrated_function(5)
        assert result1["result"] == 10
        assert call_count == 1
        
        # Second call - uses cache, no rate limit hit
        result2 = integrated_function(5)
        assert result2["result"] == 10
        assert call_count == 1  # Should not increment


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
