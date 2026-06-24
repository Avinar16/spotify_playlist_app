from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator
from cryptography.fernet import Fernet, InvalidToken
from app.config import settings


class EncryptedText(TypeDecorator):
    """Transparent column-level encryption via Fernet (AES-128-CBC + HMAC)."""
    impl = Text
    cache_ok = True

    def _fernet(self) -> Fernet:
        return Fernet(settings.ENCRYPTION_KEY.encode())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return self._fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return self._fernet().decrypt(value.encode()).decode()
        except (InvalidToken, Exception):
            return None
