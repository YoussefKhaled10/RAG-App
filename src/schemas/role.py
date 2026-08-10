from datetime import datetime
from uuid import UUID
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class RoleCreate(BaseModel):
    """
    Request schema for creating a role.
    """
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
    role_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        examples=["Document Manager"],
    )
    role_description: str | None = Field(
        default=None,
        max_length=500,
        examples=[
            "Can upload and manage documents"
        ],
    )

    @field_validator("role_name")
    @classmethod
    def normalize_role_name(
        cls,
        value: str,
    ) -> str:
        normalized_value = " ".join(
            value.split()
        )
        if not normalized_value:
            raise ValueError(
                "role_name cannot be empty"
            )
        return normalized_value

    @field_validator("role_description")
    @classmethod
    def normalize_role_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        normalized_value = " ".join(
            value.split()
        )
        return normalized_value or None


class RoleUpdate(BaseModel):
    """
    Request schema for updating a role.
    All fields are optional because the client
    may update only one field.
    """
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )
    role_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        examples=["Knowledge Base Manager"],
    )
    role_description: str | None = Field(
        default=None,
        max_length=500,
        examples=[
            "Can manage knowledge bases and uploaded files"
        ],
    )

    @field_validator("role_name")
    @classmethod
    def normalize_role_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        normalized_value = " ".join(
            value.split()
        )
        if not normalized_value:
            raise ValueError(
                "role_name cannot be empty"
            )
        return normalized_value

    @field_validator("role_description")
    @classmethod
    def normalize_role_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        normalized_value = " ".join(
            value.split()
        )
        return normalized_value or None


class RoleResponse(BaseModel):
    """
    Response schema returned by the API.
    """
    model_config = ConfigDict(
        from_attributes=True,
    )
    role_id: UUID
    tenant_id: UUID
    role_name: str
    role_description: str | None = None
    is_system_role: bool
    created_at: datetime
    updated_at: datetime | None = None


class RoleListResponse(BaseModel):
    """Paginated response containing tenant roles."""
    model_config = ConfigDict(
        from_attributes=True,
    )
    items: list[RoleResponse]
    total: int = Field(
        ...,
        ge=0,
    )
    page: int = Field(
        ...,
        ge=1,
    )
    page_size: int = Field(
        ...,
        ge=1,
        le=100,
    )
    total_pages: int = Field(
        ...,
        ge=0,
    )


class SystemRoleOption(BaseModel):
    role_id: UUID
    role_name: str
    description: str
    permissions: list[str] = Field(
        default_factory=list
    )


class SystemRoleCatalogResponse(BaseModel):
    items: list[SystemRoleOption]
    total: int = Field(..., ge=0)
