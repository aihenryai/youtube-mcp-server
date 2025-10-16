# OAuth2 Authentication Guide

## Overview

This guide explains how to set up and use OAuth2 authentication for the YouTube MCP Server, enabling write operations like playlist management, video uploads, and more.

## 🎯 Why OAuth2?

YouTube Data API requires OAuth2 for operations that modify user data:
- ✅ Create/edit/delete playlists
- ✅ Upload/update/delete videos
- ✅ Manage captions
- ✅ Update channel settings
- ❌ Read-only operations (can use API key)

## 📋 Prerequisites

1. **Google Cloud Project** with YouTube Data API v3 enabled
2. **OAuth 2.0 Client ID** (Desktop application type)
3. **Python 3.12+** with required packages

## 🚀 Setup Steps

### Step 1: Create OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable **YouTube Data API v3**:
   - APIs & Services → Enable APIs and Services
   - Search for "YouTube Data API v3"
   - Click Enable

4. Create OAuth 2.0 Client ID:
   - APIs & Services → Credentials
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: **Desktop app**
   - Name: "YouTube MCP Server"
   - Click Create

5. Download the credentials:
   - Click the download button (⬇️)
   - Save as `credentials.json` in the server directory

### Step 2: Configure OAuth Consent Screen

⚠️ **Important**: Your app must have a configured consent screen.

1. Go to APIs & Services → OAuth consent screen
2. Choose **External** (unless you have Google Workspace)
3. Fill in required fields:
   - App name: "YouTube MCP Server"
   - User support email: your email
   - Developer contact: your email
