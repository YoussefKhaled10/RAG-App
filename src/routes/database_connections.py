from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from controllers.DatabaseConnectionController import DatabaseConnectionController
from controllers.DatabasePermissionController import (
    DatabasePermissionController,
    DatabasePermissionDenied,
)
from dependencies.auth import get_current_user, require_tenant_admin
from models.DatabaseConnectionModel import DatabaseConnectionModel
from schemas.auth import CurrentUserResponse
from schemas.database_connection import (
    DatabaseConnectionCreate,
    DatabaseConnectionListResponse,
    DatabaseConnectionResponse,
    DatabaseSchemaCacheResponse,
    DatabaseSchemaDiscoveryResponse,
    DatabaseSchemaSyncResponse,
    DatabaseConnectionTestResponse,
    DatabaseConnectionUpdate,
)
from schemas.database_permission import (
    DatabasePermissionCatalogResponse,
    DatabaseRolePermissionUpsert,
    PermissionFilteredDatabaseSchemaResponse,
    SecureDatabaseQueryRequest,
    SecureDatabaseQueryResponse,
)
from stores.databases.BaseDatabaseAdapter import DatabaseAdapterError

router = APIRouter(prefix="/api/v1/database-connections", tags=["database connections"])
database_connections_router = router

async def _controller(request: Request):
    return await DatabaseConnectionController.create_instance(
        db_client=request.app.db_client,
        encryption_service=request.app.credentials_encryption_service,
    )

async def _model(request: Request):
    return await DatabaseConnectionModel.create_instance(db_client=request.app.db_client)

async def _permission_controller(request: Request):
    return await DatabasePermissionController.create_instance(
        db_client=request.app.db_client,
        encryption_service=request.app.credentials_encryption_service,
    )

@router.post("", response_model=DatabaseConnectionResponse, status_code=201)
async def create_database_connection(request: Request, payload: DatabaseConnectionCreate, current_user: CurrentUserResponse = Depends(require_tenant_admin)):
    controller = await _controller(request)
    try:
        return await controller.create_connection(current_user.user.tenant_id, current_user.user.user_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.get("", response_model=DatabaseConnectionListResponse)
async def list_database_connections(request: Request, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100), include_disabled: bool = False, current_user: CurrentUserResponse = Depends(get_current_user)):
    model = await _model(request)
    records, total, total_pages = await model.get_tenant_connections(current_user.user.tenant_id, page, page_size, include_disabled)
    return DatabaseConnectionListResponse(items=[DatabaseConnectionController.to_response(x) for x in records], total=total, page=page, page_size=page_size, total_pages=total_pages)

@router.post("/{connection_id}/test", response_model=DatabaseConnectionTestResponse)
async def test_database_connection(request: Request, connection_id: int, current_user: CurrentUserResponse = Depends(require_tenant_admin)):
    controller = await _controller(request)
    try:
        result = await controller.test_connection(current_user.user.tenant_id, connection_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="database connection not found")
    return result

@router.post(
    "/{connection_id}/discover-schema",
    response_model=DatabaseSchemaDiscoveryResponse,
)
async def discover_database_schema(
    request: Request,
    connection_id: int,
    current_user: CurrentUserResponse = Depends(require_tenant_admin),
):
    controller = await _controller(request)
    try:
        result = await controller.discover_schema(
            current_user.user.tenant_id,
            connection_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatabaseAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": exc.error_code,
                "message": str(exc),
            },
        ) from exc
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="database connection not found",
        )
    return result


@router.post(
    "/{connection_id}/sync-schema",
    response_model=DatabaseSchemaSyncResponse,
)
async def sync_database_schema(
    request: Request,
    connection_id: int,
    current_user: CurrentUserResponse = Depends(require_tenant_admin),
):
    controller = await _controller(request)
    try:
        result = await controller.sync_schema(
            current_user.user.tenant_id,
            connection_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatabaseAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": exc.error_code,
                "message": str(exc),
            },
        ) from exc
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="database connection not found",
        )
    return result


@router.get(
    "/{connection_id}/schema",
    response_model=DatabaseSchemaCacheResponse,
)
async def get_cached_database_schema(
    request: Request,
    connection_id: int,
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    controller = await _controller(request)
    result = await controller.get_cached_schema(
        current_user.user.tenant_id,
        connection_id,
    )
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="schema metadata cache not found; sync the schema first",
        )
    return result


