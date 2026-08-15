import hashlib
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from models.DatabaseConnectionModel import DatabaseConnectionModel
from models.DatabasePermissionModel import DatabasePermissionModel
from models.DatabaseSchemaCacheModel import DatabaseSchemaCacheModel
from schemas.database_permission import (
    DatabaseColumnPermissionResponse,
    DatabasePermissionCatalogResponse,
    DatabaseRolePermissionUpsert,
    DatabaseRowFilterResponse,
    DatabaseTablePermissionResponse,
    PermissionFilteredDatabaseSchemaResponse,
    SecureDatabaseQueryRequest,
    SecureDatabaseQueryResponse,
)
from stores.databases import PostgreSQLAdapter
from stores.databases.BaseDatabaseAdapter import DatabaseAdapterError


class DatabasePermissionDenied(PermissionError):
    pass


class DatabasePermissionController:
    _MASK_RANK = {
        "none": 0,
        "unmasked": 0,
        "last4": 3,
        "email": 4,
        "phone": 4,
        "partial": 5,
        "hash": 6,
        "full": 7,
    }

    def __init__(
        self,
        *,
        connection_model,
        schema_cache_model,
        permission_model,
        encryption_service,
        adapter_factory=PostgreSQLAdapter,
    ) -> None:
        self.connection_model = connection_model
        self.schema_cache_model = schema_cache_model
        self.permission_model = permission_model
        self.encryption_service = encryption_service
        self.adapter_factory = adapter_factory

    @classmethod
    async def create_instance(cls, db_client, encryption_service):
        return cls(
            connection_model=await DatabaseConnectionModel.create_instance(
                db_client=db_client
            ),
            schema_cache_model=await DatabaseSchemaCacheModel.create_instance(
                db_client=db_client
            ),
            permission_model=await DatabasePermissionModel.create_instance(
                db_client=db_client
            ),
            encryption_service=encryption_service,
        )

    async def _connection_and_cache(
        self,
        tenant_id: UUID,
        connection_id: int,
    ):
        connection = await self.connection_model.get_connection_by_id(
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        if connection is None:
            raise LookupError("database connection not found")
        cache = await self.schema_cache_model.get_cache(
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        if cache is None:
            raise LookupError(
                "schema metadata cache not found; sync the schema first"
            )
        return connection, cache

    @staticmethod
    def _schema_index(metadata_payload: dict) -> dict[tuple[str, str], dict]:
        result: dict[tuple[str, str], dict] = {}
        for schema in metadata_payload.get("schemas", []):
            schema_name = str(schema.get("schema_name") or "")
            for table in schema.get("tables", []):
                result[(schema_name, str(table.get("table_name") or ""))] = table
        return result

    @staticmethod
    def _column_index(table: dict) -> dict[str, dict]:
        return {
            str(column.get("column_name")): column
            for column in table.get("columns", [])
        }

    async def replace_role_policy(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
        role_id: UUID,
        payload: DatabaseRolePermissionUpsert,
    ) -> DatabasePermissionCatalogResponse:
        _, cache = await self._connection_and_cache(tenant_id, connection_id)
        if not await self.permission_model.role_exists(tenant_id, role_id):
            raise LookupError("role not found in this tenant")

        schema_index = self._schema_index(cache.metadata_payload)
        tables: list[dict] = []
        for table_policy in payload.tables:
            table_key = (table_policy.schema_name, table_policy.table_name)
            table = schema_index.get(table_key)
            if table is None:
                raise ValueError(
                    "table is not present in the synchronized schema: "
                    f"{table_policy.schema_name}.{table_policy.table_name}"
                )
            columns = self._column_index(table)
            for column_policy in table_policy.columns:
                if column_policy.column_name not in columns:
                    raise ValueError(
                        "column is not present in the synchronized schema: "
                        f"{table_policy.schema_name}.{table_policy.table_name}."
                        f"{column_policy.column_name}"
                    )
            for row_filter in table_policy.row_filters:
                if row_filter.column_name not in columns:
                    raise ValueError(
                        "row-filter column is not present in the synchronized "
                        "schema: "
                        f"{table_policy.schema_name}.{table_policy.table_name}."
                        f"{row_filter.column_name}"
                    )
            tables.append(table_policy.model_dump(mode="python"))

        records = await self.permission_model.replace_role_policy(
            tenant_id=tenant_id,
            connection_id=connection_id,
            role_id=role_id,
            tables=tables,
        )
        policies = [
            self._policy_response(record, role_name=None)
            for record in records
        ]
        return DatabasePermissionCatalogResponse(
            connection_id=connection_id,
            policies=policies,
            total=len(policies),
        )

    async def list_connection_policies(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
    ) -> DatabasePermissionCatalogResponse:
        connection = await self.connection_model.get_connection_by_id(
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        if connection is None:
            raise LookupError("database connection not found")
        rows = await self.permission_model.list_connection_policies(
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        policies = [
            self._policy_response(record, role_name=role_name)
            for record, role_name in rows
        ]
        return DatabasePermissionCatalogResponse(
            connection_id=connection_id,
            policies=policies,
            total=len(policies),
        )

    async def delete_role_policy(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
        role_id: UUID,
    ) -> int:
        connection = await self.connection_model.get_connection_by_id(
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        if connection is None:
            raise LookupError("database connection not found")
        if not await self.permission_model.role_exists(tenant_id, role_id):
            raise LookupError("role not found in this tenant")
        return await self.permission_model.delete_role_policy(
            tenant_id=tenant_id,
            connection_id=connection_id,
            role_id=role_id,
        )

    @staticmethod
    def _policy_response(record, role_name: str | None):
        return DatabaseTablePermissionResponse(
            table_permission_id=record.table_permission_id,
            tenant_id=record.tenant_id,
            connection_id=record.connection_id,
            role_id=record.role_id,
            role_name=role_name,
            schema_name=record.schema_name,
            table_name=record.table_name,
            can_read=record.can_read,
            columns=[
                DatabaseColumnPermissionResponse.model_validate(item)
                for item in record.column_permissions
            ],
            row_filters=[
                DatabaseRowFilterResponse.model_validate(item)
                for item in record.row_filters
            ],
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @classmethod
    def _more_restrictive_mask(cls, current: str, candidate: str) -> str:
        if current == "none" and candidate == "unmasked":
            return "unmasked"
        if cls._MASK_RANK.get(candidate, 7) > cls._MASK_RANK.get(current, 7):
            return candidate
        return current

    @classmethod
    def _effective_access(
        cls,
        metadata_payload: dict,
        policies: list,
        tenant_admin_bypass: bool,
    ) -> dict[tuple[str, str], dict]:
        schema_index = cls._schema_index(metadata_payload)
        if tenant_admin_bypass:
            return {
                key: {
                    "columns": {
                        name: {
                            "can_read": True,
                            "can_filter": True,
                            "can_aggregate": True,
                            "is_sensitive": False,
                            "masking_type": "none",
                        }
                        for name in cls._column_index(table)
                    },
                    "row_groups": [],
                }
                for key, table in schema_index.items()
            }

        effective: dict[tuple[str, str], dict] = {}
        for table_policy in policies:
            if not bool(table_policy.can_read):
                continue
            table_key = (table_policy.schema_name, table_policy.table_name)
            if table_key not in schema_index:
                continue
            table_access = effective.setdefault(
                table_key,
                {"columns": {}, "row_groups": []},
            )
            for column_policy in table_policy.column_permissions:
                column_access = table_access["columns"].setdefault(
                    column_policy.column_name,
                    {
                        "can_read": False,
                        "can_filter": False,
                        "can_aggregate": False,
                        "is_sensitive": False,
                        "masking_type": "none",
                    },
                )
                column_access["can_read"] = (
                    column_access["can_read"] or bool(column_policy.can_read)
                )
                column_access["can_filter"] = (
                    column_access["can_filter"] or bool(column_policy.can_filter)
                )
                column_access["can_aggregate"] = (
                    column_access["can_aggregate"]
                    or bool(column_policy.can_aggregate)
                )
                column_access["is_sensitive"] = (
                    column_access["is_sensitive"]
                    or bool(column_policy.is_sensitive)
                )
                if column_policy.can_read and column_policy.is_sensitive:
                    current_mask = column_access["masking_type"]
                    column_access["masking_type"] = cls._more_restrictive_mask(
                        current_mask,
                        str(column_policy.masking_type),
                    )

            enabled_filters = [
                item
                for item in table_policy.row_filters
                if bool(item.enabled)
            ]
            table_access["row_groups"].append(enabled_filters)
        return effective

    @staticmethod
    def _readable_columns(table_access: dict) -> set[str]:
        return {
            name
            for name, access in table_access["columns"].items()
            if access["can_read"]
        }

    @classmethod
    def _filtered_schema_payload(
        cls,
        metadata_payload: dict,
        effective: dict[tuple[str, str], dict],
    ) -> tuple[list[dict], list[dict]]:
        filtered_schemas: list[dict] = []
        readable_by_table = {
            key: cls._readable_columns(access)
            for key, access in effective.items()
        }

        for schema in metadata_payload.get("schemas", []):
            schema_name = str(schema.get("schema_name") or "")
            filtered_tables: list[dict] = []
            for table in schema.get("tables", []):
                table_name = str(table.get("table_name") or "")
                table_key = (schema_name, table_name)
                table_access = effective.get(table_key)
                if table_access is None:
                    continue

                allowed_columns: list[dict] = []
                for column in table.get("columns", []):
                    column_name = str(column.get("column_name") or "")
                    access = table_access["columns"].get(column_name)
                    if access is None:
                        continue
                    if not (
                        access["can_read"]
                        or access["can_filter"]
                        or access["can_aggregate"]
                    ):
                        continue
                    allowed_columns.append({**column, **access})

                readable = readable_by_table[table_key]
                primary_keys = [
                    key
                    for key in table.get("primary_keys", [])
                    if set(key.get("columns") or []).issubset(readable)
                ]
                foreign_keys = []
                for key in table.get("foreign_keys", []):
                    target = (
                        str(key.get("referenced_schema_name") or ""),
                        str(key.get("referenced_table_name") or ""),
                    )
                    if target not in effective:
                        continue
                    if not set(key.get("columns") or []).issubset(readable):
                        continue
                    if not set(key.get("referenced_columns") or []).issubset(
                        readable_by_table.get(target, set())
                    ):
                        continue
                    foreign_keys.append(key)

                groups = table_access["row_groups"]
                row_filter_count = (
                    0
                    if not groups or any(not group for group in groups)
                    else sum(len(group) for group in groups)
                )
                filtered_tables.append(
                    {
                        "schema_name": schema_name,
                        "table_name": table_name,
                        "table_type": table.get("table_type", "BASE TABLE"),
                        "can_read": True,
                        "row_filters_enforced": row_filter_count,
                        "columns": allowed_columns,
                        "primary_keys": primary_keys,
                        "foreign_keys": foreign_keys,
                    }
                )
            if filtered_tables:
                filtered_schemas.append(
                    {"schema_name": schema_name, "tables": filtered_tables}
                )

        filtered_relationships: list[dict] = []
        for relationship in metadata_payload.get("relationships", []):
            source = (
                str(relationship.get("source_schema_name") or ""),
                str(relationship.get("source_table_name") or ""),
            )
            target = (
                str(relationship.get("target_schema_name") or ""),
                str(relationship.get("target_table_name") or ""),
            )
            if source not in effective or target not in effective:
                continue
            if not set(relationship.get("source_columns") or []).issubset(
                readable_by_table[source]
            ):
                continue
            if not set(relationship.get("target_columns") or []).issubset(
                readable_by_table[target]
            ):
                continue
            filtered_relationships.append(relationship)

        return filtered_schemas, filtered_relationships

    async def get_filtered_schema(
        self,
        *,
        tenant_id: UUID,
        connection_id: int,
        user_id: UUID | None,
        role_ids: list[UUID],
        tenant_admin_bypass: bool,
    ) -> PermissionFilteredDatabaseSchemaResponse:
        connection, cache = await self._connection_and_cache(
            tenant_id,
            connection_id,
        )
        policies = []
        if not tenant_admin_bypass:
            policies = await self.permission_model.get_effective_policies(
                tenant_id=tenant_id,
                connection_id=connection_id,
                role_ids=role_ids,
            )
        effective = self._effective_access(
            cache.metadata_payload,
            policies,
            tenant_admin_bypass,
        )
        schemas, relationships = self._filtered_schema_payload(
            cache.metadata_payload,
            effective,
        )
        tables = [table for schema in schemas for table in schema["tables"]]
        return PermissionFilteredDatabaseSchemaResponse(
            connection_id=connection_id,
            database_name=connection.database_name,
            user_id=user_id,
            role_ids=role_ids,
            tenant_admin_bypass=tenant_admin_bypass,
            schema_hash=cache.schema_hash,
            synced_at=cache.synced_at,
            schema_count=len(schemas),
            table_count=len(tables),
            column_count=sum(len(table["columns"]) for table in tables),
            primary_key_count=sum(len(table["primary_keys"]) for table in tables),
            foreign_key_count=sum(len(table["foreign_keys"]) for table in tables),
            relationship_count=len(relationships),
            schemas=schemas,
            relationships=relationships,
        )

    @staticmethod
    def _quote_identifier(value: str) -> str:
        return '"' + str(value).replace('"', '""') + '"'

    @classmethod
    def _predicate_sql(
        cls,
        *,
        column_name: str,
        operator: str,
        value: Any,
        parameters: list[Any],
    ) -> str:
        identifier = cls._quote_identifier(column_name)
        if operator == "is_null":
            return f"{identifier} IS NULL"
        if operator == "not_null":
            return f"{identifier} IS NOT NULL"
        if operator in {"in", "not_in"}:
            if not isinstance(value, list) or not value:
                raise ValueError(f"{operator} requires a non-empty list")
            placeholders = []
            for item in value:
                parameters.append(item)
                placeholders.append(f"${len(parameters)}")
            keyword = "IN" if operator == "in" else "NOT IN"
            return f"{identifier} {keyword} ({', '.join(placeholders)})"

        parameters.append(value)
        placeholder = f"${len(parameters)}"
        comparisons = {
            "eq": "=",
            "ne": "<>",
            "gt": ">",
            "gte": ">=",
            "lt": "<",
            "lte": "<=",
        }
        if operator in comparisons:
            return f"{identifier} {comparisons[operator]} {placeholder}"
        if operator == "contains":
            parameters[-1] = f"%{value}%"
        elif operator == "starts_with":
            parameters[-1] = f"{value}%"
        elif operator == "ends_with":
            parameters[-1] = f"%{value}"
        else:
            raise ValueError(f"unsupported filter operator: {operator}")
        return f"CAST({identifier} AS TEXT) ILIKE {placeholder}"

    @classmethod
    def _coerce_filter_value(cls, column: dict, value: Any) -> Any:
        if isinstance(value, list):
            return [cls._coerce_filter_value(column, item) for item in value]
        if value is None:
            return None
        data_type = str(column.get("data_type") or "").lower()
        udt_name = str(column.get("udt_name") or "").lower()
        try:
            if data_type == "uuid" or udt_name == "uuid":
                return value if isinstance(value, UUID) else UUID(str(value))
            if data_type in {"smallint", "integer", "bigint"}:
                return int(value)
            if data_type in {
                "numeric",
                "decimal",
                "real",
                "double precision",
            }:
                return Decimal(str(value))
            if data_type == "boolean":
                if isinstance(value, bool):
                    return value
                normalized = str(value).strip().lower()
                if normalized in {"true", "1", "yes"}:
                    return True
                if normalized in {"false", "0", "no"}:
                    return False
                raise ValueError("invalid boolean")
            if data_type == "date":
                return value if isinstance(value, date) else date.fromisoformat(str(value))
            if data_type.startswith("timestamp"):
                if isinstance(value, datetime):
                    return value
                return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"invalid value for {column.get('column_name')} ({data_type})"
            ) from exc
        return value

    @staticmethod
    def _row_filter_value(row_filter, user_context: dict[str, Any]) -> Any:
        if row_filter.value_source == "literal":
            return row_filter.value
        mapping = {
            "current_user_id": "user_id",
            "current_tenant_id": "tenant_id",
            "current_user_email": "user_email",
        }
        key = mapping.get(str(row_filter.value_source))
        if key is None:
            raise ValueError("unsupported row-filter value source")
        value = user_context.get(key)
        if value is None:
            raise ValueError(
                f"row filter requires unavailable user context: {key}"
            )
        return value

    @classmethod
    def _row_policy_sql(
        cls,
        groups: list[list],
        user_context: dict[str, Any],
        raw_columns: dict[str, dict],
        parameters: list[Any],
    ) -> tuple[str | None, int]:
        if not groups or any(not group for group in groups):
            return None, 0
        group_sql: list[str] = []
        applied = 0
        for group in groups:
            predicates = []
            for row_filter in group:
                column = raw_columns.get(row_filter.column_name)
                if column is None:
                    raise ValueError(
                        f"row-filter column is no longer available: "
                        f"{row_filter.column_name}"
                    )
                predicates.append(
                    cls._predicate_sql(
                        column_name=row_filter.column_name,
                        operator=row_filter.operator,
                        value=cls._coerce_filter_value(
                            column,
                            cls._row_filter_value(row_filter, user_context),
                        ),
                        parameters=parameters,
                    )
                )
                applied += 1
            group_sql.append("(" + " AND ".join(predicates) + ")")
        return "(" + " OR ".join(group_sql) + ")", applied

    @staticmethod
    def _mask_value(value: Any, masking_type: str) -> Any:
        if value is None or masking_type in {"none", "unmasked"}:
            return value
        text = str(value)
        if masking_type == "full":
            return "••••••"
        if masking_type == "hash":
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            return f"sha256:{digest}"
        if masking_type == "email" and "@" in text:
            local, domain = text.split("@", 1)
            return f"{local[:1] or '*'}***@{domain}"
        if masking_type == "phone":
            return ("*" * max(len(text) - 4, 4)) + text[-4:]
        if masking_type == "last4":
            return ("*" * max(len(text) - 4, 0)) + text[-4:]
        if masking_type == "partial":
            if len(text) <= 4:
                return "*" * len(text)
            return text[:2] + ("*" * (len(text) - 4)) + text[-2:]
        return "••••••"

    async def execute_secure_query(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        user_email: str,
        role_ids: list[UUID],
        tenant_admin_bypass: bool,
        connection_id: int,
        payload: SecureDatabaseQueryRequest,
    ) -> SecureDatabaseQueryResponse:
        connection, cache = await self._connection_and_cache(
            tenant_id,
            connection_id,
        )
        if connection.connection_status == "disabled":
            raise ValueError("disabled database connection cannot be queried")

        schema_index = self._schema_index(cache.metadata_payload)
        table_key = (payload.schema_name, payload.table_name)
        raw_table = schema_index.get(table_key)
        if raw_table is None:
            raise ValueError("requested table is not in the synchronized schema")

        policies = []
        if not tenant_admin_bypass:
            policies = await self.permission_model.get_effective_policies(
                tenant_id=tenant_id,
                connection_id=connection_id,
                role_ids=role_ids,
            )
        effective = self._effective_access(
            cache.metadata_payload,
            policies,
            tenant_admin_bypass,
        )
        table_access = effective.get(table_key)
        if table_access is None:
            raise DatabasePermissionDenied(
                "the current roles cannot read this table"
            )

        raw_columns = self._column_index(raw_table)
        access_columns = table_access["columns"]
        select_parts: list[str] = []
        group_parts: list[str] = []
        output_fields: list[str] = []
        used_fields: set[str] = set()

        for column_name in payload.columns:
            if column_name not in raw_columns:
                raise ValueError(f"unknown column: {column_name}")
            access = access_columns.get(column_name)
            if access is None or not access["can_read"]:
                raise DatabasePermissionDenied(
                    f"can_read is required for column: {column_name}"
                )
            quoted = self._quote_identifier(column_name)
            select_parts.append(quoted)
            group_parts.append(quoted)
            output_fields.append(column_name)
            used_fields.add(column_name)

        aggregate_aliases: set[str] = set()
        for index, aggregate in enumerate(payload.aggregates, start=1):
            column_name = aggregate.column_name
            if column_name is not None:
                if column_name not in raw_columns:
                    raise ValueError(f"unknown aggregate column: {column_name}")
                access = access_columns.get(column_name)
                if access is None or not access["can_aggregate"]:
                    raise DatabasePermissionDenied(
                        "can_aggregate is required for column: "
                        f"{column_name}"
                    )
                argument = self._quote_identifier(column_name)
            else:
                argument = "*"

            alias = aggregate.alias or (
                f"{aggregate.function}_{column_name or 'all'}"
            )
            if alias in used_fields or alias in aggregate_aliases:
                alias = f"{alias}_{index}"
            aggregate_aliases.add(alias)
            used_fields.add(alias)
            select_parts.append(
                f"{aggregate.function.upper()}({argument}) "
                f"AS {self._quote_identifier(alias)}"
            )
            output_fields.append(alias)

        parameters: list[Any] = []
        predicates: list[str] = []
        for query_filter in payload.filters:
            if query_filter.column_name not in raw_columns:
                raise ValueError(
                    f"unknown filter column: {query_filter.column_name}"
                )
            access = access_columns.get(query_filter.column_name)
            if access is None or not access["can_filter"]:
                raise DatabasePermissionDenied(
                    "can_filter is required for column: "
                    f"{query_filter.column_name}"
                )
            predicates.append(
                self._predicate_sql(
                    column_name=query_filter.column_name,
                    operator=query_filter.operator,
                    value=self._coerce_filter_value(
                        raw_columns[query_filter.column_name],
                        query_filter.value,
                    ),
                    parameters=parameters,
                )
            )

        row_policy, row_filters_applied = self._row_policy_sql(
            table_access["row_groups"],
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "user_email": str(user_email),
            },
            raw_columns,
            parameters,
        )
        if row_policy:
            predicates.append(row_policy)

        sql = (
            f"SELECT {', '.join(select_parts)} FROM "
            f"{self._quote_identifier(payload.schema_name)}."
            f"{self._quote_identifier(payload.table_name)}"
        )
        if predicates:
            sql += " WHERE " + " AND ".join(
                f"({predicate})" for predicate in predicates
            )
        if payload.aggregates and group_parts:
            sql += " GROUP BY " + ", ".join(group_parts)

        if payload.order_by:
            order_parts = []
            for order in payload.order_by:
                if order.field not in used_fields:
                    raise DatabasePermissionDenied(
                        "order_by requires a selected column or aggregate alias: "
                        f"{order.field}"
                    )
                order_parts.append(
                    f"{self._quote_identifier(order.field)} "
                    f"{order.direction.upper()}"
                )
            sql += " ORDER BY " + ", ".join(order_parts)
        sql += f" LIMIT {int(payload.limit)} OFFSET {int(payload.offset)}"

        try:
            password = self.encryption_service.decrypt(
                connection.encrypted_password
            )
        except ValueError as exc:
            raise DatabaseAdapterError(
                "credential_decryption_failed",
                "Stored database credentials could not be decrypted",
            ) from exc

        adapter = self.adapter_factory(
            host=connection.host,
            port=connection.port,
            database_name=connection.database_name,
            username=connection.username,
            password=password,
            ssl_mode=connection.ssl_mode,
        )
        rows = await adapter.execute_read_query(sql, parameters)

        masked_columns = []
        masking_by_column = {}
        for column_name in payload.columns:
            access = access_columns[column_name]
            masking_type = access["masking_type"]
            if access["is_sensitive"] and masking_type not in {"none", "unmasked"}:
                masked_columns.append(column_name)
                masking_by_column[column_name] = masking_type

        safe_rows = []
        for raw_row in rows:
            item = dict(raw_row)
            for column_name, masking_type in masking_by_column.items():
                if column_name in item:
                    item[column_name] = self._mask_value(
                        item[column_name],
                        masking_type,
                    )
            safe_rows.append(item)

        return SecureDatabaseQueryResponse(
            connection_id=connection_id,
            schema_name=payload.schema_name,
            table_name=payload.table_name,
            columns=output_fields,
            rows=safe_rows,
            row_count=len(safe_rows),
            limit=payload.limit,
            offset=payload.offset,
            masked_columns=masked_columns,
            row_filters_applied=row_filters_applied,
        )
