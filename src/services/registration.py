from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from core.password_hasher import PasswordHasher
from models.db_schemes import Role, Tenant, User, UserRole
from models.enums.RoleEnum import ROLE_DESCRIPTIONS, RoleName
from schemas.registration import TenantRegistrationRequest


class RegistrationConflictError(ValueError):
    pass

@dataclass
class RegistrationResult:
    tenant: Tenant
    user: User
    roles: list[Role]


DEFAULT_SYSTEM_ROLES = tuple(
    (
        role_name.value,
        ROLE_DESCRIPTIONS[role_name],
    )
    for role_name in RoleName
)


class RegistrationService:
    def __init__(
        self,
        db_client: object,
        password_hasher: PasswordHasher,
    ) -> None:
        self.db_client = db_client
        self.password_hasher = password_hasher

    async def register_tenant(
        self,
        registration_data: TenantRegistrationRequest,
    ) -> RegistrationResult:
        try:
            async with self.db_client() as session:
                async with session.begin():
                    tenant_query = select(Tenant.tenant_id).where(
                        Tenant.tenant_code
                        == registration_data.tenant_code
                    )
                    tenant_result = await session.execute(
                        tenant_query
                    )
                    if tenant_result.scalar_one_or_none() is not None:
                        raise RegistrationConflictError(
                            "tenant code already exists"
                        )
                    tenant = Tenant(
                        tenant_name=registration_data.tenant_name,
                        tenant_code=registration_data.tenant_code,
                        tenant_status="active",
                        tenant_settings={},
                    )
                    session.add(tenant)
                    await session.flush()
                    password_hash = (
                        self.password_hasher.hash_password(
                            registration_data.password
                        )
                    )
                    admin_user = User(
                        tenant_id=tenant.tenant_id,
                        user_email=str(
                            registration_data.admin_email
                        ),
                        user_full_name=(
                            registration_data.admin_full_name
                        ),
                        password_hash=password_hash,
                        user_status="active",
                        is_tenant_admin=True,
                    )
                    session.add(admin_user)
                    await session.flush()
                    roles: list[Role] = []
                    tenant_admin_role: Role | None = None
                    for role_name, role_description in (
                        DEFAULT_SYSTEM_ROLES
                    ):
                        role = Role(
                            tenant_id=tenant.tenant_id,
                            role_name=role_name,
                            role_description=role_description,
                            is_system_role=True,
                        )
                        session.add(role)
                        roles.append(role)
                        if (
                            role_name
                            == RoleName.TENANT_ADMIN.value
                        ):
                            tenant_admin_role = role
                    await session.flush()
                    if tenant_admin_role is None:
                        raise RuntimeError(
                            "tenant admin role was not created"
                        )
                    assignment = UserRole(
                        user_id=admin_user.user_id,
                        role_id=tenant_admin_role.role_id,
                    )
                    session.add(assignment)
                await session.refresh(tenant)
                await session.refresh(admin_user)
                return RegistrationResult(
                    tenant=tenant,
                    user=admin_user,
                    roles=[tenant_admin_role],
                )
        except RegistrationConflictError:
            raise
        except IntegrityError as exc:
            raise RegistrationConflictError(
                "tenant code or administrator email already exists"
            ) from exc
        except SQLAlchemyError:
            raise
