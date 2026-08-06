from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class ProjectCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    project_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        examples=["Employment Laws"],
    )

    project_description: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator("project_name")
    @classmethod
    def normalize_project_name(
        cls,
        value: str,
    ) -> str:
        normalized_value = " ".join(value.split())
        if not normalized_value:
            raise ValueError(
                "project_name cannot be empty"
            )
        return normalized_value

    @field_validator("project_description")
    @classmethod
    def normalize_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        normalized_value = " ".join(value.split())
        return normalized_value or None


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    project_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )

    project_description: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator("project_name")
    @classmethod
    def normalize_project_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        normalized_value = " ".join(value.split())
        if not normalized_value:
            raise ValueError(
                "project_name cannot be empty"
            )
        return normalized_value

    @field_validator("project_description")
    @classmethod
    def normalize_description(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        normalized_value = " ".join(value.split())
        return normalized_value or None

    @model_validator(mode="after")
    def require_at_least_one_field(
        self,
    ) -> "ProjectUpdate":
        if not self.model_fields_set:
            raise ValueError(
                "at least one field must be provided"
            )
        return self


class ProjectResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    project_id: int
    project_uuid: UUID
    tenant_id: UUID
    project_name: str
    project_description: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)
