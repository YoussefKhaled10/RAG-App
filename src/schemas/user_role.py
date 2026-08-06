from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from schemas.role import RoleResponse


class UserRoleAssign(BaseModel):
    """Request schema for assigning one role to one user."""

    model_config = ConfigDict(
        extra="forbid",
    )

    role_id: UUID


class UserRolesBulkAssign(BaseModel):
    """Request schema for assigning multiple roles to one user."""

    model_config = ConfigDict(
        extra="forbid",
    )

    role_ids: list[UUID] = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    @model_validator(mode="after")
    def validate_unique_role_ids(
        self,
    ) -> "UserRolesBulkAssign":
        unique_role_ids = list(
            dict.fromkeys(self.role_ids)
        )

        if len(unique_role_ids) != len(self.role_ids):
            raise ValueError(
                "role_ids must not contain duplicates"
            )

        return self


class UserRoleResponse(BaseModel):
    """Response schema for one user-role assignment."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    user_id: UUID
    role_id: UUID
    assigned_at: datetime


class UserRolesResponse(BaseModel):
    """Response containing all roles assigned to a user."""

    user_id: UUID
    roles: list[RoleResponse] = Field(
        default_factory=list,
    )
    total: int = Field(
        ...,
        ge=0,
    )


class UserRoleOperationResponse(BaseModel):
    """Response returned after removing one role."""

    success: bool
    message: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )
    user_id: UUID
    role_id: UUID
