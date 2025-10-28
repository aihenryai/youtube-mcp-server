"""
Integration tests for security components.
Tests CORS, Request Signing, and Security Logger together.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.security import CORSValidator, RequestSigner, SecurityLogger
from utils.security.security_logger import SecurityEventType, SeverityLevel
import tempfile


class TestCORSValidation:
    """Test CORS Validator"""
    
    def test_exact_origin_match(self):
        """Test exact origin matching"""
        validator = CORSValidator(allowed_origins=["https://example.com"])
        
        assert validator.is_origin_allowed("https://example.com") is True
        assert validator.is_origin_allowed("https://evil.com") is False
    
    def test_wildcard_origin(self):
        """Test wildcard origin matching"""
        validator = CORSValidator(allowed_origins=["https://*.example.com"])
        
        assert validator.is_origin_allowed("https://api.example.com") is True
        assert validator.is_origin_allowed("https://app.example.com") is True
        assert validator.is_origin_allowed("https://example.com") is False
        assert validator.is_origin_allowed("https://evil.com") is False
    
    def test_method_validation(self):
        """Test HTTP method validation"""
        validator = CORSValidator(
            allowed_origins=["*"],
            allowed_methods=["GET", "POST"]
        )
        
        assert validator.is_method_allowed("GET") is True
        assert validator.is_method_allowed("POST") is True
        assert validator.is_method_allowed("DELETE") is False
        assert validator.is_method_allowed("PUT") is False
    
    def test_header_validation(self):
        """Test header validation"""
        validator = CORSValidator(
            allowed_origins=["*"],
            allowed_headers=["Content-Type", "Authorization"]
        )
        
        assert validator.is_header_allowed("Content-Type") is True
        assert validator.is_header_allowed("Authorization") is True
        assert validator.is_header_allowed("X-Custom-Header") is False
    
    def test_preflight_request(self):
        """Test preflight request handling"""
        validator = CORSValidator(
            allowed_origins=["https://example.com"],
            allowed_methods=["GET", "POST"],
            allowed_headers=["Content-Type"]
        )
        
        is_valid, headers = validator.handle_preflight(
            origin="https://example.com",
            method="POST",
            headers=["Content-Type"]
        )
        
        assert is_valid is True
        assert headers["Access-Control-Allow-Origin"] == "https://example.com"
        assert "POST" in headers["Access-Control-Allow-Methods"]


class TestRequestSigner:
    """Test Request Signer"""
    
    def test_signature_generation(self):
        """Test signature generation"""
        signer = RequestSigner(secret_key="test-secret-key")
        
        signature, timestamp, nonce = signer.sign_request(
            method="POST",
            path="/api/test",
            body='{"key":"value"}'
        )
        
        assert len(signature) == 64  # SHA256 hex = 64 chars
        assert len(timestamp) > 0
        assert len(nonce) == 32
    
    def test_signature_verification_valid(self):
        """Test valid signature verification"""
        signer = RequestSigner(secret_key="test-secret-key")
        
        # Generate signature
        signature, timestamp, nonce = signer.sign_request(
            method="POST",
            path="/api/test",
            body='{"key":"value"}'
        )
        
        # Verify it
        is_valid = signer.verify_signature(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            method="POST",
            path="/api/test",
            body='{"key":"value"}'
        )
        
        assert is_valid is True
    
    def test_signature_verification_wrong_body(self):
        """Test signature fails with wrong body"""
        signer = RequestSigner(secret_key="test-secret-key")
        
        # Generate signature
        signature, timestamp, nonce = signer.sign_request(
            method="POST",
            path="/api/test",
            body='{"key":"value"}'
        )
        
        # Try to verify with different body
        is_valid = signer.verify_signature(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            method="POST",
            path="/api/test",
            body='{"key":"different"}'  # Changed!
        )
        
        assert is_valid is False
    
    def test_nonce_replay_detection(self):
        """Test that same nonce cannot be reused"""
        signer = RequestSigner(secret_key="test-secret-key")
        
        # Generate signature
        signature, timestamp, nonce = signer.sign_request(
            method="POST",
            path="/api/test",
            body='{"key":"value"}'
        )
        
        # First verification should succeed
        is_valid1 = signer.verify_signature(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            method="POST",
            path="/api/test",
            body='{"key":"value"}'
        )
        
        # Second verification with same nonce should fail
        is_valid2 = signer.verify_signature(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            method="POST",
            path="/api/test",
            body='{"key":"value"}'
        )
        
        assert is_valid1 is True
        assert is_valid2 is False  # Replay attack detected!


class TestSecurityLogger:
    """Test Security Logger"""
    
    def test_log_event(self):
        """Test basic event logging"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            logger = SecurityLogger(log_file=log_file)
            
            logger.log_event(
                event_type=SecurityEventType.CORS_VIOLATION,
                severity=SeverityLevel.HIGH,
                message="Origin not allowed",
                client_ip="192.168.1.100",
                details={"origin": "https://evil.com"}
            )
            
            # Check that event was logged
            with open(log_file, 'r') as f:
                content = f.read()
                assert "CORS_VIOLATION" in content
                assert "192.168.1.100" in content
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_metrics_tracking(self):
        """Test metrics tracking"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            logger = SecurityLogger(log_file=log_file)
            
            # Log multiple events
            for i in range(5):
                logger.log_event(
                    event_type=SecurityEventType.PROMPT_INJECTION_DETECTED,
                    severity=SeverityLevel.HIGH,
                    message=f"Prompt injection {i}",
                    client_ip=f"192.168.1.{i}"
                )
            
            # Check metrics
            metrics = logger.get_metrics()
            assert metrics["total_events"] == 5
            assert metrics["high_severity"] == 5
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_suspicious_ip_tracking(self):
        """Test suspicious IP tracking"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            logger = SecurityLogger(log_file=log_file)
            
            # Log multiple suspicious events from same IP
            for i in range(6):  # Threshold is 5
                logger.log_event(
                    event_type=SecurityEventType.PROMPT_INJECTION_DETECTED,
                    severity=SeverityLevel.HIGH,
                    message=f"Attack {i}",
                    client_ip="192.168.1.100"
                )
            
            # Check that IP is marked suspicious
            metrics = logger.get_metrics()
            assert "192.168.1.100" in metrics["suspicious_ips"]
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)


