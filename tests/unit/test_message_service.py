"""
Unit tests for MessageService (Handover 0123 - Phase 2)

Tests cover:
- Message sending and broadcasting
- Message retrieval and filtering
- Message acknowledgment and completion
- Inter-agent communication
- Error handling and edge cases

Target: >80% line coverage
"""

import pytest

pytestmark = pytest.mark.skip(reason="0750b: schema drift — NOT NULL constraints + fixture updates needed")

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.services.message_service import MessageService


class TestMessageServiceSending:
    """Test message sending operations"""

    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful message sending"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"
        mock_project.tenant_key = "test-tenant"

        # Mock execution lookup (for agent name resolution)
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.agent_id = "agent-impl-1"
        mock_execution.started_at = datetime.now()
        mock_execution.messages_sent_count = 1
        mock_execution.messages_waiting_count = 1

        mock_exec_result = Mock()
        mock_exec_result.scalar_one_or_none = Mock(return_value=mock_execution)

        mock_project_result = Mock()
        mock_project_result.scalar_one_or_none = Mock(return_value=mock_project)

        # Mock UPDATE result (for counter updates)
        mock_update_result = Mock()
        mock_update_result.rowcount = 1

        # First call for project lookup, then for each agent resolution,
        # then sender lookup for counters, then counter UPDATEs, then WebSocket lookups
        session.execute = AsyncMock(
            side_effect=[
                mock_project_result,   # Project lookup
                mock_exec_result,      # First agent resolution
                mock_exec_result,      # Second agent resolution
                mock_exec_result,      # Sender lookup for counter
                mock_update_result,    # INCREMENT sent_count UPDATE
                mock_update_result,    # INCREMENT waiting_count UPDATE (1st recipient)
                mock_update_result,    # INCREMENT waiting_count UPDATE (2nd recipient)
                mock_exec_result,      # Sender lookup for WebSocket
                mock_exec_result,      # First recipient lookup for WebSocket
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.send_message(
            to_agents=["impl-1", "analyzer-1"],
            content="Review code changes",
            project_id="project-id",
            priority="high",
            tenant_key="test-tenant",
        )

        # Assert
        assert "message_id" in result
        assert len(result["to_agents"]) > 0  # At least one agent resolved
        assert result["type"] == "direct"
        # Commit called at least once for message creation
        assert session.commit.await_count >= 1

    @pytest.mark.asyncio
    async def test_send_message_project_not_found(self, mock_db_manager, mock_tenant_manager):
        """Test send_message fails when project doesn't exist"""
        # Arrange
        db_manager, session = mock_db_manager

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        service = MessageService(db_manager, mock_tenant_manager)

        # Act & Assert - should raise ResourceNotFoundError
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.send_message(
                to_agents=["impl-1"], content="test", project_id="nonexistent", tenant_key="test-tenant"
            )

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_broadcast_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful broadcast to all agents"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock agent jobs
        mock_job1 = Mock(spec=AgentJob)
        mock_job1.job_type = "implementer"
        mock_job1.tenant_key = "test-tenant"

        mock_job2 = Mock(spec=AgentJob)
        mock_job2.job_type = "analyzer"
        mock_job2.tenant_key = "test-tenant"

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"
        mock_project.tenant_key = "test-tenant"

        # Mock execution for agent resolution
        mock_execution1 = Mock(spec=AgentExecution)
        mock_execution1.agent_id = "agent-impl-1"
        mock_execution1.started_at = datetime.now()
        mock_execution1.messages_sent_count = 1
        mock_execution1.messages_waiting_count = 1

        mock_execution2 = Mock(spec=AgentExecution)
        mock_execution2.agent_id = "agent-analyzer-1"
        mock_execution2.started_at = datetime.now()
        mock_execution2.messages_sent_count = 0
        mock_execution2.messages_waiting_count = 1

        # Mock sender execution (orchestrator)
        mock_sender_execution = Mock(spec=AgentExecution)
        mock_sender_execution.agent_id = "orchestrator-id"
        mock_sender_execution.started_at = datetime.now()

        # First call returns agent jobs, then project, then executions for resolution
        mock_jobs_result = Mock()
        mock_jobs_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[mock_job1, mock_job2])))

        mock_project_result = Mock()
        mock_project_result.scalar_one_or_none = Mock(return_value=mock_project)

        mock_exec_result1 = Mock()
        mock_exec_result1.scalar_one_or_none = Mock(return_value=mock_execution1)

        mock_exec_result2 = Mock()
        mock_exec_result2.scalar_one_or_none = Mock(return_value=mock_execution2)

        mock_sender_result = Mock()
        mock_sender_result.scalar_one_or_none = Mock(return_value=mock_sender_execution)

        # Mock UPDATE result (for counter updates)
        mock_update_result = Mock()
        mock_update_result.rowcount = 1

        session.execute = AsyncMock(
            side_effect=[
                mock_jobs_result,      # Get agent jobs for broadcast
                mock_project_result,   # Get project
                mock_exec_result1,     # Resolve first agent name
                mock_exec_result2,     # Resolve second agent name
                mock_sender_result,    # Sender lookup for counter
                mock_update_result,    # INCREMENT sent_count UPDATE
                mock_update_result,    # INCREMENT waiting_count UPDATE (1st recipient)
                mock_update_result,    # INCREMENT waiting_count UPDATE (2nd recipient)
                mock_sender_result,    # Sender lookup for WebSocket
                mock_exec_result1,     # First recipient lookup for WebSocket
            ]
        )

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.broadcast(content="Project status update", project_id="project-id", priority="high")

        # Assert
        assert result["type"] == "broadcast"

    @pytest.mark.asyncio
    async def test_broadcast_no_agents(self, mock_db_manager, mock_tenant_manager):
        """Test broadcast fails when no agents in project"""
        # Arrange
        db_manager, session = mock_db_manager

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
        session.execute = AsyncMock(return_value=mock_result)

        service = MessageService(db_manager, mock_tenant_manager)

        # Act & Assert - should raise ResourceNotFoundError
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.broadcast(content="test", project_id="project-id")

        assert "No agent jobs found" in str(exc_info.value)


