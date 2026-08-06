from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID, uuid4
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
class JWTService:
    """
    Create and validate JWT access and refresh tokens.
    """
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ) -> None:

        if not secret_key or len(secret_key) < 32:
            raise ValueError(
                "JWT secret key must contain "
                "at least 32 characters"
            )

        if access_token_expire_minutes <= 0:
            raise ValueError(
                "access_token_expire_minutes "
                "must be positive"
            )

        if refresh_token_expire_days <= 0:
            raise ValueError(
                "refresh_token_expire_days "
                "must be positive"
            )

        self.secret_key = secret_key

        self.algorithm = algorithm

        self.access_token_expire_minutes = (
            access_token_expire_minutes
        )

        self.refresh_token_expire_days = (
            refresh_token_expire_days
        )

    # =========================
    # Create Access Token
    # =========================
    def create_access_token(
        self,
        user_id: UUID,
        tenant_id: UUID,
        is_tenant_admin: bool,
        roles: list[str] | None = None,
    ) -> tuple[str, int]:

        expires_delta = timedelta(
            minutes=(
                self.access_token_expire_minutes
            )
        )

        token = self._create_token(
            user_id=user_id,
            tenant_id=tenant_id,
            token_type="access",
            expires_delta=expires_delta,
            additional_claims={
                "is_tenant_admin": (
                    is_tenant_admin
                ),
                "roles": roles or [],
            },
        )

        expires_in = int(
            expires_delta.total_seconds()
        )

        return token, expires_in

    # =========================
    # Create Refresh Token
    # =========================
    def create_refresh_token(
        self,
        user_id: UUID,
        tenant_id: UUID,
    ) -> str:

        return self._create_token(
            user_id=user_id,
            tenant_id=tenant_id,
            token_type="refresh",
            expires_delta=timedelta(
                days=(
                    self.refresh_token_expire_days
                )
            ),
        )

    # =========================
    # Create Token Pair
    # =========================
    def create_token_pair(
        self,
        user_id: UUID,
        tenant_id: UUID,
        is_tenant_admin: bool,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:

        access_token, expires_in = (
            self.create_access_token(
                user_id=user_id,
                tenant_id=tenant_id,
                is_tenant_admin=(
                    is_tenant_admin
                ),
                roles=roles,
            )
        )

        refresh_token = (
            self.create_refresh_token(
                user_id=user_id,
                tenant_id=tenant_id,
            )
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }

    # =========================
    # Decode Access Token
    # =========================
    def decode_access_token(
        self,
        token: str,
    ) -> dict[str, Any]:

        return self._decode_token(
            token=token,
            expected_token_type="access",
        )

    # =========================
    # Decode Refresh Token
    # =========================
    def decode_refresh_token(
        self,
        token: str,
    ) -> dict[str, Any]:

        return self._decode_token(
            token=token,
            expected_token_type="refresh",
        )

    # =========================
    # Internal Token Creation
    # =========================
    def _create_token(
        self,
        user_id: UUID,
        tenant_id: UUID,
        token_type: Literal[
            "access",
            "refresh",
        ],
        expires_delta: timedelta,
        additional_claims: (
            dict[str, Any] | None
        ) = None,
    ) -> str:

        issued_at = datetime.now(
            timezone.utc
        )

        expires_at = (
            issued_at + expires_delta
        )

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "token_type": token_type,
            "iat": issued_at,
            "exp": expires_at,
            "jti": str(uuid4()),
        }

        if additional_claims:
            payload.update(
                additional_claims
            )

        return jwt.encode(
            payload=payload,
            key=self.secret_key,
            algorithm=self.algorithm,
        )

    # =========================
    # Internal Token Decoding
    # =========================
    def _decode_token(
        self,
        token: str,
        expected_token_type: Literal[
            "access",
            "refresh",
        ],
    ) -> dict[str, Any]:

        if not token or not token.strip():
            raise ValueError(
                "token cannot be empty"
            )

        try:
            payload = jwt.decode(
                jwt=token,
                key=self.secret_key,
                algorithms=[
                    self.algorithm
                ],
                options={
                    "require": [
                        "sub",
                        "tenant_id",
                        "token_type",
                        "iat",
                        "exp",
                        "jti",
                    ]
                },
            )

        except ExpiredSignatureError as exc:
            raise ValueError(
                "token has expired"
            ) from exc

        except InvalidTokenError as exc:
            raise ValueError(
                "invalid token"
            ) from exc

        if (
            payload.get("token_type")
            != expected_token_type
        ):
            raise ValueError(
                "expected "
                f"{expected_token_type} token"
            )

        try:
            payload["sub"] = UUID(
                payload["sub"]
            )

            payload["tenant_id"] = UUID(
                payload["tenant_id"]
            )

            payload["jti"] = UUID(
                payload["jti"]
            )

        except (
            TypeError,
            ValueError,
            KeyError,
        ) as exc:
            raise ValueError(
                "invalid token claims"
            ) from exc

        return payload