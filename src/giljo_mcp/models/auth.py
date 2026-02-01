"""
Authentication and authorization models.

This module contains all user authentication and session management models:
- User: User accounts for authentication
- APIKey: Personal API keys for MCP tool authentication
- MCPSession: MCP HTTP session tracking with tenant isolation
"""

from datetime import datetime, timedelta, timezone
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class User(Base):
    """
    User model - user accounts for authentication (LAN/WAN modes).

    Users are the primary authentication entity in LAN/WAN deployment modes.
    Each user can have multiple API keys for different applications/contexts.

    Phase 4 Enhancement: Task ownership and assignment tracking
    - created_tasks: Tasks created by this user
    - assigned_tasks: Tasks assigned to this user for completion

    Handover 0023: Password Reset and Recovery PIN
    - recovery_pin_hash: Hashed 4-digit recovery PIN for password reset
    - failed_pin_attempts: Track failed PIN attempts for rate limiting
    - pin_lockout_until: Timestamp when PIN lockout expires
    - must_change_password: Force password change on next login
    - must_set_pin: Force recovery PIN setup on next login

    Multi-tenant isolation: Users belong to a tenant_key namespace.

    Handover 0424f: User.org_id schema
    - org_id: Direct foreign key to organizations table (nullable for migration)
    - organization: Direct relationship to Organization model
    """

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)

    # Organization relationship (Handover 0424f, 0424j - NOT NULL enforced)
    org_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
        comment="Direct foreign key to organization (Handover 0424j - NOT NULL enforced)"
    )

    # Credentials
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for system users (auto-login only)

    # Recovery PIN for password reset (Handover 0023)
    recovery_pin_hash = Column(
        String(255), nullable=True, comment="Bcrypt hash of 4-digit recovery PIN for password reset"
    )
    failed_pin_attempts = Column(
        Integer, default=0, nullable=False, comment="Number of failed PIN verification attempts (rate limiting)"
    )
    pin_lockout_until = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when PIN lockout expires (15 minutes after 5 failed attempts)",
    )
    must_change_password = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Force user to change password on next login (new users, admin reset)",
    )
    must_set_pin = Column(
        Boolean, default=False, nullable=False, comment="Force user to set recovery PIN on next login (new users)"
    )

    # System user flag (for auto-login localhost user)
    is_system_user = Column(Boolean, default=False, nullable=False)

    # Profile
    full_name = Column(String(255), nullable=True)

    # Authorization
    role = Column(String(32), nullable=False, default="developer")
    # Roles: "admin", "developer", "viewer"

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # User Preferences (Handover 0048)
    field_priority_config = Column(
        JSONB, nullable=True, default=None, comment="User-customizable field priority for agent mission generation"
    )

    # Depth Configuration (Handover 0314)
    depth_config = Column(
        JSONB,
        nullable=False,
        default={
            "vision_documents": "medium",
            "memory_last_n_projects": 3,
            "git_commits": 25,
            "agent_templates": "type_only",
            "tech_stack_sections": "all",
            "architecture_depth": "overview",
            "execution_mode": "claude_code",
        },
        comment="User depth configuration for context granularity (Handover 0314)"
    )

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

    # Organization relationship (Handover 0424f)
    organization = relationship("Organization", back_populates="users", foreign_keys="User.org_id")

    # Phase 4: Task relationships (Handover 0076: removed assigned_tasks)
    created_tasks = relationship("Task", foreign_keys="Task.created_by_user_id", back_populates="created_by_user")

    __table_args__ = (
        Index("idx_user_tenant", "tenant_key"),
        Index("idx_user_username", "username"),
        Index("idx_user_email", "email"),
        Index("idx_user_active", "is_active"),
        Index("idx_user_system", "is_system_user"),  # Index for system user queries
        Index("idx_user_pin_lockout", "pin_lockout_until"),  # Index for lockout queries (Handover 0023)
        Index("idx_user_org_id", "org_id"),  # Index for organization queries (Handover 0424f)
        CheckConstraint("role IN ('admin', 'developer', 'viewer')", name="ck_user_role"),
        CheckConstraint("failed_pin_attempts >= 0", name="ck_user_pin_attempts_positive"),  # Handover 0023
    )

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class APIKey(Base):
    """
    API Key model - personal API keys for MCP tool authentication.

    API keys enable programmatic access to the MCP server in LAN/WAN modes.
    Each key is scoped to a user and can have specific permissions.

    Security:
    - Keys are hashed using bcrypt before storage (never stored in plaintext)
    - key_prefix stores first 12 chars for display purposes only
    - Actual key is only returned once at creation time

    Multi-tenant isolation: API keys inherit tenant_key from their user.
    """

    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)

    # Foreign key to user
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Key details
    name = Column(String(255), nullable=False)  # Description/label
    key_hash = Column(String(255), nullable=False, unique=True, index=True)  # Hashed API key (bcrypt)
    key_prefix = Column(String(16), nullable=False)  # First 12 chars for display (e.g., "gk_abc12...")

    # Permissions (JSON array)
    permissions = Column(JSONB, nullable=False, default=list)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("idx_apikey_tenant", "tenant_key"),
        Index("idx_apikey_user", "user_id"),
        Index("idx_apikey_hash", "key_hash"),
        Index("idx_apikey_active", "is_active"),
        # GIN index for JSONB permissions (enables efficient permission queries)
        Index("idx_apikey_permissions_gin", "permissions", postgresql_using="gin"),
        # Ensure revoked_at is set when is_active=false
        CheckConstraint(
            "(is_active = true AND revoked_at IS NULL) OR (is_active = false)", name="ck_apikey_revoked_consistency"
        ),
    )

    def __repr__(self):
        return f"<APIKey(id={self.id}, name={self.name}, user_id={self.user_id}, active={self.is_active})>"

    @property
    def display_key(self) -> str:
        """Get display-friendly version of key (prefix only)"""
        return f"{self.key_prefix}..."


