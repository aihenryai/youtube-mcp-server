# YouTube MCP Server Enhanced ✨

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A **production-ready** Model Context Protocol (MCP) server for YouTube data extraction with advanced features: caching, rate limiting, input validation, and comprehensive error handling.

## 🎯 Features

### Core Capabilities
- **Video Transcripts** - Extract subtitles and captions in 20+ languages
- **Video Metadata** - Comprehensive video information (title, description, statistics)
- **Channel Analytics** - Channel statistics and information
- **Comments** - Fetch comments with replies
- **Video Search** - Search YouTube with advanced filters
- **Server Statistics** - Monitor cache and rate limit status

### 🆕 Enhanced Features (v2.0)

#### ⚡ Performance
- **Two-Tier Caching** - Memory (fast) + disk (persistent) caching
  - Reduces API quota usage by up to 90%
  - Configurable TTL per operation type
  - Cache statistics and monitoring
  
- **Smart Rate Limiting** - Thread-safe rate limiter
  - Per-minute and per-hour limits
  - Prevents quota exhaustion
  - Per-endpoint tracking

#### 🔒 Security & Reliability
- **Input Validation** - Comprehensive validation for all inputs
  - URL/ID format validation
  - Language code verification
  - Query sanitization
  
- **Retry Logic** - Automatic retry with exponential backoff
  - Handles transient API errors
  - Configurable retry attempts
  
- **Enhanced Error Handling** - Detailed error messages
  - User-friendly error descriptions
  - Error categorization
  
- **Logging** - Comprehensive logging system
  - Configurable log levels
  - Performance monitoring

## 📊 API Quota Optimization

### Without Caching
- Search: 100 units per request
- Video info: 1 unit per request
- Comments: 1 unit per page
- Daily limit: 10,000 units = **100 searches OR 10,000 video info requests**

