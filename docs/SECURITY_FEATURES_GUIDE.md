# Advanced Security Features Guide (v2.1)

This guide covers the new security features added in YouTube MCP Server v2.1:
- CORS Validation
- Request Signature Validation (HMAC)
- Security Event Logging

---

## 🔐 1. CORS (Cross-Origin Resource Sharing) Validation

### What it does
Prevents unauthorized websites from accessing your MCP server through browsers.

### Configuration

```bash
# Enable/disable CORS validation
CORS_ENABLED=true

# Allowed origins (comma-separated)
ALLOWED_ORIGINS=https://app1.example.com,https://app2.example.com
```

### Python API Usage

```python
from utils.security import CORSValidator, CORSConfig

# Create configuration
config = CORSConfig(
    allowed_origins=[
        "https://myapp.com",
        "https://*.example.com",  # Wildcard support
    ],
    allowed_methods=["GET", "POST", "OPTIONS"],
    allowed_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
    max_age=86400  # 24 hours
)

# Initialize validator
validator = CORSValidator(config)

# Validate origin
is_allowed = validator.is_origin_allowed("https://myapp.com")

# Handle preflight request
is_valid, cors_headers = validator.handle_preflight(
    origin="https://myapp.com",
    method="POST",
    headers=["Content-Type"]
)

# Get CORS headers for response
headers = validator.get_cors_headers(origin="https://myapp.com")
```

### Security Best Practices

❌ **DON'T:**
```bash
ALLOWED_ORIGINS=*  # Never use wildcard in production!
```

✅ **DO:**
```bash
# Specific domains only
ALLOWED_ORIGINS=https://myapp.com,https://app.company.com

# Or use wildcards carefully
ALLOWED_ORIGINS=https://*.mycompany.com
```

---

## 🔏 2. Request Signature Validation (HMAC-SHA256)

### What it does
Ensures request integrity and prevents:
- Replay attacks (via timestamp + nonce)
- Request tampering (via HMAC signature)
- Man-in-the-middle modifications

### When to use
- High-security deployments
- Financial or sensitive operations
- B2B API integrations
- Preventing automated abuse

### Configuration

```bash
# Enable request signing
REQUEST_SIGNING_ENABLED=true

# Generate a secure secret (64 bytes recommended)
# Run: python -c "from utils.security.request_signer import generate_secure_secret; print(generate_secure_secret())"
REQUEST_SIGNING_SECRET=your_64_byte_hex_secret_here
```

### Server-Side Setup

```python
from utils.security import RequestSigner, SignatureConfig

# Create configuration
config = SignatureConfig(
    secret_key="your_secure_secret_key_min_32_chars",
    timestamp_tolerance=300,  # 5 minutes
    require_nonce=True,       # Prevent replay attacks
    algorithm="sha256"        # or "sha512"
)

# Initialize signer
signer = RequestSigner(config)

# Validate incoming request
is_valid, error = signer.validate_signature(
    method="POST",
    path="/api/videos",
    signature=request_headers["X-Signature"],
    timestamp=request_headers["X-Timestamp"],
    body=request_body,
    nonce=request_headers["X-Nonce"]
)

if not is_valid:
    return {"error": error}, 403
```

### Client-Side Implementation

#### Python Client

```python
import hmac
import hashlib
import time
import secrets
import requests

def sign_request(method, path, body=None, secret_key="your_secret"):
    """Sign a request with HMAC-SHA256"""
    
    # Generate timestamp and nonce
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    
    # Create signature string
    body_hash = ""
    if body:
        body_hash = hashlib.sha256(body.encode()).hexdigest()
    
    signature_string = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    
    # Compute HMAC signature
    signature = hmac.new(
        secret_key.encode(),
        signature_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return {
        "X-Signature": signature,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce
    }

# Example usage
headers = sign_request(
    method="POST",
    path="/api/videos/search",
    body='{"query": "python tutorial"}',
    secret_key="shared_secret_key"
)

response = requests.post(
    "https://your-server.com/api/videos/search",
    json={"query": "python tutorial"},
    headers=headers
)
```

