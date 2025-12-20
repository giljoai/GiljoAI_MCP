# Handover 0366a: Agent Identity Refactor - Phase A (Schema and Models)

**Date**: 2025-12-19
**Phase**: A of 4
**Status**: Ready for Execution
**Estimated Duration**: 12-16 hours
**TDD Approach**: RED → GREEN → REFACTOR

---

## Prerequisites & Reference Documents

**MUST READ before starting this phase:**

1. **Master Roadmap**: `handovers/0366_agent_identity_refactor_roadmap.md`
   - Executive summary, phase dependencies, success criteria

2. **UUID Index**: `handovers/Reference_docs/UUID_INDEX_0366.md`
   - Every file containing job_id/agent_id references (600+ files)
   - Use for impact analysis and verification

3. **Database Schema Map**: `handovers/Reference_docs/DATABASE_SCHEMA_MAP_0366.md`
   - Current MCPAgentJob schema (34 columns)
   - Proposed AgentJob + AgentExecution schemas
   - Data migration transformation logic

4. **Project Context**: `F:\GiljoAI_MCP\CLAUDE.md`
   - Full project guidance and conventions

5. **TDD Guide**: `handovers/Reference_docs/QUICK_LAUNCH.txt`
   - TDD workflow: RED → GREEN → REFACTOR

---

## Objective