class MCPSession(Base):
    """
    MCP Session model - tracks HTTP MCP sessions for stateful context preservation.

    Handover 0032: Enables pure MCP JSON-RPC 2.0 over HTTP with multi-tenant isolation.
    Sessions preserve tenant_key and project_id context across tool calls.

    Multi-tenant isolation: Sessions inherit tenant_key from API key's user.
    Session cleanup: Inactive sessions auto-expire after 24 hours.
    """

    __tablename__ = "mcp_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), unique=True, nullable=False, default=generate_uuid, index=True)

    # Foreign keys
    api_key_id = Column(String(36), ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    tenant_key = Column(String(36), nullable=False, index=True)

    # SECURITY: User ID for audit trail (Handover 0424 Phase 0)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Context preservation
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    # Session data (JSONB for performance)
    session_data = Column(
        JSONB, nullable=False, default=dict, comment="MCP protocol state: client_info, capabilities, tool_call_history"
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    api_key = relationship("APIKey", backref="mcp_sessions")
    project = relationship("Project", backref="mcp_sessions")
    user = relationship("User", backref="mcp_sessions")  # Handover 0424: Audit trail

    __table_args__ = (
        Index("idx_mcp_session_api_key", "api_key_id"),
        Index("idx_mcp_session_tenant", "tenant_key"),
        Index("idx_mcp_session_user", "user_id"),  # Handover 0424: Audit queries
        Index("idx_mcp_session_last_accessed", "last_accessed"),
        Index("idx_mcp_session_expires", "expires_at"),
        # Composite index for session cleanup queries
        Index("idx_mcp_session_cleanup", "expires_at", "last_accessed"),
        # GIN index for session_data (enables efficient JSON queries)
        Index("idx_mcp_session_data_gin", "session_data", postgresql_using="gin"),
    )

    def __repr__(self):
        return f"<MCPSession(id={self.id}, session_id={self.session_id}, tenant_key={self.tenant_key})>"

    @property
    def is_expired(self) -> bool:
        """Check if session has expired"""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def extend_expiration(self, hours: int = 24) -> None:
        """Extend session expiration by specified hours"""
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        self.last_accessed = datetime.now(timezone.utc)
