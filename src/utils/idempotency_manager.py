import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models.db_schemes.rag_db.schemes.celery_task_execution import (
    CeleryTaskExecution,
)


logger = logging.getLogger(__name__)

FINAL_TASK_STATUSES = {
    "SUCCESS",
    "FAILURE",
    "REVOKED",
}
RUNNING_TASK_STATUSES = {
    "PENDING",
    "STARTED",
    "RETRY",
}
ALL_TASK_STATUSES = FINAL_TASK_STATUSES | RUNNING_TASK_STATUSES
MAX_ERROR_MESSAGE_LENGTH = 4000


class IdempotencyManager:
    """Create, find, and update idempotent Celery execution records."""

    def __init__(
        self,
        db_client: object,
        db_engine: object | None = None,
    ) -> None:
        if db_client is None:
            raise ValueError("db_client is required")
        self.db_client = db_client
        self.db_engine = db_engine

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def normalize_task_name(task_name: str) -> str:
        normalized_name = str(task_name or "").strip()
        if not normalized_name:
            raise ValueError("task_name cannot be empty")
        if len(normalized_name) > 255:
            raise ValueError("task_name cannot exceed 255 characters")
        return normalized_name

    @staticmethod
    def normalize_task_id(
        celery_task_id: str | UUID | None,
    ) -> UUID | None:
        if celery_task_id is None:
            return None
        if isinstance(celery_task_id, UUID):
            return celery_task_id
        try:
            return UUID(str(celery_task_id).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid celery_task_id") from exc

    @staticmethod
    def normalize_task_args(
        task_args: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(task_args, dict):
            raise ValueError("task_args must be a dictionary")
        return json.loads(
            json.dumps(
                task_args,
                sort_keys=True,
                default=str,
                ensure_ascii=False,
            )
        )

    @classmethod
    def create_args_hash(
        cls,
        task_name: str,
        task_args: dict[str, Any],
    ) -> str:
        normalized_name = cls.normalize_task_name(task_name)
        normalized_args = cls.normalize_task_args(task_args)
        combined_data = {
            "task_name": normalized_name,
            "task_args": normalized_args,
        }
        json_string = json.dumps(
            combined_data,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(
            json_string.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _safe_error_message(error_message: str | None) -> str | None:
        if error_message is None:
            return None
        clean_message = str(error_message).strip()
        if not clean_message:
            return None
        return clean_message[:MAX_ERROR_MESSAGE_LENGTH]

    @staticmethod
    def _task_belongs_to_tenant(
        task_record: CeleryTaskExecution,
        tenant_id: str | UUID | None,
    ) -> bool:
        if tenant_id is None:
            return True
        task_tenant_id = (task_record.task_args or {}).get("tenant_id")
        return str(task_tenant_id) == str(tenant_id)

    async def get_existing_task(
        self,
        task_name: str,
        task_args: dict[str, Any],
    ) -> CeleryTaskExecution | None:
        normalized_name = self.normalize_task_name(task_name)
        args_hash = self.create_args_hash(
            task_name=normalized_name,
            task_args=task_args,
        )
        async with self.db_client() as session:
            statement = select(CeleryTaskExecution).where(
                CeleryTaskExecution.task_name == normalized_name,
                CeleryTaskExecution.task_args_hash == args_hash,
            )
            result = await session.execute(statement)
            return result.scalar_one_or_none()

    async def get_task_by_execution_id(
        self,
        execution_id: int,
        tenant_id: str | UUID | None = None,
    ) -> CeleryTaskExecution | None:
        if execution_id <= 0:
            return None
        async with self.db_client() as session:
            task_record = await session.get(
                CeleryTaskExecution,
                execution_id,
            )
            if task_record is None:
                return None
            if not self._task_belongs_to_tenant(
                task_record,
                tenant_id,
            ):
                return None
            return task_record

    async def get_task_by_celery_id(
        self,
        celery_task_id: str | UUID,
        tenant_id: str | UUID | None = None,
    ) -> CeleryTaskExecution | None:
        normalized_task_id = self.normalize_task_id(celery_task_id)
        async with self.db_client() as session:
            statement = select(CeleryTaskExecution).where(
                CeleryTaskExecution.celery_task_id
                == normalized_task_id
            )
            result = await session.execute(statement)
            task_record = result.scalar_one_or_none()
            if task_record is None:
                return None
            if not self._task_belongs_to_tenant(
                task_record,
                tenant_id,
            ):
                return None
            return task_record

    async def create_task_record(
        self,
        task_name: str,
        task_args: dict[str, Any],
        celery_task_id: str | UUID | None = None,
    ) -> CeleryTaskExecution:
        normalized_name = self.normalize_task_name(task_name)
        normalized_args = self.normalize_task_args(task_args)
        args_hash = self.create_args_hash(
            task_name=normalized_name,
            task_args=normalized_args,
        )
        normalized_task_id = self.normalize_task_id(celery_task_id)
        task_record = CeleryTaskExecution(
            task_name=normalized_name,
            task_args_hash=args_hash,
            task_args=normalized_args,
            celery_task_id=normalized_task_id,
            status="PENDING",
        )

        async with self.db_client() as session:
            try:
                session.add(task_record)
                await session.commit()
                await session.refresh(task_record)
                logger.info(
                    "Idempotency record created. execution_id=%s "
                    "task_name=%s task_id=%s",
                    task_record.execution_id,
                    normalized_name,
                    normalized_task_id,
                )
                return task_record
            except IntegrityError:
                await session.rollback()
                statement = select(CeleryTaskExecution).where(
                    CeleryTaskExecution.task_name == normalized_name,
                    CeleryTaskExecution.task_args_hash == args_hash,
                )
                result = await session.execute(statement)
                existing_record = result.scalar_one()
                logger.info(
                    "Existing idempotency record reused. "
                    "execution_id=%s status=%s",
                    existing_record.execution_id,
                    existing_record.status,
                )
                return existing_record
            except SQLAlchemyError:
                await session.rollback()
                logger.exception(
                    "Failed to create idempotency record. task_name=%s",
                    normalized_name,
                )
                raise

    async def mark_started(
        self,
        execution_id: int,
        celery_task_id: str | UUID | None = None,
    ) -> CeleryTaskExecution | None:
        normalized_task_id = self.normalize_task_id(celery_task_id)
        async with self.db_client() as session:
            task_record = await session.get(
                CeleryTaskExecution,
                execution_id,
            )
            if task_record is None:
                return None
            task_record.status = "STARTED"
            task_record.started_at = self.now()
            task_record.completed_at = None
            task_record.error_message = None
            task_record.result = None
            if normalized_task_id is not None:
                task_record.celery_task_id = normalized_task_id
            await session.commit()
            await session.refresh(task_record)
            return task_record

    async def mark_success(
        self,
        execution_id: int,
        result: dict[str, Any] | None = None,
    ) -> CeleryTaskExecution | None:
        return await self._mark_final_status(
            execution_id=execution_id,
            status="SUCCESS",
            result=result,
            error_message=None,
        )

    async def mark_failure(
        self,
        execution_id: int,
        error_message: str,
        result: dict[str, Any] | None = None,
    ) -> CeleryTaskExecution | None:
        return await self._mark_final_status(
            execution_id=execution_id,
            status="FAILURE",
            result=result,
            error_message=error_message,
        )

    async def mark_revoked(
        self,
        execution_id: int,
        error_message: str | None = None,
    ) -> CeleryTaskExecution | None:
        return await self._mark_final_status(
            execution_id=execution_id,
            status="REVOKED",
            result=None,
            error_message=error_message,
        )

    async def _mark_final_status(
        self,
        execution_id: int,
        status: str,
        result: dict[str, Any] | None,
        error_message: str | None,
    ) -> CeleryTaskExecution | None:
        if status not in FINAL_TASK_STATUSES:
            raise ValueError("invalid final task status")
        async with self.db_client() as session:
            task_record = await session.get(
                CeleryTaskExecution,
                execution_id,
            )
            if task_record is None:
                return None
            task_record.status = status
            task_record.result = result
            task_record.error_message = self._safe_error_message(
                error_message
            )
            task_record.completed_at = self.now()
            await session.commit()
            await session.refresh(task_record)
            return task_record

    async def mark_retry(
        self,
        execution_id: int,
        error_message: str | None = None,
    ) -> CeleryTaskExecution | None:
        async with self.db_client() as session:
            task_record = await session.get(
                CeleryTaskExecution,
                execution_id,
            )
            if task_record is None:
                return None
            task_record.status = "RETRY"
            task_record.error_message = self._safe_error_message(
                error_message
            )
            task_record.completed_at = None
            await session.commit()
            await session.refresh(task_record)
            return task_record

    async def should_execute_task(
        self,
        task_name: str,
        task_args: dict[str, Any],
        task_time_limit: int = 600,
        grace_period: int = 60,
    ) -> tuple[bool, CeleryTaskExecution | None]:
        safe_time_limit = max(int(task_time_limit), 1)
        safe_grace_period = max(int(grace_period), 0)
        existing_task = await self.get_existing_task(
            task_name=task_name,
            task_args=task_args,
        )
        if existing_task is None:
            return True, None
        if existing_task.status == "SUCCESS":
            return False, existing_task
        if existing_task.status in RUNNING_TASK_STATUSES:
            reference_time = (
                existing_task.started_at
                or existing_task.created_at
            )
            if reference_time is None:
                logger.warning(
                    "Running task has no reference timestamp. "
                    "execution_id=%s",
                    existing_task.execution_id,
                )
                return False, existing_task
            elapsed_seconds = (
                self.now() - reference_time
            ).total_seconds()
            stale_after = safe_time_limit + safe_grace_period
            if elapsed_seconds > stale_after:
                logger.warning(
                    "Stale task will be executed again. "
                    "execution_id=%s status=%s elapsed=%s",
                    existing_task.execution_id,
                    existing_task.status,
                    int(elapsed_seconds),
                )
                return True, existing_task
            return False, existing_task
        if existing_task.status in {"FAILURE", "REVOKED"}:
            return True, existing_task
        logger.warning(
            "Unknown task status will be treated as retryable. "
            "execution_id=%s status=%s",
            existing_task.execution_id,
            existing_task.status,
        )
        return True, existing_task

    async def cleanup_old_tasks(
        self,
        time_retention: int = 86400,
    ) -> int:
        safe_retention = max(int(time_retention), 0)
        cutoff_time = self.now() - timedelta(
            seconds=safe_retention
        )
        async with self.db_client() as session:
            try:
                statement = delete(CeleryTaskExecution).where(
                    CeleryTaskExecution.created_at < cutoff_time,
                    CeleryTaskExecution.status.in_(
                        FINAL_TASK_STATUSES
                    ),
                )
                result = await session.execute(statement)
                await session.commit()
                deleted_count = result.rowcount or 0
                logger.info(
                    "Old task records cleaned. count=%s cutoff=%s",
                    deleted_count,
                    cutoff_time.isoformat(),
                )
                return deleted_count
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Failed to clean old task records")
                raise
