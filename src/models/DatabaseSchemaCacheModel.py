from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from .BaseDataModel import BaseDataModel
from .db_schemes import DatabaseSchemaCache


class DatabaseSchemaCacheModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "DatabaseSchemaCacheModel":
        return cls(db_client=db_client)

    async def get_cache(
        self,
        tenant_id: UUID,
        connection_id: int,
    ) -> DatabaseSchemaCache | None:
        async with self.db_client() as session:
            query = select(DatabaseSchemaCache).where(
                DatabaseSchemaCache.tenant_id == tenant_id,
                DatabaseSchemaCache.connection_id == connection_id,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def upsert_cache(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
        schema_hash: str,
        metadata_payload: dict,
        schema_count: int,
        table_count: int,
        column_count: int,
        primary_key_count: int,
        foreign_key_count: int,
        relationship_count: int,
        synced_at: datetime,
    ) -> tuple[DatabaseSchemaCache, bool, datetime | None]:
        async with self.db_client() as session:
            query = (
                select(DatabaseSchemaCache)
                .where(
                    DatabaseSchemaCache.tenant_id == tenant_id,
                    DatabaseSchemaCache.connection_id == connection_id,
                )
                .with_for_update()
            )
            result = await session.execute(query)
            cache = result.scalar_one_or_none()

            previous_synced_at = None
            if cache is None:
                changed = True
                cache = DatabaseSchemaCache(
                    tenant_id=tenant_id,
                    connection_id=connection_id,
                )
                session.add(cache)
            else:
                previous_synced_at = cache.synced_at
                changed = cache.schema_hash != schema_hash

            cache.schema_hash = schema_hash
            cache.metadata_payload = metadata_payload
            cache.schema_count = schema_count
            cache.table_count = table_count
            cache.column_count = column_count
            cache.primary_key_count = primary_key_count
            cache.foreign_key_count = foreign_key_count
            cache.relationship_count = relationship_count
            cache.synced_at = synced_at

            await session.commit()
            await session.refresh(cache)
            return cache, changed, previous_synced_at

    async def delete_cache(
        self,
        tenant_id: UUID,
        connection_id: int,
    ) -> bool:
        async with self.db_client() as session:
            query = select(DatabaseSchemaCache).where(
                DatabaseSchemaCache.tenant_id == tenant_id,
                DatabaseSchemaCache.connection_id == connection_id,
            )
            result = await session.execute(query)
            cache = result.scalar_one_or_none()
            if cache is None:
                return False

            await session.delete(cache)
            await session.commit()
            return True
