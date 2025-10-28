"""
Request Signature Validation (HMAC-SHA256)
Ensures request integrity and authenticity
"""

import hmac
import hashlib
import time
import secrets
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class SignatureConfig:
    """Request signature configuration"""
    secret_key: str
    timestamp_tolerance: int = 300  # 5 minutes
    require_nonce: bool = True
    algorithm: str = "sha256"
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.secret_key or len(self.secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters")
        
        if self.timestamp_tolerance < 0:
            raise ValueError("Timestamp tolerance must be non-negative")
        
        if self.algorithm not in ["sha256", "sha512"]:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")


class RequestSigner:
    """
    Signs and validates request signatures using HMAC
    
    Security Features:
    - HMAC-SHA256/SHA512 signatures
    - Timestamp validation (replay attack prevention)
    - Nonce validation (for critical operations)
    - Secret key rotation support
    - Request body integrity verification
    """
    
    def __init__(self, config: SignatureConfig):
        """
        Initialize request signer
        
        Args:
            config: Signature configuration
        """
        self.config = config
        self._used_nonces = set()  # Simple nonce tracking (use Redis in production)
        self._max_nonces = 10000   # Limit nonce storage
        
        # Select hash algorithm
        self._hash_func = (
            hashlib.sha512 if config.algorithm == "sha512" else hashlib.sha256
        )
        
        logger.info(
            f"Request Signer initialized with algorithm={config.algorithm}, "
            f"timestamp_tolerance={config.timestamp_tolerance}s"
        )
    
    def sign_request(
        self,
        method: str,
        path: str,
        body: Optional[str] = None,
        timestamp: Optional[int] = None,
        nonce: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Sign a request
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            body: Request body (for POST/PUT)
            timestamp: Unix timestamp (defaults to current time)
            nonce: Unique request identifier (auto-generated if required)
            
        Returns:
            Dictionary with signature components:
            - signature: HMAC signature
            - timestamp: Unix timestamp
            - nonce: Request nonce (if enabled)
        """
        # Generate timestamp if not provided
        if timestamp is None:
            timestamp = int(time.time())
        
        # Generate nonce if required and not provided
        if self.config.require_nonce and nonce is None:
            nonce = secrets.token_hex(16)
        
        # Create signature string
        signature_string = self._create_signature_string(
            method=method,
            path=path,
            body=body,
            timestamp=timestamp,
            nonce=nonce
        )
        
        # Compute HMAC signature
        signature = hmac.new(
            self.config.secret_key.encode(),
            signature_string.encode(),
            self._hash_func
        ).hexdigest()
        
        result = {
            "signature": signature,
            "timestamp": str(timestamp)
        }
        
        if nonce:
            result["nonce"] = nonce
        
        logger.debug(f"Request signed: method={method}, path={path}")
        
        return result
    
    def validate_signature(
        self,
        method: str,
        path: str,
        signature: str,
        timestamp: str,
        body: Optional[str] = None,
        nonce: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate request signature
        
        Args:
            method: HTTP method
            path: Request path
            signature: Provided signature
            timestamp: Request timestamp
            body: Request body (for POST/PUT)
            nonce: Request nonce
            
        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, reason) if invalid
        """
        try:
            # Parse timestamp
            try:
                ts = int(timestamp)
            except ValueError:
                return False, "Invalid timestamp format"
            
            # Check timestamp freshness (replay attack prevention)
            current_time = int(time.time())
            time_diff = abs(current_time - ts)
            
            if time_diff > self.config.timestamp_tolerance:
                logger.warning(
                    f"Request timestamp expired: diff={time_diff}s, "
                    f"tolerance={self.config.timestamp_tolerance}s"
                )
                return False, f"Timestamp expired (diff: {time_diff}s)"
            
            # Validate nonce if required
            if self.config.require_nonce:
                if not nonce:
                    return False, "Nonce required but not provided"
                
                if nonce in self._used_nonces:
                    logger.warning(f"Nonce reuse detected: {nonce}")
                    return False, "Nonce already used (replay attack?)"
                
                # Track nonce (cleanup if too many)
                if len(self._used_nonces) >= self._max_nonces:
                    self._used_nonces.clear()
                    logger.info("Nonce cache cleared")
                
                self._used_nonces.add(nonce)
            
            # Recreate signature string
            signature_string = self._create_signature_string(
                method=method,
                path=path,
                body=body,
                timestamp=ts,
                nonce=nonce
            )
            
            # Compute expected signature
            expected_signature = hmac.new(
                self.config.secret_key.encode(),
                signature_string.encode(),
                self._hash_func
            ).hexdigest()
            
            # Constant-time comparison to prevent timing attacks
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning(
                    f"Signature mismatch: method={method}, path={path}"
                )
                return False, "Invalid signature"
            
            logger.debug(f"Signature valid: method={method}, path={path}")
            return True, None
            
        except Exception as e:
            logger.error(f"Signature validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    def _create_signature_string(
        self,
        method: str,
        path: str,
        body: Optional[str],
        timestamp: int,
        nonce: Optional[str]
    ) -> str:
        """
        Create canonical signature string
        
        Format: METHOD\nPATH\nTIMESTAMP\nNONCE\nBODY_HASH
        """
        # Normalize components
        method = method.upper()
        
        # Hash body if present
        body_hash = ""
        if body:
            body_hash = hashlib.sha256(body.encode()).hexdigest()
        
        # Build signature string
        parts = [
            method,
            path,
            str(timestamp),
            nonce or "",
            body_hash
        ]
        
        return "\n".join(parts)
    
    def rotate_secret(self, new_secret: str) -> None:
        """
        Rotate the secret key
        
        Args:
            new_secret: New secret key (must be at least 32 chars)
            
        Note: In production, implement graceful rotation:
        1. Add new key while keeping old one
        2. Accept signatures from both keys
        3. Remove old key after transition period
        """
        if len(new_secret) < 32:
            raise ValueError("New secret must be at least 32 characters")
        
        old_secret = self.config.secret_key
        self.config.secret_key = new_secret
        
        # Clear nonce cache on rotation for security
        self._used_nonces.clear()
        
        logger.info(f"Secret key rotated (old: {old_secret[:4]}..., new: {new_secret[:4]}...)")
    
    def get_stats(self) -> Dict[str, any]:
        """Get signer statistics"""
        return {
            "algorithm": self.config.algorithm,
            "timestamp_tolerance": self.config.timestamp_tolerance,
            "require_nonce": self.config.require_nonce,
            "nonces_tracked": len(self._used_nonces),
            "max_nonces": self._max_nonces
        }


def generate_secure_secret(length: int = 64) -> str:
    """
    Generate a cryptographically secure secret key
    
    Args:
        length: Key length in bytes (default: 64)
        
    Returns:
        Hex-encoded secret key
    """
    return secrets.token_hex(length)


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Generate a secure secret
    secret = generate_secure_secret()
    print(f"Generated secret: {secret}\n")
    
    # Create signer
    config = SignatureConfig(
        secret_key=secret,
        timestamp_tolerance=300,  # 5 minutes
        require_nonce=True,
        algorithm="sha256"
    )
    signer = RequestSigner(config)
    
    # Example 1: Sign a GET request
    print("=== Example 1: GET Request ===")
    sig_data = signer.sign_request(
        method="GET",
        path="/api/videos/123"
    )
    print(f"Signature: {sig_data['signature'][:32]}...")
    print(f"Timestamp: {sig_data['timestamp']}")
    print(f"Nonce: {sig_data['nonce']}\n")
    
    # Validate the signature
    is_valid, error = signer.validate_signature(
        method="GET",
        path="/api/videos/123",
        signature=sig_data['signature'],
        timestamp=sig_data['timestamp'],
        nonce=sig_data['nonce']
    )
    print(f"Validation: {'✅ VALID' if is_valid else '❌ INVALID'}")
    if error:
        print(f"Error: {error}")
    
    # Example 2: Sign a POST request with body
    print("\n=== Example 2: POST Request with Body ===")
    body = json.dumps({"title": "Test Video", "description": "Test"})
    sig_data = signer.sign_request(
        method="POST",
        path="/api/videos",
        body=body
    )
    print(f"Body: {body}")
    print(f"Signature: {sig_data['signature'][:32]}...")
    
    # Validate POST signature
    is_valid, error = signer.validate_signature(
        method="POST",
        path="/api/videos",
        signature=sig_data['signature'],
        timestamp=sig_data['timestamp'],
        body=body,
        nonce=sig_data['nonce']
    )
    print(f"Validation: {'✅ VALID' if is_valid else '❌ INVALID'}\n")
    
    # Example 3: Test replay attack prevention
    print("=== Example 3: Replay Attack Prevention ===")
    
    # Try to reuse the same nonce
    is_valid, error = signer.validate_signature(
        method="GET",
        path="/api/videos/123",
        signature=sig_data['signature'],
        timestamp=sig_data['timestamp'],
        nonce=sig_data['nonce']
    )
    print(f"Reused nonce: {'✅ VALID' if is_valid else '❌ INVALID (Expected!)'}")
    if error:
        print(f"Error: {error}\n")
    
    # Example 4: Test expired timestamp
    print("=== Example 4: Expired Timestamp ===")
    old_timestamp = str(int(time.time()) - 600)  # 10 minutes ago
    sig_data_old = signer.sign_request(
        method="GET",
        path="/api/videos/456",
        timestamp=int(old_timestamp)
    )
    
    is_valid, error = signer.validate_signature(
        method="GET",
        path="/api/videos/456",
        signature=sig_data_old['signature'],
        timestamp=old_timestamp,
        nonce=sig_data_old['nonce']
    )
    print(f"Old timestamp: {'✅ VALID' if is_valid else '❌ INVALID (Expected!)'}")
    if error:
        print(f"Error: {error}\n")
    
    # Show stats
    print("=== Signer Stats ===")
    stats = signer.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
