import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .database_connection import (
    DatabaseColumnResponse,
    DatabasePrimaryKeyResponse,
    DatabaseForeignKeyResponse,
    DatabaseRelationshipResponse,
)


MaskingType = Literal[
    "none",
    "full",
    "partial",
    "email",
    "phone",
    "last4",
    "hash",
    "unmasked",
]
FilterOperator = Literal[
    "eq",
    "ne",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "not_in",
    "contains",
    "starts_with",
    "ends_with",
    "is_null",
    "not_null",
]
FilterValueSource = Literal[
    "literal",
    "current_user_id",
    "current_tenant_id",
    "current_user_email",
]
AggregateFunction = Literal["count", "sum", "avg", "min", "max"]
SortDirection = Literal["asc", "desc"]


def _identifier(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized


def _validate_scalar(value: Any, field_name: str) -> None:
    if not isinstance(value, (str, int, float, bool)):
        raise ValueError(f"{field_name} must contain scalar JSON values")
    if isinstance(value, str) and len(value) > 4000:
        raise ValueError(f"{field_name} strings cannot exceed 4000 characters")


class DatabaseColumnPermissionUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    column_name: str = Field(..., min_length=1, max_length=128)
    can_read: bool = False
    can_filter: bool = False
    can_aggregate: bool = False
    is_sensitive: bool = False
    masking_type: MaskingType = "none"

    @field_validator("column_name")
    @classmethod
    def validate_column_name(cls, value: str) -> str:
        return _identifier(value, "column_name")

    @model_validator(mode="after")
    def validate_capabilities(self):
        if not (self.can_read or self.can_filter or self.can_aggregate):
            raise ValueError(
                "at least one of can_read, can_filter, or can_aggregate "
                "must be enabled"
            )
        if not self.can_read and self.masking_type != "none":
            raise ValueError("masking requires can_read")
        if self.is_sensitive and self.can_read and self.masking_type == "none":
            raise ValueError(
                "sensitive columns require a masking type; use 'unmasked' "
                "only for an explicit unmasked grant"
            )
        if not self.is_sensitive and self.masking_type != "none":
            raise ValueError("masking_type requires is_sensitive=true")
        return self


class DatabaseRowFilterUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    filter_name: str = Field(..., min_length=1, max_length=150)
    column_name: str = Field(..., min_length=1, max_length=128)
    operator: FilterOperator
    value_source: FilterValueSource = "literal"
    value: Any | None = None
    enabled: bool = True

    @field_validator("filter_name", "column_name")
    @classmethod
    def validate_names(cls, value: str, info) -> str:
        return _identifier(value, info.field_name)

    @model_validator(mode="after")
    def validate_filter_value(self):
        no_value_operator = self.operator in {"is_null", "not_null"}
        if no_value_operator:
            if self.value is not None:
                raise ValueError(f"{self.operator} does not accept a value")
            if self.value_source != "literal":
                raise ValueError(
                    f"{self.operator} must use value_source='literal'"
                )
            return self

        if self.value_source == "literal":
            if self.value is None:
                raise ValueError("literal row filters require a value")
            if self.operator in {"in", "not_in"}:
                if not isinstance(self.value, list) or not self.value:
                    raise ValueError(f"{self.operator} requires a non-empty list")
                if len(self.value) > 100:
                    raise ValueError("row filter lists cannot exceed 100 values")
                for item in self.value:
                    _validate_scalar(item, "row filter")
            else:
                _validate_scalar(self.value, "row filter")
        else:
            if self.value is not None:
                raise ValueError(
                    "context row filters cannot include a literal value"
                )
            if self.operator not in {"eq", "ne"}:
                raise ValueError(
                    "context row filters support only eq and ne operators"
                )
        return self


class DatabaseTablePermissionUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_name: str = Field(..., min_length=1, max_length=128)
    table_name: str = Field(..., min_length=1, max_length=128)
    can_read: bool = True
    columns: list[DatabaseColumnPermissionUpsert] = Field(
        default_factory=list,
        max_length=500,
    )
    row_filters: list[DatabaseRowFilterUpsert] = Field(
        default_factory=list,
        max_length=50,
    )

    @field_validator("schema_name", "table_name")
    @classmethod
    def validate_table_names(cls, value: str, info) -> str:
        return _identifier(value, info.field_name)

    @model_validator(mode="after")
    def validate_nested_uniqueness(self):
        column_names = [item.column_name for item in self.columns]
        if len(column_names) != len(set(column_names)):
            raise ValueError("column permissions must be unique per table")
        filter_names = [item.filter_name for item in self.row_filters]
        if len(filter_names) != len(set(filter_names)):
            raise ValueError("row filter names must be unique per table")
        if not self.can_read and (self.columns or self.row_filters):
            raise ValueError(
                "a denied table cannot contain column grants or row filters"
            )
        return self


class DatabaseRolePermissionUpsert(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tables: list[DatabaseTablePermissionUpsert] = Field(
        default_factory=list,
        max_length=500,
    )

    @model_validator(mode="after")
    def validate_table_uniqueness(self):
        table_keys = [
            (item.schema_name, item.table_name)
            for item in self.tables
        ]
        if len(table_keys) != len(set(table_keys)):
            raise ValueError("table permissions must be unique per role")
        return self


class DatabaseColumnPermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    column_permission_id: UUID
    column_name: str
    can_read: bool
    can_filter: bool
    can_aggregate: bool
    is_sensitive: bool
    masking_type: MaskingType
    created_at: datetime
    updated_at: datetime | None = None


class DatabaseRowFilterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row_filter_id: UUID
    filter_name: str
    column_name: str
    operator: FilterOperator
    value_source: FilterValueSource
    value: Any | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime | None = None


class DatabaseTablePermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    table_permission_id: UUID
    tenant_id: UUID
    connection_id: int
    role_id: UUID
    role_name: str | None = None
    schema_name: str
    table_name: str
    can_read: bool
    columns: list[DatabaseColumnPermissionResponse] = Field(default_factory=list)
    row_filters: list[DatabaseRowFilterResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None


class DatabasePermissionCatalogResponse(BaseModel):
    connection_id: int
    policies: list[DatabaseTablePermissionResponse] = Field(default_factory=list)
    total: int = Field(..., ge=0)


class PermissionFilteredColumnResponse(DatabaseColumnResponse):
    can_read: bool
    can_filter: bool
    can_aggregate: bool
    is_sensitive: bool
    masking_type: MaskingType


class PermissionFilteredTableResponse(BaseModel):
    schema_name: str
    table_name: str
    table_type: str
    can_read: bool = True
    row_filters_enforced: int = Field(default=0, ge=0)
    columns: list[PermissionFilteredColumnResponse] = Field(default_factory=list)
    primary_keys: list[DatabasePrimaryKeyResponse] = Field(default_factory=list)
    foreign_keys: list[DatabaseForeignKeyResponse] = Field(default_factory=list)


class PermissionFilteredSchemaResponse(BaseModel):
    schema_name: str
    tables: list[PermissionFilteredTableResponse] = Field(default_factory=list)


class PermissionFilteredDatabaseSchemaResponse(BaseModel):
    connection_id: int
    database_name: str
    user_id: UUID | None = None
    role_ids: list[UUID] = Field(default_factory=list)
    tenant_admin_bypass: bool = False
    schema_hash: str
    synced_at: datetime
    schema_count: int = Field(..., ge=0)
    table_count: int = Field(..., ge=0)
    column_count: int = Field(..., ge=0)
    primary_key_count: int = Field(..., ge=0)
    foreign_key_count: int = Field(..., ge=0)
    relationship_count: int = Field(..., ge=0)
    schemas: list[PermissionFilteredSchemaResponse] = Field(default_factory=list)
    relationships: list[DatabaseRelationshipResponse] = Field(default_factory=list)


class DatabaseQueryFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    column_name: str = Field(..., min_length=1, max_length=128)
    operator: FilterOperator
    value: Any | None = None

    @field_validator("column_name")
    @classmethod
    def validate_column_name(cls, value: str) -> str:
        return _identifier(value, "column_name")

    @model_validator(mode="after")
    def validate_value(self):
        if self.operator in {"is_null", "not_null"}:
            if self.value is not None:
                raise ValueError(f"{self.operator} does not accept a value")
        elif self.value is None:
            raise ValueError(f"{self.operator} requires a value")
        elif self.operator in {"in", "not_in"}:
            if not isinstance(self.value, list) or not self.value:
                raise ValueError(f"{self.operator} requires a non-empty list")
            if len(self.value) > 100:
                raise ValueError("filter lists cannot exceed 100 values")
            for item in self.value:
                _validate_scalar(item, "query filter")
        elif self.value is not None:
            _validate_scalar(self.value, "query filter")
        return self


class DatabaseQueryAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    function: AggregateFunction
    column_name: str | None = Field(default=None, min_length=1, max_length=128)
    alias: str | None = Field(default=None, min_length=1, max_length=63)

    @field_validator("column_name")
    @classmethod
    def validate_optional_column(cls, value: str | None) -> str | None:
        return None if value is None else _identifier(value, "column_name")

    @field_validator("alias")
    @classmethod
    def validate_alias(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value):
            raise ValueError("alias must be a safe SQL-style identifier")
        return value

    @model_validator(mode="after")
    def validate_aggregate(self):
        if self.function != "count" and self.column_name is None:
            raise ValueError(f"{self.function} requires column_name")
        return self


class DatabaseQueryOrderBy(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    field: str = Field(..., min_length=1, max_length=128)
    direction: SortDirection = "asc"

    @field_validator("field")
    @classmethod
    def validate_field(cls, value: str) -> str:
        return _identifier(value, "field")


class SecureDatabaseQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_name: str = Field(..., min_length=1, max_length=128)
    table_name: str = Field(..., min_length=1, max_length=128)
    columns: list[str] = Field(default_factory=list, max_length=100)
    filters: list[DatabaseQueryFilter] = Field(default_factory=list, max_length=50)
    aggregates: list[DatabaseQueryAggregate] = Field(
        default_factory=list,
        max_length=20,
    )
    order_by: list[DatabaseQueryOrderBy] = Field(default_factory=list, max_length=10)
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0, le=1_000_000)

    @field_validator("schema_name", "table_name")
    @classmethod
    def validate_table_names(cls, value: str, info) -> str:
        return _identifier(value, info.field_name)

    @field_validator("columns")
    @classmethod
    def validate_columns(cls, values: list[str]) -> list[str]:
        normalized = [_identifier(value, "column_name") for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("selected columns must be unique")
        return normalized

    @model_validator(mode="after")
    def require_output(self):
        if not self.columns and not self.aggregates:
            raise ValueError("select at least one column or aggregate")
        aliases = [item.alias for item in self.aggregates if item.alias]
        if len(aliases) != len(set(aliases)):
            raise ValueError("aggregate aliases must be unique")
        return self


class SecureDatabaseQueryResponse(BaseModel):
    connection_id: int
    schema_name: str
    table_name: str
    columns: list[str]
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = Field(..., ge=0)
    limit: int = Field(..., ge=1, le=1000)
    offset: int = Field(..., ge=0)
    masked_columns: list[str] = Field(default_factory=list)
    row_filters_applied: int = Field(default=0, ge=0)
