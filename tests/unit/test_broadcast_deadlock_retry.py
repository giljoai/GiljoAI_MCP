"""
Unit tests for broadcast deadlock prevention and retry (Bug Fix Feb 2026).

Tests cover:
1. Recipients are sorted before message creation (deterministic lock ordering)
2. Deadlock retry with exponential backoff on counter updates
3. RetryExhaustedError raised after max retries
4. Non-deadlock OperationalErrors propagate immediately
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from src.giljo_mcp.exceptions import RetryExhaustedError
from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.services.message_service import MessageService


def _make_execution(agent_id: str, display_name: str, status: str = "working") -> Mock:
    """Helper to create a mock AgentExecution."""
    exe = Mock(spec=AgentExecution)
    exe.agent_id = agent_id
    exe.agent_display_name = display_name
    exe.agent_name = display_name
    exe.status = status
    exe.started_at = datetime.now(timezone.utc)
    exe.messages_sent_count = 0
    exe.messages_waiting_count = 0
    return exe


def _make_deadlock_error() -> OperationalError:
    """Create an OperationalError that mimics a PostgreSQL deadlock (SQLSTATE 40P01)."""
    orig = Exception("deadlock detected")
    orig.pgcode = "40P01"
    return OperationalError("deadlock detected", params=None, orig=orig)


def _make_non_deadlock_error() -> OperationalError:
    """Create an OperationalError that is NOT a deadlock."""
    orig = Exception("connection refused")
    orig.pgcode = "08006"
    return OperationalError("connection refused", params=None, orig=orig)


class TestBroadcastRecipientSorting:
    """Verify recipients are sorted for deterministic lock ordering."""

    @pytest.mark.asyncio
    async def test_broadcast_recipients_sorted_before_message_creation(
        self, mock_db_manager, mock_tenant_manager
    ):
        """Messages should be created in sorted agent_id order to prevent deadlocks."""
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        # Create agents with IDs that sort in reverse alphabetical order
        agent_c = _make_execution("cccc-cccc", "agent-c")
        agent_a = _make_execution("aaaa-aaaa", "agent-a")
        agent_b = _make_execution("bbbb-bbbb", "agent-b")

        # Return them in non-sorted order from DB
        mock_scalars_fanout = Mock()
        mock_scalars_fanout.all.return_value = [agent_c, agent_a, agent_b]

        mock_result_fanout = Mock()
        mock_result_fanout.scalars.return_value = mock_scalars_fanout

        # Track messages added to session
        added_messages = []
        original_add = session.add

        def track_add(obj):
            if isinstance(obj, Message):
                added_messages.append(obj)
            original_add(obj)

        session.add = track_add

        # Mock: project query, then fan-out query, then sender query, then counter queries
        call_count = {"n": 0}

        async def mock_execute(*args, **kwargs):
            call_count["n"] += 1
            result = Mock()

            if call_count["n"] == 1:
                # Project lookup
                result.scalar_one_or_none = Mock(return_value=mock_project)
            elif call_count["n"] == 2:
                # Fan-out expansion query
                result.scalars = Mock(return_value=mock_scalars_fanout)
            else:
                # Sender resolution + counter queries
                result.scalar_one_or_none = Mock(return_value=agent_a)
                result.rowcount = 1
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        service = MessageService(db_manager, mock_tenant_manager)

        await service.send_message(
            to_agents=["all"],
            content="Test broadcast",
            project_id=project_id,
            from_agent="orchestrator",
            tenant_key=tenant_key,
        )

        # Verify messages were created in sorted recipient order
        assert len(added_messages) == 3
        recipient_ids = [msg.to_agents[0] for msg in added_messages]
        assert recipient_ids == sorted(recipient_ids), (
            f"Recipients must be sorted for deadlock prevention: {recipient_ids}"
        )


class TestDeadlockRetry:
    """Verify deadlock retry behavior on counter updates."""

    @pytest.mark.asyncio
    async def test_deadlock_retried_with_backoff(self, mock_db_manager, mock_tenant_manager):
        """Counter updates should retry on PostgreSQL deadlock (40P01)."""
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        agent_a = _make_execution(str(uuid4()), "agent-a")

        call_count = {"n": 0}
        deadlock_err = _make_deadlock_error()

        async def mock_execute(*args, **kwargs):
            call_count["n"] += 1
            result = Mock()

            if call_count["n"] == 1:
                result.scalar_one_or_none = Mock(return_value=mock_project)
            elif call_count["n"] == 2:
                # Fan-out: return single agent (direct message, not broadcast)
                result.scalar_one_or_none = Mock(return_value=agent_a)
                scalars = Mock()
                scalars.all = Mock(return_value=[agent_a])
                result.scalars = Mock(return_value=scalars)
            elif call_count["n"] == 3:
                # Sender resolution in counter block — first attempt: deadlock
                raise deadlock_err
            elif call_count["n"] == 4:
                # Sender resolution in counter block — retry succeeds
                result.scalar_one_or_none = Mock(return_value=agent_a)
            else:
                result.rowcount = 1
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        service = MessageService(db_manager, mock_tenant_manager)

        with patch("src.giljo_mcp.services.message_service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await service.send_message(
                to_agents=[agent_a.agent_id],
                content="Test direct",
                project_id=project_id,
                from_agent="orchestrator",
                tenant_key=tenant_key,
            )

            # Verify retry happened with a sleep call
            assert mock_sleep.call_count >= 1
            # Verify rollback was called on deadlock
            session.rollback.assert_awaited()

    @pytest.mark.asyncio
    async def test_deadlock_exhaustion_raises_retry_exhausted(
        self, mock_db_manager, mock_tenant_manager
    ):
        """After max retries, RetryExhaustedError should be raised."""
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        agent_a = _make_execution(str(uuid4()), "agent-a")
        deadlock_err = _make_deadlock_error()

        call_count = {"n": 0}

        async def mock_execute(*args, **kwargs):
            call_count["n"] += 1
            result = Mock()

            if call_count["n"] == 1:
                result.scalar_one_or_none = Mock(return_value=mock_project)
            elif call_count["n"] == 2:
                result.scalar_one_or_none = Mock(return_value=agent_a)
            else:
                # All counter attempts deadlock
                raise deadlock_err
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        service = MessageService(db_manager, mock_tenant_manager)

        with patch("src.giljo_mcp.services.message_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RetryExhaustedError, match="Deadlock retry exhausted"):
                await service.send_message(
                    to_agents=[agent_a.agent_id],
                    content="Test direct",
                    project_id=project_id,
                    from_agent="orchestrator",
                    tenant_key=tenant_key,
                )

    @pytest.mark.asyncio
    async def test_non_deadlock_operational_error_not_retried(
        self, mock_db_manager, mock_tenant_manager
    ):
        """Non-deadlock OperationalErrors should propagate immediately without retry."""
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        agent_a = _make_execution(str(uuid4()), "agent-a")
        non_deadlock_err = _make_non_deadlock_error()

        call_count = {"n": 0}

        async def mock_execute(*args, **kwargs):
            call_count["n"] += 1
            result = Mock()

            if call_count["n"] == 1:
                result.scalar_one_or_none = Mock(return_value=mock_project)
            elif call_count["n"] == 2:
                result.scalar_one_or_none = Mock(return_value=agent_a)
            else:
                raise non_deadlock_err
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        service = MessageService(db_manager, mock_tenant_manager)

        with patch("src.giljo_mcp.services.message_service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(OperationalError):
                await service.send_message(
                    to_agents=[agent_a.agent_id],
                    content="Test direct",
                    project_id=project_id,
                    from_agent="orchestrator",
                    tenant_key=tenant_key,
                )

            # No sleep = no retry attempted
            mock_sleep.assert_not_awaited()
