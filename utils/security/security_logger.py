"""
Security Event Logging System
Comprehensive security monitoring and audit trail
"""

import logging
import json
import time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import threading
from collections import defaultdict, deque


class SecurityEventType(Enum):
    """Security event types"""
    # Authentication & Authorization
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    RATE_LIMIT_WARNING = "rate_limit_warning"
    
    # Input Validation
    PROMPT_INJECTION_DETECTED = "prompt_injection_detected"
    INVALID_INPUT = "invalid_input"
    MALFORMED_REQUEST = "malformed_request"
    
    # CORS & Origin
    CORS_VIOLATION = "cors_violation"
    ORIGIN_BLOCKED = "origin_blocked"
    
    # Request Integrity
    SIGNATURE_INVALID = "signature_invalid"
    SIGNATURE_EXPIRED = "signature_expired"
    REPLAY_ATTACK = "replay_attack"
    
    # Data Access
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    UNAUTHORIZED_DATA_ACCESS = "unauthorized_data_access"
    
    # System
    SECURITY_CONFIG_CHANGE = "security_config_change"
    SECRET_ROTATION = "secret_rotation"
    CACHE_ENCRYPTION_ERROR = "cache_encryption_error"
    
    # Suspicious Activity
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    ANOMALY_DETECTED = "anomaly_detected"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"


