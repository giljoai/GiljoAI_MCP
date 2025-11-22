"""
Test mission tracking fields in AgentJob model (Handover 0233 Phase 1)

Tests verify that mission_read_at and mission_acknowledged_at timestamp fields
exist and function correctly for job lifecycle checkpoint tracking.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.giljo_mcp.models.agents import MCPAgentJob


@pytest.mark.asyncio
async def test_agent_job_has_mission_read_at_field(db_session: AsyncSession):
    """Test that MCPAgentJob model includes mission_read_at timestamp field"""
    job = MCPAgentJob(
        job_id="test-job-001",
        tenant_key="test-tenant",
        agent_type="orchestrator",
        agent_name="Test Orchestrator",
        mission="Test mission for handover 0233",
        status="waiting",
        mission_read_at=None,
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Verify field exists and is None by default
    assert hasattr(job, "mission_read_at")
    assert job.mission_read_at is None


@pytest.mark.asyncio
async def test_agent_job_has_mission_acknowledged_at_field(db_session: AsyncSession):
    """Test that MCPAgentJob model includes mission_acknowledged_at timestamp field"""
    job = MCPAgentJob(
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
async def test_agent_job_can_set_mission_read_at_timestamp(db_session: AsyncSession):
    """Test that mission_read_at can be set to a timestamp"""
    read_time = datetime.now(timezone.utc)

    job = MCPAgentJob(
        job_id="test-job-003",
        tenant_key="test-tenant",
        agent_type="orchestrator",
        agent_name="Test Orchestrator",
        mission="Test mission for handover 0233",
        status="waiting",
        mission_read_at=read_time,
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Verify timestamp was stored correctly
    assert job.mission_read_at is not None
    assert isinstance(job.mission_read_at, datetime)
    assert job.mission_read_at == read_time


@pytest.mark.asyncio
async def test_agent_job_can_set_mission_acknowledged_at_timestamp(db_session: AsyncSession):
    """Test that mission_acknowledged_at can be set to a timestamp"""
    ack_time = datetime.now(timezone.utc)

    job = MCPAgentJob(
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
async def test_agent_job_mission_tracking_independent_of_status(db_session: AsyncSession):
    """Test that mission read/ack timestamps are independent of job status"""
    read_time = datetime.now(timezone.utc)

    job = MCPAgentJob(
        job_id="test-job-005",
        tenant_key="test-tenant",
        agent_type="orchestrator",
        agent_name="Test Orchestrator",
        mission="Test mission for handover 0233",
        status="waiting",  # Still waiting
        mission_read_at=read_time,  # But mission has been read
        mission_acknowledged_at=None,  # Not yet acknowledged
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Verify mission can be read even if status is still waiting
    assert job.status == "waiting"
    assert job.mission_read_at == read_time
    assert job.mission_acknowledged_at is None


@pytest.mark.asyncio
async def test_agent_job_both_timestamps_can_be_set(db_session: AsyncSession):
    """Test that both mission_read_at and mission_acknowledged_at can be set simultaneously"""
    read_time = datetime.now(timezone.utc)
    ack_time = datetime.now(timezone.utc)

    job = MCPAgentJob(
        job_id="test-job-006",
        tenant_key="test-tenant",
        agent_type="orchestrator",
        agent_name="Test Orchestrator",
        mission="Test mission for handover 0233",
        status="working",
        mission_read_at=read_time,
        mission_acknowledged_at=ack_time,
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Verify both timestamps exist
    assert job.mission_read_at == read_time
    assert job.mission_acknowledged_at == ack_time
