"""
Unit tests for OrchestrationService (Handover 0123 - Phase 2)

Tests cover:
- Project orchestration
- Agent job lifecycle (spawn, acknowledge, complete, error)
- Job progress reporting
- Workflow status monitoring
- Pending job retrieval
- Error handling and edge cases

Target: >80% line coverage
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.models import AgentExecution, AgentJob, Project


@pytest.fixture
def mock_db_manager():
    """Reusable fixture for database manager mocking."""
    db_manager = Mock()
    session = AsyncMock()

    # Async context manager protocol
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)

    # Database operations
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()

    db_manager.get_session_async = Mock(return_value=session)

    return db_manager, session


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

        session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=mock_project)
        )

        service = OrchestrationService(db_manager, tenant_manager)

        # Mock httpx for WebSocket broadcast
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=Mock(status_code=200)
            )

            # Act
            result = await service.spawn_agent_job(
                agent_display_name="implementer",
                agent_name="impl-1",
                mission="Implement feature X",
                project_id="project-id",
                tenant_key="test-tenant"
            )

        # Assert
        assert result["success"] is True
        assert "job_id" in result
        assert "agent_prompt" in result
        assert result["thin_client"] is True
        assert result["mission_stored"] is True
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_spawn_agent_job_project_not_found(self, mock_db_manager):
        """Test spawn_agent_job fails when project doesn't exist"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None)
        )

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="test",
            project_id="nonexistent",
            tenant_key="test-tenant"
        )

        # Assert
        assert "error" in result
        assert "NOT_FOUND" in result["error"]

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
            Mock(all=Mock(return_value=[(mock_execution, mock_job)]))
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Mock httpx for WebSocket broadcast (first acknowledgement triggers events)
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=Mock(status_code=200)
            )

            # Act
            result = await service.get_agent_mission(
                job_id="job-123",
                tenant_key="test-tenant"
            )

        # Assert
        assert result["success"] is True
        assert result["job_id"] == "job-123"
        assert result["agent_display_name"] == "implementer"
        assert "Implement feature X" in result["mission"]
        assert result["thin_client"] is True

    @pytest.mark.asyncio
    async def test_acknowledge_job_success(self, mock_db_manager):
        """Test successful job acknowledgment"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock AgentExecution
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.agent_id = "agent-456"
        mock_execution.agent_display_name = "implementer"
        mock_execution.agent_name = "implementer"
        mock_execution.status = "waiting"
        mock_execution.started_at = None
        mock_execution.mission_acknowledged_at = None

        # Mock AgentJob (contains mission)
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.mission = "Test mission"

        # Two queries: 1) fetch AgentExecution, 2) fetch AgentJob
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(scalar_one_or_none=Mock(return_value=mock_job))
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.acknowledge_job(
            job_id="job-123",
            agent_id="agent-456"
        )

        # Assert
        assert result["status"] == "success"
        assert result["job"]["job_id"] == "job-123"
        assert result["job"]["mission"] == "Test mission"
        # acknowledge_job transitions waiting -> working
        assert mock_execution.status == "working"
        assert mock_execution.started_at is not None
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_acknowledge_job_idempotent(self, mock_db_manager):
        """Test that acknowledging an already-acknowledged job is idempotent"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock already-acknowledged job
        mock_job = Mock(spec=AgentExecution)
        mock_job.job_id = "job-123"
        mock_job.agent_display_name = "implementer"
        mock_job.mission = "Test mission"
        mock_job.acknowledged = True
        mock_job.status = "working"
        mock_job.started_at = datetime.now()

        session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=mock_job)
        )

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.acknowledge_job(
            job_id="job-123",
            agent_id="agent-456"
        )

        # Assert
        assert result["status"] == "success"
        # Should not commit again
        session.commit.assert_not_awaited()

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
        result = await service.complete_job(
            job_id="job-123",
            result={"output": "Successfully completed"}
        )

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
        mock_job.failure_reason = None
        mock_job.block_reason = None

        session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=mock_job)
        )

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.report_error(
            job_id="job-123",
            error="Failed to compile code"
        )

        # Assert
        assert result["status"] == "success"
        assert mock_job.status == "blocked"
        assert mock_job.failure_reason is None
        assert mock_job.block_reason == "Failed to compile code"
        session.commit.assert_awaited_once()


