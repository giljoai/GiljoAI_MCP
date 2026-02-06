"""
Configuration and system-related models for GiljoAI MCP.

This module contains models for system configuration, git settings, setup state,
optimization rules and metrics, download tokens, and API metrics.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
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
    value = Column(JSON, nullable=False)
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


class DiscoveryConfig(Base):
    """
    Discovery Configuration model - stores dynamic path overrides and discovery settings.
    Enables per-project customization of discovery behavior.
    """

    __tablename__ = "discovery_config"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    path_key = Column(String(50), nullable=False)  # vision, sessions, docs, etc.
    path_value = Column(Text, nullable=False)  # Resolved path
    priority = Column(Integer, default=0)  # Higher priority overrides lower
    enabled = Column(Boolean, default=True)
    settings = Column(JSON, default=dict)  # Additional settings (renamed from metadata)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", backref="discovery_configs")

    __table_args__ = (
        UniqueConstraint("project_id", "path_key", name="uq_discovery_path"),
        Index("idx_discovery_tenant", "tenant_key"),
        Index("idx_discovery_project", "project_id"),
    )

    def __repr__(self) -> str:
        return f"<DiscoveryConfig(id={self.id}, path_key='{self.path_key}')>"


class GitConfig(Base):
    """
    Git Configuration model - stores git settings per product for version control integration.
    Links to products via product_id for configuration-level git settings.
    Supports multiple authentication methods and webhook configuration.
    """

    __tablename__ = "git_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    product_id = Column(String(36), nullable=False)  # Links to product configuration

    # Repository configuration
    repo_url = Column(String(500), nullable=False)  # Git repository URL
    branch = Column(String(100), default="main")  # Default branch name
    remote_name = Column(String(50), default="origin")  # Remote name

    # Authentication settings
    auth_method = Column(String(20), nullable=False)  # 'https', 'ssh', 'token'
    username = Column(String(100), nullable=True)  # For HTTPS auth
    password_encrypted = Column(Text, nullable=True)  # Encrypted password/token
    ssh_key_path = Column(String(500), nullable=True)  # Path to SSH private key
    ssh_key_encrypted = Column(Text, nullable=True)  # Encrypted SSH private key content

    # Auto-commit settings
    auto_commit = Column(Boolean, default=True)  # Enable auto-commit on project completion
    auto_push = Column(Boolean, default=False)  # Enable auto-push after commit
    commit_message_template = Column(Text, nullable=True)  # Template for commit messages

    # CI/CD webhook configuration
    webhook_url = Column(String(500), nullable=True)  # Webhook URL for CI/CD triggers
    webhook_secret = Column(String(255), nullable=True)  # Webhook secret for verification
    webhook_events = Column(JSON, default=list)  # List of events to trigger webhook

    # Git ignore and repository settings
    ignore_patterns = Column(JSON, default=list)  # Additional .gitignore patterns
    git_config_options = Column(JSON, default=dict)  # Custom git config options

    # Status and metadata
    is_active = Column(Boolean, default=True)
    last_commit_hash = Column(String(40), nullable=True)  # Last known commit hash
    last_push_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)  # Last error message

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)  # Last successful auth verification

    meta_data = Column(JSON, default=dict)

    __table_args__ = (
        UniqueConstraint("product_id", name="uq_git_config_product"),
        Index("idx_git_config_tenant", "tenant_key"),
        Index("idx_git_config_product", "product_id"),
        Index("idx_git_config_active", "is_active"),
        Index("idx_git_config_auth", "auth_method"),
        CheckConstraint("auth_method IN ('https', 'ssh', 'token')", name="ck_git_config_auth_method"),
    )

    @property
    def is_configured(self) -> bool:
        """Check if git configuration is complete and valid"""
        if not self.repo_url or not self.auth_method:
            return False

        if (self.auth_method == "https" and not (self.username and self.password_encrypted)) or (
            self.auth_method == "ssh" and not (self.ssh_key_path or self.ssh_key_encrypted)
        ):
            return False
        return not (self.auth_method == "token" and not self.password_encrypted)

    @property
    def webhook_configured(self) -> bool:
        """Check if webhook is properly configured"""
        return bool(self.webhook_url and self.webhook_secret)

    def __repr__(self) -> str:
        return f"<GitConfig(id={self.id}, repo_url='{self.repo_url}')>"


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
    files_changed = Column(JSON, default=list)  # List of file paths
    insertions = Column(Integer, default=0)  # Lines added
    deletions = Column(Integer, default=0)  # Lines deleted

    # Orchestrator context
    triggered_by = Column(String(50), nullable=True)  # 'auto_commit', 'manual', 'project_completion'
    commit_type = Column(String(50), nullable=True)  # 'feature', 'fix', 'docs', 'refactor', etc.

    # Status tracking
    push_status = Column(String(20), default="pending")  # 'pending', 'pushed', 'failed'
    push_error = Column(Text, nullable=True)
    webhook_triggered = Column(Boolean, default=False)
    webhook_response = Column(JSON, nullable=True)

    # Timestamps
    committed_at = Column(DateTime(timezone=True), nullable=False)
    pushed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    meta_data = Column(JSON, default=dict)

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

    # REMOVED (Handover 0034): Default password tracking fields
    # Legacy admin/admin pattern no longer used
    # Fresh install now creates admin via CreateAdminAccount.vue
    # default_password_active = Column(...)  # REMOVED
    # password_changed_at = Column(...)  # REMOVED

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

    # Additional metadata
    meta_data = Column(JSONB, default=dict)

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

    def to_dict(self) -> Dict[str, Any]:
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
            "meta_data": self.meta_data,
        }

    @classmethod
    async def get_by_tenant(cls, session: AsyncSession, tenant_key: str) -> Optional["SetupState"]:
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

    @classmethod
    def create_or_update(cls, session: Session, tenant_key: str, **kwargs) -> "SetupState":
        """
        Create or update SetupState for a tenant.

        Args:
            session: SQLAlchemy session
            tenant_key: Tenant identifier
            **kwargs: Fields to set/update

        Returns:
            SetupState instance (new or updated)
        """
        state = cls.get_by_tenant(session, tenant_key)

        if state:
            # Update existing
            for key, value in kwargs.items():
                if hasattr(state, key):
                    setattr(state, key, value)
        else:
            # Create new
            state = cls(tenant_key=tenant_key, **kwargs)
            session.add(state)

        session.flush()
        return state

    def mark_completed(self, setup_version: Optional[str] = None) -> None:
        """
        Mark setup as completed.

        Args:
            setup_version: Optional version string to set
        """
        self.completed = True
        self.completed_at = datetime.utcnow()
        if setup_version:
            self.setup_version = setup_version

    def add_validation_failure(self, message: str) -> None:
        """
        Add a validation failure message.

        Args:
            message: Error message describing the validation failure
        """
        if self.validation_failures is None:
            self.validation_failures = []

        failures = list(self.validation_failures)  # Convert to mutable list
        failures.append({"message": message, "timestamp": datetime.utcnow().isoformat()})
        self.validation_failures = failures
        self.validation_passed = False
        self.last_validation_at = datetime.utcnow()

    def add_validation_warning(self, message: str) -> None:
        """
        Add a validation warning message.

        Args:
            message: Warning message
        """
        if self.validation_warnings is None:
            self.validation_warnings = []

        warnings = list(self.validation_warnings)  # Convert to mutable list
        warnings.append({"message": message, "timestamp": datetime.utcnow().isoformat()})
        self.validation_warnings = warnings
        self.last_validation_at = datetime.utcnow()

    def clear_validation_failures(self) -> None:
        """Clear all validation failures and warnings."""
        self.validation_failures = []
        self.validation_warnings = []
        self.validation_passed = True
        self.last_validation_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<SetupState(id={self.id}, tenant_key='{self.tenant_key}', db_initialized={self.database_initialized})>"


class OptimizationRule(Base):
    """
    Optimization Rule model - stores custom optimization rules per tenant.

    Rules define how Serena MCP operations should be optimized for specific contexts.
    Overrides default SerenaOptimizer rules when present.
    """

    __tablename__ = "optimization_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)

    # Rule definition
    operation_type = Column(String(50), nullable=False)  # OperationType enum value
    max_answer_chars = Column(Integer, nullable=False)
    prefer_symbolic = Column(Boolean, nullable=False, default=True)
    guidance = Column(Text, nullable=False)
    context_filter = Column(String(100), nullable=True)  # When to apply this rule

    # Rule metadata
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=100)  # Higher numbers = higher priority

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("idx_optimization_rule_tenant", "tenant_key"),
        Index("idx_optimization_rule_type", "operation_type"),
        Index("idx_optimization_rule_active", "is_active"),
        CheckConstraint(
            "operation_type IN ('file_read', 'symbol_search', 'symbol_replace', 'pattern_search', 'directory_list')",
            name="ck_optimization_rule_operation_type",
        ),
        CheckConstraint("max_answer_chars > 0", name="ck_optimization_rule_max_chars"),
        CheckConstraint("priority >= 0", name="ck_optimization_rule_priority"),
    )

    def __repr__(self) -> str:
        return f"<OptimizationRule(id={self.id}, operation_type={self.operation_type}, tenant_key={self.tenant_key})>"


class OptimizationMetric(Base):
    """
    Optimization Metric model - tracks context efficiency metrics from Serena MCP optimizations.

    Records every optimization operation to measure effectiveness and calculate savings.
    Enables performance analytics and optimization rule refinement.
    """

    __tablename__ = "optimization_metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)

    # Operation details
    operation_type = Column(String(50), nullable=False)  # OperationType enum value
    params_size = Column(Integer, nullable=False, default=0)
    result_size = Column(Integer, nullable=False)
    optimized = Column(Boolean, nullable=False, default=True)

    # Token calculations
    tokens_saved = Column(Integer, nullable=False, default=0)

    # Metadata
    meta_data = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships removed (Handover 0116) - Agent model eliminated

    __table_args__ = (
        Index("idx_optimization_metric_tenant", "tenant_key"),
        Index("idx_optimization_metric_type", "operation_type"),
        Index("idx_optimization_metric_date", "created_at"),
        Index("idx_optimization_metric_optimized", "optimized"),
        CheckConstraint(
            "operation_type IN ('file_read', 'symbol_search', 'symbol_replace', 'pattern_search', 'directory_list')",
            name="ck_optimization_metric_operation_type",
        ),
        CheckConstraint("params_size >= 0", name="ck_optimization_metric_params_size"),
        CheckConstraint("result_size >= 0", name="ck_optimization_metric_result_size"),
        CheckConstraint("tokens_saved >= 0", name="ck_optimization_metric_tokens_saved"),
    )

    def __repr__(self) -> str:
        return f"<OptimizationMetric(id={self.id}, operation_type={self.operation_type}, tokens_saved={self.tokens_saved})>"


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
    meta_data = Column(
        JSONB, default=dict, nullable=False, comment="Additional metadata (filename, file_count, file_size, etc.)"
    )

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
        return datetime.now(timezone.utc) > self.expires_at

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
