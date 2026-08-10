import asyncio
import socket
import ssl
from typing import Any

import asyncpg

from .BaseDatabaseAdapter import (
    BaseDatabaseAdapter,
    ConnectionTestResult,
)


class PostgreSQLAdapter(BaseDatabaseAdapter):
    """Open short-lived, read-only PostgreSQL connections safely."""

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
                "application_name": "legal_rag_runtime_connection_test",
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
                "PostgreSQL rejected the connection test",
            )
        return (
            "connection_failed",
            "Database connection test failed",
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

    async def close(self) -> None:
        if self._connection is not None:
            try:
                if not self._connection.is_closed():
                    await self._connection.close()
            finally:
                self._connection = None
