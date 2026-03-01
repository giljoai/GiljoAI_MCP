"""
Unit tests for closeout readiness gate in close_project_and_update_memory (Bug Fix Feb 2026).

Tests cover:
1. CLOSEOUT_BLOCKED returned when agents are still active
2. force=True auto-decommissions active agents and proceeds
3. All-complete agents pass the gate normally
4. Decommissioned agents are skipped (don't block)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.exceptions import ProjectStateError, ResourceNotFoundError, ValidationError
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.tools.project_closeout import (
    _check_agent_readiness,
    _force_decommission_agents,
    close_project_and_update_memory,
)


def _make_execution(
    agent_id: str,
    display_name: str,
    status: str = "complete",
    job_id: str | None = None,
    tenant_key: str = "test-tenant",
    messages_waiting: int = 0,
) -> Mock:
    """Create a mock AgentExecution."""
    exe = Mock(spec=AgentExecution)
    exe.agent_id = agent_id
    exe.agent_display_name = display_name
    exe.agent_name = display_name
    exe.status = status
    exe.job_id = job_id or str(uuid4())
    exe.tenant_key = tenant_key
    exe.messages_waiting_count = messages_waiting
    exe.started_at = datetime.now(timezone.utc)
    return exe


class TestCheckAgentReadiness:
    """Tests for _check_agent_readiness helper."""

    @pytest.mark.asyncio
    async def test_all_complete_returns_ready(self):
        """When all agents are complete, readiness check passes."""
        session = AsyncMock()
        project_id = str(uuid4())

        agent_a = _make_execution(str(uuid4()), "impl-1", "complete")
        agent_b = _make_execution(str(uuid4()), "analyzer-1", "complete")

        scalars_mock = Mock()
        scalars_mock.all.return_value = [agent_a, agent_b]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        is_ready, blockers = await _check_agent_readiness(
            session, project_id, "test-tenant"
        )

        assert is_ready is True
        assert blockers == []

    @pytest.mark.asyncio
    async def test_active_agents_return_blockers(self):
        """When agents are still working/blocked/silent, blockers are returned."""
        session = AsyncMock()
        project_id = str(uuid4())

        agent_a = _make_execution(str(uuid4()), "impl-1", "complete")
        agent_b = _make_execution(str(uuid4()), "ui-builder", "working")
        agent_c = _make_execution(str(uuid4()), "tester", "silent")

        scalars_mock = Mock()
        scalars_mock.all.return_value = [agent_a, agent_b, agent_c]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        is_ready, blockers = await _check_agent_readiness(
            session, project_id, "test-tenant"
        )

        assert is_ready is False
        assert len(blockers) == 2
        blocker_names = {b["agent_name"] for b in blockers}
        assert "ui-builder" in blocker_names
        assert "tester" in blocker_names

    @pytest.mark.asyncio
    async def test_decommissioned_agents_skipped(self):
        """Decommissioned agents should not block closeout."""
        session = AsyncMock()
        project_id = str(uuid4())

        agent_a = _make_execution(str(uuid4()), "impl-1", "complete")
        agent_b = _make_execution(str(uuid4()), "retired-agent", "decommissioned")

        scalars_mock = Mock()
        scalars_mock.all.return_value = [agent_a, agent_b]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        is_ready, blockers = await _check_agent_readiness(
            session, project_id, "test-tenant"
        )

        assert is_ready is True
        assert blockers == []

    @pytest.mark.asyncio
    async def test_empty_project_returns_ready(self):
        """A project with no agents should be closeable."""
        session = AsyncMock()
        project_id = str(uuid4())

        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        is_ready, blockers = await _check_agent_readiness(
            session, project_id, "test-tenant"
        )

        assert is_ready is True
        assert blockers == []


class TestForceDecommissionAgents:
    """Tests for _force_decommission_agents helper."""

    @pytest.mark.asyncio
    async def test_active_agents_decommissioned(self):
        """Active agents should be set to decommissioned status."""
        session = AsyncMock()
        project_id = str(uuid4())

        agent_working = _make_execution(str(uuid4()), "ui-builder", "working")
        agent_silent = _make_execution(str(uuid4()), "tester", "silent")

        scalars_mock = Mock()
        scalars_mock.all.return_value = [agent_working, agent_silent]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        decommissioned = await _force_decommission_agents(
            session, project_id, "test-tenant"
        )

        assert len(decommissioned) == 2
        assert agent_working.status == "decommissioned"
        assert agent_silent.status == "decommissioned"
        assert "ui-builder" in decommissioned
        assert "tester" in decommissioned
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_active_agents_returns_empty(self):
        """When no active agents exist, nothing should be decommissioned."""
        session = AsyncMock()
        project_id = str(uuid4())

        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        session.execute = AsyncMock(return_value=result_mock)

        decommissioned = await _force_decommission_agents(
            session, project_id, "test-tenant"
        )

        assert decommissioned == []
        session.flush.assert_not_awaited()


class TestCloseoutGateIntegration:
    """Integration tests for the readiness gate in close_project_and_update_memory."""

    @pytest.mark.asyncio
    async def test_blocked_when_agents_active_and_no_force(self):
        """Without force=True, closeout should be blocked when agents are active."""
        project_id = str(uuid4())
        product_id = str(uuid4())
        tenant_key = "test-tenant"

        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key
        mock_project.product_id = product_id

        mock_product = MagicMock(spec=Product)
        mock_product.id = product_id
        mock_product.tenant_key = tenant_key
        mock_product.product_memory = {}

        # Agent that is still working
        agent_working = _make_execution(str(uuid4()), "impl-1", "working")

        mock_session = AsyncMock()
        mock_db_manager = MagicMock()
        mock_db_manager.get_session_async.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_db_manager.get_session_async.return_value.__aexit__ = AsyncMock(
            return_value=False
        )

        call_count = {"n": 0}

        async def mock_execute(*args, **kwargs):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                # Project lookup
                result.scalar_one_or_none.return_value = mock_project
            elif call_count["n"] == 2:
                # Product lookup
                result.scalar_one_or_none.return_value = mock_product
            elif call_count["n"] == 3:
                # Agent readiness check
                scalars = MagicMock()
                scalars.all.return_value = [agent_working]
                result.scalars.return_value = scalars
            return result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        with pytest.raises(ProjectStateError) as exc_info:
            await close_project_and_update_memory(
                project_id=project_id,
                summary="Test summary for closeout",
                key_outcomes=["outcome-1"],
                decisions_made=["decision-1"],
                tenant_key=tenant_key,
                db_manager=mock_db_manager,
                force=False,
            )

        assert "agents have unfinished work" in str(exc_info.value)
        assert exc_info.value.context["status"] == "CLOSEOUT_BLOCKED"
        assert "blockers" in exc_info.value.context
        assert len(exc_info.value.context["blockers"]) == 1
        assert exc_info.value.context["blockers"][0]["agent_name"] == "impl-1"

    @pytest.mark.asyncio
    async def test_force_decommissions_and_proceeds(self):
        """With force=True, active agents should be decommissioned and closeout should proceed."""
        project_id = str(uuid4())
        product_id = str(uuid4())
        tenant_key = "test-tenant"

        mock_project = MagicMock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key
        mock_project.product_id = product_id
        mock_project.created_at = datetime.now(timezone.utc)
        mock_project.completed_at = None
        mock_project.meta_data = {}
        mock_project.name = "Test Project"

        mock_product = MagicMock(spec=Product)
        mock_product.id = product_id
        mock_product.tenant_key = tenant_key
        mock_product.product_memory = {}

        agent_working = _make_execution(str(uuid4()), "impl-1", "working")

        mock_session = AsyncMock()
        mock_db_manager = MagicMock()
        mock_db_manager.get_session_async.return_value.__aenter__ = AsyncMock(
            return_value=mock_session
        )
        mock_db_manager.get_session_async.return_value.__aexit__ = AsyncMock(
            return_value=False
        )

        call_count = {"n": 0}

        async def mock_execute(*args, **kwargs):
            call_count["n"] += 1
            result = MagicMock()
            if call_count["n"] == 1:
                result.scalar_one_or_none.return_value = mock_project
            elif call_count["n"] == 2:
                result.scalar_one_or_none.return_value = mock_product
            elif call_count["n"] == 3:
                # Readiness check — returns working agent
                scalars = MagicMock()
                scalars.all.return_value = [agent_working]
                result.scalars.return_value = scalars
            elif call_count["n"] == 4:
                # Force decommission query — returns same working agent
                scalars = MagicMock()
                scalars.all.return_value = [agent_working]
                result.scalars.return_value = scalars
            return result

        mock_session.execute = AsyncMock(side_effect=mock_execute)

        # Mock the ProductMemoryRepository to avoid real DB writes
        mock_entry = MagicMock()
        mock_entry.id = str(uuid4())
        mock_entry.to_dict.return_value = {"id": str(mock_entry.id)}

        with patch(
            "src.giljo_mcp.tools.project_closeout.ProductMemoryRepository"
        ) as MockRepo:
            repo_instance = MockRepo.return_value
            repo_instance.get_next_sequence = AsyncMock(return_value=1)
            repo_instance.create_entry = AsyncMock(return_value=mock_entry)

            with patch(
                "src.giljo_mcp.tools.project_closeout.emit_websocket_event",
                new_callable=AsyncMock,
            ):
                result = await close_project_and_update_memory(
                    project_id=project_id,
                    summary="Test summary for closeout",
                    key_outcomes=["outcome-1"],
                    decisions_made=["decision-1"],
                    tenant_key=tenant_key,
                    db_manager=mock_db_manager,
                    force=True,
                )

        # Success path: no "success" key, just check returned dict has expected fields
        assert "entry_id" in result
        assert "sequence_number" in result
        assert "message" in result
        # Verify the agent was decommissioned
        assert agent_working.status == "decommissioned"
