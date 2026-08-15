from .rag_base import SQLAlchemyBase
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    PrimaryKeyConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
class UserRole(SQLAlchemyBase):

    __tablename__ = "user_roles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "roles.role_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    assigned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # =========================
    # Relationships
    # =========================
    user = relationship(
        "User",
        back_populates="user_roles",
    )

    role = relationship(
        "Role",
        back_populates="user_roles",
    )

    __table_args__ = (
        PrimaryKeyConstraint(
            "user_id",
            "role_id",
            name="pk_user_roles",
        ),
        Index(
            "idx_user_roles_user_id",
            "user_id",
        ),
        Index(
            "idx_user_roles_role_id",
            "role_id",
        ),
    )

    def __repr__(self):
        return (
            f"<UserRole("
            f"user_id={self.user_id}, "
            f"role_id={self.role_id}"
            f")>"
        )