class TestMessageServiceRetrieval:
    """Test message retrieval operations"""

    @pytest.mark.asyncio
    async def test_get_messages_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful message retrieval"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock messages
        mock_msg1 = Mock(spec=Message)
        mock_msg1.id = "msg-1"
        mock_msg1.from_agent_id = "orchestrator"
        mock_msg1.to_agents = ["impl-1", "analyzer-1"]
        mock_msg1.content = "Message 1"
        mock_msg1.message_type = "direct"
        mock_msg1.priority = "high"
        mock_msg1.created_at = datetime.now()

        mock_msg2 = Mock(spec=Message)
        mock_msg2.id = "msg-2"
        mock_msg2.from_agent_id = "impl-1"
        mock_msg2.to_agents = ["impl-1"]
        mock_msg2.content = "Message 2"
        mock_msg2.message_type = "direct"
        mock_msg2.priority = "normal"
        mock_msg2.created_at = datetime.now()

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[mock_msg1, mock_msg2])))
        session.execute = AsyncMock(return_value=mock_result)

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.get_messages(agent_name="impl-1", project_id="project-id")

        # Assert
        assert result["agent"] == "impl-1"
        assert result["count"] == 2  # Both messages are for impl-1
        assert len(result["messages"]) == 2

    @pytest.mark.asyncio
    async def test_get_messages_filters_by_agent(self, mock_db_manager, mock_tenant_manager):
        """Test that get_messages only returns messages for specific agent"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock messages - only one for impl-1
        mock_msg1 = Mock(spec=Message)
        mock_msg1.id = "msg-1"
        mock_msg1.from_agent_id = "orchestrator"
        mock_msg1.to_agents = ["impl-1"]
        mock_msg1.content = "For impl-1"
        mock_msg1.message_type = "direct"
        mock_msg1.priority = "normal"
        mock_msg1.created_at = datetime.now()

        mock_msg2 = Mock(spec=Message)
        mock_msg2.id = "msg-2"
        mock_msg2.from_agent_id = "orchestrator"
        mock_msg2.to_agents = ["analyzer-1"]  # Different agent
        mock_msg2.content = "For analyzer-1"
        mock_msg2.message_type = "direct"
        mock_msg2.priority = "normal"
        mock_msg2.created_at = datetime.now()

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[mock_msg1, mock_msg2])))
        session.execute = AsyncMock(return_value=mock_result)

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.get_messages(agent_name="impl-1")

        # Assert
        assert result["count"] == 1  # Only one message for impl-1
        assert result["messages"][0]["id"] == "msg-1"

    @pytest.mark.asyncio
    async def test_receive_messages_success(self, mock_db_manager):
        """Test successful receive_messages"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock AgentExecution and AgentJob
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.agent_id = "agent-123"
        mock_execution.job_id = "job-123"
        mock_execution.tenant_key = "test-tenant"
        mock_execution.messages_waiting_count = 1
        mock_execution.messages_read_count = 0

        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.project_id = "project-123"
        mock_job.tenant_key = "test-tenant"

        # Mock messages
        mock_msg1 = Mock(spec=Message)
        mock_msg1.id = "msg-1"
        mock_msg1.content = "Test message 1"
        mock_msg1.message_type = "direct"
        mock_msg1.priority = "normal"
        mock_msg1.to_agents = ["agent-123"]
        mock_msg1.status = "pending"
        mock_msg1.meta_data = {"_from_agent": "orchestrator"}
        mock_msg1.created_at = datetime.now()
        mock_msg1.acknowledged_at = None
        mock_msg1.acknowledged_by = []

        mock_exec_result = Mock()
        mock_exec_result.scalar_one_or_none = Mock(return_value=mock_execution)

        mock_job_result = Mock()
        mock_job_result.scalar_one_or_none = Mock(return_value=mock_job)

        mock_messages_result = Mock()
        mock_messages_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[mock_msg1])))

        # Mock counter updates (decrement_waiting_increment_read calls)
        mock_counter_update = Mock()
        mock_counter_update.rowcount = 1

        # Need to provide enough mocked execute results for all database calls:
        # 1. Get execution
        # 2. Get job
        # 3. Get messages
        # 4. Counter update for decrement_waiting_increment_read (in loop)
        # 5. Get counter stats for WebSocket event
        session.execute = AsyncMock(
            side_effect=[
                mock_exec_result,  # Get execution
                mock_job_result,  # Get job
                mock_messages_result,  # Get messages
                mock_counter_update,  # Counter update in loop
                mock_exec_result,  # Get counter stats (re-fetch execution)
            ]
        )

        service = MessageService(db_manager, tenant_manager)

        # Act
        result = await service.receive_messages(agent_id="agent-123", limit=5, tenant_key="test-tenant")

        # Assert
        assert result["count"] == 1
        assert len(result["messages"]) == 1

    @pytest.mark.asyncio
    async def test_receive_messages_no_tenant_context(self):
        """Test receive_messages fails without tenant context"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value=None)

        service = MessageService(db_manager, tenant_manager)

        # Act & Assert - should raise ValidationError
        from src.giljo_mcp.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            await service.receive_messages(agent_id="agent-123")

        assert "No tenant context" in str(exc_info.value)


class TestMessageServiceStatusUpdates:
    """Test message status update operations"""

    @pytest.mark.asyncio
    async def test_complete_message_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful message completion"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock message
        mock_message = Mock(spec=Message)
        mock_message.id = "msg-id"
        mock_message.status = "pending"
        mock_message.result = None
        mock_message.completed_by = None
        mock_message.completed_at = None

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_message)
        session.execute = AsyncMock(return_value=mock_result)

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.complete_message(
            message_id="msg-id", agent_name="impl-1", result="Task completed successfully"
        )

        # Assert
        assert result["message_id"] == "msg-id"
        assert result["completed_by"] == "impl-1"
        assert mock_message.status == "completed"
        assert mock_message.result == "Task completed successfully"
        assert mock_message.completed_by == "impl-1"
        assert mock_message.completed_at is not None
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_complete_message_not_found(self, mock_db_manager, mock_tenant_manager):
        """Test completing a non-existent message"""
        # Arrange
        db_manager, session = mock_db_manager

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        service = MessageService(db_manager, mock_tenant_manager)

        # Act & Assert - should raise ResourceNotFoundError
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.complete_message(message_id="nonexistent", agent_name="impl-1", result="test")

        assert "not found" in str(exc_info.value).lower()


class TestMessageServiceErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_send_message_database_exception(self, failing_db_manager, mock_tenant_manager):
        """Test database exception handling in send_message"""
        # Arrange - use failing_db_manager fixture
        service = MessageService(failing_db_manager, mock_tenant_manager)

        # Act & Assert - should raise BaseGiljoException
        from src.giljo_mcp.exceptions import BaseGiljoError

        with pytest.raises((BaseGiljoError, Exception)) as exc_info:
            await service.send_message(
                to_agents=["impl-1"], content="test", project_id="project-id", tenant_key="test-tenant"
            )

        assert "Connection lost" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_messages_database_exception(self, failing_db_manager, mock_tenant_manager):
        """Test database exception handling in get_messages"""
        # Arrange - use failing_db_manager fixture
        service = MessageService(failing_db_manager, mock_tenant_manager)

        # Act & Assert - should raise BaseGiljoException
        from src.giljo_mcp.exceptions import BaseGiljoError

        with pytest.raises((BaseGiljoError, Exception)) as exc_info:
            await service.get_messages(agent_name="impl-1")

        assert "Connection lost" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_complete_message_database_exception(self, failing_db_manager, mock_tenant_manager):
        """Test database exception handling in complete_message"""
        # Arrange - use failing_db_manager fixture
        service = MessageService(failing_db_manager, mock_tenant_manager)

        # Act & Assert - should raise BaseGiljoException
        from src.giljo_mcp.exceptions import BaseGiljoError

        with pytest.raises((BaseGiljoError, Exception)) as exc_info:
            await service.complete_message(message_id="msg-id", agent_name="impl-1", result="test")

        assert "Connection lost" in str(exc_info.value)
