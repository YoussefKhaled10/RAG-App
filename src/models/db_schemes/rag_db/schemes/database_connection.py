import uuid

from sqlalchemy import (
    CheckConstraint,
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


class DatabaseConnection(SQLAlchemyBase):
    __tablename__ = "database_connections"

    connection_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    connection_uuid = Column(
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
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.user_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    connection_name = Column(
        String(150),
        nullable=False,
    )
    database_type = Column(
        String(30),
        nullable=False,
        default="postgresql",
        server_default="postgresql",
    )
    host = Column(
        String(255),
        nullable=False,
    )
    port = Column(
        Integer,
        nullable=False,
        default=5432,
        server_default="5432",
    )
    database_name = Column(
        String(150),
        nullable=False,
    )
    username = Column(
        String(150),
        nullable=False,
    )

    # This column must contain ciphertext only. Plain passwords must never
    # be assigned here. Encryption is implemented in the next stage.
    encrypted_password = Column(
        Text,
        nullable=False,
    )

    ssl_mode = Column(
        String(30),
        nullable=False,
        default="prefer",
        server_default="prefer",
    )
    connection_status = Column(
        String(30),
        nullable=False,
        default="untested",
        server_default="untested",
    )

    last_tested_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_success_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error_code = Column(
        String(100),
        nullable=True,
    )
    last_error_message = Column(
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
        back_populates="database_connections",
    )
    created_by_user = relationship(
        "User",
        back_populates="created_database_connections",
        foreign_keys=[created_by_user_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connection_name",
            name="uq_database_connections_tenant_name",
        ),
        CheckConstraint(
            "database_type IN ('postgresql')",
            name="chk_database_connections_type",
        ),
        CheckConstraint(
            "connection_status IN "
            "('untested', 'connected', 'failed', 'disabled')",
            name="chk_database_connections_status",
        ),
        CheckConstraint(
            "ssl_mode IN "
            "('disable', 'allow', 'prefer', 'require', "
            "'verify-ca', 'verify-full')",
            name="chk_database_connections_ssl_mode",
        ),
        CheckConstraint(
            "port >= 1 AND port <= 65535",
            name="chk_database_connections_port",
        ),
        Index(
            "idx_database_connections_tenant_id",
            "tenant_id",
        ),
        Index(
            "idx_database_connections_status",
            "tenant_id",
            "connection_status",
        ),
        Index(
            "idx_database_connections_created_by",
            "created_by_user_id",
        ),
    )

    def __repr__(self):
        return (
            f"<DatabaseConnection("
            f"connection_id={self.connection_id}, "
            f"connection_uuid={self.connection_uuid}, "
            f"tenant_id={self.tenant_id}, "
            f"connection_name='{self.connection_name}', "
            f"database_type='{self.database_type}', "
            f"connection_status='{self.connection_status}'"
            f")>"
        )
