"""
Agent Identity Models - AgentJob and AgentExecution.

Handover 0366a: Separates work order (job) from executor (execution).

Design Philosophy:
- AgentJob: Persistent work order (mission, scope, goals) - WHAT
- AgentExecution: Executor instance (who's working, when, status) - WHO
- Succession: New execution, SAME job (job_id persists)

Semantic Clarity:
- job_id = The work to be done (persistent across succession)
- agent_id = The executor doing the work (changes on succession)

Example Succession Flow:
1. Job created: job_id="build-auth", mission="Build OAuth2 system"
2. Execution 1: agent_id="orch-001", job_id="build-auth", instance=1
3. Succession: agent_id="orch-002", job_id="build-auth", instance=2 (NEW executor, SAME job)

Data Normalization:
- Mission stored ONCE in AgentJob (no duplication)
- All executions reference the same job via foreign key
- Progress/status tracked per execution (executor-specific)
"""

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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class AgentJob(Base):
    """
    Persistent work order - survives agent succession.

    Represents the WHAT (mission, scope, objectives).
    Does NOT change when agents hand over to successors.

    Handover 0366a: Extracted from MCPAgentJob to separate concerns.

    Relationships:
    - executions: One job → Many executions (succession history)
    - project: Many jobs → One project

    Multi-tenant Isolation:
    - All queries MUST filter by tenant_key
    - Indexes include tenant_key for performance
    """

    __tablename__ = "agent_jobs"

    job_id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(50), nullable=False, index=True)
    project_id = Column(
        String(36),
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
        comment="Project this job belongs to (Handover 0062)",
    )

    # Job definition (stored ONCE, not duplicated across executions)
    mission = Column(Text, nullable=False, comment="Agent mission/instructions")
    job_type = Column(
        String(100),
        nullable=False,
        comment="Job type: orchestrator, analyzer, implementer, tester, etc.",
    )

    # Job lifecycle
    status = Column(
        String(50),
        default="active",
        nullable=False,
        comment="Job status: active, completed, cancelled",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata (job-level configuration)
    job_metadata = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Job-level metadata (field priorities, depth config, etc.)",
    )

    # Template reference (optional)
    template_id = Column(
        String(36),
        ForeignKey("agent_templates.id"),
        nullable=True,
        comment="Template used to create this job (if any)",
    )

    # Relationships
    project = relationship("Project", back_populates="agent_jobs_v2")
    executions = relationship(
        "AgentExecution",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="AgentExecution.instance_number",
    )
    todo_items = relationship(
        "AgentTodoItem",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="AgentTodoItem.sequence",
    )

    __table_args__ = (
        Index("idx_agent_jobs_tenant", "tenant_key"),
        Index("idx_agent_jobs_project", "project_id"),
        Index("idx_agent_jobs_tenant_project", "tenant_key", "project_id"),
        Index("idx_agent_jobs_status", "status"),
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')", name="ck_agent_job_status"
        ),
    )

    def __repr__(self):
        return f"<AgentJob(job_id={self.job_id}, job_type={self.job_type}, status={self.status})>"