class TestOrchestrationServiceWorkflow:
    """Test workflow and orchestration operations"""

    @pytest.mark.asyncio
    async def test_get_workflow_status_success(self, mock_db_manager):
        """Test successful workflow status retrieval"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"

        # Mock executions with various statuses
        mock_execution1 = Mock(spec=AgentExecution)
        mock_execution1.status = "working"

        mock_execution2 = Mock(spec=AgentExecution)
        mock_execution2.status = "complete"

        mock_execution3 = Mock(spec=AgentExecution)
        mock_execution3.status = "waiting"

        # Mock jobs (needed for join)
        mock_job = Mock(spec=AgentJob)

        # Create mock result that returns rows (tuples of execution, job)
        mock_result = Mock()
        mock_result.all = Mock(return_value=[
            (mock_execution1, mock_job),
            (mock_execution2, mock_job),
            (mock_execution3, mock_job)
        ])

        # Multiple queries: project lookup, then jobs lookup (joined)
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            mock_result
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.get_workflow_status(
            project_id="project-id",
            tenant_key="test-tenant"
        )

        # Assert
        assert "active_agents" in result
        assert "completed_agents" in result
        assert "failed_agents" in result
        assert "pending_agents" in result
        assert "progress_percent" in result
        assert "current_stage" in result
        assert result["total_agents"] == 3
        assert result["active_agents"] == 1
        assert result["completed_agents"] == 1
        assert result["pending_agents"] == 1

    @pytest.mark.asyncio
    async def test_get_workflow_status_project_not_found(self, mock_db_manager):
        """Test workflow status fails when project doesn't exist"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute.return_value = Mock(
            scalar_one_or_none=Mock(return_value=None)
        )

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.get_workflow_status(
            project_id="nonexistent",
            tenant_key="test-tenant"
        )

        # Assert
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_get_pending_jobs_success(self, mock_db_manager):
        """Test successful pending jobs retrieval"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock AgentExecutions (waiting status)
        mock_execution1 = Mock(spec=AgentExecution)
        mock_execution1.agent_id = "agent-1"
        mock_execution1.agent_display_name = "implementer"

        mock_execution2 = Mock(spec=AgentExecution)
        mock_execution2.agent_id = "agent-2"
        mock_execution2.agent_display_name = "implementer"

        # Mock AgentJobs (contain missions)
        mock_job1 = Mock(spec=AgentJob)
        mock_job1.job_id = "job-1"
        mock_job1.mission = "Mission 1"
        mock_job1.created_at = datetime.now()

        mock_job2 = Mock(spec=AgentJob)
        mock_job2.job_id = "job-2"
        mock_job2.mission = "Mission 2"
        mock_job2.created_at = datetime.now()

        # Create mock result that returns rows (tuples of execution, job)
        mock_result = Mock()
        mock_result.all = Mock(return_value=[
            (mock_execution1, mock_job1),
            (mock_execution2, mock_job2)
        ])

        session.execute.return_value = mock_result

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.get_pending_jobs(
            agent_display_name="implementer",
            tenant_key="test-tenant"
        )

        # Assert
        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["jobs"]) == 2
        assert result["jobs"][0]["job_id"] == "job-1"
        assert result["jobs"][1]["job_id"] == "job-2"

    @pytest.mark.asyncio
    async def test_get_pending_jobs_empty_agent_display_name(self):
        """Test get_pending_jobs validation for empty agent_display_name"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.get_pending_jobs(
            agent_display_name="",
            tenant_key="test-tenant"
        )

        # Assert
        assert result["status"] == "error"
        assert "cannot be empty" in result["error"]


class TestOrchestrationServiceErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_spawn_agent_job_database_exception(self):
        """Test database exception handling in spawn_agent_job"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        db_manager.get_session_async = AsyncMock(
            side_effect=Exception("Connection lost")
        )

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="impl-1",
            mission="test",
            project_id="project-id",
            tenant_key="test-tenant"
        )

        # Assert
        assert "error" in result
        assert "INTERNAL_ERROR" in result["error"]

    @pytest.mark.asyncio
    async def test_acknowledge_job_no_tenant_context(self):
        """Test acknowledge_job fails without tenant context"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value=None)

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.acknowledge_job(
            job_id="job-123",
            agent_id="agent-456"
        )

        # Assert
        assert result["status"] == "error"
        assert "No tenant context" in result["error"]

    @pytest.mark.asyncio
    async def test_complete_job_invalid_result(self):
        """Test complete_job validation for invalid result"""
        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.complete_job(
            job_id="job-123",
            result="not-a-dict"  # Should be a dict
        )

        # Assert
        assert result["status"] == "error"
        assert "must be a non-empty dict" in result["error"]


