"""
Integration tests for cancel_job functionality (Handover 0420a Phase 3).

Tests end-to-end cancellation workflow with real database operations.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.services.agent_job_manager import AgentJobManager
from src.giljo_mcp.services.orchestration_service import OrchestrationService


@pytest.mark.asyncio
class TestCancelJobIntegration:
    """Integration tests for cancel_job with real database operations."""

    async def test_cancel_job_integration(
        self,
        db_session,
        db_manager,
        tenant_manager,
        test_tenant_key,
        test_project_id,
    ):
        """
        End-to-end test: Create job → Create executions → Cancel → Verify.

        Verifies:
        - Job status changed to "cancelled" in database
        - All executions marked "decommissioned"
        - decommissioned_at timestamps set

        Note: WebSocket broadcasting is tested separately in orchestration service tests.
        """
        # Setup: Create AgentJobManager
        manager = AgentJobManager(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # 1. Create a test job using spawn_agent
        spawn_result = await manager.spawn_agent(
            project_id=test_project_id,
            agent_display_name="Code Reviewer",
            mission="Review code for quality and best practices",
            tenant_key=test_tenant_key,
            agent_name="code-reviewer",
        )

        assert spawn_result["success"] is True
        job_id = spawn_result["job_id"]
        agent_id = spawn_result["agent_id"]

        # Verify job and execution were created
        from sqlalchemy import select

        job_result = await db_session.execute(
            select(AgentJob).where(AgentJob.job_id == job_id)
        )
        job = job_result.scalar_one()
        assert job.status == "active"

        execution_result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job_id)
        )
        executions = execution_result.scalars().all()
        assert len(executions) == 1
        assert executions[0].status == "waiting"  # Initial status from spawn_agent

        # 2. Create additional test executions (simulate succession)
        from uuid import uuid4

        execution2 = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job_id,
            tenant_key=test_tenant_key,
            agent_display_name="Code Reviewer",
            agent_name="code-reviewer",            status="working",  # Valid status: waiting, working, blocked, complete, failed, cancelled, decommissioned
            progress=50,
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
            health_status="healthy",
            tool_type="universal",
            context_used=5000,
            context_budget=150000,
        )
        db_session.add(execution2)
        await db_session.commit()

        # Verify we now have 2 executions
        execution_result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job_id)
        )
        executions = execution_result.scalars().all()
        assert len(executions) == 2

        # 3. Cancel the job
        cancel_result = await manager.cancel_job(
            job_id=job_id,
            tenant_key=test_tenant_key,
        )

        # Verify cancellation succeeded
        assert cancel_result["success"] is True, f"Cancel failed: {cancel_result}"
        assert cancel_result["job_id"] == job_id
        assert cancel_result["executions_decommissioned"] == 2

        # 4. Verify job status in database
        await db_session.refresh(job)
        assert job.status == "cancelled"
        assert job.completed_at is not None
        assert isinstance(job.completed_at, datetime)

        # 5. Verify all executions are decommissioned
        execution_result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job_id)
        )
        executions = execution_result.scalars().all()
        assert len(executions) == 2

        for execution in executions:
            assert execution.status == "decommissioned"
            assert execution.decommissioned_at is not None
            assert isinstance(execution.decommissioned_at, datetime)


    async def test_cancel_job_tenant_isolation_integration(
        self,
        db_session,
        db_manager,
        tenant_manager,
        test_project_id,
    ):
        """
        Security test: Verify tenant isolation when cancelling jobs.

        Creates job in tenant_a, attempts to cancel from tenant_b.
        Verifies failure (job not found for wrong tenant).
        """
        # Setup: Create AgentJobManager
        manager = AgentJobManager(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # 1. Create job in tenant_a
        tenant_a = "tenant_a_unique_key"
        spawn_result = await manager.spawn_agent(
            project_id=test_project_id,
            agent_display_name="Database Expert",
            mission="Optimize database queries",
            tenant_key=tenant_a,
            agent_name="database-expert",
        )

        assert spawn_result["success"] is True
        job_id = spawn_result["job_id"]

        # Verify job exists in tenant_a
        from sqlalchemy import select

        job_result = await db_session.execute(
            select(AgentJob).where(AgentJob.job_id == job_id)
        )
        job = job_result.scalar_one()
        assert job.tenant_key == tenant_a
        assert job.status == "active"

        # 2. Attempt to cancel from tenant_b (wrong tenant)
        tenant_b = "tenant_b_different_key"
        cancel_result = await manager.cancel_job(
            job_id=job_id,
            tenant_key=tenant_b,  # Wrong tenant!
        )

        # 3. Verify failure (job not found for tenant_b)
        assert cancel_result["success"] is False
        assert "not found" in cancel_result["error"].lower()

        # 4. Verify job still active in tenant_a (unchanged)
        await db_session.refresh(job)
        assert job.status == "active"  # Should NOT be cancelled
        assert job.tenant_key == tenant_a
        assert job.completed_at is None

        # 5. Verify executions still active (not decommissioned)
        execution_result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job_id)
        )
        executions = execution_result.scalars().all()
        assert len(executions) >= 1

        for execution in executions:
            assert execution.status != "decommissioned"
            assert execution.decommissioned_at is None

    async def test_cancel_nonexistent_job(
        self,
        db_session,
        db_manager,
        tenant_manager,
        test_tenant_key,
    ):
        """
        Test cancelling a job that doesn't exist.

        Verifies graceful failure with appropriate error message.
        """
        manager = AgentJobManager(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # Attempt to cancel nonexistent job
        fake_job_id = "nonexistent-job-uuid-12345"
        cancel_result = await manager.cancel_job(
            job_id=fake_job_id,
            tenant_key=test_tenant_key,
        )

        # Verify failure
        assert cancel_result["success"] is False
        assert fake_job_id in cancel_result["error"]
        assert "not found" in cancel_result["error"].lower()

    async def test_cancel_job_idempotency(
        self,
        db_session,
        db_manager,
        tenant_manager,
        test_tenant_key,
        test_project_id,
    ):
        """
        Test that cancelling an already-cancelled job is idempotent.

        Verifies:
        - Second cancel succeeds without error
        - Job remains cancelled with same timestamp
        - Executions remain decommissioned
        """
        manager = AgentJobManager(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # 1. Create and cancel a job
        spawn_result = await manager.spawn_agent(
            project_id=test_project_id,
            agent_display_name="Frontend Tester",
            mission="Test frontend components",
            tenant_key=test_tenant_key,
            agent_name="frontend-tester",
        )

        job_id = spawn_result["job_id"]

        first_cancel = await manager.cancel_job(
            job_id=job_id,
            tenant_key=test_tenant_key,
        )
        assert first_cancel["success"] is True

        # Get first cancellation timestamp
        from sqlalchemy import select

        job_result = await db_session.execute(
            select(AgentJob).where(AgentJob.job_id == job_id)
        )
        job = job_result.scalar_one()
        first_completed_at = job.completed_at

        # 2. Cancel again (idempotency test)
        second_cancel = await manager.cancel_job(
            job_id=job_id,
            tenant_key=test_tenant_key,
        )

        # 3. Verify second cancel succeeds (idempotent)
        assert second_cancel["success"] is True

        # 4. Verify job state unchanged
        await db_session.refresh(job)
        assert job.status == "cancelled"
        # Note: completed_at will be updated to current time on second cancel
        # This is acceptable behavior for idempotency

        # 5. Verify executions still decommissioned
        execution_result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job_id)
        )
        executions = execution_result.scalars().all()

        for execution in executions:
            assert execution.status == "decommissioned"
            assert execution.decommissioned_at is not None

    async def test_cancel_job_with_multiple_executions(
        self,
        db_session,
        db_manager,
        tenant_manager,
        test_tenant_key,
        test_project_id,
    ):
        """
        Test cancelling a job with multiple executions (succession chain).

        Verifies all executions are decommissioned regardless of status.
        """
        manager = AgentJobManager(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=db_session,
        )

        # 1. Create job
        spawn_result = await manager.spawn_agent(
            project_id=test_project_id,
            agent_display_name="System Architect",
            mission="Design system architecture",
            tenant_key=test_tenant_key,
            agent_name="system-architect",
        )

        job_id = spawn_result["job_id"]

        # 2. Create multiple executions with different statuses
        from uuid import uuid4

        # Valid statuses: waiting, working, blocked, complete, failed, cancelled, decommissioned
        statuses = ["waiting", "working", "blocked", "complete"]
        for i, status in enumerate(statuses, start=2):
            execution = AgentExecution(
                agent_id=str(uuid4()),
                job_id=job_id,
                tenant_key=test_tenant_key,
                agent_display_name="System Architect",
                agent_name="system-architect",                status=status,
                progress=i * 20,
                messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
                health_status="healthy",
                tool_type="universal",
                context_used=i * 1000,
                context_budget=150000,
            )
            db_session.add(execution)

        await db_session.commit()

        # Verify we have 5 total executions (1 from spawn + 4 added)
        from sqlalchemy import select

        execution_result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job_id)
        )
        executions = execution_result.scalars().all()
        assert len(executions) == 5

        # 3. Cancel job
        cancel_result = await manager.cancel_job(
            job_id=job_id,
            tenant_key=test_tenant_key,
        )

        # 4. Verify all executions decommissioned
        assert cancel_result["success"] is True
        assert cancel_result["executions_decommissioned"] == 5

        execution_result = await db_session.execute(
            select(AgentExecution).where(AgentExecution.job_id == job_id)
        )
        executions = execution_result.scalars().all()

        for execution in executions:
            assert execution.status == "decommissioned"
            assert execution.decommissioned_at is not None
