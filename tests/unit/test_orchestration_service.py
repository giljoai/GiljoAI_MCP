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

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.models import AgentExecution, AgentJob, ProductMemoryEntry, Project
from src.giljo_mcp.services.orchestration_service import OrchestrationService


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
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.acknowledge_job(job_id="job-123", agent_id="agent-456")

        # Assert - exception-based pattern: acknowledge_job returns {"job": {...}, "next_instructions": ...}
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

        # Mock already-acknowledged AgentExecution (already in 'working' status)
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.agent_id = "agent-456"
        mock_execution.agent_display_name = "implementer"
        mock_execution.agent_name = "implementer"
        mock_execution.status = "working"  # Already working
        mock_execution.started_at = datetime.now()
        mock_execution.mission_acknowledged_at = datetime.now()

        # Mock AgentJob (contains mission)
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.mission = "Test mission"
        mock_job.project_id = None  # No project -> skip implementation gate check

        # Two queries: 1) fetch AgentExecution, 2) fetch AgentJob
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.acknowledge_job(job_id="job-123", agent_id="agent-456")

        # Assert - exception-based pattern: returns {"job": {...}, "next_instructions": ...}
        # For idempotent call (already working), returns current state without committing
        assert result["job"]["job_id"] == "job-123"
        assert result["job"]["status"] == "working"
        # Should not commit again (idempotent)
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
        mock_job.failure_reason = None
        mock_job.block_reason = None

        session.execute.return_value = Mock(scalar_one_or_none=Mock(return_value=mock_job))

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.report_error(job_id="job-123", error="Failed to compile code")

        # Assert
        assert result["job_id"] == "job-123"
        assert result["message"] == "Error reported"
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
        mock_result.all = Mock(
            return_value=[(mock_execution1, mock_job), (mock_execution2, mock_job), (mock_execution3, mock_job)]
        )

        # Multiple queries: project lookup, then jobs lookup (joined)
        session.execute.side_effect = [Mock(scalar_one_or_none=Mock(return_value=mock_project)), mock_result]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.get_workflow_status(project_id="project-id", tenant_key="test-tenant")

        # Assert - WorkflowStatus is a Pydantic model, use attribute access
        assert result.total_agents == 3
        assert result.active_agents == 1
        assert result.completed_agents == 1
        assert result.pending_agents == 1
        assert result.failed_agents == 0
        assert result.blocked_agents == 0
        assert result.cancelled_agents == 0
        assert result.progress_percent == 33.33
        assert result.current_stage == "In Progress"

    @pytest.mark.asyncio
    async def test_get_workflow_status_project_not_found(self, mock_db_manager):
        """Test workflow status fails when project doesn't exist"""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        session.execute.return_value = Mock(scalar_one_or_none=Mock(return_value=None))

        service = OrchestrationService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern: raises ResourceNotFoundError
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.get_workflow_status(project_id="nonexistent", tenant_key="test-tenant")

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_workflow_status_blocked_agents_counted(self, mock_db_manager):
        """Test that blocked agents are counted in workflow status.

        Verifies that executions with status 'blocked' are tracked in the
        blocked_agents field and reflected in the current_stage message.
        """
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"

        # Mock executions: 1 working, 1 blocked, 1 complete
        mock_exec_working = Mock(spec=AgentExecution)
        mock_exec_working.status = "working"

        mock_exec_blocked = Mock(spec=AgentExecution)
        mock_exec_blocked.status = "blocked"

        mock_exec_complete = Mock(spec=AgentExecution)
        mock_exec_complete.status = "complete"

        mock_job = Mock(spec=AgentJob)

        # Create mock result with (execution, job) tuples
        mock_result = Mock()
        mock_result.all = Mock(
            return_value=[
                (mock_exec_working, mock_job),
                (mock_exec_blocked, mock_job),
                (mock_exec_complete, mock_job),
            ]
        )

        # Two queries: project lookup, then executions lookup
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            mock_result,
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.get_workflow_status(
            project_id="project-id", tenant_key="test-tenant"
        )

        # Assert
        assert result.blocked_agents == 1
        assert result.active_agents == 1
        assert result.completed_agents == 1
        assert result.total_agents == 3
        assert result.failed_agents == 0
        assert result.cancelled_agents == 0
        assert "blocked" in result.current_stage.lower()

    @pytest.mark.asyncio
    async def test_get_workflow_status_cancelled_agents_counted(self, mock_db_manager):
        """Test that cancelled/decommissioned agents are counted in workflow status.

        Verifies that executions with status 'cancelled' or 'decommissioned'
        are tracked in the cancelled_agents field.
        """
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"

        # Mock executions: 2 complete, 1 cancelled
        mock_exec_complete1 = Mock(spec=AgentExecution)
        mock_exec_complete1.status = "complete"

        mock_exec_complete2 = Mock(spec=AgentExecution)
        mock_exec_complete2.status = "complete"

        mock_exec_cancelled = Mock(spec=AgentExecution)
        mock_exec_cancelled.status = "cancelled"

        mock_job = Mock(spec=AgentJob)

        # Create mock result with (execution, job) tuples
        mock_result = Mock()
        mock_result.all = Mock(
            return_value=[
                (mock_exec_complete1, mock_job),
                (mock_exec_complete2, mock_job),
                (mock_exec_cancelled, mock_job),
            ]
        )

        # Two queries: project lookup, then executions lookup
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            mock_result,
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.get_workflow_status(
            project_id="project-id", tenant_key="test-tenant"
        )

        # Assert
        assert result.cancelled_agents == 1
        assert result.completed_agents == 2
        assert result.total_agents == 3
        assert result.blocked_agents == 0
        assert result.failed_agents == 0
        # Progress excludes cancelled from denominator: 2 completed / 2 actionable = 100%
        assert result.progress_percent == 100.0
        # Stage should be Completed (cancelled agents don't block completion)
        assert result.current_stage == "Completed"

    @pytest.mark.asyncio
    async def test_get_workflow_status_exclude_job_id_filters_orchestrator(self, mock_db_manager):
        """Test that exclude_job_id filters the orchestrator's own job from results.

        When an orchestrator calls get_workflow_status with its own job_id as
        exclude_job_id, the result should not include the orchestrator itself,
        only the spawned agents.
        """
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"

        # Simulate what DB would return AFTER filtering out the orchestrator:
        # Only the 2 spawned agents remain (1 complete, 1 working)
        mock_exec_spawned_complete = Mock(spec=AgentExecution)
        mock_exec_spawned_complete.status = "complete"

        mock_exec_spawned_working = Mock(spec=AgentExecution)
        mock_exec_spawned_working.status = "working"

        mock_job_spawned = Mock(spec=AgentJob)

        # Mock result returns only spawned agents (orchestrator excluded by query)
        mock_result = Mock()
        mock_result.all = Mock(
            return_value=[
                (mock_exec_spawned_complete, mock_job_spawned),
                (mock_exec_spawned_working, mock_job_spawned),
            ]
        )

        # Two queries: project lookup, then executions lookup (with filter applied)
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            mock_result,
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act - exclude the orchestrator's own job
        result = await service.get_workflow_status(
            project_id="project-id",
            tenant_key="test-tenant",
            exclude_job_id="orchestrator-job-id",
        )

        # Assert - orchestrator excluded, only 2 spawned agents counted
        assert result.total_agents == 2
        assert result.active_agents == 1
        assert result.completed_agents == 1
        assert result.progress_percent == 50.0
        assert "excluded" in result.caller_note.lower()

        # Verify that session.execute was called twice (project + filtered query)
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_workflow_status_exclude_job_id_none_returns_all(self, mock_db_manager):
        """Test backward compatibility: exclude_job_id=None includes all agents.

        When exclude_job_id is not provided (defaults to None), all agents
        including orchestrators should be counted in the workflow status.
        """
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"

        # All 3 agents returned (orchestrator + 2 spawned)
        mock_exec_orch = Mock(spec=AgentExecution)
        mock_exec_orch.status = "working"

        mock_exec_spawned1 = Mock(spec=AgentExecution)
        mock_exec_spawned1.status = "complete"

        mock_exec_spawned2 = Mock(spec=AgentExecution)
        mock_exec_spawned2.status = "working"

        mock_job = Mock(spec=AgentJob)

        # Mock result includes all 3 agents (no filtering)
        mock_result = Mock()
        mock_result.all = Mock(
            return_value=[
                (mock_exec_orch, mock_job),
                (mock_exec_spawned1, mock_job),
                (mock_exec_spawned2, mock_job),
            ]
        )

        # Two queries: project lookup, then executions lookup (no filter)
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            mock_result,
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act - no exclude_job_id (backward compatible)
        result = await service.get_workflow_status(
            project_id="project-id", tenant_key="test-tenant"
        )

        # Assert - all 3 agents counted (including orchestrator)
        assert result.total_agents == 3
        assert result.active_agents == 2
        assert result.completed_agents == 1
        assert result.current_stage == "In Progress"
        assert "included" in result.caller_note.lower()

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
        mock_result.all = Mock(return_value=[(mock_execution1, mock_job1), (mock_execution2, mock_job2)])

        session.execute.return_value = mock_result

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.get_pending_jobs(agent_display_name="implementer", tenant_key="test-tenant")

        # Assert - exception-based pattern: get_pending_jobs returns {"jobs": [...], "count": N}
        assert "jobs" in result
        assert result["count"] == 2
        assert len(result["jobs"]) == 2
        assert result["jobs"][0]["job_id"] == "job-1"
        assert result["jobs"][1]["job_id"] == "job-2"

    @pytest.mark.asyncio
    async def test_get_pending_jobs_empty_tenant_key(self):
        """Test get_pending_jobs validation for empty tenant_key"""
        from src.giljo_mcp.exceptions import ValidationError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        service = OrchestrationService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern: raises ValidationError for empty tenant_key
        with pytest.raises(ValidationError) as exc_info:
            await service.get_pending_jobs(agent_display_name="implementer", tenant_key="")

        assert "cannot be empty" in str(exc_info.value).lower()


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
    async def test_acknowledge_job_no_tenant_context(self):
        """Test acknowledge_job raises ValidationError without tenant context"""
        from src.giljo_mcp.exceptions import ValidationError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()

        tenant_manager.get_current_tenant = Mock(return_value=None)

        service = OrchestrationService(db_manager, tenant_manager)

        # Act & Assert - exception-based pattern: raises ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await service.acknowledge_job(job_id="job-123", agent_id="agent-456")

        assert "No tenant context" in str(exc_info.value)

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
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),  # No todo items
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.report_progress(
            job_id="job-123",
            progress={"percent": 50, "message": "Half done"},  # No todo_items!
            tenant_key="test-tenant",
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
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[mock_todo_item])))),
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.report_progress(
            job_id="job-123",
            progress={"mode": "todo", "todo_items": [{"content": "Task 1", "status": "completed"}]},
            tenant_key="test-tenant",
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
            if call_count % 3 == 2:
                return Mock(scalar_one_or_none=Mock(return_value=mock_job))
            # call_count % 3 == 0
            return Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[]))))

        session.execute.side_effect = execute_side_effect

        # Act - First call: warning sent
        result1 = await service.report_progress(
            job_id="job-123",
            progress={"percent": 25},  # Non-empty dict, but no todo_items
            tenant_key="test-tenant",
        )

        # Assert - First call has warning
        assert result1["status"] == "success"
        assert len(result1.get("warnings", [])) == 1

        # Act - Second call immediately: warning throttled
        result2 = await service.report_progress(
            job_id="job-123",
            progress={"percent": 50},  # Non-empty dict, but no todo_items
            tenant_key="test-tenant",
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
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),  # No todo items
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.report_progress(
            job_id="job-123",
            progress={"todo_items": []},  # Empty list!
            tenant_key="test-tenant",
        )

        # Assert
        assert result["status"] == "success"
        assert "warnings" in result
        assert len(result["warnings"]) == 1
        assert "todo_items missing" in result["warnings"][0]

    @pytest.mark.asyncio
    async def test_report_progress_top_level_todo_items(self, mock_db_manager, monkeypatch):
        """report_progress() accepts top-level todo_items parameter (Handover 0392)."""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Patch flag_modified to avoid SQLAlchemy mock issues
        monkeypatch.setattr("sqlalchemy.orm.attributes.flag_modified", Mock())

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

        # Mock job with SQLAlchemy state for flag_modified() support
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.job_metadata = {}
        mock_job._sa_instance_state = Mock()  # Required for flag_modified()

        # Mock todo_items
        mock_todo_item1 = Mock()
        mock_todo_item1.content = "Task A"
        mock_todo_item1.status = "completed"
        mock_todo_item2 = Mock()
        mock_todo_item2.content = "Task B"
        mock_todo_item2.status = "in_progress"
        mock_todo_item3 = Mock()
        mock_todo_item3.content = "Task C"
        mock_todo_item3.status = "pending"

        # Setup side_effect for multiple execute calls
        # Call 1: Get execution, Call 2: Get job, Call 3: Delete todo_items, Call 4: Get todo_items
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
            AsyncMock(),  # Delete todo_items
            Mock(
                scalars=Mock(
                    return_value=Mock(all=Mock(return_value=[mock_todo_item1, mock_todo_item2, mock_todo_item3]))
                )
            ),
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act - Use top-level todo_items parameter (simplified format)
        result = await service.report_progress(
            job_id="job-123",
            tenant_key="test-tenant",
            todo_items=[
                {"content": "Task A", "status": "completed"},
                {"content": "Task B", "status": "in_progress"},
                {"content": "Task C", "status": "pending"},
            ],
        )

        # Assert
        assert result["status"] == "success"
        assert "warnings" in result
        assert len(result["warnings"]) == 0  # No warnings when todo_items present

        # Verify progress was calculated correctly from todo_items
        # 1 completed out of 3 total = 33.33% progress
        assert mock_execution.progress == 33  # Should be set to calculated percentage
        assert mock_execution.current_task == "Task B"  # Should be set to in_progress item


