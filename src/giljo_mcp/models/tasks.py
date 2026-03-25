"""
Task and message-related models for GiljoAI MCP.

This module contains models for tasks and inter-agent messages.
Tasks track work items across sessions, while messages handle agent communication.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Float,
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


class Task(Base):
    """
    Task model - work items tracked across sessions.
    Tasks can be assigned to agents and tracked through completion.

    Phase 4 Enhancement: User assignment support
    - created_by_user_id: User who created the task
    - assigned_to_user_id: User responsible for completing the task
    - Nullable fields for backward compatibility and MCP tool creation

    Handover 0072: Task Integration
    - project_id: Now nullable to support unassigned tasks
    - status: Added "converted" state for task-to-project conversions

    Handover 0433: Task Product Binding (Security Enhancement)
    - product_id: Now required (NOT NULL) for tenant isolation
    - All tasks must be bound to a product
    - Eliminates "unassigned tasks" vulnerability
    """

    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    org_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Organization for org-level tasks (Handover 0424)",
    )
    product_id = Column(
        String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )  # Product-level scope for task isolation (Handover 0433: Made required)
    project_id = Column(
        String(36), ForeignKey("projects.id"), nullable=True
    )  # Handover 0072: Nullable for unassigned tasks
    parent_task_id = Column(String(36), ForeignKey("tasks.id"), nullable=True)
    # Handover 0076: Removed assigned_agent_id field

    # Phase 4: User ownership (Handover 0076: removed assigned_to_user_id)
    created_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    # Phase 4: Task-to-project conversion tracking
    converted_to_project_id = Column(String(36), ForeignKey("projects.id"), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(String(50), default="pending")  # pending, in_progress, completed, blocked, cancelled, converted
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    estimated_effort = Column(Float, nullable=True)  # Hours
    actual_effort = Column(Float, nullable=True)  # Hours
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    product = relationship("Product", back_populates="tasks", foreign_keys=[product_id])
    project = relationship(
        "Project", back_populates="tasks", foreign_keys=[project_id]
    )  # Specify FK to avoid ambiguity with converted_to_project_id
    subtasks = relationship("Task", back_populates="parent_task", foreign_keys="Task.parent_task_id")
    parent_task = relationship("Task", back_populates="subtasks", remote_side="Task.id")

    # Phase 4: User relationships (Handover 0076: removed assigned_to_user)
    created_by_user = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_tasks")

    __table_args__ = (
        Index("idx_task_tenant", "tenant_key"),
        Index("idx_task_org_id", "org_id"),
        Index("idx_task_product", "product_id"),
        Index("idx_task_project", "project_id"),
        Index("idx_task_status", "status"),
        Index("idx_task_priority", "priority"),
        # Phase 4: User assignment indexes (Handover 0076: removed assignment indexes)
        Index("idx_task_created_by_user", "created_by_user_id"),
        Index("idx_task_tenant_created_user", "tenant_key", "created_by_user_id"),  # Composite for "Created by Me"
        Index("idx_task_converted_to_project", "converted_to_project_id"),  # Conversion tracking
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"


class Message(Base):
    """
    Message model - inter-agent communication with acknowledgment tracking.
    Supports broadcast, direct, and priority messages.
    """

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    to_agents = Column(JSONB, default=list)  # List of agent names
    message_type = Column(String(50), default="direct")  # direct, broadcast, system
    subject = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    priority = Column(String(20), default="normal")  # low, normal, high, critical
    status = Column(String(50), default="pending")  # pending, acknowledged, completed, failed
    acknowledged_by = Column(JSONB, default=list)  # Array of agent names that acknowledged
    completed_by = Column(JSONB, default=list)  # Array of agent names that completed
    result = Column(Text, nullable=True)  # Completion result for completed messages
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    meta_data = Column(JSONB, default=dict)

    # New fields for MessageQueue system
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    backoff_seconds = Column(Integer, default=60)
    circuit_breaker_status = Column(String(20), nullable=True)

    # Relationships
    project = relationship("Project", back_populates="messages")
    # sender relationship removed (Handover 0116) - Agent model eliminated

    __table_args__ = (
        Index("idx_message_tenant", "tenant_key"),
        Index("idx_message_project", "project_id"),
        Index("idx_message_status", "status"),
        Index("idx_message_priority", "priority"),
        Index("idx_message_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, subject='{self.subject}', status='{self.status}')>"
