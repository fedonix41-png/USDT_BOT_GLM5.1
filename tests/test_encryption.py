"""Tests for EncryptionService."""

import pytest

from app.services.encryption import EncryptionService


TEST_KEY = "a" * 64


class TestEncryptionService:
    """Test AES-256-CBC encryption/decryption."""

    def test_init_valid_key(self):
        svc = EncryptionService(TEST_KEY)
        assert svc._key is not None
        assert len(svc._key) == 32

    def test_init_invalid_key_length(self):
        with pytest.raises(ValueError, match="64 hex chars"):
            EncryptionService("short")

    def test_init_invalid_hex(self):
        with pytest.raises(ValueError, match="Invalid hex"):
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
