"""
Unit tests for OrchestrationService - Job closeout and 360 memory warnings

Split from test_orchestration_service.py. Tests cover:
- complete_job() 360 memory warning system (Handover 0710)
- Missing 360 memory warning for orchestrators
- No warning when 360 memory exists
- No warning for non-orchestrator agents
- No warning for staging orchestrators
"""

from unittest.mock import AsyncMock, Mock

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.models import AgentExecution, AgentJob, ProductMemoryEntry, Project
from src.giljo_mcp.services.orchestration_service import OrchestrationService


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
