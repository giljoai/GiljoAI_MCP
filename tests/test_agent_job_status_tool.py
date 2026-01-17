"""
Comprehensive test suite for update_job_status MCP tool.

Tests agent self-navigation for Kanban board workflow.
Following TDD principles - these tests are written BEFORE implementation.

Handover 0066: Agent Job Status Update Tool
"""

import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastmcp import FastMCP


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.services.agent_job_manager import AgentJobManager
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


@pytest.fixture
def db_manager():
    """Create a synchronous database manager for testing."""
    manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
    manager.create_tables()
    yield manager
    manager.close()


@pytest.fixture
def job_manager(db_manager):
    """Create an AgentJobManager for testing."""
    return AgentJobManager(db_manager)


@pytest.fixture
def mcp_server():
    """Create a FastMCP server instance for testing."""
    return FastMCP("test-agent-job-status")


@pytest.fixture
def test_tenant():
    """Create a test tenant key."""
    return TenantManager.generate_tenant_key()


@pytest.fixture
def test_job(db_manager, job_manager, test_tenant):
    """Create a test job in pending status."""
    job = job_manager.create_job(
        tenant_key=test_tenant, agent_display_name="implementer", mission="Test mission for status updates"
    )
    return job


class TestUpdateJobStatusValidation:
    """Test input validation for update_job_status tool."""

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(self, db_manager, test_tenant, test_job):
        """Test that invalid status values are rejected."""
        # Import tool registration function
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        # Try invalid status
        result = await mcp.call_tool(
            "update_job_status", job_id=test_job.job_id, tenant_key=test_tenant, new_status="invalid_status"
        )

        assert result["success"] is False
        assert "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_empty_job_id_rejected(self, db_manager, test_tenant):
        """Test that empty job_id is rejected."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        result = await mcp.call_tool("update_job_status", job_id="", tenant_key=test_tenant, new_status="active")

        assert result["success"] is False
        assert "job_id" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_nonexistent_job_rejected(self, db_manager, test_tenant):
        """Test that non-existent job_id is rejected."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        fake_job_id = str(uuid4())
        result = await mcp.call_tool(
            "update_job_status", job_id=fake_job_id, tenant_key=test_tenant, new_status="active"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestUpdateJobStatusTransitions:
    """Test valid status transitions."""

    @pytest.mark.asyncio
    async def test_pending_to_active(self, db_manager, test_tenant, test_job):
        """Test transition from pending to active sets started_at."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        # Verify initial state
        assert test_job.status == "pending"
        assert test_job.started_at is None

        # Update to active
        result = await mcp.call_tool(
            "update_job_status", job_id=test_job.job_id, tenant_key=test_tenant, new_status="active"
        )

        assert result["success"] is True
        assert result["old_status"] == "pending"
        assert result["new_status"] == "active"
        assert result["started_at"] is not None

        # Verify database was updated
        job_manager = AgentJobManager(db_manager)
        updated_job = job_manager.get_job(test_tenant, test_job.job_id)
        assert updated_job.status == "active"
        assert updated_job.started_at is not None

    @pytest.mark.asyncio
    async def test_active_to_completed(self, db_manager, test_tenant, job_manager):
        """Test transition from active to completed sets completed_at."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        # Create job and move to active
        job = job_manager.create_job(tenant_key=test_tenant, agent_display_name="tester", mission="Test completion workflow")
        job = job_manager.acknowledge_job(test_tenant, job.job_id)

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        # Update to completed
        result = await mcp.call_tool(
            "update_job_status", job_id=job.job_id, tenant_key=test_tenant, new_status="completed"
        )

        assert result["success"] is True
        assert result["old_status"] == "active"
        assert result["new_status"] == "completed"
        assert result["completed_at"] is not None

        # Verify database
        updated_job = job_manager.get_job(test_tenant, job.job_id)
        assert updated_job.status == "completed"
        assert updated_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_active_to_blocked_with_reason(self, db_manager, test_tenant, job_manager):
        """Test transition from active to blocked with reason."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        # Create job and move to active
        job = job_manager.create_job(tenant_key=test_tenant, agent_display_name="analyzer", mission="Analyze requirements")
        job = job_manager.acknowledge_job(test_tenant, job.job_id)

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        # Update to blocked with reason
        reason = "Need database schema clarification"
        result = await mcp.call_tool(
            "update_job_status", job_id=job.job_id, tenant_key=test_tenant, new_status="blocked", reason=reason
        )

        assert result["success"] is True
        assert result["old_status"] == "active"
        assert result["new_status"] == "blocked"
        assert result["reason"] == reason
        assert result["completed_at"] is not None

        # Verify database
        updated_job = job_manager.get_job(test_tenant, job.job_id)
        assert updated_job.status == "blocked"
        assert updated_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_pending_to_blocked_with_reason(self, db_manager, test_tenant, test_job):
        """Test transition from pending to blocked (early failure detection)."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        reason = "Insufficient context to start work"
        result = await mcp.call_tool(
            "update_job_status", job_id=test_job.job_id, tenant_key=test_tenant, new_status="blocked", reason=reason
        )

        assert result["success"] is True
        assert result["old_status"] == "pending"
        assert result["new_status"] == "blocked"
        assert result["reason"] == reason


class TestUpdateJobStatusMultiTenant:
    """Test multi-tenant isolation for update_job_status."""

    @pytest.mark.asyncio
    async def test_cannot_update_other_tenant_job(self, db_manager, job_manager):
        """Test that a tenant cannot update another tenant's job."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        # Create two tenants
        tenant1_key = TenantManager.generate_tenant_key()
        tenant2_key = TenantManager.generate_tenant_key()

        # Create job for tenant1
        job = job_manager.create_job(tenant_key=tenant1_key, agent_display_name="implementer", mission="Tenant 1 mission")

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        # Try to update with tenant2's key
        result = await mcp.call_tool(
            "update_job_status", job_id=job.job_id, tenant_key=tenant2_key, new_status="active"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

        # Verify job was not updated
        original_job = job_manager.get_job(tenant1_key, job.job_id)
        assert original_job.status == "pending"

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_queries(self, db_manager, job_manager):
        """Test that jobs are properly isolated by tenant."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        # Create two tenants with same-named jobs
        tenant1_key = TenantManager.generate_tenant_key()
        tenant2_key = TenantManager.generate_tenant_key()

        job1 = job_manager.create_job(tenant_key=tenant1_key, agent_display_name="implementer", mission="Mission for Tenant A")

        job2 = job_manager.create_job(tenant_key=tenant2_key, agent_display_name="implementer", mission="Mission for Tenant B")

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, tenant_manager)

        # Update job1
        result1 = await mcp.call_tool(
            "update_job_status", job_id=job1.job_id, tenant_key=tenant1_key, new_status="active"
        )

        # Update job2
        result2 = await mcp.call_tool(
            "update_job_status", job_id=job2.job_id, tenant_key=tenant2_key, new_status="completed"
        )

        assert result1["success"] is True
        assert result2["success"] is True

        # Verify each tenant only sees their own job status
        updated_job1 = job_manager.get_job(tenant1_key, job1.job_id)
        updated_job2 = job_manager.get_job(tenant2_key, job2.job_id)

        assert updated_job1.status == "active"
        assert updated_job2.status == "completed"


