# YouTube MCP Server - Playlist Management Guide

Complete guide for managing YouTube playlists using the MCP server.

## Table of Contents

1. [Overview](#overview)
2. [Setup](#setup)
3. [Creating Playlists](#creating-playlists)
4. [Updating Playlists](#updating-playlists)
5. [Managing Videos](#managing-videos)
6. [Reordering Videos](#reordering-videos)
7. [Batch Operations](#batch-operations)
8. [Error Handling](#error-handling)
9. [Quota Management](#quota-management)
10. [Best Practices](#best-practices)

---

## Overview

The Playlist Management module provides comprehensive control over YouTube playlists:

- **PlaylistCreator** - Create and delete playlists
- **PlaylistUpdater** - Update playlist metadata
- **PlaylistManager** - Add and remove videos
- **PlaylistReorderer** - Reorder videos

### Features

✅ Full CRUD operations for playlists  
✅ Batch operations with progress tracking  
✅ Privacy control (public/private/unlisted)  
✅ Position management for videos  
✅ Duplicate detection  
✅ Comprehensive error handling  
✅ Quota tracking and optimization

---

## Setup

### Prerequisites

```python
from googleapiclient.discovery import build
from playlist import (
    PlaylistCreator,
    PlaylistUpdater,
    PlaylistManager,
    PlaylistReorderer
)

# Authenticated YouTube API resource
youtube = build('youtube', 'v3', credentials=credentials)

# Initialize managers
creator = PlaylistCreator(youtube)
updater = PlaylistUpdater(youtube)
manager = PlaylistManager(youtube)
reorderer = PlaylistReorderer(youtube)
```

### Required Scopes

```python
SCOPES = [
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]
```

---

## Creating Playlists

### Basic Creation

```python
# Create a private playlist
result = creator.create_playlist(
    title="My Favorite Videos",
    description="Collection of interesting content",
    privacy_status="private"
)

print(f"Playlist created: {result['url']}")
print(f"Playlist ID: {result['id']}")
```

**Output:**
```python
{
    'id': 'PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'title': 'My Favorite Videos',
    'description': 'Collection of interesting content',
    'privacy_status': 'private',
    'url': 'https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'published_at': '2025-10-10T10:00:00Z',
    'item_count': 0,
    'tags': []
}
```

**Quota Cost:** 50 units

### With Tags and Language

```python
result = creator.create_playlist(
    title="טיולים בישראל",
    description="מדריכי טיולים והמלצות",
    privacy_status="public",
    default_language="he",
    tags=["travel", "israel", "tourism"]
)
```

### Privacy Options

- `"private"` - Only you can see (default)
- `"public"` - Everyone can see
- `"unlisted"` - Anyone with link can see

### Validation Rules

- **Title:** 1-150 characters (required)
- **Description:** 0-5000 characters
- **Privacy:** Must be "public", "private", or "unlisted"
- **Tags:** Optional list of strings

---

## Updating Playlists

### Update Title and Description

```python
result = updater.update_playlist(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    title="Updated Title",
    description="Updated description"
)

print(f"Updated fields: {result['changes_made']}")
# Output: ['title', 'description']
```

**Quota Cost:** 50 units

### Change Privacy Status

```python
# Make playlist public
result = updater.update_playlist(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    privacy_status="public"
)
```

### Partial Updates

Only specified fields are updated. Others remain unchanged:

```python
# Update only tags, keep everything else
result = updater.update_playlist(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    tags=["new-tag", "another-tag"]
)
```

### Get Playlist Info

```python
info = updater.get_playlist_info("PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

print(f"Title: {info['title']}")
print(f"Videos: {info['item_count']}")
print(f"Privacy: {info['privacy_status']}")
```

**Output:**
```python
{
    'id': 'PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'title': 'My Playlist',
    'description': '...',
    'privacy_status': 'private',
    'published_at': '2025-10-10T10:00:00Z',
    'channel_id': 'UCxxxxxxxxxxxxxxxxxxxxxx',
    'channel_title': 'My Channel',
    'item_count': 15,
    'url': 'https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'thumbnails': {...},
    'tags': ['tag1', 'tag2']
}
```

**Quota Cost:** 1 unit

---

## Managing Videos

### Add Single Video

```python
# Add to end of playlist
result = manager.add_video(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    video_id="dQw4w9WgXcQ"
)

print(f"Added at position: {result['position']}")
```

**Quota Cost:** 50 units

### Add at Specific Position

```python
# Add at beginning (position 0)
result = manager.add_video(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    video_id="dQw4w9WgXcQ",
    position=0
)
```

### Add Multiple Videos

```python
video_ids = [
    "dQw4w9WgXcQ",
    "jNQXAC9IVRw",
    "9bZkp7q19f0"
]

def progress(current, total, video_id):
    print(f"Adding {current}/{total}: {video_id}")

result = manager.add_videos_batch(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    video_ids=video_ids,
    skip_duplicates=True,
    progress_callback=progress
)

print(f"✅ Added: {len(result['added'])}")
print(f"❌ Failed: {len(result['failed'])}")
print(f"⏭️ Skipped: {len(result['skipped'])}")
```

**Output:**
```python
{
    'added': ['dQw4w9WgXcQ', '9bZkp7q19f0'],
    'failed': [{
        'video_id': 'jNQXAC9IVRw',
        'error': 'Video not found or unavailable'
    }],
    'skipped': [],
    'total': 3
}
```

**Quota Cost:** 50 units per video

### Remove Video

```python
result = manager.remove_video(
    playlist_item_id="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxW1FVGVZQllGQU4"
)

print(result['message'])
# Output: "Video removed from playlist successfully"
```

**Quota Cost:** 50 units

### Remove Multiple Videos

```python
item_ids = [
    "UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1",
    "UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx2",
    "UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx3"
]

result = manager.remove_videos_batch(
    playlist_item_ids=item_ids,
    continue_on_error=True
)

print(f"Removed: {len(result['removed'])}/{result['total']}")
```

**Quota Cost:** 50 units per video

---

## Reordering Videos

### Move to Specific Position

```python
result = reorderer.move_video(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    playlist_item_id="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxW1FVGVZQllGQU4",
    new_position=0  # Move to top
)

print(f"Moved from {result['old_position']} to {result['new_position']}")
```

**Quota Cost:** 50 units

### Quick Position Methods

```python
# Move to top (position 0)
result = reorderer.move_to_top(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    playlist_item_id="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxW1FVGVZQllGQU4"
)

# Move to bottom
result = reorderer.move_to_bottom(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    playlist_item_id="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxW1FVGVZQllGQU4"
)
```

### Swap Two Videos

```python
result = reorderer.swap_videos(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    item_id_1="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1",
    item_id_2="UExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx2"
)

print("Videos swapped successfully!")
```

**Quota Cost:** 102 units (2 fetch + 100 move)

### Reverse Playlist

⚠️ **Warning:** Quota-intensive for large playlists!

```python
result = reorderer.reverse_playlist(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
)

print(f"Reversed {result['reversed']}/{result['total_items']} videos")
```

**Quota Cost:** 1 unit (fetch) + 50 units per video

---

## Batch Operations

### Progress Tracking

All batch operations support progress callbacks:

```python
def progress_handler(current, total, item):
    percentage = (current / total) * 100
    print(f"Progress: {percentage:.1f}% ({current}/{total})")

# Use with any batch operation
manager.add_videos_batch(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    video_ids=video_list,
    progress_callback=progress_handler
)
```

### Error Handling

```python
result = manager.add_videos_batch(
    playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    video_ids=["video1", "video2", "invalid_video"],
    skip_duplicates=True
)

# Check for failures
if result['failed']:
    print("Some videos failed:")
    for failure in result['failed']:
        print(f"  - {failure['video_id']}: {failure['error']}")
```

### Rate Limiting

Batch operations automatically include rate limiting (500ms delay) to prevent quota exhaustion.

---

## Error Handling

### Common Errors

#### Playlist Not Found
```python
try:
    updater.update_playlist(
        playlist_id="invalid_id",
        title="New Title"
    )
except ValueError as e:
    print(f"Error: {e}")
    # Output: "Playlist not found: invalid_id"
```

#### Video Not Available
```python
try:
    manager.add_video(
        playlist_id="PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        video_id="private_video"
    )
except ValueError as e:
    print(f"Error: {e}")
    # Output: "Video cannot be added (private/restricted)"
```

#### Validation Errors
```python
try:
    creator.create_playlist(
        title="",  # Empty title
        privacy_status="invalid"  # Invalid privacy
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

### Best Practices

```python
def safe_add_video(manager, playlist_id, video_id):
    """Safely add video with error handling"""
    try:
        result = manager.add_video(playlist_id, video_id)
        logger.info(f"✅ Added: {video_id}")
        return result
    except ValueError as e:
        logger.error(f"❌ Failed to add {video_id}: {e}")
        return None
    except HttpError as e:
        if e.resp.status == 403:
            logger.error("Quota exceeded or permission denied")
        else:
            logger.error(f"API error: {e}")
        return None
```

---

## Quota Management

### Daily Quota: 10,000 units

### Operation Costs

| Operation | Cost (units) |
|-----------|-------------|
| Create playlist | 50 |
| Update playlist | 50 |
| Delete playlist | 50 |
| Add video | 50 |
| Remove video | 50 |
| Move video | 50 |
| Get playlist info | 1 |
| List playlist items | 1 |

### Quota Optimization Tips

1. **Batch Operations** - Use batch methods to add multiple videos
2. **Skip Duplicates** - Enable to avoid wasted operations
3. **Cache Info** - Store playlist info to avoid repeated fetches
4. **Rate Limiting** - Built-in delays prevent rapid quota drain

### Example Calculation

```python
# Adding 20 videos to a playlist
videos = ["video1", "video2", ..., "video20"]

# Option 1: Individual adds
# Cost: 20 videos × 50 units = 1,000 units

# Option 2: Batch with duplicates check
# Cost: 1 fetch + (20 × 50) = 1,001 units
# But skips duplicates, potentially saving hundreds of units!

result = manager.add_videos_batch(
    playlist_id=playlist_id,
    video_ids=videos,
    skip_duplicates=True
)
```

---

## Best Practices

### 1. Always Validate Input

```python
def validate_video_ids(video_ids):
    """Validate list of video IDs"""
    if not video_ids:
        raise ValueError("Video list cannot be empty")
    
    valid_ids = []
    for vid in video_ids:
        if vid and len(vid) == 11:  # YouTube ID length
            valid_ids.append(vid)
    
    return valid_ids
```

### 2. Use Progress Callbacks

```python
def create_progress_bar(operation_name):
    """Create progress callback"""
    def callback(current, total, item):
        bar = "=" * (current * 20 // total)
        print(f"
{operation_name}: [{bar:<20}] {current}/{total}", end="")
    return callback

manager.add_videos_batch(
    playlist_id=playlist_id,
    video_ids=videos,
    progress_callback=create_progress_bar("Adding videos")
)
```

### 3. Handle Errors Gracefully

```python
def add_with_retry(manager, playlist_id, video_id, max_retries=3):
    """Add video with retry logic"""
    for attempt in range(max_retries):
        try:
            return manager.add_video(playlist_id, video_id)
        except HttpError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

### 4. Monitor Quota Usage

```python
class QuotaTracker:
    """Track quota usage"""
    def __init__(self, daily_limit=10000):
        self.daily_limit = daily_limit
        self.used = 0
    
    def add_cost(self, cost):
        self.used += cost
        remaining = self.daily_limit - self.used
        print(f"Quota: {self.used}/{self.daily_limit} ({remaining} remaining)")
    
    def can_perform(self, cost):
        return (self.used + cost) <= self.daily_limit

# Usage
tracker = QuotaTracker()

if tracker.can_perform(50):
    result = manager.add_video(playlist_id, video_id)
    tracker.add_cost(50)
else:
    print("⚠️ Insufficient quota!")
```

### 5. Batch Operations Smartly

```python
# Split large batches to avoid quota exhaustion
def add_videos_in_chunks(manager, playlist_id, video_ids, chunk_size=20):
    """Add videos in manageable chunks"""
    total = len(video_ids)
    
    for i in range(0, total, chunk_size):
        chunk = video_ids[i:i + chunk_size]
        print(f"Processing chunk {i//chunk_size + 1}...")
        
        result = manager.add_videos_batch(
            playlist_id=playlist_id,
            video_ids=chunk,
            skip_duplicates=True
        )
        
        print(f"✅ Added {len(result['added'])} videos")
        
        # Pause between chunks
        if i + chunk_size < total:
            time.sleep(2)
```

---

## Complete Example

```python
from googleapiclient.discovery import build
from playlist import PlaylistCreator, PlaylistManager

# Setup
youtube = build('youtube', 'v3', credentials=credentials)
creator = PlaylistCreator(youtube)
manager = PlaylistManager(youtube)

# Create playlist
print("Creating playlist...")
playlist = creator.create_playlist(
    title="Best of 2025",
    description="Top videos from 2025",
    privacy_status="public",
    tags=["2025", "best-of", "compilation"]
)

print(f"✅ Created: {playlist['url']}")
playlist_id = playlist['id']

# Add videos
videos = [
    "dQw4w9WgXcQ",
    "jNQXAC9IVRw",
    "9bZkp7q19f0"
]

print("Adding videos...")
result = manager.add_videos_batch(
    playlist_id=playlist_id,
    video_ids=videos,
    skip_duplicates=True,
    progress_callback=lambda c, t, v: print(f"  {c}/{t}: {v}")
)

print(f"✅ Added {len(result['added'])} videos")
print(f"❌ Failed: {len(result['failed'])}")

print(f"
🎉 Playlist ready: {playlist['url']}")
```

---

## Summary

The Playlist Management module provides:

✅ **Complete Control** - Full CRUD for playlists and videos  
✅ **Batch Operations** - Efficient bulk operations  
✅ **Error Handling** - Comprehensive error management  
✅ **Quota Optimization** - Smart rate limiting and duplicate detection  
✅ **Progress Tracking** - Real-time operation monitoring  
✅ **Validation** - Input validation at every step

**Total Code:** ~44KB across 4 files  
**Test Coverage:** Comprehensive error handling  
**Documentation:** Complete with examples

**Next Steps:** See [Phase 2.4](../README.md#phase-24) for Captions Management

---

*Part of YouTube MCP Server Phase 2.3 - Playlist Management*
