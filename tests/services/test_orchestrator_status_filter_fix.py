# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for orchestrator status filter (Handover 0491 - Agent Status Simplification)

These tests verify that the orchestrator deduplication logic uses the correct
status filter: ~status.in_(["decommissioned"]) - only decommissioned agents are excluded.

Handover 0491: Simplified from ~status.in_(["failed", "cancelled"]) to ~status.in_(["decommissioned"]).
The statuses 'failed' and 'cancelled' no longer exist for AgentExecution.
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from src.giljo_mcp.models import AgentExecution, AgentJob


class TestOrchestratorStatusFilterFix:
    """Test that orchestrator status filter finds non-decommissioned orchestrators"""

    @pytest.mark.asyncio
    async def test_complete_orchestrator_should_be_found(self, db_session, test_project):
        """
        Test that an orchestrator with "complete" status is found by the filter.
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

        # Test filter: ~status.in_(["decommissioned"])
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                ~AgentExecution.status.in_(["decommissioned"]),  # Handover 0491
            )
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        # ASSERT: "complete" status SHOULD be found
        assert found is not None
        assert found.status == "complete"

    @pytest.mark.asyncio
    async def test_blocked_orchestrator_should_be_found(self, db_session, test_project):
        """
        Test that an orchestrator with "blocked" status is found by the filter.
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

        # Test filter
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                ~AgentExecution.status.in_(["decommissioned"]),  # Handover 0491
            )
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        # ASSERT: "blocked" status SHOULD be found
        assert found is not None
        assert found.status == "blocked"

    @pytest.mark.asyncio
    async def test_silent_orchestrator_should_be_found(self, db_session, test_project):
        """
        Test that an orchestrator with "silent" status is found by the filter.
        Handover 0491: silent is a new status for inactive agents.
        """
        # Create orchestrator with "silent" status
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
            status="silent",  # SILENT status
            progress=25,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Test filter
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                ~AgentExecution.status.in_(["decommissioned"]),  # Handover 0491
            )
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        # ASSERT: "silent" status SHOULD be found (agent may recover)
        assert found is not None
        assert found.status == "silent"

    @pytest.mark.asyncio
    async def test_decommissioned_orchestrator_should_not_be_found(self, db_session, test_project):
        """
        Test that an orchestrator with "decommissioned" status is NOT found by the filter.
        """
        # Create orchestrator with "decommissioned" status
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
            status="decommissioned",  # DECOMMISSIONED status
            progress=10,
        )
        db_session.add(agent_execution)
        await db_session.commit()

        # Test filter
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                ~AgentExecution.status.in_(["decommissioned"]),  # Handover 0491
            )
        )
        result = await db_session.execute(stmt)
        found = result.scalar_one_or_none()

        # ASSERT: "decommissioned" status should NOT be found (excluded by filter)
        assert found is None

    @pytest.mark.asyncio
    async def test_waiting_and_working_still_found(self, db_session, test_project):
        """
        Test that "waiting" and "working" statuses are still found by the filter.
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

        # Test filter
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                ~AgentExecution.status.in_(["decommissioned"]),  # Handover 0491
            )
        )
        result = await db_session.execute(stmt)
        found = result.scalars().all()

        # ASSERT: Both "waiting" and "working" should still be found
        assert len(found) == 2
        statuses = {f.status for f in found}
        assert statuses == {"waiting", "working"}
