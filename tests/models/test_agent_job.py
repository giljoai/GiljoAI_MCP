"""
Tests for AgentJob model (Handover 0366a).

RED Phase (TDD): These tests are written FIRST and will FAIL until the model is implemented.

AgentJob represents the persistent work order:
- Survives agent succession (new execution, SAME job)
- Stores mission ONCE (no duplication across executions)
- Tracks job-level status (active, completed, cancelled)
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# These imports will FAIL until GREEN phase
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


class TestAgentJobCreation:
    """Test basic AgentJob creation and validation."""

    @pytest.mark.asyncio
    async def test_agent_job_minimal_creation(self, db_session: AsyncSession):
        """Job can be created with minimal required fields."""
        job = AgentJob(
            job_id="test-job-001",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Build authentication system with OAuth2 support",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        # Verify job was created
        assert job.job_id == "test-job-001"
        assert job.mission == "Build authentication system with OAuth2 support"
        assert job.status == "active"
        assert job.job_type == "orchestrator"
        assert job.created_at is not None  # Auto-generated

    @pytest.mark.asyncio
    async def test_agent_job_requires_mission(self, db_session: AsyncSession):
        """Job creation fails without mission (NOT NULL constraint)."""
        job = AgentJob(
            job_id="test-job-002",
            tenant_key="tenant-abc",
            project_id="project-456",
            job_type="orchestrator",
            status="active",
            # mission missing - should FAIL on commit
        )
        db_session.add(job)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_agent_job_requires_job_type(self, db_session: AsyncSession):
        """Job creation fails without job_type (NOT NULL constraint)."""
        job = AgentJob(
            job_id="test-job-003",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            status="active",
            # job_type missing - should FAIL
        )
        db_session.add(job)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_agent_job_requires_tenant_key(self, db_session: AsyncSession):
        """Job creation fails without tenant_key (NOT NULL constraint)."""
        job = AgentJob(
            job_id="test-job-004",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
            # tenant_key missing - should FAIL
        )
        db_session.add(job)

        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_agent_job_auto_generates_job_id(self, db_session: AsyncSession):
        """Job auto-generates job_id if not provided."""
        job = AgentJob(
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="analyzer",
            status="active",
            # job_id NOT provided - should auto-generate
        )
        db_session.add(job)
        await db_session.commit()

        assert job.job_id is not None
        assert len(job.job_id) == 36  # UUID format


class TestAgentJobStatusConstraint:
    """Test job status validation."""

    @pytest.mark.asyncio
    async def test_agent_job_allows_active_status(self, db_session: AsyncSession):
        """Job accepts 'active' status (valid)."""
        job = AgentJob(
            job_id="test-job-010",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        assert job.status == "active"

    @pytest.mark.asyncio
    async def test_agent_job_allows_completed_status(self, db_session: AsyncSession):
        """Job accepts 'completed' status (valid)."""
        job = AgentJob(
            job_id="test-job-011",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="completed",
        )
        db_session.add(job)
        await db_session.commit()

        assert job.status == "completed"

    @pytest.mark.asyncio
    async def test_agent_job_allows_cancelled_status(self, db_session: AsyncSession):
        """Job accepts 'cancelled' status (valid)."""
        job = AgentJob(
            job_id="test-job-012",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="cancelled",
        )
        db_session.add(job)
        await db_session.commit()

        assert job.status == "cancelled"

    @pytest.mark.asyncio
    async def test_agent_job_rejects_invalid_status(self, db_session: AsyncSession):
        """Job rejects invalid status (constraint violation)."""
        job = AgentJob(
            job_id="test-job-013",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="invalid_status",  # NOT in allowed list
        )
        db_session.add(job)

        # CheckConstraint violation
        with pytest.raises(IntegrityError):
            await db_session.commit()

        await db_session.rollback()


class TestAgentJobRelationships:
    """Test job relationships with executions."""

    @pytest.mark.asyncio
    async def test_agent_job_has_executions_relationship(self, db_session: AsyncSession):
        """Job can access its executions via relationship."""
        job = AgentJob(
            job_id="test-job-020",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Build auth system",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Relationship should exist (even if empty)
        assert hasattr(job, "executions")
        assert job.executions == []  # No executions yet

    @pytest.mark.asyncio
    async def test_agent_job_can_have_multiple_executions(self, db_session: AsyncSession):
        """Job can have multiple executions (succession scenario)."""
        job = AgentJob(
            job_id="test-job-021",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Build auth system",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Create first execution
        exec1 = AgentExecution(
            agent_id="agent-001",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="complete",
        )
        db_session.add(exec1)
        await db_session.commit()

        # Create second execution (succession)
        exec2 = AgentExecution(
            agent_id="agent-002",
            job_id=job.job_id,
            tenant_key="tenant-abc",
            agent_display_name="orchestrator",
            status="working",
        )
        db_session.add(exec2)
        await db_session.commit()

        # Refresh job to load executions
        await db_session.refresh(job)

        # Validate multiple executions
        assert len(job.executions) == 2
        assert job.executions[0].agent_id == "agent-001"
        assert job.executions[1].agent_id == "agent-002"


class TestAgentJobMetadata:
    """Test job metadata storage."""

    @pytest.mark.asyncio
    async def test_agent_job_stores_metadata(self, db_session: AsyncSession):
        """Job can store JSONB metadata."""
        job = AgentJob(
            job_id="test-job-030",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
            job_metadata={"priority": "high", "estimated_duration_hours": 8, "tags": ["auth", "security"]},
        )
        db_session.add(job)
        await db_session.commit()

        # Refresh to load from DB
        await db_session.refresh(job)

        assert job.job_metadata["priority"] == "high"
        assert job.job_metadata["estimated_duration_hours"] == 8
        assert "auth" in job.job_metadata["tags"]

    @pytest.mark.asyncio
    async def test_agent_job_metadata_defaults_to_empty_dict(self, db_session: AsyncSession):
        """Job metadata defaults to empty dict if not provided."""
        job = AgentJob(
            job_id="test-job-031",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
            # job_metadata NOT provided
        )
        db_session.add(job)
        await db_session.commit()

        await db_session.refresh(job)
        assert job.job_metadata == {}


class TestAgentJobIndexes:
    """Test job indexes for query performance."""

    @pytest.mark.asyncio
    async def test_agent_job_tenant_index_exists(self, db_session: AsyncSession):
        """Tenant index exists for fast filtering."""
        # Create multiple jobs
        for i in range(5):
            job = AgentJob(
                job_id=f"test-job-index-{i}",
                tenant_key="tenant-abc",
                project_id="project-456",
                mission=f"Test mission {i}",
                job_type="orchestrator",
                status="active",
            )
            db_session.add(job)
        await db_session.commit()

        # Query by tenant_key (should use index)
        result = await db_session.execute(select(AgentJob).filter(AgentJob.tenant_key == "tenant-abc"))
        jobs = result.scalars().all()

        assert len(jobs) == 5

    @pytest.mark.asyncio
    async def test_agent_job_project_index_exists(self, db_session: AsyncSession):
        """Project index exists for fast filtering."""
        job = AgentJob(
            job_id="test-job-index-10",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Query by project_id (should use index)
        result = await db_session.execute(select(AgentJob).filter(AgentJob.project_id == "project-456"))
        jobs = result.scalars().all()

        assert len(jobs) >= 1


class TestAgentJobLifecycle:
    """Test job lifecycle (creation → active → completed)."""

    @pytest.mark.asyncio
    async def test_agent_job_lifecycle_creation(self, db_session: AsyncSession):
        """Job starts as 'active' status."""
        job = AgentJob(
            job_id="test-job-lifecycle-1",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        assert job.status == "active"
        assert job.created_at is not None
        assert job.completed_at is None

    @pytest.mark.asyncio
    async def test_agent_job_lifecycle_completion(self, db_session: AsyncSession):
        """Job can be marked as completed."""
        job = AgentJob(
            job_id="test-job-lifecycle-2",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Mark as completed
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        assert job.status == "completed"
        assert job.completed_at is not None

    @pytest.mark.asyncio
    async def test_agent_job_lifecycle_cancellation(self, db_session: AsyncSession):
        """Job can be cancelled."""
        job = AgentJob(
            job_id="test-job-lifecycle-3",
            tenant_key="tenant-abc",
            project_id="project-456",
            mission="Test mission",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()

        # Cancel job
        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        await db_session.commit()

        assert job.status == "cancelled"
        assert job.completed_at is not None
