"""
Comprehensive tests for agent_messaging.py MCP tools
Target: 95%+ coverage

Tests send_mcp_message and read_mcp_messages tools:
- Message sending to orchestrator/broadcast/specific agents
- Message reading with filtering
- Multi-tenant isolation
- WebSocket event broadcasting
- Message status management
- Error handling
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from tests.utils.tools_helpers import ToolsTestHelper


class TestAgentMessagingTools:
    """Test class for agent messaging tools"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]

        # Create test project
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Agent Messaging Test Project")
            self.tenant_key = self.project.tenant_key

    async def _create_test_job(self, session, agent_name="test-agent", status="working"):
        """Helper to create test agent job"""
        job = AgentExecution(
            tenant_key=self.tenant_key,
            project_id=self.project.id,
            job_id=str(uuid.uuid4()),
            agent_type="implementer",
            mission="Test mission",
            status=status,
            agent_name=agent_name,
            tool_type="claude-code",
            messages=[],
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job

    # send_mcp_message tests

    @pytest.mark.asyncio
    async def test_send_mcp_message_to_orchestrator(self):
        """Test sending message to orchestrator"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session)
            job_id = job.job_id

        with patch("src.giljo_mcp.tools.agent_messaging.websocket_manager") as mock_ws:
            mock_ws.broadcast_job_message = AsyncMock()

            result = await send_mcp_message(
                job_id=job_id,
                tenant_key=self.tenant_key,
                content="Need guidance on architecture decision",
                target="orchestrator",
            )

        assert result["success"] is True
        assert "message_id" in result
        assert result["target"] == "orchestrator"
        assert "timestamp" in result

        # Verify message stored in database
        async with self.db_manager.get_session_async() as session:
            stmt = select(AgentExecution).where(AgentExecution.job_id == job_id)
            updated_job = (await session.execute(stmt)).scalar_one()
            assert len(updated_job.messages) == 1
            msg = updated_job.messages[0]
            assert msg["content"] == "Need guidance on architecture decision"
            assert msg["to_agent"] == "orchestrator"
            assert msg["type"] == "mcp_message"
            assert msg["status"] == "pending"

        # Verify WebSocket broadcast
        mock_ws.broadcast_job_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_mcp_message_broadcast(self):
        """Test broadcasting message to all agents"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        # Create multiple jobs
        async with self.db_manager.get_session_async() as session:
            job1 = await self._create_test_job(session, agent_name="agent1")
            job2 = await self._create_test_job(session, agent_name="agent2")
            job3 = await self._create_test_job(session, agent_name="agent3")
            sender_job_id = job1.job_id

        with patch("src.giljo_mcp.tools.agent_messaging.websocket_manager") as mock_ws:
            mock_ws.broadcast_job_message = AsyncMock()

            result = await send_mcp_message(
                job_id=sender_job_id,
                tenant_key=self.tenant_key,
                content="Important update for all agents",
                target="broadcast",
            )

        assert result["success"] is True
        assert result["target"] == "broadcast"
        assert result["broadcast_count"] == 3  # All 3 jobs should receive

        # Verify all jobs received message
        async with self.db_manager.get_session_async() as session:
            for job_id in [job1.job_id, job2.job_id, job3.job_id]:
                stmt = select(AgentExecution).where(AgentExecution.job_id == job_id)
                job = (await session.execute(stmt)).scalar_one()
                assert len(job.messages) >= 1
                # Find broadcast message
                broadcast_msg = next(m for m in job.messages if m.get("is_broadcast"))
                assert broadcast_msg["content"] == "Important update for all agents"

    @pytest.mark.asyncio
    async def test_send_mcp_message_to_specific_agent(self):
        """Test sending message to specific agent"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        async with self.db_manager.get_session_async() as session:
            sender = await self._create_test_job(session, agent_name="sender")
            target = await self._create_test_job(session, agent_name="target")
            sender_job_id = sender.job_id
            target_job_id = target.job_id

        with patch("src.giljo_mcp.tools.agent_messaging.websocket_manager") as mock_ws:
            mock_ws.broadcast_job_message = AsyncMock()

            result = await send_mcp_message(
                job_id=sender_job_id,
                tenant_key=self.tenant_key,
                content="Please review my implementation",
                target="agent",
                agent_id=target_job_id,
            )

        assert result["success"] is True
        assert result["target"] == "agent"

        # Verify only target received message
        async with self.db_manager.get_session_async() as session:
            stmt = select(AgentExecution).where(AgentExecution.job_id == target_job_id)
            target_job = (await session.execute(stmt)).scalar_one()
            assert len(target_job.messages) == 1
            assert target_job.messages[0]["content"] == "Please review my implementation"
            assert target_job.messages[0]["from_agent"] == sender_job_id

    @pytest.mark.asyncio
    async def test_send_mcp_message_agent_target_requires_agent_id(self):
        """Test that target='agent' requires agent_id parameter"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session)
            job_id = job.job_id

        with pytest.raises(ValueError, match="agent_id.*required.*target.*agent"):
            await send_mcp_message(
                job_id=job_id,
                tenant_key=self.tenant_key,
                content="Test message",
                target="agent",
                # Missing agent_id
            )

    @pytest.mark.asyncio
    async def test_send_mcp_message_content_length_validation(self):
        """Test message content cannot exceed 10000 characters"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session)
            job_id = job.job_id

        # Create message > 10000 chars
        long_content = "A" * 10001

        with pytest.raises(ValueError, match="content.*cannot exceed.*10000"):
            await send_mcp_message(
                job_id=job_id, tenant_key=self.tenant_key, content=long_content, target="orchestrator"
            )

    @pytest.mark.asyncio
    async def test_send_mcp_message_target_agent_not_found(self):
        """Test error when target agent doesn't exist"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session)
            job_id = job.job_id

        fake_agent_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="Target agent.*not found"):
            await send_mcp_message(
                job_id=job_id,
                tenant_key=self.tenant_key,
                content="Test message",
                target="agent",
                agent_id=fake_agent_id,
            )

    @pytest.mark.asyncio
    async def test_send_mcp_message_multi_tenant_isolation(self):
        """Test cannot send messages across tenant boundaries"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        # Create jobs in different tenants
        tenant_a = self.tenant_key

        async with self.db_manager.get_session_async() as session:
            # Job in tenant A
            job_a = await self._create_test_job(session)
            sender_id = job_a.job_id

            # Job in tenant B (different project/tenant)
            project_b = await ToolsTestHelper.create_test_project(session, "Project B")
            tenant_b = project_b.tenant_key

            job_b = AgentExecution(
                tenant_key=tenant_b,
                project_id=project_b.id,
                job_id=str(uuid.uuid4()),
                agent_type="implementer",
                mission="Test",
                status="working",
                agent_name="agent-b",
                messages=[],
            )
            session.add(job_b)
            await session.commit()
            target_id = job_b.job_id

        # Try to send from tenant A to tenant B
        with pytest.raises(ValueError, match="Target agent.*not found|different tenant"):
            await send_mcp_message(
                job_id=sender_id, tenant_key=tenant_a, content="Test message", target="agent", agent_id=target_id
            )

    @pytest.mark.asyncio
    async def test_send_mcp_message_invalid_target(self):
        """Test invalid target values are rejected"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session)
            job_id = job.job_id

        with pytest.raises(ValueError, match="target.*must be.*orchestrator.*broadcast.*agent"):
            await send_mcp_message(
                job_id=job_id, tenant_key=self.tenant_key, content="Test message", target="invalid_target"
            )

    # read_mcp_messages tests

    @pytest.mark.asyncio
    async def test_read_mcp_messages_unread_only(self):
        """Test reading only unread messages"""
        from src.giljo_mcp.tools.agent_messaging import read_mcp_messages, send_mcp_message

        async with self.db_manager.get_session_async() as session:
            sender = await self._create_test_job(session, agent_name="sender")
            reader = await self._create_test_job(session, agent_name="reader")
            reader_job_id = reader.job_id

        # Send messages to reader
        with patch("src.giljo_mcp.tools.agent_messaging.websocket_manager") as mock_ws:
            mock_ws.broadcast_job_message = AsyncMock()

            await send_mcp_message(
                job_id=sender.job_id,
                tenant_key=self.tenant_key,
                content="Message 1",
                target="agent",
                agent_id=reader_job_id,
            )
            await send_mcp_message(
                job_id=sender.job_id,
                tenant_key=self.tenant_key,
                content="Message 2",
                target="agent",
                agent_id=reader_job_id,
            )

        # Read unread messages
        result = await read_mcp_messages(
            job_id=reader_job_id,
            tenant_key=self.tenant_key,
            unread_only=True,
            mark_as_read=False,  # Don't mark as read yet
        )

        assert result["success"] is True
        assert result["unread_count"] == 2
        assert result["total_count"] == 2
        assert len(result["messages"]) == 2

    @pytest.mark.asyncio
    async def test_read_mcp_messages_mark_as_read(self):
        """Test marking messages as read"""
        from src.giljo_mcp.tools.agent_messaging import read_mcp_messages, send_mcp_message

        async with self.db_manager.get_session_async() as session:
            sender = await self._create_test_job(session, agent_name="sender")
            reader = await self._create_test_job(session, agent_name="reader")
            reader_job_id = reader.job_id

        # Send message
        with patch("src.giljo_mcp.tools.agent_messaging.websocket_manager") as mock_ws:
            mock_ws.broadcast_job_message = AsyncMock()

            await send_mcp_message(
                job_id=sender.job_id,
                tenant_key=self.tenant_key,
                content="Test message",
                target="agent",
                agent_id=reader_job_id,
            )

        # Read and mark as read
        result = await read_mcp_messages(
            job_id=reader_job_id, tenant_key=self.tenant_key, unread_only=True, mark_as_read=True
        )

        assert result["unread_count"] == 1
        assert len(result["messages"]) == 1

        # Read again - should be 0 unread
        result2 = await read_mcp_messages(
            job_id=reader_job_id, tenant_key=self.tenant_key, unread_only=True, mark_as_read=False
        )

        assert result2["unread_count"] == 0
        assert len(result2["messages"]) == 0

    @pytest.mark.asyncio
    async def test_read_mcp_messages_limit(self):
        """Test message limit parameter"""
        from src.giljo_mcp.tools.agent_messaging import read_mcp_messages, send_mcp_message

        async with self.db_manager.get_session_async() as session:
            sender = await self._create_test_job(session, agent_name="sender")
            reader = await self._create_test_job(session, agent_name="reader")
            reader_job_id = reader.job_id

        # Send 5 messages
        with patch("src.giljo_mcp.tools.agent_messaging.websocket_manager") as mock_ws:
            mock_ws.broadcast_job_message = AsyncMock()

            for i in range(5):
                await send_mcp_message(
                    job_id=sender.job_id,
                    tenant_key=self.tenant_key,
                    content=f"Message {i}",
                    target="agent",
                    agent_id=reader_job_id,
                )

        # Read with limit=3
        result = await read_mcp_messages(
            job_id=reader_job_id, tenant_key=self.tenant_key, unread_only=True, limit=3, mark_as_read=False
        )

        assert result["success"] is True
        assert len(result["messages"]) == 3
        assert result["total_count"] == 5
        assert result["unread_count"] == 5

    @pytest.mark.asyncio
    async def test_read_mcp_messages_limit_validation(self):
        """Test limit must be 1-100"""
        from src.giljo_mcp.tools.agent_messaging import read_mcp_messages

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session)
            job_id = job.job_id

        # Test limit > 100
        with pytest.raises(ValueError, match="limit.*must be.*1.*100"):
            await read_mcp_messages(job_id=job_id, tenant_key=self.tenant_key, limit=150)

        # Test limit < 1
        with pytest.raises(ValueError, match="limit.*must be.*1.*100"):
            await read_mcp_messages(job_id=job_id, tenant_key=self.tenant_key, limit=0)

    @pytest.mark.asyncio
    async def test_read_mcp_messages_all_messages(self):
        """Test reading all messages (not just unread)"""
        from src.giljo_mcp.tools.agent_messaging import read_mcp_messages, send_mcp_message

        async with self.db_manager.get_session_async() as session:
            sender = await self._create_test_job(session, agent_name="sender")
            reader = await self._create_test_job(session, agent_name="reader")
            reader_job_id = reader.job_id

        # Send messages and mark some as read
        with patch("src.giljo_mcp.tools.agent_messaging.websocket_manager") as mock_ws:
            mock_ws.broadcast_job_message = AsyncMock()

            await send_mcp_message(
                job_id=sender.job_id,
                tenant_key=self.tenant_key,
                content="Message 1",
                target="agent",
                agent_id=reader_job_id,
            )
            await send_mcp_message(
                job_id=sender.job_id,
                tenant_key=self.tenant_key,
                content="Message 2",
                target="agent",
                agent_id=reader_job_id,
            )

        # Mark first batch as read
        await read_mcp_messages(job_id=reader_job_id, tenant_key=self.tenant_key, unread_only=True, mark_as_read=True)

        # Send more messages
        with patch("src.giljo_mcp.tools.agent_messaging.websocket_manager") as mock_ws:
            mock_ws.broadcast_job_message = AsyncMock()

            await send_mcp_message(
                job_id=sender.job_id,
                tenant_key=self.tenant_key,
                content="Message 3",
                target="agent",
                agent_id=reader_job_id,
            )

        # Read all messages
        result = await read_mcp_messages(
            job_id=reader_job_id, tenant_key=self.tenant_key, unread_only=False, mark_as_read=False
        )

        assert result["total_count"] == 3
        assert result["unread_count"] == 1
        assert len(result["messages"]) == 3

    @pytest.mark.asyncio
    async def test_read_mcp_messages_job_not_found(self):
        """Test error when job doesn't exist"""
        from src.giljo_mcp.tools.agent_messaging import read_mcp_messages

        fake_job_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="Job.*not found"):
            await read_mcp_messages(job_id=fake_job_id, tenant_key=self.tenant_key)

    @pytest.mark.asyncio
    async def test_read_mcp_messages_multi_tenant_isolation(self):
        """Test cannot read messages from different tenant"""
        from src.giljo_mcp.tools.agent_messaging import read_mcp_messages

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session)
            job_id = job.job_id

        other_tenant = "other-tenant-" + str(uuid.uuid4())

        with pytest.raises(ValueError, match="Job.*not found"):
            await read_mcp_messages(job_id=job_id, tenant_key=other_tenant)

    @pytest.mark.asyncio
    async def test_read_mcp_messages_empty_queue(self):
        """Test reading from empty message queue"""
        from src.giljo_mcp.tools.agent_messaging import read_mcp_messages

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session)
            job_id = job.job_id

        result = await read_mcp_messages(job_id=job_id, tenant_key=self.tenant_key)

        assert result["success"] is True
        assert result["messages"] == []
        assert result["unread_count"] == 0
        assert result["total_count"] == 0

    @pytest.mark.asyncio
    async def test_send_mcp_message_websocket_event_structure(self):
        """Test WebSocket event has correct structure"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        async with self.db_manager.get_session_async() as session:
            sender = await self._create_test_job(session, agent_name="sender")
            target = await self._create_test_job(session, agent_name="target")
            sender_job_id = sender.job_id
            target_job_id = target.job_id

        with patch("src.giljo_mcp.tools.agent_messaging.websocket_manager") as mock_ws:
            mock_ws.broadcast_job_message = AsyncMock()

            await send_mcp_message(
                job_id=sender_job_id,
                tenant_key=self.tenant_key,
                content="Test message for WebSocket",
                target="agent",
                agent_id=target_job_id,
            )

            # Verify WebSocket was called with correct parameters
            call_args = mock_ws.broadcast_job_message.call_args
            assert call_args is not None
            kwargs = call_args.kwargs

            assert kwargs["job_id"] == sender_job_id
            assert kwargs["tenant_key"] == self.tenant_key
            assert kwargs["from_agent"] == sender_job_id
            assert kwargs["message_type"] == "mcp_message"

    @pytest.mark.asyncio
    async def test_send_mcp_message_empty_content(self):
        """Test validation for empty content"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        async with self.db_manager.get_session_async() as session:
            job = await self._create_test_job(session)
            job_id = job.job_id

        with pytest.raises(ValueError, match="content.*cannot be empty"):
            await send_mcp_message(job_id=job_id, tenant_key=self.tenant_key, content="", target="orchestrator")

    @pytest.mark.asyncio
    async def test_send_mcp_message_empty_job_id(self):
        """Test validation for empty job_id"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        with pytest.raises(ValueError, match="job_id.*cannot be empty"):
            await send_mcp_message(job_id="", tenant_key=self.tenant_key, content="Test", target="orchestrator")

    @pytest.mark.asyncio
    async def test_send_mcp_message_empty_tenant_key(self):
        """Test validation for empty tenant_key"""
        from src.giljo_mcp.tools.agent_messaging import send_mcp_message

        with pytest.raises(ValueError, match="tenant_key.*cannot be empty"):
            await send_mcp_message(job_id="some-job-id", tenant_key="", content="Test", target="orchestrator")

    @pytest.mark.asyncio
    async def test_read_mcp_messages_empty_job_id(self):
        """Test validation for empty job_id"""
        from src.giljo_mcp.tools.agent_messaging import read_mcp_messages

        with pytest.raises(ValueError, match="job_id.*cannot be empty"):
            await read_mcp_messages(job_id="", tenant_key=self.tenant_key)

    @pytest.mark.asyncio
    async def test_read_mcp_messages_empty_tenant_key(self):
        """Test validation for empty tenant_key"""
        from src.giljo_mcp.tools.agent_messaging import read_mcp_messages

        with pytest.raises(ValueError, match="tenant_key.*cannot be empty"):
            await read_mcp_messages(job_id="some-job-id", tenant_key="")
