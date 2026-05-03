# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Configuration and system-related models for GiljoAI MCP.

This module contains models for system configuration, git commits, setup state,
download tokens, and API metrics.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class Configuration(Base):
    """
    Configuration model - stores system and project configuration.
    Supports both global and project-specific settings.
    """

    __tablename__ = "configurations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=True)  # Null for global config
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)
    key = Column(String(255), nullable=False)
    value = Column(JSONB, nullable=False)
    category = Column(String(100), default="general")
    description = Column(Text, nullable=True)
    is_secret = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_key", "key", name="uq_config_tenant_key"),
        Index("idx_config_tenant", "tenant_key"),
        Index("idx_config_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<Configuration(id={self.id}, key='{self.key}', category='{self.category}')>"


class GitCommit(Base):
    """
    Git Commit model - tracks commits made through the orchestrator.
    Provides audit trail and enables commit history viewing in dashboard.
    """

    __tablename__ = "git_commits"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    product_id = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)  # Associated project if any

    # Commit details
    commit_hash = Column(String(40), nullable=False, unique=True)
    commit_message = Column(Text, nullable=False)
    author_name = Column(String(100), nullable=False)
    author_email = Column(String(255), nullable=False)
    branch_name = Column(String(100), nullable=False)

    # Files and changes
    files_changed = Column(JSONB, default=list)  # List of file paths
    insertions = Column(Integer, default=0)  # Lines added
    deletions = Column(Integer, default=0)  # Lines deleted

    # Orchestrator context
    triggered_by = Column(String(50), nullable=True)  # 'auto_commit', 'manual', 'project_completion'
    commit_type = Column(String(50), nullable=True)  # 'feature', 'fix', 'docs', 'refactor', etc.

    # Status tracking
    push_status = Column(String(20), default="pending")  # 'pending', 'pushed', 'failed'
    push_error = Column(Text, nullable=True)
    webhook_triggered = Column(Boolean, default=False)
    webhook_response = Column(JSONB, nullable=True)

    # Timestamps
    committed_at = Column(DateTime(timezone=True), nullable=False)
    pushed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", backref="git_commits")
    # agent relationship removed (Handover 0116) - Agent model eliminated

    __table_args__ = (
        Index("idx_git_commit_tenant", "tenant_key"),
        Index("idx_git_commit_product", "product_id"),
        Index("idx_git_commit_project", "project_id"),
        Index("idx_git_commit_hash", "commit_hash"),
        Index("idx_git_commit_date", "committed_at"),
        Index("idx_git_commit_trigger", "triggered_by"),
        CheckConstraint(
            "push_status IN ('pending', 'pushed', 'failed')",
            name="ck_git_commit_push_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<GitCommit(id={self.id}, commit_hash='{self.commit_hash[:8] if self.commit_hash else None}')>"


class SetupState(Base):
    """
    SetupState model - tracks installation and setup completion status.

    This table maintains setup state per tenant, replacing the legacy file-based
    setup_state.json approach. It tracks:
    - Installation completion status
    - Version information (setup, database, Python, PostgreSQL)
    - Configured features and MCP tools
    - Configuration snapshots
    - Validation failures and warnings

    Multi-tenant isolation: Each tenant has exactly one SetupState row.
    """

    __tablename__ = "setup_state"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, unique=True, index=True)

    # Database initialization status (set when install.py creates tables)
    database_initialized = Column(Boolean, default=False, nullable=False, index=True)
    database_initialized_at = Column(DateTime(timezone=True), nullable=True)

    # Version tracking
    setup_version = Column(String(20), nullable=True)  # e.g., "2.0.0"
    database_version = Column(String(20), nullable=True)  # PostgreSQL version
    python_version = Column(String(20), nullable=True)
    node_version = Column(String(20), nullable=True)

    # REMOVED (Handover 0034): Default password tracking fields removed
    # Fresh install now creates admin via CreateAdminAccount.vue

    # First admin creation tracking (Handover 0035: Security Enhancement)
    # CRITICAL SECURITY: Atomic flag preventing duplicate admin creation after first user setup
    # Used by /api/auth/create-first-admin endpoint to lock down after initial setup
    first_admin_created = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="True after first admin account created - prevents duplicate admin creation attacks",
    )
    first_admin_created_at = Column(
        DateTime(timezone=True), nullable=True, comment="Timestamp when first admin account was created"
    )

    # Feature and tool configuration (JSONB for performance)
    features_configured = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Nested dict of configured features: {database: true, api: {enabled: true, port: 7272}}",
    )
    tools_enabled = Column(JSONB, default=list, nullable=False, comment="Array of enabled MCP tool names")

    # Configuration snapshot
    config_snapshot = Column(JSONB, nullable=True, comment="Snapshot of config.yaml at setup completion")

    # Validation tracking
    validation_passed = Column(Boolean, default=True, nullable=False)
    validation_failures = Column(JSONB, default=list, nullable=False, comment="Array of validation failure messages")
    validation_warnings = Column(JSONB, default=list, nullable=False, comment="Array of validation warning messages")
    last_validation_at = Column(DateTime(timezone=True), nullable=True)

    # Installation metadata
    installer_version = Column(String(20), nullable=True)
    install_mode = Column(String(20), nullable=True, comment="Installation mode: localhost, server, lan, wan")
    install_path = Column(Text, nullable=True, comment="Installation directory path")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        # Version format constraint (semantic versioning)
        CheckConstraint(
            "setup_version IS NULL OR setup_version ~ '^[0-9]+\\.[0-9]+\\.[0-9]+(-[a-zA-Z0-9\\.\\-]+)?$'",
            name="ck_setup_version_format",
        ),
        CheckConstraint(
            "database_version IS NULL OR database_version ~ '^[0-9]+(\\.([0-9]+|[0-9]+\\.[0-9]+))?$'",
            name="ck_database_version_format",
        ),
        # Install mode constraint
        CheckConstraint(
            "install_mode IS NULL OR install_mode IN ('localhost', 'server', 'lan', 'wan')",
            name="ck_install_mode_values",
        ),
        # Database initialized timestamp must be set when database_initialized=true
        CheckConstraint(
            "(database_initialized = false) OR (database_initialized = true AND database_initialized_at IS NOT NULL)",
            name="ck_database_initialized_at_required",
        ),
        # First admin created timestamp must be set when first_admin_created=true
        CheckConstraint(
            "(first_admin_created = false) OR (first_admin_created = true AND first_admin_created_at IS NOT NULL)",
            name="ck_first_admin_created_at_required",
        ),
        # Regular indexes
        Index("idx_setup_tenant", "tenant_key"),  # Primary lookup index
        Index("idx_setup_database_initialized", "database_initialized"),  # Filter by database init status
        Index("idx_setup_mode", "install_mode"),  # Filter by installation mode
        # GIN indexes for JSONB columns (enables efficient queries on nested JSON)
        Index("idx_setup_features_gin", "features_configured", postgresql_using="gin"),
        Index("idx_setup_tools_gin", "tools_enabled", postgresql_using="gin"),
        # Partial index for incomplete database initialization (frequently queried)
        Index(
            "idx_setup_database_incomplete",
            "tenant_key",
            "database_initialized",
            postgresql_where="database_initialized = false",
        ),
        # Partial index for fresh installs (no admin created yet) - used by security checks
        Index(
            "idx_setup_fresh_install",
            "tenant_key",
            "first_admin_created",
            postgresql_where="first_admin_created = false",
        ),
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize SetupState to dictionary.

        Returns:
            Dict containing all setup state fields
        """
        return {
            "id": self.id,
            "tenant_key": self.tenant_key,
            "database_initialized": self.database_initialized,
            "database_initialized_at": self.database_initialized_at.isoformat()
            if self.database_initialized_at
            else None,
            "setup_version": self.setup_version,
            "database_version": self.database_version,
            "python_version": self.python_version,
            "node_version": self.node_version,
            # REMOVED (Handover 0034): default_password_active and password_changed_at fields
            # ADDED (Handover 0035): First admin creation tracking
            "first_admin_created": self.first_admin_created,
            "first_admin_created_at": self.first_admin_created_at.isoformat() if self.first_admin_created_at else None,
            "features_configured": self.features_configured,
            "tools_enabled": self.tools_enabled,
            "config_snapshot": self.config_snapshot,
            "validation_passed": self.validation_passed,
            "validation_failures": self.validation_failures,
            "validation_warnings": self.validation_warnings,
            "last_validation_at": self.last_validation_at.isoformat() if self.last_validation_at else None,
            "installer_version": self.installer_version,
            "install_mode": self.install_mode,
            "install_path": self.install_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    async def get_by_tenant(cls, session: AsyncSession, tenant_key: str) -> SetupState | None:
        """
        Retrieve SetupState for a specific tenant.

        Args:
            session: Async SQLAlchemy session
            tenant_key: Tenant identifier

        Returns:
            SetupState instance or None if not found
        """
        from sqlalchemy import select

        result = await session.execute(select(cls).where(cls.tenant_key == tenant_key))
        return result.scalar_one_or_none()

    # Sprint 003c: Field allowlist for create_or_update (no hasattr gate)
    _ALLOWED_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "database_initialized",
            "database_initialized_at",
            "setup_version",
            "database_version",
            "python_version",
            "node_version",
            "first_admin_created",
            "first_admin_created_at",
            "features_configured",
            "tools_enabled",
            "config_snapshot",
            "validation_passed",
            "validation_failures",
            "validation_warnings",
            "last_validation_at",
            "installer_version",
            "install_mode",
            "install_path",
        }
    )

    @classmethod
    def create_or_update(cls, session: Session, tenant_key: str, **kwargs) -> SetupState:
        """
        Create or update SetupState for a tenant.

        Sprint 003c: Uses field allowlist instead of hasattr for security.

        Args:
            session: SQLAlchemy session
            tenant_key: Tenant identifier
            **kwargs: Fields to set/update (must be in _ALLOWED_FIELDS)

        Returns:
            SetupState instance (new or updated)
        """
        # Filter to allowed fields only (security: prevents id/tenant_key/created_at overwrite)
        safe_kwargs = {k: v for k, v in kwargs.items() if k in cls._ALLOWED_FIELDS}

        state = cls.get_by_tenant(session, tenant_key)

        if state:
            for key, value in safe_kwargs.items():
                setattr(state, key, value)
        else:
            state = cls(tenant_key=tenant_key, **safe_kwargs)
            session.add(state)

        session.flush()
        return state

    def __repr__(self) -> str:
        return f"<SetupState(id={self.id}, tenant_key='{self.tenant_key}', db_initialized={self.database_initialized})>"


class DownloadToken(Base):
    """
    Download Token model for secure file downloads.

    Implements a production-grade token system with lifecycle tracking:
    - UUID v4 tokens (cryptographically random)
    - 15-minute expiry window
    - Multi-tenant isolation (tenant_key)
    - Staging lifecycle (pending -> ready | failed)
    - Download metrics (count + last_downloaded_at)
    - Background cleanup of expired/failed/abandoned tokens

    Use Cases:
    - Slash command download (UI curl command → slash_commands.zip)
    - Agent template download (/api/download/generate-token → agent_templates.zip)
    - MCP tool file retrieval (token-based downloads)

    Multi-tenant isolation: All queries filter by tenant_key.
    """

    __tablename__ = "download_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(
        String(36),
        unique=True,
        nullable=False,
        default=generate_uuid,
        index=True,
        comment="UUID v4 token used in download URL",
    )
    tenant_key = Column(String(36), nullable=False, index=True, comment="Tenant key for multi-tenant isolation")

    # Download metadata
    download_type = Column(String(50), nullable=False, comment="Type of download: 'slash_commands', 'agent_templates'")
    filename = Column(String(255), nullable=True, comment="Original filename for the download")

    # Staging lifecycle and metrics (Handover 0102)
    staging_status = Column(
        String(20), default="pending", nullable=False, comment="Staging lifecycle status: pending|ready|failed"
    )
    staging_error = Column(Text, nullable=True, comment="Staging error details when status=failed")
    download_count = Column(Integer, default=0, nullable=False, comment="Number of successful downloads for this token")
    last_downloaded_at = Column(
        DateTime(timezone=True), nullable=True, comment="Timestamp of most recent successful download"
    )

    # Expiry management
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(
        DateTime(timezone=True), nullable=False, comment="Token expiry timestamp (15 minutes after creation)"
    )

    __table_args__ = (
        Index("idx_download_token_token", "token"),
        Index("idx_download_token_tenant", "tenant_key"),
        Index("idx_download_token_expires", "expires_at"),
        Index("idx_download_token_tenant_type", "tenant_key", "download_type"),
        CheckConstraint("download_type IN ('slash_commands', 'agent_templates')", name="ck_download_token_type"),
        CheckConstraint("staging_status IN ('pending', 'ready', 'failed')", name="ck_download_token_staging_status"),
    )

    def __repr__(self) -> str:
        return f"<DownloadToken(id={self.id}, token={self.token}, type={self.download_type}, downloads={self.download_count})>"

    @property
    def is_expired(self) -> bool:
        """Check if token has expired"""
        return datetime.now(UTC) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and staging ready)."""
        return (not self.is_expired) and (self.staging_status == "ready")


class ApiMetrics(Base):
    """API Metrics model - tracks API and MCP call counts per tenant."""

    __tablename__ = "api_metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, unique=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    total_api_calls = Column(Integer, default=0)
    total_mcp_calls = Column(Integer, default=0)

    __table_args__ = (Index("idx_api_metrics_tenant_date", "tenant_key", "date"),)

    def __repr__(self) -> str:
        return f"<ApiMetrics(id={self.id}, tenant_key='{self.tenant_key}')>"
