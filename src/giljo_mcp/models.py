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
    ForeignKey, JSON, Index, UniqueConstraint, CheckConstraint
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