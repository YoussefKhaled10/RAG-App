from collections.abc import Callable

from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from controllers.AuthController import AuthController
from schemas.auth import CurrentUserResponse


bearer_scheme = HTTPBearer(
    auto_error=False,
)


async def get_current_user(
    request: Request,
    credentials: (
        HTTPAuthorizationCredentials | None
    ) = Depends(bearer_scheme),
) -> CurrentUserResponse:

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "authentication credentials "
                "are required"
            ),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid authentication scheme",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    auth_controller = (
        await AuthController.create_instance(
            db_client=request.app.db_client,
        )
    )

    try:
        return await auth_controller.get_current_user(
            access_token=credentials.credentials,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "invalid or expired access token"
            ),
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from exc


async def require_tenant_admin(
    current_user: CurrentUserResponse = Depends(
        get_current_user
    ),
) -> CurrentUserResponse:

    if not current_user.user.is_tenant_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "tenant administrator "
                "permission is required"
            ),
        )

    return current_user


def require_role(
    required_role: str,
) -> Callable:

    normalized_required_role = (
        required_role.strip().lower()
    )

    if not normalized_required_role:
        raise ValueError(
            "required_role cannot be empty"
        )

    async def role_dependency(
        current_user: CurrentUserResponse = Depends(
            get_current_user
        ),
    ) -> CurrentUserResponse:

        if current_user.user.is_tenant_admin:
            return current_user

        user_role_names = {
            role.role_name.strip().lower()
            for role in current_user.roles
            if role.role_name
        }

        if (
            normalized_required_role
            not in user_role_names
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"required role: {required_role}"
                ),
            )

        return current_user

    return role_dependency