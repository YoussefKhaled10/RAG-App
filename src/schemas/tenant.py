from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


VALID_TENANT_STATUSES = {
    "active",
    "inactive",
    "suspended",
}


class TenantCreate(BaseModel):
    """
    Validates the request body used to create a tenant.
    """
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    tenant_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        examples=["Tenant Name"],
    )

    tenant_code: str = Field(
        ...,
        min_length=2,
        max_length=100,
        pattern=r"^[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*$",
        examples=["tenant-code"],
    )

    tenant_settings: dict[str, Any] = Field(
        default_factory=dict,
        examples=[
            {
                "default_language": "ar",
                "timezone": "Africa/Cairo",
            }
        ],
    )

    @field_validator("tenant_name")
    @classmethod
    def validate_tenant_name(
        cls,
        value: str,
    ) -> str:
        normalized_value = " ".join(value.split())

        if not normalized_value:
            raise ValueError("tenant_name cannot be empty")

        return normalized_value

    @field_validator("tenant_code")
    @classmethod
    def normalize_tenant_code(
        cls,
        value: str,
    ) -> str:
        return value.strip().lower()


class TenantUpdate(BaseModel):
    """
    Validates the request body used to update a tenant.

    All fields are optional because the client may update
    only one field.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    tenant_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
        examples=["Updated Tenant Name"],
    )

    tenant_status: str | None = Field(
        default=None,
        examples=["active"],
    )

    tenant_settings: dict[str, Any] | None = Field(
        default=None,
        examples=[
            {
                "default_language": "ar",
                "timezone": "Africa/Cairo",
            }
        ],
    )

    @field_validator("tenant_name")
    @classmethod
    def validate_tenant_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized_value = " ".join(value.split())

        if not normalized_value:
            raise ValueError("tenant_name cannot be empty")

        return normalized_value

    @field_validator("tenant_status")
    @classmethod
    def validate_tenant_status(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip().lower()

        if normalized_value not in VALID_TENANT_STATUSES:
            raise ValueError(
                "tenant_status must be active, "
                "inactive, or suspended"
            )

        return normalized_value


class TenantResponse(BaseModel):
    """
    Defines the tenant data returned by the API.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    tenant_id: UUID
    tenant_name: str
    tenant_code: str
    tenant_status: str
    tenant_settings: dict[str, Any]

    created_at: datetime
    updated_at: datetime | None = None


class TenantListResponse(BaseModel):
    """
    Defines a paginated list of tenants.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    items: list[TenantResponse]
    total: int = Field(
        ...,
        ge=0,
    )

    offset: int = Field(
        default=0,
        ge=0,
    )

    limit: int = Field(
        default=100,
        ge=1,
        le=100,
    )