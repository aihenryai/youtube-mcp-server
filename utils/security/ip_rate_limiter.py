"""
Per-IP Rate Limiter
Prevents abuse by limiting requests per IP address
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class IPRateLimiter:
    """
    Per-IP rate limiting
    
    Features:
    - Per-minute and per-hour limits
    - Thread-safe
    - Automatic cleanup
    - Memory efficient
    """
    
    def __init__(
        self,
        max_per_minute: int = 10,
        max_per_hour: int = 100,
        cleanup_interval: int = 3600  # 1 hour
    ):
        """
        Initialize IP rate limiter
        
        Args:
            max_per_minute: Max requests per IP per minute
            max_per_hour: Max requests per IP per hour
            cleanup_interval: How often to clean old data (seconds)
        """
        self.max_per_minute = max_per_minute
        self.max_per_hour = max_per_hour
        self.cleanup_interval = cleanup_interval
        
        # Store request timestamps per IP
        self.minute_requests: Dict[str, List[datetime]] = defaultdict(list)
        self.hour_requests: Dict[str, List[datetime]] = defaultdict(list)
        
        # Track blocked IPs
        self.blocked_ips: Dict[str, datetime] = {}
        
        # Thread safety
        self.lock = Lock()
        
        # Last cleanup time
        self.last_cleanup = datetime.now()
        
        logger.info(
            f"IP Rate Limiter initialized: "
            f"{max_per_minute}/min, {max_per_hour}/hour"
        )
    
    def is_allowed(
        self,
        ip: str,
        endpoint: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check if IP is allowed to make request
        
        Args:
            ip: Client IP address
            endpoint: Optional endpoint name for logging
        
        Returns:
            (allowed: bool, reason: str)
        """
        with self.lock:
            # Check if IP is blocked
            if ip in self.blocked_ips:
                block_time = self.blocked_ips[ip]
                if datetime.now() - block_time < timedelta(hours=1):
                    logger.warning(
                        f"⚠️  Blocked IP attempted access: {ip} "
                        f"(endpoint: {endpoint})"
                    )
                    return False, "IP temporarily blocked due to abuse"
                else:
                    # Unblock after 1 hour
                    del self.blocked_ips[ip]
            
            # Cleanup old data periodically
            if (datetime.now() - self.last_cleanup).seconds > self.cleanup_interval:
                self._cleanup_all()
            
            now = datetime.now()
            
            # Clean old requests for this IP
            self._cleanup_ip(ip, now)
            
            # Check minute limit
            minute_count = len(self.minute_requests[ip])
            if minute_count >= self.max_per_minute:
                logger.warning(
                    f"⚠️  Rate limit exceeded (minute): {ip} "
                    f"({minute_count}/{self.max_per_minute})"
                )
                
                # Block IP if severely abusing
                if minute_count > self.max_per_minute * 2:
                    self.blocked_ips[ip] = now
                    logger.error(f"🚨 IP blocked for abuse: {ip}")
                
                return False, f"Rate limit exceeded ({self.max_per_minute}/minute)"
            
            # Check hour limit
            hour_count = len(self.hour_requests[ip])
            if hour_count >= self.max_per_hour:
                logger.warning(
                    f"⚠️  Rate limit exceeded (hour): {ip} "
                    f"({hour_count}/{self.max_per_hour})"
                )
                return False, f"Rate limit exceeded ({self.max_per_hour}/hour)"
            
            # Record request
            self.minute_requests[ip].append(now)
            self.hour_requests[ip].append(now)
            
            return True, ""
    
    def _cleanup_ip(self, ip: str, now: datetime):
        """Remove old requests for specific IP"""
        minute_cutoff = now - timedelta(minutes=1)
        hour_cutoff = now - timedelta(hours=1)
        
        self.minute_requests[ip] = [
            ts for ts in self.minute_requests[ip]
            if ts > minute_cutoff
        ]
        
        self.hour_requests[ip] = [
            ts for ts in self.hour_requests[ip]
            if ts > hour_cutoff
        ]
        
        # Clean empty entries
        if not self.minute_requests[ip]:
            del self.minute_requests[ip]
        if not self.hour_requests[ip]:
            del self.hour_requests[ip]
    
    def _cleanup_all(self):
        """Clean all old data"""
        now = datetime.now()
        
        # Clean requests
        for ip in list(self.minute_requests.keys()):
            self._cleanup_ip(ip, now)
        
        # Clean blocked IPs
        for ip in list(self.blocked_ips.keys()):
            if now - self.blocked_ips[ip] > timedelta(hours=1):
                del self.blocked_ips[ip]
        
        self.last_cleanup = now
        logger.info("🧹 Rate limiter cleanup completed")
    
    def get_stats(self, ip: str) -> Dict[str, any]:
        """
        Get rate limit stats for IP
        
        Args:
            ip: Client IP address
        
        Returns:
            Dict with current usage stats
        """
        with self.lock:
            now = datetime.now()
            self._cleanup_ip(ip, now)
            
            return {
                'ip': ip,
                'minute_requests': len(self.minute_requests.get(ip, [])),
                'minute_limit': self.max_per_minute,
                'minute_remaining': max(
                    0,
                    self.max_per_minute - len(self.minute_requests.get(ip, []))
                ),
                'hour_requests': len(self.hour_requests.get(ip, [])),
                'hour_limit': self.max_per_hour,
                'hour_remaining': max(
                    0,
                    self.max_per_hour - len(self.hour_requests.get(ip, []))
                ),
                'is_blocked': ip in self.blocked_ips
            }
    
    def block_ip(self, ip: str, reason: str = "Manual block"):
        """
        Manually block an IP
        
        Args:
            ip: IP to block
            reason: Reason for blocking
        """
        with self.lock:
            self.blocked_ips[ip] = datetime.now()
            logger.warning(f"🚨 IP manually blocked: {ip} - {reason}")
    
    def unblock_ip(self, ip: str):
        """
        Manually unblock an IP
        
        Args:
            ip: IP to unblock
        """
        with self.lock:
            if ip in self.blocked_ips:
                del self.blocked_ips[ip]
                logger.info(f"✅ IP unblocked: {ip}")


# Helper function to extract client IP
def get_client_ip(request) -> str:
    """
    Get real client IP address from request
    Handles proxies and load balancers
    
    Args:
        request: HTTP request object
    
    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header (behind proxy/load balancer)
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        # Take first IP (original client)
        ip = forwarded.split(',')[0].strip()
        return ip
    
    # Check X-Real-IP header
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct connection
    return request.client.host
