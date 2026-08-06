import re

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
class TenantRegistrationRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    tenant_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )
    tenant_code: str = Field(
        ...,
        min_length=3,
        max_length=80,
    )
    admin_full_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )
    admin_email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )
    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )

    @field_validator("tenant_code")
    @classmethod
    def validate_tenant_code(cls, value: str) -> str:
        normalized_value = value.strip().lower()

        if not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*",
            normalized_value,
        ):
            raise ValueError(
                "tenant_code must contain lowercase letters, "
                "numbers, and single hyphens only"
            )

        return normalized_value

    @field_validator("admin_email")
    @classmethod
    def validate_admin_email(cls, value: EmailStr) -> str:
        normalized_email = str(value).strip().lower()
        local_part, separator, domain = normalized_email.rpartition("@")

        if not separator or not local_part:
            raise ValueError(
                "admin email is not a valid email address"
            )

        if domain != "gmail.com":
            raise ValueError(
                "admin email must be a Gmail address "
                "ending with @gmail.com"
            )

        return normalized_email

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError(
                "password must contain at least one uppercase letter"
            )

        if not re.search(r"[a-z]", value):
            raise ValueError(
                "password must contain at least one lowercase letter"
            )

        if not re.search(r"\d", value):
            raise ValueError(
                "password must contain at least one number"
            )

        return value

    @model_validator(mode="after")
    def validate_matching_passwords(self):
        if self.password != self.confirm_password:
            raise ValueError("passwords do not match")

        return self
