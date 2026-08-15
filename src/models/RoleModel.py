from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload
from .BaseDataModel import BaseDataModel
from .db_schemes import Role, Tenant


class RoleModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "RoleModel":
        return cls(db_client=db_client)

    # =========================
    # Create Role
    # =========================
    async def create_role(
        self,
        role: Role,
    ) -> Role:

        try:
            async with self.db_client() as session:

                tenant_query = select(
                    Tenant.tenant_id
                ).where(
                    Tenant.tenant_id
                    == role.tenant_id,
                    Tenant.tenant_status
                    == "active",
                )

                tenant_result = await session.execute(
                    tenant_query
                )

                if (
                    tenant_result.scalar_one_or_none()
                    is None
                ):
                    raise ValueError(
                        "active tenant not found"
                    )

                session.add(role)

                await session.commit()
                await session.refresh(role)

                return role

        except IntegrityError as exc:
            raise ValueError(
                "Role name already exists "
                "in this tenant."
            ) from exc

        except SQLAlchemyError:
            raise

    # =========================
    # Get Role By ID
    # =========================
    async def get_role_by_id(
        self,
        tenant_id: UUID,
        role_id: UUID,
        include_users: bool = False,
    ) -> Role | None:

        async with self.db_client() as session:

            query = select(Role).where(
                Role.role_id == role_id,
                Role.tenant_id == tenant_id,
            )

            if include_users:
                query = query.options(
                    selectinload(Role.users)
                )

            result = await session.execute(query)

            return result.scalar_one_or_none()

    # =========================
    # Get Role By Name
    # =========================
    async def get_role_by_name(
        self,
        tenant_id: UUID,
        role_name: str,
        include_users: bool = False,
    ) -> Role | None:

        async with self.db_client() as session:

            query = select(Role).where(
                Role.tenant_id == tenant_id,
                Role.role_name == role_name,
            )

            if include_users:
                query = query.options(
                    selectinload(Role.users)
                )

            result = await session.execute(query)

            return result.scalar_one_or_none()

    # =========================
    # Get Tenant Roles
    # =========================
    async def get_tenant_roles(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 10,
        include_users: bool = False,
    ) -> tuple[list[Role], int, int]:

        safe_page = max(page, 1)

        safe_page_size = min(
            max(page_size, 1),
            100,
        )

        async with self.db_client() as session:

            count_query = select(
                func.count(Role.role_id)
            ).where(
                Role.tenant_id == tenant_id
            )

            count_result = await session.execute(
                count_query
            )

            total_roles = count_result.scalar_one()

            total_pages = (
                total_roles + safe_page_size - 1
            ) // safe_page_size

            query = (
                select(Role)
                .where(
                    Role.tenant_id == tenant_id
                )
                .order_by(
                    Role.created_at.desc()
                )
                .offset(
                    (safe_page - 1)
                    * safe_page_size
                )
                .limit(safe_page_size)
            )

            if include_users:
                query = query.options(
                    selectinload(Role.users)
                )

            result = await session.execute(query)

            roles = list(
                result.scalars()
                .unique()
                .all()
            )

            return (
                roles,
                total_roles,
                total_pages,
            )

    # =========================
    # Update Role
    # =========================
    async def update_role(
        self,
        tenant_id: UUID,
        role_id: UUID,
        role_name: str | None = None,
        role_description: str | None = None,
    ) -> Role | None:

        try:
            async with self.db_client() as session:

                query = select(Role).where(
                    Role.role_id == role_id,
                    Role.tenant_id == tenant_id,
                )

                result = await session.execute(
                    query
                )

                role = result.scalar_one_or_none()

                if role is None:
                    return None

                if role_name is not None:
                    role.role_name = role_name

                if role_description is not None:
                    role.role_description = (
                        role_description
                    )

                await session.commit()
                await session.refresh(role)

                return role

        except IntegrityError as exc:
            raise ValueError(
                "Role name already exists "
                "in this tenant."
            ) from exc

        except SQLAlchemyError:
            raise

    # =========================
    # Delete Role
    # =========================
    async def delete_role(
        self,
        tenant_id: UUID,
        role_id: UUID,
    ) -> bool:

        try:
            async with self.db_client() as session:

                query = select(Role).where(
                    Role.role_id == role_id,
                    Role.tenant_id == tenant_id,
                )

                result = await session.execute(
                    query
                )

                role = result.scalar_one_or_none()

                if role is None:
                    return False

                if role.is_system_role:
                    raise ValueError(
                        "system roles cannot be deleted"
                    )

                await session.delete(role)
                await session.commit()

                return True

        except SQLAlchemyError:
            raise

    # =========================
    # Check Role Exists
    # =========================
    async def role_exists(
        self,
        tenant_id: UUID,
        role_id: UUID,
    ) -> bool:

        async with self.db_client() as session:

            query = select(
                Role.role_id
            ).where(
                Role.role_id == role_id,
                Role.tenant_id == tenant_id,
            )

            result = await session.execute(query)

            return (
                result.scalar_one_or_none()
                is not None
            )