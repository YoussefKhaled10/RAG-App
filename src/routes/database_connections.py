from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from controllers.DatabaseConnectionController import DatabaseConnectionController
from dependencies.auth import get_current_user, require_tenant_admin
from models.DatabaseConnectionModel import DatabaseConnectionModel
from schemas.auth import CurrentUserResponse
from schemas.database_connection import (
    DatabaseConnectionCreate,
    DatabaseConnectionListResponse,
    DatabaseConnectionResponse,
    DatabaseConnectionTestResponse,
    DatabaseConnectionUpdate,
)

router = APIRouter(prefix="/api/v1/database-connections", tags=["database connections"])
database_connections_router = router

async def _controller(request: Request):
    return await DatabaseConnectionController.create_instance(
        db_client=request.app.db_client,
        encryption_service=request.app.credentials_encryption_service,
    )

async def _model(request: Request):
    return await DatabaseConnectionModel.create_instance(db_client=request.app.db_client)

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
