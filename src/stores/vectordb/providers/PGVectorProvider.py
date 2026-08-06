import json
import logging
import re
from typing import Any

from sqlalchemy import bindparam
from sqlalchemy.sql import text as sql_text

from models.db_schemes import RetrievedDocument

from ..VectorDBEnums import (
    DistanceMethodEnums,
    PgVectorDistanceMethodEnums,
    PgVectorDistanceOperatorEnums,
    PgVectorIndexTypeEnums,
    PgVectorTableSchemeEnums,
)
from ..VectorDBInterface import VectorDBInterface


class PGVectorProvider(VectorDBInterface):
    COLLECTION_PATTERN = re.compile(
        r"^collection_[a-z0-9_]+$"
    )

    def __init__(
        self,
        db_client,
        default_vector_size: int = 768,
        distance_method: str | None = None,
        index_threshold: int = 100,
    ):
        if db_client is None:
            raise ValueError("db_client is required")
        if default_vector_size <= 0:
            raise ValueError(
                "default_vector_size must be positive"
            )
        if index_threshold < 0:
            raise ValueError(
                "index_threshold cannot be negative"
            )

        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.index_threshold = index_threshold
        self.collection_prefix = (
            PgVectorTableSchemeEnums.PREFIX.value
        )
        self.logger = logging.getLogger(__name__)

        normalized_distance = str(
            distance_method or DistanceMethodEnums.COSINE.value
        ).lower()
        if normalized_distance == DistanceMethodEnums.DOT.value:
            self.distance_method = (
                PgVectorDistanceMethodEnums.DOT.value
            )
            self.distance_operator = (
                PgVectorDistanceOperatorEnums.DOT.value
            )
        else:
            self.distance_method = (
                PgVectorDistanceMethodEnums.COSINE.value
            )
            self.distance_operator = (
                PgVectorDistanceOperatorEnums.COSINE.value
            )

    def _validate_collection_name(
        self,
        collection_name: str,
    ) -> str:
        normalized_name = str(collection_name).strip().lower()
        if not self.COLLECTION_PATTERN.fullmatch(
            normalized_name
        ):
            raise ValueError("invalid collection name")
        return normalized_name

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        if not vector:
            raise ValueError("vector cannot be empty")
        return "[" + ",".join(str(float(v)) for v in vector) + "]"

    def _validate_vector_size(
        self,
        vector: list[float],
    ) -> None:
        if len(vector) != self.default_vector_size:
            raise ValueError(
                "vector dimension does not match configured "
                "embedding size"
            )

    async def connect(self) -> bool:
        async with self.db_client() as session:
            await session.execute(
                sql_text(
                    "CREATE EXTENSION IF NOT EXISTS vector"
                )
            )
            await session.commit()
        return True

    async def disconnect(self) -> bool:
        return True

    async def is_collection_existed(
        self,
        collection_name: str,
    ) -> bool:
        collection_name = self._validate_collection_name(
            collection_name
        )
        async with self.db_client() as session:
            result = await session.execute(
                sql_text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_tables "
                    "WHERE schemaname = current_schema() "
                    "AND tablename = :collection_name"
                    ")"
                ),
                {"collection_name": collection_name},
            )
            return bool(result.scalar_one())

    async def list_all_collections(self) -> list[str]:
        async with self.db_client() as session:
            result = await session.execute(
                sql_text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = current_schema() "
                    "AND tablename LIKE :prefix "
                    "ORDER BY tablename"
                ),
                {"prefix": f"{self.collection_prefix}%"},
            )
            return list(result.scalars().all())

    async def get_collection_info(
        self,
        collection_name: str,
    ) -> dict | None:
        collection_name = self._validate_collection_name(
            collection_name
        )
        if not await self.is_collection_existed(collection_name):
            return None

        async with self.db_client() as session:
            table_info = await session.execute(
                sql_text(
                    "SELECT schemaname, tablename, tableowner, "
                    "tablespace, hasindexes FROM pg_tables "
                    "WHERE schemaname = current_schema() "
                    "AND tablename = :collection_name"
                ),
                {"collection_name": collection_name},
            )
            record_count = await session.execute(
                sql_text(
                    f'SELECT COUNT(*) FROM "{collection_name}"'
                )
            )
            row = table_info.fetchone()
            if row is None:
                return None

            return {
                "table_info": {
                    "schemaname": row.schemaname,
                    "tablename": row.tablename,
                    "tableowner": row.tableowner,
                    "tablespace": row.tablespace,
                    "hasindexes": row.hasindexes,
                },
                "record_count": record_count.scalar_one(),
                "embedding_size": self.default_vector_size,
                "distance_method": self.distance_method,
            }

    async def delete_collection(
        self,
        collection_name: str,
    ) -> bool:
        collection_name = self._validate_collection_name(
            collection_name
        )
        async with self.db_client() as session:
            await session.execute(
                sql_text(
                    f'DROP TABLE IF EXISTS "{collection_name}"'
                )
            )
            await session.commit()
        return True

    async def create_collection(
        self,
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False,
    ) -> bool:
        collection_name = self._validate_collection_name(
            collection_name
        )
        if embedding_size <= 0:
            raise ValueError("embedding_size must be positive")
        if embedding_size != self.default_vector_size:
            raise ValueError(
                "embedding_size does not match configured "
                "EMBEDDING_MODEL_SIZE"
            )

        if do_reset:
            await self.delete_collection(collection_name)

        if await self.is_collection_existed(collection_name):
            return False

        async with self.db_client() as session:
            await session.execute(
                sql_text(
                    f'CREATE TABLE "{collection_name}" ('
                    'id bigserial PRIMARY KEY, '
                    'text text NOT NULL, '
                    f'vector vector({embedding_size}) NOT NULL, '
                    "metadata jsonb NOT NULL DEFAULT '{}'::jsonb, "
                    'chunk_id integer NOT NULL UNIQUE, '
                    'FOREIGN KEY (chunk_id) '
                    'REFERENCES chunks(chunk_id) ON DELETE CASCADE'
                    ')'
                )
            )
            await session.commit()
        return True

    def _index_name(self, collection_name: str) -> str:
        return f"{collection_name}_vector_idx"

    async def is_index_existed(
        self,
        collection_name: str,
    ) -> bool:
        collection_name = self._validate_collection_name(
            collection_name
        )
        index_name = self._index_name(collection_name)
        async with self.db_client() as session:
            result = await session.execute(
                sql_text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_indexes "
                    "WHERE schemaname = current_schema() "
                    "AND tablename = :collection_name "
                    "AND indexname = :index_name"
                    ")"
                ),
                {
                    "collection_name": collection_name,
                    "index_name": index_name,
                },
            )
            return bool(result.scalar_one())

    async def create_vector_index(
        self,
        collection_name: str,
        index_type: str = PgVectorIndexTypeEnums.HNSW.value,
    ) -> bool:
        collection_name = self._validate_collection_name(
            collection_name
        )
        normalized_index_type = str(index_type).lower()
        if normalized_index_type not in {
            PgVectorIndexTypeEnums.HNSW.value,
            PgVectorIndexTypeEnums.IVFFLAT.value,
        }:
            raise ValueError("invalid vector index type")

        if await self.is_index_existed(collection_name):
            return False

        async with self.db_client() as session:
            count_result = await session.execute(
                sql_text(
                    f'SELECT COUNT(*) FROM "{collection_name}"'
                )
            )
            if count_result.scalar_one() < self.index_threshold:
                return False

            index_name = self._index_name(collection_name)
            await session.execute(
                sql_text(
                    f'CREATE INDEX "{index_name}" '
                    f'ON "{collection_name}" '
                    f'USING {normalized_index_type} '
                    f'(vector {self.distance_method})'
                )
            )
            await session.commit()
        return True

    async def reset_vector_index(
        self,
        collection_name: str,
        index_type: str = PgVectorIndexTypeEnums.HNSW.value,
    ) -> bool:
        collection_name = self._validate_collection_name(
            collection_name
        )
        index_name = self._index_name(collection_name)
        async with self.db_client() as session:
            await session.execute(
                sql_text(
                    f'DROP INDEX IF EXISTS "{index_name}"'
                )
            )
            await session.commit()
        return await self.create_vector_index(
            collection_name=collection_name,
            index_type=index_type,
        )

    async def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list[float],
        metadata: dict | None = None,
        record_id: int | str | None = None,
    ) -> bool:
        collection_name = self._validate_collection_name(
            collection_name
        )
        if not await self.is_collection_existed(collection_name):
            return False
        if record_id is None:
            raise ValueError("chunk_id is required")

        self._validate_vector_size(vector)
        chunk_id = int(record_id)

        statement = sql_text(
            f'INSERT INTO "{collection_name}" '
            '(text, vector, metadata, chunk_id) '
            'VALUES (:text, CAST(:vector AS vector), '
            'CAST(:metadata AS jsonb), :chunk_id) '
            'ON CONFLICT (chunk_id) DO UPDATE SET '
            'text = EXCLUDED.text, '
            'vector = EXCLUDED.vector, '
            'metadata = EXCLUDED.metadata'
        )
        async with self.db_client() as session:
            await session.execute(
                statement,
                {
                    "text": text,
                    "vector": self._vector_literal(vector),
                    "metadata": json.dumps(
                        metadata or {},
                        ensure_ascii=False,
                    ),
                    "chunk_id": chunk_id,
                },
            )
            await session.commit()

        await self.create_vector_index(collection_name)
        return True

    async def insert_many(
        self,
        collection_name: str,
        texts: list[str],
        vectors: list[list[float]],
        metadata: list[dict | None] | None = None,
        record_ids: list[int | str] | None = None,
        batch_size: int = 50,
    ) -> bool:
        collection_name = self._validate_collection_name(
            collection_name
        )
        if not await self.is_collection_existed(collection_name):
            return False
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if record_ids is None:
            raise ValueError("record_ids are required")

        metadata = metadata or [{} for _ in texts]
        if not (
            len(texts)
            == len(vectors)
            == len(metadata)
            == len(record_ids)
        ):
            raise ValueError(
                "texts, vectors, metadata, and record_ids "
                "must have the same length"
            )

        for vector in vectors:
            self._validate_vector_size(vector)

        statement = sql_text(
            f'INSERT INTO "{collection_name}" '
            '(text, vector, metadata, chunk_id) '
            'VALUES (:text, CAST(:vector AS vector), '
            'CAST(:metadata AS jsonb), :chunk_id) '
            'ON CONFLICT (chunk_id) DO UPDATE SET '
            'text = EXCLUDED.text, '
            'vector = EXCLUDED.vector, '
            'metadata = EXCLUDED.metadata'
        )

        async with self.db_client() as session:
            for start in range(0, len(texts), batch_size):
                end = min(start + batch_size, len(texts))
                values = [
                    {
                        "text": texts[index],
                        "vector": self._vector_literal(
                            vectors[index]
                        ),
                        "metadata": json.dumps(
                            metadata[index] or {},
                            ensure_ascii=False,
                        ),
                        "chunk_id": int(record_ids[index]),
                    }
                    for index in range(start, end)
                ]
                await session.execute(statement, values)
            await session.commit()

        await self.create_vector_index(collection_name)
        return True

    async def search_by_vector(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
    ) -> list[RetrievedDocument]:
        collection_name = self._validate_collection_name(
            collection_name
        )
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        if not await self.is_collection_existed(collection_name):
            return []

        self._validate_vector_size(vector)
        vector_value = self._vector_literal(vector)

        if self.distance_operator == "<#>":
            score_expression = (
                "-(vector <#> CAST(:vector AS vector))"
            )
            order_expression = (
                "vector <#> CAST(:vector AS vector)"
            )
        else:
            score_expression = (
                "1 - (vector <=> CAST(:vector AS vector))"
            )
            order_expression = (
                "vector <=> CAST(:vector AS vector)"
            )

        statement = sql_text(
            f'SELECT chunk_id, text, metadata, '
            f'{score_expression} AS score '
            f'FROM "{collection_name}" '
            f'ORDER BY {order_expression} ASC '
            'LIMIT :limit'
        ).bindparams(bindparam("limit", type_=None))

        async with self.db_client() as session:
            result = await session.execute(
                statement,
                {
                    "vector": vector_value,
                    "limit": limit,
                },
            )
            records = result.fetchall()

        return [
            RetrievedDocument(
                chunk_id=int(record.chunk_id),
                text=record.text,
                score=float(record.score),
                metadata=dict(record.metadata or {}),
                asset_id=(record.metadata or {}).get("asset_id"),
                chunk_order=(record.metadata or {}).get("chunk_order"),
            )
            for record in records
        ]

    async def delete_by_ids(
        self,
        collection_name: str,
        record_ids: list[int | str],
    ) -> bool:
        collection_name = self._validate_collection_name(
            collection_name
        )
        if not record_ids:
            return True
        if not await self.is_collection_existed(collection_name):
            return False

        normalized_ids = [int(value) for value in record_ids]
        statement = sql_text(
            f'DELETE FROM "{collection_name}" '
            'WHERE chunk_id IN :record_ids'
        ).bindparams(
            bindparam(
                "record_ids",
                expanding=True,
            )
        )

        async with self.db_client() as session:
            await session.execute(
                statement,
                {"record_ids": normalized_ids},
            )
            await session.commit()
        return True
