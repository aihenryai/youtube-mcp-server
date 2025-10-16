# YouTube MCP Server - Captions Management

Complete guide for managing YouTube captions/subtitles using the MCP server.

## 📑 Table of Contents

1. [Overview](#overview)
2. [Setup](#setup)
3. [Listing Captions](#listing-captions)
4. [Uploading Captions](#uploading-captions)
5. [Downloading Captions](#downloading-captions)
6. [Updating Captions](#updating-captions)
7. [Deleting Captions](#deleting-captions)
8. [Caption Analysis](#caption-analysis)
9. [Supported Formats](#supported-formats)
10. [Quota Management](#quota-management)
11. [Best Practices](#best-practices)

---

## Overview

The Captions Management module provides comprehensive control over YouTube caption tracks:

- **CaptionsManager** - CRUD operations for caption tracks
- **CaptionsAnalyzer** - Content analysis and quality metrics

### Features

✅ List available caption tracks  
✅ Upload new caption files (SRT, VTT, TTML, SBV, SUB)  
✅ Download existing captions in multiple formats  
✅ Update caption content or metadata  
✅ Delete caption tracks  
✅ Analyze caption quality and statistics  
✅ Extract keywords and insights  
✅ Language detection (basic)

---

## Setup

### Prerequisites

```python
from googleapiclient.discovery import build
from captions import CaptionsManager, CaptionsAnalyzer

# OAuth2 required for upload/update/delete operations
# API key sufficient for list/download operations

youtube = build('youtube', 'v3', credentials=credentials)
manager = CaptionsManager(youtube)
analyzer = CaptionsAnalyzer()
```

### Required Scopes

For full functionality:
```python
SCOPES = [
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtubepartner'
]
```

---

## Listing Captions

### List All Caption Tracks

```python
# List all captions for a video
result = manager.list_captions("dQw4w9WgXcQ")

print(f"Found {result['total_count']} caption tracks")
print(f"Languages: {result['languages']}")

for track in result['tracks']:
    print(f"- {track['language']}: {track['name']}")
    print(f"  Auto-generated: {track['is_auto_generated']}")
    print(f"  Status: {track['status']}")
```

**Output:**
```python
{
    'video_id': 'dQw4w9WgXcQ',
    'tracks': [
        {
            'id': 'SwPG123abc',
            'language': 'en',
            'name': 'English',
            'track_kind': 'standard',
            'is_auto_generated': False,
            'is_cc': True,
            'is_draft': False,
            'status': 'serving'
        },
        {
            'id': 'SwPG456def',
            'language': 'he',
            'name': 'Hebrew',
            'track_kind': 'standard',
            'is_auto_generated': False,
            'status': 'serving'
        }
    ],
    'total_count': 2,
    'languages': ['en', 'he']
}
```

**Quota Cost:** 50 units

### Filter Options

```python
# Exclude auto-generated captions
result = manager.list_captions(
    video_id="dQw4w9WgXcQ",
    include_auto_generated=False
)
```

---

## Uploading Captions

### Upload New Caption Track

```python
# Upload Hebrew captions
result = manager.upload_caption(
    video_id="dQw4w9WgXcQ",
    caption_file="/path/to/hebrew_captions.srt",
    language="he",
    name="Hebrew Subtitles"
)

print(f"✅ Caption uploaded: {result['caption_id']}")
print(f"Format detected: {result['format']}")
```

**Quota Cost:** 400 units (expensive!)

### Upload as Draft

```python
# Upload without publishing
result = manager.upload_caption(
    video_id="dQw4w9WgXcQ",
    caption_file="/path/to/captions.srt",
    language="en",
    name="English Draft",
    is_draft=True  # Not visible to viewers
)
```

### Supported Languages

Common ISO 639-1 codes:
- **en** - English
- **he** - Hebrew
- **ar** - Arabic
- **es** - Spanish
- **fr** - French
- **de** - German
- **ja** - Japanese
- **ko** - Korean
- **zh** - Chinese

[Full list](https://www.loc.gov/standards/iso639-2/php/code_list.php)

---

## Downloading Captions

### Download to File

```python
# Download caption track
result = manager.download_caption(
    caption_id="SwPG123abc",
    output_file="/path/to/save/captions.srt",
    format="srt"
)

print(f"Downloaded to: {result['file_path']}")
print(f"Size: {result['size_bytes']} bytes")
```

### Download to Memory

```python
# Get caption content directly
result = manager.download_caption(
    caption_id="SwPG123abc",
    format="srt"
)

caption_text = result['content']
print(caption_text)
```

**Quota Cost:** 200 units

### Format Conversion

```python
# Download same caption in different formats
for fmt in ['srt', 'vtt', 'ttml']:
    result = manager.download_caption(
        caption_id="SwPG123abc",
        output_file=f"/path/captions.{fmt}",
        format=fmt
    )
```

---

## Updating Captions

### Update Caption Content

```python
# Update caption file
result = manager.update_caption(
    caption_id="SwPG123abc",
    caption_file="/path/to/updated_captions.srt"
)

print(f"✅ Caption updated")
```

**Quota Cost:** 450 units (very expensive!)

### Update Metadata Only

```python
# Change caption name
result = manager.update_caption(
    caption_id="SwPG123abc",
    name="Updated Caption Title"
)

# Publish draft caption
result = manager.update_caption(
    caption_id="SwPG123abc",
    is_draft=False  # Make visible
)
```

### Combined Update

```python
# Update both content and metadata
result = manager.update_caption(
    caption_id="SwPG123abc",
    caption_file="/path/to/new_content.srt",
    name="Revised Captions",
    is_draft=False
)
```

---

## Deleting Captions

### Delete Caption Track

```python
result = manager.delete_caption("SwPG123abc")

print(result['message'])  # "Caption deleted successfully"
```

**Quota Cost:** 50 units

### Important Notes

- ❌ Cannot delete auto-generated captions (ASR)
- ⚠️ Requires video owner authentication
- ⚠️ Deletion is permanent

```python
try:
    manager.delete_caption("auto_generated_id")
except ValueError as e:
    print(e)  # "Cannot delete auto-generated captions"
```

---

## Caption Analysis

### Analyze Caption Quality

```python
analyzer = CaptionsAnalyzer()

# Download caption content
result = manager.download_caption("SwPG123abc")

# Analyze
analysis = analyzer.analyze_caption_content(
    caption_content=result['content'],
    format='srt'
)

# View results
print(f"Word count: {analysis['statistics']['word_count']}")
print(f"Reading time: {analysis['statistics']['reading_time_minutes']} min")
print(f"Quality score: {analysis['quality']['quality_score']}/100")
print(f"Issues: {analysis['quality']['issues']}")
```

**Output:**
```python
{
    'statistics': {
        'total_captions': 250,
        'word_count': 1500,
        'character_count': 8000,
        'average_words_per_caption': 6.0,
        'reading_time_minutes': 7.5,
        'unique_words': 450
    },
    'timing': {
        'has_timing': True,
        'average_duration_seconds': 3.5,
        'average_gap_seconds': 0.2,
        'total_duration': 900.0
    },
    'quality': {
        'quality_score': 85,
        'issues': ['captions_too_short'],
        'has_issues': True
    },
    'keywords': [
        {'word': 'machine', 'count': 45},
        {'word': 'learning', 'count': 42},
        {'word': 'model', 'count': 38}
    ],
    'insights': [
        'Fast-paced captions - viewers may struggle to read',
        'Extensive caption content - great for accessibility'
    ]
}
```

**Quota Cost:** 0 units (local analysis)

### Reading Speed Analysis

```python
# Calculate reading speed
result = analyzer.calculate_reading_speed(
    caption_content=caption_text,
    total_duration_seconds=600  # 10 minutes
)

print(f"Words per minute: {result['words_per_minute']}")
print(f"Speed assessment: {result['speed_assessment']}")
print(f"Comfortable pace: {result['is_comfortable']}")
```

### Language Detection

```python
# Detect language (basic)
result = analyzer.detect_language(caption_text)

print(f"Detected: {result['language_name']}")
print(f"Confidence: {result['confidence']:.2%}")
```

---

## Supported Formats

### Input Formats (Upload)

All major caption formats:

1. **SRT (SubRip)** - Most common
   ```srt
   1
   00:00:01,000 --> 00:00:03,000
   Hello world!
   ```

2. **VTT (WebVTT)** - Web standard
   ```vtt
   WEBVTT

   00:00:01.000 --> 00:00:03.000
   Hello world!
   ```

3. **TTML (Timed Text Markup Language)** - XML-based

4. **SBV (YouTube SubViewer)**

5. **SUB (MicroDVD)**

### Output Formats (Download)

Same formats as input - convert between any formats!

---

## Quota Management

### Daily Quota: 10,000 units

### Operation Costs

| Operation | Cost (units) | Notes |
|-----------|-------------|-------|
| List captions | 50 | Cached |
| Download caption | 200 | Cacheable |
| Upload caption | **400** | Expensive! |
| Update caption | **450** | Very expensive! |
| Delete caption | 50 | - |
| Analyze caption | 0 | Local only |

### Quota Optimization

```python
# ❌ Bad: Download same caption multiple times
for i in range(10):
    caption = manager.download_caption("SwPG123abc")
# Cost: 2,000 units!

# ✅ Good: Download once, analyze many times
caption = manager.download_caption("SwPG123abc")
for analysis_type in ['quality', 'keywords', 'timing']:
    result = analyzer.analyze_caption_content(caption['content'])
# Cost: 200 units
```

---

## Best Practices

### 1. Caption File Preparation

```python
# Validate caption file before upload
import os

def validate_caption_file(file_path):
    """Pre-upload validation"""
    # Check file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Caption file not found: {file_path}")
    
    # Check file size (max 100MB)
    size_mb = os.path.getsize(file_path) / 1024 / 1024
    if size_mb > 100:
        raise ValueError(f"Caption file too large: {size_mb:.1f}MB (max 100MB)")
    
    # Check format
    ext = file_path.rsplit('.', 1)[-1].lower()
    if ext not in ['srt', 'vtt', 'ttml', 'sbv', 'sub']:
        raise ValueError(f"Unsupported format: {ext}")
    
    return True

# Use it
validate_caption_file("/path/to/captions.srt")
result = manager.upload_caption(...)
```

### 2. Error Handling

```python
def safe_upload_caption(manager, video_id, caption_file, language):
    """Upload with comprehensive error handling"""
    try:
        result = manager.upload_caption(
            video_id=video_id,
            caption_file=caption_file,
            language=language
        )
        logger.info(f"✅ Caption uploaded: {result['caption_id']}")
        return result
    
    except ValueError as e:
        if "duplicate" in str(e).lower():
            logger.warning(f"Caption already exists for {language}")
            # Try updating instead
            return update_existing_caption(...)
        else:
            logger.error(f"Validation error: {e}")
            raise
    
    except HttpError as e:
        if e.resp.status == 403:
            logger.error("Permission denied - check OAuth2 authentication")
        else:
            logger.error(f"Upload failed: {e}")
        raise
```

### 3. Bulk Operations

```python
def upload_multiple_captions(manager, video_id, caption_files):
    """Upload captions in multiple languages"""
    results = []
    
    for lang, file_path in caption_files.items():
        try:
            result = manager.upload_caption(
                video_id=video_id,
                caption_file=file_path,
                language=lang,
                name=f"{lang.upper()} Captions"
            )
            results.append(result)
            
            # Rate limiting - wait between uploads
            import time
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Failed to upload {lang}: {e}")
            results.append({'language': lang, 'error': str(e)})
    
    return results

# Usage
captions = {
    'en': '/path/to/english.srt',
    'he': '/path/to/hebrew.srt',
    'es': '/path/to/spanish.srt'
}

results = upload_multiple_captions(manager, video_id, captions)
```

### 4. Quality Assurance

```python
def qa_caption_file(analyzer, caption_file):
    """Quality check before upload"""
    with open(caption_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    analysis = analyzer.analyze_caption_content(content, format='srt')
    
    issues = []
    
    # Check quality score
    if analysis['quality']['quality_score'] < 70:
        issues.append(f"Low quality score: {analysis['quality']['quality_score']}")
    
    # Check for specific issues
    if 'captions_too_short' in analysis['quality']['issues']:
        issues.append("Captions display too quickly")
    
    if 'large_gaps' in analysis['quality']['issues']:
        issues.append("Large gaps between captions")
    
    # Check reading speed
    if analysis['timing']['average_duration_seconds'] < 1.5:
        issues.append("Reading speed too fast")
    
    return {
        'ready_for_upload': len(issues) == 0,
        'issues': issues,
        'quality_score': analysis['quality']['quality_score']
    }

# Use it
qa_result = qa_caption_file(analyzer, "/path/to/captions.srt")

if qa_result['ready_for_upload']:
    manager.upload_caption(...)
else:
    print(f"⚠️ Issues found: {qa_result['issues']}")
```

---

## Complete Example

```python
from googleapiclient.discovery import build
from captions import CaptionsManager, CaptionsAnalyzer
import logging

# Setup
logging.basicConfig(level=logging.INFO)
youtube = build('youtube', 'v3', credentials=credentials)
manager = CaptionsManager(youtube)
analyzer = CaptionsAnalyzer()

video_id = "dQw4w9WgXcQ"

# 1. Check existing captions
print("📋 Listing existing captions...")
existing = manager.list_captions(video_id)
print(f"Found {existing['total_count']} caption tracks")

# 2. Quality check caption file
print("
🔍 Checking caption quality...")
qa_result = qa_caption_file(analyzer, "/path/to/new_captions.srt")

if not qa_result['ready_for_upload']:
    print(f"⚠️ Quality issues: {qa_result['issues']}")
    # Fix issues manually or programmatically

# 3. Upload new caption
print("
⬆️ Uploading caption...")
result = manager.upload_caption(
    video_id=video_id,
    caption_file="/path/to/new_captions.srt",
    language="he",
    name="Hebrew Subtitles"
)

print(f"✅ Uploaded: {result['caption_id']}")

# 4. Verify upload
print("
✓ Verifying...")
updated_list = manager.list_captions(video_id)
print(f"Total captions now: {updated_list['total_count']}")

print("
🎉 Caption management complete!")
```

---

## Summary

The Captions Management module provides:

✅ **Complete Control** - Full CRUD for caption tracks  
✅ **Multi-Format Support** - SRT, VTT, TTML, SBV, SUB  
✅ **Quality Analysis** - Automatic quality checking  
✅ **Bulk Operations** - Process multiple captions  
✅ **Format Conversion** - Convert between formats  
✅ **Zero-Cost Analysis** - Local caption analysis

**Total Code:** ~1,068 lines  
**Test Coverage:** Comprehensive validation  
**Documentation:** Complete with examples

---

*Part of YouTube MCP Server Phase 2.4 - Captions Management*
