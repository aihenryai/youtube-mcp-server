# 🎬 YouTube MCP Server

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A **production-ready** [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for YouTube data extraction and management. Built with enterprise-grade features including OAuth2 authentication, intelligent caching, rate limiting, and comprehensive security.

## ✨ Key Features

### 🎯 Core Capabilities
- **📝 Video Transcripts** - Extract subtitles and captions in 20+ languages
- **📊 Video Metadata** - Comprehensive video information (title, description, statistics)
- **📺 Channel Analytics** - Channel statistics and information
- **💬 Comments** - Fetch comments with replies
- **🔍 Video Search** - Advanced search with filtering
- **📑 Playlist Management** - Create, edit, and organize playlists (OAuth2)
- **🔤 Caption Management** - Upload, update, and delete captions (OAuth2)
- **📈 Server Statistics** - Monitor performance and quota usage

### 🚀 Production Features

#### 🔐 Dual Authentication
- **API Key Mode** - Read-only operations (simple setup)
- **OAuth2 Mode** - Full access with write operations
- **Secure Token Storage** - AES-256 encryption
- **Auto Token Refresh** - Seamless authentication

#### ⚡ Performance & Reliability
- **Two-Tier Caching**
  - Memory cache (fast)
  - Disk cache (persistent)
  - 70-90% quota reduction
  - Configurable TTL per operation

- **Smart Rate Limiting**
  - Per-endpoint tracking
  - Per-IP protection
  - Quota preservation
  - Thread-safe implementation

#### 🔒 Enterprise Security
- **Prompt Injection Detection** - AI-powered security patterns
- **Input Validation** - Comprehensive sanitization
- **CORS Protection** - Configurable origins
- **Request Signing** - HMAC-SHA256 integrity
- **Security Logging** - Event tracking and alerting
- **Retry Logic** - Exponential backoff

#### 📊 Monitoring & Observability
- **Prometheus Metrics** - Full instrumentation
- **Health Checks** - Readiness and liveness probes
- **OAuth 2.1 Metadata** - RFC 9728 compliance
- **Performance Tracking** - Cache hits, API calls, errors

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- YouTube Data API v3 key ([Get one here](https://console.cloud.google.com/apis/credentials))
- (Optional) OAuth2 credentials for write operations

### Installation

```bash
# Clone the repository
git clone https://github.com/aihenryai/youtube-mcp-server.git
cd youtube-mcp-server

# Install dependencies
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your YOUTUBE_API_KEY
```

### Configuration

Edit `.env` file:

```env
# Required - YouTube API Key
YOUTUBE_API_KEY=your-api-key-here

# Optional - OAuth2 for write operations
USE_OAUTH2=false

# Optional - Performance tuning
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
RATE_LIMIT_ENABLED=true
CALLS_PER_MINUTE=30
CALLS_PER_HOUR=1000

# Optional - Server mode
MCP_TRANSPORT=stdio  # stdio (local) or http (remote)
PORT=8080
LOG_LEVEL=INFO
```

### Running the Server

```bash
# Start the server
python server.py

# The server will start in stdio mode for local MCP clients
```

### Claude Desktop Configuration

Add to your Claude Desktop config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "youtube": {
      "command": "python",
      "args": ["/absolute/path/to/youtube-mcp-server/server.py"],
      "env": {
        "YOUTUBE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**Note**: Replace `/absolute/path/to/youtube-mcp-server` with the actual path on your system.

## 🛠️ Available Tools

### Read Operations (API Key)

#### `get_video_transcript`
Extract video subtitles/captions with multi-language support.

```python
get_video_transcript(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    language="en"
)
```

**Supported languages**: en, he, ar, es, fr, de, it, pt, ru, ja, ko, zh, hi, and more  
**Quota cost**: 0 units (free!)  
**Cache TTL**: 1 hour

#### `get_video_info`
Get comprehensive video metadata.

```python
get_video_info(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
```

**Returns**: Title, description, statistics, tags, thumbnails, etc.  
**Quota cost**: 1 unit  
**Cache TTL**: 30 minutes

#### `get_channel_info`
Retrieve channel statistics and information.

```python
get_channel_info(channel_id="@googledev")  # or channel ID
```

**Quota cost**: 1 unit  
**Cache TTL**: 1 hour

#### `get_video_comments`
Fetch video comments with optional replies.

```python
get_video_comments(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    max_results=50,
    include_replies=True
)
```

**Quota cost**: 1 unit per page  
**Cache TTL**: 30 minutes

#### `search_videos`
Search YouTube with advanced filtering.

```python
search_videos(
    query="Python tutorial",
    max_results=20,
    order="viewCount"  # relevance, date, viewCount, rating, title
)
```

**Quota cost**: 100 units  
**Cache TTL**: 10 minutes

### Write Operations (OAuth2 Required)

#### `create_playlist`
Create a new playlist.

```python
create_playlist(
    title="My AI Learning Videos",
    description="Collection of AI/ML tutorials",
    privacy_status="private",
    tags=["AI", "Machine Learning"]
)
```

**Quota cost**: 50 units

#### `add_video_to_playlist`
Add a video to a playlist.

```python
add_video_to_playlist(
    playlist_id="PLxxxxxx",
    video_id="dQw4w9WgXcQ",
    position=0  # Optional: 0 for beginning, None for end
)
```

**Quota cost**: 50 units

#### `update_playlist`
Update playlist metadata.

```python
update_playlist(
    playlist_id="PLxxxxxx",
    title="Updated Title",
    privacy_status="public"
)
```

**Quota cost**: 50 units

#### `reorder_playlist_video`
Move video to new position.

```python
reorder_playlist_video(
    playlist_id="PLxxxxxx",
    video_id="dQw4w9WgXcQ",
    new_position=0
)
```

**Quota cost**: 50 units

### Monitoring Tools

#### `get_server_stats`
Get comprehensive server statistics.

```python
get_server_stats()
```

**Returns**: Cache stats, rate limits, security status, OAuth status

#### `server_health`
Check server health status.

```python
server_health()
```

**Returns**: Component health, uptime, connectivity

#### `server_metrics`
Get Prometheus metrics.

```python
server_metrics()
```

**Returns**: Metrics in Prometheus exposition format

## 🔐 OAuth2 Setup (Optional)

For write operations (playlists, captions, etc.), you need OAuth2:

### 1. Get OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create/select a project
3. Enable YouTube Data API v3
4. Create OAuth 2.0 Client ID (Desktop app)
5. Download `credentials.json`
6. Place in server root directory

### 2. Authenticate

```bash
# Set OAuth2 mode
echo "USE_OAUTH2=true" >> .env

# Run authentication
python authenticate.py auth

# Follow browser prompts to authenticate
```

### 3. Verify

```python
# In Claude, check status
check_oauth_status()
```

See [docs/OAUTH2_SETUP.md](docs/OAUTH2_SETUP.md) for detailed instructions.

## 📊 API Quota Optimization

### Without Caching
- Daily limit: 10,000 units
- 100 searches = **entire quota**
- 10,000 video info requests = **entire quota**

### With Caching (Enabled by Default) ✨
- First request: Uses quota
- Subsequent requests: **0 units** (from cache)
- Cache hit rate: 60-80% typical
- **Result**: 5-10x more requests possible!

### Example Usage

| Operation | Cost | With Cache (80% hit) | Requests/Day |
|-----------|------|---------------------|--------------|
| Search | 100 units | 20 units (avg) | 500 |
| Video Info | 1 unit | 0.2 units (avg) | 50,000 |
| Comments | 1 unit | 0.2 units (avg) | 50,000 |
| Channel Info | 1 unit | 0.1 units (avg) | 100,000 |
| Transcript | 0 units | 0 units | Unlimited* |

*Subject to rate limits only

## 🐳 Cloud Deployment

### Google Cloud Run

Deploy to Google Cloud Run for remote access:

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/youtube-mcp
gcloud run deploy youtube-mcp \
  --image gcr.io/YOUR_PROJECT_ID/youtube-mcp \
  --platform managed \
  --region us-central1 \
  --no-allow-unauthenticated
```

See [GOOGLE_CLOUD_DEPLOYMENT.md](GOOGLE_CLOUD_DEPLOYMENT.md) for full guide including:
- Secret Manager integration
- IAM configuration
- Cost optimization
- Monitoring setup

### Docker

Run locally with Docker:

```bash
# Build image
docker build -t youtube-mcp .

# Run container
docker run -p 8080:8080 \
  -e YOUTUBE_API_KEY=your-key \
  -e MCP_TRANSPORT=http \
  youtube-mcp
```

## 🔒 Security Best Practices

### Local Deployment (stdio) - ✅ Recommended
- Most secure option
- No network exposure
- API keys stay on your machine
- Direct process communication

### Remote Deployment (http) - ⚠️ Use with Caution
1. **Always use HTTPS** (Cloud Run provides this)
2. **Enable authentication** (`SERVER_API_KEY` required)
3. **Configure CORS** (restrict allowed origins)
4. **Use IAM** (Cloud Run IAM for access control)
5. **Enable monitoring** (check security logs regularly)

### Never Do This ❌
- Expose HTTP server directly to internet
- Use `ALLOWED_ORIGINS=*` in production
- Commit `.env` or `credentials.json` to Git
- Share your API key or OAuth2 tokens

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_utils.py -v
```

Test coverage includes:
- ✅ Input validators
- ✅ Cache operations
- ✅ Rate limiting
- ✅ Security features
- ✅ Integration tests

## 📖 Documentation

- [📚 OAuth2 Setup Guide](docs/OAUTH2_SETUP.md) - Detailed OAuth2 configuration
- [📑 Playlist Management](docs/PLAYLIST_MANAGEMENT.md) - Playlist operations guide
- [🔤 Caption Management](docs/CAPTIONS_MANAGEMENT.md) - Caption operations guide
- [🔐 Security Features](docs/SECURITY_FEATURES_GUIDE.md) - Security configuration
- [☁️ Cloud Deployment](GOOGLE_CLOUD_DEPLOYMENT.md) - Production deployment
- [⚡ Quick Start](QUICKSTART.md) - 5-minute setup guide

## 📊 Project Structure

```
youtube-mcp-server/
├── server.py                    # Main MCP server
├── config.py                    # Configuration management
├── youtube_client.py            # YouTube API client
├── authenticate.py              # OAuth2 authentication CLI
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── auth/                        # OAuth2 modules
│   ├── oauth2_manager.py
│   └── token_storage.py
├── playlist/                    # Playlist management
│   ├── playlist_creator.py
│   ├── playlist_manager.py
│   └── playlist_reorderer.py
├── captions/                    # Caption management
│   ├── captions_manager.py
│   └── captions_analyzer.py
├── utils/                       # Utility modules
│   ├── cache.py                 # Two-tier caching
│   ├── rate_limiter.py          # Rate limiting
│   ├── validators.py            # Input validation
│   ├── health_check.py          # Health monitoring
│   ├── prometheus_exporter.py  # Metrics exporter
│   └── security/                # Security components
│       ├── prompt_injection.py
│       ├── cors_validator.py
│       ├── ip_rate_limiter.py
│       └── request_signer.py
├── tests/                       # Test suite
│   ├── test_server.py
│   └── test_utils.py
└── docs/                        # Documentation
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation
- Maintain backward compatibility
- Add type hints
- Use black for formatting

## 🐛 Troubleshooting

### Common Issues

**"API key not configured"**
- Ensure `YOUTUBE_API_KEY` is set in `.env`
- Check the key has YouTube Data API v3 enabled

**"OAuth2 not authenticated"**
- Run `python authenticate.py auth`
- Ensure `credentials.json` exists
- Check OAuth2 consent screen is configured

**"Rate limit exceeded"**
- Wait for rate limit window to reset
- Adjust `CALLS_PER_MINUTE` in `.env`
- Enable caching to reduce API calls

**"Module not found"**
- Install dependencies: `pip install -r requirements.txt`
- Ensure Python 3.12+ is installed

**"Permission denied"**
- Check file permissions
- Run with appropriate user account
- On Windows, run as administrator if needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **MCP Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **YouTube API**: [developers.google.com/youtube/v3](https://developers.google.com/youtube/v3)
- **FastMCP**: [github.com/jlowin/fastmcp](https://github.com/jlowin/fastmcp)
- **Issues**: [github.com/aihenryai/youtube-mcp-server/issues](https://github.com/aihenryai/youtube-mcp-server/issues)

## 💬 Support & Community

- **Issues**: [Report bugs or request features](https://github.com/aihenryai/youtube-mcp-server/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/aihenryai/youtube-mcp-server/discussions)
- **Security**: [Report security vulnerabilities](SECURITY.md)

## 📈 Changelog

### v2.2 (Latest)
- ✨ Added OAuth 2.1 Protected Resource Metadata (RFC 9728)
- ✨ Enhanced Prometheus metrics with detailed tracking
- ✨ Comprehensive health check system
- 🔒 Advanced security features (prompt injection, CORS, request signing)
- 📊 Performance monitoring and observability

### v2.1
- ✨ Request signing with HMAC-SHA256
- ✨ Per-IP rate limiting
- ✨ Security event logging
- 🔒 Cache encryption (Fernet)
- 📝 Enhanced documentation

### v2.0
- ✨ OAuth2 authentication support
- ✨ Playlist and caption management
- ✨ Two-tier caching system
- ✨ Smart rate limiting
- 🔒 Comprehensive security features
- 📝 Full test coverage

### v1.0
- 🎉 Initial release
- 📝 Basic transcript and metadata extraction
- 🔍 Video search capabilities

---

**Built with ❤️ by [Henry Stauber](https://taplink.cc/henry.ai)**

⭐ **If you find this project useful, please star it on GitHub!**

---

## 🙏 Acknowledgments

- [Anthropic](https://anthropic.com) for the Model Context Protocol
- [Google](https://developers.google.com/youtube) for YouTube Data API
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP framework
- All contributors who help improve this project
