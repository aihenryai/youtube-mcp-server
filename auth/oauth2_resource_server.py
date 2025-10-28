"""
OAuth2 Resource Server Implementation (RFC 6750 + RFC 9728)
Provides full OAuth2 Protected Resource capabilities for YouTube MCP Server

Features:
- Bearer token validation
- WWW-Authenticate header generation (RFC 6750)
- OAuth 2.1 Protected Resource Metadata (RFC 9728)
- Scope-based authorization
- Token introspection
- Error responses per RFC 6750
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)


@dataclass
class TokenValidationResult:
    """Result of token validation"""
    valid: bool
    error: Optional[str] = None
    error_description: Optional[str] = None
    scopes: Optional[List[str]] = None
    user_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    

@dataclass
class ResourceServerConfig:
    """OAuth2 Resource Server configuration"""
    resource_uri: str
    authorization_servers: List[str]
    realm: str = "YouTube MCP Server"
    require_scope: bool = True
    supported_scopes: List[str] = None
    audience: Optional[str] = None
    

class OAuth2ResourceServer:
    """
    Complete OAuth2 Resource Server implementation
    
    Implements:
    - RFC 6750: Bearer Token Usage
    - RFC 9728: OAuth 2.1 Protected Resource Metadata
    - RFC 6749: OAuth 2.0 Authorization Framework
    """
    
    def __init__(self, config: ResourceServerConfig):
        """
        Initialize OAuth2 Resource Server
        
        Args:
            config: Resource server configuration
        """
        self.config = config
        self.supported_scopes = config.supported_scopes or [
            "video.read",
            "video.write",
            "playlist.read",
            "playlist.write",
            "captions.read",
            "captions.write",
            "channel.read",
            "channel.write"
        ]
        
        logger.info(f"OAuth2 Resource Server initialized for {config.resource_uri}")
    
    def validate_bearer_token(
        self,
        authorization_header: Optional[str],
        required_scopes: Optional[List[str]] = None
    ) -> TokenValidationResult:
        """
        Validate Bearer token from Authorization header
        
        Args:
            authorization_header: Authorization header value (e.g., "Bearer <token>")
            required_scopes: List of required scopes for this operation
        
        Returns:
            TokenValidationResult with validation status and details
        
        Example:
            >>> result = server.validate_bearer_token(
            ...     authorization_header="Bearer eyJhbGci...",
            ...     required_scopes=["video.read"]
            ... )
            >>> if result.valid:
            ...     # Process request
            ... else:
            ...     # Return 401 with result.error
        """
        # 1. Check Authorization header exists
        if not authorization_header:
            return TokenValidationResult(
                valid=False,
                error="invalid_request",
                error_description="Missing Authorization header"
            )
        
        # 2. Parse Bearer token
        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return TokenValidationResult(
                valid=False,
                error="invalid_request",
                error_description="Invalid Authorization header format. Expected: Bearer <token>"
            )
        
        token = parts[1]
        
        # 3. Validate token
        try:
            # For Google OAuth tokens, verify ID token
            if self._is_google_token(token):
                return self._validate_google_token(token, required_scopes)
            else:
                # For custom tokens (JWT)
                return self._validate_jwt_token(token, required_scopes)
                
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return TokenValidationResult(
                valid=False,
                error="invalid_token",
                error_description=f"Token validation failed: {str(e)}"
            )
    
    def _is_google_token(self, token: str) -> bool:
        """Check if token is a Google OAuth token"""
        # Google tokens typically start with 'ya29.' or are JWTs
        return token.startswith('ya29.') or '.' in token
    
    def _validate_google_token(
        self,
        token: str,
        required_scopes: Optional[List[str]] = None
    ) -> TokenValidationResult:
        """
        Validate Google OAuth2 token
        
        Uses Google's token verification service
        """
        try:
            # Verify Google ID token
            # Note: This requires the token to be an ID token, not an access token
            # For access tokens, you'd need to call Google's tokeninfo endpoint
            
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                self.config.audience
            )
            
            # Extract information
            user_id = idinfo.get('sub')
            email = idinfo.get('email')
            expires_at = datetime.fromtimestamp(idinfo.get('exp', 0))
            
            # Check if token is expired
            if expires_at < datetime.now():
                return TokenValidationResult(
                    valid=False,
                    error="invalid_token",
                    error_description="Token has expired"
                )
            
            # Extract scopes (if available)
            token_scopes = idinfo.get('scope', '').split() if 'scope' in idinfo else []
            
            # Validate required scopes
            if required_scopes and not self._check_scopes(token_scopes, required_scopes):
                return TokenValidationResult(
                    valid=False,
                    error="insufficient_scope",
                    error_description=f"Token missing required scopes: {', '.join(required_scopes)}"
                )
            
            return TokenValidationResult(
                valid=True,
                scopes=token_scopes,
                user_id=user_id,
                expires_at=expires_at
            )
            
        except ValueError as e:
            return TokenValidationResult(
                valid=False,
                error="invalid_token",
                error_description=f"Invalid Google token: {str(e)}"
            )
    
    def _validate_jwt_token(
        self,
        token: str,
        required_scopes: Optional[List[str]] = None
    ) -> TokenValidationResult:
        """
        Validate custom JWT token
        
        For custom authentication systems
        """
        try:
            # Decode JWT without verification (for development)
            # In production, you should verify with a secret key
            secret = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')
            
            payload = jwt.decode(
                token,
                secret,
                algorithms=['HS256'],
                options={'verify_signature': True}
            )
            
            # Extract claims
            user_id = payload.get('sub')
            expires_at = datetime.fromtimestamp(payload.get('exp', 0))
            token_scopes = payload.get('scopes', [])
            
            # Check expiration
            if expires_at < datetime.now():
                return TokenValidationResult(
                    valid=False,
                    error="invalid_token",
                    error_description="Token has expired"
                )
            
            # Validate required scopes
            if required_scopes and not self._check_scopes(token_scopes, required_scopes):
                return TokenValidationResult(
                    valid=False,
                    error="insufficient_scope",
                    error_description=f"Token missing required scopes: {', '.join(required_scopes)}"
                )
            
            return TokenValidationResult(
                valid=True,
                scopes=token_scopes,
                user_id=user_id,
                expires_at=expires_at
            )
            
        except jwt.ExpiredSignatureError:
            return TokenValidationResult(
                valid=False,
                error="invalid_token",
                error_description="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            return TokenValidationResult(
                valid=False,
                error="invalid_token",
                error_description=f"Invalid JWT token: {str(e)}"
            )
    
    def _check_scopes(
        self,
        token_scopes: List[str],
        required_scopes: List[str]
    ) -> bool:
        """Check if token has all required scopes"""
        token_scope_set = set(token_scopes)
        required_scope_set = set(required_scopes)
        return required_scope_set.issubset(token_scope_set)
    
    def generate_www_authenticate_header(
        self,
        error: Optional[str] = None,
        error_description: Optional[str] = None,
        required_scopes: Optional[List[str]] = None
    ) -> str:
        """
        Generate WWW-Authenticate header for 401 responses (RFC 6750)
        
        Args:
            error: OAuth error code (e.g., 'invalid_token', 'insufficient_scope')
            error_description: Human-readable error description
            required_scopes: List of required scopes for the operation
        
        Returns:
            WWW-Authenticate header value
        
        Example:
            >>> header = server.generate_www_authenticate_header(
            ...     error="insufficient_scope",
            ...     error_description="Token missing video.write scope",
            ...     required_scopes=["video.write"]
            ... )
            >>> # WWW-Authenticate: Bearer realm="YouTube MCP Server",
            >>>                     error="insufficient_scope",
            >>>                     error_description="Token missing video.write scope",
            >>>                     scope="video.write"
        """
        params = [f'realm="{self.config.realm}"']
        
        if error:
            params.append(f'error="{error}"')
        
        if error_description:
            # Escape quotes in description
            escaped_desc = error_description.replace('"', '\\"')
            params.append(f'error_description="{escaped_desc}"')
        
        if required_scopes:
            scope_str = " ".join(required_scopes)
            params.append(f'scope="{scope_str}"')
        
        return f"Bearer {', '.join(params)}"
    
    def get_protected_resource_metadata(self) -> Dict[str, Any]:
        """
        Get OAuth 2.1 Protected Resource Metadata (RFC 9728)
        
        Returns metadata that should be served at:
        /.well-known/oauth-protected-resource
        
        Returns:
            Dictionary with OAuth 2.1 metadata
        
        Example response:
            {
                "resource": "https://mcp-server.example.com",
                "authorization_servers": [
                    "https://accounts.google.com"
                ],
                "bearer_methods_supported": ["header"],
                "resource_signing_alg_values_supported": ["RS256"],
                "resource_documentation": "https://docs.example.com/oauth",
                "scopes_supported": [
                    "video.read",
                    "video.write",
                    ...
                ]
            }
        """
        return {
            "resource": self.config.resource_uri,
            "authorization_servers": self.config.authorization_servers,
            "bearer_methods_supported": ["header"],
            "resource_signing_alg_values_supported": ["RS256", "HS256"],
            "resource_documentation": f"{self.config.resource_uri}/docs",
            "scopes_supported": self.supported_scopes,
            "resource_server_metadata": {
                "realm": self.config.realm,
                "require_scope": self.config.require_scope,
                "token_type_supported": "Bearer"
            }
        }
    
    def get_scope_requirements(self, tool_name: str) -> List[str]:
        """
        Get required scopes for a specific MCP tool
        
        Args:
            tool_name: Name of the MCP tool
        
        Returns:
            List of required scope strings
        
        Example:
            >>> scopes = server.get_scope_requirements("create_playlist")
            >>> # ['playlist.write']
        """
        # Mapping of tools to required scopes
        scope_map = {
            # Read operations
            "get_video_info": ["video.read"],
            "get_video_transcript": ["video.read"],
            "get_channel_info": ["channel.read"],
            "get_video_comments": ["video.read"],
            "search_videos": ["video.read"],
            "list_user_playlists": ["playlist.read"],
            
            # Write operations
            "create_playlist": ["playlist.write"],
            "add_video_to_playlist": ["playlist.write"],
            "remove_video_from_playlist": ["playlist.write"],
            "update_playlist": ["playlist.write"],
            "reorder_playlist_video": ["playlist.write"],
            
            # Caption operations
            "upload_caption": ["captions.write"],
            "update_caption": ["captions.write"],
            "delete_caption": ["captions.write"],
            "list_captions": ["captions.read"],
            
            # Channel operations
            "update_channel": ["channel.write"],
        }
        
        return scope_map.get(tool_name, [])


def create_resource_server(
    resource_uri: str,
    authorization_servers: List[str],
    realm: str = "YouTube MCP Server",
    supported_scopes: Optional[List[str]] = None
) -> OAuth2ResourceServer:
    """
    Factory function to create OAuth2 Resource Server
    
    Args:
        resource_uri: URI of this protected resource
        authorization_servers: List of trusted authorization servers
        realm: Authentication realm name
        supported_scopes: List of supported scope strings
    
    Returns:
        Configured OAuth2ResourceServer instance
    
    Example:
        >>> server = create_resource_server(
        ...     resource_uri="https://mcp-server.example.com",
        ...     authorization_servers=["https://accounts.google.com"],
        ...     realm="YouTube MCP Server"
        ... )
    """
    config = ResourceServerConfig(
        resource_uri=resource_uri,
        authorization_servers=authorization_servers,
        realm=realm,
        supported_scopes=supported_scopes
    )
    
    return OAuth2ResourceServer(config)
