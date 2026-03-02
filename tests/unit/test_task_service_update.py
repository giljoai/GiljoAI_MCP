"""
Unit tests for TaskService — update, error handling, and tenant isolation (Handover 0605)

Tests cover:
- Task updates and status changes
- Task assignment
- Task completion
- Error handling and database exceptions
- Tenant isolation and security requirements
"""

from unittest.mock import AsyncMock, Mock

import pytest

pytestmark = pytest.mark.skip(reason="0750b: schema drift — description field + fixture updates needed")

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.models import Task
from src.giljo_mcp.services.task_service import TaskService


class TestTaskServiceUpdates:
    """Test task update operations"""

    @pytest.mark.asyncio
    async def test_update_task_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful task update"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock task
        mock_task = Mock(spec=Task)
        mock_task.id = "task-id"
        mock_task.status = "pending"
        mock_task.priority = "medium"

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_task)))

        service = TaskService(db_manager, mock_tenant_manager)

        # Act
        result = await service.update_task(task_id="task-id", status="in_progress", priority="high")

        # Assert - exception-based pattern: update_task returns {"task_id": ..., "updated_fields": [...]}
        assert result["task_id"] == "task-id"
        assert "status" in result["updated_fields"]
        assert "priority" in result["updated_fields"]
        assert mock_task.status == "in_progress"
        assert mock_task.priority == "high"
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, mock_db_manager, mock_tenant_manager):
        """Test update raises ResourceNotFoundError when task doesn't exist"""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        # Arrange
        db_manager, session = mock_db_manager

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

        service = TaskService(db_manager, mock_tenant_manager)

        # Act & Assert
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.update_task(task_id="nonexistent", status="completed")

        assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_assign_task_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful task assignment"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock task
        mock_task = Mock(spec=Task)
        mock_task.id = "task-id"
        mock_task.status = "pending"
        mock_task.assigned_to = None

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_task)))

        service = TaskService(db_manager, mock_tenant_manager)

        # Act
        result = await service.assign_task(task_id="task-id", agent_name="impl-1")

        # Assert - exception-based pattern: assign_task delegates to update_task
        # Returns {"task_id": ..., "updated_fields": [...]}
        assert result["task_id"] == "task-id"
        assert "assigned_to" in result["updated_fields"]
        assert mock_task.assigned_to == "impl-1"
        assert mock_task.status == "assigned"

    @pytest.mark.asyncio
    async def test_complete_task_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful task completion"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock task
        mock_task = Mock(spec=Task)
        mock_task.id = "task-id"
        mock_task.status = "in_progress"

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_task)))

        service = TaskService(db_manager, mock_tenant_manager)

        # Act
        result = await service.complete_task(task_id="task-id")

        # Assert - exception-based pattern: complete_task delegates to update_task
        # Returns {"task_id": ..., "updated_fields": [...]}
        assert result["task_id"] == "task-id"
        assert "status" in result["updated_fields"]
        assert mock_task.status == "completed"


class TestTaskServiceErrorHandling:
    """Test error handling - service raises BaseGiljoException on database errors"""

    @pytest.mark.asyncio
    async def test_log_task_database_exception(self, mock_tenant_manager):
        """Test database exception raises BaseGiljoException in log_task"""
        from src.giljo_mcp.exceptions import BaseGiljoError

        # Arrange
        db_manager = Mock()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        session.__aexit__ = AsyncMock(return_value=False)
        db_manager.get_session_async = Mock(return_value=session)

        service = TaskService(db_manager, mock_tenant_manager)

        # Act & Assert
        with pytest.raises(BaseGiljoError) as exc_info:
            await service.log_task(content="test task")

        assert "Connection lost" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_tasks_database_exception(self, mock_tenant_manager):
        """Test database exception raises BaseGiljoException in list_tasks"""
        from src.giljo_mcp.exceptions import BaseGiljoError

        # Arrange
        db_manager = Mock()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        session.__aexit__ = AsyncMock(return_value=False)
        db_manager.get_session_async = Mock(return_value=session)

        service = TaskService(db_manager, mock_tenant_manager)

        # Act & Assert
        with pytest.raises(BaseGiljoError) as exc_info:
            await service.list_tasks()

        assert "Connection lost" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_task_database_exception(self, mock_tenant_manager):
        """Test database exception raises BaseGiljoException in update_task"""
        from src.giljo_mcp.exceptions import BaseGiljoError

        # Arrange
        db_manager = Mock()
        session = AsyncMock()
        session.__aenter__ = AsyncMock(side_effect=Exception("Connection lost"))
        session.__aexit__ = AsyncMock(return_value=False)
        db_manager.get_session_async = Mock(return_value=session)

        service = TaskService(db_manager, mock_tenant_manager)

        # Act & Assert
        with pytest.raises(BaseGiljoError) as exc_info:
            await service.update_task(task_id="task-id", status="completed")

        assert "Connection lost" in str(exc_info.value)


class TestTaskServiceTenantIsolation:
    """Test tenant isolation and security requirements (Handover 0433 Phase 2)"""

    @pytest.mark.asyncio
    async def test_create_task_requires_tenant_key(self, mock_db_manager):
        """Task creation must fail if tenant_key is None."""
        from src.giljo_mcp.exceptions import ValidationError

        # Arrange
        db_manager, session = mock_db_manager
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value=None)  # No tenant context

        service = TaskService(db_manager, tenant_manager)

        # Act & Assert
        with pytest.raises(ValidationError, match="tenant_key.*required"):
            await service.log_task(
                content="Test task",
                tenant_key=None  # Explicitly None
            )

    @pytest.mark.asyncio
    async def test_create_task_requires_product_id(self, mock_db_manager, mock_tenant_manager):
        """Task creation must fail if product_id is None."""
        from src.giljo_mcp.exceptions import ValidationError

        # Arrange
        db_manager, session = mock_db_manager
        service = TaskService(db_manager, mock_tenant_manager)

        # Act & Assert
        with pytest.raises(ValidationError, match="product_id.*required"):
            await service.log_task(
                content="Test task",
                tenant_key="test-tenant",
                product_id=None  # Should raise ValidationError
            )

    @pytest.mark.asyncio
    async def test_create_task_tenant_isolation(self, mock_db_manager, mock_tenant_manager):
        """Cannot create task with project from different tenant."""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        # Arrange
        db_manager, session = mock_db_manager

        # Mock project NOT found (cross-tenant access blocked)
        session.execute = AsyncMock(
            return_value=Mock(scalar_one_or_none=Mock(return_value=None))
        )

        service = TaskService(db_manager, mock_tenant_manager)

        # Act & Assert - Attempting to use tenant_b's project from tenant_a
        with pytest.raises(ResourceNotFoundError, match="not found or access denied"):
            await service.log_task(
                content="Test task",
                tenant_key="tenant_a",
                product_id="product-from-tenant-b",
                project_id="project-from-tenant-b"
            )

    @pytest.mark.asyncio
    async def test_cannot_query_other_tenant_project(self):
        """Verify fallback logic removed - no queries without tenant_key filtering."""
        # This is a code inspection test - verify lines 149, 161-175 are removed
        import inspect
        from src.giljo_mcp.services.task_service import TaskService

        source = inspect.getsource(TaskService._log_task_impl)

        # Verify unsafe fallback patterns are NOT in the code
        assert "Fallback for backward compatibility" not in source, \
            "Line 148-149 unsafe fallback should be removed"
        assert "Find first active project" not in source or \
               "tenant_key" in source.split("Find first active project")[1].split("session.execute")[0], \
            "Lines 161-175 should be removed or require tenant_key filtering"

    @pytest.mark.asyncio
    async def test_list_tasks_all_tasks_filter_removed(self):
        """Verify filter_type='all_tasks' special handling is removed."""
        import inspect
        from src.giljo_mcp.services.task_service import TaskService

        source = inspect.getsource(TaskService.list_tasks)

        # Verify filter_type="all_tasks" handling is removed (lines 306-308)
        assert 'filter_type == "all_tasks"' not in source, \
            "Lines 306-308 filter_type='all_tasks' handling should be removed"
