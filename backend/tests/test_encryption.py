import pytest
from unittest.mock import patch
from cryptography.fernet import Fernet

from app.infrastructure.database.encrypted_type import EncryptedText

TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture
def et():
    with patch("app.infrastructure.database.encrypted_type.settings") as mock_s:
        mock_s.ENCRYPTION_KEY = TEST_KEY
        yield EncryptedText()


@pytest.mark.unit
def test_encrypt_decrypt_roundtrip(et):
    encrypted = et.process_bind_param("spotify_access_token_abc123", None)
    assert encrypted != "spotify_access_token_abc123"
    assert isinstance(encrypted, str)

    decrypted = et.process_result_value(encrypted, None)
    assert decrypted == "spotify_access_token_abc123"


@pytest.mark.unit
def test_none_passthrough(et):
    assert et.process_bind_param(None, None) is None
    assert et.process_result_value(None, None) is None


@pytest.mark.unit
def test_invalid_ciphertext_returns_none(et):
    """Unencrypted or corrupted value in DB must return None, not crash."""
    assert et.process_result_value("not_encrypted_plain_text", None) is None
    assert et.process_result_value("", None) is None


@pytest.mark.unit
def test_different_values_produce_different_ciphertexts(et):
    """Fernet includes random IV so same plaintext → different ciphertext each time."""
    enc1 = et.process_bind_param("token", None)
    enc2 = et.process_bind_param("token", None)
    assert enc1 != enc2
    assert et.process_result_value(enc1, None) == "token"
    assert et.process_result_value(enc2, None) == "token"