class TestIntegration:
    """Test all components working together"""
    
    def test_complete_request_flow(self):
        """Test a complete secure request flow"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            # Initialize all components
            cors_validator = CORSValidator(
                allowed_origins=["https://example.com"]
            )
            request_signer = RequestSigner(secret_key="test-secret")
            security_logger = SecurityLogger(log_file=log_file)
            
            # Simulate a valid request
            origin = "https://example.com"
            method = "POST"
            path = "/api/test"
            body = '{"data":"test"}'
            
            # 1. Check CORS
            cors_ok = cors_validator.is_origin_allowed(origin)
            assert cors_ok is True
            
            # 2. Generate and verify signature
            signature, timestamp, nonce = request_signer.sign_request(
                method=method,
                path=path,
                body=body
            )
            
            sig_valid = request_signer.verify_signature(
                signature=signature,
                timestamp=timestamp,
                nonce=nonce,
                method=method,
                path=path,
                body=body
            )
            assert sig_valid is True
            
            # 3. Log successful access
            security_logger.log_event(
                event_type=SecurityEventType.REQUEST_VALIDATED,
                severity=SeverityLevel.INFO,
                message="Request validated successfully",
                client_ip="192.168.1.100"
            )
            
            # Check that event was logged
            metrics = security_logger.get_metrics()
            assert metrics["total_events"] == 1
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_blocked_request_flow(self):
        """Test blocking an invalid request"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = f.name
        
        try:
            # Initialize all components
            cors_validator = CORSValidator(
                allowed_origins=["https://example.com"]
            )
            security_logger = SecurityLogger(log_file=log_file)
            
            # Simulate a request from disallowed origin
            origin = "https://evil.com"
            
            # 1. Check CORS - should fail
            cors_ok = cors_validator.is_origin_allowed(origin)
            assert cors_ok is False
            
            # 2. Log the violation
            security_logger.log_cors_violation(
                origin=origin,
                client_ip="192.168.1.200"
            )
            
            # Check that violation was logged
            metrics = security_logger.get_metrics()
            assert metrics["total_events"] == 1
            assert metrics["high_severity"] == 1
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