#### JavaScript/TypeScript Client

```javascript
import crypto from 'crypto';

async function signRequest(method, path, body = null, secretKey = 'your_secret') {
  // Generate timestamp and nonce
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const nonce = crypto.randomBytes(16).toString('hex');
  
  // Create body hash
  let bodyHash = '';
  if (body) {
    bodyHash = crypto
      .createHash('sha256')
      .update(JSON.stringify(body))
      .digest('hex');
  }
  
  // Create signature string
  const signatureString = `${method}\n${path}\n${timestamp}\n${nonce}\n${bodyHash}`;
  
  // Compute HMAC signature
  const signature = crypto
    .createHmac('sha256', secretKey)
    .update(signatureString)
    .digest('hex');
  
  return {
    'X-Signature': signature,
    'X-Timestamp': timestamp,
    'X-Nonce': nonce
  };
}

// Example usage
const headers = await signRequest(
  'POST',
  '/api/videos/search',
  { query: 'python tutorial' },
  'shared_secret_key'
);

const response = await fetch('https://your-server.com/api/videos/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    ...headers
  },
  body: JSON.stringify({ query: 'python tutorial' })
});
```

### Secret Key Management

#### Generate Secure Secret

```bash
# Generate 64-byte hex secret (recommended)
python -c "from utils.security.request_signer import generate_secure_secret; print(generate_secure_secret())"

# Or using OpenSSL
openssl rand -hex 64
```

#### Rotate Secret Key

```python
from utils.security import RequestSigner

# Rotate to new secret
signer.rotate_secret("new_secure_secret_min_32_chars")

# In production: Implement graceful rotation
# 1. Add new key while keeping old one
# 2. Accept signatures from both keys for transition period
# 3. Remove old key after all clients updated
```

---

## 📊 3. Security Event Logging

### What it does
Centralized security monitoring and audit trail:
- Authentication events
- Rate limiting violations
- Prompt injection attempts
- CORS violations
- Suspicious activity detection

### Configuration

```bash
SECURITY_LOGGING_ENABLED=true
SECURITY_LOG_FILE=security.log
SECURITY_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Usage

```python
from utils.security import get_security_logger

# Get global security logger
sec_logger = get_security_logger()

# Log authentication failure
sec_logger.log_auth_failure(
    "Invalid API key",
    ip_address="192.168.1.100",
    user_id="user123"
)

# Log rate limit exceeded
sec_logger.log_rate_limit(
    "Rate limit exceeded",
    ip_address="192.168.1.100",
    limit_type="per_minute"
)

# Log prompt injection
sec_logger.log_prompt_injection(
    "Detected injection pattern",
    ip_address="192.168.1.200",
    request_id="req-789",
    pattern="ignore_previous",
    risk_score=85
)

# Log CORS violation
sec_logger.log_cors_violation(
    "Origin not allowed",
    ip_address="192.168.1.300",
    origin="https://evil.com"
)

# Log suspicious activity
sec_logger.log_suspicious_activity(
    "Multiple failed attempts",
    ip_address="192.168.1.100",
    attempt_count=5
)
```

### Retrieve Metrics

```python
# Get current metrics
metrics = sec_logger.get_metrics()
print(f"Total events: {metrics['total_events']}")
print(f"Blocked attempts: {metrics['blocked_attempts']}")
print(f"Events per minute: {metrics['events_per_minute']}")

# Get recent events
recent = sec_logger.get_recent_events(count=10)
for event in recent:
    print(f"{event['timestamp_iso']}: {event['message']}")

# Get suspicious IPs
suspicious = sec_logger.get_suspicious_ips(threshold=3)
for item in suspicious:
    print(f"IP: {item['ip']}, Incidents: {item['incidents']}")