class SeverityLevel(Enum):
    """Event severity levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security event data structure"""
    event_type: SecurityEventType
    severity: SeverityLevel
    message: str
    timestamp: float = field(default_factory=time.time)
    
    # Context information
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    
    # Event-specific data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Tracking
    event_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        data["timestamp_iso"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class SecurityMetrics:
    """Real-time security metrics"""
    total_events: int = 0
    events_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_severity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Recent activity (last N events)
    recent_events: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Suspicious activity tracking
    suspicious_ips: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    blocked_attempts: int = 0
    
    # Performance
    start_time: float = field(default_factory=time.time)
    
    def uptime(self) -> float:
        """Get system uptime in seconds"""
        return time.time() - self.start_time
    
    def events_per_minute(self) -> float:
        """Calculate events per minute"""
        uptime_minutes = self.uptime() / 60
        return self.total_events / uptime_minutes if uptime_minutes > 0 else 0


class SecurityLogger:
    """
    Centralized security event logging and monitoring
    
    Features:
    - Structured security event logging
    - Real-time metrics and statistics
    - Suspicious activity detection
    - Thread-safe operations
    - JSON export for SIEM integration
    """
    
    def __init__(
        self,
        log_level: int = logging.INFO,
        enable_console: bool = True,
        enable_file: bool = True,
        log_file: str = "security.log"
    ):
        """
        Initialize security logger
        
        Args:
            log_level: Logging level (default: INFO)
            enable_console: Enable console output
            enable_file: Enable file logging
            log_file: Log file path
        """
        self.logger = logging.getLogger("SecurityLogger")
        self.logger.setLevel(log_level)
        self.logger.propagate = False  # Prevent duplicate logs
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_formatter = logging.Formatter(
                '%(asctime)s - [SECURITY] - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # File handler
        if enable_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(log_level)
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.error(f"Failed to setup file handler: {e}")
        
        # Metrics
        self.metrics = SecurityMetrics()
        self._lock = threading.Lock()
        
        self.logger.info("Security Logger initialized")
    
    def log_event(self, event: SecurityEvent) -> None:
        """
        Log a security event
        
        Args:
            event: SecurityEvent instance
        """
        with self._lock:
            # Update metrics
            self.metrics.total_events += 1
            self.metrics.events_by_type[event.event_type.value] += 1
            self.metrics.events_by_severity[event.severity.value] += 1
            self.metrics.recent_events.append(event)
            
            # Track suspicious IPs
            if event.ip_address and event.severity in [SeverityLevel.WARNING, SeverityLevel.ERROR, SeverityLevel.CRITICAL]:
                self.metrics.suspicious_ips[event.ip_address] += 1
            
            # Track blocked attempts
            if event.event_type in [
                SecurityEventType.AUTH_FAILURE,
                SecurityEventType.RATE_LIMIT_EXCEEDED,
                SecurityEventType.CORS_VIOLATION,
                SecurityEventType.SIGNATURE_INVALID
            ]:
                self.metrics.blocked_attempts += 1
        
        # Log to standard logger
        log_message = self._format_log_message(event)
        
        if event.severity == SeverityLevel.DEBUG:
            self.logger.debug(log_message)
        elif event.severity == SeverityLevel.INFO:
            self.logger.info(log_message)
        elif event.severity == SeverityLevel.WARNING:
            self.logger.warning(log_message)
        elif event.severity == SeverityLevel.ERROR:
            self.logger.error(log_message)
        elif event.severity == SeverityLevel.CRITICAL:
            self.logger.critical(log_message)
    
    def _format_log_message(self, event: SecurityEvent) -> str:
        """Format security event for logging"""
        parts = [
            f"[{event.event_type.value}]",
            event.message
        ]
        
        if event.ip_address:
            parts.append(f"IP={event.ip_address}")
        
        if event.user_id:
            parts.append(f"User={event.user_id}")
        
        if event.request_id:
            parts.append(f"ReqID={event.request_id}")
        
        if event.metadata:
            metadata_str = ", ".join(f"{k}={v}" for k, v in event.metadata.items())
            parts.append(f"[{metadata_str}]")
        
        return " | ".join(parts)
    
    # Convenience methods for common events
    
    def log_auth_failure(
        self,
        message: str,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        **metadata
    ) -> None:
        """Log authentication failure"""
        event = SecurityEvent(
            event_type=SecurityEventType.AUTH_FAILURE,
            severity=SeverityLevel.WARNING,
            message=message,
            ip_address=ip_address,
            user_id=user_id,
            metadata=metadata
        )
        self.log_event(event)
    
    def log_rate_limit(
        self,
        message: str,
        ip_address: Optional[str] = None,
        **metadata
    ) -> None:
        """Log rate limit exceeded"""
        event = SecurityEvent(
            event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
            severity=SeverityLevel.WARNING,
            message=message,
            ip_address=ip_address,
            metadata=metadata
        )
        self.log_event(event)
    
    def log_prompt_injection(
        self,
        message: str,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        **metadata
    ) -> None:
        """Log prompt injection attempt"""
        event = SecurityEvent(
            event_type=SecurityEventType.PROMPT_INJECTION_DETECTED,
            severity=SeverityLevel.ERROR,
            message=message,
            ip_address=ip_address,
            request_id=request_id,
            metadata=metadata
        )
        self.log_event(event)
    
    def log_cors_violation(
        self,
        message: str,
        ip_address: Optional[str] = None,
        **metadata
    ) -> None:
        """Log CORS violation"""
        event = SecurityEvent(
            event_type=SecurityEventType.CORS_VIOLATION,
            severity=SeverityLevel.WARNING,
            message=message,
            ip_address=ip_address,
            metadata=metadata
        )
        self.log_event(event)
    
    def log_signature_invalid(
        self,
        message: str,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        **metadata
    ) -> None:
        """Log invalid signature"""
        event = SecurityEvent(
            event_type=SecurityEventType.SIGNATURE_INVALID,
            severity=SeverityLevel.ERROR,
            message=message,
            ip_address=ip_address,
            request_id=request_id,
            metadata=metadata
        )
        self.log_event(event)
    
    def log_suspicious_activity(
        self,
        message: str,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        **metadata
    ) -> None:
        """Log suspicious activity"""
        event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_PATTERN,
            severity=SeverityLevel.CRITICAL,
            message=message,
            ip_address=ip_address,
            user_id=user_id,
            metadata=metadata
        )
        self.log_event(event)
    
    # Metrics and reporting
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current security metrics"""
        with self._lock:
            return {
                "total_events": self.metrics.total_events,
                "events_by_type": dict(self.metrics.events_by_type),
                "events_by_severity": dict(self.metrics.events_by_severity),
                "recent_events_count": len(self.metrics.recent_events),
                "suspicious_ips": dict(self.metrics.suspicious_ips),
                "blocked_attempts": self.metrics.blocked_attempts,
                "uptime_seconds": self.metrics.uptime(),
                "events_per_minute": round(self.metrics.events_per_minute(), 2)
            }
    
    def get_recent_events(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent security events"""
        with self._lock:
            recent = list(self.metrics.recent_events)[-count:]
            return [event.to_dict() for event in recent]
    
    def get_suspicious_ips(self, threshold: int = 3) -> List[Dict[str, Any]]:
        """Get IPs with suspicious activity above threshold"""
        with self._lock:
            suspicious = [
                {"ip": ip, "incidents": count}
                for ip, count in self.metrics.suspicious_ips.items()
                if count >= threshold
            ]
            return sorted(suspicious, key=lambda x: x["incidents"], reverse=True)
    
    def export_logs(self, format: str = "json") -> str:
        """
        Export security logs
        
        Args:
            format: Export format (json, csv - currently only json)
            
        Returns:
            Exported data as string
        """
        if format == "json":
            data = {
                "metrics": self.get_metrics(),
                "recent_events": self.get_recent_events(100),
                "suspicious_ips": self.get_suspicious_ips(1)
            }
            return json.dumps(data, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def reset_metrics(self) -> None:
        """Reset all metrics (use with caution)"""
        with self._lock:
            self.metrics = SecurityMetrics()
            self.logger.info("Security metrics reset")


# Global security logger instance
_global_security_logger: Optional[SecurityLogger] = None


def get_security_logger() -> SecurityLogger:
    """Get or create global security logger"""
    global _global_security_logger
    if _global_security_logger is None:
        _global_security_logger = SecurityLogger()
    return _global_security_logger


# Example usage
if __name__ == "__main__":
    # Create security logger
    sec_logger = SecurityLogger(
        log_level=logging.DEBUG,
        enable_console=True,
        enable_file=True,
        log_file="security_test.log"
    )
    
    print("=== Security Logger Test ===\n")
    
    # Log various security events
    sec_logger.log_auth_failure(
        "Failed login attempt",
        ip_address="192.168.1.100",
        user_id="user123",
        reason="invalid_password"
    )
    
    sec_logger.log_rate_limit(
        "Rate limit exceeded",
        ip_address="192.168.1.100",
        limit_type="per_minute",
        limit_value=10
    )
    
    sec_logger.log_prompt_injection(
        "Prompt injection detected",
        ip_address="192.168.1.200",
        request_id="req-456",
        pattern="ignore_previous",
        risk_score=85
    )
    
    sec_logger.log_cors_violation(
        "Origin not allowed",
        ip_address="192.168.1.300",
        origin="https://evil.com"
    )
    
    sec_logger.log_suspicious_activity(
        "Multiple failed attempts from same IP",
        ip_address="192.168.1.100",
        attempt_count=5
    )
    
    # Show metrics
    print("\n=== Security Metrics ===")
    metrics = sec_logger.get_metrics()
    print(json.dumps(metrics, indent=2))
    
    # Show suspicious IPs
    print("\n=== Suspicious IPs ===")
    suspicious = sec_logger.get_suspicious_ips(threshold=2)
    for item in suspicious:
        print(f"IP: {item['ip']}, Incidents: {item['incidents']}")
    
    # Export logs
    print("\n=== Export Logs ===")
    exported = sec_logger.export_logs(format="json")
    print(f"Exported {len(exported)} characters")
