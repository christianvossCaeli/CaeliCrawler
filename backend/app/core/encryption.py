"""Fernet-based encryption for sensitive user data (API keys, secrets).

This module provides symmetric encryption using Fernet, which guarantees:
- AES-128-CBC encryption
- HMAC-SHA256 authentication
- Timestamp-based token validation

The encryption key is derived from the application's secret_key using SHA-256.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

import structlog
from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

logger = structlog.get_logger()


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""

    pass


class EncryptionService:
    """Service for encrypting/decrypting sensitive data using Fernet.

    This service provides a secure way to store sensitive data like API keys
    in the database. Data is encrypted using Fernet symmetric encryption,
    with the key derived from the application's secret_key.

    Usage:
        # Encrypt credentials
        encrypted = EncryptionService.encrypt({"api_key": "sk-..."})

        # Decrypt credentials
        data = EncryptionService.decrypt(encrypted)
    """

    _fernet: Fernet | None = None
    _key_hash: str | None = None

    @classmethod
    def _get_fernet(cls) -> Fernet:
        """Get or create Fernet instance.

        The Fernet key is derived from the application's secret_key using SHA-256
        to ensure consistent 32-byte key length.

        Returns:
            Fernet instance for encryption/decryption
        """
        settings = get_settings()
        current_key_hash = hashlib.sha256(settings.secret_key.encode()).hexdigest()[:16]

        # Recreate Fernet if secret_key changed (useful for testing)
        if cls._fernet is None or cls._key_hash != current_key_hash:
            # Derive 32-byte key from secret_key using SHA-256
            key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            cls._fernet = Fernet(fernet_key)
            cls._key_hash = current_key_hash

        return cls._fernet

    @classmethod
    def encrypt(cls, data: dict[str, Any]) -> str:
        """Encrypt a dictionary of credentials.

        Args:
            data: Dictionary with credential data (api_key, endpoint, etc.)

        Returns:
            Base64-encoded encrypted string suitable for database storage

        Raises:
            EncryptionError: If encryption fails
        """
        if not data:
            raise EncryptionError("Cannot encrypt empty data")

        try:
            fernet = cls._get_fernet()
            json_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
            encrypted = fernet.encrypt(json_bytes)
            return encrypted.decode("utf-8")
        except Exception as e:
            logger.error("encryption_failed", error=str(e))
            raise EncryptionError(f"Failed to encrypt data: {e}") from e

    @classmethod
    def decrypt(cls, encrypted_data: str) -> dict[str, Any]:
        """Decrypt credentials back to dictionary.

        Args:
            encrypted_data: Base64-encoded encrypted string from database

        Returns:
            Decrypted dictionary with original credential data

        Raises:
            EncryptionError: If decryption fails (invalid token, corrupted data, etc.)
        """
        if not encrypted_data:
            raise EncryptionError("Cannot decrypt empty data")

        try:
            fernet = cls._get_fernet()
            decrypted = fernet.decrypt(encrypted_data.encode("utf-8"))
            return json.loads(decrypted.decode("utf-8"))
        except InvalidToken as e:
            logger.error(
                "decryption_failed_invalid_token",
                error="Invalid token - data may be corrupted or secret_key changed",
            )
            raise EncryptionError(
                "Failed to decrypt data: invalid token. "
                "This may occur if the secret_key has changed since encryption."
            ) from e
        except json.JSONDecodeError as e:
            logger.error("decryption_failed_invalid_json", error=str(e))
            raise EncryptionError(f"Failed to parse decrypted data: {e}") from e
        except Exception as e:
            logger.error("decryption_failed", error=str(e))
            raise EncryptionError(f"Failed to decrypt data: {e}") from e

    @classmethod
    def reset(cls) -> None:
        """Reset the Fernet instance.

        Useful for testing when secret_key changes between tests.
        """
        cls._fernet = None
        cls._key_hash = None

    @classmethod
    def is_encrypted(cls, data: str) -> bool:
        """Check if a string appears to be Fernet-encrypted.

        This is a heuristic check based on Fernet token format.

        Args:
            data: String to check

        Returns:
            True if the string looks like a Fernet token
        """
        if not data:
            return False

        # Fernet tokens are base64-encoded and have a specific structure
        try:
            # Fernet tokens are at least 128 characters when base64 encoded
            if len(data) < 100:
                return False

            # Try to decode as base64
            decoded = base64.urlsafe_b64decode(data.encode("utf-8"))

            # Fernet tokens have a version byte (0x80) at the start
            return len(decoded) >= 1 and decoded[0] == 0x80
        except Exception:
            return False