# Export logs (for SIEM integration)
json_logs = sec_logger.export_logs(format="json")
```

### Log Format

```
2025-10-27 12:34:56 - [SECURITY] - WARNING - [rate_limit_exceeded] Rate limit exceeded | IP=192.168.1.100 | [limit_type=per_minute]
2025-10-27 12:35:01 - [SECURITY] - ERROR - [prompt_injection_detected] Detected injection pattern | IP=192.168.1.200 | ReqID=req-789 | [pattern=ignore_previous, risk_score=85]
```

---

## 🚀 Complete Integration Example

### Server Setup (server.py)

```python
from utils.security import (
    CORSValidator, CORSConfig,
    RequestSigner, SignatureConfig,
    get_security_logger
)
from config import config

# Initialize security components
cors_validator = None
request_signer = None
sec_logger = get_security_logger()

if config.security.cors_enabled:
    cors_config = CORSConfig(
        allowed_origins=config.security.allowed_origins,
        allowed_methods=config.security.cors_allowed_methods,
        allowed_headers=config.security.cors_allowed_headers,
        allow_credentials=config.security.cors_allow_credentials,
        max_age=config.security.cors_max_age
    )
    cors_validator = CORSValidator(cors_config)
    sec_logger.logger.info("CORS validation enabled")

if config.security.request_signing_enabled:
    if not config.security.request_signing_secret:
        raise ValueError("REQUEST_SIGNING_SECRET must be set when request signing is enabled")
    
    sig_config = SignatureConfig(
        secret_key=config.security.request_signing_secret,
        timestamp_tolerance=config.security.request_signing_timestamp_tolerance,
        require_nonce=config.security.request_signing_require_nonce,
        algorithm=config.security.request_signing_algorithm
    )
    request_signer = RequestSigner(sig_config)
    sec_logger.logger.info("Request signature validation enabled")

# Request handler with security checks
def handle_request(request):
    client_ip = get_client_ip(request)
    
    # 1. CORS Validation
    if cors_validator:
        origin = request.headers.get("Origin")
        validation = cors_validator.validate_request(
            origin=origin,
            method=request.method,
            headers=request.headers.get("Access-Control-Request-Headers", "").split(",")
        )
        
        if not validation["is_valid"]:
            sec_logger.log_cors_violation(
                f"CORS validation failed: {validation}",
                ip_address=client_ip,
                origin=origin
            )
            return {"error": "CORS validation failed"}, 403
    
    # 2. Request Signature Validation
    if request_signer:
        signature = request.headers.get("X-Signature")
        timestamp = request.headers.get("X-Timestamp")
        nonce = request.headers.get("X-Nonce")
        
        if not all([signature, timestamp, nonce]):
            sec_logger.log_signature_invalid(
                "Missing signature headers",
                ip_address=client_ip
            )
            return {"error": "Signature required"}, 403
        
        is_valid, error = request_signer.validate_signature(
            method=request.method,
            path=request.path,
            signature=signature,
            timestamp=timestamp,
            body=request.get_data(as_text=True),
            nonce=nonce
        )
        
        if not is_valid:
            sec_logger.log_signature_invalid(
                f"Invalid signature: {error}",
                ip_address=client_ip,
                reason=error
            )
            return {"error": f"Invalid signature: {error}"}, 403
    
    # Process request...
    return process_tool_call(request)
```

---

## 🛡️ Security Checklist

### Production Deployment

- [ ] **CORS**: Configure specific allowed origins (no wildcards)
- [ ] **Request Signing**: Enable for sensitive operations
- [ ] **Security Logging**: Enable with INFO or WARNING level
- [ ] **Secret Management**: Use environment variables or Secret Manager
- [ ] **Secret Rotation**: Implement key rotation policy (90 days)
- [ ] **Monitoring**: Set up alerts for suspicious activity
- [ ] **Rate Limiting**: Enable per-IP limits
- [ ] **HTTPS**: Always use HTTPS in production
- [ ] **Audit**: Regularly review security logs

### Testing

```bash
# Test CORS
python utils/security/cors_validator.py

# Test Request Signing
python utils/security/request_signer.py

# Test Security Logging
python utils/security/security_logger.py
```

---

## 📚 Additional Resources

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [NIST Cryptographic Standards](https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines)
- [MCP Security Best Practices](../SECURITY.md)

---

**Need help?** Contact: Henrystauber22@gmail.com
