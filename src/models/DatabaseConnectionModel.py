from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .BaseDataModel import BaseDataModel
from .db_schemes import DatabaseConnection, Tenant, User


class DatabaseConnectionModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "DatabaseConnectionModel":
        return cls(db_client=db_client)

    @staticmethod
    def _normalize_name(value: str) -> str:
        return " ".join(str(value).split())

    @staticmethod
    def _normalize_host(value: str) -> str:
        return str(value).strip().lower()

    async def create_connection(
        self,
        connection: DatabaseConnection,
    ) -> DatabaseConnection:
        try:
            async with self.db_client() as session:
                tenant_query = select(Tenant.tenant_id).where(
                    Tenant.tenant_id == connection.tenant_id,
                    Tenant.tenant_status == "active",
                )
                tenant_result = await session.execute(tenant_query)
                if tenant_result.scalar_one_or_none() is None:
                    raise ValueError("active tenant not found")

                if connection.created_by_user_id is not None:
                    user_query = select(User.user_id).where(
                        User.user_id == connection.created_by_user_id,
                        User.tenant_id == connection.tenant_id,
                        User.user_status == "active",
                    )
                    user_result = await session.execute(user_query)
                    if user_result.scalar_one_or_none() is None:
                        raise ValueError(
                            "active creator user not found in tenant"
                        )

                connection.connection_name = self._normalize_name(
                    connection.connection_name
                )
                connection.host = self._normalize_host(connection.host)
                connection.database_name = str(
                    connection.database_name
                ).strip()
                connection.username = str(connection.username).strip()

                session.add(connection)
                await session.commit()
                await session.refresh(connection)
                return connection
        except IntegrityError as exc:
            raise ValueError(
                "connection name already exists in this tenant"
            ) from exc
        except SQLAlchemyError:
            raise

    async def get_connection_by_id(
        self,
        tenant_id: UUID,
        connection_id: int,
    ) -> DatabaseConnection | None:
        async with self.db_client() as session:
            query = select(DatabaseConnection).where(
                DatabaseConnection.connection_id == connection_id,
                DatabaseConnection.tenant_id == tenant_id,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_connection_by_uuid(
        self,
        tenant_id: UUID,
        connection_uuid: UUID,
    ) -> DatabaseConnection | None:
        async with self.db_client() as session:
            query = select(DatabaseConnection).where(
                DatabaseConnection.connection_uuid == connection_uuid,
                DatabaseConnection.tenant_id == tenant_id,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_connection_by_name(
        self,
        tenant_id: UUID,
        connection_name: str,
    ) -> DatabaseConnection | None:
        normalized_name = self._normalize_name(connection_name)
        async with self.db_client() as session:
            query = select(DatabaseConnection).where(
                DatabaseConnection.tenant_id == tenant_id,
                DatabaseConnection.connection_name == normalized_name,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_tenant_connections(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 10,
        include_disabled: bool = False,
    ) -> tuple[list[DatabaseConnection], int, int]:
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)

        filters = [DatabaseConnection.tenant_id == tenant_id]
        if not include_disabled:
            filters.append(
                DatabaseConnection.connection_status != "disabled"
            )

        async with self.db_client() as session:
            count_query = select(
                func.count(DatabaseConnection.connection_id)
            ).where(*filters)
            count_result = await session.execute(count_query)
            total_connections = count_result.scalar_one()
            total_pages = (
                total_connections + safe_page_size - 1
            ) // safe_page_size

            query = (
                select(DatabaseConnection)
                .where(*filters)
                .order_by(DatabaseConnection.created_at.desc())
                .offset((safe_page - 1) * safe_page_size)
                .limit(safe_page_size)
            )
            result = await session.execute(query)
            connections = list(result.scalars().all())
            return connections, total_connections, total_pages

    async def update_connection(
        self,
        tenant_id: UUID,
        connection_id: int,
        *,
        connection_name: str | None = None,
        host: str | None = None,
        port: int | None = None,
        database_name: str | None = None,
        username: str | None = None,
        encrypted_password: str | None = None,
        ssl_mode: str | None = None,
        connection_status: str | None = None,
    ) -> DatabaseConnection | None:
        try:
            async with self.db_client() as session:
                query = select(DatabaseConnection).where(
                    DatabaseConnection.connection_id == connection_id,
                    DatabaseConnection.tenant_id == tenant_id,
                )
                result = await session.execute(query)
                connection = result.scalar_one_or_none()
                if connection is None:
                    return None

                if connection_name is not None:
                    connection.connection_name = self._normalize_name(
                        connection_name
                    )
                if host is not None:
                    connection.host = self._normalize_host(host)
                if port is not None:
                    connection.port = int(port)
                if database_name is not None:
                    connection.database_name = database_name.strip()
                if username is not None:
                    connection.username = username.strip()
                if encrypted_password is not None:
                    connection.encrypted_password = encrypted_password
                if ssl_mode is not None:
                    connection.ssl_mode = ssl_mode
                if connection_status is not None:
                    connection.connection_status = connection_status

                await session.commit()
                await session.refresh(connection)
                return connection
        except IntegrityError as exc:
            raise ValueError(
                "connection name already exists in this tenant"
            ) from exc
        except SQLAlchemyError:
            raise

    async def update_test_status(
        self,
        tenant_id: UUID,
        connection_id: int,
        *,
        connection_status: str,
        last_tested_at,
        last_success_at=None,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> DatabaseConnection | None:
        async with self.db_client() as session:
            query = select(DatabaseConnection).where(
                DatabaseConnection.connection_id == connection_id,
                DatabaseConnection.tenant_id == tenant_id,
            )
            result = await session.execute(query)
            connection = result.scalar_one_or_none()
            if connection is None:
                return None

            connection.connection_status = connection_status
            connection.last_tested_at = last_tested_at
            connection.last_success_at = last_success_at
            connection.last_error_code = last_error_code
            connection.last_error_message = last_error_message

            await session.commit()
            await session.refresh(connection)
            return connection

    async def delete_connection(
        self,
        tenant_id: UUID,
        connection_id: int,
    ) -> bool:
        try:
            async with self.db_client() as session:
                query = select(DatabaseConnection).where(
                    DatabaseConnection.connection_id == connection_id,
                    DatabaseConnection.tenant_id == tenant_id,
                )
                result = await session.execute(query)
                connection = result.scalar_one_or_none()
                if connection is None:
                    return False

                await session.delete(connection)
                await session.commit()
                return True
        except SQLAlchemyError:
            raise

    async def connection_exists(
        self,
        tenant_id: UUID,
        connection_id: int,
    ) -> bool:
        async with self.db_client() as session:
            query = select(DatabaseConnection.connection_id).where(
                DatabaseConnection.connection_id == connection_id,
                DatabaseConnection.tenant_id == tenant_id,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none() is not None
