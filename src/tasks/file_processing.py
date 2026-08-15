import asyncio
import inspect
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from celery_app import celery_app
from controllers import NLPController, ProcessController
from helpers.config import get_settings
from models.AssetModel import AssetModel
from models.ChunkModel import ChunkModel
from models.ProjectModel import ProjectModel
from models.db_schemes import DataChunk
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.llm.templates.template_parser import TemplateParser
from stores.vectordb.VectorDBProviderFactory import (
    VectorDBProviderFactory,
)
from utils.idempotency_manager import IdempotencyManager

logger = logging.getLogger(__name__)


async def _maybe_await(value):
    if inspect.isawaitable(value):
        return await value

    return value


async def process_uploaded_file_async(
    tenant_id: str,
    project_id: int,
    asset_id: int,
    file_id: str,
    chunk_size: int = 500,
    overlap_size: int = 50,
    celery_task_id: str | None = None,
    run_id: str | None = None,
):
    settings = get_settings()
    tenant_uuid = UUID(tenant_id)

    task_name = "tasks.file_processing.process_uploaded_file"

    task_args = {
        "tenant_id": str(tenant_uuid),
        "project_id": project_id,
        "asset_id": asset_id,
        "file_id": file_id,
        "chunk_size": chunk_size,
        "overlap_size": overlap_size,
    }
    if run_id is not None:
        task_args["run_id"] = str(run_id)

    db_engine = create_async_engine(
        settings.POSTGRES_URL,
        echo=False,
        pool_pre_ping=True,
    )

    db_client = sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    idempotency_manager = IdempotencyManager(
        db_client=db_client,
        db_engine=db_engine,
    )

    task_record = None
    asset_model = None
    chunk_model = None
    nlp_controller = None
    project = None
    new_chunk_ids: list[int] = []
    stage = "initialization"

    try:
        logger.info(
            "File processing started. tenant_id=%s project_id=%s "
            "asset_id=%s file_id=%s task_id=%s",
            tenant_uuid,
            project_id,
            asset_id,
            file_id,
            celery_task_id,
        )
        stage = "idempotency_check"
        should_execute, existing_task = (
            await idempotency_manager.should_execute_task(
                task_name=task_name,
                task_args=task_args,
                task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
            )
        )

        if not should_execute:
            return {
                "status": "skipped",
                "reason": "task_already_running_or_completed",
                "existing_status": existing_task.status,
                "existing_result": existing_task.result,
                "execution_id": existing_task.execution_id,
            }

        stage = "task_record_creation"
        task_record = await idempotency_manager.create_task_record(
            task_name=task_name,
            task_args=task_args,
            celery_task_id=celery_task_id,
        )

        await idempotency_manager.mark_started(
            execution_id=task_record.execution_id,
            celery_task_id=celery_task_id,
        )

        stage = "provider_initialization"
        llm_provider_factory = LLMProviderFactory(settings)

        generation_client = llm_provider_factory.create(
            provider=settings.GENERATION_BACKEND
        )
        generation_client.set_generation_model(
            model_id=settings.GENERATION_MODEL_ID
        )

        embedding_client = llm_provider_factory.create(
            provider=settings.EMBEDDING_BACKEND
        )
        embedding_client.set_embedding_model(
            model_id=settings.EMBEDDING_MODEL_ID,
            embedding_size=settings.EMBEDDING_MODEL_SIZE,
        )

        vectordb_provider_factory = VectorDBProviderFactory(
            config=settings,
            db_client=db_client,
        )
        vectordb_client = vectordb_provider_factory.create(
            provider=settings.VECTOR_DB_BACKEND
        )

        template_parser = TemplateParser(
            language=settings.PRIMARY_LANG,
            default_language=settings.DEFAULT_LANG,
        )

        project_model = await ProjectModel.create_instance(
            db_client=db_client
        )
        chunk_model = await ChunkModel.create_instance(
            db_client=db_client
        )
        asset_model = await AssetModel.create_instance(
            db_client=db_client
        )

        stage = "resource_validation"
        project = await project_model.get_project_by_id(
            tenant_id=tenant_uuid,
            project_id=project_id,
        )

        if project is None:
            raise ValueError("project_not_found_for_tenant")

        asset = await asset_model.get_asset_by_id(
            tenant_id=tenant_uuid,
            asset_id=asset_id,
        )

        if asset is None:
            raise ValueError("asset_not_found_for_tenant")

        if asset.asset_project_id != project.project_id:
            raise ValueError("asset_does_not_belong_to_project")

        # Parse and chunk first. If the file is invalid, the previous
        # successful index remains available.
        stage = "file_parsing"
        process_controller = ProcessController(
            tenant_id=tenant_uuid,
            project_id=project_id,
        )
        try:
            file_content = process_controller.get_file_content(
                file_id=file_id
            )
            file_content = await _maybe_await(file_content)
        except Exception as exc:
            raise RuntimeError(
                f"document_parsing_failed: {exc}"
            ) from exc
        if not file_content:
            raise RuntimeError(
                "document_parsing_failed: no readable content was extracted"
            )

        stage = "file_chunking"
        try:
            file_chunks = process_controller.process_file_content(
                file_content=file_content,
                file_id=file_id,
                chunk_size=chunk_size,
                overlap_size=overlap_size,
            )
            file_chunks = await _maybe_await(file_chunks)
        except Exception as exc:
            raise RuntimeError(
                f"document_chunking_failed: {exc}"
            ) from exc

        clean_file_chunks = [
            chunk
            for chunk in file_chunks
            if chunk.page_content and chunk.page_content.strip()
        ]
        if not clean_file_chunks:
            raise RuntimeError(
                "document_chunking_failed: all generated chunks are empty"
            )

        stage = "asset_status_processing"
        await asset_model.mark_asset_processing(
            tenant_id=tenant_uuid,
            asset_id=asset_id,
        )

        nlp_controller = NLPController(
            vectordb_client=vectordb_client,
            generation_client=generation_client,
            embedding_client=embedding_client,
            template_parser=template_parser,
        )

        stage = "old_index_cleanup"
        old_chunks = await chunk_model.get_chunks_by_asset_id(
            tenant_id=tenant_uuid,
            asset_id=asset_id,
        )
        old_chunk_ids = [
            chunk.chunk_id
            for chunk in old_chunks
            if chunk.chunk_id is not None
        ]
        if old_chunk_ids:
            vectors_deleted = await nlp_controller.delete_vectors_by_ids(
                project=project,
                record_ids=old_chunk_ids,
            )
            if not vectors_deleted:
                raise RuntimeError(
                    "old_index_cleanup_failed: vector deletion returned false"
                )
            await chunk_model.delete_chunks_by_asset_id(
                tenant_id=tenant_uuid,
                asset_id=asset_id,
            )

        file_chunk_records = [
            DataChunk(
                chunk_text=chunk.page_content.strip(),
                chunk_metadata=(
                    chunk.metadata
                    if chunk.metadata
                    else {}
                ),
                chunk_order=index + 1,
                chunk_project_id=project.project_id,
                chunk_asset_id=asset_id,
            )
            for index, chunk in enumerate(
                clean_file_chunks
            )
        ]

        stage = "chunk_database_insert"
        inserted_chunks = await chunk_model.insert_many_chunks(
            tenant_id=tenant_uuid,
            chunks=file_chunk_records,
        )

        chunk_ids = [
            chunk.chunk_id
            for chunk in file_chunk_records
            if chunk.chunk_id is not None
        ]

        if len(chunk_ids) != len(file_chunk_records):
            raise RuntimeError(
                "chunk_database_insert_failed: chunk IDs were not generated"
            )
        new_chunk_ids = list(chunk_ids)

        stage = "vector_indexing"
        index_batch_size = 5
        indexed_chunks = 0

        for index in range(
            0,
            len(file_chunk_records),
            index_batch_size,
        ):
            batch_chunks = file_chunk_records[
                index:
                index + index_batch_size
            ]
            batch_chunk_ids = chunk_ids[
                index:
                index + index_batch_size
            ]

            is_indexed = await nlp_controller.index_into_vector_db(
                project=project,
                chunks=batch_chunks,
                chunks_ids=batch_chunk_ids,
                do_reset=False,
            )

            if not is_indexed:
                batch_number = (
                    index // index_batch_size
                ) + 1
                raise RuntimeError(
                    "insert_into_vectordb_error_at_"
                    f"batch_{batch_number}"
                )

            indexed_chunks += len(batch_chunks)
            await asyncio.sleep(3)

        success_result = {
            "status": "completed",
            "tenant_id": str(tenant_uuid),
            "project_id": project_id,
            "asset_id": asset_id,
            "file_id": file_id,
            "inserted_chunks": inserted_chunks,
            "indexed_chunks": indexed_chunks,
        }

        stage = "success_finalization"
        await asset_model.mark_asset_indexed(
            tenant_id=tenant_uuid,
            asset_id=asset_id,
            indexed_chunks=indexed_chunks,
        )

        await idempotency_manager.mark_success(
            execution_id=task_record.execution_id,
            result=success_result,
        )

        logger.info(
            "File processing completed. tenant_id=%s project_id=%s "
            "asset_id=%s indexed_chunks=%s",
            tenant_uuid,
            project_id,
            asset_id,
            indexed_chunks,
        )
        return success_result

    except Exception as exc:
        logger.exception(
            "File processing failed. stage=%s tenant_id=%s "
            "project_id=%s asset_id=%s file_id=%s task_id=%s",
            stage,
            tenant_uuid,
            project_id,
            asset_id,
            file_id,
            celery_task_id,
        )

        # Remove only data created by this failed run. The source file is
        # intentionally kept so the user can reprocess it later.
        if new_chunk_ids and chunk_model is not None:
            logger.warning(
                "Cleaning partial processing data. asset_id=%s chunks=%s",
                asset_id,
                len(new_chunk_ids),
            )
            if nlp_controller is not None and project is not None:
                try:
                    await nlp_controller.delete_vectors_by_ids(
                        project=project,
                        record_ids=new_chunk_ids,
                    )
                except Exception:
                    logger.exception(
                        "Partial vector cleanup failed. asset_id=%s",
                        asset_id,
                    )
            try:
                await chunk_model.delete_chunks_by_asset_id(
                    tenant_id=tenant_uuid,
                    asset_id=asset_id,
                )
            except Exception:
                logger.exception(
                    "Partial chunk cleanup failed. asset_id=%s",
                    asset_id,
                )
        failure_result = {
            "status": "failed",
            "tenant_id": str(tenant_uuid),
            "stage": stage,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "project_id": project_id,
            "asset_id": asset_id,
            "file_id": file_id,
        }

        if asset_model is not None:
            try:
                await asset_model.mark_asset_failed(
                    tenant_id=tenant_uuid,
                    asset_id=asset_id,
                    error=str(exc),
                )
            except Exception:
                logger.exception(
                    "Failed to mark asset as failed. asset_id=%s",
                    asset_id,
                )

        if task_record is not None:
            try:
                await idempotency_manager.mark_failure(
                    execution_id=task_record.execution_id,
                    error_message=str(exc),
                    result=failure_result,
                )
            except Exception:
                logger.exception(
                    "Failed to mark task as failed. execution_id=%s",
                    task_record.execution_id,
                )

        raise RuntimeError(
            f"file_processing_failed_at_{stage}: {exc}"
        ) from exc

    finally:
        await db_engine.dispose()


@celery_app.task(
    name="tasks.file_processing.process_uploaded_file",
    bind=True,
)
def process_uploaded_file(
    self,
    tenant_id: str,
    project_id: int,
    asset_id: int,
    file_id: str,
    chunk_size: int = 500,
    overlap_size: int = 50,
    run_id: str | None = None,
):
    return asyncio.run(
        process_uploaded_file_async(
            tenant_id=tenant_id,
            project_id=project_id,
            asset_id=asset_id,
            file_id=file_id,
            chunk_size=chunk_size,
            overlap_size=overlap_size,
            celery_task_id=self.request.id,
            run_id=run_id,
        )
    )
