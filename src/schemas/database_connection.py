from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

DatabaseType = Literal["postgresql"]
SSLMode = Literal[
    "disable", "allow", "prefer", "require", "verify-ca", "verify-full"
]
ConnectionStatus = Literal["untested", "connected", "failed", "disabled"]


def _normalize_required(value: str, field_name: str) -> str:
    normalized = " ".join(str(value).split())
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


class DatabaseConnectionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    connection_name: str = Field(..., min_length=2, max_length=150)
    database_type: DatabaseType = "postgresql"
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(default=5432, ge=1, le=65535)
    database_name: str = Field(..., min_length=1, max_length=150)
    username: str = Field(..., min_length=1, max_length=150)
    password: str = Field(..., min_length=1, max_length=1024)
    ssl_mode: SSLMode = "prefer"

    @field_validator("connection_name", "host", "database_name", "username")
    @classmethod
    def normalize_required_text(cls, value: str, info) -> str:
        normalized = _normalize_required(value, info.field_name)
        return normalized.lower() if info.field_name == "host" else normalized


class DatabaseConnectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    connection_name: str | None = Field(default=None, min_length=2, max_length=150)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    database_name: str | None = Field(default=None, min_length=1, max_length=150)
    username: str | None = Field(default=None, min_length=1, max_length=150)
    password: str | None = Field(default=None, min_length=1, max_length=1024)
    ssl_mode: SSLMode | None = None

    @field_validator("connection_name", "host", "database_name", "username")
    @classmethod
    def normalize_optional_text(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        normalized = _normalize_required(value, info.field_name)
        return normalized.lower() if info.field_name == "host" else normalized

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("at least one field must be provided")
        return self


class DatabaseConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    connection_id: int
    connection_uuid: UUID
    tenant_id: UUID
    created_by_user_id: UUID | None = None
    connection_name: str
    database_type: DatabaseType
    host: str
    port: int
    database_name: str
    username: str
    ssl_mode: SSLMode
    connection_status: ConnectionStatus
    has_password: bool = True
    last_tested_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class DatabaseConnectionListResponse(BaseModel):
    items: list[DatabaseConnectionResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)


class DatabaseConnectionTestResponse(BaseModel):
    connection_id: int
    success: bool
    connection_status: Literal["connected", "failed"]
    message: str
    error_code: str | None = None
    read_only: bool | None = None
    ssl_in_use: bool | None = None
    server_version: str | None = None
    tested_at: datetime
