#!/usr/bin/env python3
"""
Proxy support for YouTube MCP Server
Enables API requests through HTTP/HTTPS proxies
"""

import os
import logging
from typing import Optional, Dict
import urllib3
from urllib.parse import urlparse

from config import config

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Manages proxy configuration for API requests
    Supports HTTP, HTTPS, and SOCKS proxies
    """
    
    def __init__(self):
        """Initialize proxy manager"""
        self.enabled = config.proxy.enabled
        self.http_proxy = config.proxy.http_proxy
        self.https_proxy = config.proxy.https_proxy
        
        if self.enabled:
            logger.info(
                f"Proxy enabled - HTTP: {self._mask_proxy(self.http_proxy)}, "
                f"HTTPS: {self._mask_proxy(self.https_proxy)}"
            )
    
    def _mask_proxy(self, proxy_url: Optional[str]) -> str:
        """
        Mask sensitive parts of proxy URL for logging
        
        Args:
            proxy_url: Full proxy URL
            
        Returns:
            Masked URL safe for logging
        """
        if not proxy_url:
            return "None"
        
        try:
            parsed = urlparse(proxy_url)
            if parsed.username:
                # Mask credentials
                return f"{parsed.scheme}://***:***@{parsed.hostname}:{parsed.port}"
            return proxy_url
        except Exception:
            return "Invalid URL"
    
    def get_proxy_dict(self) -> Optional[Dict[str, str]]:
        """
        Get proxy configuration as dictionary for requests
        
        Returns:
            Dictionary with http and https proxy URLs, or None if disabled
        """
        if not self.enabled:
            return None
        
        proxies = {}
        
        if self.http_proxy:
            proxies['http'] = self.http_proxy
        
        if self.https_proxy:
            proxies['https'] = self.https_proxy
        
        return proxies if proxies else None
    
    def configure_urllib3(self) -> Optional[urllib3.ProxyManager]:
        """
        Configure urllib3 proxy manager
        
        Returns:
            ProxyManager instance or None if proxies disabled
        """
        if not self.enabled or not self.https_proxy:
            return None
        
        try:
            proxy_manager = urllib3.ProxyManager(
                self.https_proxy,
                maxsize=10,
                headers={'User-Agent': 'YouTube-MCP-Server/2.1'}
            )
            
            logger.info("urllib3 ProxyManager configured")
            return proxy_manager
            
        except Exception as e:
            logger.error(f"Failed to configure urllib3 proxy: {e}")
            return None
    
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """
        Test proxy connection by making a simple request
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        if not self.enabled:
            return True, None
        
        try:
            import requests
            
            proxies = self.get_proxy_dict()
            
            # Test with a simple request
            response = requests.get(
                'https://www.google.com',
                proxies=proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ Proxy connection test successful")
                return True, None
            else:
                error_msg = f"Proxy test failed with status {response.status_code}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Proxy connection test failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg
    
    def get_env_config(self) -> Dict[str, str]:
        """
        Get proxy configuration as environment variables
        Useful for subprocess calls
        
        Returns:
            Dictionary of environment variables
        """
        env_config = {}
        
        if self.enabled:
            if self.http_proxy:
                env_config['HTTP_PROXY'] = self.http_proxy
                env_config['http_proxy'] = self.http_proxy
            
            if self.https_proxy:
                env_config['HTTPS_PROXY'] = self.https_proxy
                env_config['https_proxy'] = self.https_proxy
        
        return env_config


# Global proxy manager instance
proxy_manager = ProxyManager()


def get_proxy_config() -> Optional[Dict[str, str]]:
    """
    Get current proxy configuration
    
    Returns:
        Proxy dictionary for requests library, or None
    """
    return proxy_manager.get_proxy_dict()


def test_proxy_connection() -> tuple[bool, Optional[str]]:
    """
    Test if proxy is working
    
    Returns:
        (is_working: bool, error_message: Optional[str])
    """
    return proxy_manager.test_connection()


def configure_google_api_proxy():
    """
    Configure proxy for Google API client
    Note: Google API client uses httplib2 which reads from environment variables
    """
    if proxy_manager.enabled:
        env_config = proxy_manager.get_env_config()
        os.environ.update(env_config)
        logger.info("Google API client proxy configured via environment variables")


# Auto-configure on import
if proxy_manager.enabled:
    configure_google_api_proxy()
