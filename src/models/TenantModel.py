from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .BaseDataModel import BaseDataModel
from .db_schemes import Tenant

VALID_TENANT_STATUSES = {
    "active",
    "inactive",
    "suspended",
}
class TenantModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "TenantModel":

        return cls(db_client=db_client)

    # =========================
    # Create Tenant
    # =========================
    async def create_tenant(
        self,
        tenant: Tenant,
    ) -> Tenant:

        normalized_name = tenant.tenant_name.strip()
        normalized_code = tenant.tenant_code.strip().lower()
        normalized_status = tenant.tenant_status.strip().lower()

        if not normalized_name:
            raise ValueError(
                "tenant_name cannot be empty"
            )

        if not normalized_code:
            raise ValueError(
                "tenant_code cannot be empty"
            )

        if normalized_status not in VALID_TENANT_STATUSES:
            raise ValueError(
                "invalid tenant_status"
            )

        tenant.tenant_name = normalized_name
        tenant.tenant_code = normalized_code
        tenant.tenant_status = normalized_status

        if tenant.tenant_settings is None:
            tenant.tenant_settings = {}

        try:
            async with self.db_client() as session:
                session.add(tenant)

                await session.commit()
                await session.refresh(tenant)

                return tenant

        except IntegrityError as exc:
            raise ValueError(
                "Tenant code already exists."
            ) from exc

        except SQLAlchemyError:
            raise

    # =========================
    # Get Tenant By ID
    # =========================
    async def get_tenant_by_id(
        self,
        tenant_id: UUID,
    ) -> Tenant | None:

        async with self.db_client() as session:
            query = select(Tenant).where(
                Tenant.tenant_id == tenant_id
            )

            result = await session.execute(query)

            return result.scalar_one_or_none()

    # =========================
    # Get Tenant By Code
    # =========================
    async def get_tenant_by_code(
        self,
        tenant_code: str,
    ) -> Tenant | None:

        normalized_code = tenant_code.strip().lower()

        if not normalized_code:
            return None

        async with self.db_client() as session:
            query = select(Tenant).where(
                Tenant.tenant_code == normalized_code
            )

            result = await session.execute(query)

            return result.scalar_one_or_none()

    # =========================
    # Get All Tenants
    # =========================
    async def get_all_tenants(
        self,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Tenant], int, int]:

        safe_page = max(page, 1)
        safe_page_size = min(
            max(page_size, 1),
            100,
        )

        async with self.db_client() as session:
            count_query = select(
                func.count(Tenant.tenant_id)
            )

            count_result = await session.execute(
                count_query
            )

            total_tenants = count_result.scalar_one()

            total_pages = (
                total_tenants + safe_page_size - 1
            ) // safe_page_size

            query = (
                select(Tenant)
                .order_by(Tenant.created_at.desc())
                .offset(
                    (safe_page - 1) * safe_page_size
                )
                .limit(safe_page_size)
            )

            result = await session.execute(query)

            tenants = list(
                result.scalars().all()
            )

            return (
                tenants,
                total_tenants,
                total_pages,
            )

    # =========================
    # Update Tenant
    # =========================
    async def update_tenant(
        self,
        tenant_id: UUID,
        tenant_name: str | None = None,
        tenant_status: str | None = None,
        tenant_settings: dict | None = None,
    ) -> Tenant | None:

        try:
            async with self.db_client() as session:
                query = select(Tenant).where(
                    Tenant.tenant_id == tenant_id
                )

                result = await session.execute(query)
                tenant = result.scalar_one_or_none()

                if tenant is None:
                    return None

                if tenant_name is not None:
                    normalized_name = tenant_name.strip()

                    if not normalized_name:
                        raise ValueError(
                            "tenant_name cannot be empty"
                        )

                    tenant.tenant_name = normalized_name

                if tenant_status is not None:
                    normalized_status = (
                        tenant_status.strip().lower()
                    )

                    if (
                        normalized_status
                        not in VALID_TENANT_STATUSES
                    ):
                        raise ValueError(
                            "invalid tenant_status"
                        )

                    tenant.tenant_status = normalized_status

                if tenant_settings is not None:
                    if not isinstance(
                        tenant_settings,
                        dict,
                    ):
                        raise ValueError(
                            "tenant_settings must be a dict"
                        )

                    tenant.tenant_settings = dict(
                        tenant_settings
                    )

                await session.commit()
                await session.refresh(tenant)

                return tenant

        except IntegrityError as exc:
            raise ValueError(
                "Could not update tenant."
            ) from exc

        except SQLAlchemyError:
            raise

    # =========================
    # Delete Tenant
    # =========================
    async def delete_tenant(
        self,
        tenant_id: UUID,
    ) -> bool:

        try:
            async with self.db_client() as session:
                query = select(Tenant).where(
                    Tenant.tenant_id == tenant_id
                )

                result = await session.execute(query)
                tenant = result.scalar_one_or_none()

                if tenant is None:
                    return False

                await session.delete(tenant)
                await session.commit()

                return True

        except SQLAlchemyError:
            raise

    # =========================
    # Check Tenant Exists
    # =========================
    async def tenant_exists(
        self,
        tenant_id: UUID,
    ) -> bool:

        async with self.db_client() as session:
            query = select(
                Tenant.tenant_id
            ).where(
                Tenant.tenant_id == tenant_id
            )

            result = await session.execute(query)

            return result.scalar_one_or_none() is not None

    # =========================
    # Check Tenant Is Active
    # =========================
    async def tenant_is_active(
        self,
        tenant_id: UUID,
    ) -> bool:

        async with self.db_client() as session:
            query = select(
                Tenant.tenant_id
            ).where(
                Tenant.tenant_id == tenant_id,
                Tenant.tenant_status == "active",
            )

            result = await session.execute(query)

            return result.scalar_one_or_none() is not None