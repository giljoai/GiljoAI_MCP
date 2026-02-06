"""
Comprehensive test suite for update_job_status MCP tool.

Tests agent self-navigation for job status management.
Following TDD principles - these tests are written BEFORE implementation.

Handover 0066: Agent Job Status Update Tool

NOTE: AgentJob statuses are: active, completed, cancelled (per database schema)
AgentExecution has different statuses: waiting, working, blocked, complete, cancelled, failed, decommissioned
"""

import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

import pytest
import pytest_asyncio


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def test_job_active(db_session, test_tenant_key):
    """Create a test AgentJob in active status."""
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

    # Create AgentJob (work order) - statuses: active, completed, cancelled
    job = AgentJob(
        job_id=str(uuid4()),
        tenant_key=test_tenant_key,
        project_id=None,  # project_id is nullable
        job_type="implementer",
        mission="Test mission for status updates",
        status="active",
        created_at=datetime.now(timezone.utc),
        job_metadata={},
    )
    db_session.add(job)

    # Create AgentExecution (executor)
    execution = AgentExecution(
        agent_id=str(uuid4()),
        job_id=job.job_id,
        tenant_key=test_tenant_key,
        agent_display_name="implementer",
        agent_name="Test Implementer",        status="working",
        progress=0,
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        health_status="healthy",
        tool_type="universal",
        context_used=0,
        context_budget=150000,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(job)

    return job


class TestUpdateJobStatusValidation:
    """Test input validation for update_job_status tool."""

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(self, test_tenant_key, test_job_active):
        """Test that invalid status values are rejected."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status

        # Try invalid status
        result = await update_job_status(
            job_id=test_job_active.job_id, tenant_key=test_tenant_key, new_status="invalid_status"
        )

        assert result["success"] is False
        assert "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_empty_job_id_rejected(self, test_tenant_key):
        """Test that empty job_id is rejected."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status

        result = await update_job_status(job_id="", tenant_key=test_tenant_key, new_status="active")

        assert result["success"] is False
        assert "job_id" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_nonexistent_job_rejected(self, test_tenant_key):
        """Test that non-existent job_id is rejected."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status

        fake_job_id = str(uuid4())
        result = await update_job_status(
            job_id=fake_job_id, tenant_key=test_tenant_key, new_status="active"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestUpdateJobStatusTransitions:
    """Test valid status transitions."""

    @pytest.mark.asyncio
    async def test_active_to_completed(self, test_tenant_key, test_job_active):
        """Test transition from active to completed sets completed_at."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status, get_job_status

        # Verify initial state
        assert test_job_active.status == "active"

        # Update to completed
        result = await update_job_status(
            job_id=test_job_active.job_id, tenant_key=test_tenant_key, new_status="completed"
        )

        assert result["success"] is True
        assert result["old_status"] == "active"
        assert result["new_status"] == "completed"
        assert result["completed_at"] is not None

        # Verify database was updated
        status = await get_job_status(job_id=test_job_active.job_id, tenant_key=test_tenant_key)
        assert status["success"] is True
        assert status["status"] == "completed"
        assert status["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_active_to_cancelled(self, test_tenant_key, test_job_active):
        """Test transition from active to cancelled sets completed_at."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status, get_job_status

        # Update to cancelled
        result = await update_job_status(
            job_id=test_job_active.job_id, tenant_key=test_tenant_key, new_status="cancelled"
        )

        assert result["success"] is True
        assert result["old_status"] == "active"
        assert result["new_status"] == "cancelled"
        assert result["completed_at"] is not None

        # Verify database
        status = await get_job_status(job_id=test_job_active.job_id, tenant_key=test_tenant_key)
        assert status["success"] is True
        assert status["status"] == "cancelled"
        assert status["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_active_to_cancelled_with_reason(self, test_tenant_key, test_job_active):
        """Test transition from active to cancelled with reason."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status, get_job_status

        # Update to cancelled with reason
        reason = "Need database schema clarification"
        result = await update_job_status(
            job_id=test_job_active.job_id, tenant_key=test_tenant_key, new_status="cancelled", reason=reason
        )

        assert result["success"] is True
        assert result["old_status"] == "active"
        assert result["new_status"] == "cancelled"
        assert result["reason"] == reason
        assert result["completed_at"] is not None

        # Verify database
        status = await get_job_status(job_id=test_job_active.job_id, tenant_key=test_tenant_key)
        assert status["success"] is True
        assert status["status"] == "cancelled"


class TestUpdateJobStatusMultiTenant:
    """Test multi-tenant isolation for update_job_status."""

    @pytest.mark.asyncio
    async def test_cannot_update_other_tenant_job(self, db_session):
        """Test that a tenant cannot update another tenant's job."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status
        from src.giljo_mcp.models.agent_identity import AgentJob

        # Create two tenants
        tenant1_key = TenantManager.generate_tenant_key()
        tenant2_key = TenantManager.generate_tenant_key()

        # Create job for tenant1
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant1_key,
            project_id=None,  # project_id is nullable
            job_type="implementer",
            mission="Tenant 1 mission",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(job)
        await db_session.commit()

        # Try to update with tenant2's key
        result = await update_job_status(
            job_id=job.job_id, tenant_key=tenant2_key, new_status="completed"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

        # Verify job was not updated
        await db_session.refresh(job)
        assert job.status == "active"

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_queries(self, db_session):
        """Test that jobs are properly isolated by tenant."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status, get_job_status
        from src.giljo_mcp.models.agent_identity import AgentJob

        # Create two tenants with same-named jobs
        tenant1_key = TenantManager.generate_tenant_key()
        tenant2_key = TenantManager.generate_tenant_key()

        job1 = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant1_key,
            project_id=None,  # project_id is nullable
            job_type="implementer",
            mission="Mission for Tenant A",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(job1)

        job2 = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant2_key,
            project_id=None,  # project_id is nullable
            job_type="implementer",
            mission="Mission for Tenant B",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(job2)
        await db_session.commit()

        # Update job1 to cancelled
        result1 = await update_job_status(
            job_id=job1.job_id, tenant_key=tenant1_key, new_status="cancelled"
        )

        # Update job2 to completed
        result2 = await update_job_status(
            job_id=job2.job_id, tenant_key=tenant2_key, new_status="completed"
        )

        assert result1["success"] is True
        assert result2["success"] is True

        # Verify each tenant only sees their own job status
        status1 = await get_job_status(job_id=job1.job_id, tenant_key=tenant1_key)
        status2 = await get_job_status(job_id=job2.job_id, tenant_key=tenant2_key)

        assert status1["status"] == "cancelled"
        assert status2["status"] == "completed"


class TestUpdateJobStatusTimestamps:
    """Test timestamp handling for different status transitions."""

    @pytest.mark.asyncio
    async def test_completed_at_set_on_terminal_states(self, db_session, test_tenant_key):
        """Test that completed_at is set for completed and cancelled states."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status
        from src.giljo_mcp.models.agent_identity import AgentJob

        # Test completed status
        job1 = AgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=None,  # project_id is nullable
            job_type="tester",
            mission="Test completion timestamp",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(job1)

        # Test cancelled status
        job2 = AgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=None,  # project_id is nullable
            job_type="analyzer",
            mission="Test cancelled timestamp",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(job2)
        await db_session.commit()

        result1 = await update_job_status(
            job_id=job1.job_id, tenant_key=test_tenant_key, new_status="completed"
        )
        assert result1["completed_at"] is not None

        result2 = await update_job_status(
            job_id=job2.job_id, tenant_key=test_tenant_key, new_status="cancelled", reason="Test reason"
        )
        assert result2["completed_at"] is not None


class TestUpdateJobStatusReasonParameter:
    """Test the optional reason parameter."""

    @pytest.mark.asyncio
    async def test_cancelled_without_reason(self, test_tenant_key, test_job_active):
        """Test cancelled status without providing a reason."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status

        result = await update_job_status(
            job_id=test_job_active.job_id, tenant_key=test_tenant_key, new_status="cancelled"
        )

        assert result["success"] is True
        assert result["new_status"] == "cancelled"
        assert result.get("reason") is None

    @pytest.mark.asyncio
    async def test_reason_parameter_accepted_for_any_status(self, test_tenant_key, test_job_active):
        """Test that reason parameter is accepted for any status transition."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status

        # Reason provided for completed status
        result = await update_job_status(
            job_id=test_job_active.job_id,
            tenant_key=test_tenant_key,
            new_status="completed",
            reason="Successfully finished all tasks",
        )

        assert result["success"] is True
        assert result["new_status"] == "completed"
        # Reason is captured in response even for non-cancelled statuses
        assert result.get("reason") == "Successfully finished all tasks"


class TestUpdateJobStatusErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_database_error_handled_gracefully(self, test_tenant_key):
        """Test that database errors are handled gracefully."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status

        # Try to update non-existent job
        result = await update_job_status(
            job_id=str(uuid4()), tenant_key=test_tenant_key, new_status="active"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_concurrent_updates(self, db_session, test_tenant_key):
        """Test handling of concurrent status updates."""
        from src.giljo_mcp.tools.agent_job_status import update_job_status, get_job_status
        from src.giljo_mcp.models.agent_identity import AgentJob

        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=test_tenant_key,
            project_id=None,  # project_id is nullable
            job_type="implementer",
            mission="Test concurrent updates",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(job)
        await db_session.commit()

        # Simulate concurrent updates (in real scenario, would use asyncio.gather)
        # First update: still active (no change)
        result1 = await update_job_status(
            job_id=job.job_id, tenant_key=test_tenant_key, new_status="active"
        )

        # Second update: completed
        result2 = await update_job_status(
            job_id=job.job_id, tenant_key=test_tenant_key, new_status="completed"
        )

        # Both should succeed (last write wins)
        assert result1["success"] is True
        assert result2["success"] is True

        # Final state should be completed
        status = await get_job_status(job_id=job.job_id, tenant_key=test_tenant_key)
        assert status["status"] == "completed"
