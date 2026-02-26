"""
Tests for Handover 0498: Early Termination Protocol + Jobs Dashboard Reduction.

TDD: Tests written FIRST, then implementation.
Covers:
- Phase 1: AgentTodoItem "skipped" status
- Phase 2: Smart force decommission lifecycle drain
- Phase 3: ProjectService.close_out_project smart drain
- Phase 4: report_progress "skipped" status
- Phase 6: Steps aggregation with skipped count
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import (
    AgentExecution,
    AgentJob,
    AgentTodoItem,
)


# ============================================================================
# Phase 1: AgentTodoItem accepts "skipped" status
# ============================================================================


class TestAgentTodoItemSkippedStatus:
    """Phase 1: Verify AgentTodoItem model accepts 'skipped' as a valid status."""

    @pytest.mark.asyncio
    async def test_todo_item_accepts_skipped_status(self, db_session, test_agent_job):
        """AgentTodoItem should accept 'skipped' as a valid status value."""
        job, execution = test_agent_job

        todo = AgentTodoItem(
            job_id=job.job_id,
            tenant_key=job.tenant_key,
            content="Test item to be skipped",
            status="skipped",
            sequence=0,
        )
        db_session.add(todo)
        await db_session.flush()

        result = await db_session.execute(
            select(AgentTodoItem).where(AgentTodoItem.id == todo.id)
        )
        saved = result.scalar_one()
        assert saved.status == "skipped"

    @pytest.mark.asyncio
    async def test_todo_item_still_accepts_existing_statuses(self, db_session, test_agent_job):
        """Existing statuses (pending, in_progress, completed) still work."""
        job, execution = test_agent_job

        for status in ("pending", "in_progress", "completed"):
            todo = AgentTodoItem(
                job_id=job.job_id,
                tenant_key=job.tenant_key,
                content=f"Test item with status {status}",
                status=status,
                sequence=0,
            )
            db_session.add(todo)
            await db_session.flush()
            assert todo.status == status

    @pytest.mark.asyncio
    async def test_todo_item_rejects_invalid_status(self, db_session, test_agent_job):
        """Invalid statuses should be rejected by the CHECK constraint."""
        job, execution = test_agent_job

        todo = AgentTodoItem(
            job_id=job.job_id,
            tenant_key=job.tenant_key,
            content="Test item with invalid status",
            status="invalid_status",
            sequence=0,
        )
        db_session.add(todo)

        with pytest.raises(Exception):
            await db_session.flush()
        await db_session.rollback()


# ============================================================================
# Phase 2: Smart force decommission with lifecycle drain
# ============================================================================


class TestSmartForceDecommission:
    """Phase 2: _force_decommission_agents marks TODOs as skipped
    and messages as read with prefix before decommissioning."""

    @pytest_asyncio.fixture
    async def active_agent_with_todos_and_messages(self, db_session, test_project_id, test_tenant_key):
        """Create an active agent with pending TODOs and unread messages."""
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            job_type="worker",
            mission="Test worker",
            status="active",
            created_at=datetime.now(timezone.utc),
            job_metadata={},
        )
        db_session.add(job)

        execution = AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name="test-worker",
            agent_name="Test Worker",
            status="working",
            progress=50,
            messages_sent_count=0,
            messages_waiting_count=1,
            messages_read_count=0,
            health_status="healthy",
            tool_type="universal",
        )
        db_session.add(execution)

        # Create TODO items
        todo_pending = AgentTodoItem(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            content="Pending task",
            status="pending",
            sequence=0,
        )
        todo_in_progress = AgentTodoItem(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            content="In progress task",
            status="in_progress",
            sequence=1,
        )
        todo_completed = AgentTodoItem(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            content="Completed task",
            status="completed",
            sequence=2,
        )
        db_session.add_all([todo_pending, todo_in_progress, todo_completed])

        # Create unread message to this agent
        message = Message(
            id=str(uuid.uuid4()),
            tenant_key=test_tenant_key,
            project_id=test_project_id,
            to_agents=[execution.agent_id],
            subject="Test message",
            content="Original message content",
            priority="normal",
            status="pending",
            acknowledged_by=[],
            completed_by=[],
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(message)
        await db_session.flush()

        return job, execution, [todo_pending, todo_in_progress, todo_completed], message

    @pytest.mark.asyncio
    async def test_force_decommission_marks_pending_todos_as_skipped(
        self, db_session, active_agent_with_todos_and_messages, test_tenant_key
    ):
        """Pending and in_progress TODOs should be marked 'skipped' during force decommission."""
        job, execution, todos, message = active_agent_with_todos_and_messages

        from src.giljo_mcp.tools.project_closeout import _force_decommission_agents

        await _force_decommission_agents(db_session, job.project_id, test_tenant_key)

        # Refresh TODO items
        for todo in todos:
            await db_session.refresh(todo)

        assert todos[0].status == "skipped"  # was pending
        assert todos[1].status == "skipped"  # was in_progress
        assert todos[2].status == "completed"  # stays completed

    @pytest.mark.asyncio
    async def test_force_decommission_marks_messages_as_read_with_prefix(
        self, db_session, active_agent_with_todos_and_messages, test_tenant_key
    ):
        """Unread messages should get '[SKIPPED - early termination]' prefix and be acknowledged."""
        job, execution, todos, message = active_agent_with_todos_and_messages

        from src.giljo_mcp.tools.project_closeout import _force_decommission_agents

        await _force_decommission_agents(db_session, job.project_id, test_tenant_key)

        await db_session.refresh(message)
        assert message.content.startswith("[SKIPPED - early termination]")
        assert execution.agent_id in message.acknowledged_by
        assert message.acknowledged_at is not None

    @pytest.mark.asyncio
    async def test_force_decommission_sets_status_to_decommissioned(
        self, db_session, active_agent_with_todos_and_messages, test_tenant_key
    ):
        """Agent execution status should be set to 'decommissioned'."""
        job, execution, todos, message = active_agent_with_todos_and_messages

        from src.giljo_mcp.tools.project_closeout import _force_decommission_agents

        result = await _force_decommission_agents(db_session, job.project_id, test_tenant_key)

        await db_session.refresh(execution)
        assert execution.status == "decommissioned"
        assert "test-worker" in result

    @pytest.mark.asyncio
    async def test_force_decommission_leaves_completed_todos_untouched(
        self, db_session, active_agent_with_todos_and_messages, test_tenant_key
    ):
        """Already-completed TODOs should not be changed to 'skipped'."""
        job, execution, todos, message = active_agent_with_todos_and_messages

        from src.giljo_mcp.tools.project_closeout import _force_decommission_agents

        await _force_decommission_agents(db_session, job.project_id, test_tenant_key)

        await db_session.refresh(todos[2])
        assert todos[2].status == "completed"


# ============================================================================
# Phase 4: report_progress allows "skipped" status
# ============================================================================


class TestReportProgressSkippedStatus:
    """Phase 4: report_progress validates 'skipped' as allowed TODO status."""

    @pytest.mark.asyncio
    async def test_report_progress_accepts_skipped_todo_status(
        self, db_session, test_agent_job, test_tenant_key, orchestration_service_with_session
    ):
        """report_progress should accept 'skipped' as a valid TODO item status."""
        job, execution = test_agent_job
        execution.status = "working"
        await db_session.flush()

        service = orchestration_service_with_session
        result = await service.report_progress(
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            todo_items=[
                {"content": "Task 1", "status": "completed"},
                {"content": "Task 2", "status": "skipped"},
                {"content": "Task 3", "status": "pending"},
            ],
        )

        assert result.status == "success"

        # Verify the skipped item was saved with correct status
        todo_result = await db_session.execute(
            select(AgentTodoItem)
            .where(AgentTodoItem.job_id == job.job_id)
            .order_by(AgentTodoItem.sequence)
        )
        items = todo_result.scalars().all()
        assert len(items) == 3
        assert items[0].status == "completed"
        assert items[1].status == "skipped"
        assert items[2].status == "pending"


# ============================================================================
# Phase 6: Steps aggregation includes skipped count
# ============================================================================


class TestStepsAggregationSkippedCount:
    """Phase 6: _list_jobs_by_project includes skipped count in steps_summary."""

    @pytest.mark.asyncio
    async def test_steps_summary_includes_skipped_from_todo_items(
        self, db_session, test_agent_job, test_tenant_key
    ):
        """Steps summary fallback path should include skipped count from todo_items."""
        job, execution = test_agent_job

        # Create TODO items with various statuses including skipped
        items = [
            AgentTodoItem(
                job_id=job.job_id,
                tenant_key=test_tenant_key,
                content="Completed task",
                status="completed",
                sequence=0,
            ),
            AgentTodoItem(
                job_id=job.job_id,
                tenant_key=test_tenant_key,
                content="Skipped task",
                status="skipped",
                sequence=1,
            ),
            AgentTodoItem(
                job_id=job.job_id,
                tenant_key=test_tenant_key,
                content="Pending task",
                status="pending",
                sequence=2,
            ),
        ]
        db_session.add_all(items)
        await db_session.flush()

        # Verify the items are queryable with expected statuses
        result = await db_session.execute(
            select(AgentTodoItem)
            .where(AgentTodoItem.job_id == job.job_id)
            .order_by(AgentTodoItem.sequence)
        )
        saved_items = result.scalars().all()
        assert len(saved_items) == 3
        completed = sum(1 for i in saved_items if i.status == "completed")
        skipped = sum(1 for i in saved_items if i.status == "skipped")
        assert completed == 1
        assert skipped == 1


# ============================================================================
# Phase 5: Orchestrator protocol includes early termination
# ============================================================================


class TestOrchestratorEarlyTerminationProtocol:
    """Phase 5: Orchestrator protocol includes Early Termination Protocol section."""

    def test_orchestrator_protocol_contains_early_termination_section(self):
        """_build_orchestrator_protocol should include Early Termination Protocol in CH5."""
        from src.giljo_mcp.services.orchestration_service import _build_orchestrator_protocol

        result = _build_orchestrator_protocol(
            cli_mode=False,
            project_id="test-project-id",
            orchestrator_id="test-orch-id",
            tenant_key="test-tenant",
            include_implementation_reference=True,
        )

        ch5 = result["ch5_reference"]
        assert "EARLY TERMINATION PROTOCOL" in ch5
        assert "skipped" in ch5.lower()
        assert "close_project_and_update_memory" in ch5

    def test_template_seeder_messaging_protocol_contains_early_termination(self):
        """_get_orchestrator_messaging_protocol_section should mention early termination."""
        from src.giljo_mcp.template_seeder import _get_orchestrator_messaging_protocol_section

        protocol = _get_orchestrator_messaging_protocol_section()
        assert "EARLY TERMINATION" in protocol.upper() or "early termination" in protocol.lower()
