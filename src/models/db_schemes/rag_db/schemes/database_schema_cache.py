from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .rag_base import SQLAlchemyBase


class DatabaseSchemaCache(SQLAlchemyBase):
    __tablename__ = "database_schema_caches"

    cache_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id = Column(
        Integer,
        ForeignKey(
            "database_connections.connection_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    schema_hash = Column(
        String(64),
        nullable=False,
    )
    metadata_payload = Column(
        JSONB,
        nullable=False,
    )
    schema_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    table_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    column_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    primary_key_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    foreign_key_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    relationship_count = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    synced_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connection_id",
            name="uq_schema_cache_tenant_connection",
        ),
        CheckConstraint(
            "schema_count >= 0 AND table_count >= 0 "
            "AND column_count >= 0 AND primary_key_count >= 0 "
            "AND foreign_key_count >= 0 AND relationship_count >= 0",
            name="chk_schema_cache_nonnegative_counts",
        ),
        Index(
            "idx_schema_cache_tenant_connection",
            "tenant_id",
            "connection_id",
        ),
        Index(
            "idx_schema_cache_synced_at",
            "tenant_id",
            "synced_at",
        ),
    )

    def __repr__(self):
        return (
            f"<DatabaseSchemaCache(cache_id={self.cache_id}, "
            f"tenant_id={self.tenant_id}, "
            f"connection_id={self.connection_id}, "
            f"synced_at={self.synced_at})>"
        )