class AgentExecution(Base):
    """
    Executor instance - represents an active agent.

    Represents the WHO (which agent instance is executing).

    Handover 0461b DEPRECATION NOTICE:
    The following columns are deprecated and will be removed in v4.0:
    - instance_number: Use single instance per agent

    NOTE: The `messages` JSONB column is also DEPRECATED (Handover 0387i).
    Use `messages_sent_count`, `messages_waiting_count`, `messages_read_count` instead.

    Relationships:
    - job: Many executions → One job (work order)
    - spawned_by: Points to parent agent_id (who spawned this executor) - STILL ACTIVE

    Multi-tenant Isolation:
    - All queries MUST filter by tenant_key
    """

    __tablename__ = "agent_executions"

    # Primary key: Internal UUID for database integrity (Handover 0429)
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Agent identity: Same agent_id can have multiple instances (succession)
    agent_id = Column(String(36), nullable=False, index=True, default=generate_uuid)
    job_id = Column(
        String(36),
        ForeignKey("agent_jobs.job_id"),
        nullable=False,
        index=True,
        comment="Foreign key to parent AgentJob",
    )
    tenant_key = Column(String(50), nullable=False, index=True)

    # Executor identity
    agent_display_name = Column(
        String(100),
        nullable=False,
        comment="Human-readable display name for UI",
    )
    instance_number = Column(
        Integer,
        default=1,
        nullable=False,
        comment="DEPRECATED (Handover 0461b): Will be removed in v4.0. Use single instance per agent.",
    )

    # Execution lifecycle
    status = Column(
        String(50),
        default="waiting",
        nullable=False,
        comment="Execution status: waiting, working, blocked, complete, failed, cancelled",
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Succession tracking (points to OTHER executions via agent_id)
    spawned_by = Column(
        String(36),
        nullable=True,
        comment="Agent ID of parent executor (clear: agent, not job)",
    )

    # Progress tracking
    progress = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Execution completion progress (0-100%)",
    )
    current_task = Column(Text, nullable=True, comment="Description of current task")
    block_reason = Column(
        Text,
        nullable=True,
        comment="Explanation of why execution is blocked (NULL if not blocked)",
    )

    # Health monitoring
    health_status = Column(
        String(20),
        default="unknown",
        nullable=False,
        comment="Health state: unknown, healthy, warning, critical, timeout",
    )
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    health_failure_count = Column(Integer, default=0, nullable=False)

    # Activity tracking
    last_progress_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last progress update from agent",
    )
    last_message_check_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last message queue check",
    )
    mission_acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when agent first fetched mission",
    )

    # Tool assignment
    tool_type = Column(
        String(20),
        default="universal",
        nullable=False,
        comment="AI coding tool assigned (claude-code, codex, gemini, universal)",
    )

    # Context tracking (for orchestrator executions)
    context_used = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Current context window usage in tokens",
    )
    context_budget = Column(
        Integer,
        default=150000,
        nullable=False,
        comment="Maximum context window budget in tokens",
    )

    # DEPRECATED (Handover 0387i): This column is no longer used.
    # Message counter columns (Handover 0387e - AUTHORITATIVE)
    # Note: JSONB messages column removed in Handover 0700c
    messages_sent_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Count of outbound messages sent by this agent",
    )
    messages_waiting_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Count of inbound messages waiting to be read",
    )
    messages_read_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Count of inbound messages that have been acknowledged/read",
    )

    # Failure tracking
    failure_reason = Column(
        String(50),
        nullable=True,
        comment="Reason for failure: error, timeout, system_error (Handover 0113)",
    )

    # Display name (optional)
    agent_name = Column(
        String(255),
        nullable=True,
        comment="Human-readable display name for UI",
    )

    # Relationships
    job = relationship("AgentJob", back_populates="executions")

    __table_args__ = (
        Index("idx_agent_executions_tenant", "tenant_key"),
        Index("idx_agent_executions_job", "job_id"),
        Index("idx_agent_executions_tenant_job", "tenant_key", "job_id"),
        Index("idx_agent_executions_status", "status"),
        Index("idx_agent_executions_instance", "job_id", "instance_number"),
        Index("idx_agent_executions_health", "health_status"),
        Index("idx_agent_executions_last_progress", "last_progress_at"),
        # Handover 0429: Allow same agent_id with different instance_number (succession)
        UniqueConstraint("agent_id", "instance_number", name="uq_agent_instance"),
        CheckConstraint(
            "status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned')",
            name="ck_agent_execution_status",
        ),
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ck_agent_execution_progress_range",
        ),
        CheckConstraint(
            "instance_number >= 1", name="ck_agent_execution_instance_positive"
        ),
        CheckConstraint(
            "tool_type IN ('claude-code', 'codex', 'gemini', 'universal')",
            name="ck_agent_execution_tool_type",
        ),
        CheckConstraint(
            "health_status IN ('unknown', 'healthy', 'warning', 'critical', 'timeout')",
            name="ck_agent_execution_health_status",
        ),
        CheckConstraint(
            "context_used >= 0 AND context_used <= context_budget",
            name="ck_agent_execution_context_usage",
        ),
    )

    def __repr__(self):
        return (
            f"<AgentExecution(agent_id={self.agent_id}, job_id={self.job_id}, "
            f"agent_display_name={self.agent_display_name}, status={self.status}, instance={self.instance_number})>"
        )


class AgentTodoItem(Base):
    """
    Agent TODO item - tracks individual tasks within an agent job.

    Handover 0402: Replaces JSONB storage with proper relational table.

    Purpose:
    - Store agent TODO items as structured data for UI display
    - Enable real-time updates via WebSocket when items change
    - Support progress tracking with status indicators

    Relationships:
    - job: Many items → One job (work order)

    Multi-tenant Isolation:
    - All queries MUST filter by tenant_key
    - Composite indexes for (job_id, sequence) queries
    """

    __tablename__ = "agent_todo_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(
        String(36),
        ForeignKey("agent_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to parent AgentJob",
    )
    tenant_key = Column(String(64), nullable=False, index=True)

    # TODO item details
    content = Column(
        String(255),
        nullable=False,
        comment="TODO item description/task text",
    )
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="Item status: pending, in_progress, completed",
    )
    sequence = Column(
        Integer,
        nullable=False,
        comment="Display order (0-based index in agent's TODO list)",
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    job = relationship("AgentJob", back_populates="todo_items")

    __table_args__ = (
        Index("idx_todo_items_job", "job_id"),
        Index("idx_todo_items_tenant_status", "tenant_key", "status"),
        Index("idx_todo_items_job_sequence", "job_id", "sequence"),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')",
            name="ck_agent_todo_item_status",
        ),
        CheckConstraint(
            "sequence >= 0",
            name="ck_agent_todo_item_sequence_positive",
        ),
    )

    def __repr__(self):
        return (
            f"<AgentTodoItem(id={self.id}, job_id={self.job_id}, "
            f"content={self.content[:30]}..., status={self.status}, sequence={self.sequence})>"
        )
