import hashlib
import logging
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from controllers import DataController, NLPController, ProcessController
from dependencies.auth import get_current_user, require_role
from helpers.config import Settings, get_settings
from models import ResponseSignal
from models.AssetModel import AssetModel
from models.ChunkModel import ChunkModel
from models.ProjectModel import ProjectModel
from models.db_schemes import Asset
from models.enums.AssetTypeEnum import AssetTypeEnum
from models.enums.RoleEnum import RoleName
from schemas.asset import (
    AssetListResponse,
    AssetResponse,
    FileUploadResponse,
)
from schemas.auth import CurrentUserResponse
from tasks.file_processing import process_uploaded_file


logger = logging.getLogger("uvicorn.error")

files_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["project files"],
)


async def _get_project_or_404(
    request: Request,
    tenant_id,
    project_id: int,
):
    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client,
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
    return project


async def _get_asset_or_404(
    request: Request,
    tenant_id,
    project_id: int,
    asset_id: int,
):
    project = await _get_project_or_404(
        request=request,
        tenant_id=tenant_id,
        project_id=project_id,
    )
    asset_model = await AssetModel.create_instance(
        db_client=request.app.db_client,
    )
    asset = await asset_model.get_asset_by_id(
        tenant_id=tenant_id,
        asset_id=asset_id,
    )
    if (
        asset is None
        or asset.asset_project_id != project.project_id
        or asset.asset_type != AssetTypeEnum.FILE.value
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="file not found",
        )
    return project, asset, asset_model


@files_router.post(
    "/{project_id}/files",
    response_model=FileUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_project_file(
    request: Request,
    project_id: int,
    file: UploadFile = File(...),
    current_user: CurrentUserResponse = Depends(
        require_role(RoleName.DOCUMENT_MANAGER.value)
    ),
    app_settings: Settings = Depends(get_settings),
) -> FileUploadResponse:
    tenant_id = current_user.user.tenant_id
    project = await _get_project_or_404(
        request=request,
        tenant_id=tenant_id,
        project_id=project_id,
    )

    data_controller = DataController()
    is_valid, validation_signal = (
        data_controller.validate_uploaded_file(file)
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_signal,
        )

    file_path, stored_file_name = (
        data_controller.generate_unique_filepath(
            original_file_name=file.filename or "",
            tenant_id=tenant_id,
            project_id=project.project_id,
        )
    )

    written_size = 0
    checksum = hashlib.sha256()
    try:
        async with aiofiles.open(file_path, "wb") as destination:
            while True:
                chunk = await file.read(
                    app_settings.FILE_DEFAULT_CHUNK_SIZE
                )
                if not chunk:
                    break
                written_size += len(chunk)
                if written_size > app_settings.FILE_MAX_SIZE:
                    raise HTTPException(
                        status_code=(
                            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                        ),
                        detail=(
                            ResponseSignal.FILE_SIZE_EXCEEDED.value
                        ),
                    )
                checksum.update(chunk)
                await destination.write(chunk)
    except HTTPException:
        Path(file_path).unlink(missing_ok=True)
        raise
    except Exception as exc:
        Path(file_path).unlink(missing_ok=True)
        logger.exception("file upload failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ResponseSignal.FILE_UPLOAD_FAILED.value,
        ) from exc
    finally:
        await file.close()

    if written_size == 0:
        Path(file_path).unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="uploaded file is empty",
        )

    asset_model = await AssetModel.create_instance(
        db_client=request.app.db_client,
    )
    asset_record = Asset(
        asset_project_id=project.project_id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=stored_file_name,
        asset_size=written_size,
        asset_config={
            "original_file_name": Path(
                file.filename or "uploaded-file"
            ).name,
            "content_type": file.content_type,
            "checksum_algorithm": "sha256",
            "checksum": checksum.hexdigest(),
        },
        asset_status="uploaded",
        asset_indexed_chunks=0,
    )
    try:
        asset_record = await asset_model.create_asset(
            tenant_id=tenant_id,
            asset=asset_record,
        )
    except Exception:
        Path(file_path).unlink(missing_ok=True)
        raise

    task = process_uploaded_file.apply_async(
        kwargs={
            "tenant_id": str(tenant_id),
            "project_id": project.project_id,
            "asset_id": asset_record.asset_id,
            "file_id": stored_file_name,
            "chunk_size": 500,
            "overlap_size": 50,
        },
        queue="file_processing",
    )

    return FileUploadResponse(
        signal=ResponseSignal.FILE_UPLOAD_SUCCESS.value,
        asset=AssetResponse.model_validate(asset_record),
        task_id=task.id,
    )


