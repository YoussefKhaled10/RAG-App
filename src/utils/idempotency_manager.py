import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models.db_schemes.rag_db.schemes.celery_task_execution import (
    CeleryTaskExecution,
)


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
class IdempotencyManager:

    def __init__(self, db_client: object, db_engine: object | None = None):
        self.db_client = db_client
        self.db_engine = db_engine

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def normalize_task_id(
        celery_task_id: str | UUID | None,
    ) -> UUID | None:
        if celery_task_id is None:
            return None

        if isinstance(celery_task_id, UUID):
            return celery_task_id

        try:
            return UUID(celery_task_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid celery_task_id") from exc

    @staticmethod
    def create_args_hash(
        task_name: str,
        task_args: dict[str, Any],
    ) -> str:
        combined_data = {
            **task_args,
            "task_name": task_name,
        }

        json_string = json.dumps(
            combined_data,
            sort_keys=True,
            default=str,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            json_string.encode("utf-8")
        ).hexdigest()

    async def get_existing_task(
        self,
        task_name: str,
        task_args: dict[str, Any],
    ) -> CeleryTaskExecution | None:
        args_hash = self.create_args_hash(
            task_name=task_name,
            task_args=task_args,
        )

        async with self.db_client() as session:
            statement = select(CeleryTaskExecution).where(
                CeleryTaskExecution.task_name == task_name,
                CeleryTaskExecution.task_args_hash == args_hash,
            )

            result = await session.execute(statement)
            return result.scalar_one_or_none()

    async def get_task_by_execution_id(
        self,
        execution_id: int,
    ) -> CeleryTaskExecution | None:
        async with self.db_client() as session:
            return await session.get(
                CeleryTaskExecution,
                execution_id,
            )

    async def get_task_by_celery_id(
        self,
        celery_task_id: str | UUID,
    ) -> CeleryTaskExecution | None:
        normalized_task_id = self.normalize_task_id(
            celery_task_id
        )

        async with self.db_client() as session:
            statement = select(CeleryTaskExecution).where(
                CeleryTaskExecution.celery_task_id
                == normalized_task_id
            )

            result = await session.execute(statement)
            return result.scalar_one_or_none()

    async def create_task_record(
        self,
        task_name: str,
        task_args: dict[str, Any],
        celery_task_id: str | UUID | None = None,
    ) -> CeleryTaskExecution:
        args_hash = self.create_args_hash(
            task_name=task_name,
            task_args=task_args,
        )

        normalized_task_id = self.normalize_task_id(
            celery_task_id
        )

        task_record = CeleryTaskExecution(
            task_name=task_name,
            task_args_hash=args_hash,
            task_args=task_args,
            celery_task_id=normalized_task_id,
            status="PENDING",
        )

        async with self.db_client() as session:
            try:
                session.add(task_record)
                await session.commit()
                await session.refresh(task_record)
                return task_record

            except IntegrityError:
                await session.rollback()

                statement = select(CeleryTaskExecution).where(
                    CeleryTaskExecution.task_name == task_name,
                    CeleryTaskExecution.task_args_hash == args_hash,
                )

                result = await session.execute(statement)
                return result.scalar_one()

            except SQLAlchemyError:
                await session.rollback()
                raise

    async def mark_started(
        self,
        execution_id: int,
        celery_task_id: str | UUID | None = None,
    ) -> CeleryTaskExecution | None:
        normalized_task_id = self.normalize_task_id(
            celery_task_id
        )

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
        async with self.db_client() as session:
            task_record = await session.get(
                CeleryTaskExecution,
                execution_id,
            )

            if task_record is None:
                return None

            task_record.status = "SUCCESS"
            task_record.result = result
            task_record.error_message = None
            task_record.completed_at = self.now()

            await session.commit()
            await session.refresh(task_record)

            return task_record

    async def mark_failure(
        self,
        execution_id: int,
        error_message: str,
        result: dict[str, Any] | None = None,
    ) -> CeleryTaskExecution | None:
        async with self.db_client() as session:
            task_record = await session.get(
                CeleryTaskExecution,
                execution_id,
            )

            if task_record is None:
                return None

            task_record.status = "FAILURE"
            task_record.error_message = error_message
            task_record.result = result
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
            task_record.error_message = error_message
            task_record.completed_at = None

            await session.commit()
            await session.refresh(task_record)

            return task_record

    async def should_execute_task(
        self,
        task_name: str,
        task_args: dict[str, Any],
        task_time_limit: int = 600,
    ) -> tuple[bool, CeleryTaskExecution | None]:
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

            if reference_time is not None:
                elapsed_seconds = (
                    self.now() - reference_time
                ).total_seconds()

                grace_period = 60

                if elapsed_seconds > task_time_limit + grace_period:
                    return True, existing_task

            return False, existing_task

        if existing_task.status in {"FAILURE", "REVOKED"}:
            return True, existing_task

        return True, existing_task

    async def cleanup_old_tasks(
        self,
        time_retention: int = 86400,
    ) -> int:
        cutoff_time = self.now() - timedelta(
            seconds=max(time_retention, 0)
        )

        async with self.db_client() as session:
            statement = delete(CeleryTaskExecution).where(
                CeleryTaskExecution.created_at < cutoff_time,
                CeleryTaskExecution.status.in_(
                    FINAL_TASK_STATUSES
                ),
            )

            result = await session.execute(statement)
            await session.commit()

            return result.rowcount or 0
