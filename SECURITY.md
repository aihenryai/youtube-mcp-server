# Security Policy

## 🔒 Supported Versions

| Version | Support Status |
|---------|---------------|
| 2.0.x   | ✅ Full support + security updates |
| 1.x     | ⚠️ Security patches only (EOL: 2025-12) |
| < 1.0   | ❌ No longer supported |

## 🚨 Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

Instead, please report security issues privately:
- **Email**: security@your-domain.com
- Include: Description, steps to reproduce, potential impact, suggested fix (if any)
- You'll receive a response within 48 hours

## 🛡️ Known Security Considerations

### 1. CORS Configuration (Critical)
**Issue**: Default CORS settings allow no origins (safe default)

**Before Production Deployment:**
```env
# ⚠️ REQUIRED: Configure allowed origins
ALLOWED_ORIGINS=https://your-frontend.com,https://your-app.com

# ❌ NEVER use "*" in production
# ALLOWED_ORIGINS=*  # THIS IS DANGEROUS!
```

**Why it matters**: Wildcard CORS allows any website to make requests to your server, enabling potential CSRF attacks.

### 2. OAuth2 Token Storage
**Current Implementation**:
- ✅ Tokens encrypted at rest (AES-256)
- ✅ Secure key derivation (PBKDF2)
- ⚠️ Tokens decrypted in memory during use

**For Production on Google Cloud**:
```python
# Recommended: Use Google Secret Manager
from google.cloud import secretmanager

def get_token():
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(
        request={"name": "projects/PROJECT/secrets/youtube-token/versions/latest"}
    )
    return json.loads(response.payload.data.decode("UTF-8"))
```

### 3. API Key Protection
**Current Implementation**:
- ✅ API key in .env (gitignored)
- ✅ Basic format validation
- ⚠️ No advanced validation

**Best Practices**:
```bash
# Use environment variables
export YOUTUBE_API_KEY=your-key-here

# Rotate keys every 90 days
# Monitor usage in Google Cloud Console
# Set quota limits to prevent abuse
```

### 4. Rate Limiting
**Current Implementation**:
- ✅ Global rate limiting
- ⚠️ No per-IP/user limiting

**Known Limitation**: A single malicious user can exhaust quota for everyone.

**Mitigation** (Coming in v2.1):
```python
# Per-IP rate limiting will be added
@rate_limit_per_ip(max_per_minute=10)
def tool_handler():
    ...
```

## 🔐 Security Best Practices

### Local Development (stdio mode)
✅ **Recommended Setup** - Most secure
```json
{
  "mcpServers": {
    "youtube": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "YOUTUBE_API_KEY": "your-key",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

**Why secure**: No network exposure, API key stays local

### HTTP Mode (Remote Server)
⚠️ **Use with caution**

**Required Security Measures**:
```env
# 1. Enable authentication
SERVER_API_KEY=generate-strong-random-key-here

# 2. Configure CORS
ALLOWED_ORIGINS=https://your-frontend.com

# 3. Use HTTPS only
# Never expose HTTP endpoint to internet

# 4. Enable rate limiting
RATE_LIMIT_ENABLED=true
```

### Google Cloud Run Deployment
✅ **Production-Ready Setup**

**Security Checklist**:
- [ ] Enable IAM authentication
- [ ] Use Secret Manager for API keys
- [ ] Configure CORS properly
- [ ] Enable Cloud Armor (DDoS protection)
- [ ] Set up monitoring and alerts
- [ ] Use least-privilege service account

```bash
# Deploy with security
gcloud run deploy youtube-mcp \
  --image gcr.io/PROJECT/youtube-mcp \
  --no-allow-unauthenticated \  # Require IAM auth
  --set-secrets="YOUTUBE_API_KEY=youtube-api-key:latest" \
  --service-account=mcp-server@PROJECT.iam.gserviceaccount.com
```

## 🔍 Input Validation

### Implemented Protections
✅ All user inputs are validated:
- URL/ID format validation
- Language code whitelist
- Query length limits (500 chars)
- Result count limits (1-100)
- Text sanitization (HTML/script removal)

### Protected Against
- SQL Injection (N/A - no database)
- XSS (text sanitization)
- Path Traversal (input validation)
- Excessive API usage (rate limiting)

## 📝 Logging Security

### Current Implementation
✅ Safe logging practices:
- No API keys in logs
- No OAuth tokens in logs
- No user credentials logged
- Structured logging (JSON)

### Log Access
```bash
# Logs stored locally
logs/youtube-mcp.log

# Google Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision"
```

## 🚫 Known Limitations

### 1. No Built-in User Authentication
- The server uses either stdio (no auth needed) or API key authentication
- For multi-user scenarios, implement a separate auth layer

### 2. Global Rate Limiting
- Rate limits apply to the entire server, not per-user
- A single user can impact others

### 3. Cache Security
- Cache stored unencrypted on disk
- Sensitive data may persist in cache
- Recommendation: Use cache only for public data

## 🔧 Security Updates

To receive security updates:
1. Watch the GitHub repository
2. Subscribe to release notifications
3. Follow @yourusername on Twitter

## ✅ Security Checklist

Before deploying to production:

### Required
- [ ] Set `ALLOWED_ORIGINS` (not "*")
- [ ] Enable `SERVER_API_KEY` for HTTP mode
- [ ] Use HTTPS only (no HTTP)
- [ ] Rotate API keys regularly
- [ ] Review logs for suspicious activity

### Recommended
- [ ] Use Google Secret Manager
- [ ] Enable Cloud Armor
- [ ] Set up monitoring and alerts
- [ ] Implement per-user rate limiting
- [ ] Use least-privilege service accounts
- [ ] Enable audit logging

### Optional but Advised
- [ ] Use VPC for internal communication
- [ ] Implement request signing
- [ ] Add request logging
- [ ] Set up SIEM integration

## 📚 References

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Google Cloud Security Best Practices](https://cloud.google.com/security/best-practices)
- [YouTube API Security](https://developers.google.com/youtube/v3/guides/authentication)

## 🔄 Update Policy

- **Critical vulnerabilities**: Patched within 24-48 hours
- **High severity**: Patched within 1 week
- **Medium/Low**: Addressed in next release

---

**Last Updated**: 2025-10-16
**Security Contact**: security@your-domain.com
