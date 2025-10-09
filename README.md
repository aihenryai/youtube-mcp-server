# YouTube MCP Server

A comprehensive Model Context Protocol (MCP) server for YouTube data extraction. This server provides tools for retrieving video transcripts, channel analytics, comments, video descriptions, and metadata from YouTube.

## 🎯 Features

- **Video Transcripts** - Extract subtitles and captions in multiple languages
- **Video Metadata** - Get titles, descriptions, tags, thumbnails, and more
- **Channel Analytics** - Retrieve channel statistics and information
- **Comments** - Fetch video comments with replies
- **Video Analytics** - Access view counts, likes, engagement metrics
- **Multiple Deployments** - Run locally or deploy to Google Cloud Run

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- YouTube Data API v3 key ([Get one here](https://console.cloud.google.com/apis/credentials))

### Local Installation

```bash
# Clone the repository
git clone https://github.com/aihenryai/youtube-mcp-server.git
cd youtube-mcp-server

# Install dependencies using uv (recommended)
uv pip install -r requirements.txt

# Or use pip
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your YOUTUBE_API_KEY
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
      "args": ["/path/to/youtube-mcp-server/server.py"],
      "env": {
        "YOUTUBE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

## 🛠️ Available Tools

### 1. `get_video_transcript`
Extract video subtitles/captions.

**Parameters:**
- `video_url` (string): YouTube video URL or ID
- `language` (string, optional): Language code (default: "en")

**Example:**
```python
get_video_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ", language="en")
```

### 2. `get_video_info`
Get comprehensive video metadata.

**Parameters:**
- `video_url` (string): YouTube video URL or ID

**Returns:** Title, description, channel, publish date, duration, tags, thumbnails

### 3. `get_channel_info`
Retrieve channel statistics and information.

**Parameters:**
- `channel_id` (string): YouTube channel ID or URL

**Returns:** Channel name, subscriber count, video count, view count, description

### 4. `get_video_comments`
Fetch video comments with optional replies.

**Parameters:**
- `video_url` (string): YouTube video URL or ID
- `max_results` (int, optional): Maximum comments to retrieve (default: 100)
- `include_replies` (bool, optional): Include comment replies (default: true)

### 5. `search_videos`
Search for YouTube videos.

**Parameters:**
- `query` (string): Search query
- `max_results` (int, optional): Maximum results (default: 10)

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
  --set-env-vars YOUTUBE_API_KEY=your-key-here

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

- **API Keys**: Never commit API keys. Use environment variables.
- **Authentication**: Cloud deployment requires IAM authentication.
- **Rate Limits**: Respects YouTube API quotas (10,000 units/day free tier).

## 📝 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 key | Yes |
| `MCP_TRANSPORT` | Transport mode (`stdio` or `http`) | No (default: `stdio`) |
| `PORT` | Server port for HTTP mode | No (default: `8080`) |

## 🧪 Testing

```bash
# Run with MCP Inspector
npx @modelcontextprotocol/inspector python server.py
```

## 📊 API Quota Usage

Typical quota costs per operation:
- Get video info: 1 unit
- Get comments: 1 unit per page
- Search videos: 100 units
- Get channel info: 1 unit

Free tier: 10,000 units/day

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see LICENSE file for details

## 🔗 Links

- [Model Context Protocol](https://modelcontextprotocol.io)
- [YouTube Data API](https://developers.google.com/youtube/v3)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)

## 💬 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Built with ❤️ for the MCP community**
