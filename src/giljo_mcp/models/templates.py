"""
Agent template-related models for GiljoAI MCP.

This module contains models for agent templates, template archives,
augmentations, and usage statistics. These models support template management
and version control for agent missions.
"""

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class AgentTemplate(Base):
    """
    Agent Template model - stores reusable agent mission templates.
    Templates are scoped by tenant_key/product_id for multi-tenant isolation.
    Supports variable substitution and runtime augmentation.
    """

    __tablename__ = "agent_templates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    product_id = Column(String(36), nullable=True)  # Product-level scope

    # Template identification
    name = Column(String(100), nullable=False)  # e.g., "orchestrator", "analyzer"
    # Default category is "role" for backward compatibility with older tests
    # and data that did not explicitly set a category.
    category = Column(
        String(50),
        nullable=False,
        default="role",
        server_default="role",
    )  # 'role', 'project_type', 'custom'
    role = Column(String(50), nullable=True)  # AgentRole enum value
    project_type = Column(String(50), nullable=True)  # ProjectType enum value

    # Template content (Handover 0106: Dual-field system)
    system_instructions = Column(
        Text,
        nullable=False,
        default="",
        comment="Protected MCP coordination instructions (non-editable by users)",
    )
    user_instructions = Column(
        Text,
        nullable=True,
        comment="User-customizable role-specific guidance (editable)",
    )
    template_content = Column(
        Text,
        nullable=False,
        comment="DEPRECATED (v3.1): Use system_instructions + user_instructions. Kept for backward compatibility.",
    )  # Template with {variable} placeholders
    variables = Column(JSON, default=list)  # List of required variables
    behavioral_rules = Column(JSON, default=list)  # Role-specific rules
    success_criteria = Column(JSON, default=list)  # Success metrics

    # Tool assignment (Handover 0045 - Multi-Tool Agent Orchestration)
    tool = Column(String(50), nullable=False, default="claude", index=True)  # AI tool: claude, codex, gemini

    # Multi-CLI Tool Support (Handover 0103)
    cli_tool = Column(String(20), default="claude", nullable=False)  # CLI tool: claude, codex, gemini, generic
    background_color = Column(String(7))  # Hex color code for role visualization
    model = Column(String(20))  # Model selection: sonnet, opus, haiku, inherit
    tools = Column(String(50))  # Tool selection (null = inherit all)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    avg_generation_ms = Column(Float, nullable=True)  # Performance tracking

    # Export tracking (Handover 0335)
    last_exported_at = Column(DateTime(timezone=True), nullable=True)  # Timestamp of last export to CLI

    # Metadata
    description = Column(Text, nullable=True)
    version = Column(String(20), default="1.0.0")
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # One default per role
    tags = Column(JSON, default=list)
    meta_data = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String(100), nullable=True)

    # Relationships
    archives = relationship("TemplateArchive", back_populates="template", cascade="all, delete-orphan")
    usage_stats = relationship("TemplateUsageStats", back_populates="template", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("product_id", "name", "version", name="uq_template_product_name_version"),
        Index("idx_template_tenant", "tenant_key"),
        Index("idx_template_product", "product_id"),
        Index("idx_template_category", "category"),
        Index("idx_template_role", "role"),
        Index("idx_template_active", "is_active"),
        Index("idx_template_tool", "tool"),  # Handover 0045 - Tool-based filtering
    )

    @property
    def variable_list(self) -> list[str]:
        """Get list of variables in template"""
        import re

        return re.findall(r"\{(\w+)\}", self.template_content)

    @property
    def may_be_stale(self) -> bool:
        """
        Check if template may be stale (modified after last export).

        Returns True if template has been updated after the last export,
        indicating the exported CLI version may be outdated.

        Returns:
            bool: True if updated_at > last_exported_at, False otherwise
        """
        if self.updated_at is None or self.last_exported_at is None:
            return False

        return self.updated_at > self.last_exported_at


class TemplateArchive(Base):
    """
    Template Archive model - stores version history of templates.
    Auto-created when templates are modified for audit and rollback.
    """

    __tablename__ = "template_archives"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    template_id = Column(String(36), ForeignKey("agent_templates.id"), nullable=False)
    product_id = Column(String(36), nullable=True)

    # Archived template data (snapshot)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    role = Column(String(50), nullable=True)
    # Full system+user instructions snapshot for v3.1 dual-field support
    system_instructions = Column(Text, nullable=True)
    user_instructions = Column(Text, nullable=True)
    template_content = Column(Text, nullable=False)
    variables = Column(JSON, default=list)
    behavioral_rules = Column(JSON, default=list)
    success_criteria = Column(JSON, default=list)

    # Archive metadata
    version = Column(String(20), nullable=False)
    archive_reason = Column(String(255), nullable=True)
    archive_type = Column(String(20), default="manual")  # 'manual', 'auto', 'scheduled'
    archived_by = Column(String(100), nullable=True)
    archived_at = Column(DateTime(timezone=True), server_default=func.now())

    # Performance snapshot
    usage_count_at_archive = Column(Integer, nullable=True)
    avg_generation_ms_at_archive = Column(Float, nullable=True)

    # Restoration tracking
    is_restorable = Column(Boolean, default=True)
    restored_at = Column(DateTime(timezone=True), nullable=True)
    restored_by = Column(String(100), nullable=True)

    meta_data = Column(JSON, default=dict)

    # Relationships
    template = relationship("AgentTemplate", back_populates="archives")

    __table_args__ = (
        Index("idx_archive_tenant", "tenant_key"),
        Index("idx_archive_template", "template_id"),
        Index("idx_archive_product", "product_id"),
        Index("idx_archive_version", "version"),
        Index("idx_archive_date", "archived_at"),
    )


class TemplateUsageStats(Base):
    """
    Template Usage Stats model - tracks template usage for optimization and recommendations.
    Helps identify which templates are most effective and need optimization.
    """

    __tablename__ = "template_usage_stats"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    template_id = Column(String(36), ForeignKey("agent_templates.id"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)

    # Usage details
    used_at = Column(DateTime(timezone=True), server_default=func.now())
    generation_ms = Column(Integer, nullable=True)  # Time to generate
    variables_used = Column(JSON, default=dict)  # Actual variables substituted
    augmentations_applied = Column(JSON, default=list)  # List of augmentation IDs

    # Outcome tracking
    agent_completed = Column(Boolean, nullable=True)
    agent_success_rate = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)

    # Relationships
    template = relationship("AgentTemplate", back_populates="usage_stats")
    # agent relationship removed (Handover 0116) - Agent model eliminated
    project = relationship("Project", backref="template_usage_stats")

    __table_args__ = (
        Index("idx_usage_tenant", "tenant_key"),
        Index("idx_usage_template", "template_id"),
        Index("idx_usage_project", "project_id"),
        Index("idx_usage_date", "used_at"),
    )