4. Add scopes (optional, we'll request them dynamically)
5. Add test users if app is in "Testing" mode

### Step 3: Install Dependencies

```bash
pip install cryptography
```

(Already in requirements.txt if you did `pip install -r requirements.txt`)

### Step 4: Run Authentication

```bash
# Full access (recommended)
python authenticate.py auth

# Read-only access
python authenticate.py auth --scope readonly

# Upload only
python authenticate.py auth --scope upload
```

**What happens:**
1. Browser opens to Google consent page
2. You sign in with your Google account
3. Grant permissions to the app
4. Token is saved encrypted to `token.json`
5. Done! ✅

## 🔐 Security Features

### Token Encryption
- Tokens stored with **AES-256 encryption** (Fernet)
- Encryption key derived from machine ID
- Key stored in `token.key` (600 permissions)
- Token stored in `token.json.encrypted`

### File Permissions
```
-rw------- token.json    # Owner read/write only
-rw------- token.key     # Owner read/write only
```

### Auto-Refresh
- Tokens auto-refresh before expiry
- No manual intervention needed
- Refresh token stored securely

## 🛠️ CLI Commands

### Authenticate
```bash
# First time or re-authenticate
python authenticate.py auth

# Force re-authentication (even if valid token exists)
python authenticate.py auth --force

# Authenticate with specific scope
python authenticate.py auth --scope readonly
```

### Check Status
```bash
python authenticate.py status
```

**Output:**
```
📊 Authentication Status
============================================================
✅ Authenticated: True
   Valid: True
   Expired: False
   Has refresh token: True

⏰ Token Expiry: 2025-10-13T12:30:00
   Time remaining: 23.5 hours

🔑 Scopes:
   - https://www.googleapis.com/auth/youtube
   - https://www.googleapis.com/auth/youtube.force-ssl
```

### Test Connection
```bash
python authenticate.py test
```

**Output:**
```
🧪 Testing YouTube API connection...
============================================================
Fetching your channel info...

✅ Connection successful!
============================================================
Channel: Your Channel Name
Subscribers: 1234
Videos: 56
Views: 78900

💡 Your YouTube MCP Server is ready to use!
```

### Revoke Authentication
```bash
python authenticate.py revoke
```

Deletes token and revokes access.

## 📊 OAuth2 Scopes

### Readonly (`--scope readonly`)
```
https://www.googleapis.com/auth/youtube.readonly
```
- View channel analytics
- Read playlists
- Read video metadata
- **Cannot** modify anything

### Upload (`--scope upload`)
```
https://www.googleapis.com/auth/youtube.upload
```
- Upload videos
- Update video metadata
- **Cannot** manage playlists or other features

### Full (`--scope full`, default)
```
https://www.googleapis.com/auth/youtube
https://www.googleapis.com/auth/youtube.force-ssl
```
- **Everything** - full access to your YouTube account
- Recommended for MCP server usage

## 🔧 Programmatic Usage

### In Python Code

```python
from auth import OAuth2Manager

# Initialize
oauth = OAuth2Manager(
    credentials_file='credentials.json',
    scopes=OAuth2Manager.SCOPES['full']
)

# Authenticate (opens browser first time)
creds = oauth.authorize()

# Get authenticated service
youtube = oauth.get_authenticated_service()

# Use the API
response = youtube.playlists().list(
    part='snippet',
    mine=True
).execute()
```

### In MCP Server

```python
# server.py
from auth import OAuth2Manager

# Initialize OAuth2
oauth_manager = OAuth2Manager()

# Authenticate (if not already)
oauth_manager.authorize()

# Get authenticated service
youtube = oauth_manager.get_authenticated_service()

# Now use with playlist tools
@mcp.tool()
def create_playlist(title: str, ...):
    # youtube variable already has valid credentials
    response = youtube.playlists().insert(...)
    return response
```

## ⚠️ Troubleshooting

### "credentials.json not found"
**Solution:** Download OAuth2 credentials from Google Cloud Console and save as `credentials.json` in server directory.

### "Redirect URI mismatch"
**Cause:** OAuth client type is wrong (should be "Desktop app", not "Web app")  
**Solution:** Create new OAuth client as Desktop application type.

### "Access blocked: Authorization Error"
**Causes:**
1. App is in "Testing" mode and you're not a test user
2. OAuth consent screen not configured
3. YouTube Data API not enabled

**Solutions:**
1. Add your Google account as test user in OAuth consent screen
2. Complete OAuth consent screen configuration
3. Enable YouTube Data API v3 in APIs & Services

### "Token expired" / "Refresh failed"
**Solution:** Re-authenticate:
```bash
python authenticate.py auth --force
```

### "Permission denied" on token files
**Solution:** Fix file permissions:
```bash
chmod 600 token.json token.key
```

## 🔄 Token Lifecycle

1. **First Auth**: User consents in browser → Token saved
2. **Usage**: Server uses token for API calls
3. **Auto-Refresh**: Token refreshes automatically before expiry
4. **Expiry**: Access token expires (1 hour), refresh extends it
5. **Revoke**: User can revoke anytime

**Token Lifespan:**
- Access Token: ~1 hour
- Refresh Token: Long-lived (until revoked)
- Auto-refresh: Happens automatically

## 🎓 Best Practices

### Development
✅ Use `--scope readonly` for testing  
✅ Test with `authenticate.py test`  
✅ Check status before operations  
❌ Don't commit `credentials.json`  
❌ Don't commit `token.json` or `token.key`

### Production
✅ Store credentials securely (env vars or secrets manager)  
✅ Use `.gitignore` for sensitive files  
✅ Monitor token expiry  
✅ Implement error handling for auth failures  
❌ Never share credentials or tokens

### .gitignore Entry
```
credentials.json
token.json
token.key
*.key
```

## 📚 Additional Resources

- [YouTube Data API Reference](https://developers.google.com/youtube/v3/docs)
- [OAuth 2.0 Guide](https://developers.google.com/identity/protocols/oauth2)
- [Google API Client Library](https://github.com/googleapis/google-api-python-client)
- [OAuth Consent Screen Setup](https://support.google.com/cloud/answer/10311615)

## 💬 Support

If you encounter issues:
1. Check this guide's troubleshooting section
2. Verify all prerequisites are met
3. Check server logs for detailed errors
4. Open an issue on GitHub with error details

---

**Security Note:** Your OAuth2 credentials and tokens grant access to your YouTube account. Keep them secure and never share them publicly.
