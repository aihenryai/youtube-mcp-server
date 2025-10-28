# 🚀 Installation Guide

Complete installation guide for YouTube MCP Server.

## 📋 Prerequisites

### Required
- **Python 3.12 or higher** ([Download](https://www.python.org/downloads/))
- **YouTube Data API v3 key** ([Get one here](https://console.cloud.google.com/apis/credentials))

### Recommended
- **Git** for cloning the repository
- **pip** for package management (included with Python)
- **Virtual environment** for isolated installation

## 🖥️ Installation Methods

### Method 1: Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/aihenryai/youtube-mcp-server.git
cd youtube-mcp-server

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and add your YOUTUBE_API_KEY
```

### Method 2: Manual Install

1. **Download** the repository as ZIP from GitHub
2. **Extract** to your preferred location
3. **Open Terminal** in the extracted directory
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Configure** environment variables (see Configuration section)

### Method 3: Using Virtual Environment (Best Practice)

```bash
# Clone repository
git clone https://github.com/aihenryai/youtube-mcp-server.git
cd youtube-mcp-server

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and add your YOUTUBE_API_KEY
```

## ⚙️ Configuration

### Step 1: Get YouTube API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable **YouTube Data API v3**
4. Go to **Credentials** → **Create Credentials** → **API Key**
5. Copy the API key

### Step 2: Configure Environment

Create `.env` file in the project root:

```env
# Required
YOUTUBE_API_KEY=your-api-key-here

# Optional - OAuth2 (for write operations)
USE_OAUTH2=false

# Optional - Server Settings
MCP_TRANSPORT=stdio
PORT=8080
LOG_LEVEL=INFO

# Optional - Performance
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
RATE_LIMIT_ENABLED=true
CALLS_PER_MINUTE=30
CALLS_PER_HOUR=1000
```

### Step 3: Test Installation

```bash
# Run the server
python server.py

# You should see:
# INFO - YouTube MCP Server Enhanced v2.0
# INFO - Transport: stdio
# INFO - Cache enabled: True
```

## 🔐 OAuth2 Setup (Optional)

For write operations like playlist management:

### Step 1: Get OAuth2 Credentials

1. In [Google Cloud Console](https://console.cloud.google.com)
2. Go to **APIs & Services** → **Credentials**
3. Click **Create Credentials** → **OAuth client ID**
4. Choose **Desktop app**
5. Download as `credentials.json`
6. Place in project root directory

### Step 2: Enable OAuth2

Edit `.env`:
```env
USE_OAUTH2=true
```

### Step 3: Authenticate

```bash
python authenticate.py auth
```

This will:
- Open browser for Google consent
- Save encrypted tokens
- Enable write operations

### Step 4: Verify

```bash
python authenticate.py status
```

## 🎮 Claude Desktop Integration

### Windows

1. **Locate config file**:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```

2. **Edit config** (or create if doesn't exist):
   ```json
   {
     "mcpServers": {
       "youtube": {
         "command": "python",
         "args": ["C:\\path\\to\\youtube-mcp-server\\server.py"],
         "env": {
           "YOUTUBE_API_KEY": "your-api-key-here"
         }
       }
     }
   }
   ```

3. **Replace path** with your actual installation path

4. **Restart Claude Desktop**

### macOS

1. **Locate config file**:
   ```bash
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

2. **Edit config**:
   ```json
   {
     "mcpServers": {
       "youtube": {
         "command": "python3",
         "args": ["/absolute/path/to/youtube-mcp-server/server.py"],
         "env": {
           "YOUTUBE_API_KEY": "your-api-key-here"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop**

### Linux

1. **Locate config file**:
   ```bash
   ~/.config/Claude/claude_desktop_config.json
   ```

2. **Edit config** (same as macOS)

3. **Restart Claude Desktop**

## 🐳 Docker Installation (Advanced)

### Using Pre-built Image

```bash
# Pull image (when available)
docker pull ghcr.io/aihenryai/youtube-mcp-server:latest

# Run container
docker run -d \
  -p 8080:8080 \
  -e YOUTUBE_API_KEY=your-key \
  -e MCP_TRANSPORT=http \
  --name youtube-mcp \
  ghcr.io/aihenryai/youtube-mcp-server:latest
```

### Building from Source

```bash
# Clone repository
git clone https://github.com/aihenryai/youtube-mcp-server.git
cd youtube-mcp-server

# Build image
docker build -t youtube-mcp .

# Run container
docker run -d \
  -p 8080:8080 \
  -e YOUTUBE_API_KEY=your-key \
  -e MCP_TRANSPORT=http \
  --name youtube-mcp \
  youtube-mcp
```

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  youtube-mcp:
    build: .
    ports:
      - "8080:8080"
    environment:
      - YOUTUBE_API_KEY=${YOUTUBE_API_KEY}
      - MCP_TRANSPORT=http
      - LOG_LEVEL=INFO
      - CACHE_ENABLED=true
    restart: unless-stopped
```

Run:
```bash
docker-compose up -d
```

## ✅ Verify Installation

### Test Basic Functionality

```bash
# Run server
python server.py
```

Expected output:
```
INFO - YouTube API client initialized successfully
INFO - YouTube MCP Server Enhanced v2.0
INFO - Transport: stdio
INFO - Cache enabled: True
INFO - Rate limiting enabled: True
```

### Test API Connection

Create `test_connection.py`:

```python
from server import get_video_info

result = get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(f"Success: {result.get('success')}")
print(f"Title: {result.get('title')}")
```

Run:
```bash
python test_connection.py
```

## 🔧 Troubleshooting

### Python Version Issues

**Error**: `Python 3.12+ required`

**Solution**:
```bash
# Check Python version
python --version

# If < 3.12, download from python.org
# Or use pyenv to manage versions
```

### Dependency Installation Fails

**Error**: `Could not install packages`

**Solution**:
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Try installing again
pip install -r requirements.txt

# If still fails, install manually
pip install fastmcp youtube-transcript-api google-api-python-client
```

### API Key Not Working

**Error**: `API key not found` or `Invalid API key`

**Solution**:
1. Check `.env` file exists
2. Verify `YOUTUBE_API_KEY` is set
3. Ensure YouTube Data API v3 is enabled in Google Cloud Console
4. Try regenerating the API key

### OAuth2 Authentication Issues

**Error**: `credentials.json not found`

**Solution**:
1. Download OAuth credentials from Google Cloud Console
2. Save as `credentials.json` in project root
3. Run `python authenticate.py auth`

### Port Already in Use (HTTP Mode)

**Error**: `Address already in use: 8080`

**Solution**:
```bash
# Change port in .env
PORT=8081

# Or kill process using the port (Windows)
netstat -ano | findstr :8080
taskkill /PID [PID] /F

# Or kill process (macOS/Linux)
lsof -ti:8080 | xargs kill -9
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'X'`

**Solution**:
```bash
# Ensure virtual environment is activated
# Then reinstall dependencies
pip install -r requirements.txt

# Or install specific package
pip install [package-name]
```

## 🔄 Updating

### Pull Latest Changes

```bash
# Navigate to project directory
cd youtube-mcp-server

# Pull updates
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart server
python server.py
```

### Version Check

```bash
# Check current version
python -c "from server import __version__; print(__version__)"
```

## 🗑️ Uninstallation

### Remove Installation

```bash
# If using virtual environment
deactivate
rm -rf venv

# Remove project directory
cd ..
rm -rf youtube-mcp-server
```

### Remove from Claude Desktop

Edit `claude_desktop_config.json` and remove the `youtube` entry.

## 📚 Next Steps

After installation:

1. **Read Quick Start** - [QUICKSTART.md](QUICKSTART.md)
2. **Explore Tools** - [README.md](README.md#-available-tools)
3. **Setup OAuth2** - [docs/OAUTH2_SETUP.md](docs/OAUTH2_SETUP.md)
4. **Deploy to Cloud** - [GOOGLE_CLOUD_DEPLOYMENT.md](GOOGLE_CLOUD_DEPLOYMENT.md)

## 💬 Need Help?

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/aihenryai/youtube-mcp-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/aihenryai/youtube-mcp-server/discussions)
- **Email**: henrystauber22@gmail.com

---

**Ready to use YouTube MCP Server! 🎉**
