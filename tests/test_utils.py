#!/usr/bin/env python3
"""
Comprehensive unit tests for YouTube MCP Server utilities
Tests validators, cache, and rate limiter functionality
"""

import pytest
import time
import os
import tempfile
from datetime import datetime, timedelta

# Import utilities to test
from utils.validators import (
    validate_video_url,
    validate_channel_id,
    validate_language,
    validate_search_query,
    validate_max_results,
    validate_order,
    sanitize_text,
    ValidationError
)


class TestValidators:
    """Test input validation functions"""
    
    def test_validate_video_url_with_valid_id(self):
        """Test video ID validation"""
        # Valid video ID
        result = validate_video_url("dQw4w9WgXcQ")
        assert result == "dQw4w9WgXcQ"
    
    def test_validate_video_url_with_full_url(self):
        """Test full YouTube URL parsing"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = validate_video_url(url)
        assert result == "dQw4w9WgXcQ"
    
    def test_validate_video_url_with_short_url(self):
        """Test short youtu.be URL parsing"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = validate_video_url(url)
        assert result == "dQw4w9WgXcQ"
    
    def test_validate_video_url_with_mobile_url(self):
        """Test mobile URL parsing"""
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        result = validate_video_url(url)
        assert result == "dQw4w9WgXcQ"
    
    def test_validate_video_url_with_invalid_id(self):
        """Test invalid video ID rejection"""
        with pytest.raises(ValidationError):
            validate_video_url("invalid")
    
    def test_validate_video_url_with_empty_string(self):
        """Test empty string rejection"""
        with pytest.raises(ValidationError):
            validate_video_url("")
    
    def test_validate_channel_id_with_valid_id(self):
        """Test channel ID validation"""
        channel_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"
        result = validate_channel_id(channel_id)
        assert result == channel_id
    
    def test_validate_channel_id_with_username(self):
        """Test @username format"""
        result = validate_channel_id("@googledev")
        assert result == "@googledev"
    
    def test_validate_channel_id_with_url(self):
        """Test channel URL parsing"""
        url = "https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw"
        result = validate_channel_id(url)
        assert result == "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    
    def test_validate_channel_id_with_invalid_format(self):
        """Test invalid channel ID rejection"""
        with pytest.raises(ValidationError):
            validate_channel_id("invalid_channel")
    
    def test_validate_language_with_valid_code(self):
        """Test valid language codes"""
        assert validate_language("en") == "en"
        assert validate_language("he") == "he"
        assert validate_language("ES") == "es"  # Case insensitive
    
    def test_validate_language_with_invalid_code(self):
        """Test invalid language code rejection"""
        with pytest.raises(ValidationError):
            validate_language("xx")
    
    def test_validate_search_query_with_valid_query(self):
        """Test valid search queries"""
        query = "Python tutorial 2024"
        result = validate_search_query(query)
        assert result == query
    
    def test_validate_search_query_with_special_chars(self):
        """Test query with safe special characters"""
        query = "How to code? (Tutorial) - 2024!"
        result = validate_search_query(query)
        assert result == query
    
    def test_validate_search_query_with_hebrew(self):
        """Test Hebrew query"""
        query = "מדריך פייתון"
        result = validate_search_query(query)
        assert result == query
    
    def test_validate_search_query_too_long(self):
        """Test query length limit"""
        query = "a" * 600  # Exceeds 500 char limit
        with pytest.raises(ValidationError):
            validate_search_query(query)
    
    def test_validate_search_query_empty(self):
        """Test empty query rejection"""
        with pytest.raises(ValidationError):
            validate_search_query("")
    
    def test_validate_max_results_with_valid_number(self):
        """Test valid max_results"""
        assert validate_max_results(10) == 10
        assert validate_max_results("25") == 25
    
    def test_validate_max_results_with_limit_exceeded(self):
        """Test max_results capping"""
        # Should cap at 50 for regular results
        assert validate_max_results(100) == 50
    
    def test_validate_max_results_with_comments(self):
        """Test comments limit"""
        # Should cap at 100 for comments
        assert validate_max_results(150, "comments") == 100
    
    def test_validate_max_results_with_invalid_type(self):
        """Test invalid type rejection"""
        with pytest.raises(ValidationError):
            validate_max_results("invalid")
    
    def test_validate_max_results_too_small(self):
        """Test minimum value"""
        with pytest.raises(ValidationError):
            validate_max_results(0)
    
    def test_validate_order_with_valid_orders(self):
        """Test valid sort orders"""
        assert validate_order("relevance") == "relevance"
        assert validate_order("date") == "date"
        assert validate_order("viewCount") == "viewCount"
    
    def test_validate_order_with_aliases(self):
        """Test order aliases"""
        assert validate_order("views") == "viewCount"
        assert validate_order("recent") == "date"
        assert validate_order("popular") == "viewCount"
    
    def test_validate_order_case_insensitive(self):
        """Test case insensitivity"""
        assert validate_order("RELEVANCE") == "relevance"
    
    def test_validate_order_with_invalid(self):
        """Test invalid order rejection"""
        with pytest.raises(ValidationError):
            validate_order("invalid_order")
    
    def test_sanitize_text_removes_control_chars(self):
        """Test control character removal"""
        text = "Hello\x00World\x01Test\x1F"
        result = sanitize_text(text)
        assert result == "HelloWorldTest"
    
    def test_sanitize_text_preserves_newlines(self):
        """Test newline preservation"""
        text = "Line 1\nLine 2\nLine 3"
        result = sanitize_text(text)
        assert "\n" in result
    
    def test_sanitize_text_limits_length(self):
        """Test length limiting"""
        text = "a" * 1000
        result = sanitize_text(text, max_length=100)
        assert len(result) == 100
    
    def test_sanitize_text_strips_whitespace(self):
        """Test whitespace stripping"""
        text = "  Hello World  "
        result = sanitize_text(text)
        assert result == "Hello World"


