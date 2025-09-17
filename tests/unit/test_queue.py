"""
Unit tests for MessageQueue class.
Tests message routing, acknowledgments, persistence, and concurrent handling.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import uuid
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.queue import MessageQueue, MessagePriority
from src.giljo_mcp.enums import MessageStatus
from src.giljo_mcp.models import Message, Agent
from tests.fixtures.base_test import BaseAsyncTest
from tests.fixtures.base_fixtures import TestData


class TestMessageQueue(BaseAsyncTest):
    """Test suite for MessageQueue"""

    def setup_method(self, method):
        """Setup test method"""
        super().setup_method(method)
        self.queue = MessageQueue()
        self.project_id = str(uuid.uuid4())
        self.tenant_key = TestData.generate_tenant_key()

    # ==================== Message Creation Tests ====================

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending"""
        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await self.queue.send_message(
            from_agent="orchestrator",
            to_agent="analyzer",
            content="Analyze the codebase",
            project_id=self.project_id,
            priority=MessagePriority.HIGH,
            db_session=mock_session
        )

        assert result["status"] == "success"
        assert result["message"] is not None
        assert result["message"].from_agent == "orchestrator"
        assert result["message"].to_agent == "analyzer"
        assert result["message"].priority == MessagePriority.HIGH.value
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_broadcast_message(self):
        """Test broadcasting message to all agents"""
        mock_session = self.create_async_mock("session")

        # Mock agents in project
        agents = [
            Mock(name="agent1", project_id=self.project_id),
            Mock(name="agent2", project_id=self.project_id),
            Mock(name="agent3", project_id=self.project_id)
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.filter.return_value.all.return_value = agents
        mock_session.query.return_value = mock_query
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()

        result = await self.queue.broadcast_message(
            from_agent="orchestrator",
            content="System update",
            project_id=self.project_id,
            db_session=mock_session
        )

        assert result["status"] == "success"
        assert result["sent_count"] == 3
        assert mock_session.add.call_count == 3
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_metadata(self):
        """Test sending message with metadata"""
        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        metadata = {
            "task_type": "analysis",
            "requires_response": True,
            "timeout": 300
        }

        result = await self.queue.send_message(
            from_agent="orchestrator",
            to_agent="analyzer",
            content="Analyze with metadata",
            project_id=self.project_id,
            metadata=metadata,
            db_session=mock_session
        )

        assert result["message"].metadata == metadata

    # ==================== Message Retrieval Tests ====================

    @pytest.mark.asyncio
    async def test_get_pending_messages(self):
        """Test retrieving pending messages for an agent"""
        mock_session = self.create_async_mock("session")

        # Create mock messages
        messages = [
            Mock(id=str(uuid.uuid4()), content="Message 1", status=MessageStatus.PENDING.value),
            Mock(id=str(uuid.uuid4()), content="Message 2", status=MessageStatus.PENDING.value)
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = messages
        mock_session.query.return_value = mock_query

        result = await self.queue.get_pending_messages(
            agent_name="analyzer",
            project_id=self.project_id,
            limit=10,
            db_session=mock_session
        )

        assert len(result) == 2
        mock_query.filter_by.assert_called_with(
            to_agent="analyzer",
            project_id=self.project_id
        )

    @pytest.mark.asyncio
    async def test_get_messages_by_priority(self):
        """Test retrieving messages ordered by priority"""
        mock_session = self.create_async_mock("session")

        # Create mock messages with different priorities
        high_priority = Mock(
            id="1",
            priority=MessagePriority.CRITICAL.value,
            created_at=datetime.utcnow()
        )
        medium_priority = Mock(
            id="2",
            priority=MessagePriority.NORMAL.value,
            created_at=datetime.utcnow()
        )

        mock_query = Mock()
        # Should order by priority DESC, created_at ASC
        mock_query.filter_by.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            high_priority, medium_priority
        ]
        mock_session.query.return_value = mock_query

        result = await self.queue.get_pending_messages(
            agent_name="analyzer",
            project_id=self.project_id,
            db_session=mock_session
        )

        assert result[0].priority == MessagePriority.CRITICAL.value
        assert result[1].priority == MessagePriority.NORMAL.value

    # ==================== Acknowledgment Tests ====================

    @pytest.mark.asyncio
    async def test_acknowledge_message(self):
        """Test message acknowledgment"""
        mock_session = self.create_async_mock("session")

        mock_message = Mock(spec=Message)
        mock_message.id = str(uuid.uuid4())
        mock_message.status = MessageStatus.PENDING.value
        mock_message.metadata = {}

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_message
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        result = await self.queue.acknowledge_message(
            message_id=mock_message.id,
            agent_name="analyzer",
            db_session=mock_session
        )

        assert result["status"] == "success"
        assert mock_message.status == MessageStatus.ACKNOWLEDGED.value
        assert mock_message.metadata["acknowledged_by"] == "analyzer"
        assert "acknowledged_at" in mock_message.metadata
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_acknowledge_array(self):
        """Test acknowledging multiple messages at once"""
        mock_session = self.create_async_mock("session")

        # Create mock messages
        messages = []
        message_ids = []
        for i in range(3):
            msg = Mock(spec=Message)
            msg.id = str(uuid.uuid4())
            msg.status = MessageStatus.PENDING.value
            msg.metadata = {}
            messages.append(msg)
            message_ids.append(msg.id)

        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = messages
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        result = await self.queue.acknowledge_array(
            message_ids=message_ids,
            agent_name="analyzer",
            db_session=mock_session
        )

        assert result["status"] == "success"
        assert result["acknowledged_count"] == 3
        for msg in messages:
            assert msg.status == MessageStatus.ACKNOWLEDGED.value
            assert msg.metadata["acknowledged_by"] == "analyzer"
        mock_session.commit.assert_called_once()

    # ==================== Message Completion Tests ====================

    @pytest.mark.asyncio
    async def test_complete_message(self):
        """Test marking message as completed"""
        mock_session = self.create_async_mock("session")

        mock_message = Mock(spec=Message)
        mock_message.id = str(uuid.uuid4())
        mock_message.status = MessageStatus.ACKNOWLEDGED.value
        mock_message.metadata = {"acknowledged_by": "analyzer"}

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_message
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        result_data = {"analysis": "complete", "findings": ["issue1", "issue2"]}

        result = await self.queue.complete_message(
            message_id=mock_message.id,
            agent_name="analyzer",
            result=result_data,
            db_session=mock_session
        )

        assert result["status"] == "success"
        assert mock_message.status == MessageStatus.COMPLETED.value
        assert mock_message.metadata["result"] == result_data
        assert "completed_at" in mock_message.metadata
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_fail_message(self):
        """Test marking message as failed"""
        mock_session = self.create_async_mock("session")

        mock_message = Mock(spec=Message)
        mock_message.id = str(uuid.uuid4())
        mock_message.status = MessageStatus.ACKNOWLEDGED.value
        mock_message.metadata = {}

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_message
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        error_msg = "Failed to process: timeout"

        result = await self.queue.fail_message(
            message_id=mock_message.id,
            error=error_msg,
            db_session=mock_session
        )

        assert result["status"] == "success"
        assert mock_message.status == MessageStatus.FAILED.value
        assert mock_message.metadata["error"] == error_msg
        assert "failed_at" in mock_message.metadata
        mock_session.commit.assert_called_once()

    # ==================== Retry Logic Tests ====================

    @pytest.mark.asyncio
    async def test_retry_failed_message(self):
        """Test retrying a failed message"""
        mock_session = self.create_async_mock("session")

        mock_message = Mock(spec=Message)
        mock_message.id = str(uuid.uuid4())
        mock_message.status = MessageStatus.FAILED.value
        mock_message.metadata = {
            "error": "Previous error",
            "retry_count": 1
        }

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_message
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        result = await self.queue.retry_message(
            message_id=mock_message.id,
            db_session=mock_session
        )

        assert result["status"] == "success"
        assert mock_message.status == MessageStatus.PENDING.value
        assert mock_message.metadata["retry_count"] == 2
        assert "last_retry_at" in mock_message.metadata
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that messages can't be retried beyond max limit"""
        mock_session = self.create_async_mock("session")

        mock_message = Mock(spec=Message)
        mock_message.id = str(uuid.uuid4())
        mock_message.status = MessageStatus.FAILED.value
        mock_message.metadata = {"retry_count": 3}  # Already at max

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_message
        mock_session.query.return_value = mock_query

        result = await self.queue.retry_message(
            message_id=mock_message.id,
            max_retries=3,
            db_session=mock_session
        )

        assert result["status"] == "error"
        assert "Max retries exceeded" in result["error"]

    # ==================== Queue Statistics Tests ====================

    @pytest.mark.asyncio
    async def test_get_queue_stats(self):
        """Test getting queue statistics"""
        mock_session = self.create_async_mock("session")

        # Mock count queries for different statuses
        mock_query = Mock()
        mock_query.filter_by.side_effect = [
            Mock(count=Mock(return_value=10)),  # Pending
            Mock(count=Mock(return_value=5)),   # Acknowledged
            Mock(count=Mock(return_value=20)),  # Completed
            Mock(count=Mock(return_value=2))    # Failed
        ]
        mock_session.query.return_value = mock_query

        result = await self.queue.get_queue_stats(
            project_id=self.project_id,
            db_session=mock_session
        )

        assert result["pending"] == 10
        assert result["acknowledged"] == 5
        assert result["completed"] == 20
        assert result["failed"] == 2
        assert result["total"] == 37

    # ==================== Concurrent Message Handling Tests ====================

    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self):
        """Test handling concurrent message operations"""
        mock_session = self.create_async_mock("session")
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Simulate concurrent message sending
        tasks = []
        for i in range(10):
            task = self.queue.send_message(
                from_agent="orchestrator",
                to_agent=f"agent_{i}",
                content=f"Message {i}",
                project_id=self.project_id,
                db_session=mock_session
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        assert all(r["status"] == "success" for r in results)
        assert mock_session.add.call_count == 10

    @pytest.mark.asyncio
    async def test_message_ordering_with_timestamps(self):
        """Test that messages are properly ordered by timestamp"""
        mock_session = self.create_async_mock("session")

        # Create messages with different timestamps
        now = datetime.utcnow()
        messages = [
            Mock(created_at=now - timedelta(minutes=5), priority=MessagePriority.NORMAL.value),
            Mock(created_at=now - timedelta(minutes=2), priority=MessagePriority.NORMAL.value),
            Mock(created_at=now - timedelta(minutes=10), priority=MessagePriority.NORMAL.value)
        ]

        mock_query = Mock()
        mock_query.filter_by.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = sorted(
            messages, key=lambda x: x.created_at
        )
        mock_session.query.return_value = mock_query

        result = await self.queue.get_pending_messages(
            agent_name="analyzer",
            project_id=self.project_id,
            db_session=mock_session
        )

        # Should be ordered oldest first (FIFO for same priority)
        assert result[0].created_at < result[1].created_at
        assert result[1].created_at < result[2].created_at

    # ==================== Message Filtering Tests ====================

    @pytest.mark.asyncio
    async def test_filter_messages_by_metadata(self):
        """Test filtering messages by metadata attributes"""
        mock_session = self.create_async_mock("session")

        # Create messages with different metadata
        urgent_msg = Mock(
            id="1",
            metadata={"urgent": True, "task_type": "critical"}
        )
        normal_msg = Mock(
            id="2",
            metadata={"urgent": False, "task_type": "routine"}
        )

        mock_query = Mock()
        mock_query.filter_by.return_value.filter.return_value.all.return_value = [urgent_msg]
        mock_session.query.return_value = mock_query

        result = await self.queue.get_messages_by_metadata(
            project_id=self.project_id,
            metadata_filter={"urgent": True},
            db_session=mock_session
        )

        assert len(result) == 1
        assert result[0].metadata["urgent"] is True

    @pytest.mark.asyncio
    async def test_purge_old_messages(self):
        """Test purging old completed messages"""
        mock_session = self.create_async_mock("session")

        # Mock old messages
        cutoff_date = datetime.utcnow() - timedelta(days=7)

        mock_query = Mock()
        mock_query.filter_by.return_value.filter.return_value.filter.return_value.delete.return_value = 5
        mock_session.query.return_value = mock_query
        mock_session.commit = AsyncMock()

        result = await self.queue.purge_old_messages(
            project_id=self.project_id,
            older_than_days=7,
            db_session=mock_session
        )

        assert result["status"] == "success"
        assert result["purged_count"] == 5
        mock_session.commit.assert_called_once()