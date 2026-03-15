"""
Unit tests for deadlock prevention and retry on the send path.

Tests cover:
1. Recipients are sorted before message creation (deterministic lock ordering)
2. Send-path: deadlock retry with exponential backoff on counter updates
3. Send-path: RetryExhaustedError raised after max retries
4. Send-path: non-deadlock OperationalErrors propagate immediately
5. Shared utility: with_deadlock_retry behavior
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import OperationalError

from src.giljo_mcp.exceptions import RetryExhaustedError
from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.utils.db_retry import with_deadlock_retry


# Patch target for asyncio.sleep inside the shared retry utility
_SLEEP_PATCH_TARGET = "src.giljo_mcp.utils.db_retry.asyncio.sleep"


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
    exe.job_id = str(uuid4())
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

        agent_c = _make_execution("cccc-cccc", "agent-c")
        agent_a = _make_execution("aaaa-aaaa", "agent-a")
        agent_b = _make_execution("bbbb-bbbb", "agent-b")

        mock_scalars_fanout = Mock()
        mock_scalars_fanout.all.return_value = [agent_c, agent_a, agent_b]

        added_messages = []
        original_add = session.add

        def track_add(obj):
            if isinstance(obj, Message):
                added_messages.append(obj)
            original_add(obj)

        session.add = track_add

        call_count = {"n": 0}

        async def mock_execute(*args, **kwargs):
            call_count["n"] += 1
            result = Mock()

            if call_count["n"] == 1:
                result.scalar_one_or_none = Mock(return_value=mock_project)
            elif call_count["n"] == 2:
                result.scalars = Mock(return_value=mock_scalars_fanout)
            else:
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

        assert len(added_messages) == 3
        recipient_ids = [msg.to_agents[0] for msg in added_messages]
        assert recipient_ids == sorted(recipient_ids), (
            f"Recipients must be sorted for deadlock prevention: {recipient_ids}"
        )


class TestSendPathDeadlockRetry:
    """Verify deadlock retry behavior on send-path counter updates."""

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
                result.scalar_one_or_none = Mock(return_value=agent_a)
                scalars = Mock()
                scalars.all = Mock(return_value=[agent_a])
                result.scalars = Mock(return_value=scalars)
            elif call_count["n"] == 3:
                raise deadlock_err
            elif call_count["n"] == 4:
                result.scalar_one_or_none = Mock(return_value=agent_a)
            else:
                result.rowcount = 1
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        service = MessageService(db_manager, mock_tenant_manager)

        with patch(_SLEEP_PATCH_TARGET, new_callable=AsyncMock) as mock_sleep:
            await service.send_message(
                to_agents=[agent_a.agent_id],
                content="Test direct",
                project_id=project_id,
                from_agent="orchestrator",
                tenant_key=tenant_key,
            )

            assert mock_sleep.call_count >= 1
            session.rollback.assert_awaited()

    @pytest.mark.asyncio
    async def test_send_counter_exhaustion_returns_success(
        self, mock_db_manager, mock_tenant_manager
    ):
        """Send succeeds even when counter update exhausts all retries.

        The message is already committed before counter updates. If the counter
        update deadlocks exhaustively, RetryExhaustedError is caught and logged.
        The caller should NOT receive an error (counter skew is recoverable,
        duplicate messages are not).
        """
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
                raise deadlock_err
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        service = MessageService(db_manager, mock_tenant_manager)

        with patch(_SLEEP_PATCH_TARGET, new_callable=AsyncMock):
            # Should NOT raise -- RetryExhaustedError is caught on send path
            result = await service.send_message(
                to_agents=[agent_a.agent_id],
                content="Test direct",
                project_id=project_id,
                from_agent="orchestrator",
                tenant_key=tenant_key,
            )
            # send_message returns the sender execution on success
            assert result is not None

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

        with patch(_SLEEP_PATCH_TARGET, new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(OperationalError):
                await service.send_message(
                    to_agents=[agent_a.agent_id],
                    content="Test direct",
                    project_id=project_id,
                    from_agent="orchestrator",
                    tenant_key=tenant_key,
                )

            mock_sleep.assert_not_awaited()


class TestWithDeadlockRetryUtility:
    """Verify the shared with_deadlock_retry utility directly."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Operation succeeds immediately without retry."""
        session = AsyncMock()
        result = await with_deadlock_retry(
            session,
            AsyncMock(return_value="ok"),
            operation_name="test_op",
        )
        assert result == "ok"
        session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_retry_on_deadlock_then_success(self):
        """Operation retries on deadlock and succeeds on second attempt."""
        session = AsyncMock()
        deadlock_err = _make_deadlock_error()

        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise deadlock_err
            return "recovered"

        with patch(_SLEEP_PATCH_TARGET, new_callable=AsyncMock) as mock_sleep:
            result = await with_deadlock_retry(
                session,
                flaky_operation,
                operation_name="test_op",
            )

        assert result == "recovered"
        assert call_count == 2
        session.rollback.assert_awaited_once()
        mock_sleep.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exhaustion_raises_retry_exhausted_error(self):
        """After max_retries deadlocks, RetryExhaustedError is raised."""
        session = AsyncMock()
        deadlock_err = _make_deadlock_error()

        with (
            patch(_SLEEP_PATCH_TARGET, new_callable=AsyncMock),
            pytest.raises(RetryExhaustedError, match="Deadlock retry exhausted"),
        ):
            await with_deadlock_retry(
                session,
                AsyncMock(side_effect=deadlock_err),
                operation_name="test_op",
                max_retries=2,
            )

    @pytest.mark.asyncio
    async def test_non_deadlock_error_propagates_immediately(self):
        """Non-deadlock OperationalError propagates without retry."""
        session = AsyncMock()
        non_deadlock_err = _make_non_deadlock_error()

        with patch(_SLEEP_PATCH_TARGET, new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(OperationalError):
                await with_deadlock_retry(
                    session,
                    AsyncMock(side_effect=non_deadlock_err),
                    operation_name="test_op",
                )

            mock_sleep.assert_not_awaited()
            session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_context_included_in_retry_exhausted_error(self):
        """Context dict is included in RetryExhaustedError."""
        session = AsyncMock()
        deadlock_err = _make_deadlock_error()

        with patch(_SLEEP_PATCH_TARGET, new_callable=AsyncMock):
            with pytest.raises(RetryExhaustedError) as exc_info:
                await with_deadlock_retry(
                    session,
                    AsyncMock(side_effect=deadlock_err),
                    operation_name="test_op",
                    context={"project_id": "abc-123"},
                    max_retries=1,
                )

            assert exc_info.value.context["project_id"] == "abc-123"
            assert exc_info.value.context["operation"] == "test_op"

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Each retry uses exponentially increasing delay."""
        session = AsyncMock()
        deadlock_err = _make_deadlock_error()
        call_count = 0

        async def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise deadlock_err
            return "ok"

        with patch(_SLEEP_PATCH_TARGET, new_callable=AsyncMock) as mock_sleep:
            await with_deadlock_retry(
                session,
                fail_twice_then_succeed,
                operation_name="test_op",
                max_retries=3,
                base_delay=0.1,
                jitter_max=0.0,  # Zero jitter for deterministic test
            )

        assert mock_sleep.call_count == 2
        # First delay: 0.1 * 2^0 = 0.1
        first_delay = mock_sleep.call_args_list[0][0][0]
        assert 0.09 <= first_delay <= 0.11
        # Second delay: 0.1 * 2^1 = 0.2
        second_delay = mock_sleep.call_args_list[1][0][0]
        assert 0.19 <= second_delay <= 0.21


class TestWithDeadlockRetryParameterValidation:
    """Verify parameter validation in with_deadlock_retry."""

    @pytest.mark.asyncio
    async def test_max_retries_zero_raises_value_error(self):
        """max_retries=0 should raise ValueError."""
        session = AsyncMock()
        with pytest.raises(ValueError, match="max_retries must be >= 1"):
            await with_deadlock_retry(
                session,
                AsyncMock(return_value="ok"),
                operation_name="test_op",
                max_retries=0,
            )

    @pytest.mark.asyncio
    async def test_max_retries_negative_raises_value_error(self):
        """Negative max_retries should raise ValueError."""
        session = AsyncMock()
        with pytest.raises(ValueError, match="max_retries must be >= 1"):
            await with_deadlock_retry(
                session,
                AsyncMock(return_value="ok"),
                operation_name="test_op",
                max_retries=-1,
            )

    @pytest.mark.asyncio
    async def test_negative_base_delay_raises_value_error(self):
        """Negative base_delay should raise ValueError."""
        session = AsyncMock()
        with pytest.raises(ValueError, match="base_delay must be >= 0"):
            await with_deadlock_retry(
                session,
                AsyncMock(return_value="ok"),
                operation_name="test_op",
                base_delay=-0.1,
            )
