"""
Agent-related models for GiljoAI MCP.

This module contains models for agent jobs, interactions, and job tracking.
These models support the agentic orchestration system.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class MCPAgentJob(Base):
    """
    MCP Agent Job model - tracks agent jobs separately from user tasks.

    Handover 0017: Enables agent-to-agent job coordination for agentic orchestration.
    Handover 0073: Enhanced with progress tracking, tool assignment, and expanded status states.
    Handover 0080: Orchestrator succession architecture for unlimited project duration.
    Handover 0225: Performance indexes for status board queries (last_progress_at, health_status, composite).
    Separate from Task model which tracks user-facing work items.

    Multi-tenant isolation: All queries filter by tenant_key.

    Message Tracking (Auto-implemented):
    - messages (JSONB): Message array with status tracking
      - Status transition: "pending" (unread) → "acknowledged" (read)
      - Auto-tracking: read_mcp_messages() marks messages as acknowledged
    - last_message_check_at (DateTime): Auto-updated when agent reads messages

    Progress Tracking:
    - last_progress_at (DateTime): Updated by agents reporting progress
    - progress (Integer, 0-100): Job completion percentage
    - current_task (Text): Current task description

    Health Monitoring:
    - health_status (String): unknown, healthy, warning, critical, timeout
    - last_health_check (DateTime): Last health check timestamp
    - health_failure_count (Integer): Consecutive health check failures

    Status Board Optimizations:
    - Indexed fields: last_progress_at, health_status
    - Composite index: (project_id, status, last_progress_at)
    - Enables fast sorting/filtering for table view

    See: agent_messaging.py for message auto-tracking implementation
    """

    __tablename__ = "mcp_agent_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_key = Column(String(36), nullable=False, index=True)
    project_id = Column(
        String(36),
        ForeignKey("projects.id"),
        nullable=True,
        index=True,
        comment="Project ID this job belongs to (Handover 0062)",
    )  # nullable=True for backward compat
    job_id = Column(String(36), unique=True, nullable=False, default=generate_uuid)
    agent_type = Column(
        String(100), nullable=False, comment="Agent type: orchestrator, analyzer, implementer, tester, etc."
    )
    mission = Column(Text, nullable=False, comment="Agent mission/instructions")

    # Handover 0073: Expanded status states
    # Handover 0107: Added 'cancelling' state for graceful cancellation
    # Handover 0113: Simplified to 7 states (waiting, working, blocked, complete, failed, cancelled, decommissioned)
    status = Column(String(50), default="waiting", nullable=False)
    failure_reason = Column(
        String(50), nullable=True, comment="Reason for failure: error, timeout, system_error (Handover 0113)"
    )

    spawned_by = Column(String(36), nullable=True, comment="Agent ID that spawned this job")
    context_chunks = Column(JSON, default=list, comment="Array of chunk_ids from mcp_context_index for context loading")
    messages = Column(JSONB, default=list, comment="Array of message objects for agent communication")
    acknowledged = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Handover 0073: Progress tracking columns
    progress = Column(Integer, default=0, nullable=False, comment="Job completion progress (0-100%)")
    block_reason = Column(Text, nullable=True, comment="Explanation of why job is blocked (NULL if not blocked)")
    current_task = Column(Text, nullable=True, comment="Description of current task being executed")
    estimated_completion = Column(DateTime(timezone=True), nullable=True, comment="Estimated completion timestamp")

    # Handover 0073: Tool assignment columns
    tool_type = Column(
        String(20),
        default="universal",
        nullable=False,
        comment="AI coding tool assigned to this agent job (claude-code, codex, gemini, universal)",
    )
    agent_name = Column(
        String(255), nullable=True, comment="Human-readable agent display name (e.g., Backend Agent, Database Agent)"
    )

    # Handover 0080: Orchestrator succession architecture
    instance_number = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Sequential instance number for orchestrator succession (1, 2, 3, ...)",
    )
    handover_to = Column(String(36), nullable=True, comment="UUID of successor orchestrator job (NULL if no handover)")
    handover_summary = Column(JSONB, nullable=True, comment="Compressed state transfer for successor orchestrator")
    handover_context_refs = Column(
        JSON, default=list, comment="Array of context chunk IDs referenced in handover summary"
    )
    succession_reason = Column(
        String(100), nullable=True, comment="Reason for succession: 'context_limit', 'manual', 'phase_transition'"
    )
    context_used = Column(Integer, default=0, nullable=False, comment="Current context window usage in tokens")
    context_budget = Column(Integer, default=150000, nullable=False, comment="Maximum context window budget in tokens")

    # Handover 0088: Thin client architecture metadata
    job_metadata = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="JSONB metadata for thin client architecture (Handover 0088). Stores field_priorities, user_id, tool, etc.",
    )

    # Handover 0106: Health monitoring fields
    last_health_check = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last health check scan"
    )
    health_status = Column(
        String(20),
        default="unknown",
        nullable=False,
        comment="Health state: unknown, healthy, warning, critical, timeout"
    )
    health_failure_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Consecutive health check failures"
    )

    # Handover 0107: Agent activity tracking fields
    last_progress_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last progress update from agent (Handover 0107)"
    )
    last_message_check_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last message queue check (Handover 0107)"
    )

    # Handover 0113: Project closeout workflow
    decommissioned_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when agent job was decommissioned (Handover 0113)"
    )

    # Handover 0233: Mission tracking fields (job lifecycle checkpoints)
    mission_read_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when agent first read mission via get_orchestrator_instructions() (Handover 0233)"
    )
    mission_acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when agent acknowledged mission via status transition to 'working' (Handover 0233)"
    )

    # Relationships (Handover 0062)
    project = relationship("Project", back_populates="agent_jobs")

    __table_args__ = (
        Index("idx_mcp_agent_jobs_tenant_status", "tenant_key", "status"),
        Index("idx_mcp_agent_jobs_tenant_type", "tenant_key", "agent_type"),
        Index("idx_mcp_agent_jobs_job_id", "job_id"),
        Index("idx_mcp_agent_jobs_project", "project_id"),  # Handover 0062
        Index("idx_mcp_agent_jobs_tenant_project", "tenant_key", "project_id"),  # Handover 0062
        Index("idx_mcp_agent_jobs_tenant_tool", "tenant_key", "tool_type"),  # Handover 0073
        # Handover 0080: Succession indexes
        Index("idx_agent_jobs_instance", "project_id", "agent_type", "instance_number"),
        Index("idx_agent_jobs_handover", "handover_to"),
        # Handover 0225: Performance indexes for status board queries
        Index("idx_mcp_agent_jobs_last_progress", "last_progress_at"),
        Index("idx_mcp_agent_jobs_health_status", "health_status"),
        Index("idx_mcp_agent_jobs_composite_status", "project_id", "status", "last_progress_at"),
        CheckConstraint(
            "status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned')",
            name="ck_mcp_agent_job_status",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_mcp_agent_job_progress_range"),
        # Handover 0113: Failure reason constraint
        CheckConstraint(
            "failure_reason IS NULL OR failure_reason IN ('error', 'timeout', 'system_error')",
            name="ck_mcp_agent_job_failure_reason",
        ),
        CheckConstraint(
            "tool_type IN ('claude-code', 'codex', 'gemini', 'universal')", name="ck_mcp_agent_job_tool_type"
        ),
        # Handover 0080: Succession constraints
        CheckConstraint("instance_number >= 1", name="ck_mcp_agent_job_instance_positive"),
        CheckConstraint(
            "succession_reason IS NULL OR succession_reason IN ('context_limit', 'manual', 'phase_transition')",
            name="ck_mcp_agent_job_succession_reason",
        ),
        CheckConstraint("context_used >= 0 AND context_used <= context_budget", name="ck_mcp_agent_job_context_usage"),
        # Handover 0106: Health monitoring constraints
        CheckConstraint(
            "health_status IN ('unknown', 'healthy', 'warning', 'critical', 'timeout')",
            name="ck_mcp_agent_job_health_status"
        ),
        CheckConstraint("health_failure_count >= 0", name="ck_mcp_agent_job_health_failure_count"),
    )

    def __repr__(self):
        return f"<MCPAgentJob(id={self.id}, job_id={self.job_id}, agent_type={self.agent_type}, status={self.status}, progress={self.progress}%, instance={self.instance_number})>"


class AgentInteraction(Base):
    """
    Agent Interaction model - tracks sub-agent spawning and completion.
    Enables hybrid orchestration with Claude Code's native sub-agent capabilities.
    """

    __tablename__ = "agent_interactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
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
    # parent_agent relationship removed (Handover 0116) - Agent model eliminated

    __table_args__ = (
        Index("idx_interaction_tenant", "tenant_key"),
        Index("idx_interaction_project", "project_id"),
        Index("idx_interaction_type", "interaction_type"),
        Index("idx_interaction_created", "created_at"),
        CheckConstraint(
            "interaction_type IN ('SPAWN', 'COMPLETE', 'ERROR')",
            name="ck_interaction_type",
        ),
    )


class Job(Base):
    """
    Job model - tracks assigned work for agents.
    Jobs contain tasks and define scope boundaries.
    """

    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    job_type = Column(String(100), nullable=False)
    status = Column(String(50), default="active")  # active, completed, cancelled
    tasks = Column(JSON, default=list)  # List of task descriptions
    scope_boundary = Column(Text, nullable=True)
    vision_alignment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    meta_data = Column(JSON, default=dict)

    # Relationships removed (Handover 0116) - Agent model eliminated

    __table_args__ = (
        Index("idx_job_tenant", "tenant_key"),
        Index("idx_job_status", "status"),
    )
