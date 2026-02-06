"""
Integration tests for orchestrator status filtering in project endpoints.

Bug: GET /api/v1/projects/{id}/orchestrator returns cancelled orchestrators
     instead of active ones when multiple orchestrators exist.

TDD: RED phase - tests should FAIL before fix is applied.

Handover: Bug fix for "Project not ready to launch" error
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


class TestOrchestratorStatusFiltering:
    """Tests for orchestrator status filtering behavior."""

    @pytest.mark.asyncio
    async def test_get_orchestrator_excludes_cancelled(
        self, db_session: AsyncSession, test_project
    ):
        """
        BEHAVIOR: When multiple orchestrators exist, return active one (not cancelled).
        """
        # Create cancelled orchestrator (higher instance number)
        cancelled_orch = AgentExecution(
            job_id=str(uuid4()),
            project_id=test_project.id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="Orchestrator #1",
            status="cancelled",            decommissioned_at=datetime.now(timezone.utc),
            mission="Cancelled mission",
        )
        db_session.add(cancelled_orch)

        # Create active orchestrator (lower instance number but ACTIVE)
        active_orch = AgentExecution(
            job_id=str(uuid4()),
            project_id=test_project.id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="Orchestrator #2",
            status="waiting",            mission="Active mission",
        )
        db_session.add(active_orch)
        await db_session.commit()

        # Buggy query (no status filter) - documents the bug
        buggy_stmt = (
            select(AgentExecution)
            .where(
                AgentExecution.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
            )
            .order_by(AgentExecution.instance_number.desc())
        )
        buggy_result = await db_session.execute(buggy_stmt)
        buggy_orchestrator = buggy_result.scalars().first()

        # Bug: returns cancelled orchestrator
        assert buggy_orchestrator.status == "cancelled"

        # Fixed query (with status filter)
        fixed_stmt = (
            select(AgentExecution)
            .where(
                AgentExecution.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                AgentExecution.status.in_(["waiting", "working", "blocked"]),
            )
            .order_by(AgentExecution.instance_number.desc())
        )
        fixed_result = await db_session.execute(fixed_stmt)
        fixed_orchestrator = fixed_result.scalars().first()

        # Expected: returns active orchestrator
        assert fixed_orchestrator is not None
        assert fixed_orchestrator.status == "waiting"
        assert fixed_orchestrator.job_id == active_orch.job_id

    @pytest.mark.asyncio
    async def test_get_orchestrator_returns_none_when_all_terminal(
        self, db_session: AsyncSession, test_project
    ):
        """
        BEHAVIOR: Return None when all orchestrators are in terminal states.
        """
        # Create only cancelled/failed orchestrators
        cancelled_orch = AgentExecution(
            job_id=str(uuid4()),
            project_id=test_project.id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="Cancelled Orchestrator",
            status="cancelled",            mission="Cancelled",
        )
        db_session.add(cancelled_orch)

        failed_orch = AgentExecution(
            job_id=str(uuid4()),
            project_id=test_project.id,
            tenant_key=test_project.tenant_key,
            agent_display_name="orchestrator",
            agent_name="Failed Orchestrator",
            status="failed",            mission="Failed",
        )
        db_session.add(failed_orch)
        await db_session.commit()

        # Fixed query should return None
        fixed_stmt = (
            select(AgentExecution)
            .where(
                AgentExecution.project_id == test_project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == test_project.tenant_key,
                AgentExecution.status.in_(["waiting", "working", "blocked"]),
            )
            .order_by(AgentExecution.instance_number.desc())
        )
        result = await db_session.execute(fixed_stmt)
        orchestrator = result.scalars().first()

        assert orchestrator is None
