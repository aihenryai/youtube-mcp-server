"""
Secure Token Storage with Encryption
Handles encrypted storage of OAuth2 tokens
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)


class TokenStorage:
    """
    Secure storage for OAuth2 tokens with encryption
    
    Features:
    - AES-256 encryption via Fernet
    - Key derivation from machine-specific data
    - Automatic key generation
    - Safe file operations
    """
    
    def __init__(self, token_file: str = "token.json"):
        """
        Initialize token storage
        
        Args:
            token_file: Path to encrypted token file
        """
        self.token_file = Path(token_file)
        self.key_file = self.token_file.with_suffix('.key')
        
        # Initialize or load encryption key
        self.cipher = self._get_cipher()
    
    def _get_cipher(self) -> Fernet:
        """Get or create Fernet cipher"""
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate new key
            key = self._generate_key()
            # Save key securely (read-only)
            self.key_file.write_bytes(key)
            self.key_file.chmod(0o600)  # Read/write for owner only
            logger.info(f"✅ Generated new encryption key: {self.key_file}")
        
        return Fernet(key)
    
    def _generate_key(self) -> bytes:
        """
        Generate encryption key from machine-specific data
        
        Uses PBKDF2 with machine ID as salt for deterministic key generation
        """
        try:
            # Try to get machine-specific identifier
            import uuid
            machine_id = str(uuid.getnode()).encode()
        except:
            # Fallback to random
            machine_id = os.urandom(16)
        
        # Derive key using PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=machine_id,
            iterations=100000,
            backend=default_backend()
        )
        
        # Use a combination of machine ID and username
        password = (machine_id + os.getenv('USER', 'default').encode())
        key = base64.urlsafe_b64encode(kdf.derive(password))
        
        return key
    
    def save(self, token_data: Dict[str, Any]):
        """
        Save token data with encryption
        
        Args:
            token_data: Token dictionary to save
        """
        try:
            # Serialize to JSON
            json_data = json.dumps(token_data).encode('utf-8')
            
            # Encrypt
            encrypted_data = self.cipher.encrypt(json_data)
            
            # Save to file (read-only for owner)
            self.token_file.write_bytes(encrypted_data)
            self.token_file.chmod(0o600)
            
            logger.info(f"✅ Token saved securely to {self.token_file}")
            
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
            raise RuntimeError(f"Token storage failed: {e}")
    
    def load(self) -> Optional[Dict[str, Any]]:
        """
        Load and decrypt token data
        
        Returns:
            Token dictionary or None if not found
        """
        if not self.token_file.exists():
            return None
        
        try:
            # Read encrypted data
            encrypted_data = self.token_file.read_bytes()
            
            # Decrypt
            json_data = self.cipher.decrypt(encrypted_data)
            
            # Parse JSON
            token_data = json.loads(json_data.decode('utf-8'))
            
            logger.info("✅ Token loaded successfully")
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            # Don't raise - might be corrupted, allow re-auth
            return None
    
    def delete(self):
        """Delete token and key files"""
        files_deleted = []
        
        if self.token_file.exists():
            self.token_file.unlink()
            files_deleted.append(str(self.token_file))
        
        if self.key_file.exists():
            self.key_file.unlink()
            files_deleted.append(str(self.key_file))
        
        if files_deleted:
            logger.info(f"✅ Deleted: {', '.join(files_deleted)}")
    
    def exists(self) -> bool:
        """Check if token file exists"""
        return self.token_file.exists()
