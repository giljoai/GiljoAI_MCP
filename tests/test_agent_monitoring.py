"""
Unit tests for Agent Monitoring (Handover 0107).

Tests progress tracking, message check tracking, health monitoring,
and stale job detection with multi-tenant isolation.

Coverage Target: 80%+
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.tools.agent_status import report_progress
from src.giljo_mcp.tools.agent_messaging import read_mcp_messages
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from sqlalchemy import select
from tests.helpers.test_db_helper import PostgreSQLTestHelper


# Helper function for testing - detects stale jobs
async def get_stale_jobs(tenant_key: str, threshold_minutes: int = 10):
    """
    Test helper: Find jobs with no progress updates for > threshold_minutes.
    """
    from datetime import timedelta

    db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=True), is_async=True)

    async with db_manager.get_session_async() as session:
        threshold_time = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

        stmt = select(AgentExecution).where(
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.status.in_(["active", "working"]),
            AgentExecution.last_progress_at <= threshold_time
        )

        result = await session.execute(stmt)
        stale_jobs = result.scalars().all()

        await db_manager.close_async()
        return stale_jobs


@pytest_asyncio.fixture
async def db_manager():
    """Create async database manager for testing."""
    manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=True), is_async=True)
    yield manager
    await manager.close_async()


@pytest_asyncio.fixture
async def db_session(db_manager):
    """Get async database session for testing."""
    async with db_manager.get_session_async() as session:
        yield session


@pytest_asyncio.fixture
async def test_job(db_session):
    """Create test agent job."""
    tenant_key = f"tk_test_{uuid4().hex[:16]}"
    project_id = str(uuid4())

    job = AgentExecution(
        tenant_key=tenant_key,
        project_id=project_id,
        job_id=str(uuid4()),
        agent_display_name="implementer",
        mission="Test mission",
        status="active",
        last_progress_at=None,
        last_message_check_at=None,
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    return job


class TestProgressTracking:
    """Test progress tracking timestamp updates."""

    @pytest.mark.asyncio
    async def test_report_progress_updates_timestamp(self, db_session, test_job):
        """Test that report_progress updates last_progress_at timestamp."""
        # Record initial state
        initial_progress_at = test_job.last_progress_at
        assert initial_progress_at is None

        # Report progress
        await report_progress(
            job_id=test_job.job_id,
            tenant_key=test_job.tenant_key,
            progress={
                "task": "Implementing feature X",
                "percent": 50
            }
        )

        # Refresh and verify timestamp updated
        await db_session.refresh(test_job)
        assert test_job.last_progress_at is not None
        assert test_job.last_progress_at > datetime.now(timezone.utc) - timedelta(seconds=5)
        # Progress is stored in job_metadata, not direct field
        assert test_job.job_metadata is not None
        assert test_job.job_metadata["latest_progress"]["percent"] == 50

    @pytest.mark.asyncio
    async def test_report_progress_updates_on_subsequent_calls(self, db_session, test_job):
        """Test that report_progress updates timestamp on subsequent calls."""
        # First call
        await report_progress(
            job_id=test_job.job_id,
            tenant_key=test_job.tenant_key,
            progress={"task": "Task 1", "percent": 25}
        )
        await db_session.refresh(test_job)
        first_timestamp = test_job.last_progress_at

        # Wait a moment
        import asyncio
        await asyncio.sleep(0.1)

        # Second call
        await report_progress(
            job_id=test_job.job_id,
            tenant_key=test_job.tenant_key,
            progress={"task": "Task 2", "percent": 75}
        )
        await db_session.refresh(test_job)
        second_timestamp = test_job.last_progress_at

        # Verify timestamp advanced
        assert second_timestamp > first_timestamp
        assert test_job.job_metadata["latest_progress"]["percent"] == 75
        assert test_job.job_metadata["latest_progress"]["task"] == "Task 2"


class TestMessageChecking:
    """Test message check timestamp updates."""

    @pytest.mark.asyncio
    async def test_receive_messages_updates_timestamp(self, db_session, test_job):
        """Test that receive_messages updates last_message_check_at timestamp."""
        # Record initial state
        initial_check_at = test_job.last_message_check_at
        assert initial_check_at is None

        # Receive messages (empty array is fine for this test)
        await read_mcp_messages(
            job_id=test_job.job_id,
            tenant_key=test_job.tenant_key
        )

        # Refresh and verify timestamp updated
        await db_session.refresh(test_job)
        assert test_job.last_message_check_at is not None
        assert test_job.last_message_check_at > datetime.now(timezone.utc) - timedelta(seconds=5)

    @pytest.mark.asyncio
    async def test_receive_messages_updates_on_subsequent_calls(self, db_session, test_job):
        """Test that receive_messages updates timestamp on subsequent calls."""
        # First call
        await read_mcp_messages(
            job_id=test_job.job_id,
            tenant_key=test_job.tenant_key
        )
        await db_session.refresh(test_job)
        first_timestamp = test_job.last_message_check_at

        # Wait a moment
        import asyncio
        await asyncio.sleep(0.1)

        # Second call
        await read_mcp_messages(
            job_id=test_job.job_id,
            tenant_key=test_job.tenant_key
        )
        await db_session.refresh(test_job)
        second_timestamp = test_job.last_message_check_at

        # Verify timestamp advanced
        assert second_timestamp > first_timestamp


class TestHealthMonitoring:
    """Test health monitoring and stale job detection."""

    @pytest.mark.asyncio
    async def test_health_monitor_detects_stale_jobs(self, db_session):
        """Test health monitor detects jobs with no progress for >10 minutes."""
        tenant_key = f"tk_test_{uuid4().hex[:16]}"
        project_id = str(uuid4())

        # Create job with stale timestamp (11 minutes ago)
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=11)
        stale_job = AgentExecution(
            tenant_key=tenant_key,
            project_id=project_id,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Stale job",
            status="active",
            last_progress_at=stale_time,
        )

        db_session.add(stale_job)
        await db_session.commit()

        # Detect stale jobs
        stale_jobs = await get_stale_jobs(tenant_key=tenant_key, threshold_minutes=10)

        # Verify detection
        assert len(stale_jobs) == 1
        assert stale_jobs[0].job_id == stale_job.job_id

    @pytest.mark.asyncio
    async def test_health_monitor_ignores_recent_jobs(self, db_session):
        """Test health monitor ignores jobs with recent activity."""
        tenant_key = f"tk_test_{uuid4().hex[:16]}"
        project_id = str(uuid4())

        # Create job with recent timestamp (5 minutes ago)
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_job = AgentExecution(
            tenant_key=tenant_key,
            project_id=project_id,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Recent job",
            status="active",
            last_progress_at=recent_time,
        )

        db_session.add(recent_job)
        await db_session.commit()

        # Detect stale jobs
        stale_jobs = await get_stale_jobs(tenant_key=tenant_key, threshold_minutes=10)

        # Verify not detected as stale
        assert len(stale_jobs) == 0

    @pytest.mark.asyncio
    async def test_stale_threshold_calculation(self, db_session):
        """Test stale threshold calculation is accurate."""
        tenant_key = f"tk_test_{uuid4().hex[:16]}"
        project_id = str(uuid4())

        # Create jobs at different staleness levels
        now = datetime.now(timezone.utc)

        # Exactly at threshold (10 minutes)
        threshold_job = AgentExecution(
            tenant_key=tenant_key,
            project_id=project_id,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Threshold job",
            status="active",
            last_progress_at=now - timedelta(minutes=10),
        )

        # Just over threshold (10.5 minutes)
        stale_job = AgentExecution(
            tenant_key=tenant_key,
            project_id=project_id,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Stale job",
            status="active",
            last_progress_at=now - timedelta(minutes=10, seconds=30),
        )

        # Just under threshold (9.5 minutes)
        recent_job = AgentExecution(
            tenant_key=tenant_key,
            project_id=project_id,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Recent job",
            status="active",
            last_progress_at=now - timedelta(minutes=9, seconds=30),
        )

        db_session.add_all([threshold_job, stale_job, recent_job])
        await db_session.commit()

        # Detect stale jobs with 10-minute threshold
        stale_jobs = await get_stale_jobs(tenant_key=tenant_key, threshold_minutes=10)

        # Verify: jobs at or over threshold are detected
        stale_job_ids = [job.job_id for job in stale_jobs]
        assert stale_job.job_id in stale_job_ids  # Over threshold
        assert threshold_job.job_id in stale_job_ids  # At threshold (inclusive)
        assert recent_job.job_id not in stale_job_ids  # Under threshold


class TestMultiTenantIsolation:
    """Test multi-tenant isolation in monitoring."""

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, db_session):
        """Test that stale job detection respects tenant boundaries."""
        tenant_a = f"tk_test_{uuid4().hex[:16]}"
        tenant_b = f"tk_test_{uuid4().hex[:16]}"
        project_id = str(uuid4())

        # Create stale jobs for both tenants
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=15)

        job_a = AgentExecution(
            tenant_key=tenant_a,
            project_id=project_id,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Tenant A job",
            status="active",
            last_progress_at=stale_time,
        )

        job_b = AgentExecution(
            tenant_key=tenant_b,
            project_id=project_id,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Tenant B job",
            status="active",
            last_progress_at=stale_time,
        )

        db_session.add_all([job_a, job_b])
        await db_session.commit()

        # Detect stale jobs for tenant A
        stale_jobs_a = await get_stale_jobs(tenant_key=tenant_a, threshold_minutes=10)

        # Verify only tenant A's job returned
        assert len(stale_jobs_a) == 1
        assert stale_jobs_a[0].job_id == job_a.job_id
        assert stale_jobs_a[0].tenant_key == tenant_a

        # Detect stale jobs for tenant B
        stale_jobs_b = await get_stale_jobs(tenant_key=tenant_b, threshold_minutes=10)

        # Verify only tenant B's job returned
        assert len(stale_jobs_b) == 1
        assert stale_jobs_b[0].job_id == job_b.job_id
        assert stale_jobs_b[0].tenant_key == tenant_b
