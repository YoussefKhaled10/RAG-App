import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .rag_base import SQLAlchemyBase


class Project(SQLAlchemyBase):
    __tablename__ = "projects"

    project_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    project_uuid = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "tenants.tenant_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    project_name = Column(
        String(150),
        nullable=False,
    )

    project_description = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    tenant = relationship(
        "Tenant",
        back_populates="projects",
    )

    chunks = relationship(
        "DataChunk",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    assets = relationship(
        "Asset",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "project_name",
            name="uq_projects_tenant_name",
        ),
        Index(
            "idx_projects_tenant_id",
            "tenant_id",
        ),
    )

    def __repr__(self):
        return (
            f"<Project("
            f"project_id={self.project_id}, "
            f"project_uuid={self.project_uuid}, "
            f"tenant_id={self.tenant_id}, "
            f"project_name='{self.project_name}'"
            f")>"
        )
