from typing import Any
from uuid import UUID

from core.jwt_service import JWTService
from core.password_hasher import PasswordHasher
from helpers.config import get_settings
from models.TenantModel import TenantModel
from models.UserModel import UserModel
from schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    TokenResponse,
)
from schemas.registration import TenantRegistrationRequest
from schemas.role import RoleResponse
from schemas.tenant import TenantResponse
from schemas.user import UserResponse
from services.registration import RegistrationService


class AuthController:
    def __init__(
        self,
        db_client: object,
        password_hasher: PasswordHasher,
        jwt_service: JWTService,
    ) -> None:
        self.db_client = db_client
        self.password_hasher = password_hasher
        self.jwt_service = jwt_service

        self.tenant_model = TenantModel(db_client=db_client)
        self.user_model = UserModel(db_client=db_client)
        self.registration_service = RegistrationService(
            db_client=db_client,
            password_hasher=password_hasher,
        )

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "AuthController":
        settings = get_settings()

        return cls(
            db_client=db_client,
            password_hasher=PasswordHasher(),
            jwt_service=JWTService(
                secret_key=settings.JWT_SECRET_KEY,
                algorithm=settings.JWT_ALGORITHM,
                access_token_expire_minutes=(
                    settings.ACCESS_TOKEN_EXPIRE_MINUTES
                ),
                refresh_token_expire_days=(
                    settings.REFRESH_TOKEN_EXPIRE_DAYS
                ),
            ),
        )

    async def register_tenant(
        self,
        registration_data: TenantRegistrationRequest,
    ) -> TokenResponse:
        result = await self.registration_service.register_tenant(
            registration_data=registration_data
        )

        token_pair = self.jwt_service.create_token_pair(
            user_id=result.user.user_id,
            tenant_id=result.tenant.tenant_id,
            is_tenant_admin=True,
            roles=self._role_names(result.roles),
        )

        return TokenResponse.model_validate(token_pair)

    async def login(
        self,
        login_data: LoginRequest,
    ) -> TokenResponse:
        user = (
            await self.user_model.get_user_by_tenant_code_and_email(
                tenant_code=login_data.tenant_code,
                user_email=str(login_data.email),
                include_roles=True,
            )
        )

        if user is None or user.user_status != "active":
            raise ValueError("invalid credentials")

        if not self.password_hasher.verify_password(
            plain_password=login_data.password,
            password_hash=user.password_hash,
        ):
            raise ValueError("invalid credentials")

        if not await self.tenant_model.tenant_is_active(
            tenant_id=user.tenant_id
        ):
            raise ValueError("invalid credentials")

        token_pair = self.jwt_service.create_token_pair(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            is_tenant_admin=user.is_tenant_admin,
            roles=self._role_names(user.roles),
        )

        await self.user_model.update_last_login(
            tenant_id=user.tenant_id,
            user_id=user.user_id,
        )

        return TokenResponse.model_validate(token_pair)

    async def refresh_tokens(
        self,
        refresh_token: str,
    ) -> TokenResponse:
        payload = self.jwt_service.decode_refresh_token(
            refresh_token
        )

        user = await self.user_model.get_user_by_id(
            tenant_id=payload["tenant_id"],
            user_id=payload["sub"],
            include_roles=True,
        )

        if user is None or user.user_status != "active":
            raise ValueError("user is not active")

        if not await self.tenant_model.tenant_is_active(
            tenant_id=user.tenant_id
        ):
            raise ValueError("tenant is not active")

        token_pair = self.jwt_service.create_token_pair(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            is_tenant_admin=user.is_tenant_admin,
            roles=self._role_names(user.roles),
        )

        return TokenResponse.model_validate(token_pair)

    async def get_current_user(
        self,
        access_token: str,
    ) -> CurrentUserResponse:
        payload = self.jwt_service.decode_access_token(
            access_token
        )

        return await self.get_current_user_from_ids(
            tenant_id=payload["tenant_id"],
            user_id=payload["sub"],
        )

    async def get_current_user_from_ids(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> CurrentUserResponse:
        user = await self.user_model.get_user_by_id(
            tenant_id=tenant_id,
            user_id=user_id,
            include_roles=True,
        )

        if user is None or user.user_status != "active":
            raise ValueError("user is not active")

        tenant = await self.tenant_model.get_tenant_by_id(
            tenant_id=tenant_id
        )

        if tenant is None or tenant.tenant_status != "active":
            raise ValueError("tenant is not active")

        return CurrentUserResponse(
            user=UserResponse.model_validate(user),
            tenant=TenantResponse.model_validate(tenant),
            roles=[
                RoleResponse.model_validate(role)
                for role in list(user.roles or [])
            ],
        )

    def decode_access_token(
        self,
        access_token: str,
    ) -> dict[str, Any]:
        return self.jwt_service.decode_access_token(
            access_token
        )

    @staticmethod
    def _role_names(roles: Any) -> list[str]:
        if not roles:
            return []

        return sorted(
            {
                role.role_name
                for role in roles
                if role.role_name
            }
        )
