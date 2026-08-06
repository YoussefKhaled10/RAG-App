from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from dependencies.auth import require_tenant_admin
from models.RoleModel import RoleModel
from models.UserModel import UserModel
from models.UserRoleModel import UserRoleModel
from schemas.auth import CurrentUserResponse
from schemas.role import RoleResponse
from schemas.user_role import (
    UserRoleOperationResponse,
    UserRoleResponse,
    UserRolesBulkAssign,
    UserRolesResponse,
)


user_roles_router = APIRouter(
    prefix="/api/v1/users",
    tags=["user roles"],
)


async def _get_models(
    request: Request,
) -> tuple[UserModel, RoleModel, UserRoleModel]:
    user_model = await UserModel.create_instance(
        db_client=request.app.db_client,
    )
    role_model = await RoleModel.create_instance(
        db_client=request.app.db_client,
    )
    user_role_model = await UserRoleModel.create_instance(
        db_client=request.app.db_client,
    )
    return user_model, role_model, user_role_model


async def _validate_user_and_role(
    tenant_id: UUID,
    user_id: UUID,
    role_id: UUID,
    user_model: UserModel,
    role_model: RoleModel,
) -> None:
    user = await user_model.get_user_by_id(
        tenant_id=tenant_id,
        user_id=user_id,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )

    role = await role_model.get_role_by_id(
        tenant_id=tenant_id,
        role_id=role_id,
    )
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="role not found",
        )


@user_roles_router.post(
    "/{user_id}/roles/{role_id}",
    response_model=UserRoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_role_to_user(
    request: Request,
    user_id: UUID,
    role_id: UUID,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> UserRoleResponse:
    tenant_id = current_user.user.tenant_id
    user_model, role_model, user_role_model = (
        await _get_models(request)
    )

    await _validate_user_and_role(
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=role_id,
        user_model=user_model,
        role_model=role_model,
    )

    already_assigned = await user_role_model.user_has_role(
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=role_id,
    )
    if already_assigned:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="role is already assigned to user",
        )

    try:
        assignment = await user_role_model.assign_role_to_user(
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=role_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return UserRoleResponse.model_validate(assignment)


@user_roles_router.post(
    "/{user_id}/roles",
    response_model=UserRolesResponse,
)
async def assign_roles_to_user(
    request: Request,
    user_id: UUID,
    assignment_data: UserRolesBulkAssign,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> UserRolesResponse:
    tenant_id = current_user.user.tenant_id
    user_model, role_model, user_role_model = (
        await _get_models(request)
    )

    user = await user_model.get_user_by_id(
        tenant_id=tenant_id,
        user_id=user_id,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )

    for role_id in assignment_data.role_ids:
        role = await role_model.get_role_by_id(
            tenant_id=tenant_id,
            role_id=role_id,
        )
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"role not found: {role_id}",
            )

    try:
        await user_role_model.assign_roles_to_user(
            tenant_id=tenant_id,
            user_id=user_id,
            role_ids=assignment_data.role_ids,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    roles = await user_role_model.get_user_roles(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    return UserRolesResponse(
        user_id=user_id,
        roles=[
            RoleResponse.model_validate(role)
            for role in roles
        ],
        total=len(roles),
    )


@user_roles_router.get(
    "/{user_id}/roles",
    response_model=UserRolesResponse,
)
async def get_user_roles(
    request: Request,
    user_id: UUID,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> UserRolesResponse:
    tenant_id = current_user.user.tenant_id
    user_model, _, user_role_model = await _get_models(request)

    user = await user_model.get_user_by_id(
        tenant_id=tenant_id,
        user_id=user_id,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )

    roles = await user_role_model.get_user_roles(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    return UserRolesResponse(
        user_id=user_id,
        roles=[
            RoleResponse.model_validate(role)
            for role in roles
        ],
        total=len(roles),
    )


@user_roles_router.delete(
    "/{user_id}/roles/{role_id}",
    response_model=UserRoleOperationResponse,
)
async def remove_role_from_user(
    request: Request,
    user_id: UUID,
    role_id: UUID,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> UserRoleOperationResponse:
    tenant_id = current_user.user.tenant_id
    user_model, role_model, user_role_model = (
        await _get_models(request)
    )

    await _validate_user_and_role(
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=role_id,
        user_model=user_model,
        role_model=role_model,
    )

    role = await role_model.get_role_by_id(
        tenant_id=tenant_id,
        role_id=role_id,
    )
    user = await user_model.get_user_by_id(
        tenant_id=tenant_id,
        user_id=user_id,
    )

    if (
        role is not None
        and role.role_name == "Tenant Admin"
        and user is not None
        and user.is_tenant_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "remove tenant administrator status before "
                "removing the Tenant Admin role"
            ),
        )

    removed = await user_role_model.remove_role_from_user(
        tenant_id=tenant_id,
        user_id=user_id,
        role_id=role_id,
    )
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="role assignment not found",
        )

    return UserRoleOperationResponse(
        success=True,
        message="role removed from user successfully",
        user_id=user_id,
        role_id=role_id,
    )


@user_roles_router.delete(
    "/{user_id}/roles",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_all_user_roles(
    request: Request,
    user_id: UUID,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> None:
    tenant_id = current_user.user.tenant_id
    user_model, _, user_role_model = await _get_models(request)

    user = await user_model.get_user_by_id(
        tenant_id=tenant_id,
        user_id=user_id,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="user not found",
        )

    if user.is_tenant_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "remove tenant administrator status before "
                "removing all roles"
            ),
        )

    await user_role_model.remove_all_user_roles(
        tenant_id=tenant_id,
        user_id=user_id,
    )
