from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from .role import RoleResponse
from .tenant import TenantResponse
from .user import UserResponse


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    tenant_code: str = Field(
        ...,
        min_length=3,
        max_length=80,
    )
    email: EmailStr
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
    )

    @field_validator("tenant_code")
    @classmethod
    def normalize_tenant_code(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("email")
    @classmethod
    def normalize_login_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class RefreshTokenRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    refresh_token: str = Field(
        ...,
        min_length=20,
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(gt=0)


class AccessTokenPayload(BaseModel):
    sub: UUID
    tenant_id: UUID
    token_type: Literal["access"]
    is_tenant_admin: bool
    roles: list[str] = Field(default_factory=list)
    iat: int
    exp: int
    jti: UUID


class RefreshTokenPayload(BaseModel):
    sub: UUID
    tenant_id: UUID
    token_type: Literal["refresh"]
    iat: int
    exp: int
    jti: UUID


class CurrentUserResponse(BaseModel):
    user: UserResponse
    tenant: TenantResponse
    roles: list[RoleResponse] = Field(default_factory=list)


class AuthenticationErrorResponse(BaseModel):
    detail: str
    context: dict[str, Any] | None = None
