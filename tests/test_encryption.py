"""Tests for EncryptionService."""

import base64

import pytest

from app.services.encryption import EncryptionService

TEST_KEY = "a" * 64
TEST_KEY_B64 = base64.urlsafe_b64encode(b"\x01" * 32).decode()


class TestEncryptionService:
    """Test AES-256-CBC encryption/decryption."""

    def test_init_valid_key(self):
        svc = EncryptionService(TEST_KEY)
        assert svc._key is not None
        assert len(svc._key) == 32

    def test_init_valid_base64_key(self):
        svc = EncryptionService(TEST_KEY_B64)
        assert len(svc._key) == 32

    def test_init_invalid_key_length(self):
        with pytest.raises(ValueError, match="32 bytes"):
            EncryptionService("short")

    def test_init_invalid_hex(self):
        with pytest.raises(ValueError, match="ENCRYPTION_KEY must be"):
            EncryptionService("x" * 64)

    def test_encrypt_decrypt_roundtrip(self):
        svc = EncryptionService(TEST_KEY)
        plaintext = "https://example.com/pay"
        encrypted = svc.encrypt(plaintext)
        assert encrypted != plaintext
        assert svc.decrypt(encrypted) == plaintext

    def test_encrypt_empty_string(self):
        svc = EncryptionService(TEST_KEY)
        assert svc.encrypt("") == ""

    def test_decrypt_empty_string(self):
        svc = EncryptionService(TEST_KEY)
        assert svc.decrypt("") == ""

    def test_encrypt_long_text(self):
        svc = EncryptionService(TEST_KEY)
        text = "A" * 1000
        encrypted = svc.encrypt(text)
        assert svc.decrypt(encrypted) == text

    def test_encrypt_unicode(self):
        svc = EncryptionService(TEST_KEY)
        text = "Реквизиты: карта 4276 **** 1234"
        encrypted = svc.encrypt(text)
        assert svc.decrypt(encrypted) == text

    def test_different_iv_each_time(self):
        svc = EncryptionService(TEST_KEY)
        text = "same text"
        enc1 = svc.encrypt(text)
        enc2 = svc.encrypt(text)
        # Different IV means different ciphertext
        assert enc1 != enc2
        # But both decrypt to same text
        assert svc.decrypt(enc1) == text
        assert svc.decrypt(enc2) == text

    def test_decrypt_invalid_hex(self):
        svc = EncryptionService(TEST_KEY)
        with pytest.raises(ValueError, match="Invalid hex"):
            svc.decrypt("not-hex")

    def test_decrypt_too_short(self):
        svc = EncryptionService(TEST_KEY)
        with pytest.raises(ValueError, match="too short"):
            svc.decrypt("abcd")

    def test_wrong_key_fails(self):
        svc1 = EncryptionService(TEST_KEY)
        svc2 = EncryptionService("b" * 64)
        encrypted = svc1.encrypt("secret")
        with pytest.raises(Exception):
            svc2.decrypt(encrypted)

    def test_encrypt_decrypt_gcm(self):
        svc = EncryptionService(TEST_KEY)
        plaintext = "Hello, GCM World!"
        ciphertext = svc.encrypt(plaintext)
        
        assert ciphertext.startswith("gcm$")
        assert ciphertext != plaintext
        
        decrypted = svc.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_decrypt_legacy_cbc(self):
        import os
        from binascii import hexlify
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.padding import PKCS7
        svc = EncryptionService(TEST_KEY)
        
        plaintext = "Hello, CBC World!"
        iv = os.urandom(16)
        padder = PKCS7(128).padder()
        padded = padder.update(plaintext.encode("utf-8")) + padder.finalize()
        cipher = Cipher(algorithms.AES(svc._key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ciphertext_bytes = encryptor.update(padded) + encryptor.finalize()
        
        legacy_cipher_hex = hexlify(iv + ciphertext_bytes).decode("ascii")
        
        decrypted = svc.decrypt(legacy_cipher_hex)
        assert decrypted == plaintext

    def test_decrypt_size_limit(self):
        svc = EncryptionService(TEST_KEY)
        large_cipher = "gcm$" + "a" * 102401
        with pytest.raises(ValueError, match="too long"):
            svc.decrypt(large_cipher)
