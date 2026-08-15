from .rag_base import SQLAlchemyBase
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
class Role(SQLAlchemyBase):

    __tablename__ = "roles"

    role_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "tenants.tenant_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    role_name = Column(
        String(100),
        nullable=False,
    )

    role_description = Column(
        Text,
        nullable=True,
    )

    is_system_role = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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

    # =========================
    # Relationships
    # =========================
    tenant = relationship(
        "Tenant",
        back_populates="roles",
    )

    user_roles = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    users = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
        viewonly=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "role_name",
            name="uq_roles_tenant_name",
        ),
        Index(
            "idx_roles_tenant_id",
            "tenant_id",
        ),
    )

    def __repr__(self):
        return (
            f"<Role("
            f"role_id={self.role_id}, "
            f"tenant_id={self.tenant_id}, "
            f"role_name='{self.role_name}', "
            f"is_system_role={self.is_system_role}"
            f")>"
        )