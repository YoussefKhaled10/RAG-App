from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
class PasswordHasher:
    """
    Hash and verify user passwords using Argon2.
    """
    def __init__(self) -> None:
        self._password_hash = (
            PasswordHash.recommended()
        )

    def hash_password(
        self,
        plain_password: str,
    ) -> str:
        if not plain_password:
            raise ValueError(
                "password cannot be empty"
            )

        return self._password_hash.hash(
            plain_password
        )

    def verify_password(
        self,
        plain_password: str,
        password_hash: str,
    ) -> bool:
        if not plain_password:
            return False

        if not password_hash:
            return False

        try:
            return self._password_hash.verify(
                plain_password,
                password_hash,
            )

        except (
            UnknownHashError,
            ValueError,
            TypeError,
        ):
            return False