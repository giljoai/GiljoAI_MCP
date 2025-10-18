"""
SQLAlchemy models for GiljoAI MCP with multi-tenant support.

All models include tenant_key for project isolation.
Supports PostgreSQL (production).
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Session, declarative_base, relationship
from sqlalchemy.sql import func


Base = declarative_base()


def generate_uuid():
    """Generate a string UUID for cross-database compatibility."""
    return str(uuid4())


class Product(Base):
    """
    Product model - TOP-level organizational unit.
    All projects, tasks, and agents belong to a product.

    Vision Storage (Handover 0017 - Hybrid Approach):
    - vision_path: File-based storage (existing workflow)
    - vision_document: Inline text storage (new agentic workflow)
    - vision_type: Source type ('file', 'inline', 'none')
    - chunked: Has vision been chunked into mcp_context_index
    """

    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Vision storage - Hybrid approach (file OR inline)
    vision_path = Column(String(500), nullable=True,
        comment="File path to vision document (file-based workflow)")
    vision_document = Column(Text, nullable=True,
        comment="Inline vision text (alternative to vision_path for agentic workflow)")
    vision_type = Column(String(20), default="none",
        comment="Vision source: 'file', 'inline', or 'none'")
    chunked = Column(Boolean, default=False,
        comment="Has vision been chunked into mcp_context_index for agentic RAG")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    meta_data = Column(JSON, default=dict)

    # Rich configuration data (JSONB for PostgreSQL performance)
    config_data = Column(
        JSONB,
        nullable=True,
        default=dict,
        comment="Rich project configuration: architecture, tech_stack, features, etc.",
    )

    # Relationships
    projects = relationship("Project", back_populates="product", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_product_tenant", "tenant_key"),
        Index("idx_product_name", "name"),
        Index("idx_product_config_data_gin", "config_data", postgresql_using="gin"),  # GIN index for JSONB
        CheckConstraint(
            "vision_type IN ('file', 'inline', 'none')",
            name="ck_product_vision_type"
        ),
    )

    @property
    def has_config_data(self) -> bool:
        """Check if product has config_data populated"""
        return bool(self.config_data and len(self.config_data) > 0)

    def get_config_field(self, field_path: str, default: Any = None) -> Any:
        """
        Get config field using dot notation (e.g., 'tech_stack.python')

        Args:
            field_path: Dot-separated path (e.g., 'architecture' or 'test_config.coverage')
            default: Default value if field not found

        Returns:
            Field value or default
        """
        if not self.config_data:
            return default

        keys = field_path.split(".")
        value = self.config_data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value


class Project(Base):
    """
    Project model - work initiatives with vision documents.
    Projects belong to a Product and can be created from Tasks.
    """

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)  # Projects belong to Products
    name = Column(String(255), nullable=False)
    mission = Column(Text, nullable=False)
    status = Column(String(50), default="active")  # active, paused, completed, archived
    context_budget = Column(Integer, default=150000)
    context_used = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    meta_data = Column(JSON, default=dict)

    # Relationships
    product = relationship("Product", back_populates="projects")
    agents = relationship("Agent", back_populates="project", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", foreign_keys="Task.project_id", back_populates="project", cascade="all, delete-orphan")  # Specify FK to avoid ambiguity
    sessions = relationship("Session", back_populates="project", cascade="all, delete-orphan")
    visions = relationship("Vision", back_populates="project", cascade="all, delete-orphan")
    context_indexes = relationship("ContextIndex", back_populates="project", cascade="all, delete-orphan")
    document_indexes = relationship("LargeDocumentIndex", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_project_tenant", "tenant_key"),
        Index("idx_project_status", "status"),
    )


class Agent(Base):
    """
    Agent model - represents an AI agent working on a project.
    Each agent belongs to exactly one project (multi-tenant).
    """

    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)  # orchestrator, analyzer, implementer, tester, etc.
    status = Column(String(50), default="active")  # active, idle, working, decommissioned
    mission = Column(Text, nullable=True)
    context_used = Column(Integer, default=0)
    last_active = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    decommissioned_at = Column(DateTime(timezone=True), nullable=True)
    meta_data = Column(JSON, default=dict)

    # Relationships
    project = relationship("Project", back_populates="agents")
    sent_messages = relationship("Message", foreign_keys="Message.from_agent_id", back_populates="sender")
    jobs = relationship("Job", back_populates="agent", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_agent_project_name"),
        Index("idx_agent_tenant", "tenant_key"),
        Index("idx_agent_project", "project_id"),
        Index("idx_agent_status", "status"),
    )

    @property
    def message_count(self):
        """Get count of messages received by this agent"""
        # Count messages sent to this agent
        if hasattr(self, "sent_messages"):
            return len(self.sent_messages) if self.sent_messages else 0
        return 0


class Message(Base):
    """
    Message model - inter-agent communication with acknowledgment tracking.
    Supports broadcast, direct, and priority messages.
    """

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    from_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    to_agents = Column(JSON, default=list)  # List of agent names
    message_type = Column(String(50), default="direct")  # direct, broadcast, system
    subject = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    priority = Column(String(20), default="normal")  # low, normal, high, critical
    status = Column(String(50), default="pending")  # pending, acknowledged, completed, failed
    acknowledged_by = Column(JSON, default=list)  # Array of agent names that acknowledged
    completed_by = Column(JSON, default=list)  # Array of agent names that completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    meta_data = Column(JSON, default=dict)

    # New fields for MessageQueue system
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    backoff_seconds = Column(Integer, default=60)
    circuit_breaker_status = Column(String(20), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="messages")
    sender = relationship("Agent", foreign_keys=[from_agent_id], back_populates="sent_messages")

    __table_args__ = (
        Index("idx_message_tenant", "tenant_key"),
        Index("idx_message_project", "project_id"),
        Index("idx_message_status", "status"),
        Index("idx_message_priority", "priority"),
        Index("idx_message_created", "created_at"),
    )


class Task(Base):
    """
    Task model - work items tracked across sessions.
    Tasks can be assigned to agents and tracked through completion.

    Phase 4 Enhancement: User assignment support
    - created_by_user_id: User who created the task
    - assigned_to_user_id: User responsible for completing the task
    - Nullable fields for backward compatibility and MCP tool creation
    """

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)  # Product-level scope for task isolation
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    assigned_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    parent_task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True)

    # Phase 4: User ownership and assignment
    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    assigned_to_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    # Phase 4: Task-to-project conversion tracking
    converted_to_project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(String(50), default="pending")  # pending, in_progress, completed, blocked, cancelled
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    estimated_effort = Column(Float, nullable=True)  # Hours
    actual_effort = Column(Float, nullable=True)  # Hours
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    meta_data = Column(JSON, default=dict)

    # Relationships
    product = relationship("Product", back_populates="tasks", foreign_keys=[product_id])
    project = relationship("Project", back_populates="tasks", foreign_keys=[project_id])  # Specify FK to avoid ambiguity with converted_to_project_id
    subtasks = relationship("Task", back_populates="parent_task", foreign_keys="Task.parent_task_id")
    parent_task = relationship("Task", back_populates="subtasks", remote_side=[id])

    # Phase 4: User relationships
    created_by_user = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_tasks")
    assigned_to_user = relationship("User", foreign_keys=[assigned_to_user_id], back_populates="assigned_tasks")

    __table_args__ = (
        Index("idx_task_tenant", "tenant_key"),
        Index("idx_task_product", "product_id"),
        Index("idx_task_project", "project_id"),
        Index("idx_task_status", "status"),
        Index("idx_task_priority", "priority"),
        Index("idx_task_assigned", "assigned_agent_id"),
        # Phase 4: User assignment indexes for performance
        Index("idx_task_created_by_user", "created_by_user_id"),
        Index("idx_task_assigned_to_user", "assigned_to_user_id"),
        Index("idx_task_tenant_assigned_user", "tenant_key", "assigned_to_user_id"),  # Composite for "My Tasks"
        Index("idx_task_tenant_created_user", "tenant_key", "created_by_user_id"),  # Composite for "Created by Me"
        Index("idx_task_converted_to_project", "converted_to_project_id"),  # Conversion tracking
    )


class Session(Base):
    """
    Session model - tracks development sessions and their outcomes.
    Captures session context, decisions, and results.
    """

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    session_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    objectives = Column(Text, nullable=True)
    outcomes = Column(Text, nullable=True)
    decisions = Column(JSON, default=list)
    blockers = Column(JSON, default=list)
    next_steps = Column(JSON, default=list)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    meta_data = Column(JSON, default=dict)

    # Relationships
    project = relationship("Project", back_populates="sessions")

    __table_args__ = (
        UniqueConstraint("project_id", "session_number", name="uq_session_project_number"),
        Index("idx_session_tenant", "tenant_key"),
        Index("idx_session_project", "project_id"),
    )


class Vision(Base):
    """
    Vision model - stores product vision documents and chunks.
    Supports large documents through chunking (50K+ tokens).
    """

    __tablename__ = "visions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    document_name = Column(String(255), nullable=False)
    chunk_number = Column(Integer, default=1)
    total_chunks = Column(Integer, default=1)
    content = Column(Text, nullable=False)
    tokens = Column(Integer, nullable=True)
    version = Column(String(50), default="1.0.0")
    # New fields for enhanced chunking
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)
    boundary_type = Column(String(20), nullable=True)  # document, section, paragraph, line, sentence, word, forced
    keywords = Column(JSON, default=list)  # List of keywords extracted from chunk
    headers = Column(JSON, default=list)  # List of headers found in chunk
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    meta_data = Column(JSON, default=dict)

    # Relationships
    project = relationship("Project", back_populates="visions")

    __table_args__ = (
        UniqueConstraint("project_id", "document_name", "chunk_number", name="uq_vision_chunk"),
        Index("idx_vision_tenant", "tenant_key"),
        Index("idx_vision_project", "project_id"),
        Index("idx_vision_document", "document_name"),
    )


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


class ContextIndex(Base):
    """
    Context Index model - provides fast navigation for chunked documents.
    Enables O(1) chunk retrieval and document discovery.
    """

    __tablename__ = "context_index"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    index_type = Column(String(50), nullable=False)  # vision, document, session
    document_name = Column(String(255), nullable=False)
    section_name = Column(String(255), nullable=True)
    chunk_numbers = Column(JSON, default=list)  # Array of chunk numbers this appears in
    summary = Column(Text, nullable=True)
    token_count = Column(Integer, nullable=True)
    keywords = Column(JSON, default=list)  # Array of keywords
    full_path = Column(Text, nullable=True)
    content_hash = Column(String(32), nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="context_indexes")

    __table_args__ = (
        UniqueConstraint("project_id", "document_name", "section_name", name="uq_context_index"),
        Index("idx_context_tenant", "tenant_key"),
        Index("idx_context_type", "index_type"),
        Index("idx_context_doc", "document_name"),
    )


class LargeDocumentIndex(Base):
    """
    Large Document Index model - tracks documents requiring chunking.
    Provides metadata and navigation for documents over 50K tokens.
    """

    __tablename__ = "large_document_index"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    document_path = Column(Text, nullable=False)
    document_type = Column(String(50), nullable=True)  # markdown, yaml, text
    total_size = Column(Integer, nullable=True)  # Total characters
    total_tokens = Column(Integer, nullable=True)  # Estimated total tokens
    chunk_count = Column(Integer, nullable=True)
    meta_data = Column(JSON, default=dict)  # Changed from metadata to avoid SQLAlchemy conflict
    indexed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="document_indexes")

    __table_args__ = (
        UniqueConstraint("project_id", "document_path", name="uq_large_doc_path"),
        Index("idx_large_doc_tenant", "tenant_key"),
    )


class Job(Base):
    """
    Job model - tracks assigned work for agents.
    Jobs contain tasks and define scope boundaries.
    """

    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    job_type = Column(String(100), nullable=False)
    status = Column(String(50), default="active")  # active, completed, cancelled
    tasks = Column(JSON, default=list)  # List of task descriptions
    scope_boundary = Column(Text, nullable=True)
    vision_alignment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    meta_data = Column(JSON, default=dict)

    # Relationships
    agent = relationship("Agent", back_populates="jobs")

    __table_args__ = (
        Index("idx_job_tenant", "tenant_key"),
        Index("idx_job_agent", "agent_id"),
        Index("idx_job_status", "status"),
    )


class AgentInteraction(Base):
    """
    Agent Interaction model - tracks sub-agent spawning and completion.
    Enables hybrid orchestration with Claude Code's native sub-agent capabilities.
    """

    __tablename__ = "agent_interactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    parent_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    sub_agent_name = Column(String(100), nullable=False)
    interaction_type = Column(String(20), nullable=False)  # SPAWN, COMPLETE, ERROR
    mission = Column(Text, nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    meta_data = Column(JSON, default=dict)

    # Relationships
    project = relationship("Project", backref="agent_interactions")
    parent_agent = relationship("Agent", backref="sub_agent_interactions")

    __table_args__ = (
        Index("idx_interaction_tenant", "tenant_key"),
        Index("idx_interaction_project", "project_id"),
        Index("idx_interaction_parent", "parent_agent_id"),
        Index("idx_interaction_type", "interaction_type"),
        Index("idx_interaction_created", "created_at"),
        CheckConstraint(
            "interaction_type IN ('SPAWN', 'COMPLETE', 'ERROR')",
            name="ck_interaction_type",
        ),
    )


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
    category = Column(String(50), nullable=False)  # 'role', 'project_type', 'custom'
    role = Column(String(50), nullable=True)  # AgentRole enum value
    project_type = Column(String(50), nullable=True)  # ProjectType enum value

    # Template content
    template_content = Column(Text, nullable=False)  # Template with {variable} placeholders
    variables = Column(JSON, default=list)  # List of required variables
    behavioral_rules = Column(JSON, default=list)  # Role-specific rules
    success_criteria = Column(JSON, default=list)  # Success metrics
    preferred_tool = Column(String(50), default="claude")  # Preferred AI tool: claude, codex, gemini

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    avg_generation_ms = Column(Float, nullable=True)  # Performance tracking

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
    augmentations = relationship("TemplateAugmentation", back_populates="template", cascade="all, delete-orphan")
    usage_stats = relationship("TemplateUsageStats", back_populates="template", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("product_id", "name", "version", name="uq_template_product_name_version"),
        Index("idx_template_tenant", "tenant_key"),
        Index("idx_template_product", "product_id"),
        Index("idx_template_category", "category"),
        Index("idx_template_role", "role"),
        Index("idx_template_active", "is_active"),
    )

    @property
    def variable_list(self) -> list[str]:
        """Get list of variables in template"""
        import re

        return re.findall(r"\{(\w+)\}", self.template_content)


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


class TemplateAugmentation(Base):
    """
    Template Augmentation model - stores runtime modifications to templates.
    Allows task-specific customization without modifying base templates.
    """

    __tablename__ = "template_augmentations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    template_id = Column(String(36), ForeignKey("agent_templates.id"), nullable=False)

    # Augmentation details
    name = Column(String(100), nullable=False)
    augmentation_type = Column(String(50), nullable=False)  # 'append', 'prepend', 'replace', 'inject'
    target_section = Column(String(100), nullable=True)  # Which section to augment
    content = Column(Text, nullable=False)
    conditions = Column(JSON, default=dict)  # When to apply this augmentation
    priority = Column(Integer, default=0)  # Order of application

    # Usage
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    template = relationship("AgentTemplate", back_populates="augmentations")

    __table_args__ = (
        Index("idx_augment_tenant", "tenant_key"),
        Index("idx_augment_template", "template_id"),
        Index("idx_augment_active", "is_active"),
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
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
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
    agent = relationship("Agent", backref="template_usage_stats")
    project = relationship("Project", backref="template_usage_stats")

    __table_args__ = (
        Index("idx_usage_tenant", "tenant_key"),
        Index("idx_usage_template", "template_id"),
        Index("idx_usage_project", "project_id"),
        Index("idx_usage_date", "used_at"),
    )


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
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
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
    agent = relationship("Agent", backref="git_commits")

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

    # Default password tracking
    default_password_active = Column(Boolean, default=True, nullable=False, comment="True if default admin/admin password is still active")
    password_changed_at = Column(DateTime(timezone=True), nullable=True, comment="Timestamp when default password was changed")

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
            name="ck_database_initialized_at_required"
        ),
        # Regular indexes
        Index("idx_setup_tenant", "tenant_key"),  # Primary lookup index
        Index("idx_setup_database_initialized", "database_initialized"),  # Filter by database init status
        Index("idx_setup_mode", "install_mode"),  # Filter by installation mode
        # GIN indexes for JSONB columns (enables efficient queries on nested JSON)
        Index("idx_setup_features_gin", "features_configured", postgresql_using="gin"),
        Index("idx_setup_tools_gin", "tools_enabled", postgresql_using="gin"),
        # Partial index for incomplete database initialization (frequently queried)
        Index("idx_setup_database_incomplete", "tenant_key", "database_initialized", postgresql_where="database_initialized = false"),
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
            "database_initialized_at": self.database_initialized_at.isoformat() if self.database_initialized_at else None,
            "setup_version": self.setup_version,
            "database_version": self.database_version,
            "python_version": self.python_version,
            "node_version": self.node_version,
            "default_password_active": self.default_password_active,
            "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
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
    def get_by_tenant(cls, session: Session, tenant_key: str) -> Optional["SetupState"]:
        """
        Retrieve SetupState for a specific tenant.

        Args:
            session: SQLAlchemy session
            tenant_key: Tenant identifier

        Returns:
            SetupState instance or None if not found
        """
        return session.query(cls).filter(cls.tenant_key == tenant_key).first()

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

    def has_feature(self, feature_path: str) -> bool:
        """
        Check if a feature is configured.

        Supports nested paths using dot notation: "api.enabled"

        Args:
            feature_path: Dot-separated path to feature (e.g., "database" or "api.enabled")

        Returns:
            True if feature is configured and truthy, False otherwise
        """
        if not self.features_configured:
            return False

        keys = feature_path.split(".")
        value = self.features_configured

        for key in keys:
            if not isinstance(value, dict) or key not in value:
                return False
            value = value[key]

        return bool(value)

    def has_tool(self, tool_name: str) -> bool:
        """
        Check if an MCP tool is enabled.

        Args:
            tool_name: Name of the MCP tool

        Returns:
            True if tool is in tools_enabled list, False otherwise
        """
        return tool_name in (self.tools_enabled or [])


class User(Base):
    """
    User model - user accounts for authentication (LAN/WAN modes).

    Users are the primary authentication entity in LAN/WAN deployment modes.
    Each user can have multiple API keys for different applications/contexts.

    Phase 4 Enhancement: Task ownership and assignment tracking
    - created_tasks: Tasks created by this user
    - assigned_tasks: Tasks assigned to this user for completion

    Multi-tenant isolation: Users belong to a tenant_key namespace.
    """

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)

    # Credentials
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for system users (auto-login only)

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

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

    # Phase 4: Task relationships
    created_tasks = relationship("Task", foreign_keys="Task.created_by_user_id", back_populates="created_by_user")
    assigned_tasks = relationship("Task", foreign_keys="Task.assigned_to_user_id", back_populates="assigned_to_user")

    __table_args__ = (
        Index("idx_user_tenant", "tenant_key"),
        Index("idx_user_username", "username"),
        Index("idx_user_email", "email"),
        Index("idx_user_active", "is_active"),
        Index("idx_user_system", "is_system_user"),  # Index for system user queries
        CheckConstraint("role IN ('admin', 'developer', 'viewer')", name="ck_user_role"),
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
    
    # Context preservation
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    
    # Session data (JSONB for performance)
    session_data = Column(
        JSONB,
        nullable=False,
        default=dict,
        comment="MCP protocol state: client_info, capabilities, tool_call_history"
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_accessed = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    api_key = relationship("APIKey", backref="mcp_sessions")
    project = relationship("Project", backref="mcp_sessions")
    
    __table_args__ = (
        Index("idx_mcp_session_api_key", "api_key_id"),
        Index("idx_mcp_session_tenant", "tenant_key"),
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
        from datetime import timedelta
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        self.last_accessed = datetime.now(timezone.utc)


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
            name="ck_optimization_rule_operation_type"
        ),
        CheckConstraint("max_answer_chars > 0", name="ck_optimization_rule_max_chars"),
        CheckConstraint("priority >= 0", name="ck_optimization_rule_priority"),
    )
    
    def __repr__(self):
        return f"<OptimizationRule(id={self.id}, operation_type={self.operation_type}, tenant_key={self.tenant_key})>"


class OptimizationMetric(Base):
    """
    Optimization Metric model - tracks token savings from Serena MCP optimizations.
    
    Records every optimization operation to measure effectiveness and calculate savings.
    Enables performance analytics and optimization rule refinement.
    """
    
    __tablename__ = "optimization_metrics"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)
    
    # Foreign keys
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=False)
    
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
    
    # Relationships
    agent = relationship("Agent", backref="optimization_metrics")
    
    __table_args__ = (
        Index("idx_optimization_metric_tenant", "tenant_key"),
        Index("idx_optimization_metric_agent", "agent_id"),
        Index("idx_optimization_metric_type", "operation_type"),
        Index("idx_optimization_metric_date", "created_at"),
        Index("idx_optimization_metric_optimized", "optimized"),
        CheckConstraint(
            "operation_type IN ('file_read', 'symbol_search', 'symbol_replace', 'pattern_search', 'directory_list')",
            name="ck_optimization_metric_operation_type"
        ),
        CheckConstraint("params_size >= 0", name="ck_optimization_metric_params_size"),
        CheckConstraint("result_size >= 0", name="ck_optimization_metric_result_size"),
        CheckConstraint("tokens_saved >= 0", name="ck_optimization_metric_tokens_saved"),
    )
    
    def __repr__(self):
        return f"<OptimizationMetric(id={self.id}, operation_type={self.operation_type}, tokens_saved={self.tokens_saved})>"


class MCPContextIndex(Base):
    """
    MCP Context Index model - stores chunked vision documents for agentic RAG.
    
    Handover 0017: Enables full-text search on vision document chunks for token reduction.
    Chunks are created by EnhancedChunker from vision_document or vision_path content.
    
    Multi-tenant isolation: All queries filter by tenant_key.
    """
    
    __tablename__ = 'mcp_context_index'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_key = Column(String(36), nullable=False, index=True)
    chunk_id = Column(String(36), unique=True, nullable=False, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True,
        comment="Optional LLM-generated summary (NULL for Phase 1 non-LLM chunking)")
    keywords = Column(JSON, default=list,
        comment="Array of keyword strings extracted via regex or LLM")
    token_count = Column(Integer, nullable=True)
    chunk_order = Column(Integer, nullable=True,
        comment="Sequential chunk number for maintaining document order")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # PostgreSQL full-text search (requires pg_trgm extension)
    searchable_vector = Column(TSVECTOR, nullable=True,
        comment="Full-text search vector for fast keyword lookup")
    
    # Relationships
    product = relationship("Product", backref="context_chunks")
    
    __table_args__ = (
        Index("idx_mcp_context_tenant_product", "tenant_key", "product_id"),
        Index("idx_mcp_context_searchable", "searchable_vector", postgresql_using="gin"),
        Index("idx_mcp_context_chunk_id", "chunk_id"),
    )
    
    def __repr__(self):
        return f"<MCPContextIndex(id={self.id}, chunk_id={self.chunk_id}, product_id={self.product_id})>"


class MCPContextSummary(Base):
    """
    MCP Context Summary model - tracks orchestrator-created condensed missions.
    
    Handover 0017: Enables 70% token reduction by condensing full context into missions.
    Orchestrator creates condensed versions of vision chunks for agent spawning.
    
    Multi-tenant isolation: All queries filter by tenant_key.
    """
    
    __tablename__ = 'mcp_context_summary'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_key = Column(String(36), nullable=False, index=True)
    context_id = Column(String(36), unique=True, nullable=False, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
    full_content = Column(Text, nullable=False,
        comment="Original full context before condensation")
    condensed_mission = Column(Text, nullable=False,
        comment="Orchestrator-generated condensed mission")
    full_token_count = Column(Integer, nullable=True)
    condensed_token_count = Column(Integer, nullable=True)
    reduction_percent = Column(Float, nullable=True,
        comment="Token reduction percentage achieved")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", backref="context_summaries")
    
    __table_args__ = (
        Index("idx_mcp_summary_tenant_product", "tenant_key", "product_id"),
        Index("idx_mcp_summary_context_id", "context_id"),
    )
    
    def __repr__(self):
        return f"<MCPContextSummary(id={self.id}, context_id={self.context_id}, reduction={self.reduction_percent}%)>"


class MCPAgentJob(Base):
    """
    MCP Agent Job model - tracks agent jobs separately from user tasks.
    
    Handover 0017: Enables agent-to-agent job coordination for agentic orchestration.
    Separate from Task model which tracks user-facing work items.
    
    Multi-tenant isolation: All queries filter by tenant_key.
    """
    
    __tablename__ = 'mcp_agent_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_key = Column(String(36), nullable=False, index=True)
    job_id = Column(String(36), unique=True, nullable=False, default=generate_uuid)
    agent_type = Column(String(100), nullable=False,
        comment="Agent type: orchestrator, analyzer, implementer, tester, etc.")
    mission = Column(Text, nullable=False,
        comment="Agent mission/instructions")
    status = Column(String(50), default="pending", nullable=False)
    spawned_by = Column(String(36), nullable=True,
        comment="Agent ID that spawned this job")
    context_chunks = Column(JSON, default=list,
        comment="Array of chunk_ids from mcp_context_index for context loading")
    messages = Column(JSONB, default=list,
        comment="Array of message objects for agent communication")
    acknowledged = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index("idx_mcp_agent_jobs_tenant_status", "tenant_key", "status"),
        Index("idx_mcp_agent_jobs_tenant_type", "tenant_key", "agent_type"),
        Index("idx_mcp_agent_jobs_job_id", "job_id"),
        CheckConstraint(
            "status IN ('pending', 'active', 'completed', 'failed')",
            name="ck_mcp_agent_job_status"
        ),
    )
    
    def __repr__(self):
        return f"<MCPAgentJob(id={self.id}, job_id={self.job_id}, agent_type={self.agent_type}, status={self.status})>"
