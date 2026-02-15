"""
Tests for AgentExecution model (Handover 0366a).

RED Phase (TDD): These tests are written FIRST and will FAIL until the model is implemented.

AgentExecution represents the executor instance:
- Changes on agent succession (new execution, SAME job)
- Tracks executor-specific state (progress, health, context usage)
- Forms succession chains via spawned_by/succeeded_by
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# These imports will FAIL until GREEN phase
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


class TestAgentExecutionCreation:
    """Test basic AgentExecution creation and validation."""

    @pytest.mark.asyncio
    async def test_agent_execution_minimal_creation(self, db_session: AsyncSession):
        """Execution can be created with minimal required fields."""
        # Create parent job first
        job = AgentJob(
            job_id="job-exec-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution
        execution = AgentExecution(
            agent_id="agent-abc-123",
            job_id="job-exec-001",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="waiting",
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.agent_id == "agent-abc-123"
        assert execution.job_id == "job-exec-001"
        assert execution.status == "waiting"

    @pytest.mark.asyncio
    async def test_agent_execution_requires_job_id(self, db_session: AsyncSession):
        """Execution creation fails without job_id (NOT NULL constraint)."""
        execution = AgentExecution(
            agent_id="agent-abc-456",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="waiting",
            # job_id missing - should FAIL
        )
        db_session.add(execution)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_agent_execution_requires_tenant_key(self, db_session: AsyncSession):
        """Execution creation fails without tenant_key (NOT NULL constraint)."""
        job = AgentJob(
            job_id="job-exec-002",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id="agent-abc-789",
            job_id="job-exec-002",
            agent_display_name="orchestrator",
            status="waiting",
            # tenant_key missing - should FAIL
        )
        db_session.add(execution)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_agent_execution_auto_generates_agent_id(self, db_session: AsyncSession):
        """Execution auto-generates agent_id if not provided."""
        job = AgentJob(
            job_id="job-exec-003",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            job_id="job-exec-003",
            tenant_key="tenant-abc",
            agent_display_name="analyzer",
            status="waiting",
            # agent_id NOT provided - should auto-generate
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.agent_id is not None
        assert len(execution.agent_id) == 36  # UUID format


class TestAgentExecutionForeignKey:
    """Test execution foreign key to job."""

    @pytest.mark.asyncio
    async def test_agent_execution_belongs_to_job(self, db_session: AsyncSession):
        """Execution references its parent job via foreign key."""
        job = AgentJob(
            job_id="job-fk-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id="agent-fk-001",
            job_id="job-fk-001",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="waiting",
        )
        db_session.add(execution)
        await db_session.commit()

        # Verify foreign key relationship
        assert execution.job_id == job.job_id
        assert execution.job == job  # ORM relationship

    @pytest.mark.asyncio
    async def test_agent_execution_rejects_invalid_job_id(self, db_session: AsyncSession):
        """Execution creation fails with non-existent job_id (FK constraint)."""
        execution = AgentExecution(
            agent_id="agent-fk-002",
            job_id="nonexistent-job-id",  # Does NOT exist
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="waiting",
        )
        db_session.add(execution)

        # Foreign key constraint violation
        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()


class TestAgentExecutionStatusConstraint:
    """Test execution status validation."""

    @pytest.mark.parametrize(
        "status", ["waiting", "working", "blocked", "complete", "silent", "decommissioned"]
    )
    @pytest.mark.asyncio
    async def test_agent_execution_allows_valid_statuses(self, db_session: AsyncSession, status: str):
        """Execution accepts all valid status values."""
        job = AgentJob(
            job_id=f"job-status-{status}",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id=f"agent-status-{status}",
            job_id=f"job-status-{status}",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status=status,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.status == status

    @pytest.mark.asyncio
    async def test_agent_execution_rejects_invalid_status(self, db_session: AsyncSession):
        """Execution rejects invalid status (constraint violation)."""
        job = AgentJob(
            job_id="job-status-invalid",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id="agent-status-invalid",
            job_id="job-status-invalid",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="invalid_status",  # NOT in allowed list
        )
        db_session.add(execution)

        # CheckConstraint violation
        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()


class TestAgentExecutionProgressConstraint:
    """Test execution progress validation."""

    @pytest.mark.asyncio
    async def test_agent_execution_allows_valid_progress(self, db_session: AsyncSession):
        """Execution accepts progress 0-100."""
        job = AgentJob(
            job_id="job-progress-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id="agent-progress-001",
            job_id="job-progress-001",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            progress=50,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.progress == 50

    @pytest.mark.asyncio
    async def test_agent_execution_rejects_negative_progress(self, db_session: AsyncSession):
        """Execution rejects negative progress (constraint violation)."""
        job = AgentJob(
            job_id="job-progress-002",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id="agent-progress-002",
            job_id="job-progress-002",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            progress=-10,  # INVALID - negative
        )
        db_session.add(execution)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_agent_execution_rejects_excessive_progress(self, db_session: AsyncSession):
        """Execution rejects progress > 100 (constraint violation)."""
        job = AgentJob(
            job_id="job-progress-003",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id="agent-progress-003",
            job_id="job-progress-003",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            progress=150,  # INVALID - exceeds 100
        )
        db_session.add(execution)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()


class TestAgentExecutionSuccessionChain:
    """Test succession chain functionality."""

    @pytest.mark.asyncio
    async def test_agent_execution_succession_chain(self, db_session: AsyncSession):
        """Executions can form succession chains via succeeded_by/spawned_by."""
        job = AgentJob(
            job_id="job-succession-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create execution 1
        exec1 = AgentExecution(
            agent_id="agent-001",
            job_id="job-succession-001",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="complete",
            succeeded_by="agent-002",  # Points to next execution
        )
        db_session.add(exec1)
        await db_session.commit()

        # Create execution 2 (successor)
        exec2 = AgentExecution(
            agent_id="agent-002",
            job_id="job-succession-001",  # SAME job
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            spawned_by="agent-001",  # Points to previous execution
        )
        db_session.add(exec2)
        await db_session.commit()

        # Validate succession chain
        assert exec1.succeeded_by == exec2.agent_id
        assert exec2.spawned_by == exec1.agent_id
        assert exec1.job_id == exec2.job_id  # SAME work order


class TestAgentExecutionHealthMonitoring:
    """Test health monitoring fields."""

    @pytest.mark.parametrize("health_status", ["unknown", "healthy", "warning", "critical", "timeout"])
    @pytest.mark.asyncio
    async def test_agent_execution_allows_valid_health_statuses(self, db_session: AsyncSession, health_status: str):
        """Execution accepts all valid health status values."""
        job = AgentJob(
            job_id=f"job-health-{health_status}",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id=f"agent-health-{health_status}",
            job_id=f"job-health-{health_status}",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            health_status=health_status,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.health_status == health_status

    @pytest.mark.asyncio
    async def test_agent_execution_tracks_health_failures(self, db_session: AsyncSession):
        """Execution tracks consecutive health check failures."""
        job = AgentJob(
            job_id="job-health-tracking",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id="agent-health-tracking",
            job_id="job-health-tracking",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            health_status="warning",
            health_failure_count=3,
            last_health_check=datetime.now(timezone.utc),
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.health_failure_count == 3
        assert execution.last_health_check is not None


class TestAgentExecutionToolAssignment:
    """Test tool_type field validation."""

    @pytest.mark.parametrize("tool_type", ["claude-code", "codex", "gemini", "universal"])
    @pytest.mark.asyncio
    async def test_agent_execution_allows_valid_tool_types(self, db_session: AsyncSession, tool_type: str):
        """Execution accepts all valid tool types."""
        job = AgentJob(
            job_id=f"job-tool-{tool_type}",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id=f"agent-tool-{tool_type}",
            job_id=f"job-tool-{tool_type}",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            tool_type=tool_type,
        )
        db_session.add(execution)
        await db_session.commit()

        assert execution.tool_type == tool_type

    @pytest.mark.asyncio
    async def test_agent_execution_rejects_invalid_tool_type(self, db_session: AsyncSession):
        """Execution rejects invalid tool_type (constraint violation)."""
        job = AgentJob(
            job_id="job-tool-invalid",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        execution = AgentExecution(
            agent_id="agent-tool-invalid",
            job_id="job-tool-invalid",
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
            tool_type="invalid-tool",  # NOT in allowed list
        )
        db_session.add(execution)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()
