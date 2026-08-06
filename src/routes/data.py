import logging
import os
from pathlib import Path
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from controllers import DataController, NLPController, ProcessController
from dependencies.auth import get_current_user
from helpers.config import Settings, get_settings
from models import ResponseSignal
from models.AssetModel import AssetModel
from models.ChunkModel import ChunkModel
from models.ProjectModel import ProjectModel
from models.db_schemes import Asset, DataChunk
from models.enums.AssetTypeEnum import AssetTypeEnum
from schemas.auth import CurrentUserResponse
from .schemes.data import ProcessRequest
logger = logging.getLogger("uvicorn.error")
data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)


@data_router.post(
    "/upload/{project_id}",
    status_code=status.HTTP_201_CREATED,
)
async def upload_data(
    request: Request,
    project_id: int,
    file: UploadFile,
    current_user: CurrentUserResponse = Depends(get_current_user),
    app_settings: Settings = Depends(get_settings),
):
    tenant_id = current_user.user.tenant_id

    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    project = await project_model.get_project_by_id(
        tenant_id=tenant_id,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="project not found",
        )

    data_controller = DataController()
    is_valid, result_signal = data_controller.validate_uploaded_file(
        file=file
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result_signal,
        )

    original_file_name = file.filename or ""
    file_path, stored_file_name = (
        data_controller.generate_unique_filepath(
            original_file_name=original_file_name,
            tenant_id=tenant_id,
            project_id=project.project_id,
        )
    )

    try:
        async with aiofiles.open(file_path, "wb") as destination:
            while True:
                chunk = await file.read(
                    app_settings.FILE_DEFAULT_CHUNK_SIZE
                )

                if not chunk:
                    break

                await destination.write(chunk)

    except Exception as exc:
        Path(file_path).unlink(missing_ok=True)
        logger.exception("Error while uploading file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ResponseSignal.FILE_UPLOAD_FAILED.value,
        ) from exc

    finally:
        await file.close()

    asset_model = await AssetModel.create_instance(
        db_client=request.app.db_client
    )

    asset_resource = Asset(
        asset_project_id=project.project_id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=stored_file_name,
        asset_size=os.path.getsize(file_path),
        asset_status="uploaded",
        asset_indexed_chunks=0,
    )

    try:
        asset_record = await asset_model.create_asset(
            tenant_id=tenant_id,
            asset=asset_resource,
        )
    except Exception:
        Path(file_path).unlink(missing_ok=True)
        raise

    return {
        "signal": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
        "asset_id": asset_record.asset_id,
        "asset_uuid": str(asset_record.asset_uuid),
        "file_id": asset_record.asset_name,
        "project_id": project.project_id,
    }


@data_router.post("/process/{project_id}")
async def process_endpoint(
    request: Request,
    project_id: int,
    process_request: ProcessRequest,
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    tenant_id = current_user.user.tenant_id
    chunk_size = process_request.chunk_size
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset

    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    )
    project = await project_model.get_project_by_id(
        tenant_id=tenant_id,
        project_id=project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="project not found",
        )

    asset_model = await AssetModel.create_instance(
        db_client=request.app.db_client
    )

    project_files: list[Asset]

    if process_request.file_id:
        asset_record = await asset_model.get_asset_record(
            tenant_id=tenant_id,
            asset_project_id=project.project_id,
            asset_name=process_request.file_id,
        )

        if asset_record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ResponseSignal.FILE_ID_ERROR.value,
            )

        project_files = [asset_record]

    else:
        project_files, _, _ = (
            await asset_model.get_all_project_assets(
                tenant_id=tenant_id,
                asset_project_id=project.project_id,
                asset_type=AssetTypeEnum.FILE.value,
                page=1,
                page_size=100,
            )
        )

    if not project_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ResponseSignal.NO_FILES_ERROR.value,
        )

    process_controller = ProcessController(
        tenant_id=tenant_id,
        project_id=project.project_id,
    )

    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.db_client
    )

    nlp_controller = NLPController(
        vectordb_client=request.app.vectordb_client,
        generation_client=request.app.generation_client,
        embedding_client=request.app.embedding_client,
        template_parser=request.app.template_parser,
    )

    if do_reset == 1:
        collection_name = nlp_controller.create_collection_name(
            project_id=project.project_id
        )
        await request.app.vectordb_client.delete_collection(
            collection_name=collection_name
        )
        await chunk_model.delete_chunks_by_project_id(
            tenant_id=tenant_id,
            project_id=project.project_id,
        )

    inserted_records = 0
    processed_files = 0
    failed_files: list[str] = []

    for asset_record in project_files:
        file_content = process_controller.get_file_content(
            file_id=asset_record.asset_name
        )

        if not file_content:
            failed_files.append(asset_record.asset_name)
            logger.error(
                "Error while processing file: %s",
                asset_record.asset_name,
            )
            continue

        file_chunks = process_controller.process_file_content(
            file_content=file_content,
            file_id=asset_record.asset_name,
            chunk_size=chunk_size,
            overlap_size=overlap_size,
        )

        if not file_chunks:
            failed_files.append(asset_record.asset_name)
            continue

        if do_reset != 1:
            await chunk_model.delete_chunks_by_asset_id(
                tenant_id=tenant_id,
                asset_id=asset_record.asset_id,
            )

        chunk_records = [
            DataChunk(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,
                chunk_order=index + 1,
                chunk_project_id=project.project_id,
                chunk_asset_id=asset_record.asset_id,
            )
            for index, chunk in enumerate(file_chunks)
        ]

        inserted_records += await chunk_model.insert_many_chunks(
            tenant_id=tenant_id,
            chunks=chunk_records,
        )
        processed_files += 1

    if processed_files == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ResponseSignal.PROCESSING_FAILED.value,
        )

    return {
        "signal": ResponseSignal.PROCESSING_SUCCESS.value,
        "inserted_chunks": inserted_records,
        "processed_files": processed_files,
        "failed_files": failed_files,
    }
