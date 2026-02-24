"""
Tests for AgentJob.phase column (Handover 0411a).

RED Phase (TDD): These tests verify the phase column on AgentJob:
- Column exists and is nullable
- Defaults to None when not provided
- Accepts integer values (1, 2, 3, etc.)
- Can be updated after creation
- Multiple jobs can share the same phase value (parallel execution)
"""

import uuid

import pytest
from sqlalchemy import Integer, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentJob


class TestAgentJobPhaseColumn:
    """Test the phase column on AgentJob model."""

    @pytest.mark.asyncio
    async def test_phase_defaults_to_none(
        self, db_session: AsyncSession, test_project_id: str, test_tenant_key: str
    ):
        """Phase should default to None when not provided."""
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            mission="Test mission for phase default",
            job_type="sub_agent",
            status="active",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        assert job.phase is None

    @pytest.mark.asyncio
    async def test_phase_accepts_integer_value(
        self, db_session: AsyncSession, test_project_id: str, test_tenant_key: str
    ):
        """Phase should accept an integer value."""
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            mission="Test mission for phase integer",
            job_type="sub_agent",
            status="active",
            phase=1,
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        assert job.phase == 1

    @pytest.mark.asyncio
    async def test_phase_accepts_higher_values(
        self, db_session: AsyncSession, test_project_id: str, test_tenant_key: str
    ):
        """Phase should accept values greater than 1."""
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            mission="Test mission for phase 3",
            job_type="sub_agent",
            status="active",
            phase=3,
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        assert job.phase == 3

    @pytest.mark.asyncio
    async def test_phase_can_be_updated(
        self, db_session: AsyncSession, test_project_id: str, test_tenant_key: str
    ):
        """Phase should be updatable after creation."""
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            mission="Test mission for phase update",
            job_type="sub_agent",
            status="active",
            phase=1,
        )
        db_session.add(job)
        await db_session.commit()

        # Update phase
        job.phase = 2
        await db_session.commit()
        await db_session.refresh(job)

        assert job.phase == 2

    @pytest.mark.asyncio
    async def test_phase_can_be_set_to_none(
        self, db_session: AsyncSession, test_project_id: str, test_tenant_key: str
    ):
        """Phase should be clearable (set back to None)."""
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            mission="Test mission for phase clear",
            job_type="sub_agent",
            status="active",
            phase=1,
        )
        db_session.add(job)
        await db_session.commit()

        # Clear phase
        job.phase = None
        await db_session.commit()
        await db_session.refresh(job)

        assert job.phase is None

    @pytest.mark.asyncio
    async def test_multiple_jobs_same_phase(
        self, db_session: AsyncSession, test_project_id: str, test_tenant_key: str
    ):
        """Multiple jobs can share the same phase (parallel execution)."""
        job1 = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            mission="First parallel agent",
            job_type="sub_agent",
            status="active",
            phase=1,
        )
        job2 = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            mission="Second parallel agent",
            job_type="sub_agent",
            status="active",
            phase=1,
        )
        db_session.add_all([job1, job2])
        await db_session.commit()

        # Both should have phase 1
        result = await db_session.execute(
            select(AgentJob).filter(
                AgentJob.project_id == test_project_id,
                AgentJob.phase == 1,
            )
        )
        phase1_jobs = result.scalars().all()

        assert len(phase1_jobs) == 2

    @pytest.mark.asyncio
    async def test_phase_queryable_with_filter(
        self, db_session: AsyncSession, test_project_id: str, test_tenant_key: str
    ):
        """Jobs can be filtered by phase value."""
        # Create jobs in different phases
        for phase_val in [1, 1, 2, 2, 3, None]:
            job = AgentJob(
                job_id=str(uuid.uuid4()),
                tenant_key=test_tenant_key,
                project_id=test_project_id,
                mission=f"Agent in phase {phase_val}",
                job_type="sub_agent",
                status="active",
                phase=phase_val,
            )
            db_session.add(job)
        await db_session.commit()

        # Query phase 2 jobs
        result = await db_session.execute(
            select(AgentJob).filter(
                AgentJob.tenant_key == test_tenant_key,
                AgentJob.project_id == test_project_id,
                AgentJob.phase == 2,
            )
        )
        phase2_jobs = result.scalars().all()
        assert len(phase2_jobs) == 2

        # Query jobs with no phase
        result = await db_session.execute(
            select(AgentJob).filter(
                AgentJob.tenant_key == test_tenant_key,
                AgentJob.project_id == test_project_id,
                AgentJob.phase.is_(None),
            )
        )
        no_phase_jobs = result.scalars().all()
        assert len(no_phase_jobs) == 1


class TestAgentJobPhaseColumnSchema:
    """Test that the phase column has correct schema properties."""

    @pytest.mark.asyncio
    async def test_phase_column_exists_in_model(self, db_session: AsyncSession):
        """AgentJob model should have a phase attribute."""
        assert hasattr(AgentJob, "phase"), "AgentJob model missing 'phase' attribute"

    @pytest.mark.asyncio
    async def test_phase_column_is_nullable(self, db_session: AsyncSession):
        """Phase column should be nullable in the database."""
        phase_col = AgentJob.__table__.columns["phase"]
        assert phase_col.nullable is True

    @pytest.mark.asyncio
    async def test_phase_column_type_is_integer(self, db_session: AsyncSession):
        """Phase column should be Integer type."""
        phase_col = AgentJob.__table__.columns["phase"]
        assert isinstance(phase_col.type, Integer)
