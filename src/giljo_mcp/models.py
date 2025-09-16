"""
SQLAlchemy models for GiljoAI MCP with multi-tenant support.

All models include tenant_key for project isolation.
Supports both SQLite (local) and PostgreSQL (production).
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4
from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, Float,
    ForeignKey, JSON, Index, UniqueConstraint, CheckConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


def generate_uuid():
    """Generate a string UUID for cross-database compatibility."""
    return str(uuid4())


class Project(Base):
    """
    Project model - root entity for multi-tenant isolation.
    Each project has a unique tenant_key for complete data isolation.
    """
    __tablename__ = "projects"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, unique=True, default=generate_uuid)
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
    agents = relationship("Agent", back_populates="project", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
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
        if hasattr(self, 'sent_messages'):
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
    """
    __tablename__ = "tasks"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    product_id = Column(String(36), nullable=True)  # Product-level scope for task isolation
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    assigned_agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    parent_task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True)
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
    project = relationship("Project", back_populates="tasks")
    subtasks = relationship("Task", back_populates="parent_task", foreign_keys="Task.parent_task_id")
    parent_task = relationship("Task", back_populates="subtasks", remote_side=[id])
    
    __table_args__ = (
        Index("idx_task_tenant", "tenant_key"),
        Index("idx_task_product", "product_id"),
        Index("idx_task_project", "project_id"),
        Index("idx_task_status", "status"),
        Index("idx_task_priority", "priority"),
        Index("idx_task_assigned", "assigned_agent_id"),
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
            name="ck_interaction_type"
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
    def variable_list(self) -> List[str]:
        """Get list of variables in template"""
        import re
        return re.findall(r'\{(\w+)\}', self.template_content)


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
    branch = Column(String(100), default="main")    # Default branch name
    remote_name = Column(String(50), default="origin")  # Remote name
    
    # Authentication settings
    auth_method = Column(String(20), nullable=False)  # 'https', 'ssh', 'token'
    username = Column(String(100), nullable=True)    # For HTTPS auth
    password_encrypted = Column(Text, nullable=True)  # Encrypted password/token
    ssh_key_path = Column(String(500), nullable=True)  # Path to SSH private key
    ssh_key_encrypted = Column(Text, nullable=True)   # Encrypted SSH private key content
    
    # Auto-commit settings
    auto_commit = Column(Boolean, default=True)      # Enable auto-commit on project completion
    auto_push = Column(Boolean, default=False)       # Enable auto-push after commit
    commit_message_template = Column(Text, nullable=True)  # Template for commit messages
    
    # CI/CD webhook configuration
    webhook_url = Column(String(500), nullable=True)  # Webhook URL for CI/CD triggers
    webhook_secret = Column(String(255), nullable=True)  # Webhook secret for verification
    webhook_events = Column(JSON, default=list)      # List of events to trigger webhook
    
    # Git ignore and repository settings
    ignore_patterns = Column(JSON, default=list)     # Additional .gitignore patterns
    git_config_options = Column(JSON, default=dict)  # Custom git config options
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    last_commit_hash = Column(String(40), nullable=True)  # Last known commit hash
    last_push_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)         # Last error message
    
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
        CheckConstraint(
            "auth_method IN ('https', 'ssh', 'token')",
            name="ck_git_config_auth_method"
        ),
    )
    
    @property
    def is_configured(self) -> bool:
        """Check if git configuration is complete and valid"""
        if not self.repo_url or not self.auth_method:
            return False
        
        if self.auth_method == 'https' and not (self.username and self.password_encrypted):
            return False
        elif self.auth_method == 'ssh' and not (self.ssh_key_path or self.ssh_key_encrypted):
            return False
        elif self.auth_method == 'token' and not self.password_encrypted:
            return False
            
        return True
    
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
    files_changed = Column(JSON, default=list)       # List of file paths
    insertions = Column(Integer, default=0)          # Lines added
    deletions = Column(Integer, default=0)           # Lines deleted
    
    # Orchestrator context
    triggered_by = Column(String(50), nullable=True)  # 'auto_commit', 'manual', 'project_completion'
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    commit_type = Column(String(50), nullable=True)   # 'feature', 'fix', 'docs', 'refactor', etc.
    
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
            name="ck_git_commit_push_status"
        ),
    )
