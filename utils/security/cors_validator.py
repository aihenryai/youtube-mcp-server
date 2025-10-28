"""
CORS (Cross-Origin Resource Sharing) Validator
Protects against unauthorized cross-origin requests
"""

from typing import List, Optional, Dict
from dataclasses import dataclass
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class CORSConfig:
    """CORS configuration settings"""
    allowed_origins: List[str]
    allowed_methods: List[str]
    allowed_headers: List[str]
    allow_credentials: bool
    max_age: int  # Preflight cache duration in seconds
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.allowed_origins:
            raise ValueError("At least one allowed origin must be specified")
        
        # Validate origin patterns
        for origin in self.allowed_origins:
            if origin != "*" and not self._is_valid_origin(origin):
                raise ValueError(f"Invalid origin pattern: {origin}")
    
    @staticmethod
    def _is_valid_origin(origin: str) -> bool:
        """Validate origin format"""
        # Must start with http:// or https://
        if not origin.startswith(("http://", "https://")):
            return False
        
        # Check for valid domain format
        pattern = r'^https?://[\w\-]+(\.[\w\-]+)*(\:\d+)?$'
        return bool(re.match(pattern, origin))


class CORSValidator:
    """
    Validates CORS requests and provides appropriate headers
    
    Security Features:
    - Whitelist-based origin validation
    - Wildcard pattern support (e.g., *.example.com)
    - Method and header validation
    - Preflight request handling
    - Credential-aware CORS
    """
    
    def __init__(self, config: CORSConfig):
        """
        Initialize CORS validator
        
        Args:
            config: CORS configuration
        """
        self.config = config
        self._compiled_patterns = self._compile_origin_patterns()
        
        logger.info(
            f"CORS Validator initialized with {len(config.allowed_origins)} "
            f"allowed origins"
        )
    
    def _compile_origin_patterns(self) -> List[re.Pattern]:
        """Compile origin patterns into regex for efficient matching"""
        patterns = []
        
        for origin in self.config.allowed_origins:
            if origin == "*":
                # Match everything (not recommended for production)
                patterns.append(re.compile(r".*"))
            elif "*" in origin:
                # Convert wildcard pattern to regex
                # e.g., "*.example.com" -> r"^https?://[^.]+\.example\.com$"
                pattern = origin.replace(".", r"\.").replace("*", r"[^.]+")
                patterns.append(re.compile(f"^{pattern}$"))
            else:
                # Exact match
                patterns.append(re.compile(f"^{re.escape(origin)}$"))
        
        return patterns
    
    def is_origin_allowed(self, origin: str) -> bool:
        """
        Check if origin is allowed
        
        Args:
            origin: Request origin header value
            
        Returns:
            True if origin is allowed, False otherwise
        """
        if not origin:
            return False
        
        # Check against compiled patterns
        for pattern in self._compiled_patterns:
            if pattern.match(origin):
                logger.debug(f"Origin allowed: {origin}")
                return True
        
        logger.warning(f"Origin blocked: {origin}")
        return False
    
    def validate_request(
        self,
        origin: Optional[str],
        method: str,
        headers: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Validate a CORS request
        
        Args:
            origin: Request origin
            method: HTTP method
            headers: Requested headers (for preflight)
            
        Returns:
            Dictionary with validation results:
            - origin_valid: Origin is allowed
            - method_valid: Method is allowed
            - headers_valid: Headers are allowed
            - is_valid: Overall validation result
        """
        result = {
            "origin_valid": False,
            "method_valid": False,
            "headers_valid": True,  # Default to True if not checked
            "is_valid": False
        }
        
        # Validate origin
        if origin:
            result["origin_valid"] = self.is_origin_allowed(origin)
        
        # Validate method
        if method.upper() in [m.upper() for m in self.config.allowed_methods]:
            result["method_valid"] = True
        else:
            logger.warning(f"Method not allowed: {method}")
        
        # Validate headers (for preflight requests)
        if headers:
            result["headers_valid"] = all(
                h.lower() in [ah.lower() for ah in self.config.allowed_headers]
                for h in headers
            )
            if not result["headers_valid"]:
                logger.warning(f"Some headers not allowed: {headers}")
        
        # Overall validation
        result["is_valid"] = (
            result["origin_valid"] and
            result["method_valid"] and
            result["headers_valid"]
        )
        
        return result
    
    def get_cors_headers(
        self,
        origin: Optional[str],
        is_preflight: bool = False
    ) -> Dict[str, str]:
        """
        Get appropriate CORS headers for response
        
        Args:
            origin: Request origin
            is_preflight: Whether this is a preflight request
            
        Returns:
            Dictionary of CORS headers
        """
        if not origin or not self.is_origin_allowed(origin):
            return {}
        
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": ", ".join(self.config.allowed_methods),
            "Access-Control-Allow-Headers": ", ".join(self.config.allowed_headers),
        }
        
        if self.config.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
        
        if is_preflight:
            headers["Access-Control-Max-Age"] = str(self.config.max_age)
        
        return headers
    
    def handle_preflight(
        self,
        origin: Optional[str],
        method: str,
        headers: Optional[List[str]] = None
    ) -> tuple[bool, Dict[str, str]]:
        """
        Handle CORS preflight request
        
        Args:
            origin: Request origin
            method: Requested method
            headers: Requested headers
            
        Returns:
            Tuple of (is_valid, cors_headers)
        """
        validation = self.validate_request(origin, method, headers)
        
        if validation["is_valid"]:
            return True, self.get_cors_headers(origin, is_preflight=True)
        else:
            logger.warning(
                f"Preflight validation failed: origin={origin}, "
                f"method={method}, validation={validation}"
            )
            return False, {}
    
    def get_stats(self) -> Dict[str, any]:
        """Get CORS validator statistics"""
        return {
            "allowed_origins_count": len(self.config.allowed_origins),
            "allowed_methods": self.config.allowed_methods,
            "allow_credentials": self.config.allow_credentials,
            "patterns_compiled": len(self._compiled_patterns)
        }


def create_default_cors_config() -> CORSConfig:
    """Create a secure default CORS configuration"""
    return CORSConfig(
        allowed_origins=[
            "http://localhost:3000",  # Local development
            "http://localhost:8080",
            "https://*.claude.ai",    # Claude.ai domains
        ],
        allowed_methods=["GET", "POST", "OPTIONS"],
        allowed_headers=[
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Client-Version"
        ],
        allow_credentials=True,
        max_age=86400  # 24 hours
    )


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create validator with default config
    config = create_default_cors_config()
    validator = CORSValidator(config)
    
    # Test cases
    test_origins = [
        "http://localhost:3000",      # Should pass
        "https://claude.ai",           # Should pass (*.claude.ai)
        "https://app.claude.ai",       # Should pass (*.claude.ai)
        "https://evil.com",            # Should fail
        None,                          # Should fail
    ]
    
    print("\n=== CORS Validation Tests ===\n")
    for origin in test_origins:
        is_allowed = validator.is_origin_allowed(origin) if origin else False
        status = "✅ ALLOWED" if is_allowed else "❌ BLOCKED"
        print(f"{status}: {origin}")
    
    # Test preflight request
    print("\n=== Preflight Request Test ===\n")
    is_valid, headers = validator.handle_preflight(
        origin="http://localhost:3000",
        method="POST",
        headers=["Content-Type", "Authorization"]
    )
    
    print(f"Preflight valid: {is_valid}")
    print(f"CORS headers: {headers}")
    
    # Show stats
    print("\n=== Validator Stats ===\n")
    stats = validator.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
