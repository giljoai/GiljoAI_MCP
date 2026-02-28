"""
Unit tests for Broadcast Fan-out at Write (Handover 0387)

Tests cover:
1. Fan-out creates individual messages per recipient
2. Per-recipient acknowledgment works independently
3. Sender exclusion during fan-out
4. Completed/decommissioned agents exclusion during fan-out
5. Silent agents included in broadcasts
6. Excluded agents returned in response
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.schemas.service_responses import MessageListResult, SendMessageResult
from src.giljo_mcp.services.message_service import MessageService


def _update_result(rowcount=1):
    """Create a mock result for UPDATE statements (increment_sent_count, increment_waiting_count)."""
    r = Mock()
    r.rowcount = rowcount
    return r


def _scalar_result(value):
    """Create a mock result for scalar_one_or_none queries."""
    r = Mock()
    r.scalar_one_or_none = Mock(return_value=value)
    return r


def _scalars_result(values):
    """Create a mock result for scalars().all() queries."""
    r = Mock()
    r.scalars = Mock(return_value=Mock(all=Mock(return_value=values)))
    return r


class TestBroadcastFanoutSendMessage:
    """Tests for fan-out behavior in send_message() when to_agents=['all']"""

    @pytest.mark.asyncio
    async def test_broadcast_fanout_creates_individual_messages(self, mock_db_manager, mock_tenant_manager):
        """Broadcast to 'all' should create one Message per active agent (excluding sender)."""
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        orch_execution = Mock(spec=AgentExecution)
        orch_execution.agent_id = str(uuid4())
        orch_execution.agent_display_name = "orchestrator"
        orch_execution.status = "working"

        impl_execution = Mock(spec=AgentExecution)
        impl_execution.agent_id = str(uuid4())
        impl_execution.agent_display_name = "implementer"
        impl_execution.status = "waiting"

        analyzer_execution = Mock(spec=AgentExecution)
        analyzer_execution.agent_id = str(uuid4())
        analyzer_execution.agent_display_name = "analyzer"
        analyzer_execution.status = "working"

        all_executions = [orch_execution, impl_execution, analyzer_execution]

        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        # session.execute call sequence:
        # 1. Project lookup
        # 2. Fan-out agent query (all agents)
        # 3. Sender execution lookup (counter section)
        # 4. increment_sent_count (UPDATE)
        # 5. increment_waiting_count for recipient 1 (UPDATE)
        # 6. increment_waiting_count for recipient 2 (UPDATE)
        # 7. Staging orchestrator detection (sender lookup by agent_id)
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(mock_project),
                _scalars_result(all_executions),
                _scalar_result(orch_execution),   # sender lookup
                _update_result(),                  # increment sent
                _update_result(),                  # increment waiting 1
                _update_result(),                  # increment waiting 2
                _scalar_result(None),              # staging detection (no match)
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        result = await service.send_message(
            to_agents=["all"],
            content="Broadcast test message",
            project_id=project_id,
            message_type="broadcast",
            from_agent="orchestrator",
            tenant_key=tenant_key,
        )

        assert isinstance(result, SendMessageResult)
        assert result.message_id is not None

        # Fan-out should create 2 messages (impl + analyzer, excluding orchestrator sender)
        assert len(added_messages) == 2, (
            f"Expected 2 individual messages (fan-out), got {len(added_messages)}"
        )

        for msg in added_messages:
            assert "all" not in msg.to_agents
            assert len(msg.to_agents) == 1

        recipient_ids = [msg.to_agents[0] for msg in added_messages]
        assert len(recipient_ids) == len(set(recipient_ids))

    @pytest.mark.asyncio
    async def test_broadcast_excludes_sender(self, mock_db_manager, mock_tenant_manager):
        """Sender should not receive their own broadcast."""
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())
        sender_agent_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        sender_execution = Mock(spec=AgentExecution)
        sender_execution.agent_id = sender_agent_id
        sender_execution.agent_display_name = "orchestrator"
        sender_execution.status = "working"

        other_execution = Mock(spec=AgentExecution)
        other_execution.agent_id = str(uuid4())
        other_execution.agent_display_name = "implementer"
        other_execution.status = "waiting"

        all_executions = [sender_execution, other_execution]

        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(mock_project),
                _scalars_result(all_executions),
                _scalar_result(sender_execution),  # sender lookup
                _update_result(),                   # increment sent
                _update_result(),                   # increment waiting
                _scalar_result(None),               # staging detection
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        result = await service.send_message(
            to_agents=["all"],
            content="Test broadcast",
            project_id=project_id,
            from_agent="orchestrator",
            tenant_key=tenant_key,
        )

        assert isinstance(result, SendMessageResult)

        all_recipients = []
        for msg in added_messages:
            all_recipients.extend(msg.to_agents)

        assert sender_agent_id not in all_recipients, (
            f"Sender ({sender_agent_id}) should be excluded from broadcast recipients"
        )

    @pytest.mark.asyncio
    async def test_broadcast_excludes_completed_agents(self, mock_db_manager, mock_tenant_manager):
        """Completed agents should not receive broadcasts and should appear in excluded_agents."""
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())
        completed_agent_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        active_execution = Mock(spec=AgentExecution)
        active_execution.agent_id = str(uuid4())
        active_execution.agent_display_name = "implementer"
        active_execution.status = "waiting"

        completed_execution = Mock(spec=AgentExecution)
        completed_execution.agent_id = completed_agent_id
        completed_execution.agent_display_name = "analyzer"
        completed_execution.status = "completed"

        # Fan-out query returns ALL agents (no status filter), partitioned in Python
        all_executions = [active_execution, completed_execution]

        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(mock_project),
                _scalars_result(all_executions),
                _scalar_result(None),   # sender lookup (external-sender not found)
                _update_result(),       # increment waiting for active agent
                _scalar_result(None),   # staging detection
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        result = await service.send_message(
            to_agents=["all"],
            content="Test broadcast",
            project_id=project_id,
            from_agent="external-sender",
            tenant_key=tenant_key,
        )

        assert isinstance(result, SendMessageResult)

        all_recipients = []
        for msg in added_messages:
            all_recipients.extend(msg.to_agents)

        assert completed_agent_id not in all_recipients
        assert len(result.excluded_agents) == 1
        assert "analyzer (completed)" in result.excluded_agents[0]

    @pytest.mark.asyncio
    async def test_broadcast_excludes_decommissioned_agents(self, mock_db_manager, mock_tenant_manager):
        """Decommissioned agents should not receive broadcasts and should appear in excluded_agents."""
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        active_execution = Mock(spec=AgentExecution)
        active_execution.agent_id = str(uuid4())
        active_execution.agent_display_name = "implementer"
        active_execution.status = "working"

        decom_execution = Mock(spec=AgentExecution)
        decom_execution.agent_id = str(uuid4())
        decom_execution.agent_display_name = "old-agent"
        decom_execution.status = "decommissioned"

        all_executions = [active_execution, decom_execution]

        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(mock_project),
                _scalars_result(all_executions),
                _scalar_result(None),   # sender lookup
                _update_result(),       # increment waiting
                _scalar_result(None),   # staging detection
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        result = await service.send_message(
            to_agents=["all"],
            content="Test broadcast",
            project_id=project_id,
            from_agent="external-sender",
            tenant_key=tenant_key,
        )

        assert isinstance(result, SendMessageResult)
        assert len(result.excluded_agents) == 1
        assert "old-agent (decommissioned)" in result.excluded_agents[0]

    @pytest.mark.asyncio
    async def test_broadcast_includes_silent_agents(self, mock_db_manager, mock_tenant_manager):
        """Silent agents should still receive broadcasts (could be a connection bug)."""
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        silent_execution = Mock(spec=AgentExecution)
        silent_execution.agent_id = str(uuid4())
        silent_execution.agent_display_name = "silent-agent"
        silent_execution.status = "silent"

        all_executions = [silent_execution]

        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(mock_project),
                _scalars_result(all_executions),
                _scalar_result(None),   # sender lookup
                _update_result(),       # increment waiting
                _scalar_result(None),   # staging detection
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        result = await service.send_message(
            to_agents=["all"],
            content="Test broadcast",
            project_id=project_id,
            from_agent="external-sender",
            tenant_key=tenant_key,
        )

        assert isinstance(result, SendMessageResult)
        assert len(added_messages) == 1, "Silent agent should receive broadcast"
        assert added_messages[0].to_agents == [silent_execution.agent_id]
        assert len(result.excluded_agents) == 0


class TestBroadcastFanoutReceiveMessages:
    """Tests for simplified receive_messages() after fan-out implementation"""

    @pytest.mark.asyncio
    async def test_broadcast_per_recipient_acknowledgment(self, mock_db_manager):
        """Each agent should acknowledge independently after fan-out."""
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        agent_a_id = str(uuid4())
        agent_b_id = str(uuid4())
        project_id = str(uuid4())
        job_id = str(uuid4())

        agent_a_execution = Mock(spec=AgentExecution)
        agent_a_execution.agent_id = agent_a_id
        agent_a_execution.job_id = job_id
        agent_a_execution.tenant_key = "test-tenant"

        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = job_id
        mock_job.project_id = project_id
        mock_job.job_type = "implementer"

        msg_for_a = Mock(spec=Message)
        msg_for_a.id = str(uuid4())
        msg_for_a.to_agents = [agent_a_id]
        msg_for_a.status = "pending"
        msg_for_a.content = "Broadcast content"
        msg_for_a.message_type = "broadcast"
        msg_for_a.priority = "normal"
        msg_for_a.created_at = datetime.now(timezone.utc)
        msg_for_a.acknowledged_at = None
        msg_for_a.acknowledged_by = None
        msg_for_a.meta_data = {"_from_agent": "orchestrator"}

        msg_for_b = Mock(spec=Message)
        msg_for_b.id = str(uuid4())
        msg_for_b.to_agents = [agent_b_id]
        msg_for_b.status = "pending"

        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(agent_a_execution),  # Agent execution lookup
                _scalar_result(mock_job),            # Job lookup
                _scalars_result([msg_for_a]),         # Messages query
                _update_result(),                     # decrement_waiting_increment_read UPDATE
            ]
        )

        service = MessageService(db_manager, tenant_manager)
        result = await service.receive_messages(agent_id=agent_a_id, limit=10, tenant_key="test-tenant")

        assert isinstance(result, MessageListResult)
        assert result.count == 1
        assert msg_for_a.status == "acknowledged"
        assert msg_for_b.status == "pending"

    @pytest.mark.asyncio
    async def test_receive_no_broadcast_or_clause_needed(self, mock_db_manager):
        """After fan-out, receive_messages should match individual agent_id, not literal 'all'."""
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        agent_id = str(uuid4())
        project_id = str(uuid4())
        job_id = str(uuid4())

        mock_execution = Mock(spec=AgentExecution)
        mock_execution.agent_id = agent_id
        mock_execution.job_id = job_id
        mock_execution.tenant_key = "test-tenant"

        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = job_id
        mock_job.project_id = project_id
        mock_job.job_type = "implementer"

        fanout_msg = Mock(spec=Message)
        fanout_msg.id = str(uuid4())
        fanout_msg.to_agents = [agent_id]
        fanout_msg.status = "pending"
        fanout_msg.content = "Fan-out message"
        fanout_msg.message_type = "broadcast"
        fanout_msg.priority = "normal"
        fanout_msg.created_at = datetime.now(timezone.utc)
        fanout_msg.acknowledged_at = None
        fanout_msg.acknowledged_by = None
        fanout_msg.meta_data = {"_from_agent": "orchestrator"}

        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(mock_execution),       # Agent execution lookup
                _scalar_result(mock_job),              # Job lookup
                _scalars_result([fanout_msg]),          # Messages query
                _update_result(),                      # decrement_waiting_increment_read UPDATE
            ]
        )

        service = MessageService(db_manager, tenant_manager)
        result = await service.receive_messages(agent_id=agent_id, tenant_key="test-tenant")

        assert isinstance(result, MessageListResult)
        received_ids = [m["id"] for m in result.messages]
        assert str(fanout_msg.id) in received_ids


class TestBroadcastFanoutEdgeCases:
    """Edge case tests for broadcast fan-out"""

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_project_no_messages_created(self, mock_db_manager, mock_tenant_manager):
        """Broadcast to project with only sender should create 0 messages."""
        db_manager, session = mock_db_manager
        project_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = "test-tenant"

        sender_execution = Mock(spec=AgentExecution)
        sender_execution.agent_id = str(uuid4())
        sender_execution.agent_display_name = "orchestrator"
        sender_execution.status = "working"

        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        # 3 calls: project lookup + fan-out query + staging detection (no messages, so no counter ops)
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(mock_project),
                _scalars_result([sender_execution]),
                _scalar_result(None),   # staging detection
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        result = await service.send_message(
            to_agents=["all"],
            content="Lonely broadcast",
            project_id=project_id,
            from_agent="orchestrator",
            tenant_key="test-tenant",
        )

        assert isinstance(result, SendMessageResult)
        assert len(added_messages) == 0

    @pytest.mark.asyncio
    async def test_direct_message_unchanged(self, mock_db_manager, mock_tenant_manager):
        """Direct messages (to_agents=['specific-agent']) should still work normally."""
        db_manager, session = mock_db_manager
        project_id = str(uuid4())
        target_agent_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = "test-tenant"

        target_execution = Mock(spec=AgentExecution)
        target_execution.agent_id = target_agent_id
        target_execution.agent_display_name = "implementer"
        target_execution.status = "waiting"

        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        sender_execution = Mock(spec=AgentExecution)
        sender_execution.agent_id = str(uuid4())
        sender_execution.agent_display_name = "orchestrator"
        sender_execution.status = "working"

        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(mock_project),       # Project lookup
                _scalar_result(target_execution),    # Agent display name resolution
                _scalar_result(sender_execution),    # Sender lookup for counters
                _update_result(),                    # increment sent
                _update_result(),                    # increment waiting
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        result = await service.send_message(
            to_agents=["implementer"],
            content="Direct message",
            project_id=project_id,
            message_type="direct",
            from_agent="orchestrator",
            tenant_key="test-tenant",
        )

        assert isinstance(result, SendMessageResult)
        assert len(added_messages) == 1
        assert target_agent_id in added_messages[0].to_agents


# Fixtures
@pytest.fixture
def mock_db_manager():
    """Create properly configured mock database manager."""
    db_manager = Mock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.rollback = AsyncMock()
    db_manager.get_session_async = Mock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    """Create mock tenant manager with default test tenant."""
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
    return tenant_manager
