from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(slots=True)
class ConnectionTestResult:
    success: bool
    message: str
    error_code: str | None = None
    read_only: bool | None = None
    ssl_in_use: bool | None = None
    server_version: str | None = None


class DatabaseAdapterError(RuntimeError):
    """A sanitized runtime-database error safe to expose through the API."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


@dataclass(slots=True, frozen=True)
class ColumnMetadata:
    column_name: str
    ordinal_position: int
    data_type: str
    udt_name: str
    is_nullable: bool
    column_default: str | None = None
    character_maximum_length: int | None = None
    numeric_precision: int | None = None
    numeric_scale: int | None = None
    datetime_precision: int | None = None


@dataclass(slots=True, frozen=True)
class PrimaryKeyMetadata:
    constraint_name: str
    columns: list[str]


@dataclass(slots=True, frozen=True)
class ForeignKeyMetadata:
    constraint_name: str
    columns: list[str]
    referenced_schema_name: str
    referenced_table_name: str
    referenced_columns: list[str]
    update_rule: str
    delete_rule: str


@dataclass(slots=True, frozen=True)
class RelationshipMetadata:
    constraint_name: str
    source_schema_name: str
    source_table_name: str
    source_columns: list[str]
    target_schema_name: str
    target_table_name: str
    target_columns: list[str]
    update_rule: str
    delete_rule: str


@dataclass(slots=True)
class TableMetadata:
    schema_name: str
    table_name: str
    table_type: str
    columns: list[ColumnMetadata] = field(default_factory=list)
    primary_keys: list[PrimaryKeyMetadata] = field(default_factory=list)
    foreign_keys: list[ForeignKeyMetadata] = field(default_factory=list)


@dataclass(slots=True)
class SchemaMetadata:
    schema_name: str
    tables: list[TableMetadata] = field(default_factory=list)


@dataclass(slots=True)
class SchemaDiscoveryResult:
    schemas: list[SchemaMetadata] = field(default_factory=list)
    relationships: list[RelationshipMetadata] = field(default_factory=list)

    @property
    def schema_count(self) -> int:
        return len(self.schemas)

    @property
    def table_count(self) -> int:
        return sum(len(schema.tables) for schema in self.schemas)

    @property
    def column_count(self) -> int:
        return sum(
            len(table.columns)
            for schema in self.schemas
            for table in schema.tables
        )

    @property
    def primary_key_count(self) -> int:
        return sum(
            len(table.primary_keys)
            for schema in self.schemas
            for table in schema.tables
        )

    @property
    def foreign_key_count(self) -> int:
        return sum(
            len(table.foreign_keys)
            for schema in self.schemas
            for table in schema.tables
        )

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)


class BaseDatabaseAdapter(ABC):
    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """Test connectivity and return a sanitized result."""
        raise NotImplementedError

    @abstractmethod
    async def discover_schema(self) -> SchemaDiscoveryResult:
        """Discover queryable schemas, tables, and columns."""
        raise NotImplementedError

    @abstractmethod
    async def execute_read_query(
        self,
        query: str,
        parameters: list,
    ) -> list[dict]:
        """Execute a controller-built, parameterized read-only query."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close any open connection held by the adapter."""
        raise NotImplementedError
