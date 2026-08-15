import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .rag_base import SQLAlchemyBase


class DataChunk(SQLAlchemyBase):
    __tablename__ = "chunks"

    chunk_id = Column(Integer, primary_key=True, autoincrement=True)
    chunk_uuid = Column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    chunk_text = Column(Text, nullable=False)
    chunk_metadata = Column(JSONB, nullable=True)
    chunk_order = Column(Integer, nullable=False)
    chunk_project_id = Column(
        Integer, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False
    )
    chunk_asset_id = Column(
        Integer, ForeignKey("assets.asset_id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    project = relationship("Project", back_populates="chunks")
    asset = relationship("Asset", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunk_project_id", "chunk_project_id"),
        Index("ix_chunk_asset_id", "chunk_asset_id"),
    )


class RetrievedDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunk_id: int
    text: str
    score: float
    metadata: dict = Field(default_factory=dict)
    asset_id: int | None = None
    chunk_order: int | None = None
