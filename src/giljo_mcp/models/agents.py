"""
Agent-related models for GiljoAI MCP.

This module contains models for agent jobs, interactions, and job tracking.
These models support the agentic orchestration system.
"""

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


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

    def __repr__(self) -> str:
        return (
            f"<AgentInteraction(id={self.id}, sub_agent_name='{self.sub_agent_name}', type='{self.interaction_type}')>"
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

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, job_type='{self.job_type}', status='{self.status}')>"
