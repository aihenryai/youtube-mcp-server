# Contributing to YouTube MCP Server

Thank you for your interest in contributing to the YouTube MCP Server! This document provides guidelines and instructions for contributing to this project.

## 🤝 Ways to Contribute

- **🐛 Bug Reports**: Report issues and bugs
- **✨ Feature Requests**: Suggest new features or improvements
- **📝 Documentation**: Improve or add documentation
- **🔧 Code**: Submit bug fixes or new features
- **🧪 Testing**: Add or improve test coverage
- **🌍 Translations**: Help translate documentation

## 📋 Before You Start

1. **Check existing issues** to avoid duplicates
2. **Read the documentation** to understand the project
3. **Review the code of conduct** (see below)
4. **Set up your development environment**

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/youtube-mcp-server.git
cd youtube-mcp-server
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock black flake8 mypy
```

### 3. Configure API Keys

```bash
# Copy environment template
cp .env.example .env

# Add your YouTube API key
echo "YOUTUBE_API_KEY=your-test-api-key" >> .env
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_server.py -v
```

## 🔧 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

**Branch naming conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `test/` - Test improvements
- `refactor/` - Code refactoring

### 2. Make Your Changes

- Follow the code style guidelines (see below)
- Write clear commit messages
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run tests
pytest

# Run linters
black .
flake8 .
mypy .

# Check security
bandit -r . -ll
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

**Commit message format:**
```
<type>: <subject>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title and description
- Reference to related issues
- Screenshots (if applicable)
- Test results

## 📝 Code Style Guidelines

### Python Code

**Follow PEP 8** with these specifics:

```python
# Use type hints
def get_video_info(video_url: str) -> Dict[str, Any]:
    pass

# Use descriptive names
video_metadata = get_video_info(url)  # Good
data = get_info(url)                  # Bad

# Document functions with docstrings
def search_videos(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Search for YouTube videos.
    
    Args:
        query: Search query string
        max_results: Maximum number of results (1-50)
    
    Returns:
        Dictionary with search results
    """
    pass

# Use constants for magic values
MAX_COMMENT_LENGTH = 10000
DEFAULT_CACHE_TTL = 3600

# Handle errors gracefully
try:
    result = api_call()
except HttpError as e:
    logger.error(f"API error: {e}")
    return {"success": False, "error": str(e)}
```

### Code Organization

```python
# 1. Standard library imports
import os
import logging
from typing import Optional, Dict, Any

# 2. Third-party imports
from fastmcp import FastMCP
from googleapiclient.errors import HttpError

# 3. Local imports
from utils import cached, rate_limited
from config import config
```

### Formatting

Use **Black** for code formatting:

```bash
# Format all Python files
black .

# Check without making changes
black --check .
```

### Linting

Use **Flake8** for linting:

```bash
# Run linter
flake8 .

# With specific rules
flake8 --max-line-length=88 --extend-ignore=E203,W503 .
```

### Type Checking

Use **MyPy** for type checking:

```bash
# Type check
mypy .

# Strict mode
mypy --strict .
```

## 🧪 Testing Guidelines

### Writing Tests

```python
import pytest
from unittest.mock import Mock, patch

def test_get_video_info_success():
    """Test successful video info retrieval."""
    # Arrange
    video_id = "test_video_id"
    mock_response = {"items": [{"id": video_id}]}
    
    # Act
    with patch("youtube.videos") as mock_videos:
        mock_videos.list.return_value.execute.return_value = mock_response
        result = get_video_info(video_id)
    
    # Assert
    assert result["success"] is True
    assert result["video_id"] == video_id

def test_get_video_info_not_found():
    """Test video not found scenario."""
    with patch("youtube.videos") as mock_videos:
        mock_videos.list.return_value.execute.return_value = {"items": []}
        result = get_video_info("invalid_id")
    
    assert result["success"] is False
    assert "not found" in result["error"].lower()
```

### Test Coverage

- Aim for **80%+ coverage** for new code
- Test both success and failure cases
- Test edge cases and boundary conditions
- Mock external dependencies (API calls)

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_server.py

# Run with coverage
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

