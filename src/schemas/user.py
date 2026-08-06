from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


UserStatus = Literal[
    "active",
    "inactive",
    "suspended",
]


class UserCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    user_email: EmailStr
    user_full_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )
    user_status: UserStatus = "active"
    is_tenant_admin: bool = False

    @field_validator("user_email")
    @classmethod
    def validate_user_email(cls, value: EmailStr) -> str:
        normalized_email = str(value).strip().lower()
        local_part, separator, domain = normalized_email.rpartition("@")

        if not separator or not local_part:
            raise ValueError(
                "user email is not a valid email address"
            )

        if domain != "gmail.com":
            raise ValueError(
                "user email must be a Gmail address "
                "ending with @gmail.com"
            )

        return normalized_email


class UserUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    user_email: EmailStr | None = None
    user_full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    user_status: UserStatus | None = None
    is_tenant_admin: bool | None = None

    @field_validator("user_email")
    @classmethod
    def validate_user_email(
        cls,
        value: EmailStr | None,
    ) -> str | None:
        if value is None:
            return None

        normalized_email = str(value).strip().lower()
        local_part, separator, domain = normalized_email.rpartition("@")

        if not separator or not local_part:
            raise ValueError(
                "user email is not a valid email address"
            )

        if domain != "gmail.com":
            raise ValueError(
                "user email must be a Gmail address "
                "ending with @gmail.com"
            )

        return normalized_email

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError(
                "at least one field must be provided"
            )

        return self


class UserPasswordUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )
    confirm_new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("new passwords do not match")

        if self.current_password == self.new_password:
            raise ValueError(
                "new password must be different from current password"
            )

        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    tenant_id: UUID
    user_email: EmailStr
    user_full_name: str
    user_status: UserStatus
    is_tenant_admin: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_pages: int = Field(ge=0)