@files_router.get(
    "/{project_id}/files",
    response_model=AssetListResponse,
)
async def list_project_files(
    request: Request,
    project_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUserResponse = Depends(
        get_current_user
    ),
) -> AssetListResponse:
    tenant_id = current_user.user.tenant_id
    project = await _get_project_or_404(
        request=request,
        tenant_id=tenant_id,
        project_id=project_id,
    )
    asset_model = await AssetModel.create_instance(
        db_client=request.app.db_client,
    )
    assets, total, total_pages = (
        await asset_model.get_all_project_assets(
            tenant_id=tenant_id,
            asset_project_id=project.project_id,
            asset_type=AssetTypeEnum.FILE.value,
            page=page,
            page_size=page_size,
        )
    )
    return AssetListResponse(
        items=[
            AssetResponse.model_validate(asset)
            for asset in assets
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@files_router.get(
    "/{project_id}/files/{asset_id}",
    response_model=AssetResponse,
)
async def get_project_file(
    request: Request,
    project_id: int,
    asset_id: int,
    current_user: CurrentUserResponse = Depends(
        get_current_user
    ),
) -> AssetResponse:
    tenant_id = current_user.user.tenant_id
    _, asset, _ = await _get_asset_or_404(
        request=request,
        tenant_id=tenant_id,
        project_id=project_id,
        asset_id=asset_id,
    )
    return AssetResponse.model_validate(asset)


@files_router.get(
    "/{project_id}/files/{asset_id}/download",
    response_class=FileResponse,
)
async def download_project_file(
    request: Request,
    project_id: int,
    asset_id: int,
    current_user: CurrentUserResponse = Depends(
        get_current_user
    ),
):
    tenant_id = current_user.user.tenant_id
    project, asset, _ = await _get_asset_or_404(
        request=request,
        tenant_id=tenant_id,
        project_id=project_id,
        asset_id=asset_id,
    )
    process_controller = ProcessController(
        tenant_id=tenant_id,
        project_id=project.project_id,
    )
    file_path = Path(
        process_controller.get_file_path(asset.asset_name)
    )
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="stored file not found",
        )
    asset_config = dict(asset.asset_config or {})
    original_name = Path(
        asset_config.get("original_file_name")
        or asset.asset_name
    ).name
    return FileResponse(
        path=str(file_path),
        filename=original_name,
        media_type=asset_config.get("content_type"),
    )


@files_router.post(
    "/{project_id}/files/{asset_id}/reprocess",
    response_model=FileUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_project_file(
    request: Request,
    project_id: int,
    asset_id: int,
    current_user: CurrentUserResponse = Depends(
        require_role(RoleName.DOCUMENT_MANAGER.value)
    ),
) -> FileUploadResponse:
    tenant_id = current_user.user.tenant_id
    project, asset, _ = await _get_asset_or_404(
        request=request,
        tenant_id=tenant_id,
        project_id=project_id,
        asset_id=asset_id,
    )
    if asset.asset_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="file is already being processed",
        )

    process_controller = ProcessController(
        tenant_id=tenant_id,
        project_id=project.project_id,
    )
    file_path = Path(
        process_controller.get_file_path(asset.asset_name)
    )
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="stored file not found",
        )

    task = process_uploaded_file.apply_async(
        kwargs={
            "tenant_id": str(tenant_id),
            "project_id": project.project_id,
            "asset_id": asset.asset_id,
            "file_id": asset.asset_name,
            "chunk_size": 500,
            "overlap_size": 50,
            "run_id": uuid4().hex,
        },
        queue="file_processing",
    )
    return FileUploadResponse(
        signal=ResponseSignal.FILE_UPLOAD_SUCCESS.value,
        asset=AssetResponse.model_validate(asset),
        task_id=task.id,
    )


@files_router.delete(
    "/{project_id}/files/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project_file(
    request: Request,
    project_id: int,
    asset_id: int,
    current_user: CurrentUserResponse = Depends(
        require_role(RoleName.DOCUMENT_MANAGER.value)
    ),
) -> None:
    tenant_id = current_user.user.tenant_id
    project, asset, asset_model = await _get_asset_or_404(
        request=request,
        tenant_id=tenant_id,
        project_id=project_id,
        asset_id=asset_id,
    )
    if asset.asset_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="a processing file cannot be deleted",
        )

    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.db_client,
    )
    chunks = await chunk_model.get_chunks_by_asset_id(
        tenant_id=tenant_id,
        asset_id=asset.asset_id,
    )
    chunk_ids = [
        chunk.chunk_id
        for chunk in chunks
        if chunk.chunk_id is not None
    ]

    if chunk_ids:
        nlp_controller = NLPController(
            vectordb_client=request.app.vectordb_client,
            generation_client=request.app.generation_client,
            embedding_client=request.app.embedding_client,
            template_parser=request.app.template_parser,
        )
        deleted_vectors = await nlp_controller.delete_vectors_by_ids(
            project=project,
            record_ids=chunk_ids,
        )
        if not deleted_vectors:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to delete file vectors",
            )
        await chunk_model.delete_chunks_by_asset_id(
            tenant_id=tenant_id,
            asset_id=asset.asset_id,
        )

    process_controller = ProcessController(
        tenant_id=tenant_id,
        project_id=project.project_id,
    )
    file_path = Path(
        process_controller.get_file_path(asset.asset_name)
    )

    deleted_asset = await asset_model.delete_asset(
        tenant_id=tenant_id,
        asset_id=asset.asset_id,
    )
    if not deleted_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="file not found",
        )

    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        logger.exception(
            "asset was deleted but stored file cleanup failed: %s",
            file_path,
        )
