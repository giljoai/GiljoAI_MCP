"""
Unit tests for OrchestrationService - Progress reporting and todo warnings

Split from test_orchestration_service.py. Tests cover:
- report_progress() warning system (Handover 0406)
- Missing todo_items warnings
- Empty todo_items warnings
- Warning throttling
- Top-level todo_items parameter (Handover 0392)
"""

from unittest.mock import AsyncMock, Mock

import pytest

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.models import AgentExecution, AgentJob
from src.giljo_mcp.services.orchestration_service import OrchestrationService


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
