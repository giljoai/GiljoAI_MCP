"""
Test mission tracking fields in AgentJob model - Updated for simplified job signaling

Tests verify that mission_acknowledged_at timestamp field exists and functions correctly.

Note: mission_read_at has been removed; only mission_acknowledged_at remains.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.giljo_mcp.models.agent_identity import AgentExecution


@pytest.mark.asyncio
async def test_agent_job_has_mission_acknowledged_at_field_defaults_none(db_session: AsyncSession):
    """Test that MCPAgentJob model includes mission_acknowledged_at timestamp field defaulting to None"""
    job = AgentExecution(
        job_id="test-job-001",
        tenant_key="test-tenant",
        agent_type="orchestrator",
        agent_name="Test Orchestrator",
        mission="Test mission",
        status="waiting",
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Verify field exists and is None by default
    assert hasattr(job, "mission_acknowledged_at")
    assert job.mission_acknowledged_at is None


@pytest.mark.asyncio
async def test_agent_job_has_mission_acknowledged_at_field(db_session: AsyncSession):
    """Test that MCPAgentJob model includes mission_acknowledged_at timestamp field"""
    job = AgentExecution(
        job_id="test-job-002",
        tenant_key="test-tenant",
        agent_type="orchestrator",
        agent_name="Test Orchestrator",
        mission="Test mission for handover 0233",
        status="waiting",
        mission_acknowledged_at=None,
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Verify field exists and is None by default
    assert hasattr(job, "mission_acknowledged_at")
    assert job.mission_acknowledged_at is None


@pytest.mark.asyncio
async def test_agent_job_can_update_mission_acknowledged_at(db_session: AsyncSession):
    """Test that mission_acknowledged_at can be set and updated"""
    job = AgentExecution(
        job_id="test-job-003",
        tenant_key="test-tenant",
        agent_type="orchestrator",
        agent_name="Test Orchestrator",
        mission="Test mission",
        status="waiting",
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Initially None
    assert job.mission_acknowledged_at is None

    # Set timestamp
    ack_time = datetime.now(timezone.utc)
    job.mission_acknowledged_at = ack_time
    await db_session.commit()
    await db_session.refresh(job)

    # Verify timestamp was stored correctly
    assert job.mission_acknowledged_at is not None
    assert isinstance(job.mission_acknowledged_at, datetime)
    assert job.mission_acknowledged_at == ack_time


@pytest.mark.asyncio
async def test_agent_job_can_set_mission_acknowledged_at_timestamp(db_session: AsyncSession):
    """Test that mission_acknowledged_at can be set to a timestamp"""
    ack_time = datetime.now(timezone.utc)

    job = AgentExecution(
        job_id="test-job-004",
        tenant_key="test-tenant",
        agent_type="orchestrator",
        agent_name="Test Orchestrator",
        mission="Test mission for handover 0233",
        status="waiting",
        mission_acknowledged_at=ack_time,
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Verify timestamp was stored correctly
    assert job.mission_acknowledged_at is not None
    assert isinstance(job.mission_acknowledged_at, datetime)
    assert job.mission_acknowledged_at == ack_time


@pytest.mark.asyncio
async def test_agent_job_mission_acknowledged_at_independent_of_status(db_session: AsyncSession):
    """Test that mission_acknowledged_at timestamp is independent of job status"""
    ack_time = datetime.now(timezone.utc)

    job = AgentExecution(
        job_id="test-job-005",
        tenant_key="test-tenant",
        agent_type="orchestrator",
        agent_name="Test Orchestrator",
        mission="Test mission",
        status="waiting",  # Still waiting
        mission_acknowledged_at=ack_time,  # But mission has been acknowledged
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Verify mission can be acknowledged even if status is still waiting
    assert job.status == "waiting"
    assert job.mission_acknowledged_at == ack_time


@pytest.mark.asyncio
async def test_agent_job_mission_acknowledged_at_persists_across_sessions(db_session: AsyncSession):
    """Test that mission_acknowledged_at persists correctly across database sessions"""
    ack_time = datetime.now(timezone.utc)

    job = AgentExecution(
        job_id="test-job-006",
        tenant_key="test-tenant",
        agent_type="orchestrator",
        agent_name="Test Orchestrator",
        mission="Test mission",
        status="working",
        mission_acknowledged_at=ack_time,
    )

    db_session.add(job)
    await db_session.commit()

    # Close session and reopen
    job_id = job.job_id
    await db_session.close()

    # Create new session and verify timestamp persists
    from sqlalchemy import select
    async with db_session.begin():
        result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job_id)
        )
        retrieved_job = result.scalar_one_or_none()

        assert retrieved_job is not None
        assert retrieved_job.mission_acknowledged_at == ack_time
