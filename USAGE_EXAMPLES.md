# Usage Examples

## Basic Usage

### 1. Get Video Transcript

```python
# Using Claude Desktop
# Just ask: "Get the transcript of this video: https://youtube.com/watch?v=..."

# Claude will use:
get_video_transcript(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    language="en"
)
```

### 2. Search Videos

```python
# Ask Claude: "Search for Python tutorials on YouTube"

# Claude will use:
search_videos(
    query="Python tutorials",
    max_results=10,
    order="relevance"
)
```

### 3. Get Video Information

```python
# Ask: "Get info about this video: [URL]"

get_video_info("https://www.youtube.com/watch?v=VIDEO_ID")
```

## Advanced Usage with OAuth2

### 1. Create a Playlist

```python
# First, authenticate:
# python authenticate.py auth

# Then ask Claude: "Create a playlist called 'AI Learning'"

create_playlist(
    title="AI Learning Videos",
    description="Collection of AI/ML tutorials",
    privacy_status="private",
    tags=["AI", "Machine Learning", "Deep Learning"]
)
```

### 2. Add Videos to Playlist

```python
# Ask: "Add this video to my playlist: [PLAYLIST_ID]"

add_video_to_playlist(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    video_id="dQw4w9WgXcQ",
    position=0  # Add to beginning
)
```

## Real-World Examples

### Example 1: Create Learning Playlist

**Request to Claude:**
> "I want to create a private playlist for Python tutorials. Find the top 10 Python tutorial videos and add them to a new playlist."

**What happens:**
1. Claude creates playlist with OAuth2
2. Searches for "Python tutorials"
3. Adds top 10 videos to the playlist
4. Returns playlist URL

### Example 2: Analyze Channel

**Request to Claude:**
> "Give me statistics about the @googledev YouTube channel"

**What happens:**
1. Claude resolves @googledev to channel ID
2. Fetches channel statistics
3. Returns formatted report with:
   - Subscriber count
   - Total videos
   - Total views
   - Latest uploads

### Example 3: Transcript Analysis

**Request to Claude:**
> "Get the transcript of [VIDEO_URL] and summarize the key points"

**What happens:**
1. Fetches transcript (from cache if available)
2. Claude analyzes the full text
3. Provides structured summary

## Tips & Tricks

### Performance Optimization

- **Use caching**: Repeated requests are instant (served from cache)
- **Monitor quota**: Use `get_server_stats()` to check usage
- **Batch operations**: Ask Claude to process multiple videos at once

### OAuth2 Best Practices

- Keep `credentials.json` secure
- Re-authenticate if token expires
- Use `check_oauth_status()` to verify authentication

### Error Handling

If you encounter errors:

1. **"API quota exceeded"**: Wait or enable caching
2. **"OAuth2 required"**: Run `python authenticate.py auth`
3. **"Video not found"**: Check URL format
4. **"No transcript available"**: Video may not have captions

## Common Patterns

### Pattern 1: Research Assistant

```
User: "Find videos about quantum computing from the last year, 
       get their transcripts, and help me understand the key concepts"

Claude will:
1. Search videos (with date filter)
2. Get transcripts for top results
3. Analyze and summarize concepts
```

### Pattern 2: Content Curator

```
User: "Create a playlist of the best machine learning tutorials, 
       organized by difficulty"

Claude will:
1. Create playlist with OAuth2
2. Search for ML tutorials
3. Get video info to assess difficulty
4. Add videos in order
5. Update playlist description
```

### Pattern 3: Channel Analysis

```
User: "Compare the subscriber growth and content strategy 
       of @channel1 and @channel2"

Claude will:
1. Get channel info for both
2. Analyze statistics
3. Search recent videos
4. Provide comparative analysis
```

## Integration Examples

### With Other MCP Servers

```json
{
  "mcpServers": {
    "youtube": {
      "command": "python",
      "args": ["path/to/youtube-mcp-server/server.py"]
    },
    "filesystem": {
      // Save transcripts to files
    },
    "web-search": {
      // Complement YouTube search with web results
    }
  }
}
```

### Automation Scripts

```python
# Example: Daily digest of channel uploads
from youtube_client import YouTubeClient

client = YouTubeClient(api_key="YOUR_KEY")
channel_info = client.get_channel_info("@channel")
# ... process and send digest
```

## Need Help?

- 📖 Check [README.md](README.md) for full documentation
- 🐛 Report issues on [GitHub](https://github.com/aihenryai/youtube-mcp-server/issues)
- 💬 Ask questions in discussions