from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from .BaseDataModel import BaseDataModel
from .db_schemes import (
    DatabaseColumnPermission,
    DatabaseRowFilter,
    DatabaseTablePermission,
    Role,
)


class DatabasePermissionModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "DatabasePermissionModel":
        return cls(db_client=db_client)

    async def role_exists(
        self,
        tenant_id: UUID,
        role_id: UUID,
    ) -> bool:
        async with self.db_client() as session:
            query = select(Role.role_id).where(
                Role.tenant_id == tenant_id,
                Role.role_id == role_id,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none() is not None

    async def replace_role_policy(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
        role_id: UUID,
        tables: list[dict],
    ) -> list[DatabaseTablePermission]:
        async with self.db_client() as session:
            await session.execute(
                delete(DatabaseTablePermission).where(
                    DatabaseTablePermission.tenant_id == tenant_id,
                    DatabaseTablePermission.connection_id == connection_id,
                    DatabaseTablePermission.role_id == role_id,
                )
            )
            await session.flush()

            records: list[DatabaseTablePermission] = []
            for table_data in tables:
                table_permission = DatabaseTablePermission(
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                    role_id=role_id,
                    schema_name=table_data["schema_name"],
                    table_name=table_data["table_name"],
                    can_read=table_data["can_read"],
                )
                table_permission.column_permissions = [
                    DatabaseColumnPermission(
                        tenant_id=tenant_id,
                        column_name=item["column_name"],
                        can_read=item["can_read"],
                        can_filter=item["can_filter"],
                        can_aggregate=item["can_aggregate"],
                        is_sensitive=item["is_sensitive"],
                        masking_type=item["masking_type"],
                    )
                    for item in table_data["columns"]
                ]
                table_permission.row_filters = [
                    DatabaseRowFilter(
                        tenant_id=tenant_id,
                        filter_name=item["filter_name"],
                        column_name=item["column_name"],
                        operator=item["operator"],
                        value_source=item["value_source"],
                        value=item["value"],
                        enabled=item["enabled"],
                    )
                    for item in table_data["row_filters"]
                ]
                session.add(table_permission)
                records.append(table_permission)

            await session.commit()
            for record in records:
                await session.refresh(record)

            return await self.get_role_policy(
                tenant_id=tenant_id,
                connection_id=connection_id,
                role_id=role_id,
            )

    async def get_role_policy(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
        role_id: UUID,
    ) -> list[DatabaseTablePermission]:
        async with self.db_client() as session:
            query = (
                select(DatabaseTablePermission)
                .options(
                    selectinload(
                        DatabaseTablePermission.column_permissions
                    ),
                    selectinload(DatabaseTablePermission.row_filters),
                )
                .where(
                    DatabaseTablePermission.tenant_id == tenant_id,
                    DatabaseTablePermission.connection_id == connection_id,
                    DatabaseTablePermission.role_id == role_id,
                )
                .order_by(
                    DatabaseTablePermission.schema_name,
                    DatabaseTablePermission.table_name,
                )
            )
            result = await session.execute(query)
            return list(result.scalars().unique().all())

    async def get_effective_policies(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
        role_ids: list[UUID],
    ) -> list[DatabaseTablePermission]:
        if not role_ids:
            return []
        async with self.db_client() as session:
            query = (
                select(DatabaseTablePermission)
                .options(
                    selectinload(
                        DatabaseTablePermission.column_permissions
                    ),
                    selectinload(DatabaseTablePermission.row_filters),
                )
                .where(
                    DatabaseTablePermission.tenant_id == tenant_id,
                    DatabaseTablePermission.connection_id == connection_id,
                    DatabaseTablePermission.role_id.in_(role_ids),
                    DatabaseTablePermission.can_read.is_(True),
                )
                .order_by(
                    DatabaseTablePermission.schema_name,
                    DatabaseTablePermission.table_name,
                    DatabaseTablePermission.role_id,
                )
            )
            result = await session.execute(query)
            return list(result.scalars().unique().all())

    async def list_connection_policies(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
    ) -> list[tuple[DatabaseTablePermission, str]]:
        async with self.db_client() as session:
            query = (
                select(DatabaseTablePermission, Role.role_name)
                .join(Role, Role.role_id == DatabaseTablePermission.role_id)
                .options(
                    selectinload(
                        DatabaseTablePermission.column_permissions
                    ),
                    selectinload(DatabaseTablePermission.row_filters),
                )
                .where(
                    DatabaseTablePermission.tenant_id == tenant_id,
                    DatabaseTablePermission.connection_id == connection_id,
                    Role.tenant_id == tenant_id,
                )
                .order_by(
                    Role.role_name,
                    DatabaseTablePermission.schema_name,
                    DatabaseTablePermission.table_name,
                )
            )
            result = await session.execute(query)
            return list(result.unique().all())

    async def delete_role_policy(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
        role_id: UUID,
    ) -> int:
        async with self.db_client() as session:
            result = await session.execute(
                delete(DatabaseTablePermission).where(
                    DatabaseTablePermission.tenant_id == tenant_id,
                    DatabaseTablePermission.connection_id == connection_id,
                    DatabaseTablePermission.role_id == role_id,
                )
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def delete_connection_policies(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
    ) -> int:
        async with self.db_client() as session:
            result = await session.execute(
                delete(DatabaseTablePermission).where(
                    DatabaseTablePermission.tenant_id == tenant_id,
                    DatabaseTablePermission.connection_id == connection_id,
                )
            )
            await session.commit()
            return int(result.rowcount or 0)
