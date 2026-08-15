from .rag_base import SQLAlchemyBase
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid


class User(SQLAlchemyBase):
    __tablename__ = "users"

    user_id = Column(
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
    user_email = Column(
        String(255),
        nullable=False,
    )
    user_full_name = Column(
        String(255),
        nullable=True,
    )
    password_hash = Column(
        String,
        nullable=False,
    )
    user_status = Column(
        String(30),
        nullable=False,
        default="active",
        server_default="active",
    )
    is_tenant_admin = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    last_login_at = Column(
        DateTime(timezone=True),
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
        back_populates="users",
    )
    user_roles = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    roles = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
        viewonly=True,
    )
    created_database_connections = relationship(
        "DatabaseConnection",
        back_populates="created_by_user",
        foreign_keys="DatabaseConnection.created_by_user_id",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "user_email",
            name="uq_users_tenant_email",
        ),
        CheckConstraint(
            "user_status IN ('active', 'inactive', 'suspended')",
            name="chk_user_status",
        ),
        Index(
            "idx_users_tenant_id",
            "tenant_id",
        ),
        Index(
            "idx_users_email",
            "user_email",
        ),
    )

    def __repr__(self):
        return (
            f"<User("
            f"user_id={self.user_id}, "
            f"tenant_id={self.tenant_id}, "
            f"user_email='{self.user_email}', "
            f"user_status='{self.user_status}', "
            f"is_tenant_admin={self.is_tenant_admin}"
            f")>"
        )
