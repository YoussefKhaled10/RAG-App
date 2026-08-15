import asyncio
import socket
import ssl
from typing import Any

import asyncpg

from .BaseDatabaseAdapter import (
    BaseDatabaseAdapter,
    ColumnMetadata,
    ConnectionTestResult,
    DatabaseAdapterError,
    ForeignKeyMetadata,
    PrimaryKeyMetadata,
    RelationshipMetadata,
    SchemaDiscoveryResult,
    SchemaMetadata,
    TableMetadata,
)


class PostgreSQLAdapter(BaseDatabaseAdapter):
    """Open short-lived, read-only PostgreSQL connections safely."""

    _SCHEMAS_QUERY = """
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
          AND schema_name NOT LIKE 'pg_toast%'
          AND schema_name NOT LIKE 'pg_temp_%'
        ORDER BY schema_name
    """

    _TABLES_QUERY = """
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = ANY($1::text[])
          AND table_type IN ('BASE TABLE', 'VIEW', 'FOREIGN')
        ORDER BY table_schema, table_name
    """

    _COLUMNS_QUERY = """
        SELECT
            table_schema,
            table_name,
            column_name,
            ordinal_position,
            data_type,
            udt_name,
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            datetime_precision
        FROM information_schema.columns
        WHERE table_schema = ANY($1::text[])
        ORDER BY table_schema, table_name, ordinal_position
    """

    _PRIMARY_KEYS_QUERY = """
        SELECT
            tc.table_schema,
            tc.table_name,
            tc.constraint_name,
            kcu.column_name,
            kcu.ordinal_position
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON kcu.constraint_catalog = tc.constraint_catalog
         AND kcu.constraint_schema = tc.constraint_schema
         AND kcu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = ANY($1::text[])
        ORDER BY
            tc.table_schema,
            tc.table_name,
            tc.constraint_name,
            kcu.ordinal_position
    """

    _FOREIGN_KEYS_QUERY = """
        SELECT
            kcu.table_schema,
            kcu.table_name,
            kcu.constraint_name,
            kcu.column_name,
            kcu.ordinal_position,
            referenced_kcu.table_schema AS referenced_table_schema,
            referenced_kcu.table_name AS referenced_table_name,
            referenced_kcu.column_name AS referenced_column_name,
            rc.update_rule,
            rc.delete_rule
        FROM information_schema.referential_constraints AS rc
        JOIN information_schema.key_column_usage AS kcu
          ON kcu.constraint_catalog = rc.constraint_catalog
         AND kcu.constraint_schema = rc.constraint_schema
         AND kcu.constraint_name = rc.constraint_name
        JOIN information_schema.key_column_usage AS referenced_kcu
          ON referenced_kcu.constraint_catalog = rc.unique_constraint_catalog
         AND referenced_kcu.constraint_schema = rc.unique_constraint_schema
         AND referenced_kcu.constraint_name = rc.unique_constraint_name
         AND referenced_kcu.ordinal_position = kcu.position_in_unique_constraint
        WHERE kcu.table_schema = ANY($1::text[])
        ORDER BY
            kcu.table_schema,
            kcu.table_name,
            kcu.constraint_name,
            kcu.ordinal_position
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        ssl_mode: str = "prefer",
        connect_timeout_seconds: float = 10.0,
        statement_timeout_milliseconds: int = 5000,
    ) -> None:
        self.host = str(host).strip()
        self.port = int(port)
        self.database_name = str(database_name).strip()
        self.username = str(username).strip()
        self.password = str(password)
        self.ssl_mode = str(ssl_mode).strip().lower()
        self.connect_timeout_seconds = max(
            float(connect_timeout_seconds),
            1.0,
        )
        self.statement_timeout_milliseconds = max(
            int(statement_timeout_milliseconds),
            1000,
        )
        self._connection: asyncpg.Connection | None = None

    def _connection_options(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database_name,
            "user": self.username,
            "password": self.password,
            "ssl": self.ssl_mode,
            "timeout": self.connect_timeout_seconds,
            "server_settings": {
                "application_name": "rag_runtime_database",
                "statement_timeout": str(
                    self.statement_timeout_milliseconds
                ),
                # Enforce read-only behavior for this test session.
                "default_transaction_read_only": "on",
            },
        }

    async def _connect(self) -> asyncpg.Connection:
        self._connection = await asyncpg.connect(
            **self._connection_options()
        )
        return self._connection

    @staticmethod
    def _safe_error(exc: Exception) -> tuple[str, str]:
        if isinstance(exc, asyncpg.InvalidPasswordError):
            return (
                "authentication_failed",
                "Database authentication failed",
            )
        if isinstance(exc, asyncpg.InvalidCatalogNameError):
            return (
                "database_not_found",
                "The configured database does not exist",
            )
        if isinstance(exc, asyncpg.InsufficientPrivilegeError):
            return (
                "permission_denied",
                "The database user does not have the required permissions",
            )
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
            return (
                "connection_timeout",
                "Database connection timed out",
            )
        if isinstance(exc, ssl.SSLError):
            return (
                "ssl_error",
                "Database SSL negotiation or verification failed",
            )
        if isinstance(exc, socket.gaierror):
            return (
                "host_unreachable",
                "Database host could not be resolved",
            )
        if isinstance(exc, ConnectionRefusedError):
            return (
                "connection_refused",
                "Database connection was refused",
            )
        if isinstance(exc, OSError):
            return (
                "host_unreachable",
                "Database host could not be reached",
            )
        if isinstance(exc, asyncpg.PostgresError):
            return (
                "database_error",
                "PostgreSQL rejected the database operation",
            )
        return (
            "connection_failed",
            "Database operation failed",
        )

    async def test_connection(self) -> ConnectionTestResult:
        try:
            connection = await self._connect()

            probe = await connection.fetchval("SELECT 1")
            if probe != 1:
                return ConnectionTestResult(
                    success=False,
                    error_code="unexpected_probe_result",
                    message="Database connection probe returned an invalid result",
                )

            read_only_value = await connection.fetchval(
                "SELECT current_setting('transaction_read_only')"
            )
            read_only = str(read_only_value).lower() == "on"

            ssl_in_use = await connection.fetchval(
                "SELECT ssl FROM pg_stat_ssl "
                "WHERE pid = pg_backend_pid()"
            )
            server_version = await connection.fetchval(
                "SHOW server_version"
            )

            if not read_only:
                return ConnectionTestResult(
                    success=False,
                    error_code="read_only_not_enforced",
                    message="The test session could not be made read-only",
                    read_only=False,
                    ssl_in_use=(
                        bool(ssl_in_use)
                        if ssl_in_use is not None
                        else None
                    ),
                    server_version=str(server_version),
                )

            return ConnectionTestResult(
                success=True,
                message="Database connection tested successfully",
                read_only=True,
                ssl_in_use=(
                    bool(ssl_in_use)
                    if ssl_in_use is not None
                    else None
                ),
                server_version=str(server_version),
            )
        except Exception as exc:
            error_code, message = self._safe_error(exc)
            return ConnectionTestResult(
                success=False,
                error_code=error_code,
                message=message,
            )
        finally:
            await self.close()

    async def discover_schema(self) -> SchemaDiscoveryResult:
        """Read PostgreSQL metadata without reading any application rows."""
        try:
            connection = await self._connect()
            schema_rows = await connection.fetch(self._SCHEMAS_QUERY)
            schema_names = [str(row["schema_name"]) for row in schema_rows]

            if not schema_names:
                return SchemaDiscoveryResult()

            table_rows = await connection.fetch(
                self._TABLES_QUERY,
                schema_names,
            )
            column_rows = await connection.fetch(
                self._COLUMNS_QUERY,
                schema_names,
            )
            primary_key_rows = await connection.fetch(
                self._PRIMARY_KEYS_QUERY,
                schema_names,
            )
            foreign_key_rows = await connection.fetch(
                self._FOREIGN_KEYS_QUERY,
                schema_names,
            )

            schemas_by_name = {
                name: SchemaMetadata(schema_name=name)
                for name in schema_names
            }
            tables_by_key: dict[tuple[str, str], TableMetadata] = {}

            for row in table_rows:
                schema_name = str(row["table_schema"])
                table_name = str(row["table_name"])
                table = TableMetadata(
                    schema_name=schema_name,
                    table_name=table_name,
                    table_type=str(row["table_type"]),
                )
                tables_by_key[(schema_name, table_name)] = table
                schemas_by_name[schema_name].tables.append(table)

            for row in column_rows:
                key = (
                    str(row["table_schema"]),
                    str(row["table_name"]),
                )
                table = tables_by_key.get(key)
                if table is None:
                    continue
                table.columns.append(
                    ColumnMetadata(
                        column_name=str(row["column_name"]),
                        ordinal_position=int(row["ordinal_position"]),
                        data_type=str(row["data_type"]),
                        udt_name=str(row["udt_name"]),
                        is_nullable=str(row["is_nullable"]).upper() == "YES",
                        column_default=row["column_default"],
                        character_maximum_length=row[
                            "character_maximum_length"
                        ],
                        numeric_precision=row["numeric_precision"],
                        numeric_scale=row["numeric_scale"],
                        datetime_precision=row["datetime_precision"],
                    )
                )

            primary_keys_by_constraint: dict[
                tuple[str, str, str], list[str]
            ] = {}
            for row in primary_key_rows:
                key = (
                    str(row["table_schema"]),
                    str(row["table_name"]),
                    str(row["constraint_name"]),
                )
                primary_keys_by_constraint.setdefault(key, []).append(
                    str(row["column_name"])
                )

            for (
                schema_name,
                table_name,
                constraint_name,
            ), columns in primary_keys_by_constraint.items():
                table = tables_by_key.get((schema_name, table_name))
                if table is None:
                    continue
                table.primary_keys.append(
                    PrimaryKeyMetadata(
                        constraint_name=constraint_name,
                        columns=columns,
                    )
                )

            foreign_keys_by_constraint: dict[
                tuple[str, str, str], dict[str, Any]
            ] = {}
            for row in foreign_key_rows:
                key = (
                    str(row["table_schema"]),
                    str(row["table_name"]),
                    str(row["constraint_name"]),
                )
                grouped = foreign_keys_by_constraint.setdefault(
                    key,
                    {
                        "columns": [],
                        "referenced_schema_name": str(
                            row["referenced_table_schema"]
                        ),
                        "referenced_table_name": str(
                            row["referenced_table_name"]
                        ),
                        "referenced_columns": [],
                        "update_rule": str(row["update_rule"]),
                        "delete_rule": str(row["delete_rule"]),
                    },
                )
                grouped["columns"].append(str(row["column_name"]))
                grouped["referenced_columns"].append(
                    str(row["referenced_column_name"])
                )

            relationships: list[RelationshipMetadata] = []
            for (
                schema_name,
                table_name,
                constraint_name,
            ), values in foreign_keys_by_constraint.items():
                table = tables_by_key.get((schema_name, table_name))
                if table is None:
                    continue
                foreign_key = ForeignKeyMetadata(
                    constraint_name=constraint_name,
                    columns=values["columns"],
                    referenced_schema_name=values[
                        "referenced_schema_name"
                    ],
                    referenced_table_name=values[
                        "referenced_table_name"
                    ],
                    referenced_columns=values["referenced_columns"],
                    update_rule=values["update_rule"],
                    delete_rule=values["delete_rule"],
                )
                table.foreign_keys.append(foreign_key)
                relationships.append(
                    RelationshipMetadata(
                        constraint_name=constraint_name,
                        source_schema_name=schema_name,
                        source_table_name=table_name,
                        source_columns=values["columns"],
                        target_schema_name=values[
                            "referenced_schema_name"
                        ],
                        target_table_name=values[
                            "referenced_table_name"
                        ],
                        target_columns=values["referenced_columns"],
                        update_rule=values["update_rule"],
                        delete_rule=values["delete_rule"],
                    )
                )

            return SchemaDiscoveryResult(
                schemas=list(schemas_by_name.values()),
                relationships=relationships,
            )
        except Exception as exc:
            error_code, message = self._safe_error(exc)
            raise DatabaseAdapterError(error_code, message) from exc
        finally:
            await self.close()

    async def execute_read_query(
        self,
        query: str,
        parameters: list,
    ) -> list[dict]:
        """Execute only the validated SELECT built by the permission layer."""
        normalized_query = str(query).lstrip()
        if not normalized_query.upper().startswith("SELECT "):
            raise DatabaseAdapterError(
                "read_only_query_required",
                "Only read-only SELECT queries are permitted",
            )
        try:
            connection = await self._connect()
            transaction = connection.transaction(
                readonly=True,
                isolation="read_committed",
            )
            async with transaction:
                rows = await connection.fetch(query, *parameters)
            return [dict(row) for row in rows]
        except DatabaseAdapterError:
            raise
        except Exception as exc:
            error_code, message = self._safe_error(exc)
            raise DatabaseAdapterError(error_code, message) from exc
        finally:
            await self.close()

    async def close(self) -> None:
        if self._connection is not None:
            try:
                if not self._connection.is_closed():
                    await self._connection.close()
            finally:
                self._connection = None