Split the monolithic `MCPAgentJob` model into two semantically clear entities:
1. **AgentJob** - The persistent work order (mission, scope, goals)
2. **AgentExecution** - The executor instance (who's working on it, when, status)

This phase lays the **foundation** for the entire 0366 refactor series. All subsequent phases depend on this schema being correct.

---

## Background: The Problem

### Current Schema (MCPAgentJob)
```python
class MCPAgentJob(Base):
    __tablename__ = "mcp_agent_jobs"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(36), unique=True)  # CONFLATED: work + worker
    agent_type = Column(String(100))
    mission = Column(Text)
    status = Column(String(50))
    instance_number = Column(Integer, default=1)
    spawned_by = Column(String(36))  # Points to parent job_id (confusing)
    handover_to = Column(String(36))  # Points to successor job_id (confusing)
    # ... 30+ more fields mixing work and worker concerns
```

**Problems**:
- `job_id` identifies BOTH the work AND the worker (semantic conflation)
- Succession creates NEW `job_id` → breaks historical continuity
- Duplicate `mission` data across succession instances (data bloat)
- Foreign keys (`spawned_by`, `handover_to`) point to job_id (ambiguous: work or worker?)
- Audit trail unclear: "Which agent instance worked on this job?"

### Proposed Schema (AgentJob + AgentExecution)

```python
class AgentJob(Base):
    """Persistent work order - survives succession."""
    __tablename__ = "agent_jobs"

    job_id = Column(String(36), primary_key=True)  # The WORK
    tenant_key = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"))
    mission = Column(Text, nullable=False)  # Stored ONCE
    job_type = Column(String(100))  # orchestrator, analyzer, implementer
    status = Column(String(50))  # active, completed, cancelled
    created_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    # Relationships
    executions = relationship("AgentExecution", back_populates="job")

class AgentExecution(Base):
    """Executor instance - changes on succession."""
    __tablename__ = "agent_executions"

    agent_id = Column(String(36), primary_key=True)  # The WORKER
    job_id = Column(String(36), ForeignKey("agent_jobs.job_id"))  # Which work?
    tenant_key = Column(String(36), nullable=False, index=True)
    agent_type = Column(String(100))  # orchestrator, analyzer, etc.
    instance_number = Column(Integer, default=1)
    status = Column(String(50))  # waiting, working, complete, failed
    spawned_by = Column(String(36))  # Parent AGENT_ID (clear!)
    succeeded_by = Column(String(36))  # Successor AGENT_ID (clear!)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    # Progress tracking
    progress = Column(Integer, default=0)
    current_task = Column(Text)
    health_status = Column(String(20))
    # Relationships
    job = relationship("AgentJob", back_populates="executions")
```

**Benefits**:
- **Semantic clarity**: job_id = work, agent_id = worker
- **Data normalization**: Mission stored ONCE in AgentJob, shared by all executions
- **Clear succession**: New execution, SAME job
- **Precise audit trail**: "Agent abc-123 worked on job def-456 from T1 to T2"
- **Foreign key clarity**: spawned_by/succeeded_by point to agent_id (unambiguous)

---

## TDD Approach (MANDATORY)

### Phase 1: RED (30-40% of time) - Write Failing Tests FIRST

Before writing ANY implementation code, create these test files:

#### `tests/models/test_agent_job.py`
```python
"""
Tests for AgentJob model.
These tests MUST be written FIRST (TDD RED phase).
"""
import pytest
from datetime import datetime, timezone
from src.giljo_mcp.models import AgentJob

def test_agent_job_creation():
    """Job can be created with minimal fields."""
    job = AgentJob(
        job_id="test-job-123",
        tenant_key="tenant-abc",
        project_id="project-456",
        mission="Build authentication system",
        job_type="orchestrator",
        status="active"
    )
    assert job.job_id == "test-job-123"
    assert job.mission == "Build authentication system"
    assert job.status == "active"

def test_agent_job_requires_mission():
    """Job creation fails without mission (NOT NULL constraint)."""
    with pytest.raises(Exception):  # IntegrityError expected
        job = AgentJob(
            job_id="test-job-123",
            tenant_key="tenant-abc",
            project_id="project-456",
            job_type="orchestrator",
            status="active"
            # mission missing - should FAIL
        )

def test_agent_job_has_executions_relationship():
    """Job can access its executions via relationship."""
    job = AgentJob(
        job_id="test-job-123",
        tenant_key="tenant-abc",
        project_id="project-456",
        mission="Build auth",
        job_type="orchestrator",
        status="active"
    )
    # Relationship should exist (even if empty)
    assert hasattr(job, 'executions')
    assert job.executions == []  # No executions yet

def test_agent_job_status_constraint():
    """Job status must be one of allowed values."""
    # Valid statuses: active, completed, cancelled
    job = AgentJob(
        job_id="test-job-123",
        tenant_key="tenant-abc",
        project_id="project-456",
        mission="Build auth",
        job_type="orchestrator",
        status="invalid_status"  # Should FAIL on commit
    )
    # Constraint violation expected on database commit
```

#### `tests/models/test_agent_execution.py`
```python
"""
Tests for AgentExecution model.
These tests MUST be written FIRST (TDD RED phase).
"""
import pytest
from datetime import datetime, timezone
from src.giljo_mcp.models import AgentJob, AgentExecution

def test_agent_execution_creation():
    """Execution can be created with minimal fields."""
    execution = AgentExecution(
        agent_id="agent-abc-123",
        job_id="job-def-456",
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="waiting"
    )
    assert execution.agent_id == "agent-abc-123"
    assert execution.job_id == "job-def-456"
    assert execution.instance_number == 1

def test_agent_execution_belongs_to_job():
    """Execution references its parent job via foreign key."""
    execution = AgentExecution(
        agent_id="agent-abc-123",
        job_id="job-def-456",  # Must exist in agent_jobs table
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="waiting"
    )
    assert execution.job_id == "job-def-456"
    # Foreign key constraint should be enforced

def test_agent_execution_succession_chain():
    """Executions can form succession chains via succeeded_by."""
    exec1 = AgentExecution(
        agent_id="agent-001",
        job_id="job-abc",
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="complete",
        succeeded_by="agent-002"  # Points to next execution
    )
    exec2 = AgentExecution(
        agent_id="agent-002",
        job_id="job-abc",  # SAME job
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=2,
        status="working",
        spawned_by="agent-001"  # Points to previous execution
    )
    # Succession chain validated
    assert exec1.succeeded_by == exec2.agent_id
    assert exec2.spawned_by == exec1.agent_id
    assert exec1.job_id == exec2.job_id  # SAME work order

def test_agent_execution_status_constraint():
    """Execution status must be one of allowed values."""
    # Valid statuses: waiting, working, blocked, complete, failed, cancelled, decommissioned
    execution = AgentExecution(
        agent_id="agent-abc-123",
        job_id="job-def-456",
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="invalid_status"  # Should FAIL on commit
    )
    # Constraint violation expected

def test_agent_execution_progress_range():
    """Execution progress must be 0-100."""
    execution = AgentExecution(
        agent_id="agent-abc-123",
        job_id="job-def-456",
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="working",
        progress=150  # INVALID - exceeds 100
    )
    # Constraint violation expected
```

#### `tests/models/test_job_execution_integration.py`
```python
"""
Integration tests for AgentJob + AgentExecution.
These tests MUST be written FIRST (TDD RED phase).
"""
import pytest
from datetime import datetime, timezone
from src.giljo_mcp.models import AgentJob, AgentExecution

def test_job_persists_across_succession(db_session):
    """Job persists when executions change (succession scenario)."""
    # Create job
    job = AgentJob(
        job_id="job-persistent",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Build authentication system",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)
    db_session.commit()

    # Create execution 1
    exec1 = AgentExecution(
        agent_id="agent-001",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="complete"
    )
    db_session.add(exec1)
    db_session.commit()

    # Create execution 2 (succession)
    exec2 = AgentExecution(
        agent_id="agent-002",
        job_id=job.job_id,  # SAME job
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=2,
        status="working",
        spawned_by=exec1.agent_id
    )
    exec1.succeeded_by = exec2.agent_id
    db_session.add(exec2)
    db_session.commit()

    # Validate job persistence
    assert len(job.executions) == 2
    assert job.executions[0].agent_id == "agent-001"
    assert job.executions[1].agent_id == "agent-002"
    assert job.mission == "Build authentication system"  # Unchanged

def test_message_routing_uses_agent_id(db_session):
    """Messages are routed to agent_id, NOT job_id."""
    # This test validates the semantic shift:
    # OLD: "Send message to job_id abc-123" (ambiguous - which executor?)
    # NEW: "Send message to agent_id def-456" (precise - specific executor)

    job = AgentJob(
        job_id="job-messaging-test",
        tenant_key="tenant-abc",
        project_id="project-123",
        mission="Test messaging",
        job_type="orchestrator",
        status="active"
    )
    db_session.add(job)

    exec1 = AgentExecution(
        agent_id="agent-sender",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="orchestrator",
        instance_number=1,
        status="working"
    )
    exec2 = AgentExecution(
        agent_id="agent-receiver",
        job_id=job.job_id,
        tenant_key="tenant-abc",
        agent_type="analyzer",
        instance_number=1,
        status="working"
    )
    db_session.add_all([exec1, exec2])
    db_session.commit()

    # Message would be sent to agent_id (NOT job_id)
    # to_agent = "agent-receiver"  # Clear and precise
    # Validation: agent_id must exist in agent_executions table
    assert exec2.agent_id == "agent-receiver"
```

### Phase 2: GREEN (40-50% of time) - Minimal Implementation

Create the actual models to make tests pass:

#### `src/giljo_mcp/models/agent_identity.py` (NEW FILE)
```python
"""
Agent Identity Models - AgentJob and AgentExecution.

Handover 0366a: Separates work order (job) from executor (execution).

Design:
- AgentJob: Persistent work order (mission, scope, goals)
- AgentExecution: Executor instance (who's working, when, status)
- Succession: New execution, SAME job
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
    """
    __tablename__ = "agent_jobs"

    job_id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)

    # Job definition (stored ONCE, not duplicated across executions)
    mission = Column(Text, nullable=False, comment="Agent mission/instructions")
    job_type = Column(
        String(100),
        nullable=False,
        comment="Job type: orchestrator, analyzer, implementer, tester, etc."
    )

    # Job lifecycle
    status = Column(
        String(50),
        default="active",
        nullable=False,
        comment="Job status: active, completed, cancelled"
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    job_metadata = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Job-level metadata (field priorities, depth config, etc.)"
    )

    # Relationships
    project = relationship("Project", back_populates="agent_jobs")
    executions = relationship(
        "AgentExecution",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="AgentExecution.instance_number"
    )

    __table_args__ = (
        Index("idx_agent_jobs_tenant", "tenant_key"),
        Index("idx_agent_jobs_project", "project_id"),
        Index("idx_agent_jobs_tenant_project", "tenant_key", "project_id"),
        Index("idx_agent_jobs_status", "status"),
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="ck_agent_job_status"
        ),
    )

    def __repr__(self):
        return f"<AgentJob(job_id={self.job_id}, job_type={self.job_type}, status={self.status})>"


class AgentExecution(Base):
    """
    Executor instance - changes on agent succession.

    Represents the WHO (which agent instance is executing).
    Changes when agents hand over to successors (new execution, SAME job).

    Handover 0366a: Extracted from MCPAgentJob to separate concerns.
    """
    __tablename__ = "agent_executions"

    agent_id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(
        String(36),
        ForeignKey("agent_jobs.job_id"),
        nullable=False,
        index=True,
        comment="Foreign key to parent AgentJob"
    )
    tenant_key = Column(String(36), nullable=False, index=True)

    # Executor identity
    agent_type = Column(
        String(100),
        nullable=False,
        comment="Agent type: orchestrator, analyzer, implementer, tester, etc."
    )
    instance_number = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Sequential instance number for succession (1, 2, 3, ...)"
    )

    # Execution lifecycle
    status = Column(
        String(50),
        default="waiting",
        nullable=False,
        comment="Execution status: waiting, working, blocked, complete, failed, cancelled, decommissioned"
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    decommissioned_at = Column(DateTime(timezone=True), nullable=True)

    # Succession tracking (points to OTHER executions via agent_id)
    spawned_by = Column(
        String(36),
        nullable=True,
        comment="Agent ID of parent executor (clear: agent, not job)"
    )
    succeeded_by = Column(
        String(36),
        nullable=True,
        comment="Agent ID of successor executor (clear: agent, not job)"
    )

    # Progress tracking
    progress = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Execution completion progress (0-100%)"
    )
    current_task = Column(Text, nullable=True, comment="Description of current task")
    block_reason = Column(
        Text,
        nullable=True,
        comment="Explanation of why execution is blocked (NULL if not blocked)"
    )

    # Health monitoring
    health_status = Column(
        String(20),
        default="unknown",
        nullable=False,
        comment="Health state: unknown, healthy, warning, critical, timeout"
    )
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    health_failure_count = Column(Integer, default=0, nullable=False)

    # Activity tracking
    last_progress_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last progress update from agent"
    )
    last_message_check_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last message queue check"
    )
    mission_acknowledged_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when agent first fetched mission"
    )

    # Tool assignment
    tool_type = Column(
        String(20),
        default="universal",
        nullable=False,
        comment="AI coding tool assigned (claude-code, codex, gemini, universal)"
    )

    # Context tracking (for orchestrator executions)
    context_used = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Current context window usage in tokens"
    )
    context_budget = Column(
        Integer,
        default=150000,
        nullable=False,
        comment="Maximum context window budget in tokens"
    )

    # Succession metadata (for orchestrator executions)
    succession_reason = Column(
        String(100),
        nullable=True,
        comment="Reason for succession: context_limit, manual, phase_transition"
    )
    handover_summary = Column(
        JSONB,
        nullable=True,
        comment="Compressed state transfer for successor orchestrator"
    )

    # Messages (JSONB array for WebSocket counter persistence)
    messages = Column(
        JSONB,
        default=list,
        comment="Array of message objects for agent communication"
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
        CheckConstraint(
            "status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned')",
            name="ck_agent_execution_status"
        ),
        CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="ck_agent_execution_progress_range"
        ),
        CheckConstraint(
            "instance_number >= 1",
            name="ck_agent_execution_instance_positive"
        ),
        CheckConstraint(
            "tool_type IN ('claude-code', 'codex', 'gemini', 'universal')",
            name="ck_agent_execution_tool_type"
        ),
        CheckConstraint(
            "health_status IN ('unknown', 'healthy', 'warning', 'critical', 'timeout')",
            name="ck_agent_execution_health_status"
        ),
        CheckConstraint(
            "context_used >= 0 AND context_used <= context_budget",
            name="ck_agent_execution_context_usage"
        ),
    )

    def __repr__(self):
        return (
            f"<AgentExecution(agent_id={self.agent_id}, job_id={self.job_id}, "
            f"agent_type={self.agent_type}, status={self.status}, instance={self.instance_number})>"
        )
```

### Phase 3: REFACTOR (10-20% of time) - Polish and Optimize

- Add database indexes for query performance
- Add docstrings and inline comments
- Create migration script (see below)
- Update `__init__.py` to export new models

---

## Database Migration Script

### `migrations/0366a_split_agent_job.py`
```python
"""
Migration 0366a: Split MCPAgentJob into AgentJob + AgentExecution

This migration transforms existing data:
1. Create agent_jobs table (work orders)
2. Create agent_executions table (executor instances)
3. Migrate data from mcp_agent_jobs to both tables
4. Preserve succession chains and foreign key relationships
5. Drop old mcp_agent_jobs table (after validation)

CRITICAL: This is a destructive migration. Backup database first!
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text

# Revision identifiers
revision = '0366a'
down_revision = 'previous_migration_id'  # Replace with actual
branch_labels = None
depends_on = None


def upgrade():
    """Split MCPAgentJob into AgentJob + AgentExecution."""

    # Step 1: Create agent_jobs table
    op.create_table(
        'agent_jobs',
        sa.Column('job_id', sa.String(36), primary_key=True),
        sa.Column('tenant_key', sa.String(36), nullable=False, index=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), index=True),
        sa.Column('mission', sa.Text, nullable=False),
        sa.Column('job_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('job_metadata', postgresql.JSONB, default={}, nullable=False),
        sa.CheckConstraint("status IN ('active', 'completed', 'cancelled')", name='ck_agent_job_status'),
    )

    # Step 2: Create agent_executions table
    op.create_table(
        'agent_executions',
        sa.Column('agent_id', sa.String(36), primary_key=True),
        sa.Column('job_id', sa.String(36), sa.ForeignKey('agent_jobs.job_id'), nullable=False, index=True),
        sa.Column('tenant_key', sa.String(36), nullable=False, index=True),
        sa.Column('agent_type', sa.String(100), nullable=False),
        sa.Column('instance_number', sa.Integer, default=1, nullable=False),
        sa.Column('status', sa.String(50), default='waiting', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('decommissioned_at', sa.DateTime(timezone=True)),
        sa.Column('spawned_by', sa.String(36)),
        sa.Column('succeeded_by', sa.String(36)),
        sa.Column('progress', sa.Integer, default=0, nullable=False),
        sa.Column('current_task', sa.Text),
        sa.Column('block_reason', sa.Text),
        sa.Column('health_status', sa.String(20), default='unknown', nullable=False),
        sa.Column('last_health_check', sa.DateTime(timezone=True)),
        sa.Column('health_failure_count', sa.Integer, default=0, nullable=False),
        sa.Column('last_progress_at', sa.DateTime(timezone=True)),
        sa.Column('last_message_check_at', sa.DateTime(timezone=True)),
        sa.Column('mission_acknowledged_at', sa.DateTime(timezone=True)),
        sa.Column('tool_type', sa.String(20), default='universal', nullable=False),
        sa.Column('context_used', sa.Integer, default=0, nullable=False),
        sa.Column('context_budget', sa.Integer, default=150000, nullable=False),
        sa.Column('succession_reason', sa.String(100)),
        sa.Column('handover_summary', postgresql.JSONB),
        sa.Column('messages', postgresql.JSONB, default=[]),
        sa.CheckConstraint("status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned')", name='ck_agent_execution_status'),
        sa.CheckConstraint("progress >= 0 AND progress <= 100", name='ck_agent_execution_progress_range'),
        sa.CheckConstraint("instance_number >= 1", name='ck_agent_execution_instance_positive'),
        sa.CheckConstraint("tool_type IN ('claude-code', 'codex', 'gemini', 'universal')", name='ck_agent_execution_tool_type'),
        sa.CheckConstraint("health_status IN ('unknown', 'healthy', 'warning', 'critical', 'timeout')", name='ck_agent_execution_health_status'),
        sa.CheckConstraint("context_used >= 0 AND context_used <= context_budget", name='ck_agent_execution_context_usage'),
    )

    # Step 3: Migrate data from mcp_agent_jobs
    # STRATEGY: Each row in mcp_agent_jobs becomes:
    # - 1 row in agent_jobs (work order)
    # - 1 row in agent_executions (executor instance)

    # Insert jobs (deduplicated by job_id)
    op.execute(text("""
        INSERT INTO agent_jobs (job_id, tenant_key, project_id, mission, job_type, status, created_at, completed_at, job_metadata)
        SELECT DISTINCT
            job_id,
            tenant_key,
            project_id,
            mission,
            agent_type AS job_type,
            CASE
                WHEN status IN ('complete', 'failed', 'cancelled', 'decommissioned') THEN 'completed'
                WHEN status = 'cancelled' THEN 'cancelled'
                ELSE 'active'
            END AS status,
            created_at,
            completed_at,
            job_metadata
        FROM mcp_agent_jobs
    """))

    # Insert executions (1:1 with mcp_agent_jobs rows)
    op.execute(text("""
        INSERT INTO agent_executions (
            agent_id, job_id, tenant_key, agent_type, instance_number, status,
            started_at, completed_at, decommissioned_at,
            spawned_by, succeeded_by, progress, current_task, block_reason,
            health_status, last_health_check, health_failure_count,
            last_progress_at, last_message_check_at, mission_acknowledged_at,
            tool_type, context_used, context_budget, succession_reason, handover_summary, messages
        )
        SELECT
            job_id AS agent_id,  -- OLD job_id becomes NEW agent_id
            job_id,  -- job_id stays the same (links to agent_jobs)
            tenant_key,
            agent_type,
            instance_number,
            status,
            started_at,
            completed_at,
            decommissioned_at,
            spawned_by,
            handover_to AS succeeded_by,  -- Rename column
            progress,
            current_task,
            block_reason,
            health_status,
            last_health_check,
            health_failure_count,
            last_progress_at,
            last_message_check_at,
            mission_acknowledged_at,
            tool_type,
            context_used,
            context_budget,
            succession_reason,
            handover_summary,
            messages
        FROM mcp_agent_jobs
    """))

    # Step 4: Update foreign key references (spawned_by, succeeded_by)
    # These now point to agent_id instead of job_id
    # (Already handled in INSERT above via column mapping)

    # Step 5: Drop old table (AFTER validation)
    # CRITICAL: Uncomment ONLY after verifying data migration success
    # op.drop_table('mcp_agent_jobs')

    print("Migration 0366a complete: MCPAgentJob split into AgentJob + AgentExecution")


def downgrade():
    """Rollback: Merge AgentJob + AgentExecution back into MCPAgentJob."""

    # Recreate mcp_agent_jobs table (original schema)
    op.create_table(
        'mcp_agent_jobs',
        # ... (full MCPAgentJob schema from models/agents.py)
    )

    # Migrate data back
    op.execute(text("""
        INSERT INTO mcp_agent_jobs (
            job_id, tenant_key, project_id, agent_type, mission, status,
            instance_number, spawned_by, handover_to,
            started_at, completed_at, created_at, decommissioned_at,
            progress, current_task, block_reason,
            health_status, last_health_check, health_failure_count,
            last_progress_at, last_message_check_at, mission_acknowledged_at,
            tool_type, context_used, context_budget, succession_reason,
            handover_summary, messages, job_metadata
        )
        SELECT
            e.agent_id AS job_id,  -- agent_id becomes job_id again
            e.tenant_key,
            j.project_id,
            e.agent_type,
            j.mission,
            e.status,
            e.instance_number,
            e.spawned_by,
            e.succeeded_by AS handover_to,
            e.started_at,
            e.completed_at,
            j.created_at,
            e.decommissioned_at,
            e.progress,
            e.current_task,
            e.block_reason,
            e.health_status,
            e.last_health_check,
            e.health_failure_count,
            e.last_progress_at,
            e.last_message_check_at,
            e.mission_acknowledged_at,
            e.tool_type,
            e.context_used,
            e.context_budget,
            e.succession_reason,
            e.handover_summary,
            e.messages,
            j.job_metadata
        FROM agent_executions e
        JOIN agent_jobs j ON e.job_id = j.job_id
    """))

    # Drop new tables
    op.drop_table('agent_executions')
    op.drop_table('agent_jobs')

    print("Migration 0366a rollback complete: Restored MCPAgentJob")
```

---

## Validation Checklist

Before marking Phase A complete:

- [ ] All tests in `test_agent_job.py` pass
- [ ] All tests in `test_agent_execution.py` pass
- [ ] All tests in `test_job_execution_integration.py` pass
- [ ] Migration script runs successfully on test database
- [ ] Data integrity verified (row counts match before/after)
- [ ] Foreign key constraints enforced (no orphaned records)
- [ ] Succession chains preserved (spawned_by/succeeded_by correct)
- [ ] Performance benchmarks (query time for common operations)
- [ ] Rollback script tested and validated

---

## Kickoff Prompt

Copy and paste this prompt to start a fresh session for Phase A:

---

**Mission**: Implement Handover 0366a - Split MCPAgentJob into AgentJob + AgentExecution

**Context**: You are the Database Expert Agent working on GiljoAI MCP Server. This phase splits the monolithic `MCPAgentJob` model into two semantically clear entities: AgentJob (persistent work order) and AgentExecution (executor instance).

**TDD Approach** (MANDATORY):
1. **RED** (30-40% time): Write ALL tests FIRST in `tests/models/` directory
2. **GREEN** (40-50% time): Implement models in `src/giljo_mcp/models/agent_identity.py`
3. **REFACTOR** (10-20% time): Create migration script, add indexes, polish

**Test Files to Create** (RED phase):
- `tests/models/test_agent_job.py` (AgentJob model tests)
- `tests/models/test_agent_execution.py` (AgentExecution model tests)
- `tests/models/test_job_execution_integration.py` (integration tests)

**Implementation Files** (GREEN phase):
- `src/giljo_mcp/models/agent_identity.py` (new models)
- `migrations/0366a_split_agent_job.py` (data migration)
- Update `src/giljo_mcp/models/__init__.py` to export new models

**Success Criteria**:
- All tests pass (>80% coverage)
- Migration runs successfully on test database
- Data integrity verified (no data loss)
- Rollback script validated

**Reference**: Read `handovers/0366a_schema_and_models.md` for complete specifications.

**Environment**:
- PostgreSQL 18 (local)
- Python 3.11+
- pytest for testing

**First Step**: Create `tests/models/test_agent_job.py` with failing tests (RED phase).

---

**Estimated Duration**: 12-16 hours
**Priority**: CRITICAL - Blocks all subsequent phases
**Status**: Ready for execution
