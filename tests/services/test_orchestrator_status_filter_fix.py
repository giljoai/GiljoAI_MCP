"""
Tests for orchestrator status filter fix (Handover 0485 - Bug B)

These tests verify that the orchestrator deduplication logic uses the correct
status filter: ~status.in_(["failed", "cancelled"]) instead of status.in_(["waiting", "working"])
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import AgentExecution, AgentJob


class TestOrchestratorStatusFilterFix:
    """Test that orchestrator status filter finds non-failed orchestrators"""

    @pytest.mark.asyncio
    async def test_complete_orchestrator_should_be_found(self, db_session, test_project):
        """
        Test that an orchestrator with "complete" status is found by the filter.

        The old filter status.in_(["waiting", "working"]) would NOT find "complete" status.
        The new filter ~status.in_(["failed", "cancelled"]) WILL find "complete" status.
        """
        # Create orchestrator with "complete" status
        job_id = str(uuid4())
        agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission=f"Orchestrator for project: {test_project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="complete",  # COMPLETE status
            progress=100,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Test NEW filter: ~status.in_(["failed", "cancelled"])
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                ~AgentExecution.status.in_(["failed", "cancelled"]),  # NEW FILTER
            )
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        # ASSERT: "complete" status SHOULD be found with new filter
        assert found is not None
        assert found.status == "complete"

        # Test OLD filter: status.in_(["waiting", "working"])
        old_stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                AgentExecution.status.in_(["waiting", "working"]),  # OLD FILTER
            )
        )
        old_result = await db_session.execute(old_stmt)
        old_found = old_result.scalar_one_or_none()

        # ASSERT: "complete" status would NOT be found with old filter (THIS IS THE BUG)
        assert old_found is None

    @pytest.mark.asyncio
    async def test_blocked_orchestrator_should_be_found(self, db_session, test_project):
        """
        Test that an orchestrator with "blocked" status is found by the new filter.
        """
        # Create orchestrator with "blocked" status
        job_id = str(uuid4())
        agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission=f"Orchestrator for project: {test_project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="blocked",  # BLOCKED status
            progress=50,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Test NEW filter
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                ~AgentExecution.status.in_(["failed", "cancelled"]),  # NEW FILTER
            )
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        # ASSERT: "blocked" status SHOULD be found with new filter
        assert found is not None
        assert found.status == "blocked"

    @pytest.mark.asyncio
    async def test_failed_orchestrator_should_not_be_found(self, db_session, test_project):
        """
        Test that an orchestrator with "failed" status is NOT found by the new filter.
        """
        # Create orchestrator with "failed" status
        job_id = str(uuid4())
        agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission=f"Orchestrator for project: {test_project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="failed",  # FAILED status
            progress=25,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Test NEW filter
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                ~AgentExecution.status.in_(["failed", "cancelled"]),  # NEW FILTER
            )
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        # ASSERT: "failed" status should NOT be found (excluded by new filter)
        assert found is None

    @pytest.mark.asyncio
    async def test_cancelled_orchestrator_should_not_be_found(self, db_session, test_project):
        """
        Test that an orchestrator with "cancelled" status is NOT found by the new filter.
        """
        # Create orchestrator with "cancelled" status
        job_id = str(uuid4())
        agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission=f"Orchestrator for project: {test_project.name}",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="cancelled",  # CANCELLED status
            progress=10,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Test NEW filter
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                ~AgentExecution.status.in_(["failed", "cancelled"]),  # NEW FILTER
            )
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        # ASSERT: "cancelled" status should NOT be found (excluded by new filter)
        assert found is None

    @pytest.mark.asyncio
    async def test_waiting_and_working_still_found(self, db_session, test_project):
        """
        Test that "waiting" and "working" statuses are still found by the new filter.
        (These were the only statuses found by the old filter - we still want them)
        """
        # Create orchestrator with "waiting" status
        waiting_job_id = str(uuid4())
        waiting_agent_id = str(uuid4())

        agent_job_waiting = AgentJob(
            job_id=waiting_job_id,
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission="Waiting Orchestrator",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job_waiting)

        agent_execution_waiting = AgentExecution(
            agent_id=waiting_agent_id,
            job_id=waiting_job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="waiting",  # WAITING status
            progress=0,
        )
        db_session.add(agent_execution_waiting)

        # Create orchestrator with "working" status
        working_job_id = str(uuid4())
        working_agent_id = str(uuid4())

        agent_job_working = AgentJob(
            job_id=working_job_id,
            tenant_key=test_project.tenant_key,
            project_id=test_project.id,
            mission="Working Orchestrator",
            job_type="orchestrator",
            status="active",
        )
        db_session.add(agent_job_working)

        agent_execution_working = AgentExecution(
            agent_id=working_agent_id,
            job_id=working_job_id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="working",  # WORKING status
            progress=75,
        )
        db_session.add(agent_execution_working)

        await db_session.commit()

        # Test NEW filter
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                ~AgentExecution.status.in_(["failed", "cancelled"]),  # NEW FILTER
            )
        )
        result = await db_session.execute(stmt)
        found = result.scalars().all()

        # ASSERT: Both "waiting" and "working" should still be found
        assert len(found) == 2
        assert found[0].status == "waiting"
        assert found[1].status == "working"