class TestOrchestrationService360MemoryWarnings:
    """Test complete_job() 360 memory warning system (Handover 0710)"""

    @pytest.mark.asyncio
    async def test_complete_job_warns_orchestrator_missing_360_memory(self, mock_db_manager):
        """complete_job() returns warning when orchestrator hasn't written 360 memory."""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock execution (orchestrator)
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.status = "working"
        mock_execution.completed_at = None
        mock_execution.started_at = None
        mock_execution.agent_id = "agent-456"
        mock_execution.agent_display_name = "orchestrator"  # Orchestrator!
        mock_execution.agent_name = "orchestrator-coordinator"

        # Mock job
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.project_id = "project-1"
        mock_job.status = "active"
        mock_job.completed_at = None

        # Mock project (non-staging, with product)
        mock_project = Mock(spec=Project)
        mock_project.project_id = "project-1"
        mock_project.product_id = "product-1"
        mock_project.staging_status = None  # Not staging

        # Execute call sequence:
        # 1. Get execution
        # 2. Get job
        # 3. Get unread messages (empty)
        # 4. Get incomplete todos (empty)
        # 5. Check other active executions (none)
        # 6. Get project (for staging check)
        # 7. Get 360 memory (none exists)
        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),  # unread messages
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),  # incomplete todos
            Mock(scalar_one_or_none=Mock(return_value=None)),  # other active executions
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),  # project
            Mock(scalar_one_or_none=Mock(return_value=None)),  # No 360 memory!
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.complete_job(job_id="job-123", result={"output": "Successfully completed"})

        # Assert
        assert result["status"] == "success"
        assert result["job_id"] == "job-123"
        assert "warnings" in result
        assert len(result["warnings"]) == 1
        assert "360 Memory" in result["warnings"][0]
        assert "write_360_memory()" in result["warnings"][0]

    @pytest.mark.asyncio
    async def test_complete_job_no_warning_with_360_memory(self, mock_db_manager):
        """complete_job() has no warning when 360 memory entry exists."""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock execution (orchestrator)
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.status = "working"
        mock_execution.completed_at = None
        mock_execution.started_at = None
        mock_execution.agent_id = "agent-456"
        mock_execution.agent_display_name = "orchestrator"
        mock_execution.agent_name = "orchestrator-coordinator"

        # Mock job
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.project_id = "project-1"
        mock_job.status = "active"
        mock_job.completed_at = None

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.project_id = "project-1"
        mock_project.product_id = "product-1"
        mock_project.staging_status = None

        # Mock 360 memory entry (exists!)
        mock_memory = Mock(spec=ProductMemoryEntry)
        mock_memory.id = "memory-1"

        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
            Mock(scalar_one_or_none=Mock(return_value=None)),
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            Mock(scalar_one_or_none=Mock(return_value=mock_memory)),  # 360 memory exists!
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.complete_job(job_id="job-123", result={"output": "Successfully completed"})

        # Assert
        assert result["status"] == "success"
        assert result["warnings"] == []  # No warnings

    @pytest.mark.asyncio
    async def test_complete_job_no_warning_non_orchestrator(self, mock_db_manager):
        """complete_job() doesn't warn non-orchestrator agents about 360 memory."""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock execution (NOT orchestrator)
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.status = "working"
        mock_execution.completed_at = None
        mock_execution.started_at = None
        mock_execution.agent_id = "agent-456"
        mock_execution.agent_display_name = "implementer"  # Not orchestrator!
        mock_execution.agent_name = "implementer"

        # Mock job
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
        assert result["warnings"] == []  # No warnings for non-orchestrator

    @pytest.mark.asyncio
    async def test_complete_job_no_warning_staging_orchestrator(self, mock_db_manager):
        """complete_job() doesn't warn staging orchestrators about 360 memory."""
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="test-tenant")

        # Mock execution (orchestrator)
        mock_execution = Mock(spec=AgentExecution)
        mock_execution.job_id = "job-123"
        mock_execution.status = "working"
        mock_execution.completed_at = None
        mock_execution.started_at = None
        mock_execution.agent_id = "agent-456"
        mock_execution.agent_display_name = "orchestrator"
        mock_execution.agent_name = "orchestrator-coordinator"

        # Mock job
        mock_job = Mock(spec=AgentJob)
        mock_job.job_id = "job-123"
        mock_job.project_id = "project-1"
        mock_job.status = "active"
        mock_job.completed_at = None

        # Mock project (STAGING - should skip warning)
        mock_project = Mock(spec=Project)
        mock_project.project_id = "project-1"
        mock_project.product_id = "product-1"
        mock_project.staging_status = "staging"  # Staging orchestrator!

        session.execute.side_effect = [
            Mock(scalar_one_or_none=Mock(return_value=mock_execution)),
            Mock(scalar_one_or_none=Mock(return_value=mock_job)),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
            Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))),
            Mock(scalar_one_or_none=Mock(return_value=None)),
            Mock(scalar_one_or_none=Mock(return_value=mock_project)),
            # Note: No 360 memory query because staging is skipped
        ]

        service = OrchestrationService(db_manager, tenant_manager)

        # Act
        result = await service.complete_job(job_id="job-123", result={"output": "Successfully completed"})

        # Assert
        assert result["status"] == "success"
        assert result["warnings"] == []  # No warnings for staging orchestrator
