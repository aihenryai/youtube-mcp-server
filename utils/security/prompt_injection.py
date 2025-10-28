"""
Prompt Injection Detector
Detects potential prompt injection attempts in user inputs
"""

import re
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class PromptInjectionDetector:
    """
    Detect potential prompt injection attempts in user inputs
    
    Based on:
    - MCP Security Research 2025
    - OWASP Top 10 for LLMs
    - Known attack patterns
    """
    
    # Patterns that indicate prompt injection attempts
    CRITICAL_PATTERNS = [
        (r'ignore\s+(all\s+)?(previous|prior|earlier)\s+(instructions?|commands?|prompts?)', 'ignore_previous'),
        (r'forget\s+(everything|all|previous|prior)', 'forget_command'),
        (r'from\s+now\s+on', 'from_now_on'),
        (r'you\s+are\s+now', 'identity_override'),
        (r'always\s+(respond|say|return|output|do)', 'always_directive'),
        (r'never\s+(respond|say|return|output|do)', 'never_directive'),
        (r'\[system\]|\[instruction\]|\[admin\]', 'system_tags'),
        (r'system:\s*|instruction:\s*|admin:\s*', 'system_prefix'),
    ]
    
    SUSPICIOUS_PATTERNS = [
        (r'<\s*script', 'script_tag'),
        (r'javascript:', 'javascript_protocol'),
        (r'onerror\s*=', 'event_handler'),
        (r'eval\s*\(', 'eval_function'),
        (r'exec\s*\(', 'exec_function'),
        (r'__import__', 'import_function'),
        (r'\.\./', 'path_traversal'),
        (r'\.\./\.\./\.\.]/', 'path_traversal_deep'),
    ]
    
    # Unicode tricks
    UNICODE_TRICKS = [
        ('\u200B', 'zero_width_space'),
        ('\u200C', 'zero_width_non_joiner'),
        ('\u200D', 'zero_width_joiner'),
        ('\uFEFF', 'zero_width_no_break_space'),
        ('\u202E', 'right_to_left_override'),
    ]
    
    @classmethod
    def detect(
        cls,
        text: str,
        strict: bool = False
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Detect prompt injection attempts
        
        Args:
            text: Text to analyze
            strict: If True, also flag suspicious patterns
        
        Returns:
            (is_injection, pattern_type, details)
        """
        if not text or not isinstance(text, str):
            return False, None, None
        
        text_lower = text.lower()
        
        # Check critical patterns
        for pattern, pattern_type in cls.CRITICAL_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(
                    f"🚨 Prompt injection detected: {pattern_type}"
                )
                return True, pattern_type, f"Matched pattern: {pattern}"
        
        # Check suspicious patterns (if strict mode)
        if strict:
            for pattern, pattern_type in cls.SUSPICIOUS_PATTERNS:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    logger.warning(
                        f"⚠️  Suspicious pattern detected: {pattern_type}"
                    )
                    return True, pattern_type, f"Matched pattern: {pattern}"
        
        # Check for Unicode tricks
        for char, trick_type in cls.UNICODE_TRICKS:
            if char in text:
                logger.warning(
                    f"⚠️  Unicode obfuscation detected: {trick_type}"
                )
                return True, trick_type, "Unicode obfuscation attempt"
        
        return False, None, None
    
    @classmethod
    def sanitize(cls, text: str) -> str:
        """
        Remove injection patterns from text
        
        Args:
            text: Text to sanitize
        
        Returns:
            Sanitized text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Remove Unicode tricks
        for char, _ in cls.UNICODE_TRICKS:
            text = text.replace(char, '')
        
        # Replace suspicious patterns with [REDACTED]
        for pattern, _ in cls.CRITICAL_PATTERNS + cls.SUSPICIOUS_PATTERNS:
            text = re.sub(
                pattern,
                '[REDACTED]',
                text,
                flags=re.IGNORECASE
            )
        
        return text
    
    @classmethod
    def analyze_risk_score(cls, text: str) -> Tuple[int, List[str]]:
        """
        Calculate risk score (0-100) and list flagged patterns
        
        Args:
            text: Text to analyze
        
        Returns:
            (risk_score, flagged_patterns)
        """
        if not text:
            return 0, []
        
        score = 0
        flagged = []
        text_lower = text.lower()
        
        # Critical patterns: +30 points each
        for pattern, pattern_type in cls.CRITICAL_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 30
                flagged.append(pattern_type)
        
        # Suspicious patterns: +15 points each
        for pattern, pattern_type in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 15
                flagged.append(pattern_type)
        
        # Unicode tricks: +20 points each
        for char, trick_type in cls.UNICODE_TRICKS:
            if char in text:
                score += 20
                flagged.append(trick_type)
        
        # Cap at 100
        score = min(score, 100)
        
        return score, flagged


# Convenience function
def check_injection(text: str, threshold: int = 30) -> bool:
    """
    Quick check if text contains injection
    
    Args:
        text: Text to check
        threshold: Risk score threshold (0-100)
    
    Returns:
        True if injection detected above threshold
    """
    score, _ = PromptInjectionDetector.analyze_risk_score(text)
    return score >= threshold


def sanitize_for_llm(text: str) -> str:
    """
    Sanitize text before passing to LLM
    
    Args:
        text: Text to sanitize
    
    Returns:
        Sanitized text safe for LLM consumption
    """
    return PromptInjectionDetector.sanitize(text)
