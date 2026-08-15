import uuid

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import relationship

from .rag_base import SQLAlchemyBase


class DatabaseTablePermission(SQLAlchemyBase):
    __tablename__ = "database_table_permissions"

    table_permission_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    connection_id = Column(
        Integer,
        ForeignKey("database_connections.connection_id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.role_id", ondelete="CASCADE"),
        nullable=False,
    )
    schema_name = Column(String(128), nullable=False)
    table_name = Column(String(128), nullable=False)
    can_read = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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

    column_permissions = relationship(
        "DatabaseColumnPermission",
        back_populates="table_permission",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DatabaseColumnPermission.column_name",
    )
    row_filters = relationship(
        "DatabaseRowFilter",
        back_populates="table_permission",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DatabaseRowFilter.filter_name",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "connection_id",
            "role_id",
            "schema_name",
            "table_name",
            name="uq_db_table_permissions_scope",
        ),
        Index(
            "idx_db_table_permissions_tenant_connection_role",
            "tenant_id",
            "connection_id",
            "role_id",
        ),
        Index(
            "idx_db_table_permissions_table",
            "tenant_id",
            "connection_id",
            "schema_name",
            "table_name",
        ),
    )


class DatabaseColumnPermission(SQLAlchemyBase):
    __tablename__ = "database_column_permissions"

    column_permission_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    table_permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "database_table_permissions.table_permission_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    column_name = Column(String(128), nullable=False)
    can_read = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    can_filter = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    can_aggregate = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    is_sensitive = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    masking_type = Column(
        String(20),
        nullable=False,
        default="none",
        server_default="none",
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

    table_permission = relationship(
        "DatabaseTablePermission",
        back_populates="column_permissions",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "table_permission_id",
            "column_name",
            name="uq_db_column_permissions_scope",
        ),
        CheckConstraint(
            "masking_type IN "
            "('none', 'full', 'partial', 'email', 'phone', "
            "'last4', 'hash', 'unmasked')",
            name="chk_db_column_permissions_masking",
        ),
        CheckConstraint(
            "can_read OR can_filter OR can_aggregate",
            name="chk_db_column_permissions_capability",
        ),
        CheckConstraint(
            "(is_sensitive AND ((can_read AND masking_type <> 'none') OR "
            "(NOT can_read AND masking_type = 'none'))) OR "
            "(NOT is_sensitive AND masking_type = 'none')",
            name="chk_db_column_permissions_sensitive_mask",
        ),
        Index(
            "idx_db_column_permissions_table_permission",
            "tenant_id",
            "table_permission_id",
        ),
    )


class DatabaseRowFilter(SQLAlchemyBase):
    __tablename__ = "database_row_filters"

    row_filter_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    table_permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "database_table_permissions.table_permission_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    filter_name = Column(String(150), nullable=False)
    column_name = Column(String(128), nullable=False)
    operator = Column(String(30), nullable=False)
    value_source = Column(
        String(30),
        nullable=False,
        default="literal",
        server_default="literal",
    )
    value = Column(JSONB, nullable=True)
    enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    table_permission = relationship(
        "DatabaseTablePermission",
        back_populates="row_filters",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "table_permission_id",
            "filter_name",
            name="uq_db_row_filters_scope",
        ),
        CheckConstraint(
            "operator IN "
            "('eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'not_in', "
            "'contains', 'starts_with', 'ends_with', 'is_null', 'not_null')",
            name="chk_db_row_filters_operator",
        ),
        CheckConstraint(
            "value_source IN "
            "('literal', 'current_user_id', 'current_tenant_id', "
            "'current_user_email')",
            name="chk_db_row_filters_value_source",
        ),
        Index(
            "idx_db_row_filters_table_permission",
            "tenant_id",
            "table_permission_id",
            "enabled",
        ),
    )
