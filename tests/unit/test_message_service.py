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
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from giljo_mcp.services.message_service import MessageService
from giljo_mcp.models import Message, Project
from giljo_mcp.models.agent_identity import AgentJob, AgentExecution


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

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_project)
        session.execute = AsyncMock(return_value=mock_result)

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.send_message(
            to_agents=["impl-1", "analyzer-1"],
            content="Review code changes",
            project_id="project-id",
            priority="high"
        )

        # Assert
        assert result["success"] is True
        assert "message_id" in result
        assert result["to_agents"] == ["impl-1", "analyzer-1"]
        assert result["type"] == "direct"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_message_project_not_found(self, mock_db_manager, mock_tenant_manager):
        """Test send_message fails when project doesn't exist"""
        # Arrange
        db_manager, session = mock_db_manager

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.send_message(
            to_agents=["impl-1"],
            content="test",
            project_id="nonexistent"
        )

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_broadcast_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful broadcast to all agents"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock agent jobs
        mock_job1 = Mock(spec=AgentExecution)
        mock_job1.agent_type = "implementer"

        mock_job2 = Mock(spec=AgentExecution)
        mock_job2.agent_type = "analyzer"

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"
        mock_project.tenant_key = "test-tenant"

        # First call returns agent jobs, second returns project
        mock_jobs_result = Mock()
        mock_jobs_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[mock_job1, mock_job2])))

        mock_project_result = Mock()
        mock_project_result.scalar_one_or_none = Mock(return_value=mock_project)

        session.execute = AsyncMock(side_effect=[mock_jobs_result, mock_project_result])

        service = MessageService(db_manager, mock_tenant_manager)

        # Act
        result = await service.broadcast(
            content="Project status update",
            project_id="project-id",
            priority="high"
        )

        # Assert
        assert result["success"] is True
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

        # Act
        result = await service.broadcast(
            content="test",
            project_id="project-id"
        )

        # Assert
        assert result["success"] is False
        assert "No agent jobs found" in result["error"]


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
        result = await service.get_messages(
            agent_name="impl-1",
            project_id="project-id"
        )

        # Assert
        assert result["success"] is True
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
        assert result["success"] is True
        assert result["count"] == 1  # Only one message for impl-1
        assert result["messages"][0]["id"] == "msg-1"

    @pytest.mark.asyncio
    async def test_receive_messages_success(self, mock_db_manager):
        """Test successful receive_messages via AgentMessageQueue"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock the AgentMessageQueue
        mock_queue_result = {
            "status": "success",
            "messages": [
                {"id": "msg-1", "content": "Test message 1"},
                {"id": "msg-2", "content": "Test message 2"}
            ]
        }

        with pytest.MonkeyPatch.context() as m:
            mock_queue = Mock()
            mock_queue.get_messages = AsyncMock(return_value=mock_queue_result)

            mock_queue_class = Mock(return_value=mock_queue)
            m.setattr("giljo_mcp.agent_message_queue.AgentMessageQueue", mock_queue_class)

            service = MessageService(db_manager, tenant_manager)

            # Act
            result = await service.receive_messages(
                agent_id="job-123",
                limit=5
            )

            # Assert
            assert result["success"] is True
            assert len(result["messages"]) == 2

    @pytest.mark.asyncio
    async def test_receive_messages_no_tenant_context(self):
        """Test receive_messages fails without tenant context"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value=None)

        service = MessageService(db_manager, tenant_manager)

        # Act
        result = await service.receive_messages(agent_id="job-123")

        # Assert
        assert result["success"] is False
        assert "No tenant context" in result["error"]


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
            message_id="msg-id",
            agent_name="impl-1",
            result="Task completed successfully"
        )

        # Assert
        assert result["success"] is True
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

        # Act
        result = await service.complete_message(
            message_id="nonexistent",
            agent_name="impl-1",
            result="test"
        )

        # Assert
        assert result["success"] is False
        assert "not found" in result["error"]


class TestMessageServiceErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_send_message_database_exception(self, failing_db_manager, mock_tenant_manager):
        """Test database exception handling in send_message"""
        # Arrange - use failing_db_manager fixture
        service = MessageService(failing_db_manager, mock_tenant_manager)

        # Act
        result = await service.send_message(
            to_agents=["impl-1"],
            content="test",
            project_id="project-id"
        )

        # Assert
        assert result["success"] is False
        assert "Connection lost" in result["error"]

    @pytest.mark.asyncio
    async def test_get_messages_database_exception(self, failing_db_manager, mock_tenant_manager):
        """Test database exception handling in get_messages"""
        # Arrange - use failing_db_manager fixture
        service = MessageService(failing_db_manager, mock_tenant_manager)

        # Act
        result = await service.get_messages(agent_name="impl-1")

        # Assert
        assert result["success"] is False
        assert "Connection lost" in result["error"]

    @pytest.mark.asyncio
    async def test_complete_message_database_exception(self, failing_db_manager, mock_tenant_manager):
        """Test database exception handling in complete_message"""
        # Arrange - use failing_db_manager fixture
        service = MessageService(failing_db_manager, mock_tenant_manager)

        # Act
        result = await service.complete_message(
            message_id="msg-id",
            agent_name="impl-1",
            result="test"
        )

        # Assert
        assert result["success"] is False
        assert "Connection lost" in result["error"]
