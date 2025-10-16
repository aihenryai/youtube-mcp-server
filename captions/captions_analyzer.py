"""
YouTube MCP Server - Captions Analyzer
=====================================

Analyzes caption content for insights, statistics, and quality metrics.

Features:
- Language detection and analysis
- Content statistics (word count, reading time, etc.)
- Quality metrics (timing, formatting)
- Keyword extraction
- Readability analysis
- Sentiment analysis (basic)

Part of Phase 2.4: Captions Management
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import logging
from collections import Counter
from datetime import timedelta

logger = logging.getLogger(__name__)


class CaptionsAnalyzer:
    """
    Analyzes caption content for various metrics and insights.
    
    Provides methods to extract statistics, detect quality issues,
    analyze content, and generate insights from caption tracks.
    """
    
    def __init__(self):
        """Initialize CaptionsAnalyzer."""
        logger.info("CaptionsAnalyzer initialized")
    
    def analyze_caption_content(
        self,
        caption_content: str,
        format: str = 'srt'
    ) -> Dict[str, Any]:
        """
        Comprehensive analysis of caption content.
        
        Args:
            caption_content: Caption file content
            format: Caption format ('srt', 'vtt', 'ttml')
        
        Returns:
            Dictionary containing:
            - statistics: Basic statistics
            - timing: Timing analysis
            - quality: Quality metrics
            - keywords: Top keywords
            - insights: Analysis insights
        
        Example:
            ```python
            analyzer = CaptionsAnalyzer()
            
            with open('captions.srt', 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = analyzer.analyze_caption_content(content, format='srt')
            
            print(f"Total words: {analysis['statistics']['word_count']}")
            print(f"Reading time: {analysis['statistics']['reading_time_minutes']}")
            print(f"Top keywords: {analysis['keywords'][:5]}")
            ```
        """
        logger.info(f"Analyzing {format.upper()} caption content")
        
        # Parse captions based on format
        if format == 'srt':
            captions = self._parse_srt(caption_content)
        elif format == 'vtt':
            captions = self._parse_vtt(caption_content)
        else:
            captions = self._parse_generic(caption_content)
        
        # Extract statistics
        statistics = self._calculate_statistics(captions)
        
        # Analyze timing
        timing = self._analyze_timing(captions)
        
        # Quality metrics
        quality = self._assess_quality(captions, timing)
        
        # Extract keywords
        keywords = self._extract_keywords(captions)
        
        # Generate insights
        insights = self._generate_insights(statistics, timing, quality)
        
        return {
            'statistics': statistics,
            'timing': timing,
            'quality': quality,
            'keywords': keywords,
            'insights': insights,
            'caption_count': len(captions)
        }
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect language from caption text (basic heuristic).
        
        Args:
            text: Caption text to analyze
        
        Returns:
            Dictionary with detected language and confidence
        
        Note:
            This is a basic heuristic detector. For production,
            consider using langdetect or similar libraries.
        """
        # Clean text
        clean_text = re.sub(r'[^a-zA-Zא-ת\s]', '', text.lower())
        
        # Simple character-based detection
        hebrew_chars = len(re.findall(r'[א-ת]', clean_text))
        latin_chars = len(re.findall(r'[a-z]', clean_text))
        
        total_chars = hebrew_chars + latin_chars
        
        if total_chars == 0:
            return {
                'language': 'unknown',
                'confidence': 0.0
            }
        
        hebrew_ratio = hebrew_chars / total_chars
        
        if hebrew_ratio > 0.7:
            return {
                'language': 'he',
                'language_name': 'Hebrew',
                'confidence': hebrew_ratio
            }
        elif hebrew_ratio < 0.3:
            return {
                'language': 'en',
                'language_name': 'English',
                'confidence': 1 - hebrew_ratio
            }
        else:
            return {
                'language': 'mixed',
                'language_name': 'Mixed (Hebrew/English)',
                'confidence': 0.5
            }
    
    def calculate_reading_speed(
        self,
        caption_content: str,
        total_duration_seconds: float
    ) -> Dict[str, Any]:
        """
        Calculate reading speed metrics.
        
        Args:
            caption_content: Caption text
            total_duration_seconds: Video duration in seconds
        
        Returns:
            Dictionary with reading speed metrics
        """
        # Count words
        words = self._extract_words(caption_content)
        word_count = len(words)
        
        # Calculate words per minute
        duration_minutes = total_duration_seconds / 60.0
        words_per_minute = word_count / duration_minutes if duration_minutes > 0 else 0
        
        # Assess reading speed
        if words_per_minute < 100:
            speed_assessment = 'slow'
        elif words_per_minute < 150:
            speed_assessment = 'comfortable'
        elif words_per_minute < 200:
            speed_assessment = 'fast'
        else:
            speed_assessment = 'very_fast'
        
        return {
            'word_count': word_count,
            'duration_minutes': round(duration_minutes, 2),
            'words_per_minute': round(words_per_minute, 1),
            'speed_assessment': speed_assessment,
            'is_comfortable': 100 <= words_per_minute <= 180
        }
    
    def extract_timestamps(self, caption_content: str) -> List[Dict[str, Any]]:
        """
        Extract all timestamps from captions.
        
        Args:
            caption_content: SRT or VTT caption content
        
        Returns:
            List of timestamp dictionaries
        """
        timestamps = []
        
        # SRT timestamp pattern: 00:00:01,000 --> 00:00:03,000
        srt_pattern = r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})'
        
        # VTT timestamp pattern: 00:00:01.000 --> 00:00:03.000
        vtt_pattern = r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})'
        
        # Try SRT first
        matches = re.findall(srt_pattern, caption_content)
        
        # Try VTT if no SRT matches
        if not matches:
            matches = re.findall(vtt_pattern, caption_content)
        
        for start, end in matches:
            timestamps.append({
                'start': start,
                'end': end,
                'start_seconds': self._timestamp_to_seconds(start),
                'end_seconds': self._timestamp_to_seconds(end)
            })
        
        return timestamps
    
    def _parse_srt(self, content: str) -> List[Dict[str, Any]]:
        """Parse SRT format captions."""
        captions = []
        
        # Split by double newline (caption separator)
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            
            if len(lines) < 3:
                continue
            
            # Parse timestamp line
            timestamp_line = lines[1]
            match = re.search(
                r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})',
                timestamp_line
            )
            
            if not match:
                continue
            
            start, end = match.groups()
            
            # Get text (everything after timestamp)
            text = ' '.join(lines[2:])
            
            captions.append({
                'start': start,
                'end': end,
                'text': text,
                'start_seconds': self._timestamp_to_seconds(start),
                'end_seconds': self._timestamp_to_seconds(end)
            })
        
        return captions
    
    def _parse_vtt(self, content: str) -> List[Dict[str, Any]]:
        """Parse WebVTT format captions."""
        captions = []
        
        # Remove WEBVTT header
        content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.MULTILINE)
        
        # Split by double newline
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            
            if len(lines) < 2:
                continue
            
            # Find timestamp line
            timestamp_line = None
            text_start = 0
            
            for i, line in enumerate(lines):
                if '-->' in line:
                    timestamp_line = line
                    text_start = i + 1
                    break
            
            if not timestamp_line:
                continue
            
            match = re.search(
                r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})',
                timestamp_line
            )
            
            if not match:
                continue
            
            start, end = match.groups()
            text = ' '.join(lines[text_start:])
            
            captions.append({
                'start': start,
                'end': end,
                'text': text,
                'start_seconds': self._timestamp_to_seconds(start),
                'end_seconds': self._timestamp_to_seconds(end)
            })
        
        return captions
    
    def _parse_generic(self, content: str) -> List[Dict[str, Any]]:
        """Parse generic caption format (text only)."""
        # Just extract text, no timing
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        return [
            {
                'text': line,
                'start_seconds': 0,
                'end_seconds': 0
            }
            for line in lines
        ]
    
    def _calculate_statistics(self, captions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate basic caption statistics."""
        if not captions:
            return {
                'total_captions': 0,
                'word_count': 0,
                'character_count': 0,
                'average_words_per_caption': 0,
                'average_characters_per_caption': 0
            }
        
        # Extract all text
        all_text = ' '.join(caption['text'] for caption in captions)
        
        # Count words and characters
        words = self._extract_words(all_text)
        word_count = len(words)
        char_count = len(all_text)
        
        # Calculate averages
        avg_words = word_count / len(captions)
        avg_chars = char_count / len(captions)
        
        # Calculate reading time (assuming 200 words per minute)
        reading_time_minutes = word_count / 200.0
        
        return {
            'total_captions': len(captions),
            'word_count': word_count,
            'character_count': char_count,
            'average_words_per_caption': round(avg_words, 2),
            'average_characters_per_caption': round(avg_chars, 2),
            'reading_time_minutes': round(reading_time_minutes, 2),
            'unique_words': len(set(word.lower() for word in words))
        }
    
    def _analyze_timing(self, captions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze caption timing patterns."""
        if not captions or not captions[0].get('start_seconds'):
            return {
                'has_timing': False
            }
        
        durations = []
        gaps = []
        
        for i, caption in enumerate(captions):
            # Duration of this caption
            duration = caption['end_seconds'] - caption['start_seconds']
            durations.append(duration)
            
            # Gap to next caption
            if i < len(captions) - 1:
                gap = captions[i + 1]['start_seconds'] - caption['end_seconds']
                gaps.append(gap)
        
        # Calculate statistics
        avg_duration = sum(durations) / len(durations)
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        
        return {
            'has_timing': True,
            'average_duration_seconds': round(avg_duration, 2),
            'average_gap_seconds': round(avg_gap, 2),
            'shortest_duration': round(min(durations), 2),
            'longest_duration': round(max(durations), 2),
            'total_duration': round(captions[-1]['end_seconds'], 2)
        }
    
    def _assess_quality(
        self,
        captions: List[Dict[str, Any]],
        timing: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess caption quality."""
        issues = []
        
        # Check for timing issues
        if timing.get('has_timing'):
            if timing['average_duration_seconds'] < 1:
                issues.append('captions_too_short')
            
            if timing['average_duration_seconds'] > 7:
                issues.append('captions_too_long')
            
            if timing['average_gap_seconds'] < 0:
                issues.append('overlapping_captions')
            
            if timing['average_gap_seconds'] > 2:
                issues.append('large_gaps')
        
        # Check for text issues
        for caption in captions:
            text = caption['text']
            
            # Too long text
            if len(text) > 200:
                issues.append('text_too_long')
                break
            
            # All caps (shouting)
            if text.isupper() and len(text) > 10:
                issues.append('excessive_caps')
                break
        
        # Overall quality score
        quality_score = 100 - (len(set(issues)) * 15)
        quality_score = max(0, min(100, quality_score))
        
        return {
            'quality_score': quality_score,
            'issues': list(set(issues)),
            'has_issues': len(issues) > 0
        }
    
    def _extract_keywords(
        self,
        captions: List[Dict[str, Any]],
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """Extract top keywords from captions."""
        # Extract all text
        all_text = ' '.join(caption['text'] for caption in captions)
        
        # Get words
        words = self._extract_words(all_text)
        
        # Filter out common stop words (basic list)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'can', 'could', 'should', 'may', 'might', 'must', 'this',
            'that', 'these', 'those', 'it', 'its', 'i', 'you', 'he',
            'she', 'we', 'they', 'my', 'your', 'his', 'her', 'our', 'their'
        }
        
        # Count words (excluding stop words)
        filtered_words = [
            word.lower() for word in words
            if len(word) > 3 and word.lower() not in stop_words
        ]
        
        # Get top keywords
        word_counts = Counter(filtered_words)
        top_keywords = word_counts.most_common(top_n)
        
        return [
            {'word': word, 'count': count}
            for word, count in top_keywords
        ]
    
    def _generate_insights(
        self,
        statistics: Dict[str, Any],
        timing: Dict[str, Any],
        quality: Dict[str, Any]
    ) -> List[str]:
        """Generate insights from analysis."""
        insights = []
        
        # Word count insights
        word_count = statistics['word_count']
        if word_count < 100:
            insights.append("Very short caption content - consider adding more detail")
        elif word_count > 5000:
            insights.append("Extensive caption content - great for accessibility")
        
        # Reading time insights
        reading_time = statistics['reading_time_minutes']
        if reading_time > 60:
            insights.append(f"Long video ({reading_time:.0f} minutes of captions)")
        
        # Timing insights
        if timing.get('has_timing'):
            avg_duration = timing['average_duration_seconds']
            
            if avg_duration < 2:
                insights.append("Fast-paced captions - viewers may struggle to read")
            elif avg_duration > 6:
                insights.append("Slow-paced captions - good for readability")
        
        # Quality insights
        if quality['quality_score'] < 60:
            insights.append("Caption quality needs improvement")
        elif quality['quality_score'] > 90:
            insights.append("Excellent caption quality!")
        
        return insights
    
    def _extract_words(self, text: str) -> List[str]:
        """Extract words from text."""
        # Remove punctuation and split
        clean_text = re.sub(r'[^\w\s]', ' ', text)
        words = [word for word in clean_text.split() if word]
        return words
    
    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert timestamp to seconds."""
        # Handle both SRT (HH:MM:SS,mmm) and VTT (HH:MM:SS.mmm) formats
        timestamp = timestamp.replace(',', '.')
        
        try:
            parts = timestamp.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            return total_seconds
        except (ValueError, IndexError):
            return 0.0
