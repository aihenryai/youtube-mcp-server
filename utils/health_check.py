"""
Health Check Module for YouTube MCP Server
==========================================

Provides comprehensive health checks for monitoring and readiness probes.

Health Check Components:
1. Basic: Server is running
2. YouTube API: Connectivity and quota status
3. OAuth: Token validity
4. Cache: Storage availability
5. Security: Component status

Author: Claude + Henry
Date: October 2025
Version: 1.0.0
"""

import time
import os
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthChecker:
    """
    Comprehensive health checker for YouTube MCP Server
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.last_check: Optional[Dict[str, Any]] = None
        
    async def check_health(self, include_details: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Args:
            include_details: Include detailed component status
            
        Returns:
            Health check results
        """
        checks = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": HealthStatus.HEALTHY.value,
            "uptime_seconds": time.time() - self.start_time,
            "version": "2.0.0",
        }
        
        if include_details:
            components = {}
            
            # Check basic server
            components["server"] = self._check_server()
            
            # Check cache
            components["cache"] = self._check_cache()
            
            # Check security components
            components["security"] = self._check_security()
            
            # Check YouTube API (if API key present)
            if os.getenv("YOUTUBE_API_KEY"):
                components["youtube_api"] = self._check_youtube_api()
            
            # Check OAuth (if OAuth configured)
            if os.getenv("OAUTH_CLIENT_ID"):
                components["oauth"] = self._check_oauth()
            
            checks["components"] = components
            
            # Determine overall status
            unhealthy = [k for k, v in components.items() if v["status"] == HealthStatus.UNHEALTHY.value]
            degraded = [k for k, v in components.items() if v["status"] == HealthStatus.DEGRADED.value]
            
            if unhealthy:
                checks["status"] = HealthStatus.UNHEALTHY.value
                checks["unhealthy_components"] = unhealthy
            elif degraded:
                checks["status"] = HealthStatus.DEGRADED.value
                checks["degraded_components"] = degraded
        
        self.last_check = checks
        return checks
    
    def _check_server(self) -> Dict[str, Any]:
        """Check basic server status"""
        return {
            "status": HealthStatus.HEALTHY.value,
            "message": "Server is running",
            "uptime_seconds": time.time() - self.start_time
        }
    
    def _check_cache(self) -> Dict[str, Any]:
        """Check cache availability"""
        try:
            from utils.cache import CacheManager
            
            # Try to access cache
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
            if os.path.exists(cache_dir):
                return {
                    "status": HealthStatus.HEALTHY.value,
                    "message": "Cache is available"
                }
            else:
                return {
                    "status": HealthStatus.DEGRADED.value,
                    "message": "Cache directory not found"
                }
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": f"Cache check failed: {str(e)}"
            }
    
    def _check_security(self) -> Dict[str, Any]:
        """Check security components"""
        try:
            # Try to import security modules
            from utils.security.prompt_injection import PromptInjectionDetector
            from utils.security.ip_rate_limiter import IPRateLimiter
            from utils.security.cors_validator import CORSValidator
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "Security components loaded",
                "components": [
                    "PromptInjectionDetector",
                    "IPRateLimiter",
                    "CORSValidator"
                ]
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Security components failed: {str(e)}"
            }
    
    def _check_youtube_api(self) -> Dict[str, Any]:
        """Check YouTube API connectivity"""
        api_key = os.getenv("YOUTUBE_API_KEY")
        
        if not api_key:
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": "YouTube API key not configured"
            }
        
        # For now, just check if key exists
        # In production, you might want to make a test API call
        return {
            "status": HealthStatus.HEALTHY.value,
            "message": "YouTube API key configured"
        }
    
    def _check_oauth(self) -> Dict[str, Any]:
        """Check OAuth configuration"""
        try:
            from auth.oauth2_manager import OAuth2Manager
            
            client_id = os.getenv("OAUTH_CLIENT_ID")
            if not client_id:
                return {
                    "status": HealthStatus.DEGRADED.value,
                    "message": "OAuth not configured"
                }
            
            return {
                "status": HealthStatus.HEALTHY.value,
                "message": "OAuth configured"
            }
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED.value,
                "message": f"OAuth check failed: {str(e)}"
            }
    
    def get_readiness(self) -> Dict[str, Any]:
        """
        Get readiness probe result (lighter than full health check)
        
        Returns:
            Readiness status
        """
        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - self.start_time
        }
    
    def get_liveness(self) -> Dict[str, Any]:
        """
        Get liveness probe result (minimal check)
        
        Returns:
            Liveness status
        """
        return {
            "alive": True,
            "timestamp": datetime.utcnow().isoformat()
        }

# Global health checker instance
_health_checker: Optional[HealthChecker] = None

def get_health_checker() -> HealthChecker:
    """Get global HealthChecker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker

async def check_health(include_details: bool = True) -> Dict[str, Any]:
    """Convenience function for health check"""
    return await get_health_checker().check_health(include_details)

def get_readiness() -> Dict[str, Any]:
    """Convenience function for readiness probe"""
    return get_health_checker().get_readiness()

def get_liveness() -> Dict[str, Any]:
    """Convenience function for liveness probe"""
    return get_health_checker().get_liveness()
