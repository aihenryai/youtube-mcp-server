# Quick Start Guide - YouTube MCP Server

## 🚀 Installation & Setup (5 minutes)

### Step 1: Install Dependencies
```bash
cd youtube-mcp-server-local
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API key
# Get one at: https://console.cloud.google.com/apis/credentials
YOUTUBE_API_KEY=your_api_key_here
```

### Step 3: Test Basic Operations (Read-Only)
```bash
# Run the server
python server.py
```

**At this point, you can use:**
✅ get_video_transcript  
✅ get_video_info  
✅ get_channel_info  
✅ get_video_comments  
✅ search_videos

## 🔐 Enable OAuth2 (Optional - for Write Operations)

If you want to manage playlists, upload videos, or modify content:

### Step 1: Get OAuth2 Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID (Desktop app)
3. Download `credentials.json` and save in server directory

### Step 2: Enable OAuth2
```bash
# Edit .env
USE_OAUTH2=true
```

### Step 3: Authenticate
```bash
python authenticate.py auth
```

This will:
- Open browser for Google consent
- Save encrypted token
- Enable write operations

### Step 4: Verify
```bash
python authenticate.py test
```

**Now you can use:**
✅ create_playlist  
✅ add_video_to_playlist  
✅ update_playlist  
✅ And all other write operations!

## 📝 Quick Examples

### Example 1: Get Video Transcript
```python
from server import get_video_transcript

result = get_video_transcript(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    language="en"
)

print(result['full_text'])
```

### Example 2: Create Playlist (OAuth2 required)
```python
from server import create_playlist

result = create_playlist(
    title="My AI Learning Videos",
    description="Collection of AI tutorials",
    privacy_status="private"
)

print(f"Playlist created: {result['playlist_id']}")
```

### Example 3: Search Videos
```python
from server import search_videos

result = search_videos(
    query="Python tutorial",
    max_results=10,
    order="viewCount"
)

for video in result['videos']:
    print(f"{video['title']} - {video['channel_title']}")
```

## 🔍 Troubleshooting

### "YouTube API key not found"
- Make sure `.env` file exists
- Check that `YOUTUBE_API_KEY` is set

### "OAuth2 authentication required"
- Set `USE_OAUTH2=true` in `.env`
- Run `python authenticate.py auth`

### "credentials.json not found"
- Download OAuth2 credentials from Google Cloud Console
- Save as `credentials.json` in server directory

## 📚 Next Steps

1. **Read full documentation**: Check `docs/OAUTH2_SETUP.md`
2. **Explore tools**: See `README.md` for all available tools
3. **Check examples**: Look at playlist and captions docs

## ⚡ Performance Tips

- Enable caching for better performance (already enabled by default)
- Use rate limiting to avoid quota exhaustion
- Check quota usage with `get_server_stats()`

## 🆘 Need Help?

1. Check logs for detailed error messages
2. Run `python authenticate.py status` for OAuth status
3. See troubleshooting guides in docs/
4. Open an issue on GitHub

---

**Ready to go?** Start with read-only operations, then enable OAuth2 when needed!
