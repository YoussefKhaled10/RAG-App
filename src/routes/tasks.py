from uuid import UUID

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Request, status

from celery_app import celery_app
from dependencies.auth import get_current_user
from schemas.auth import CurrentUserResponse
from utils.idempotency_manager import IdempotencyManager


tasks_router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["api_v1", "tasks"],
)


@tasks_router.get("/{task_id}")
async def get_task_status(
    task_id: UUID,
    request: Request,
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    tenant_id = current_user.user.tenant_id

    idempotency_manager = IdempotencyManager(
        db_client=request.app.db_client
    )

    task_record = await idempotency_manager.get_task_by_celery_id(
        celery_task_id=task_id,
        tenant_id=tenant_id,
    )

    if task_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="task not found",
        )

    task_tenant_id = (task_record.task_args or {}).get(
        "tenant_id"
    )

    if task_tenant_id != str(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="task not found",
        )

    task_result = AsyncResult(
        str(task_id),
        app=celery_app,
    )

    response = {
        "task_id": str(task_id),
        "execution_id": task_record.execution_id,
        "status": task_record.status,
        "ready": task_result.ready(),
        "successful": (
            task_result.successful()
            if task_result.ready()
            else False
        ),
        "created_at": task_record.created_at,
        "started_at": task_record.started_at,
        "completed_at": task_record.completed_at,
    }

    if task_record.status == "SUCCESS":
        response["result"] = task_record.result

    elif task_record.status == "FAILURE":
        response["error"] = task_record.error_message
        response["result"] = task_record.result

    return response