## 🔒 Security Guidelines

### Input Validation

Always validate user input:

```python
from utils.validators import validate_video_url, validate_language

def process_video(video_url: str, language: str = "en"):
    # Validate inputs
    video_id = validate_video_url(video_url)
    language = validate_language(language)
    
    # Process safely
    result = fetch_data(video_id, language)
    return result
```

### Sensitive Data

**Never commit:**
- API keys (`.env`)
- OAuth credentials (`credentials.json`)
- Tokens (`token.json`)
- Private keys (`*.key`)

Use `.gitignore` to exclude these files.

### Security Checks

```bash
# Run Bandit security scanner
bandit -r . -ll

# Check dependencies for vulnerabilities
pip-audit

# Update dependencies
pip list --outdated
```

## 📚 Documentation Guidelines

### Code Documentation

```python
def complex_function(param1: str, param2: int, option: bool = False) -> Dict[str, Any]:
    """
    Brief one-line description.
    
    Longer description explaining what the function does,
    any important behavior, and potential side effects.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        option: Description of optional parameter (default: False)
    
    Returns:
        Dictionary containing:
        - key1: Description
        - key2: Description
    
    Raises:
        ValueError: When param2 is negative
        HttpError: When API call fails
    
    Example:
        >>> result = complex_function("test", 42, option=True)
        >>> print(result["key1"])
        'value'
    """
    pass
```

### README Updates

When adding features, update:
- Feature list
- Usage examples
- Configuration options
- Troubleshooting section

### Changelog

Add entries to README.md changelog:

```markdown
### v2.3 (YYYY-MM-DD)
- ✨ Added new feature X
- 🐛 Fixed bug Y
- 📝 Updated documentation for Z
```

## 🎯 Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] No sensitive data committed
- [ ] Branch is up to date with main
- [ ] PR description is clear and complete

## 🐛 Bug Report Template

When reporting bugs, include:

```markdown
**Description**
A clear description of the bug.

**Steps to Reproduce**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What you expected to happen.

**Actual Behavior**
What actually happened.

**Environment**
- OS: [e.g., Windows 11, macOS 14, Ubuntu 22.04]
- Python version: [e.g., 3.12.0]
- Server version: [e.g., v2.2]
- Transport mode: [stdio/http]

**Additional Context**
- Error messages
- Log output
- Screenshots
- Configuration files (redact sensitive data)
```

## ✨ Feature Request Template

When requesting features, include:

```markdown
**Problem Statement**
What problem does this solve?

**Proposed Solution**
Describe your proposed solution.

**Alternatives Considered**
Other approaches you've considered.

**Additional Context**
- Use cases
- Expected behavior
- Mockups/examples
```

## 📞 Getting Help

If you need help:

1. **Check the documentation** - [docs/](docs/)
2. **Search existing issues** - [Issues](https://github.com/aihenryai/youtube-mcp-server/issues)
3. **Ask in discussions** - [Discussions](https://github.com/aihenryai/youtube-mcp-server/discussions)
4. **Contact maintainer** - [henrystauber22@gmail.com](mailto:henrystauber22@gmail.com)

## 📜 Code of Conduct

### Our Pledge

We pledge to make participation in this project a harassment-free experience for everyone, regardless of:
- Age, body size, disability, ethnicity
- Gender identity and expression
- Level of experience, education
- Nationality, personal appearance, race, religion
- Sexual identity and orientation

### Our Standards

**Positive behavior:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards others

**Unacceptable behavior:**
- Trolling, insulting comments, personal attacks
- Public or private harassment
- Publishing others' private information
- Other conduct reasonably considered inappropriate

### Enforcement

Violations may result in:
1. **Warning** - First offense
2. **Temporary ban** - Repeated offenses
3. **Permanent ban** - Severe or continued violations

Report violations to: [henrystauber22@gmail.com](mailto:henrystauber22@gmail.com)

## 🏆 Recognition

Contributors will be recognized in:
- README.md acknowledgments section
- Release notes
- Project documentation

Significant contributors may be invited to become maintainers.

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to YouTube MCP Server! 🎉**
