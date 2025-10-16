# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-10-16

### 🎉 Major Release - Enhanced Edition

This release transforms the YouTube MCP Server into a production-ready, enterprise-grade tool with advanced features.

### ✨ Added

#### Authentication & Security
- **OAuth2 Support**: Full OAuth2 flow with encrypted token storage (AES-256)
- **Secure Credentials**: Token encryption with PBKDF2 key derivation
- **Auto-Refresh**: Tokens refresh automatically without user intervention
- **CLI Authentication**: Simple `authenticate.py` tool for easy setup
- **Dual Authentication**: API key for read operations, OAuth2 for write operations

#### Performance
- **Two-Tier Caching**: Memory cache (fast) + disk cache (persistent)
  - Reduces API quota usage by up to 90%
  - Configurable TTL per operation type
  - Automatic cleanup and size management
  - Cache statistics and monitoring via `get_server_stats()`
  
- **Smart Rate Limiting**: Thread-safe rate limiter
  - Per-minute and per-hour limits
  - Per-endpoint tracking
  - Prevents quota exhaustion
  - Configurable limits via environment variables

#### New Features
- **Playlist Management** (OAuth2 required):
  - `create_playlist()`: Create new playlists with metadata
  - `add_video_to_playlist()`: Add videos with position control
  - `remove_video_from_playlist()`: Remove by ID, position, or video
  - `update_playlist()`: Update metadata (title, description, privacy)
  - `reorder_playlist_video()`: Reorder playlist items
  - `list_user_playlists()`: List all user playlists

- **Caption Management** (OAuth2 required):
  - Upload custom captions
  - Update caption tracks
  - Delete captions
  - Analyze caption availability

- **Server Statistics**:
  - `get_server_stats()`: Monitor cache hits/misses, rate limits
  - `check_oauth_status()`: Check OAuth2 authentication status

#### Quality & Reliability
- **Input Validation**: Comprehensive validation for all inputs
  - URL/ID format validation
  - Language code verification
  - Query sanitization (XSS prevention)
  - Parameter bounds checking
  
- **Retry Logic**: Automatic retry with exponential backoff
  - Configurable retry attempts
  - Handles transient API errors
  - Smart failure detection

- **Enhanced Error Handling**:
  - User-friendly error messages
  - Detailed logging
  - Error categorization

#### Developer Experience
- **Comprehensive Tests**: Full test suite with pytest
  - Unit tests for all validators
  - Cache operation tests
  - Rate limiting tests
  - Integration tests
  - >80% code coverage

- **Documentation**:
  - Complete README overhaul
  - Security policy (SECURITY.md)
  - Quick start guide (QUICKSTART.md)
  - Google Cloud deployment guide
  - OAuth2 setup instructions
  - Playlist management guide
  - Caption management guide
  - Usage examples
  - Contributing guidelines

#### Infrastructure
- **Docker Support**: Production-ready Dockerfile with multi-stage build
- **Cloud Ready**: Google Cloud Run deployment with Cloud Build
- **Secret Management**: Integration with Google Cloud Secret Manager
- **CI/CD Ready**: Structured for automated deployments

### 🔄 Changed

- **API Client**: Refactored to support both API key and OAuth2
- **Configuration**: Centralized config management with Pydantic
- **Logging**: Enhanced structured logging throughout
- **Project Structure**: Organized into logical modules (auth/, playlist/, captions/, utils/)

### 🐛 Fixed

- Channel @username resolution now works correctly
- Improved error messages for missing captions
- Better handling of quota errors
- Fixed cache key generation for consistent hits

### 🔒 Security

- AES-256 encryption for OAuth2 tokens
- Input sanitization prevents XSS
- No sensitive data in logs
- Secure defaults for HTTP mode
- CORS configuration required for production

### 📚 Documentation

- Added SECURITY.md with security policy
- Added CONTRIBUTING.md for contributors
- Added USAGE_EXAMPLES.md with real-world patterns
- Added CHANGELOG.md (this file)
- Comprehensive inline documentation
- API reference in README
- Troubleshooting guides

### 🏗️ Infrastructure

- Added Dockerfile for containerization
- Added cloudbuild.yaml for CI/CD
- Added .gcloudignore for Google Cloud
- Added test suite infrastructure

## [1.0.0] - 2025-01-01

### Initial Release

- Basic MCP server functionality
- Video transcripts extraction
- Video metadata retrieval
- Channel information
- Comment fetching
- Video search
- Simple caching
- Basic error handling

---

## Upgrade Guide

### From 1.0 to 2.0

1. **Install new dependencies**:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

2. **Update configuration**:
   - Copy new environment variables from `.env.example`
   - Set `USE_OAUTH2=false` if you only need read operations
   - Configure caching and rate limiting settings

3. **OAuth2 Setup** (optional, for write operations):
   ```bash
   # Download credentials.json from Google Cloud Console
   python authenticate.py auth
   ```

4. **Test the upgrade**:
   ```bash
   python server.py
   # In another terminal:
   pytest
   ```

### Breaking Changes

None - v2.0 is fully backward compatible with v1.0. All existing functionality works as before, with new features requiring explicit enablement (OAuth2).

---

## Support

For issues, questions, or feature requests:
- 🐛 [GitHub Issues](https://github.com/aihenryai/youtube-mcp-server/issues)
- 📧 Email: henrystauber22@gmail.com
- 💬 [Discussions](https://github.com/aihenryai/youtube-mcp-server/discussions)