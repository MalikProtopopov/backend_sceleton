"""Encryption utilities for secure storage of sensitive data.

Uses Fernet symmetric encryption (AES-128-CBC) for encrypting
sensitive values like API tokens, secrets, etc.
"""

import base64
import logging
import os
import secrets

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""
    pass


class EncryptionService:
    """Service for encrypting and decrypting sensitive data.
    
    Uses Fernet symmetric encryption with key from environment.
    If no key is configured, generates a temporary one (dev mode only).
    """
    
    def __init__(self) -> None:
        self._fernet: Fernet | None = None
    
    @property
    def fernet(self) -> Fernet:
        """Lazy initialization of Fernet instance."""
        if self._fernet is None:
            key = self._get_or_generate_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def _get_or_generate_key(self) -> bytes:
        """Get encryption key from settings or generate temporary one.
        
        In production, ENCRYPTION_KEY must be set.
        In development, a temporary key is generated with a warning.
        """
        if settings.encryption_key:
            # Key should be base64-encoded 32-byte value
            try:
                key = settings.encryption_key.encode()
                # Validate it's a proper Fernet key
                Fernet(key)
                return key
            except Exception as e:
                logger.error(f"Invalid ENCRYPTION_KEY format: {e}")
                raise EncryptionError(
                    "Invalid ENCRYPTION_KEY. Must be a valid Fernet key "
                    "(32-byte base64-encoded). Generate with: "
                    "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
        
        if settings.is_production:
            raise EncryptionError(
                "ENCRYPTION_KEY must be set in production environment"
            )
        
        # Development mode: generate temporary key
        logger.warning(
            "ENCRYPTION_KEY not set. Using temporary key. "
            "Data encrypted in this session will not be recoverable after restart!"
        )
        return Fernet.generate_key()
    
    def encrypt(self, value: str) -> str:
        """Encrypt a string value.
        
        Args:
            value: Plain text value to encrypt
            
        Returns:
            Base64-encoded encrypted value
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not value:
            return ""
        
        try:
            encrypted = self.fernet.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError("Failed to encrypt value")
    
    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt an encrypted value.
        
        Args:
            encrypted_value: Base64-encoded encrypted value
            
        Returns:
            Decrypted plain text
            
        Raises:
            EncryptionError: If decryption fails
        """
        if not encrypted_value:
            return ""
        
        try:
            decrypted = self.fernet.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Decryption failed: invalid token (wrong key or corrupted data)")
            raise EncryptionError("Failed to decrypt value: invalid token")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError("Failed to decrypt value")


def mask_value(value: str, visible_chars: int = 4) -> str:
    """Mask a sensitive value for display.
    
    Shows only the last N characters, replacing the rest with bullets.
    
    Args:
        value: Value to mask
        visible_chars: Number of characters to show at the end
        
    Returns:
        Masked value like "••••••••1234"
    """
    if not value:
        return ""
    
    if len(value) <= visible_chars:
        return "•" * len(value)
    
    hidden_part = "•" * (len(value) - visible_chars)
    visible_part = value[-visible_chars:]
    return hidden_part + visible_part


def generate_secret(length: int = 32) -> str:
    """Generate a cryptographically secure random secret.
    
    Args:
        length: Number of bytes of randomness (output will be longer due to base64)
        
    Returns:
        URL-safe base64-encoded random string
    """
    return secrets.token_urlsafe(length)


# Singleton instance for convenience
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get singleton encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service

