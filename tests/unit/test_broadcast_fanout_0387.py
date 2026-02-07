"""
Unit tests for Broadcast Fan-out at Write (Handover 0387)

TDD RED Phase: Tests written BEFORE implementation.
Tests cover:
1. Fan-out creates individual messages per recipient
2. Per-recipient acknowledgment works independently
3. Sender exclusion during fan-out
4. Completed agents exclusion during fan-out

Expected: ALL tests FAIL until implementation is complete.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.services.message_service import MessageService


class TestBroadcastFanoutSendMessage:
    """Tests for fan-out behavior in send_message() when to_agents=['all']"""

    @pytest.mark.asyncio
    async def test_broadcast_fanout_creates_individual_messages(self, mock_db_manager, mock_tenant_manager):
        """
        TDD RED: Broadcast to 'all' should create one Message per active agent.

        Scenario:
        - Project has 3 active agents (orchestrator, impl-1, analyzer-1)
        - Orchestrator sends broadcast to_agents=["all"]
        - Expected: 2 Message records created (excluding sender)
        - Each Message has to_agents=[single_agent_id] (not "all")
        """
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        # Mock active agent executions (3 agents)
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

        active_executions = [orch_execution, impl_execution, analyzer_execution]

        # Track added messages
        added_messages = []

        def track_add(msg):
            added_messages.append(msg)

        session.add = Mock(side_effect=track_add)

        # Mock database responses in order:
        # 1. Project lookup (with tenant isolation)
        # 2. Active agents lookup for fan-out
        project_result = Mock()
        project_result.scalar_one_or_none = Mock(return_value=mock_project)

        agents_result = Mock()
        agents_result.scalars = Mock(return_value=Mock(all=Mock(return_value=active_executions)))

        # Additional calls for WebSocket event processing
        ws_agents_result = Mock()
        ws_agents_result.scalars = Mock(return_value=Mock(all=Mock(return_value=active_executions)))

        session.execute = AsyncMock(
            side_effect=[
                project_result,  # Project lookup
                agents_result,  # Fan-out agent lookup
                ws_agents_result,  # WebSocket recipient lookup
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        # Act: Send broadcast from orchestrator
        result = await service.send_message(
            to_agents=["all"],
            content="Broadcast test message",
            project_id=project_id,
            message_type="broadcast",
            from_agent="orchestrator",
            tenant_key=tenant_key,
        )

        # Assert: Success
        assert result["success"] is True, f"Expected success, got error: {result.get('error')}"

        # Assert: Fan-out created individual messages
        # Should have 2 messages (impl + analyzer, excluding orchestrator sender)
        assert len(added_messages) == 2, (
            f"Expected 2 individual messages (fan-out), got {len(added_messages)}. "
            f"Fan-out should create one message per recipient, excluding sender."
        )

        # Assert: Each message has single recipient (not "all")
        for msg in added_messages:
            assert "all" not in msg.to_agents, (
                f"Message should have individual agent_id, not 'all'. Got: {msg.to_agents}"
            )
            assert len(msg.to_agents) == 1, (
                f"Each fan-out message should have exactly 1 recipient. Got: {msg.to_agents}"
            )

        # Assert: All recipients are unique
        recipient_ids = [msg.to_agents[0] for msg in added_messages]
        assert len(recipient_ids) == len(set(recipient_ids)), (
            f"Recipients should be unique. Got duplicates: {recipient_ids}"
        )

    @pytest.mark.asyncio
    async def test_broadcast_excludes_sender(self, mock_db_manager, mock_tenant_manager):
        """
        TDD RED: Sender should not receive their own broadcast.

        Scenario:
        - Orchestrator sends broadcast
        - Orchestrator's agent_id should NOT be in any Message.to_agents
        """
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())
        sender_agent_id = str(uuid4())

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        # Mock executions including sender
        sender_execution = Mock(spec=AgentExecution)
        sender_execution.agent_id = sender_agent_id
        sender_execution.agent_display_name = "orchestrator"
        sender_execution.status = "working"

        other_execution = Mock(spec=AgentExecution)
        other_execution.agent_id = str(uuid4())
        other_execution.agent_display_name = "implementer"
        other_execution.status = "waiting"

        active_executions = [sender_execution, other_execution]

        # Track added messages
        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        project_result = Mock()
        project_result.scalar_one_or_none = Mock(return_value=mock_project)

        agents_result = Mock()
        agents_result.scalars = Mock(return_value=Mock(all=Mock(return_value=active_executions)))

        ws_agents_result = Mock()
        ws_agents_result.scalars = Mock(return_value=Mock(all=Mock(return_value=active_executions)))

        session.execute = AsyncMock(
            side_effect=[
                project_result,
                agents_result,
                ws_agents_result,
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.send_message(
            to_agents=["all"],
            content="Test broadcast",
            project_id=project_id,
            from_agent="orchestrator",
            tenant_key=tenant_key,
        )

        # Assert: Sender not in recipients
        assert result["success"] is True

        all_recipients = []
        for msg in added_messages:
            all_recipients.extend(msg.to_agents)

        assert sender_agent_id not in all_recipients, (
            f"Sender ({sender_agent_id}) should be excluded from broadcast recipients. Found in: {all_recipients}"
        )

    @pytest.mark.asyncio
    async def test_broadcast_excludes_completed_agents(self, mock_db_manager, mock_tenant_manager):
        """
        TDD RED: Completed agents should not receive broadcasts.

        Scenario:
        - Project has 3 agents: 2 active, 1 completed
        - Broadcast should only go to active agents
        """
        db_manager, session = mock_db_manager
        tenant_key = "test-tenant"
        project_id = str(uuid4())
        completed_agent_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = tenant_key

        # Only active agents returned (status filter)
        active_execution = Mock(spec=AgentExecution)
        active_execution.agent_id = str(uuid4())
        active_execution.agent_display_name = "implementer"
        active_execution.status = "waiting"

        # This execution is completed - should NOT be in fan-out query results
        completed_execution = Mock(spec=AgentExecution)
        completed_execution.agent_id = completed_agent_id
        completed_execution.agent_display_name = "analyzer"
        completed_execution.status = "completed"

        # Fan-out query should only return active agents
        active_executions = [active_execution]  # completed excluded by query

        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        project_result = Mock()
        project_result.scalar_one_or_none = Mock(return_value=mock_project)

        agents_result = Mock()
        agents_result.scalars = Mock(return_value=Mock(all=Mock(return_value=active_executions)))

        ws_agents_result = Mock()
        ws_agents_result.scalars = Mock(return_value=Mock(all=Mock(return_value=active_executions)))

        session.execute = AsyncMock(
            side_effect=[
                project_result,
                agents_result,
                ws_agents_result,
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.send_message(
            to_agents=["all"],
            content="Test broadcast",
            project_id=project_id,
            from_agent="external-sender",  # External so no sender exclusion overlap
            tenant_key=tenant_key,
        )

        # Assert
        assert result["success"] is True

        all_recipients = []
        for msg in added_messages:
            all_recipients.extend(msg.to_agents)

        assert completed_agent_id not in all_recipients, (
            f"Completed agent ({completed_agent_id}) should be excluded. Found in: {all_recipients}"
        )


class TestBroadcastFanoutReceiveMessages:
    """Tests for simplified receive_messages() after fan-out implementation"""

    @pytest.mark.asyncio
    async def test_broadcast_per_recipient_acknowledgment(self, mock_db_manager):
        """
        TDD RED: Each agent should acknowledge independently.

        Scenario:
        - Broadcast sent to 3 agents (fan-out created 3 Message records)
        - Agent A reads messages -> Agent A's Message.status = acknowledged
        - Agent B's Message.status should remain "pending"
        """
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        agent_a_id = str(uuid4())
        agent_b_id = str(uuid4())
        agent_c_id = str(uuid4())
        project_id = str(uuid4())
        job_id = str(uuid4())

        # Mock Agent A's execution
        agent_a_execution = Mock(spec=AgentExecution)
        agent_a_execution.agent_id = agent_a_id
        agent_a_execution.job_id = job_id
        agent_a_execution.tenant_key = "test-tenant"

        # Mock job
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = job_id
        mock_job.project_id = project_id
        mock_job.job_type = "implementer"

        # Fan-out created individual messages - Agent A's message
        msg_for_a = Mock(spec=Message)
        msg_for_a.id = str(uuid4())
        msg_for_a.to_agents = [agent_a_id]  # Individual recipient (fan-out)
        msg_for_a.status = "pending"
        msg_for_a.content = "Broadcast content"
        msg_for_a.message_type = "broadcast"
        msg_for_a.priority = "normal"
        msg_for_a.created_at = datetime.now(timezone.utc)
        msg_for_a.acknowledged_at = None
        msg_for_a.acknowledged_by = None
        msg_for_a.meta_data = {"_from_agent": "orchestrator"}

        # Agent B's message (should NOT be affected)
        msg_for_b = Mock(spec=Message)
        msg_for_b.id = str(uuid4())
        msg_for_b.to_agents = [agent_b_id]
        msg_for_b.status = "pending"

        # Setup mocks
        exec_result = Mock()
        exec_result.scalar_one_or_none = Mock(return_value=agent_a_execution)

        job_result = Mock()
        job_result.scalar_one_or_none = Mock(return_value=mock_job)

        # Messages query returns only Agent A's message
        msg_result = Mock()
        msg_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[msg_for_a])))

        session.execute = AsyncMock(
            side_effect=[
                exec_result,  # Agent execution lookup
                job_result,  # Job lookup
                msg_result,  # Messages query
            ]
        )

        service = MessageService(db_manager, tenant_manager)

        # Act: Agent A receives messages
        result = await service.receive_messages(agent_id=agent_a_id, limit=10, tenant_key="test-tenant")

        # Assert: Success and message retrieved
        assert result["success"] is True
        assert result["count"] == 1

        # Assert: Agent A's message status changed
        assert msg_for_a.status == "acknowledged", f"Agent A's message should be acknowledged. Got: {msg_for_a.status}"

        # Assert: Agent B's message NOT affected (independent Message record)
        assert msg_for_b.status == "pending", (
            f"Agent B's message should remain pending. Got: {msg_for_b.status}. "
            "Fan-out ensures each agent has independent message record."
        )

    @pytest.mark.asyncio
    async def test_receive_no_broadcast_or_clause_needed(self, mock_db_manager):
        """
        TDD RED: After fan-out, receive_messages should NOT need broadcast OR clause.

        With fan-out at write, each Message has to_agents=[single_agent_id].
        Query simplifies to: Message.to_agents.contains([agent_id])
        No need for: OR(to_agents.contains(['all']) AND sender != agent)

        This test verifies the query doesn't match literal 'all' messages.
        """
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        agent_id = str(uuid4())
        project_id = str(uuid4())
        job_id = str(uuid4())

        # Mock execution
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.agent_id = agent_id
        mock_execution.job_id = job_id
        mock_execution.tenant_key = "test-tenant"

        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = job_id
        mock_job.project_id = project_id
        mock_job.job_type = "implementer"

        # Message with literal 'all' (OLD pattern - should NOT be matched)
        old_broadcast_msg = Mock(spec=Message)
        old_broadcast_msg.id = str(uuid4())
        old_broadcast_msg.to_agents = ["all"]  # OLD pattern
        old_broadcast_msg.status = "pending"

        # Message with fan-out (NEW pattern - should be matched)
        fanout_msg = Mock(spec=Message)
        fanout_msg.id = str(uuid4())
        fanout_msg.to_agents = [agent_id]  # NEW pattern
        fanout_msg.status = "pending"
        fanout_msg.content = "Fan-out message"
        fanout_msg.message_type = "broadcast"
        fanout_msg.priority = "normal"
        fanout_msg.created_at = datetime.now(timezone.utc)
        fanout_msg.acknowledged_at = None
        fanout_msg.acknowledged_by = None
        fanout_msg.meta_data = {"_from_agent": "orchestrator"}

        exec_result = Mock()
        exec_result.scalar_one_or_none = Mock(return_value=mock_execution)

        job_result = Mock()
        job_result.scalar_one_or_none = Mock(return_value=mock_job)

        # After implementation, query should only match fan-out messages
        # (not old 'all' messages)
        msg_result = Mock()
        msg_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[fanout_msg])))

        session.execute = AsyncMock(
            side_effect=[
                exec_result,
                job_result,
                msg_result,
            ]
        )

        service = MessageService(db_manager, tenant_manager)

        # Act
        result = await service.receive_messages(agent_id=agent_id, tenant_key="test-tenant")

        # Assert
        assert result["success"] is True

        # With fan-out, we should NOT receive old 'all' messages
        # Only individual fan-out messages should be delivered
        received_ids = [m["id"] for m in result["messages"]]
        assert str(old_broadcast_msg.id) not in received_ids, (
            "Old-style 'all' messages should not be matched after fan-out implementation. "
            "Query should be simplified to direct agent_id match only."
        )


class TestBroadcastFanoutEdgeCases:
    """Edge case tests for broadcast fan-out"""

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_project_no_messages_created(self, mock_db_manager, mock_tenant_manager):
        """
        Broadcast to project with only sender should create 0 messages.
        """
        db_manager, session = mock_db_manager
        project_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = "test-tenant"

        # Only sender in project
        sender_execution = Mock(spec=AgentExecution)
        sender_execution.agent_id = str(uuid4())
        sender_execution.agent_display_name = "orchestrator"
        sender_execution.status = "working"

        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        project_result = Mock()
        project_result.scalar_one_or_none = Mock(return_value=mock_project)

        agents_result = Mock()
        agents_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[sender_execution])))

        ws_agents_result = Mock()
        ws_agents_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))

        session.execute = AsyncMock(
            side_effect=[
                project_result,
                agents_result,
                ws_agents_result,
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.send_message(
            to_agents=["all"],
            content="Lonely broadcast",
            project_id=project_id,
            from_agent="orchestrator",
            tenant_key="test-tenant",
        )

        # Assert: Should succeed but create 0 messages (no recipients)
        assert result["success"] is True
        assert len(added_messages) == 0, (
            f"Broadcast to empty project should create 0 messages. Got: {len(added_messages)}"
        )

    @pytest.mark.asyncio
    async def test_direct_message_unchanged(self, mock_db_manager, mock_tenant_manager):
        """
        Direct messages (to_agents=['specific-agent']) should still work normally.
        Fan-out only applies when to_agents=['all'].
        """
        db_manager, session = mock_db_manager
        project_id = str(uuid4())
        target_agent_id = str(uuid4())

        mock_project = Mock(spec=Project)
        mock_project.id = project_id
        mock_project.tenant_key = "test-tenant"

        # Mock resolved agent execution
        target_execution = Mock(spec=AgentExecution)
        target_execution.agent_id = target_agent_id
        target_execution.agent_display_name = "implementer"
        target_execution.status = "waiting"
        added_messages = []
        session.add = Mock(side_effect=lambda msg: added_messages.append(msg))

        project_result = Mock()
        project_result.scalar_one_or_none = Mock(return_value=mock_project)

        # For direct message, agent type resolution
        exec_result = Mock()
        exec_result.scalar_one_or_none = Mock(return_value=target_execution)

        ws_agents_result = Mock()
        ws_agents_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[target_execution])))

        session.execute = AsyncMock(
            side_effect=[
                project_result,
                exec_result,  # Agent type resolution
                ws_agents_result,
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        # Act: Send direct message (NOT broadcast)
        result = await service.send_message(
            to_agents=["implementer"],  # Direct to specific agent type
            content="Direct message",
            project_id=project_id,
            message_type="direct",
            from_agent="orchestrator",
            tenant_key="test-tenant",
        )

        # Assert: Direct message creates exactly 1 message
        assert result["success"] is True
        assert len(added_messages) == 1, f"Direct message should create exactly 1 message. Got: {len(added_messages)}"

        # Assert: to_agents contains resolved agent_id (not "implementer" or "all")
        msg = added_messages[0]
        assert target_agent_id in msg.to_agents, f"Direct message should resolve to agent_id. Got: {msg.to_agents}"


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
