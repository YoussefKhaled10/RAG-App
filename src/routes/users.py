from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)

from core.password_hasher import PasswordHasher
from dependencies.auth import require_tenant_admin
from models.UserModel import UserModel
from models.db_schemes import User
from schemas.auth import CurrentUserResponse
from schemas.user import (
    UserCreate,
    UserListResponse,
    UserPasswordUpdate,
    UserResponse,
    UserUpdate,
)


users_router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
)


async def _get_user_model(
    request: Request,
) -> UserModel:
    return await UserModel.create_instance(
        db_client=request.app.db_client,
    )


def _to_user_response(
    user: User,
) -> UserResponse:
    return UserResponse.model_validate(user)


@users_router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    request: Request,
    user_data: UserCreate,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> UserResponse:
    tenant_id = current_user.user.tenant_id
    user_model = await _get_user_model(request)

    existing_user = await user_model.get_user_by_email(
        tenant_id=tenant_id,
        user_email=str(user_data.user_email),
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "a user with this email already exists "
                "inside the tenant"
            ),
        )

    password_hash = PasswordHasher().hash_password(
        user_data.password
    )

    user_record = User(
        tenant_id=tenant_id,
        user_email=str(user_data.user_email),
        user_full_name=user_data.user_full_name,
        password_hash=password_hash,
        user_status=user_data.user_status,
        is_tenant_admin=user_data.is_tenant_admin,
    )

    try:
        created_user = await user_model.create_user(
            user=user_record,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _to_user_response(created_user)


@users_router.get(
    "",
    response_model=UserListResponse,
)
async def list_users(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    include_roles: bool = Query(default=False),
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> UserListResponse:
    tenant_id = current_user.user.tenant_id
    user_model = await _get_user_model(request)

    users, total_users, total_pages = (
        await user_model.get_tenant_users(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            include_roles=include_roles,
        )
    )

    return UserListResponse(
        items=[
            _to_user_response(user)
            for user in users
        ],
        total=total_users,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@users_router.get(
    "/{user_id}",
    response_model=UserResponse,
)
async def get_user(
    request: Request,
    user_id: UUID,
    include_roles: bool = Query(default=False),
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> UserResponse:
    tenant_id = current_user.user.tenant_id
    user_model = await _get_user_model(request)

    user = await user_model.get_user_by_id(
        tenant_id=tenant_id,
        user_id=user_id,
        include_roles=include_roles,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )

    return _to_user_response(user)


@users_router.patch(
    "/{user_id}",
    response_model=UserResponse,
)
async def update_user(
    request: Request,
    user_id: UUID,
    user_data: UserUpdate,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> UserResponse:
    tenant_id = current_user.user.tenant_id
    current_user_id = current_user.user.user_id
    user_model = await _get_user_model(request)

    update_data = user_data.model_dump(
        exclude_unset=True,
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="at least one field must be provided",
        )

    if "user_email" in update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "email updates are not supported by this "
                "endpoint"
            ),
        )

    if user_id == current_user_id:
        requested_status = update_data.get("user_status")
        requested_admin_value = update_data.get(
            "is_tenant_admin"
        )

        if requested_status in {
            "inactive",
            "suspended",
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "an administrator cannot deactivate or "
                    "suspend the current account"
                ),
            )

        if requested_admin_value is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "an administrator cannot remove the "
                    "current account administrator status"
                ),
            )

    updated_user = await user_model.update_user(
        tenant_id=tenant_id,
        user_id=user_id,
        user_full_name=update_data.get(
            "user_full_name"
        ),
        user_status=update_data.get("user_status"),
        is_tenant_admin=update_data.get(
            "is_tenant_admin"
        ),
    )

    if updated_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )

    return _to_user_response(updated_user)


@users_router.patch(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def update_user_password(
    request: Request,
    user_id: UUID,
    password_data: UserPasswordUpdate,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> None:
    tenant_id = current_user.user.tenant_id
    user_model = await _get_user_model(request)

    user_exists = await user_model.user_exists(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )

    password_hash = PasswordHasher().hash_password(
        password_data.new_password
    )

    updated = await user_model.update_password(
        tenant_id=tenant_id,
        user_id=user_id,
        password_hash=password_hash,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )


@users_router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(
    request: Request,
    user_id: UUID,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> None:
    tenant_id = current_user.user.tenant_id
    current_user_id = current_user.user.user_id

    if user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "an administrator cannot delete the "
                "current account"
            ),
        )

    user_model = await _get_user_model(request)

    deleted = await user_model.delete_user(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )
