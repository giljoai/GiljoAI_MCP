"""
Unit tests for TaskService — query and listing operations (Handover 0605)

Tests cover:
- Task listing and filtering
- Empty results handling
- Tenant context validation for queries
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

pytestmark = pytest.mark.skip(reason="0750b: schema drift — description field + fixture updates needed")

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.models import Project, Task
from src.giljo_mcp.services.task_service import TaskService


class TestTaskServiceRetrieval:
    """Test task retrieval operations"""

    @pytest.mark.asyncio
    async def test_list_tasks_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful task listing"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"
        mock_project.tenant_key = "test-tenant"

        # Mock tasks with ALL fields that list_tasks expects
        mock_task1 = Mock(spec=Task)
        mock_task1.id = "task-1"
        mock_task1.tenant_key = "test-tenant"
        mock_task1.product_id = None
        mock_task1.project_id = "project-id"
        mock_task1.parent_task_id = None
        mock_task1.job_id = None
        mock_task1.created_by_user_id = None
        mock_task1.converted_to_project_id = None
        mock_task1.title = "Task 1"
        mock_task1.description = "Description 1"
        mock_task1.category = "bug"
        mock_task1.status = "pending"
        mock_task1.priority = "high"
        mock_task1.created_at = datetime.now()
        mock_task1.started_at = None
        mock_task1.completed_at = None
        mock_task1.due_date = None
        mock_task1.estimated_effort = None
        mock_task1.actual_effort = None

        mock_task2 = Mock(spec=Task)
        mock_task2.id = "task-2"
        mock_task2.tenant_key = "test-tenant"
        mock_task2.product_id = None
        mock_task2.project_id = "project-id"
        mock_task2.parent_task_id = None
        mock_task2.job_id = None
        mock_task2.created_by_user_id = None
        mock_task2.converted_to_project_id = None
        mock_task2.title = "Task 2"
        mock_task2.description = "Description 2"
        mock_task2.category = "feature"
        mock_task2.status = "completed"
        mock_task2.priority = "medium"
        mock_task2.created_at = datetime.now()
        mock_task2.started_at = None
        mock_task2.completed_at = None
        mock_task2.due_date = None
        mock_task2.estimated_effort = None
        mock_task2.actual_effort = None

        # Setup mock result - only ONE execute call (no filter_type means no product lookup)
        session.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[mock_task1, mock_task2]))))
        )

        service = TaskService(db_manager, mock_tenant_manager)

        # Act
        result = await service.list_tasks()

        # Assert - exception-based pattern: list_tasks returns {"tasks": [], "count": N}
        assert "tasks" in result
        assert "count" in result
        assert len(result["tasks"]) == 2
        assert result["count"] == 2
        assert result["tasks"][0]["id"] == "task-1"
        assert result["tasks"][1]["id"] == "task-2"

    @pytest.mark.asyncio
    async def test_list_tasks_filtered_by_status(self, mock_db_manager, mock_tenant_manager):
        """Test task listing with status filter"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"

        # Mock only pending tasks with ALL fields
        mock_task = Mock(spec=Task)
        mock_task.id = "task-1"
        mock_task.tenant_key = "test-tenant"
        mock_task.product_id = None
        mock_task.project_id = "project-id"
        mock_task.parent_task_id = None
        mock_task.job_id = None
        mock_task.created_by_user_id = None
        mock_task.converted_to_project_id = None
        mock_task.title = "Pending Task"
        mock_task.description = "Description"
        mock_task.category = None
        mock_task.status = "pending"
        mock_task.priority = "medium"
        mock_task.created_at = datetime.now()
        mock_task.started_at = None
        mock_task.completed_at = None
        mock_task.due_date = None
        mock_task.estimated_effort = None
        mock_task.actual_effort = None

        # Only ONE execute call (no filter_type means no product lookup)
        session.execute = AsyncMock(
            return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[mock_task]))))
        )

        service = TaskService(db_manager, mock_tenant_manager)

        # Act
        result = await service.list_tasks(status="waiting")

        # Assert - exception-based pattern: list_tasks returns {"tasks": [], "count": N}
        assert "tasks" in result
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, mock_db_manager, mock_tenant_manager):
        """Test listing when no tasks exist"""
        # Arrange
        db_manager, session = mock_db_manager

        # Only ONE execute call (no filter_type means no product lookup)
        session.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[])))))

        service = TaskService(db_manager, mock_tenant_manager)

        # Act
        result = await service.list_tasks()

        # Assert - exception-based pattern: list_tasks returns {"tasks": [], "count": N}
        assert "tasks" in result
        assert len(result["tasks"]) == 0
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_list_tasks_no_tenant_context(self, mock_tenant_manager):
        """Test list_tasks raises ValidationError without tenant context"""
        from src.giljo_mcp.exceptions import ValidationError

        # Arrange
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value=None)

        service = TaskService(db_manager, tenant_manager)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await service.list_tasks()

        assert "No tenant context" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_tasks_no_project_found(self, mock_db_manager, mock_tenant_manager):
        """Test list_tasks returns empty when filter_type=product_tasks and no active product"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock no active product found (for filter_type="product_tasks")
        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        service = TaskService(db_manager, mock_tenant_manager)

        # Act - with filter_type="product_tasks", no active product returns empty list
        result = await service.list_tasks(filter_type="product_tasks")

        # Assert - service returns empty list when no active product
        # exception-based pattern: list_tasks returns {"tasks": [], "count": N}
        assert "tasks" in result
        assert result["tasks"] == []
        assert result["count"] == 0
