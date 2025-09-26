"""
Comprehensive tests for message.py tools
Target: 4.26% → 95%+ coverage

Tests all message tool functions:
- register_message_tools
- send_message
- get_messages
- acknowledge_message
- complete_message
- broadcast
- log_task
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio

from src.giljo_mcp.models import Message
from src.giljo_mcp.tools.message import register_message_tools
from tests.utils.tools_helpers import (
    AssertionHelpers,
    MockMCPToolRegistrar,
    ToolsTestHelper,
)


class TestMessageTools:
    """Test class for message tools"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup, mock_message_queue):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]
        self.mock_server = tools_test_setup["mcp_server"]
        self.mock_queue = mock_message_queue

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Message Test Project")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

            # Create test agents
            self.agent1 = await ToolsTestHelper.create_test_agent(session, self.project.id, "agent1")
            self.agent2 = await ToolsTestHelper.create_test_agent(session, self.project.id, "agent2")
            self.orchestrator = await ToolsTestHelper.create_test_agent(session, self.project.id, "orchestrator")

    @pytest.mark.asyncio
    async def test_register_message_tools(self):
        """Test that all message tools are registered properly"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Register tools
        register_message_tools(mock_server, self.db_manager, self.tenant_manager)

        # Verify all expected tools are registered
        expected_tools = [
            "send_message",
            "get_messages",
            "acknowledge_message",
            "complete_message",
            "broadcast",
            "log_task",
        ]

        registered_tools = registrar.get_all_tools()
        for tool in expected_tools:
            AssertionHelpers.assert_tool_registered(registrar, tool)

        assert len(registered_tools) >= len(expected_tools)

    # send_message tests
    @pytest.mark.asyncio
    async def test_send_message_single_recipient(self):
        """Test sending message to single agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        send_message = registrar.get_registered_tool("send_message")

        result = await send_message(
            to_agents=["agent1"],
            content="Test message content",
            project_id=self.project.id,
            message_type="direct",
            priority="normal",
        )

        AssertionHelpers.assert_success_response(result, ["message_id", "to_agents", "delivery"])
        assert result["to_agents"] == ["agent1"]
        assert result["delivery"]["successful"] == 1
        assert result["delivery"]["failed"] == 0

    @pytest.mark.asyncio
    async def test_send_message_multiple_recipients(self):
        """Test sending message to multiple agents"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        send_message = registrar.get_registered_tool("send_message")

        result = await send_message(
            to_agents=["agent1", "agent2"],
            content="Broadcast test message",
            project_id=self.project.id,
            message_type="broadcast",
            priority="high",
        )

        AssertionHelpers.assert_success_response(result, ["message_id", "to_agents", "delivery"])
        assert len(result["to_agents"]) == 2
        assert result["delivery"]["successful"] == 2

    @pytest.mark.asyncio
    async def test_send_message_invalid_recipient(self):
        """Test sending message to non-existent agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        send_message = registrar.get_registered_tool("send_message")

        result = await send_message(to_agents=["nonexistent_agent"], content="Test message", project_id=self.project.id)

        AssertionHelpers.assert_success_response(result, ["delivery"])
        assert result["delivery"]["failed"] == 1
        assert len(result["delivery"]["errors"]) == 1

    @pytest.mark.asyncio
    async def test_send_message_mixed_valid_invalid(self):
        """Test sending message to mix of valid and invalid agents"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        send_message = registrar.get_registered_tool("send_message")

        result = await send_message(
            to_agents=["agent1", "nonexistent_agent", "agent2"],
            content="Mixed recipient test",
            project_id=self.project.id,
        )

        AssertionHelpers.assert_success_response(result, ["delivery"])
        assert result["delivery"]["successful"] == 2
        assert result["delivery"]["failed"] == 1

    @pytest.mark.asyncio
    async def test_send_message_no_active_project(self):
        """Test sending message with no active project"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        self.tenant_manager.clear_current_tenant()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        send_message = registrar.get_registered_tool("send_message")

        result = await send_message(to_agents=["agent1"], content="Test message", project_id=self.project.id)

        AssertionHelpers.assert_error_response(result, "No active project")

    # get_messages tests
    @pytest.mark.asyncio
    async def test_get_messages_success(self):
        """Test getting messages for an agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test messages
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_message(session, self.project.id, "orchestrator", "agent1", "Message 1")
            await ToolsTestHelper.create_test_message(session, self.project.id, "orchestrator", "agent1", "Message 2")

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        get_messages = registrar.get_registered_tool("get_messages")

        result = await get_messages(agent_name="agent1")

        AssertionHelpers.assert_success_response(result, ["agent", "count", "messages"])
        assert result["agent"] == "agent1"
        assert result["count"] == 2
        assert len(result["messages"]) == 2

    @pytest.mark.asyncio
    async def test_get_messages_with_status_filter(self):
        """Test getting messages with status filter"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create messages with different statuses
        async with self.db_manager.get_session_async() as session:
            pending_msg = Message(
                id=str(uuid.uuid4()),
                from_agent="orchestrator",
                to_agent="agent1",
                content="Pending message",
                type="direct",
                priority="normal",
                status="pending",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )

            acknowledged_msg = Message(
                id=str(uuid.uuid4()),
                from_agent="orchestrator",
                to_agent="agent1",
                content="Acknowledged message",
                type="direct",
                priority="normal",
                status="acknowledged",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )

            session.add_all([pending_msg, acknowledged_msg])
            await session.commit()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        get_messages = registrar.get_registered_tool("get_messages")

        # Get only pending messages
        result = await get_messages(agent_name="agent1", status="pending")
        AssertionHelpers.assert_success_response(result)
        assert result["count"] == 1
        assert result["messages"][0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_messages_with_pagination(self):
        """Test getting messages with pagination"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create multiple test messages
        async with self.db_manager.get_session_async() as session:
            for i in range(5):
                await ToolsTestHelper.create_test_message(
                    session, self.project.id, "orchestrator", "agent1", f"Message {i + 1}"
                )

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        get_messages = registrar.get_registered_tool("get_messages")

        result = await get_messages(agent_name="agent1", limit=2, offset=1)

        AssertionHelpers.assert_success_response(result)
        assert len(result["messages"]) == 2
        assert result["total"] == 5

    @pytest.mark.asyncio
    async def test_get_messages_agent_not_found(self):
        """Test getting messages for non-existent agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        get_messages = registrar.get_registered_tool("get_messages")

        result = await get_messages(agent_name="nonexistent_agent")

        AssertionHelpers.assert_error_response(result, "Agent not found")

    # acknowledge_message tests
    @pytest.mark.asyncio
    async def test_acknowledge_message_success(self):
        """Test successful message acknowledgment"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test message
        async with self.db_manager.get_session_async() as session:
            message = await ToolsTestHelper.create_test_message(
                session, self.project.id, "orchestrator", "agent1", "Test message"
            )

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        acknowledge_message = registrar.get_registered_tool("acknowledge_message")

        result = await acknowledge_message(message_id=message.id, agent_name="agent1")

        AssertionHelpers.assert_success_response(result, ["message_id", "status", "acknowledged_by"])
        assert result["message_id"] == message.id
        assert result["status"] == "acknowledged"
        assert result["acknowledged_by"] == "agent1"

    @pytest.mark.asyncio
    async def test_acknowledge_message_not_found(self):
        """Test acknowledging non-existent message"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        acknowledge_message = registrar.get_registered_tool("acknowledge_message")

        result = await acknowledge_message(message_id=str(uuid.uuid4()), agent_name="agent1")

        AssertionHelpers.assert_error_response(result, "Message not found")

    @pytest.mark.asyncio
    async def test_acknowledge_message_wrong_recipient(self):
        """Test acknowledging message by wrong agent"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create message for agent1
        async with self.db_manager.get_session_async() as session:
            message = await ToolsTestHelper.create_test_message(
                session, self.project.id, "orchestrator", "agent1", "Test message"
            )

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        acknowledge_message = registrar.get_registered_tool("acknowledge_message")

        # Try to acknowledge with agent2
        result = await acknowledge_message(message_id=message.id, agent_name="agent2")

        AssertionHelpers.assert_error_response(result, "not authorized")

    # complete_message tests
    @pytest.mark.asyncio
    async def test_complete_message_success(self):
        """Test successful message completion"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create and acknowledge message first
        async with self.db_manager.get_session_async() as session:
            message = Message(
                id=str(uuid.uuid4()),
                from_agent="orchestrator",
                to_agent="agent1",
                content="Task completion request",
                type="direct",
                priority="normal",
                status="acknowledged",  # Already acknowledged
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )
            session.add(message)
            await session.commit()
            await session.refresh(message)

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        complete_message = registrar.get_registered_tool("complete_message")

        result = await complete_message(
            message_id=message.id, agent_name="agent1", result="Task completed successfully"
        )

        AssertionHelpers.assert_success_response(result, ["message_id", "status", "completed_by"])
        assert result["status"] == "completed"
        assert result["result"] == "Task completed successfully"

    @pytest.mark.asyncio
    async def test_complete_message_not_acknowledged(self):
        """Test completing message that wasn't acknowledged"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create pending message (not acknowledged)
        async with self.db_manager.get_session_async() as session:
            message = await ToolsTestHelper.create_test_message(
                session, self.project.id, "orchestrator", "agent1", "Test message"
            )

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        complete_message = registrar.get_registered_tool("complete_message")

        result = await complete_message(message_id=message.id, agent_name="agent1", result="Attempted completion")

        AssertionHelpers.assert_error_response(result, "not acknowledged")

    # broadcast tests
    @pytest.mark.asyncio
    async def test_broadcast_success(self):
        """Test successful broadcast to all agents"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        broadcast = registrar.get_registered_tool("broadcast")

        result = await broadcast(
            content="Important announcement to all agents", project_id=self.project.id, priority="high"
        )

        AssertionHelpers.assert_success_response(result, ["message_id", "broadcast_to", "count"])
        assert result["count"] == 3  # agent1, agent2, orchestrator
        assert len(result["broadcast_to"]) == 3

    @pytest.mark.asyncio
    async def test_broadcast_no_agents(self):
        """Test broadcast when no agents exist"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create project with no agents
        async with self.db_manager.get_session_async() as session:
            empty_project = await ToolsTestHelper.create_test_project(session, "Empty Project")

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        broadcast = registrar.get_registered_tool("broadcast")

        result = await broadcast(content="Broadcast to empty project", project_id=empty_project.id)

        AssertionHelpers.assert_success_response(result)
        assert result["count"] == 0
        assert len(result["broadcast_to"]) == 0

    @pytest.mark.asyncio
    async def test_broadcast_invalid_project(self):
        """Test broadcast to non-existent project"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        broadcast = registrar.get_registered_tool("broadcast")

        result = await broadcast(content="Broadcast to invalid project", project_id=str(uuid.uuid4()))

        AssertionHelpers.assert_error_response(result, "Project not found")

    # log_task tests
    @pytest.mark.asyncio
    async def test_log_task_success(self):
        """Test successful task logging"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        log_task = registrar.get_registered_tool("log_task")

        result = await log_task(content="Implement new feature X", category="development", priority="high")

        AssertionHelpers.assert_success_response(result, ["task_id", "logged"])
        assert result["task"]["content"] == "Implement new feature X"
        assert result["task"]["category"] == "development"
        assert result["task"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_log_task_minimal_params(self):
        """Test task logging with minimal parameters"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        log_task = registrar.get_registered_tool("log_task")

        result = await log_task(content="Simple task")

        AssertionHelpers.assert_success_response(result, ["task_id"])
        assert result["task"]["content"] == "Simple task"
        assert result["task"]["priority"] == "medium"  # Default

    @pytest.mark.asyncio
    async def test_log_task_no_active_project(self):
        """Test task logging with no active project"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        self.tenant_manager.clear_current_tenant()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        log_task = registrar.get_registered_tool("log_task")

        result = await log_task(content="Task without project")

        AssertionHelpers.assert_error_response(result, "No active project")

    # Error handling and edge cases
    @pytest.mark.asyncio
    async def test_message_tools_database_error_handling(self):
        """Test that message tools handle database errors gracefully"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database to raise exception
        with patch.object(self.db_manager, "get_session_async") as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            register_message_tools(mock_server, self.db_manager, self.tenant_manager)
            get_messages = registrar.get_registered_tool("get_messages")

            result = await get_messages(agent_name="agent1")

        AssertionHelpers.assert_error_response(result, "Database connection failed")

    @pytest.mark.asyncio
    async def test_message_acknowledgment_arrays(self):
        """Test message acknowledgment arrays functionality"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create message sent to multiple agents
        async with self.db_manager.get_session_async() as session:
            message = Message(
                id=str(uuid.uuid4()),
                from_agent="orchestrator",
                to_agent="agent1,agent2",  # Multiple recipients
                content="Multi-recipient message",
                type="broadcast",
                priority="normal",
                status="pending",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                acknowledgment_array=[],  # Empty initially
                created_at=datetime.now(timezone.utc),
            )
            session.add(message)
            await session.commit()
            await session.refresh(message)

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        acknowledge_message = registrar.get_registered_tool("acknowledge_message")

        # First acknowledgment
        result1 = await acknowledge_message(message_id=message.id, agent_name="agent1")
        AssertionHelpers.assert_success_response(result1)

        # Second acknowledgment
        result2 = await acknowledge_message(message_id=message.id, agent_name="agent2")
        AssertionHelpers.assert_success_response(result2)

        # Verify acknowledgment array tracking
        async with self.db_manager.get_session_async() as session:
            updated_message = await session.get(Message, message.id)
            assert len(updated_message.acknowledgment_array) == 2
            assert "agent1" in updated_message.acknowledgment_array
            assert "agent2" in updated_message.acknowledgment_array

    @pytest.mark.asyncio
    async def test_message_priority_handling(self):
        """Test message priority handling and ordering"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create messages with different priorities
        async with self.db_manager.get_session_async() as session:
            low_msg = Message(
                id=str(uuid.uuid4()),
                from_agent="orchestrator",
                to_agent="agent1",
                content="Low priority message",
                type="direct",
                priority="low",
                status="pending",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )

            high_msg = Message(
                id=str(uuid.uuid4()),
                from_agent="orchestrator",
                to_agent="agent1",
                content="High priority message",
                type="direct",
                priority="high",
                status="pending",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )

            session.add_all([low_msg, high_msg])
            await session.commit()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        get_messages = registrar.get_registered_tool("get_messages")

        result = await get_messages(agent_name="agent1")

        AssertionHelpers.assert_success_response(result)
        # High priority should come first
        assert result["messages"][0]["priority"] == "high"
        assert result["messages"][1]["priority"] == "low"

    @pytest.mark.asyncio
    async def test_concurrent_message_operations(self):
        """Test concurrent message operations"""
        import asyncio

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        send_message = registrar.get_registered_tool("send_message")

        # Run multiple concurrent message sends
        tasks = [
            send_message(to_agents=["agent1"], content=f"Concurrent message {i}", project_id=self.project.id)
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)

        # All should succeed
        for result in results:
            AssertionHelpers.assert_success_response(result)

    @pytest.mark.asyncio
    async def test_message_lifecycle_complete_workflow(self):
        """Test complete message lifecycle workflow"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        send_message = registrar.get_registered_tool("send_message")
        get_messages = registrar.get_registered_tool("get_messages")
        acknowledge_message = registrar.get_registered_tool("acknowledge_message")
        complete_message = registrar.get_registered_tool("complete_message")

        # 1. Send message
        send_result = await send_message(
            to_agents=["agent1"], content="Lifecycle test message", project_id=self.project.id
        )
        AssertionHelpers.assert_success_response(send_result)
        message_id = send_result["message_id"]

        # 2. Get messages
        get_result = await get_messages(agent_name="agent1")
        AssertionHelpers.assert_success_response(get_result)
        assert get_result["count"] >= 1

        # 3. Acknowledge message
        ack_result = await acknowledge_message(message_id=message_id, agent_name="agent1")
        AssertionHelpers.assert_success_response(ack_result)

        # 4. Complete message
        complete_result = await complete_message(
            message_id=message_id, agent_name="agent1", result="Lifecycle test completed"
        )
        AssertionHelpers.assert_success_response(complete_result)

        # Verify final state
        assert complete_result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_message_queue_integration(self):
        """Test integration with message queue system"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_message_tools(mock_server, self.db_manager, self.tenant_manager)
        send_message = registrar.get_registered_tool("send_message")

        # Mock message queue is injected via fixture
        result = await send_message(to_agents=["agent1"], content="Queue integration test", project_id=self.project.id)

        AssertionHelpers.assert_success_response(result)
        # Message should be processed through the queue
        assert result["delivery"]["successful"] == 1
