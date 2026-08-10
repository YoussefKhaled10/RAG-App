from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class ConnectionTestResult:
    success: bool
    message: str
    error_code: str | None = None
    read_only: bool | None = None
    ssl_in_use: bool | None = None
    server_version: str | None = None


class BaseDatabaseAdapter(ABC):
    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """Test connectivity and return a sanitized result."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close any open connection held by the adapter."""
        raise NotImplementedError