class TestOrchestrationServiceTodoWarnings:
    """Test report_progress() warning system (Handover 0406)"""

    @pytest.mark.asyncio
    async def test_report_progress_warns_on_missing_todo_items(self, mock_db_manager):
        """report_progress() returns warning when todo_items missing."""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock execution
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.status = "working"
        mock_execution.agent_display_name = "implementer"
        mock_execution.agent_id = "agent-123"
        mock_execution.agent_name = "test-agent"
        mock_execution.progress = 0
        mock_execution.current_task = None
        mock_execution.last_progress_at = None

        # Mock job
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.job_metadata = {}

        # Setup side_effect for multiple execute calls
        # Call 1: Get execution, Call 2: Get job, Call 3: Get todo_items (empty)
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))  # No todo items
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.report_progress(
            job_id="job-123",
            progress={"percent": 50, "message": "Half done"},  # No todo_items!
            tenant_key="test-tenant"
        )

        # Assert
        assert result["status"] == "success"
        assert "warnings" in result
        assert len(result["warnings"]) == 1
        assert "todo_items missing" in result["warnings"][0]
        assert "Dashboard Steps shows '--'" in result["warnings"][0]

    @pytest.mark.asyncio
    async def test_report_progress_no_warning_with_todo_items(self, mock_db_manager):
        """report_progress() has no warning when todo_items present."""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock execution
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.status = "working"
        mock_execution.agent_display_name = "implementer"
        mock_execution.agent_id = "agent-123"
        mock_execution.agent_name = "test-agent"
        mock_execution.progress = 0
        mock_execution.current_task = None
        mock_execution.last_progress_at = None

        # Mock job
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.job_metadata = {}

        # Mock todo_item
        mock_todo_item = Mock()
        mock_todo_item.content = "Task 1"
        mock_todo_item.status = "completed"

        # Setup side_effect for multiple execute calls
        # Call 1: Get execution, Call 2: Get job, Call 3: Delete todo_items, Call 4: Get todo_items
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
            AsyncMock(),  # Delete todo_items
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[mock_todo_item]))))
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.report_progress(
            job_id="job-123",
            progress={
                "mode": "todo",
                "todo_items": [{"content": "Task 1", "status": "completed"}]
            },
            tenant_key="test-tenant"
        )

        # Assert
        assert result["status"] == "success"
        assert result.get("warnings", []) == []

    @pytest.mark.asyncio
    async def test_report_progress_warning_throttled(self, mock_db_manager):
        """Second warning within 5 min is suppressed."""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock execution
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.status = "working"
        mock_execution.agent_display_name = "implementer"
        mock_execution.agent_id = "agent-123"
        mock_execution.agent_name = "test-agent"
        mock_execution.progress = 0
        mock_execution.current_task = None
        mock_execution.last_progress_at = None

        # Mock job
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.job_metadata = {}

        service = OrchestrationService(db_manager, tenant_manager)

        # Setup execute mock to return appropriate values based on call count
        call_count = 0
        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Pattern: execution, job, todo_items query (repeats for each report_progress call)
            if call_count % 3 == 1:
                return Mock(scalar_one_or_none=Mock(return_value=mock_execution))
            elif call_count % 3 == 2:
                return Mock(scalar_one_or_none=Mock(return_value=mock_job))
            else:  # call_count % 3 == 0
                return Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))

        session.execute.side_effect = execute_side_effect

        # Act - First call: warning sent
        result1 = await service.report_progress(
            job_id="job-123",
            progress={"percent": 25},  # Non-empty dict, but no todo_items
            tenant_key="test-tenant"
        )

        # Assert - First call has warning
        assert result1["status"] == "success"
        assert len(result1.get("warnings", [])) == 1

        # Act - Second call immediately: warning throttled
        result2 = await service.report_progress(
            job_id="job-123",
            progress={"percent": 50},  # Non-empty dict, but no todo_items
            tenant_key="test-tenant"
        )

        # Assert - Second call has no warning (throttled)
        assert result2["status"] == "success"
        assert len(result2.get("warnings", [])) == 0

    @pytest.mark.asyncio
    async def test_report_progress_warning_empty_todo_items(self, mock_db_manager):
        """report_progress() warns when todo_items is empty list."""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock execution
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.status = "working"
        mock_execution.agent_display_name = "implementer"
        mock_execution.agent_id = "agent-123"
        mock_execution.agent_name = "test-agent"
        mock_execution.progress = 0
        mock_execution.current_task = None
        mock_execution.last_progress_at = None

        # Mock job
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.job_metadata = {}

        # Setup side_effect for multiple execute calls
        # Call 1: Get execution, Call 2: Get job, Call 3: Get todo_items (empty)
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))  # No todo items
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.report_progress(
            job_id="job-123",
            progress={"todo_items": []},  # Empty list!
            tenant_key="test-tenant"
        )

        # Assert
        assert result["status"] == "success"
        assert "warnings" in result
        assert len(result["warnings"]) == 1
        assert "todo_items missing" in result["warnings"][0]
