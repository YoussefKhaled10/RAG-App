from typing import List
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .BaseDataModel import BaseDataModel
from .db_schemes import Asset, Project
VALID_ASSET_STATUSES = {
    "uploaded",
    "processing",
    "indexed",
    "failed",
}
class AssetModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "AssetModel":
        return cls(db_client=db_client)

    # =========================
    # Create Asset
    # =========================
    async def create_asset(
        self,
        tenant_id: UUID,
        asset: Asset,
    ) -> Asset:

        try:
            async with self.db_client() as session:

                project_query = select(
                    Project.project_id
                ).where(
                    Project.project_id
                    == asset.asset_project_id,
                    Project.tenant_id
                    == tenant_id,
                )

                project_result = await session.execute(
                    project_query
                )

                if (
                    project_result.scalar_one_or_none()
                    is None
                ):
                    raise ValueError(
                        "project not found for this tenant"
                    )

                session.add(asset)

                await session.commit()
                await session.refresh(asset)

                return asset

        except IntegrityError as exc:
            raise ValueError(
                "could not create asset"
            ) from exc

        except SQLAlchemyError:
            raise

    # =========================
    # Get Asset By ID
    # =========================
    async def get_asset_by_id(
        self,
        tenant_id: UUID,
        asset_id: int,
    ) -> Asset | None:

        async with self.db_client() as session:

            query = (
                select(Asset)
                .join(
                    Project,
                    Project.project_id
                    == Asset.asset_project_id,
                )
                .where(
                    Asset.asset_id == asset_id,
                    Project.tenant_id == tenant_id,
                )
            )

            result = await session.execute(query)

            return result.scalar_one_or_none()

    # =========================
    # Get Asset By UUID
    # =========================
    async def get_asset_by_uuid(
        self,
        tenant_id: UUID,
        asset_uuid: UUID,
    ) -> Asset | None:

        async with self.db_client() as session:

            query = (
                select(Asset)
                .join(
                    Project,
                    Project.project_id
                    == Asset.asset_project_id,
                )
                .where(
                    Asset.asset_uuid == asset_uuid,
                    Project.tenant_id == tenant_id,
                )
            )

            result = await session.execute(query)

            return result.scalar_one_or_none()

    # =========================
    # Get Project Assets
    # =========================
    async def get_all_project_assets(
        self,
        tenant_id: UUID,
        asset_project_id: int,
        asset_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[Asset], int, int]:

        safe_page = max(
            page,
            1,
        )

        safe_page_size = min(
            max(page_size, 1),
            100,
        )

        async with self.db_client() as session:

            filters = [
                Asset.asset_project_id
                == asset_project_id,
                Project.tenant_id
                == tenant_id,
            ]

            if asset_type is not None:
                filters.append(
                    Asset.asset_type == asset_type
                )

            count_query = (
                select(
                    func.count(Asset.asset_id)
                )
                .join(
                    Project,
                    Project.project_id
                    == Asset.asset_project_id,
                )
                .where(*filters)
            )

            count_result = await session.execute(
                count_query
            )

            total_assets = count_result.scalar_one()

            total_pages = (
                total_assets
                + safe_page_size
                - 1
            ) // safe_page_size

            query = (
                select(Asset)
                .join(
                    Project,
                    Project.project_id
                    == Asset.asset_project_id,
                )
                .where(*filters)
                .order_by(
                    Asset.created_at.desc()
                )
                .offset(
                    (safe_page - 1)
                    * safe_page_size
                )
                .limit(safe_page_size)
            )

            result = await session.execute(query)

            assets = list(
                result.scalars().all()
            )

            return (
                assets,
                total_assets,
                total_pages,
            )

    # =========================
    # Get Asset By Name
    # =========================
    async def get_asset_record(
        self,
        tenant_id: UUID,
        asset_project_id: int,
        asset_name: str,
    ) -> Asset | None:

        async with self.db_client() as session:

            query = (
                select(Asset)
                .join(
                    Project,
                    Project.project_id
                    == Asset.asset_project_id,
                )
                .where(
                    Asset.asset_project_id
                    == asset_project_id,
                    Asset.asset_name
                    == asset_name,
                    Project.tenant_id
                    == tenant_id,
                )
            )

            result = await session.execute(query)

            return result.scalar_one_or_none()

    # =========================
    # Update Asset Status
    # =========================
    async def update_asset_status(
        self,
        tenant_id: UUID,
        asset_id: int,
        status: str,
        error: str | None = None,
        indexed_chunks: int | None = None,
        clear_error: bool = False,
    ) -> Asset | None:

        if status not in VALID_ASSET_STATUSES:
            raise ValueError(
                "invalid asset status"
            )

        if (
            indexed_chunks is not None
            and indexed_chunks < 0
        ):
            raise ValueError(
                "indexed_chunks cannot be negative"
            )

        try:
            async with self.db_client() as session:

                query = (
                    select(Asset)
                    .join(
                        Project,
                        Project.project_id
                        == Asset.asset_project_id,
                    )
                    .where(
                        Asset.asset_id == asset_id,
                        Project.tenant_id
                        == tenant_id,
                    )
                )

                result = await session.execute(query)

                asset = result.scalar_one_or_none()

                if asset is None:
                    return None

                asset.asset_status = status

                if clear_error:
                    asset.asset_error = None

                elif error is not None:
                    asset.asset_error = error

                if indexed_chunks is not None:
                    asset.asset_indexed_chunks = (
                        indexed_chunks
                    )

                await session.commit()
                await session.refresh(asset)

                return asset

        except SQLAlchemyError:
            raise

    # =========================
    # Mark Asset Processing
    # =========================
    async def mark_asset_processing(
        self,
        tenant_id: UUID,
        asset_id: int,
    ) -> Asset | None:

        return await self.update_asset_status(
            tenant_id=tenant_id,
            asset_id=asset_id,
            status="processing",
            indexed_chunks=0,
            clear_error=True,
        )

    # =========================
    # Mark Asset Indexed
    # =========================
    async def mark_asset_indexed(
        self,
        tenant_id: UUID,
        asset_id: int,
        indexed_chunks: int,
    ) -> Asset | None:

        return await self.update_asset_status(
            tenant_id=tenant_id,
            asset_id=asset_id,
            status="indexed",
            indexed_chunks=indexed_chunks,
            clear_error=True,
        )

    # =========================
    # Mark Asset Failed
    # =========================
    async def mark_asset_failed(
        self,
        tenant_id: UUID,
        asset_id: int,
        error: str,
    ) -> Asset | None:

        return await self.update_asset_status(
            tenant_id=tenant_id,
            asset_id=asset_id,
            status="failed",
            error=error,
        )

    # =========================
    # Delete Asset
    # =========================
    async def delete_asset(
        self,
        tenant_id: UUID,
        asset_id: int,
    ) -> bool:

        try:
            async with self.db_client() as session:

                query = (
                    select(Asset)
                    .join(
                        Project,
                        Project.project_id
                        == Asset.asset_project_id,
                    )
                    .where(
                        Asset.asset_id == asset_id,
                        Project.tenant_id
                        == tenant_id,
                    )
                )

                result = await session.execute(query)

                asset = result.scalar_one_or_none()

                if asset is None:
                    return False

                await session.delete(asset)
                await session.commit()

                return True

        except SQLAlchemyError:
            raise

    # =========================
    # Check Asset Exists
    # =========================
    async def asset_exists(
        self,
        tenant_id: UUID,
        asset_id: int,
    ) -> bool:

        async with self.db_client() as session:

            query = (
                select(Asset.asset_id)
                .join(
                    Project,
                    Project.project_id
                    == Asset.asset_project_id,
                )
                .where(
                    Asset.asset_id == asset_id,
                    Project.tenant_id == tenant_id,
                )
            )

            result = await session.execute(query)

            return (
                result.scalar_one_or_none()
                is not None
            )