### With Caching (v2.0) ✨
- First request: Uses quota
- Subsequent requests: **0 units** (from cache)
- **Result**: 10x-100x more requests possible!

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- YouTube Data API v3 key ([Get one here](https://console.cloud.google.com/apis/credentials))

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

Create or edit `.env` file:

```env
# Required
YOUTUBE_API_KEY=your-api-key-here

# Optional - Server Settings
MCP_TRANSPORT=stdio              # stdio (local) or http (remote)
PORT=8080                        # Port for HTTP mode
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR

# Optional - Performance Settings (defaults shown)
CACHE_ENABLED=true               # Enable caching
CACHE_TTL_SECONDS=3600          # Cache duration (1 hour)
RATE_LIMIT_ENABLED=true         # Enable rate limiting
CALLS_PER_MINUTE=30             # Max calls per minute
CALLS_PER_HOUR=1000             # Max calls per hour

# Optional - Security (HTTP mode only)
SERVER_API_KEY=your-secret-key  # Required for HTTP authentication
```

### Running Locally

```bash
# Run the server
python server.py

# The server will start in stdio mode for local MCP clients
```

### Claude Desktop Configuration

Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

## 🛠️ Available Tools

### 1. `get_video_transcript`
Extract video subtitles/captions with caching.

**Enhanced Features:**
- ✨ Cached for 1 hour
- ✨ Input validation
- ✨ Multi-language support (20+ languages)
- ✨ Automatic fallback to English

**Parameters:**
- `video_url` (string): YouTube video URL or ID
- `language` (string, optional): Language code (default: "en")

**Supported Languages:** en, he, ar, es, fr, de, it, pt, ru, ja, ko, zh, hi, and more

**Example:**
```python
get_video_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ", language="en")
```

### 2. `get_video_info`
Get comprehensive video metadata with retry logic.

**Enhanced Features:**
- ✨ Cached for 30 minutes
- ✨ Automatic retry (3 attempts)
- ✨ Text sanitization
- ✨ Rate limited

**Parameters:**
- `video_url` (string): YouTube video URL or ID

**Returns:** Title, description, channel, statistics, tags, thumbnails, etc.

### 3. `get_channel_info`
Retrieve channel statistics and information.

**Enhanced Features:**
- ✨ Cached for 1 hour
- ✨ @username resolution
- ✨ Automatic retry
- ✨ Rate limited

**Parameters:**
- `channel_id` (string): Channel ID, URL, or @username

**Examples:**
```python
get_channel_info("UC_x5XG1OV2P6uZZ5FSM9Ttw")  # Channel ID
get_channel_info("@googledev")                 # Username
```

### 4. `get_video_comments`
Fetch video comments with optional replies.

**Enhanced Features:**
- ✨ Cached for 30 minutes
- ✨ Comment sanitization
- ✨ Rate limited
- ✨ Reply limiting (max 10 per comment)

**Parameters:**
- `video_url` (string): YouTube video URL or ID
- `max_results` (int, optional): Maximum comments (1-100, default: 100)
- `include_replies` (bool, optional): Include replies (default: true)

### 5. `search_videos`
Search for YouTube videos with advanced filtering.

**Enhanced Features:**
- ✨ Cached for 10 minutes
- ✨ Smart order mapping
- ✨ Query validation
- ✨ Automatic retry

**Parameters:**
- `query` (string): Search query
- `max_results` (int, optional): Maximum results (1-50, default: 10)
- `order` (string, optional): Sort order

**Order Options:**
- `relevance` - Most relevant (default)
- `date` - Newest first
- `viewCount` - Most views
- `rating` - Highest rated
- `title` - Alphabetical

**Smart Order Mapping:**
- `views` → `viewCount`
- `recent` / `newest` → `date`
- `popular` → `viewCount`
- `top` → `rating`

### 6. `get_server_stats` ⭐ NEW
Monitor server performance and status.

**Returns:**
- Cache statistics (hits, misses, size)
- Rate limit status per endpoint
- Current configuration
- Server health

**Example:**
```python
get_server_stats()
```

## 🧪 Testing

Run the test suite:

```bash
# Install dev dependencies (already in requirements.txt)
pip install pytest pytest-asyncio pytest-cov

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
- ✅ Integration tests

## ☁️ Cloud Deployment (Google Cloud Run)

### Prerequisites
- Google Cloud account
- gcloud CLI installed and configured

### Deploy to Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/youtube-mcp
gcloud run deploy youtube-mcp \
  --image gcr.io/YOUR_PROJECT_ID/youtube-mcp \
  --platform managed \
  --region us-central1 \
  --no-allow-unauthenticated \
  --set-env-vars YOUTUBE_API_KEY=your-key-here,SERVER_API_KEY=your-secret-key

# Get the service URL
gcloud run services describe youtube-mcp \
  --region us-central1 \
  --format 'value(status.url)'
```

### Connect to Remote Server

```bash
# Run Cloud Run proxy
gcloud run services proxy youtube-mcp --region us-central1 --port 3000
```

Update Claude Desktop config:
```json
{
  "mcpServers": {
    "youtube-remote": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:3000/sse"]
    }
  }
}
```

## 🔒 Security

### Local Mode (stdio) - ✅ Recommended
- Most secure option
- No network exposure
- API key stays on your machine

### HTTP Mode - ⚠️ Use with Caution
- Enable `SERVER_API_KEY` authentication
- Use Cloud Run IAM for access control
- Never expose directly to the internet
- Use HTTPS only

**Security Features:**
- Input validation and sanitization
- Rate limiting prevents abuse
- No sensitive data in logs
- API key validation

## 📝 Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key | ✅ Yes | - |
| `MCP_TRANSPORT` | Transport mode (`stdio` or `http`) | No | `stdio` |
| `PORT` | Server port for HTTP mode | No | `8080` |
| `LOG_LEVEL` | Logging level | No | `INFO` |
| `CACHE_ENABLED` | Enable caching | No | `true` |
| `CACHE_TTL_SECONDS` | Cache duration | No | `3600` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | No | `true` |
| `CALLS_PER_MINUTE` | Max calls per minute | No | `30` |
| `CALLS_PER_HOUR` | Max calls per hour | No | `1000` |
| `SERVER_API_KEY` | Authentication for HTTP mode | HTTP only | - |

## 📊 Performance Metrics

### Cache Performance
- **Hit Rate**: Typically 60-80% for repeated queries
- **Response Time**: 
  - Cache hit: ~5ms
  - Cache miss: ~200-500ms (API call)
- **Storage**: 
  - Memory: 100 items (configurable)
  - Disk: Unlimited (automatic cleanup)

### Rate Limiting
- **Per-Minute**: 30 calls (prevents short bursts)
- **Per-Hour**: 1,000 calls (prevents quota exhaustion)
- **Quota Savings**: 70-90% reduction with caching

## 📊 API Quota Usage

Typical quota costs per operation:

| Operation | Cost (units) | With Cache |
|-----------|-------------|------------|
| Get video info | 1 | 0.1-0.3 (avg) |
| Get comments | 1 | 0.2-0.4 (avg) |
| Search videos | 100 | 10-30 (avg) |
| Get channel info | 1 | 0.1-0.2 (avg) |
| Get transcript | 0 (free!) | 0 |

**Daily Quota:** 10,000 units/day (free tier)

**Example Usage:**
- Without caching: 100 searches = entire quota
- With caching (80% hit rate): 500 searches = 10,000 units

## 🔧 Development

### Code Style
```bash
# Format code
black server.py utils/ tests/

# Lint code
flake8 server.py utils/ tests/

# Type checking
mypy server.py utils/
```

### Project Structure
```
youtube-mcp-server/
├── server.py           # Main server with enhanced features
├── config.py           # Centralized configuration
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── .gitignore         # Git ignore rules
├── utils/             # Utility modules
│   ├── __init__.py
│   ├── cache.py       # Two-tier caching
│   ├── rate_limiter.py # Rate limiting
│   └── validators.py  # Input validation
├── tests/             # Test suite
│   ├── __init__.py
│   └── test_utils.py  # Unit tests
└── README.md          # This file
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Development Guidelines:**
- Write tests for new features
- Follow PEP 8 style guidelines
- Update documentation
- Maintain backward compatibility

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Model Context Protocol](https://modelcontextprotocol.io)
- [YouTube Data API](https://developers.google.com/youtube/v3)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [GitHub Repository](https://github.com/aihenryai/youtube-mcp-server)

## 💬 Support

For issues, questions, or suggestions:
- Open an issue on [GitHub](https://github.com/aihenryai/youtube-mcp-server/issues)
- Check existing issues for solutions
- Provide detailed error messages and logs

## 📈 Changelog

### v2.0 - Enhanced Edition (2025-10-10)
- ✨ Added two-tier caching system (memory + disk)
- ✨ Implemented thread-safe rate limiting
- ✨ Added comprehensive input validation
- ✨ Implemented retry logic with exponential backoff
- ✨ Enhanced error handling and logging
- ✨ Added text sanitization
- ✨ New tool: `get_server_stats()`
- ✨ Added comprehensive test suite
- ✨ Improved security for HTTP mode
- 📝 Complete documentation overhaul

### v1.0 - Initial Release
- Basic MCP server functionality
- Video transcripts, metadata, channel info
- Comments and search capabilities

---

**Built with ❤️ for the MCP community**

⭐ **Star this repo if you find it useful!**