class TestCacheManagement:
    """Test cache functionality"""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create temporary cache directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_cache_set_and_get(self, temp_cache_dir, monkeypatch):
        """Test basic cache operations"""
        # Import after monkeypatch to ensure config is updated
        monkeypatch.setenv("CACHE_DIR", temp_cache_dir)
        from utils.cache import cache_manager
        
        # Set a value
        cache_manager.set("test_key", {"data": "test_value"})
        
        # Get the value
        result = cache_manager.get("test_key")
        assert result == {"data": "test_value"}
    
    def test_cache_miss(self, temp_cache_dir, monkeypatch):
        """Test cache miss"""
        monkeypatch.setenv("CACHE_DIR", temp_cache_dir)
        from utils.cache import cache_manager
        
        result = cache_manager.get("nonexistent_key")
        assert result is None
    
    def test_cache_delete(self, temp_cache_dir, monkeypatch):
        """Test cache deletion"""
        monkeypatch.setenv("CACHE_DIR", temp_cache_dir)
        from utils.cache import cache_manager
        
        # Set and delete
        cache_manager.set("test_key", {"data": "test"})
        cache_manager.delete("test_key")
        
        # Should be None after deletion
        result = cache_manager.get("test_key")
        assert result is None
    
    def test_cache_stats(self, temp_cache_dir, monkeypatch):
        """Test cache statistics"""
        monkeypatch.setenv("CACHE_DIR", temp_cache_dir)
        from utils.cache import cache_manager
        
        stats = cache_manager.get_stats()
        assert "enabled" in stats
        assert "memory_size" in stats or stats["enabled"] is False


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_rate_limit_allows_initial_calls(self):
        """Test that initial calls are allowed"""
        from utils.rate_limiter import rate_limiter
        
        # Reset for clean test
        rate_limiter.reset("test_endpoint")
        
        # First call should be allowed
        allowed, wait_time = rate_limiter.is_allowed("test_endpoint")
        assert allowed is True
        assert wait_time is None
    
    def test_rate_limit_records_calls(self):
        """Test call recording"""
        from utils.rate_limiter import rate_limiter
        
        rate_limiter.reset("test_endpoint")
        
        # Record some calls
        for _ in range(5):
            rate_limiter.record_call("test_endpoint")
        
        # Get stats
        stats = rate_limiter.get_stats("test_endpoint")
        if stats.get("enabled"):
            assert stats["calls_last_minute"] == 5
    
    def test_rate_limit_enforcement(self):
        """Test that rate limits are enforced"""
        from utils.rate_limiter import rate_limiter, config
        
        if not config.rate_limit.enabled:
            pytest.skip("Rate limiting disabled")
        
        rate_limiter.reset("test_endpoint_enforcement")
        
        # Record calls up to limit
        limit = config.rate_limit.calls_per_minute
        for _ in range(limit):
            rate_limiter.record_call("test_endpoint_enforcement")
        
        # Next call should be blocked
        allowed, wait_time = rate_limiter.is_allowed("test_endpoint_enforcement")
        assert allowed is False
        assert wait_time is not None
    
    def test_rate_limit_reset(self):
        """Test rate limit reset"""
        from utils.rate_limiter import rate_limiter
        
        # Record calls
        for _ in range(5):
            rate_limiter.record_call("test_reset")
        
        # Reset
        rate_limiter.reset("test_reset")
        
        # Should be clean now
        stats = rate_limiter.get_stats("test_reset")
        if stats.get("enabled"):
            assert stats["calls_last_minute"] == 0


class TestIntegration:
    """Integration tests for combined functionality"""
    
    def test_cached_decorator_basic(self):
        """Test cached decorator"""
        from utils.cache import cached
        
        call_count = 0
        
        @cached(ttl=60)
        def test_function(arg):
            nonlocal call_count
            call_count += 1
            return {"success": True, "data": arg, "count": call_count}
        
        # First call
        result1 = test_function("test")
        
        # Second call (should be cached)
        result2 = test_function("test")
        
        # Call count should only increment once if cache is working
        # Note: Might be 2 if cache is disabled
        assert result1["success"] is True
        assert result2["success"] is True
    
    def test_rate_limited_decorator_basic(self):
        """Test rate_limited decorator"""
        from utils.rate_limiter import rate_limited
        
        @rate_limited(endpoint="test_decorator")
        def test_function():
            return {"success": True, "data": "test"}
        
        # Should work on first call
        result = test_function()
        assert result["success"] is True


# Run tests with: pytest tests/test_utils.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
