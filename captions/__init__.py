"""
YouTube MCP Server - Captions Management
========================================

Comprehensive caption track management for YouTube videos.

Modules:
- CaptionsManager: List, download, upload, update, delete caption tracks
- CaptionsAnalyzer: Analyze caption content, detect languages, extract insights

Part of Phase 2.4: Captions Management
"""

from .captions_manager import CaptionsManager
from .captions_analyzer import CaptionsAnalyzer

__all__ = [
    'CaptionsManager',
    'CaptionsAnalyzer'
]
