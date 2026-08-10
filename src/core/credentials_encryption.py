import base64
import binascii

from cryptography.fernet import Fernet, InvalidToken


class CredentialsEncryptionService:
    """Encrypt and decrypt external database credentials using Fernet."""

    TOKEN_PREFIX = "v1:"

    def __init__(self, encryption_key: str) -> None:
        clean_key = str(encryption_key or "").strip()
        if not clean_key:
            raise ValueError(
                "DATABASE_CREDENTIALS_ENCRYPTION_KEY was not configured"
            )

        try:
            decoded_key = base64.urlsafe_b64decode(
                clean_key.encode("ascii")
            )
        except (ValueError, UnicodeEncodeError, binascii.Error) as exc:
            raise ValueError(
                "DATABASE_CREDENTIALS_ENCRYPTION_KEY is invalid"
            ) from exc

        if len(decoded_key) != 32:
            raise ValueError(
                "DATABASE_CREDENTIALS_ENCRYPTION_KEY must be a "
                "Fernet-compatible 32-byte URL-safe base64 key"
            )

        self._fernet = Fernet(clean_key.encode("ascii"))

    def encrypt(self, plain_value: str) -> str:
        clean_value = str(plain_value or "")
        if not clean_value:
            raise ValueError("credential value cannot be empty")

        encrypted = self._fernet.encrypt(
            clean_value.encode("utf-8")
        ).decode("ascii")
        return f"{self.TOKEN_PREFIX}{encrypted}"

    def decrypt(self, encrypted_value: str) -> str:
        clean_value = str(encrypted_value or "").strip()
        if not clean_value.startswith(self.TOKEN_PREFIX):
            raise ValueError("encrypted credential version is unsupported")

        token = clean_value[len(self.TOKEN_PREFIX):]
        try:
            return self._fernet.decrypt(
                token.encode("ascii")
            ).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError) as exc:
            raise ValueError(
                "encrypted credential could not be decrypted"
            ) from exc

    def is_encrypted(self, value: str | None) -> bool:
        return bool(
            value
            and str(value).startswith(self.TOKEN_PREFIX)
        )