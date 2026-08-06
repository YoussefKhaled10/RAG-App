from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)

from dependencies.auth import require_tenant_admin
from models.RoleModel import RoleModel
from models.db_schemes import Role
from schemas.auth import CurrentUserResponse
from schemas.role import (
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
)


roles_router = APIRouter(
    prefix="/api/v1/roles",
    tags=["roles"],
)


async def _get_role_model(
    request: Request,
) -> RoleModel:
    return await RoleModel.create_instance(
        db_client=request.app.db_client,
    )


def _to_role_response(
    role: Role,
) -> RoleResponse:
    return RoleResponse.model_validate(role)


@roles_router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role(
    request: Request,
    role_data: RoleCreate,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> RoleResponse:
    tenant_id = current_user.user.tenant_id
    role_model = await _get_role_model(request)

    existing_role = await role_model.get_role_by_name(
        tenant_id=tenant_id,
        role_name=role_data.role_name,
    )

    if existing_role is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "a role with this name already exists "
                "inside the tenant"
            ),
        )

    role_record = Role(
        tenant_id=tenant_id,
        role_name=role_data.role_name,
        role_description=role_data.role_description,
        is_system_role=False,
    )

    try:
        created_role = await role_model.create_role(
            role=role_record,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _to_role_response(created_role)


@roles_router.get(
    "",
    response_model=RoleListResponse,
)
async def list_roles(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    include_users: bool = Query(default=False),
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> RoleListResponse:
    tenant_id = current_user.user.tenant_id
    role_model = await _get_role_model(request)

    roles, total_roles, total_pages = (
        await role_model.get_tenant_roles(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            include_users=include_users,
        )
    )

    return RoleListResponse(
        items=[
            _to_role_response(role)
            for role in roles
        ],
        total=total_roles,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@roles_router.get(
    "/{role_id}",
    response_model=RoleResponse,
)
async def get_role(
    request: Request,
    role_id: UUID,
    include_users: bool = Query(default=False),
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> RoleResponse:
    tenant_id = current_user.user.tenant_id
    role_model = await _get_role_model(request)

    role = await role_model.get_role_by_id(
        tenant_id=tenant_id,
        role_id=role_id,
        include_users=include_users,
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="role not found",
        )

    return _to_role_response(role)


@roles_router.patch(
    "/{role_id}",
    response_model=RoleResponse,
)
async def update_role(
    request: Request,
    role_id: UUID,
    role_data: RoleUpdate,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> RoleResponse:
    tenant_id = current_user.user.tenant_id
    role_model = await _get_role_model(request)

    update_data = role_data.model_dump(
        exclude_unset=True,
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="at least one field must be provided",
        )

    existing_role = await role_model.get_role_by_id(
        tenant_id=tenant_id,
        role_id=role_id,
    )

    if existing_role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="role not found",
        )

    if existing_role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="system roles cannot be modified",
        )

    new_role_name = update_data.get("role_name")

    if (
        new_role_name is not None
        and new_role_name != existing_role.role_name
    ):
        role_with_same_name = (
            await role_model.get_role_by_name(
                tenant_id=tenant_id,
                role_name=new_role_name,
            )
        )

        if role_with_same_name is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "a role with this name already exists "
                    "inside the tenant"
                ),
            )

    try:
        updated_role = await role_model.update_role(
            tenant_id=tenant_id,
            role_id=role_id,
            role_name=new_role_name,
            role_description=update_data.get(
                "role_description"
            ),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if updated_role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="role not found",
        )

    return _to_role_response(updated_role)


@roles_router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_role(
    request: Request,
    role_id: UUID,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> None:
    tenant_id = current_user.user.tenant_id
    role_model = await _get_role_model(request)

    try:
        deleted = await role_model.delete_role(
            tenant_id=tenant_id,
            role_id=role_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="role not found",
        )