@router.get(
    "/{connection_id}/permissions",
    response_model=DatabasePermissionCatalogResponse,
)
async def list_database_permissions(
    request: Request,
    connection_id: int,
    current_user: CurrentUserResponse = Depends(require_tenant_admin),
):
    controller = await _permission_controller(request)
    try:
        return await controller.list_connection_policies(
            tenant_id=current_user.user.tenant_id,
            connection_id=connection_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/{connection_id}/permissions/roles/{role_id}",
    response_model=DatabasePermissionCatalogResponse,
)
async def replace_database_role_permissions(
    request: Request,
    connection_id: int,
    role_id: UUID,
    payload: DatabaseRolePermissionUpsert,
    current_user: CurrentUserResponse = Depends(require_tenant_admin),
):
    controller = await _permission_controller(request)
    try:
        return await controller.replace_role_policy(
            tenant_id=current_user.user.tenant_id,
            connection_id=connection_id,
            role_id=role_id,
            payload=payload,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/{connection_id}/permissions/roles/{role_id}",
    status_code=204,
)
async def delete_database_role_permissions(
    request: Request,
    connection_id: int,
    role_id: UUID,
    current_user: CurrentUserResponse = Depends(require_tenant_admin),
) -> None:
    controller = await _permission_controller(request)
    try:
        await controller.delete_role_policy(
            tenant_id=current_user.user.tenant_id,
            connection_id=connection_id,
            role_id=role_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{connection_id}/schema/filtered",
    response_model=PermissionFilteredDatabaseSchemaResponse,
)
async def get_permission_filtered_database_schema(
    request: Request,
    connection_id: int,
    role_id: UUID | None = Query(default=None),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    if role_id is not None and not current_user.user.is_tenant_admin:
        raise HTTPException(
            status_code=403,
            detail="only tenant administrators can preview another role",
        )

    controller = await _permission_controller(request)
    role_ids = (
        [role_id]
        if role_id is not None
        else [role.role_id for role in current_user.roles]
    )
    try:
        return await controller.get_filtered_schema(
            tenant_id=current_user.user.tenant_id,
            connection_id=connection_id,
            user_id=(None if role_id is not None else current_user.user.user_id),
            role_ids=role_ids,
            tenant_admin_bypass=(
                bool(current_user.user.is_tenant_admin)
                and role_id is None
            ),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{connection_id}/query",
    response_model=SecureDatabaseQueryResponse,
)
async def execute_permission_checked_database_query(
    request: Request,
    connection_id: int,
    payload: SecureDatabaseQueryRequest,
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    controller = await _permission_controller(request)
    try:
        return await controller.execute_secure_query(
            tenant_id=current_user.user.tenant_id,
            user_id=current_user.user.user_id,
            user_email=current_user.user.user_email,
            role_ids=[role.role_id for role in current_user.roles],
            tenant_admin_bypass=bool(current_user.user.is_tenant_admin),
            connection_id=connection_id,
            payload=payload,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DatabasePermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatabaseAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.error_code, "message": str(exc)},
        ) from exc

@router.get("/{connection_id}", response_model=DatabaseConnectionResponse)
async def get_database_connection(request: Request, connection_id: int, current_user: CurrentUserResponse = Depends(get_current_user)):
    model = await _model(request)
    record = await model.get_connection_by_id(current_user.user.tenant_id, connection_id)
    if record is None:
        raise HTTPException(status_code=404, detail="database connection not found")
    return DatabaseConnectionController.to_response(record)

@router.patch("/{connection_id}", response_model=DatabaseConnectionResponse)
async def update_database_connection(request: Request, connection_id: int, payload: DatabaseConnectionUpdate, current_user: CurrentUserResponse = Depends(require_tenant_admin)):
    controller = await _controller(request)
    try:
        updated = await controller.update_connection(current_user.user.tenant_id, connection_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="database connection not found")
    return updated

@router.delete("/{connection_id}", status_code=204)
async def delete_database_connection(request: Request, connection_id: int, current_user: CurrentUserResponse = Depends(require_tenant_admin)) -> None:
    model = await _model(request)
    deleted = await model.delete_connection(current_user.user.tenant_id, connection_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="database connection not found")