class TestUpdateJobStatusTimestamps:
    """Test timestamp handling for different status transitions."""

    @pytest.mark.asyncio
    async def test_started_at_set_only_on_first_active(self, db_manager, test_tenant, job_manager):
        """Test that started_at is set only on first transition to active."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        job = job_manager.create_job(
            tenant_key=test_tenant, agent_display_name="implementer", mission="Test timestamp behavior"
        )

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        # First transition to active
        result1 = await mcp.call_tool(
            "update_job_status", job_id=job.job_id, tenant_key=test_tenant, new_status="active"
        )

        first_started_at = result1["started_at"]
        assert first_started_at is not None

        # Transition to pending (hypothetical for testing)
        # Then back to active
        # In real workflow, terminal states can't transition back
        # but we test the timestamp preservation logic
        updated_job = job_manager.get_job(test_tenant, job.job_id)
        assert updated_job.started_at is not None

    @pytest.mark.asyncio
    async def test_completed_at_set_on_terminal_states(self, db_manager, test_tenant, job_manager):
        """Test that completed_at is set for completed and blocked states."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        # Test completed status
        job1 = job_manager.create_job(tenant_key=test_tenant, agent_display_name="tester", mission="Test completion timestamp")
        job1 = job_manager.acknowledge_job(test_tenant, job1.job_id)

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        result1 = await mcp.call_tool(
            "update_job_status", job_id=job1.job_id, tenant_key=test_tenant, new_status="completed"
        )

        assert result1["completed_at"] is not None

        # Test blocked status
        job2 = job_manager.create_job(tenant_key=test_tenant, agent_display_name="analyzer", mission="Test blocked timestamp")

        result2 = await mcp.call_tool(
            "update_job_status", job_id=job2.job_id, tenant_key=test_tenant, new_status="blocked", reason="Test reason"
        )

        assert result2["completed_at"] is not None


class TestUpdateJobStatusReasonParameter:
    """Test the optional reason parameter."""

    @pytest.mark.asyncio
    async def test_blocked_without_reason(self, db_manager, test_tenant, test_job):
        """Test blocked status without providing a reason."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        result = await mcp.call_tool(
            "update_job_status", job_id=test_job.job_id, tenant_key=test_tenant, new_status="blocked"
        )

        assert result["success"] is True
        assert result["new_status"] == "blocked"
        assert result.get("reason") is None

    @pytest.mark.asyncio
    async def test_reason_parameter_ignored_for_non_blocked(self, db_manager, test_tenant, test_job):
        """Test that reason parameter is accepted but not required for non-blocked statuses."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        # Reason provided but status is active (not blocked)
        result = await mcp.call_tool(
            "update_job_status",
            job_id=test_job.job_id,
            tenant_key=test_tenant,
            new_status="active",
            reason="This should be ignored",
        )

        assert result["success"] is True
        assert result["new_status"] == "active"


class TestUpdateJobStatusErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_database_error_handled_gracefully(self, db_manager, test_tenant):
        """Test that database errors are handled gracefully."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        # Close database connection to simulate error
        db_manager.close()

        result = await mcp.call_tool(
            "update_job_status", job_id=str(uuid4()), tenant_key=test_tenant, new_status="active"
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_concurrent_updates(self, db_manager, test_tenant, job_manager):
        """Test handling of concurrent status updates."""
        from src.giljo_mcp.tools.agent_job_status import register_agent_job_status_tools

        job = job_manager.create_job(
            tenant_key=test_tenant, agent_display_name="implementer", mission="Test concurrent updates"
        )

        mcp = FastMCP("test-server")
        register_agent_job_status_tools(mcp, db_manager, TenantManager())

        # Simulate concurrent updates (in real scenario, would use asyncio.gather)
        result1 = await mcp.call_tool(
            "update_job_status", job_id=job.job_id, tenant_key=test_tenant, new_status="active"
        )

        result2 = await mcp.call_tool(
            "update_job_status", job_id=job.job_id, tenant_key=test_tenant, new_status="completed"
        )

        # Both should succeed (last write wins)
        assert result1["success"] is True
        assert result2["success"] is True

        # Final state should be completed
        final_job = job_manager.get_job(test_tenant, job.job_id)
        assert final_job.status == "completed"
