from typing import List
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .BaseDataModel import BaseDataModel
from .db_schemes import Role, User, UserRole


class UserRoleModel(BaseDataModel):

    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "UserRoleModel":
        return cls(db_client=db_client)

    # =========================
    # Assign One Role To User
    # =========================
    async def assign_role_to_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        role_id: UUID,
    ) -> UserRole:

        try:
            async with self.db_client() as session:

                user_query = select(
                    User.user_id
                ).where(
                    User.user_id == user_id,
                    User.tenant_id == tenant_id,
                    User.user_status == "active",
                )

                user_result = await session.execute(
                    user_query
                )

                if user_result.scalar_one_or_none() is None:
                    raise ValueError(
                        "active user not found"
                    )

                role_query = select(
                    Role.role_id
                ).where(
                    Role.role_id == role_id,
                    Role.tenant_id == tenant_id,
                )

                role_result = await session.execute(
                    role_query
                )

                if role_result.scalar_one_or_none() is None:
                    raise ValueError(
                        "role not found"
                    )

                existing_query = select(
                    UserRole
                ).where(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id,
                )

                existing_result = await session.execute(
                    existing_query
                )

                existing_assignment = (
                    existing_result.scalar_one_or_none()
                )

                if existing_assignment is not None:
                    return existing_assignment

                assignment = UserRole(
                    user_id=user_id,
                    role_id=role_id,
                )

                session.add(assignment)

                await session.commit()
                await session.refresh(assignment)

                return assignment

        except IntegrityError as exc:
            raise ValueError(
                "role is already assigned to user"
            ) from exc

        except SQLAlchemyError:
            raise

    # =========================
    # Assign Multiple Roles
    # =========================
    async def assign_roles_to_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        role_ids: List[UUID],
    ) -> List[UserRole]:

        if not role_ids:
            return []

        unique_role_ids = list(
            dict.fromkeys(role_ids)
        )

        try:
            async with self.db_client() as session:

                user_query = select(
                    User.user_id
                ).where(
                    User.user_id == user_id,
                    User.tenant_id == tenant_id,
                    User.user_status == "active",
                )

                user_result = await session.execute(
                    user_query
                )

                if user_result.scalar_one_or_none() is None:
                    raise ValueError(
                        "active user not found"
                    )

                roles_query = select(
                    Role.role_id
                ).where(
                    Role.tenant_id == tenant_id,
                    Role.role_id.in_(unique_role_ids),
                )

                roles_result = await session.execute(
                    roles_query
                )

                valid_role_ids = set(
                    roles_result.scalars().all()
                )

                missing_role_ids = (
                    set(unique_role_ids)
                    - valid_role_ids
                )

                if missing_role_ids:
                    raise ValueError(
                        "one or more roles were not found"
                    )

                existing_query = select(
                    UserRole
                ).where(
                    UserRole.user_id == user_id,
                    UserRole.role_id.in_(
                        unique_role_ids
                    ),
                )

                existing_result = await session.execute(
                    existing_query
                )

                existing_assignments = list(
                    existing_result.scalars().all()
                )

                existing_role_ids = {
                    assignment.role_id
                    for assignment
                    in existing_assignments
                }

                new_assignments = [
                    UserRole(
                        user_id=user_id,
                        role_id=role_id,
                    )
                    for role_id in unique_role_ids
                    if role_id
                    not in existing_role_ids
                ]

                if new_assignments:
                    session.add_all(
                        new_assignments
                    )

                    await session.commit()

                    for assignment in new_assignments:
                        await session.refresh(
                            assignment
                        )

                return (
                    existing_assignments
                    + new_assignments
                )

        except IntegrityError as exc:
            raise ValueError(
                "one or more roles are already "
                "assigned to user"
            ) from exc

        except SQLAlchemyError:
            raise

    # =========================
    # Check User Has Role
    # =========================
    async def user_has_role(
        self,
        tenant_id: UUID,
        user_id: UUID,
        role_id: UUID,
    ) -> bool:

        async with self.db_client() as session:

            query = (
                select(UserRole.user_id)
                .join(
                    User,
                    User.user_id
                    == UserRole.user_id,
                )
                .join(
                    Role,
                    Role.role_id
                    == UserRole.role_id,
                )
                .where(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role_id,
                    User.tenant_id == tenant_id,
                    Role.tenant_id == tenant_id,
                )
            )

            result = await session.execute(
                query
            )

            return (
                result.scalar_one_or_none()
                is not None
            )

    # =========================
    # Get User Roles
    # =========================
    async def get_user_roles(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> List[Role]:

        async with self.db_client() as session:

            query = (
                select(Role)
                .join(
                    UserRole,
                    UserRole.role_id
                    == Role.role_id,
                )
                .join(
                    User,
                    User.user_id
                    == UserRole.user_id,
                )
                .where(
                    User.user_id == user_id,
                    User.tenant_id == tenant_id,
                    Role.tenant_id == tenant_id,
                )
                .order_by(
                    Role.role_name.asc()
                )
            )

            result = await session.execute(
                query
            )

            return list(
                result.scalars()
                .unique()
                .all()
            )

    # =========================
    # Get User Role IDs
    # =========================
    async def get_user_role_ids(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> List[UUID]:

        roles = await self.get_user_roles(
            tenant_id=tenant_id,
            user_id=user_id,
        )

        return [
            role.role_id
            for role in roles
        ]

    # =========================
    # Count User Roles
    # =========================
    async def count_user_roles(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> int:

        async with self.db_client() as session:

            query = (
                select(
                    func.count(
                        UserRole.role_id
                    )
                )
                .join(
                    User,
                    User.user_id
                    == UserRole.user_id,
                )
                .where(
                    UserRole.user_id == user_id,
                    User.tenant_id == tenant_id,
                )
            )

            result = await session.execute(
                query
            )

            return result.scalar_one()

    # =========================
    # Remove One Role From User
    # =========================
    async def remove_role_from_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        role_id: UUID,
    ) -> bool:

        try:
            async with self.db_client() as session:

                assignment_query = (
                    select(UserRole)
                    .join(
                        User,
                        User.user_id
                        == UserRole.user_id,
                    )
                    .join(
                        Role,
                        Role.role_id
                        == UserRole.role_id,
                    )
                    .where(
                        UserRole.user_id == user_id,
                        UserRole.role_id == role_id,
                        User.tenant_id == tenant_id,
                        Role.tenant_id == tenant_id,
                    )
                )

                assignment_result = (
                    await session.execute(
                        assignment_query
                    )
                )

                assignment = (
                    assignment_result
                    .scalar_one_or_none()
                )

                if assignment is None:
                    return False

                await session.delete(
                    assignment
                )

                await session.commit()

                return True

        except SQLAlchemyError:
            raise

    # =========================
    # Remove All User Roles
    # =========================
    async def remove_all_user_roles(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> int:

        try:
            async with self.db_client() as session:

                user_query = select(
                    User.user_id
                ).where(
                    User.user_id == user_id,
                    User.tenant_id == tenant_id,
                )

                user_result = await session.execute(
                    user_query
                )

                if user_result.scalar_one_or_none() is None:
                    return 0

                delete_query = delete(
                    UserRole
                ).where(
                    UserRole.user_id == user_id
                )

                result = await session.execute(
                    delete_query
                )

                await session.commit()

                return result.rowcount or 0

        except SQLAlchemyError:
            raise