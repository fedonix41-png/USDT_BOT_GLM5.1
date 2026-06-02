"""AES-256-CBC encryption/decryption service.

Key: 32 bytes derived from ENCRYPTION_KEY (64-char hex string).
IV: 16 random bytes generated per encryption, prepended to ciphertext.
Output: hex-encoded string (IV + ciphertext) for storage in TEXT database fields.
"""

import base64
import os
from binascii import hexlify, unhexlify

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


class EncryptionService:
    """AES-256-GCM encryption/decryption service (with CBC fallback for old data)."""

    BLOCK_SIZE = 16  # AES block size in bytes
    KEY_SIZE = 32  # AES-256 key size in bytes

    def __init__(self, key_hex: str) -> None:
        """Initialize with a 64-character hex string or base64 string (32 bytes for AES-256).

        Args:
            key_hex: 64-character hex string OR base64-encoded 32-byte key.

        Raises:
            ValueError: If key cannot be decoded to 32 bytes.
        """
        key_bytes = self._decode_key(key_hex)
        if len(key_bytes) != self.KEY_SIZE:
            raise ValueError(
                f"ENCRYPTION_KEY must decode to {self.KEY_SIZE} bytes, got {len(key_bytes)}"
            )
        self._key = key_bytes

    @staticmethod
    def _decode_key(raw: str) -> bytes:
        raw = raw.strip()
        try:
            key = unhexlify(raw)
            if len(key) == 32:
                return key
        except (ValueError, TypeError):
            pass
        try:
            key = base64.b64decode(raw)
            if len(key) == 32:
                return key
        except (ValueError, TypeError):
            pass
        try:
            key = base64.urlsafe_b64decode(raw)
            if len(key) == 32:
                return key
        except (ValueError, TypeError):
            pass
        raise ValueError(
            f"ENCRYPTION_KEY must be 64 hex chars or base64 of 32 bytes, got {len(raw)} chars"
        )

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using AES-256-GCM.

        Generates a random 12-byte IV, encrypts, and returns hex-encoded (IV + Tag + ciphertext)
        with a 'gcm$' prefix.

        Args:
            plaintext: The string to encrypt.

        Returns:
            Hex-encoded string prefixed with 'gcm$'.
        """
        if not plaintext:
            return ""

        iv = os.urandom(12)  # Recommended length for GCM

        cipher = Cipher(algorithms.AES(self._key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()

        # tag is 16 bytes
        return "gcm$" + hexlify(iv + encryptor.tag + ciphertext).decode("ascii")

    def decrypt(self, cipher_hex: str) -> str:
        """Decrypt hex-encoded string.

        Supports 'gcm$' prefix (AES-GCM) and fallback to old format (AES-CBC).

        Args:
            cipher_hex: Hex-encoded string.

        Returns:
            The decrypted plaintext string.

        Raises:
            ValueError: If cipher_hex is empty, too long, or invalid.
        """
        if not cipher_hex:
            return ""
            
        if len(cipher_hex) > 102400:  # 100 KB limit to prevent DoS
            raise ValueError("Cipher text too long")

        if cipher_hex.startswith("gcm$"):
            hex_data = cipher_hex[4:]
            try:
                raw = unhexlify(hex_data)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid hex cipher text: {e}")
                
            if len(raw) < 12 + 16:
                raise ValueError("Cipher text too short for GCM")
                
            iv = raw[:12]
            tag = raw[12:28]
            ciphertext = raw[28:]
            
            cipher = Cipher(algorithms.AES(self._key), modes.GCM(iv, tag))
            decryptor = cipher.decryptor()
            return (decryptor.update(ciphertext) + decryptor.finalize()).decode("utf-8")
        else:
            # Fallback to AES-CBC
            try:
                raw = unhexlify(cipher_hex)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid hex cipher text: {e}")

            if len(raw) < self.BLOCK_SIZE + 1:
                raise ValueError("Cipher text too short")

            iv = raw[: self.BLOCK_SIZE]
            ciphertext = raw[self.BLOCK_SIZE :]

            cipher = Cipher(algorithms.AES(self._key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded = decryptor.update(ciphertext) + decryptor.finalize()

            # Remove PKCS7 padding
            unpadder = PKCS7(self.BLOCK_SIZE * 8).unpadder()
            data = unpadder.update(padded) + unpadder.finalize()

            return data.decode("utf-8")
