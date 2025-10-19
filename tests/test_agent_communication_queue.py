"""
Unit tests for AgentCommunicationQueue class.

Handover 0019: Tests for JSONB-based agent communication queue
operating on MCPAgentJob.messages field.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import MCPAgentJob
from tests.fixtures.base_test import BaseAsyncTest


class TestAgentCommunicationQueue(BaseAsyncTest):
    """Test suite for AgentCommunicationQueue"""

    def setup_method(self, method):
        """Setup test method"""
        super().setup_method(method)
        self.tenant_key = str(uuid.uuid4())
        self.job_id = str(uuid.uuid4())

    # ==================== Message Sending Tests ====================

    @pytest.mark.asyncio
    async def test_send_message_with_all_parameters(self):
        """Test sending message with all parameters specified"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        # Mock job retrieval
        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.job_id = self.job_id
        mock_job.messages = []

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="orchestrator",
            to_agent="analyzer",
            message_type="task_assignment",
            content="Analyze the codebase",
            priority=2,
            metadata={"task_type": "analysis"},
        )

        assert result["status"] == "success"
        assert result["message_id"] is not None
        assert len(mock_job.messages) == 1

        msg = mock_job.messages[0]
        assert msg["from_agent"] == "orchestrator"
        assert msg["to_agent"] == "analyzer"
        assert msg["type"] == "task_assignment"
        assert msg["content"] == "Analyze the codebase"
        assert msg["priority"] == 2
        assert msg["acknowledged"] is False
        assert msg["metadata"]["task_type"] == "analysis"
        assert "id" in msg
        assert "timestamp" in msg

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_broadcast(self):
        """Test sending broadcast message (to_agent=None)"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.job_id = self.job_id
        mock_job.messages = []

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="orchestrator",
            to_agent=None,
            message_type="broadcast",
            content="System update",
            priority=1,
        )

        assert result["status"] == "success"
        msg = mock_job.messages[0]
        assert msg["to_agent"] is None
        assert msg["type"] == "broadcast"

    @pytest.mark.asyncio
    async def test_send_message_batch(self):
        """Test batch message sending"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.job_id = self.job_id
        mock_job.messages = []

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        queue = AgentCommunicationQueue(mock_db)

        messages = [
            {
                "from_agent": "orchestrator",
                "to_agent": "analyzer",
                "type": "task",
                "content": "Task 1",
                "priority": 1,
            },
            {
                "from_agent": "orchestrator",
                "to_agent": "implementer",
                "type": "task",
                "content": "Task 2",
                "priority": 2,
            },
            {
                "from_agent": "orchestrator",
                "to_agent": "tester",
                "type": "task",
                "content": "Task 3",
                "priority": 0,
            },
        ]

        result = await queue.send_message_batch(
            session=mock_session, job_id=self.job_id, tenant_key=self.tenant_key, messages=messages
        )

        assert result["status"] == "success"
        assert result["sent_count"] == 3
        assert len(mock_job.messages) == 3

        # Verify each message
        assert mock_job.messages[0]["content"] == "Task 1"
        assert mock_job.messages[1]["content"] == "Task 2"
        assert mock_job.messages[2]["content"] == "Task 3"

        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_priority_handling(self):
        """Test message priority values (0=low, 1=normal, 2=high)"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = []

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        queue = AgentCommunicationQueue(mock_db)

        # Test low priority
        await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="agent1",
            to_agent="agent2",
            message_type="info",
            content="Low priority",
            priority=0,
        )

        # Test normal priority
        await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="agent1",
            to_agent="agent2",
            message_type="info",
            content="Normal priority",
            priority=1,
        )

        # Test high priority
        await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="agent1",
            to_agent="agent2",
            message_type="info",
            content="High priority",
            priority=2,
        )

        assert mock_job.messages[0]["priority"] == 0
        assert mock_job.messages[1]["priority"] == 1
        assert mock_job.messages[2]["priority"] == 2

    @pytest.mark.asyncio
    async def test_send_message_invalid_priority(self):
        """Test sending message with invalid priority value"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = []

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="agent1",
            to_agent="agent2",
            message_type="info",
            content="Invalid priority",
            priority=5,
        )

        assert result["status"] == "error"
        assert "priority" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_message_job_not_found(self):
        """Test sending message when job doesn't exist"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.send_message(
            session=mock_session,
            job_id="nonexistent-job",
            tenant_key=self.tenant_key,
            from_agent="agent1",
            to_agent="agent2",
            message_type="info",
            content="Test",
        )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_message_tenant_isolation(self):
        """Test that messages are tenant-isolated"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        # Job belongs to different tenant
        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = "different-tenant-key"
        mock_job.messages = []

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="agent1",
            to_agent="agent2",
            message_type="info",
            content="Test",
        )

        assert result["status"] == "error"
        assert "tenant" in result["error"].lower()

    # ==================== Message Retrieval Tests ====================

    @pytest.mark.asyncio
    async def test_get_messages_no_filters(self):
        """Test retrieving all messages without filters"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {
                "id": str(uuid.uuid4()),
                "from_agent": "agent1",
                "to_agent": "agent2",
                "type": "task",
                "content": "Message 1",
                "priority": 1,
                "acknowledged": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "from_agent": "agent1",
                "to_agent": "agent3",
                "type": "info",
                "content": "Message 2",
                "priority": 0,
                "acknowledged": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.get_messages(session=mock_session, job_id=self.job_id, tenant_key=self.tenant_key)

        assert result["status"] == "success"
        assert len(result["messages"]) == 2

    @pytest.mark.asyncio
    async def test_get_messages_filtered_by_to_agent(self):
        """Test retrieving messages filtered by to_agent"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {
                "id": str(uuid.uuid4()),
                "from_agent": "orchestrator",
                "to_agent": "analyzer",
                "type": "task",
                "content": "For analyzer",
                "priority": 1,
                "acknowledged": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "from_agent": "orchestrator",
                "to_agent": "implementer",
                "type": "task",
                "content": "For implementer",
                "priority": 1,
                "acknowledged": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "from_agent": "orchestrator",
                "to_agent": "analyzer",
                "type": "info",
                "content": "Another for analyzer",
                "priority": 0,
                "acknowledged": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.get_messages(
            session=mock_session, job_id=self.job_id, tenant_key=self.tenant_key, to_agent="analyzer"
        )

        assert result["status"] == "success"
        assert len(result["messages"]) == 2
        assert all(msg["to_agent"] == "analyzer" for msg in result["messages"])

    @pytest.mark.asyncio
    async def test_get_messages_filtered_by_message_type(self):
        """Test retrieving messages filtered by message_type"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {
                "id": str(uuid.uuid4()),
                "from_agent": "agent1",
                "to_agent": "agent2",
                "type": "task",
                "content": "Task message",
                "priority": 1,
                "acknowledged": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "from_agent": "agent1",
                "to_agent": "agent2",
                "type": "info",
                "content": "Info message",
                "priority": 0,
                "acknowledged": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "from_agent": "agent1",
                "to_agent": "agent2",
                "type": "task",
                "content": "Another task",
                "priority": 2,
                "acknowledged": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.get_messages(
            session=mock_session, job_id=self.job_id, tenant_key=self.tenant_key, message_type="task"
        )

        assert result["status"] == "success"
        assert len(result["messages"]) == 2
        assert all(msg["type"] == "task" for msg in result["messages"])

    @pytest.mark.asyncio
    async def test_get_messages_unread_only(self):
        """Test retrieving only unread messages"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {
                "id": str(uuid.uuid4()),
                "from_agent": "agent1",
                "to_agent": "agent2",
                "type": "task",
                "content": "Unread message 1",
                "priority": 1,
                "acknowledged": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "from_agent": "agent1",
                "to_agent": "agent2",
                "type": "info",
                "content": "Read message",
                "priority": 0,
                "acknowledged": True,
                "acknowledged_at": datetime.now(timezone.utc).isoformat(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "from_agent": "agent1",
                "to_agent": "agent2",
                "type": "task",
                "content": "Unread message 2",
                "priority": 2,
                "acknowledged": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.get_messages(
            session=mock_session, job_id=self.job_id, tenant_key=self.tenant_key, unread_only=True
        )

        assert result["status"] == "success"
        assert len(result["messages"]) == 2
        assert all(msg["acknowledged"] is False for msg in result["messages"])

    @pytest.mark.asyncio
    async def test_get_unread_count(self):
        """Test getting count of unread messages"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {"id": str(uuid.uuid4()), "acknowledged": False},
            {"id": str(uuid.uuid4()), "acknowledged": True},
            {"id": str(uuid.uuid4()), "acknowledged": False},
            {"id": str(uuid.uuid4()), "acknowledged": False},
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.get_unread_count(session=mock_session, job_id=self.job_id, tenant_key=self.tenant_key)

        assert result["status"] == "success"
        assert result["unread_count"] == 3

    @pytest.mark.asyncio
    async def test_get_unread_count_by_agent(self):
        """Test getting unread count for specific agent"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {"id": str(uuid.uuid4()), "to_agent": "analyzer", "acknowledged": False},
            {"id": str(uuid.uuid4()), "to_agent": "analyzer", "acknowledged": True},
            {"id": str(uuid.uuid4()), "to_agent": "implementer", "acknowledged": False},
            {"id": str(uuid.uuid4()), "to_agent": "analyzer", "acknowledged": False},
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.get_unread_count(
            session=mock_session, job_id=self.job_id, tenant_key=self.tenant_key, to_agent="analyzer"
        )

        assert result["status"] == "success"
        assert result["unread_count"] == 2

    # ==================== Message Acknowledgment Tests ====================

    @pytest.mark.asyncio
    async def test_acknowledge_message(self):
        """Test acknowledging a message"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        message_id = str(uuid.uuid4())
        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {
                "id": message_id,
                "from_agent": "orchestrator",
                "to_agent": "analyzer",
                "type": "task",
                "content": "Test message",
                "priority": 1,
                "acknowledged": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        # Use flag_modified mock
        type(mock_job).messages = PropertyMock(return_value=mock_job.messages)

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.acknowledge_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            message_id=message_id,
            agent_id="analyzer",
        )

        assert result["status"] == "success"
        assert mock_job.messages[0]["acknowledged"] is True
        assert mock_job.messages[0]["acknowledged_by"] == "analyzer"
        assert "acknowledged_at" in mock_job.messages[0]
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_acknowledge_already_acknowledged_message(self):
        """Test acknowledging an already acknowledged message"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        message_id = str(uuid.uuid4())
        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {
                "id": message_id,
                "acknowledged": True,
                "acknowledged_at": datetime.now(timezone.utc).isoformat(),
                "acknowledged_by": "another_agent",
            }
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.acknowledge_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            message_id=message_id,
            agent_id="analyzer",
        )

        assert result["status"] == "error"
        assert "already acknowledged" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_acknowledge_message_not_found(self):
        """Test acknowledging a non-existent message"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = []

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.acknowledge_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            message_id="nonexistent-id",
            agent_id="analyzer",
        )

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_acknowledge_all_messages(self):
        """Test acknowledging all unread messages"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {
                "id": str(uuid.uuid4()),
                "to_agent": "analyzer",
                "acknowledged": False,
            },
            {
                "id": str(uuid.uuid4()),
                "to_agent": "analyzer",
                "acknowledged": True,
                "acknowledged_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "to_agent": "analyzer",
                "acknowledged": False,
            },
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        type(mock_job).messages = PropertyMock(return_value=mock_job.messages)

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.acknowledge_all_messages(
            session=mock_session, job_id=self.job_id, tenant_key=self.tenant_key, agent_id="analyzer", to_agent="analyzer"
        )

        assert result["status"] == "success"
        assert result["acknowledged_count"] == 2

        # Verify only unread messages were acknowledged
        unread_count = sum(1 for msg in mock_job.messages if msg["acknowledged"])
        assert unread_count == 3  # 1 already acked + 2 newly acked

        mock_session.commit.assert_called_once()

    # ==================== JSONB Operations Tests ====================

    @pytest.mark.asyncio
    async def test_jsonb_array_append(self):
        """Test JSONB array append operation"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [{"id": "existing-msg", "content": "Existing"}]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        queue = AgentCommunicationQueue(mock_db)

        # Send new message (should append to array)
        await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="agent1",
            to_agent="agent2",
            message_type="info",
            content="New message",
        )

        assert len(mock_job.messages) == 2
        assert mock_job.messages[0]["id"] == "existing-msg"
        assert mock_job.messages[1]["content"] == "New message"

    @pytest.mark.asyncio
    async def test_jsonb_message_update_acknowledgment(self):
        """Test JSONB message update for acknowledgment"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        message_id = str(uuid.uuid4())
        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {
                "id": message_id,
                "content": "Test",
                "acknowledged": False,
            }
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        type(mock_job).messages = PropertyMock(return_value=mock_job.messages)

        queue = AgentCommunicationQueue(mock_db)

        # Acknowledge message
        await queue.acknowledge_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            message_id=message_id,
            agent_id="test_agent",
        )

        # Verify JSONB object was updated
        msg = mock_job.messages[0]
        assert msg["acknowledged"] is True
        assert msg["acknowledged_by"] == "test_agent"
        assert "acknowledged_at" in msg

    @pytest.mark.asyncio
    async def test_jsonb_query_filtering(self):
        """Test JSONB query filtering by message properties"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = self.tenant_key
        mock_job.messages = [
            {"id": "1", "to_agent": "analyzer", "type": "task", "acknowledged": False},
            {"id": "2", "to_agent": "implementer", "type": "task", "acknowledged": False},
            {"id": "3", "to_agent": "analyzer", "type": "info", "acknowledged": True},
            {"id": "4", "to_agent": "analyzer", "type": "task", "acknowledged": False},
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        # Filter by to_agent, type, and unread
        result = await queue.get_messages(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            to_agent="analyzer",
            message_type="task",
            unread_only=True,
        )

        assert result["status"] == "success"
        assert len(result["messages"]) == 2
        assert all(msg["to_agent"] == "analyzer" for msg in result["messages"])
        assert all(msg["type"] == "task" for msg in result["messages"])
        assert all(msg["acknowledged"] is False for msg in result["messages"])

    # ==================== Multi-Tenant Isolation Tests ====================

    @pytest.mark.asyncio
    async def test_multi_tenant_message_isolation(self):
        """Test that messages are isolated by tenant_key"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        # Job belongs to different tenant
        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = "different-tenant"
        mock_job.messages = []

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        # Try to send message with wrong tenant_key
        result = await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="agent1",
            to_agent="agent2",
            message_type="info",
            content="Test",
        )

        assert result["status"] == "error"
        assert "tenant" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_cross_tenant_message_prevention(self):
        """Test prevention of cross-tenant message access"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        tenant1_key = str(uuid.uuid4())
        tenant2_key = str(uuid.uuid4())

        # Job belongs to tenant1
        mock_job = Mock(spec=MCPAgentJob)
        mock_job.tenant_key = tenant1_key
        mock_job.messages = [{"id": str(uuid.uuid4()), "content": "Tenant 1 message", "acknowledged": False}]

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_job
        mock_session.query.return_value = mock_query

        queue = AgentCommunicationQueue(mock_db)

        # Try to access with tenant2 credentials
        result = await queue.get_messages(session=mock_session, job_id=self.job_id, tenant_key=tenant2_key)

        assert result["status"] == "error"
        assert "tenant" in result["error"].lower()

    # ==================== Error Handling Tests ====================

    @pytest.mark.asyncio
    async def test_database_error_handling(self):
        """Test handling of database errors"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        # Simulate database error
        mock_session.query.side_effect = Exception("Database connection error")

        queue = AgentCommunicationQueue(mock_db)

        result = await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="agent1",
            to_agent="agent2",
            message_type="info",
            content="Test",
        )

        assert result["status"] == "error"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test validation of required message fields"""
        from src.giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        mock_db = Mock(spec=DatabaseManager)
        mock_session = self.create_async_mock("session")

        queue = AgentCommunicationQueue(mock_db)

        # Missing content
        result = await queue.send_message(
            session=mock_session,
            job_id=self.job_id,
            tenant_key=self.tenant_key,
            from_agent="agent1",
            to_agent="agent2",
            message_type="info",
            content="",
        )

        assert result["status"] == "error"
        assert "content" in result["error"].lower()
