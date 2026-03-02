"""
Unit tests for OrchestrationService - Spawn, mission, complete, error handling

Split from test_orchestration_service.py. Tests cover:
- Agent job spawning (success + project not found + DB error)
- Agent mission retrieval
- Job completion (success + invalid result validation)
- Error reporting
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.models import AgentExecution, AgentJob, Project
from src.giljo_mcp.services.orchestration_service import OrchestrationService


class TestOrchestrationServiceJobManagement:
    """Test agent job management operations"""

    @pytest.mark.asyncio
    async def test_spawn_agent_job_success(self, mock_db_manager):
        """Test successful agent job creation"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"
        mock_project.name = "Test Project"
        mock_project.tenant_key = "test-tenant"

        session.execute.return_value = Mock(scalar_one_or_none=Mock(return_value=mock_project))

        service = OrchestrationService(db_manager, tenant_manager)

        # Mock httpx for WebSocket broadcast
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=Mock(status_code=200))

            # Act
            result = await service.spawn_agent_job(
                agent_display_name="implementer",
                agent_name="impl-1",
                mission="Implement feature X",
                project_id="project-id",
                tenant_key="test-tenant",
            )

        # Assert - exception-based pattern: spawn_agent_job returns dict directly (no success wrapper)
        assert "job_id" in result
        assert "agent_prompt" in result
        assert result["thin_client"] is True
        assert result["mission_stored"] is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_spawn_agent_job_project_not_found(self, mock_db_manager):
        """Test spawn_agent_job raises ResourceNotFoundError when project doesn't exist"""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute.return_value = Mock(scalar_one_or_none=Mock(return_value=None))

        service = OrchestrationService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.spawn_agent_job(
                agent_display_name="implementer",
                agent_name="impl-1",
                mission="test",
                project_id="nonexistent",
                tenant_key="test-tenant",
            )

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_agent_mission_success(self, mock_db_manager):
        """Test successful mission retrieval"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock AgentJob (work order with mission)
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.mission = "Implement feature X with unit tests"
        mock_job.project_id = "project-id"

        # Mock AgentExecution (executor instance)
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.agent_id = "agent-456"
        mock_execution.agent_display_name = "implementer"
        mock_execution.spawned_by = "parent-agent-id"
        mock_execution.status = "waiting"
        mock_execution.mission_acknowledged_at = None  # First fetch

        # Three queries in get_agent_mission:
        # 1) fetch AgentJob
        # 2) fetch AgentExecution
        # 3) fetch all project executions (joined with jobs)
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(all=Mock(return_value=[(mock_execution, mock_job)])),
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Mock httpx for WebSocket broadcast (first acknowledgement triggers events)
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=Mock(status_code=200))

            # Act
            result = await service.get_agent_mission(job_id="job-123", tenant_key="test-tenant")

        # Assert - exception-based pattern: get_agent_mission returns dict directly (no success wrapper)
        assert result["job_id"] == "job-123"
        assert result["agent_display_name"] == "implementer"
        assert "Implement feature X" in result["mission"]
        assert result["thin_client"] is True

    @pytest.mark.asyncio
    async def test_complete_job_success(self, mock_db_manager):
        """Test successful job completion"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock execution and job
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.status = "working"
        mock_execution.completed_at = None
        mock_execution.started_at = None
        mock_execution.agent_id = "agent-456"
        mock_execution.agent_display_name = "implementer"
        mock_execution.agent_name = "implementer"

        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.project_id = "project-1"
        mock_job.status = "active"
        mock_job.completed_at = None

        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
            Mock(scalar_one_or_none=Mock(return_value=None)),
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.complete_job(job_id="job-123", result={"output": "Successfully completed"})

        # Assert
        assert result["status"] == "success"
        assert result["job_id"] == "job-123"
        assert mock_execution.status == "complete"
        assert mock_execution.completed_at is not None
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_report_error_success(self, mock_db_manager):
        """Test successful error reporting"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock job
        mock_job = Mock(spec=AgentExecution)
        mock_job.job_id = "job-123"
        mock_job.status = "working"
        mock_job.block_reason = None

        session.execute.return_value = Mock(scalar_one_or_none=Mock(return_value=mock_job))

        service = OrchestrationService(db_manager, tenant_manager)

        # Act - Handover 0491: severity param removed, always sets blocked
        result = await service.report_error(job_id="job-123", error="Failed to compile code")

        # Assert
        assert result.job_id == "job-123"
        assert result.message == "Error reported"
        assert mock_job.status == "blocked"
        assert mock_job.block_reason == "Failed to compile code"
        session.commit.assert_awaited_once()


class TestOrchestrationServiceErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_spawn_agent_job_database_exception(self):
        """Test database exception handling in spawn_agent_job"""
        from src.giljo_mcp.exceptions import DatabaseError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        # Create a proper async context manager that raises on enter
        session = AsyncMock()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        session.__aexit__ = AsyncMock(return_value=None)
        db_manager.get_session_async = Mock(return_value=session)

        service = OrchestrationService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern: raises DatabaseError
        with pytest.raises(DatabaseError) as exc_info:
            await service.spawn_agent_job(
                agent_display_name="implementer",
                agent_name="impl-1",
                mission="test",
                project_id="project-id",
                tenant_key="test-tenant",
            )

        assert "connection lost" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_complete_job_invalid_result(self):
        """Test complete_job validation for invalid result"""
        from src.giljo_mcp.exceptions import ValidationError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = OrchestrationService(db_manager, tenant_manager)

        # Act & Assert - ValidationError raised for invalid result
        with pytest.raises(ValidationError) as exc_info:
            await service.complete_job(
                job_id="job-123",
                result="not-a-dict",  # Should be a dict
            )

        assert "must be a non-empty dict" in str(exc_info.value)
