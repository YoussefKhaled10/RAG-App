from .rag_base import SQLAlchemyBase
from sqlalchemy import (
    Column,
    String,
    DateTime,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid


class Tenant(SQLAlchemyBase):
    __tablename__ = "tenants"

    tenant_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_name = Column(
        String(200),
        nullable=False,
    )
    tenant_code = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    tenant_status = Column(
        String(30),
        nullable=False,
        default="active",
        server_default="active",
    )
    tenant_settings = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
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

    users = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    roles = relationship(
        "Role",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    projects = relationship(
        "Project",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    database_connections = relationship(
        "DatabaseConnection",
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "tenant_status IN ('active', 'inactive', 'suspended')",
            name="chk_tenant_status",
        ),
    )

    def __repr__(self):
        return (
            f"<Tenant("
            f"tenant_id={self.tenant_id}, "
            f"tenant_name='{self.tenant_name}', "
            f"tenant_code='{self.tenant_code}', "
            f"tenant_status='{self.tenant_status}'"
            f")>"
        )
