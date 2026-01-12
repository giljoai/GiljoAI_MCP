"""
Unit tests for Job Cancellation (Handover 0107).

Tests graceful cancellation requests, force-fail operations,
and multi-tenant isolation for cancellation features.

Coverage Target: 80%+
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.agent_job_manager import request_job_cancellation, force_fail_job
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.helpers.test_db_helper import PostgreSQLTestHelper


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
async def active_job(db_session):
    """Create working test agent job."""
    tenant_key = f"tk_test_{uuid4().hex[:16]}"

    job = AgentExecution(
        tenant_key=tenant_key,
        project_id=None,  # No project needed for unit tests
        job_id=str(uuid4()),
        agent_display_name="implementer",
        mission="Test mission",
        status="working",
        messages=None,  # Will be initialized as empty JSONB array
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    return job


@pytest_asyncio.fixture
async def pending_job(db_session):
    """Create waiting test agent job."""
    tenant_key = f"tk_test_{uuid4().hex[:16]}"

    job = AgentExecution(
        tenant_key=tenant_key,
        project_id=None,  # No project needed for unit tests
        job_id=str(uuid4()),
        agent_display_name="implementer",
        mission="Test mission",
        status="waiting",
        messages=None,
    )

    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    return job


class TestCancellationRequest:
    """Test graceful cancellation request operations."""

    @pytest.mark.asyncio
    async def test_request_cancellation_changes_status(self, db_session, active_job, db_manager):
        """Test that request_job_cancellation changes status to 'cancelling'."""
        # Request cancellation
        result = await request_job_cancellation(
            job_id=active_job.job_id,
            reason="User requested cancellation",
            tenant_key=active_job.tenant_key,
            db_manager=db_manager,
        )

        # Verify result
        assert result["success"] is True
        assert result["status"] == "cancelled"
        assert result["job_id"] == active_job.job_id

        # Refresh and verify database
        await db_session.refresh(active_job)
        assert active_job.status == "cancelled"

    @pytest.mark.asyncio
    async def test_request_cancellation_sends_message(self, db_session, active_job, db_manager):
        """Test that cancellation request adds message to job.messages."""
        # Request cancellation
        await request_job_cancellation(
            job_id=active_job.job_id,
            reason="Testing cancellation message",
            tenant_key=active_job.tenant_key,
            db_manager=db_manager,
        )

        # Refresh and verify message added
        await db_session.refresh(active_job)
        assert len(active_job.messages) > 0

        # Verify message structure
        cancel_message = active_job.messages[-1]
        assert cancel_message["type"] == "cancel"
        assert cancel_message["priority"] == "critical"
        assert "Testing cancellation message" in cancel_message["reason"]

    @pytest.mark.asyncio
    async def test_request_cancellation_on_pending_job(self, db_session, pending_job, db_manager):
        """Test that pending jobs can also be cancelled."""
        # Request cancellation
        result = await request_job_cancellation(
            job_id=pending_job.job_id,
            reason="Cancel before start",
            tenant_key=pending_job.tenant_key,
            db_manager=db_manager,
        )

        # Verify result
        assert result["success"] is True
        assert result["status"] == "cancelled"

        # Refresh and verify
        await db_session.refresh(pending_job)
        assert pending_job.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_job_returns_error(self, db_session, db_manager):
        """Test that cancelling a completed job returns error."""
        tenant_key = f"tk_test_{uuid4().hex[:16]}"

        # Create completed job
        completed_job = AgentExecution(
            tenant_key=tenant_key,
            project_id=None,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Completed job",
            status="complete",
            messages=None,
        )

        db_session.add(completed_job)
        await db_session.commit()

        # Attempt to cancel (should NOT raise, but return success=False)
        result = await request_job_cancellation(
            job_id=completed_job.job_id,
            reason="Should fail",
            tenant_key=tenant_key,
            db_manager=db_manager,
        )

        # Verify result indicates cannot cancel terminal state
        assert result["success"] is False
        assert "terminal state" in result["message"].lower()


class TestForceFailJob:
    """Test force-fail operations."""

    @pytest.mark.asyncio
    async def test_force_fail_marks_failed(self, db_session, active_job, db_manager):
        """Test that force_fail_job marks job as failed."""
        # Force fail
        result = await force_fail_job(
            job_id=active_job.job_id,
            reason="Agent unresponsive",
            tenant_key=active_job.tenant_key,
            db_manager=db_manager,
        )

        # Verify result (force_fail_job returns dict)
        assert result is not None
        assert result["success"] is True
        assert result["status"] == "failed"

        # Refresh and verify database
        await db_session.refresh(active_job)
        assert active_job.status == "failed"

    @pytest.mark.asyncio
    async def test_force_fail_logs_reason(self, db_session, active_job, db_manager):
        """Test that force-fail reason is logged in block_reason or messages."""
        # Force fail with specific reason
        await force_fail_job(
            job_id=active_job.job_id,
            reason="Force failed due to timeout after 15 minutes",
            tenant_key=active_job.tenant_key,
            db_manager=db_manager,
        )

        # Refresh and verify reason is stored
        await db_session.refresh(active_job)

        # Check messages for the forced failure reason
        assert len(active_job.messages) > 0, "No messages found"

        failure_message = active_job.messages[-1]
        assert failure_message["type"] == "forced_failure"
        assert "timeout after 15 minutes" in failure_message["reason"]

    @pytest.mark.asyncio
    async def test_force_fail_cancelled_job(self, db_session, db_manager):
        """Test that force-fail works on jobs in 'cancelled' state."""
        tenant_key = f"tk_test_{uuid4().hex[:16]}"

        # Create job in cancelled state
        cancelled_job = AgentExecution(
            tenant_key=tenant_key,
            project_id=None,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Cancelled job",
            status="cancelled",
            messages=None,
        )

        db_session.add(cancelled_job)
        await db_session.commit()

        # Force fail
        result = await force_fail_job(
            job_id=cancelled_job.job_id,
            reason="Agent didn't respond to cancel request",
            tenant_key=tenant_key,
            db_manager=db_manager,
        )

        # Verify transitioned to failed
        await db_session.refresh(cancelled_job)
        assert cancelled_job.status == "failed"


class TestCancellationEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_cancel_invalid_job_returns_error(self, db_session, db_manager):
        """Test that cancelling non-existent job raises error."""
        tenant_key = f"tk_test_{uuid4().hex[:16]}"
        fake_job_id = str(uuid4())

        # Attempt to cancel non-existent job
        with pytest.raises(ValueError) as exc_info:
            await request_job_cancellation(
                job_id=fake_job_id,
                reason="Should fail",
                tenant_key=tenant_key,
                db_manager=db_manager,
            )

        # Verify error message indicates job not found
        assert "not found" in str(exc_info.value).lower() or "does not exist" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_force_fail_invalid_job_returns_error(self, db_session, db_manager):
        """Test that force-failing non-existent job raises error."""
        tenant_key = f"tk_test_{uuid4().hex[:16]}"
        fake_job_id = str(uuid4())

        # Attempt to force-fail non-existent job
        with pytest.raises(ValueError) as exc_info:
            await force_fail_job(
                job_id=fake_job_id,
                reason="Should fail",
                tenant_key=tenant_key,
                db_manager=db_manager,
            )

        # Verify error message
        assert "not found" in str(exc_info.value).lower() or "does not exist" in str(exc_info.value).lower()


class TestMultiTenantIsolation:
    """Test multi-tenant isolation in cancellation operations."""

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_cancellation(self, db_session, db_manager):
        """Test that users cannot cancel other tenants' jobs."""
        tenant_a = f"tk_test_{uuid4().hex[:16]}"
        tenant_b = f"tk_test_{uuid4().hex[:16]}"

        # Create job for tenant A
        job_a = AgentExecution(
            tenant_key=tenant_a,
            project_id=None,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Tenant A job",
            status="working",
            messages=None,
        )

        db_session.add(job_a)
        await db_session.commit()

        # Attempt to cancel tenant A's job using tenant B's key
        with pytest.raises(ValueError) as exc_info:
            await request_job_cancellation(
                job_id=job_a.job_id,
                reason="Cross-tenant attack",
                tenant_key=tenant_b,  # Wrong tenant!
                db_manager=db_manager,
            )

        # Verify error and job status unchanged
        await db_session.refresh(job_a)
        assert job_a.status == "working"  # Still working, not cancelled
        assert "not found" in str(exc_info.value).lower() or "access denied" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_force_fail(self, db_session, db_manager):
        """Test that users cannot force-fail other tenants' jobs."""
        tenant_a = f"tk_test_{uuid4().hex[:16]}"
        tenant_b = f"tk_test_{uuid4().hex[:16]}"

        # Create job for tenant A
        job_a = AgentExecution(
            tenant_key=tenant_a,
            project_id=None,
            job_id=str(uuid4()),
            agent_display_name="implementer",
            mission="Tenant A job",
            status="working",
            messages=None,
        )

        db_session.add(job_a)
        await db_session.commit()

        # Attempt to force-fail tenant A's job using tenant B's key
        with pytest.raises(ValueError) as exc_info:
            await force_fail_job(
                job_id=job_a.job_id,
                reason="Cross-tenant attack",
                tenant_key=tenant_b,  # Wrong tenant!
                db_manager=db_manager,
            )

        # Verify error and job status unchanged
        await db_session.refresh(job_a)
        assert job_a.status == "working"  # Still working, not failed
        assert "not found" in str(exc_info.value).lower() or "access denied" in str(exc_info.value).lower()
