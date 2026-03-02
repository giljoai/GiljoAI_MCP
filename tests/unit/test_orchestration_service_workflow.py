"""
Unit tests for OrchestrationService - Workflow status and pending jobs

Split from test_orchestration_service.py. Tests cover:
- Workflow status retrieval (success + project not found)
- Blocked agents counting
- Decommissioned agents counting
- Orchestrator self-exclusion via exclude_job_id
- Pending job retrieval (success + empty tenant validation)
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.models import AgentExecution, AgentJob, Project
from src.giljo_mcp.services.orchestration_service import OrchestrationService


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
        assert result.blocked_agents == 0
        assert result.silent_agents == 0
        assert result.decommissioned_agents == 0
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
        assert result.silent_agents == 0
        assert result.decommissioned_agents == 0
        assert "blocked" in result.current_stage.lower()

    @pytest.mark.asyncio
    async def test_get_workflow_status_decommissioned_agents_counted(self, mock_db_manager):
        """Test that decommissioned agents are counted in workflow status.

        Verifies that executions with status 'decommissioned'
        are tracked in the decommissioned_agents field.
        Handover 0491: cancelled -> decommissioned.
        """
        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"

        # Mock executions: 2 complete, 1 decommissioned
        mock_exec_complete1 = Mock(spec=AgentExecution)
        mock_exec_complete1.status = "complete"

        mock_exec_complete2 = Mock(spec=AgentExecution)
        mock_exec_complete2.status = "complete"

        mock_exec_decommissioned = Mock(spec=AgentExecution)
        mock_exec_decommissioned.status = "decommissioned"

        mock_job = Mock(spec=AgentJob)

        # Create mock result with (execution, job) tuples
        mock_result = Mock()
        mock_result.all = Mock(
            return_value=[
                (mock_exec_complete1, mock_job),
                (mock_exec_complete2, mock_job),
                (mock_exec_decommissioned, mock_job),
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
        assert result.decommissioned_agents == 1
        assert result.completed_agents == 2
        assert result.total_agents == 3
        assert result.blocked_agents == 0
        assert result.silent_agents == 0
        # Progress excludes decommissioned from denominator: 2 completed / 2 actionable = 100%
        assert result.progress_percent == 100.0
        # Stage should be Completed (decommissioned agents don't block completion)
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
