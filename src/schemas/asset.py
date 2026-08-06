from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


AssetStatus = Literal[
    "uploaded",
    "processing",
    "indexed",
    "failed",
]


class AssetResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    asset_id: int
    asset_uuid: UUID
    asset_type: str
    asset_name: str
    asset_size: int
    asset_config: dict[str, Any] | None = None
    asset_status: AssetStatus
    asset_error: str | None = None
    asset_indexed_chunks: int
    asset_project_id: int
    created_at: datetime
    updated_at: datetime | None = None


class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)


class FileUploadResponse(BaseModel):
    signal: str
    asset: AssetResponse
    task_id: str
    processing_status: Literal["queued"] = "queued"
