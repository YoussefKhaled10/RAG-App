import re
from typing import List
from uuid import UUID

from sqlalchemy import (
    Text,
    cast,
    delete,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .BaseDataModel import BaseDataModel
from .db_schemes import Asset, DataChunk, Project


class ChunkModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "ChunkModel":
        return cls(db_client=db_client)

    # =========================
    # Create Chunk
    # =========================
    async def create_chunk(
        self,
        tenant_id: UUID,
        chunk: DataChunk,
    ) -> DataChunk:
        try:
            async with self.db_client() as session:
                ownership_query = (
                    select(Asset.asset_id)
                    .join(
                        Project,
                        Project.project_id
                        == Asset.asset_project_id,
                    )
                    .where(
                        Asset.asset_id
                        == chunk.chunk_asset_id,
                        Asset.asset_project_id
                        == chunk.chunk_project_id,
                        Project.tenant_id == tenant_id,
                    )
                )

                ownership_result = await session.execute(
                    ownership_query
                )

                if (
                    ownership_result.scalar_one_or_none()
                    is None
                ):
                    raise ValueError(
                        "asset and project were not found "
                        "for this tenant"
                    )

                session.add(chunk)
                await session.commit()
                await session.refresh(chunk)
                return chunk

        except IntegrityError as exc:
            raise ValueError(
                "could not create chunk"
            ) from exc
        except SQLAlchemyError:
            raise

    # =========================
    # Insert Many Chunks
    # =========================
    async def insert_many_chunks(
        self,
        tenant_id: UUID,
        chunks: List[DataChunk],
        batch_size: int = 100,
    ) -> int:
        if not chunks:
            return 0

        safe_batch_size = min(
            max(batch_size, 1),
            1000,
        )

        project_ids = {
            chunk.chunk_project_id
            for chunk in chunks
        }
        asset_ids = {
            chunk.chunk_asset_id
            for chunk in chunks
        }

        if len(project_ids) != 1 or len(asset_ids) != 1:
            raise ValueError(
                "all chunks in one batch must belong "
                "to one project and one asset"
            )

        project_id = next(iter(project_ids))
        asset_id = next(iter(asset_ids))

        try:
            async with self.db_client() as session:
                ownership_query = (
                    select(Asset.asset_id)
                    .join(
                        Project,
                        Project.project_id
                        == Asset.asset_project_id,
                    )
                    .where(
                        Asset.asset_id == asset_id,
                        Asset.asset_project_id == project_id,
                        Project.tenant_id == tenant_id,
                    )
                )

                ownership_result = await session.execute(
                    ownership_query
                )

                if (
                    ownership_result.scalar_one_or_none()
                    is None
                ):
                    raise ValueError(
                        "asset and project were not found "
                        "for this tenant"
                    )

                for index in range(
                    0,
                    len(chunks),
                    safe_batch_size,
                ):
                    batch = chunks[
                        index:index + safe_batch_size
                    ]
                    session.add_all(batch)

                await session.flush()
                await session.commit()
                return len(chunks)

        except IntegrityError as exc:
            raise ValueError(
                "could not insert chunks"
            ) from exc
        except SQLAlchemyError:
            raise

    # =========================
    # Get Chunks By Asset ID
    # =========================
    async def get_chunks_by_asset_id(
        self,
        tenant_id: UUID,
        asset_id: int,
    ) -> List[DataChunk]:
        async with self.db_client() as session:
            query = (
                select(DataChunk)
                .join(
                    Project,
                    Project.project_id
                    == DataChunk.chunk_project_id,
                )
                .where(
                    DataChunk.chunk_asset_id == asset_id,
                    Project.tenant_id == tenant_id,
                )
                .order_by(
                    DataChunk.chunk_order.asc()
                )
            )

            result = await session.execute(query)
            return list(result.scalars().all())

    # =========================
    # Delete Chunks By Asset ID
    # =========================
    async def delete_chunks_by_asset_id(
        self,
        tenant_id: UUID,
        asset_id: int,
    ) -> int:
        try:
            async with self.db_client() as session:
                chunk_ids_query = (
                    select(DataChunk.chunk_id)
                    .join(
                        Project,
                        Project.project_id
                        == DataChunk.chunk_project_id,
                    )
                    .where(
                        DataChunk.chunk_asset_id
                        == asset_id,
                        Project.tenant_id == tenant_id,
                    )
                )

                chunk_ids_result = await session.execute(
                    chunk_ids_query
                )
                chunk_ids = list(
                    chunk_ids_result.scalars().all()
                )

                if not chunk_ids:
                    return 0

                delete_query = delete(DataChunk).where(
                    DataChunk.chunk_id.in_(chunk_ids)
                )
                result = await session.execute(
                    delete_query
                )
                await session.commit()
                return result.rowcount or 0

        except SQLAlchemyError:
            raise

    # =========================
    # Delete Chunks By Project ID
    # =========================
    async def delete_chunks_by_project_id(
        self,
        tenant_id: UUID,
        project_id: int,
    ) -> int:
        try:
            async with self.db_client() as session:
                project_query = select(
                    Project.project_id
                ).where(
                    Project.project_id == project_id,
                    Project.tenant_id == tenant_id,
                )

                project_result = await session.execute(
                    project_query
                )

                if (
                    project_result.scalar_one_or_none()
                    is None
                ):
                    return 0

                delete_query = delete(DataChunk).where(
                    DataChunk.chunk_project_id
                    == project_id
                )
                result = await session.execute(
                    delete_query
                )
                await session.commit()
                return result.rowcount or 0

        except SQLAlchemyError:
            raise

    # =========================
    # Get Total Chunks Count
    # =========================
    async def get_total_chunks_count(
        self,
        tenant_id: UUID,
        project_id: int,
    ) -> int:
        async with self.db_client() as session:
            query = (
                select(
                    func.count(DataChunk.chunk_id)
                )
                .join(
                    Project,
                    Project.project_id
                    == DataChunk.chunk_project_id,
                )
                .where(
                    DataChunk.chunk_project_id
                    == project_id,
                    Project.tenant_id == tenant_id,
                )
            )

            result = await session.execute(query)
            return result.scalar_one()

    # =========================
    # Get Project Chunks
    # =========================
    async def get_project_chunks(
        self,
        tenant_id: UUID,
        project_id: int,
        page_no: int = 1,
        page_size: int = 50,
    ) -> List[DataChunk]:
        safe_page_no = max(page_no, 1)
        safe_page_size = min(
            max(page_size, 1),
            100,
        )

        async with self.db_client() as session:
            query = (
                select(DataChunk)
                .join(
                    Project,
                    Project.project_id
                    == DataChunk.chunk_project_id,
                )
                .where(
                    DataChunk.chunk_project_id
                    == project_id,
                    Project.tenant_id == tenant_id,
                )
                .order_by(
                    DataChunk.chunk_order.asc()
                )
                .offset(
                    (safe_page_no - 1)
                    * safe_page_size
                )
                .limit(safe_page_size)
            )

            result = await session.execute(query)
            return list(result.scalars().all())

    # =========================
    # Backward-Compatible Alias
    # =========================
    async def get_poject_chunks(
        self,
        tenant_id: UUID,
        project_id: int,
        page_no: int = 1,
        page_size: int = 50,
    ) -> List[DataChunk]:
        return await self.get_project_chunks(
            tenant_id=tenant_id,
            project_id=project_id,
            page_no=page_no,
            page_size=page_size,
        )

    # =========================
    # Hybrid Keyword Search
    # =========================
    async def keyword_search(
        self,
        tenant_id: UUID,
        project_id: int,
        query_text: str,
        limit: int = 20,
    ) -> list[dict]:
        """
        Search project chunks using:

        1. PostgreSQL Full-Text Search.
        2. Trigram text similarity.
        3. Exact substring matching with ILIKE.
        4. Tenant and project isolation.
        """

        clean_query = " ".join(
            str(query_text).split()
        )

        if not clean_query:
            return []

        safe_limit = min(
            max(limit, 1),
            100,
        )

        query_as_text = cast(
            clean_query.lower(),
            Text,
        )

        full_text_vector = func.to_tsvector(
            "simple",
            DataChunk.chunk_text,
        )

        full_text_query = func.websearch_to_tsquery(
            "simple",
            clean_query,
        )

        full_text_score = func.ts_rank_cd(
            full_text_vector,
            full_text_query,
        )

        trigram_score = func.coalesce(
            func.similarity(
                func.lower(
                    DataChunk.chunk_text
                ),
                query_as_text,
            ),
            0.0,
        )

        keyword_score = func.greatest(
            full_text_score,
            trigram_score,
        ).label("keyword_score")

        async with self.db_client() as session:
            search_query = (
                select(
                    DataChunk.chunk_id,
                    DataChunk.chunk_text,
                    DataChunk.chunk_metadata,
                    DataChunk.chunk_asset_id,
                    DataChunk.chunk_order,
                    keyword_score,
                )
                .join(
                    Project,
                    Project.project_id
                    == DataChunk.chunk_project_id,
                )
                .where(
                    DataChunk.chunk_project_id
                    == project_id,
                    Project.tenant_id
                    == tenant_id,
                    (
                        full_text_vector.op("@@")(
                            full_text_query
                        )
                        |
                        DataChunk.chunk_text.ilike(
                            "%{}%".format(
                                re.sub(
                                    r"([%_\\])",
                                    r"\\\1",
                                    clean_query,
                                )
                            )
                        )
                        |
                        (
                            func.similarity(
                                func.lower(
                                    DataChunk.chunk_text
                                ),
                                query_as_text,
                            )
                            > 0.05
                        )
                    ),
                )
                .order_by(
                    keyword_score.desc(),
                    DataChunk.chunk_id.asc(),
                )
                .limit(safe_limit)
            )

            result = await session.execute(
                search_query
            )
            rows = result.fetchall()

            return [
                {
                    "chunk_id": int(
                        row.chunk_id
                    ),
                    "text": row.chunk_text,
                    "metadata": dict(
                        row.chunk_metadata or {}
                    ),
                    "asset_id": (
                        row.chunk_asset_id
                    ),
                    "chunk_order": (
                        row.chunk_order
                    ),
                    "score": float(
                        row.keyword_score or 0.0
                    ),
                }
                for row in rows
            ]