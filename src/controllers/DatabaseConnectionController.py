import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from core.credentials_encryption import CredentialsEncryptionService
from models.DatabaseConnectionModel import DatabaseConnectionModel
from models.DatabasePermissionModel import DatabasePermissionModel
from models.DatabaseSchemaCacheModel import DatabaseSchemaCacheModel
from models.db_schemes import DatabaseConnection
from schemas.database_connection import (
    DatabaseConnectionCreate,
    DatabaseConnectionResponse,
    DatabaseSchemaCacheResponse,
    DatabaseSchemaDiscoveryResponse,
    DatabaseSchemaSyncResponse,
    DatabaseConnectionTestResponse,
    DatabaseConnectionUpdate,
)
from stores.databases import PostgreSQLAdapter
from stores.databases.BaseDatabaseAdapter import DatabaseAdapterError


class DatabaseConnectionController:
    def __init__(
        self,
        database_connection_model,
        encryption_service,
        schema_cache_model=None,
        permission_model=None,
    ) -> None:
        self.database_connection_model = database_connection_model
        self.encryption_service = encryption_service
        self.schema_cache_model = schema_cache_model
        self.permission_model = permission_model

    @classmethod
    async def create_instance(cls, db_client, encryption_service):
        model = await DatabaseConnectionModel.create_instance(db_client=db_client)
        schema_cache_model = await DatabaseSchemaCacheModel.create_instance(
            db_client=db_client
        )
        permission_model = await DatabasePermissionModel.create_instance(
            db_client=db_client
        )
        return cls(
            model,
            encryption_service,
            schema_cache_model,
            permission_model,
        )

    @staticmethod
    def to_response(connection: DatabaseConnection) -> DatabaseConnectionResponse:
        return DatabaseConnectionResponse(
            connection_id=connection.connection_id,
            connection_uuid=connection.connection_uuid,
            tenant_id=connection.tenant_id,
            created_by_user_id=connection.created_by_user_id,
            connection_name=connection.connection_name,
            database_type=connection.database_type,
            host=connection.host,
            port=connection.port,
            database_name=connection.database_name,
            username=connection.username,
            ssl_mode=connection.ssl_mode,
            connection_status=connection.connection_status,
            has_password=bool(connection.encrypted_password),
            last_tested_at=connection.last_tested_at,
            last_success_at=connection.last_success_at,
            last_error_code=connection.last_error_code,
            last_error_message=connection.last_error_message,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )

    async def create_connection(self, tenant_id: UUID, created_by_user_id: UUID, payload):
        record = DatabaseConnection(
            tenant_id=tenant_id,
            created_by_user_id=created_by_user_id,
            connection_name=payload.connection_name,
            database_type=payload.database_type,
            host=payload.host,
            port=payload.port,
            database_name=payload.database_name,
            username=payload.username,
            encrypted_password=self.encryption_service.encrypt(payload.password),
            ssl_mode=payload.ssl_mode,
            connection_status="untested",
        )
        created = await self.database_connection_model.create_connection(connection=record)
        return self.to_response(created)

    async def update_connection(self, tenant_id: UUID, connection_id: int, payload):
        data = payload.model_dump(exclude_unset=True)
        password = data.pop("password", None)
        encrypted_password = self.encryption_service.encrypt(password) if password is not None else None
        data["connection_status"] = "untested"
        updated = await self.database_connection_model.update_connection(
            tenant_id=tenant_id,
            connection_id=connection_id,
            encrypted_password=encrypted_password,
            **data,
        )
        if updated is not None and self.schema_cache_model is not None:
            await self.schema_cache_model.delete_cache(
                tenant_id=tenant_id,
                connection_id=connection_id,
            )
        if updated is not None and self.permission_model is not None:
            await self.permission_model.delete_connection_policies(
                tenant_id=tenant_id,
                connection_id=connection_id,
            )
        return self.to_response(updated) if updated is not None else None

    async def test_connection(
        self,
        tenant_id: UUID,
        connection_id: int,
        *,
        connect_timeout_seconds: float = 10.0,
    ) -> DatabaseConnectionTestResponse | None:
        record = await self.database_connection_model.get_connection_by_id(
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        if record is None:
            return None
        if record.connection_status == "disabled":
            raise ValueError("disabled database connection cannot be tested")

        tested_at = datetime.now(timezone.utc)
        try:
            password = self.encryption_service.decrypt(record.encrypted_password)
        except ValueError:
            result_status = "failed"
            error_code = "credential_decryption_failed"
            message = "Stored database credentials could not be decrypted"
            await self.database_connection_model.update_test_status(
                tenant_id=tenant_id,
                connection_id=connection_id,
                connection_status=result_status,
                last_tested_at=tested_at,
                last_success_at=record.last_success_at,
                last_error_code=error_code,
                last_error_message=message,
            )
            return DatabaseConnectionTestResponse(
                connection_id=connection_id,
                success=False,
                connection_status=result_status,
                message=message,
                error_code=error_code,
                tested_at=tested_at,
            )

        adapter = PostgreSQLAdapter(
            host=record.host,
            port=record.port,
            database_name=record.database_name,
            username=record.username,
            password=password,
            ssl_mode=record.ssl_mode,
            connect_timeout_seconds=connect_timeout_seconds,
        )
        result = await adapter.test_connection()
        status = "connected" if result.success else "failed"
        await self.database_connection_model.update_test_status(
            tenant_id=tenant_id,
            connection_id=connection_id,
            connection_status=status,
            last_tested_at=tested_at,
            last_success_at=(tested_at if result.success else record.last_success_at),
            last_error_code=(None if result.success else result.error_code),
            last_error_message=(None if result.success else result.message),
        )
        return DatabaseConnectionTestResponse(
            connection_id=connection_id,
            success=result.success,
            connection_status=status,
            message=result.message,
            error_code=result.error_code,
            read_only=result.read_only,
            ssl_in_use=result.ssl_in_use,
            server_version=result.server_version,
            tested_at=tested_at,
        )

    async def discover_schema(
        self,
        tenant_id: UUID,
        connection_id: int,
        *,
        connect_timeout_seconds: float = 10.0,
    ) -> DatabaseSchemaDiscoveryResponse | None:
        record = await self.database_connection_model.get_connection_by_id(
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        if record is None:
            return None
        if record.connection_status == "disabled":
            raise ValueError("disabled database connection cannot be discovered")

        try:
            password = self.encryption_service.decrypt(
                record.encrypted_password
            )
        except ValueError as exc:
            raise DatabaseAdapterError(
                "credential_decryption_failed",
                "Stored database credentials could not be decrypted",
            ) from exc

        adapter = PostgreSQLAdapter(
            host=record.host,
            port=record.port,
            database_name=record.database_name,
            username=record.username,
            password=password,
            ssl_mode=record.ssl_mode,
            connect_timeout_seconds=connect_timeout_seconds,
        )
        result = await adapter.discover_schema()
        return DatabaseSchemaDiscoveryResponse(
            connection_id=connection_id,
            database_name=record.database_name,
            discovered_at=datetime.now(timezone.utc),
            schema_count=result.schema_count,
            table_count=result.table_count,
            column_count=result.column_count,
            primary_key_count=result.primary_key_count,
            foreign_key_count=result.foreign_key_count,
            relationship_count=result.relationship_count,
            schemas=result.schemas,
            relationships=result.relationships,
        )

    @staticmethod
    def _cache_payload(
        discovery: DatabaseSchemaDiscoveryResponse,
    ) -> dict:
        return {
            "schemas": [
                schema.model_dump(mode="json")
                for schema in discovery.schemas
            ],
            "relationships": [
                relationship.model_dump(mode="json")
                for relationship in discovery.relationships
            ],
        }

    @staticmethod
    def _schema_hash(payload: dict) -> str:
        canonical_payload = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(
            canonical_payload.encode("utf-8")
        ).hexdigest()

    async def sync_schema(
        self,
        tenant_id: UUID,
        connection_id: int,
        *,
        connect_timeout_seconds: float = 10.0,
    ) -> DatabaseSchemaSyncResponse | None:
        discovery = await self.discover_schema(
            tenant_id,
            connection_id,
            connect_timeout_seconds=connect_timeout_seconds,
        )
        if discovery is None:
            return None
        if self.schema_cache_model is None:
            raise RuntimeError("schema cache model is not configured")

        payload = self._cache_payload(discovery)
        schema_hash = self._schema_hash(payload)
        synced_at = datetime.now(timezone.utc)
        permissions_invalidated = False
        existing_cache = await self.schema_cache_model.get_cache(
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        if (
            existing_cache is not None
            and existing_cache.schema_hash != schema_hash
            and self.permission_model is not None
        ):
            deleted = await self.permission_model.delete_connection_policies(
                tenant_id=tenant_id,
                connection_id=connection_id,
            )
            permissions_invalidated = deleted > 0
        cache, changed, previous_synced_at = (
            await self.schema_cache_model.upsert_cache(
                tenant_id=tenant_id,
                connection_id=connection_id,
                schema_hash=schema_hash,
                metadata_payload=payload,
                schema_count=discovery.schema_count,
                table_count=discovery.table_count,
                column_count=discovery.column_count,
                primary_key_count=discovery.primary_key_count,
                foreign_key_count=discovery.foreign_key_count,
                relationship_count=discovery.relationship_count,
                synced_at=synced_at,
            )
        )
        return DatabaseSchemaSyncResponse(
            connection_id=connection_id,
            database_name=discovery.database_name,
            synced_at=cache.synced_at,
            previous_synced_at=previous_synced_at,
            changed=changed,
            permissions_invalidated=permissions_invalidated,
            schema_hash=cache.schema_hash,
            schema_count=cache.schema_count,
            table_count=cache.table_count,
            column_count=cache.column_count,
            primary_key_count=cache.primary_key_count,
            foreign_key_count=cache.foreign_key_count,
            relationship_count=cache.relationship_count,
            schemas=cache.metadata_payload.get("schemas", []),
            relationships=cache.metadata_payload.get(
                "relationships", []
            ),
        )

    async def get_cached_schema(
        self,
        tenant_id: UUID,
        connection_id: int,
    ) -> DatabaseSchemaCacheResponse | None:
        connection = await self.database_connection_model.get_connection_by_id(
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        if connection is None:
            return None
        if self.schema_cache_model is None:
            raise RuntimeError("schema cache model is not configured")

        cache = await self.schema_cache_model.get_cache(
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        if cache is None:
            return None
        return DatabaseSchemaCacheResponse(
            connection_id=connection_id,
            database_name=connection.database_name,
            synced_at=cache.synced_at,
            schema_hash=cache.schema_hash,
            schema_count=cache.schema_count,
            table_count=cache.table_count,
            column_count=cache.column_count,
            primary_key_count=cache.primary_key_count,
            foreign_key_count=cache.foreign_key_count,
            relationship_count=cache.relationship_count,
            schemas=cache.metadata_payload.get("schemas", []),
            relationships=cache.metadata_payload.get(
                "relationships", []
            ),
        )
