from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload
from .BaseDataModel import BaseDataModel
from .db_schemes import Tenant, User

VALID_USER_STATUSES = {
    "active",
    "inactive",
    "suspended",
}
class UserModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "UserModel":
        return cls(db_client=db_client)

    # =========================
    # Create User
    # =========================
    async def create_user(
        self,
        user: User,
    ) -> User:

        normalized_email = user.user_email.strip().lower()
        normalized_status = user.user_status.strip().lower()

        normalized_full_name = (
            " ".join(user.user_full_name.split())
            if user.user_full_name
            else None
        )

        if not normalized_email:
            raise ValueError(
                "user_email cannot be empty"
            )

        if (
            not user.password_hash
            or not user.password_hash.strip()
        ):
            raise ValueError(
                "password_hash cannot be empty"
            )

        if normalized_status not in VALID_USER_STATUSES:
            raise ValueError(
                "invalid user_status"
            )

        user.user_email = normalized_email
        user.user_status = normalized_status
        user.user_full_name = normalized_full_name

        try:
            async with self.db_client() as session:

                tenant_query = select(
                    Tenant.tenant_id
                ).where(
                    Tenant.tenant_id == user.tenant_id,
                    Tenant.tenant_status == "active",
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

                session.add(user)

                await session.commit()
                await session.refresh(user)

                return user

        except IntegrityError as exc:
            raise ValueError(
                "User email already exists "
                "in this tenant."
            ) from exc

        except SQLAlchemyError:
            raise

    # =========================
    # Get User By ID
    # =========================
    async def get_user_by_id(
        self,
        tenant_id: UUID,
        user_id: UUID,
        include_roles: bool = False,
    ) -> User | None:

        async with self.db_client() as session:

            query = select(User).where(
                User.user_id == user_id,
                User.tenant_id == tenant_id,
            )

            if include_roles:
                query = query.options(
                    selectinload(User.roles)
                )

            result = await session.execute(query)

            return result.scalar_one_or_none()

    # =========================
    # Get User By Email
    # =========================
    async def get_user_by_email(
        self,
        tenant_id: UUID,
        user_email: str,
        include_roles: bool = False,
    ) -> User | None:

        normalized_email = (
            user_email.strip().lower()
        )

        if not normalized_email:
            return None

        async with self.db_client() as session:

            query = select(User).where(
                User.tenant_id == tenant_id,
                User.user_email == normalized_email,
            )

            if include_roles:
                query = query.options(
                    selectinload(User.roles)
                )

            result = await session.execute(query)

            return result.scalar_one_or_none()

    # =========================
    # Get User By Tenant Code
    # And Email
    # Used During Login
    # =========================
    async def get_user_by_tenant_code_and_email(
        self,
        tenant_code: str,
        user_email: str,
        include_roles: bool = False,
    ) -> User | None:

        normalized_tenant_code = (
            tenant_code.strip().lower()
        )

        normalized_email = (
            user_email.strip().lower()
        )

        if (
            not normalized_tenant_code
            or not normalized_email
        ):
            return None

        async with self.db_client() as session:

            query = (
                select(User)
                .join(
                    Tenant,
                    Tenant.tenant_id
                    == User.tenant_id,
                )
                .where(
                    Tenant.tenant_code
                    == normalized_tenant_code,
                    Tenant.tenant_status
                    == "active",
                    User.user_email
                    == normalized_email,
                )
            )

            if include_roles:
                query = query.options(
                    selectinload(User.roles)
                )

            result = await session.execute(query)

            return result.scalar_one_or_none()

    # =========================
    # Get Tenant Users
    # =========================
    async def get_tenant_users(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 10,
        include_roles: bool = False,
    ) -> tuple[list[User], int, int]:

        safe_page = max(page, 1)

        safe_page_size = min(
            max(page_size, 1),
            100,
        )

        async with self.db_client() as session:

            count_query = select(
                func.count(User.user_id)
            ).where(
                User.tenant_id == tenant_id
            )

            count_result = await session.execute(
                count_query
            )

            total_users = count_result.scalar_one()

            total_pages = (
                total_users + safe_page_size - 1
            ) // safe_page_size

            query = (
                select(User)
                .where(
                    User.tenant_id == tenant_id
                )
                .order_by(
                    User.created_at.desc()
                )
                .offset(
                    (safe_page - 1)
                    * safe_page_size
                )
                .limit(safe_page_size)
            )

            if include_roles:
                query = query.options(
                    selectinload(User.roles)
                )

            result = await session.execute(query)

            users = list(
                result.scalars()
                .unique()
                .all()
            )

            return (
                users,
                total_users,
                total_pages,
            )

    # =========================
    # Update User
    # =========================
    async def update_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        user_full_name: str | None = None,
        user_status: str | None = None,
        is_tenant_admin: bool | None = None,
    ) -> User | None:

        try:
            async with self.db_client() as session:

                query = select(User).where(
                    User.user_id == user_id,
                    User.tenant_id == tenant_id,
                )

                result = await session.execute(
                    query
                )

                user = result.scalar_one_or_none()

                if user is None:
                    return None

                if user_full_name is not None:
                    normalized_full_name = " ".join(
                        user_full_name.split()
                    )

                    user.user_full_name = (
                        normalized_full_name
                        or None
                    )

                if user_status is not None:
                    normalized_status = (
                        user_status
                        .strip()
                        .lower()
                    )

                    if (
                        normalized_status
                        not in VALID_USER_STATUSES
                    ):
                        raise ValueError(
                            "invalid user_status"
                        )

                    user.user_status = (
                        normalized_status
                    )

                if is_tenant_admin is not None:
                    user.is_tenant_admin = (
                        is_tenant_admin
                    )

                await session.commit()
                await session.refresh(user)

                return user

        except IntegrityError as exc:
            raise ValueError(
                "Could not update user."
            ) from exc

        except SQLAlchemyError:
            raise

    # =========================
    # Update Password Hash
    # =========================
    async def update_password(
        self,
        tenant_id: UUID,
        user_id: UUID,
        password_hash: str,
    ) -> bool:

        if (
            not password_hash
            or not password_hash.strip()
        ):
            raise ValueError(
                "password_hash cannot be empty"
            )

        try:
            async with self.db_client() as session:

                query = select(User).where(
                    User.user_id == user_id,
                    User.tenant_id == tenant_id,
                )

                result = await session.execute(
                    query
                )

                user = result.scalar_one_or_none()

                if user is None:
                    return False

                user.password_hash = password_hash

                await session.commit()

                return True

        except SQLAlchemyError:
            raise

    # =========================
    # Update Last Login
    # =========================
    async def update_last_login(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:

        try:
            async with self.db_client() as session:

                query = select(User).where(
                    User.user_id == user_id,
                    User.tenant_id == tenant_id,
                )

                result = await session.execute(
                    query
                )

                user = result.scalar_one_or_none()

                if user is None:
                    return False

                user.last_login_at = datetime.now(
                    timezone.utc
                )

                await session.commit()

                return True

        except SQLAlchemyError:
            raise

    # =========================
    # Delete User
    # =========================
    async def delete_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:

        try:
            async with self.db_client() as session:

                query = select(User).where(
                    User.user_id == user_id,
                    User.tenant_id == tenant_id,
                )

                result = await session.execute(
                    query
                )

                user = result.scalar_one_or_none()

                if user is None:
                    return False

                await session.delete(user)
                await session.commit()

                return True

        except SQLAlchemyError:
            raise

    # =========================
    # Check User Exists
    # =========================
    async def user_exists(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:

        async with self.db_client() as session:

            query = select(
                User.user_id
            ).where(
                User.user_id == user_id,
                User.tenant_id == tenant_id,
            )

            result = await session.execute(query)

            return (
                result.scalar_one_or_none()
                is not None
            )

    # =========================
    # Check User Is Active
    # =========================
    async def user_is_active(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:

        async with self.db_client() as session:

            query = select(
                User.user_id
            ).where(
                User.user_id == user_id,
                User.tenant_id == tenant_id,
                User.user_status == "active",
            )

            result = await session.execute(query)

            return (
                result.scalar_one_or_none()
                is not None
            )