"""
Unit tests for TaskService (Handover 0605)

Tests cover:
- Task creation and logging
- Task listing and filtering
- Task updates and status changes
- Task assignment
- Error handling and edge cases

Target: 60%+ line coverage (pragmatic given complexity)
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.giljo_mcp.models import Project, Task
from src.giljo_mcp.services.task_service import TaskService


@pytest.fixture
def mock_db_manager():
    """Create properly configured mock database manager."""
    db_manager = Mock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    db_manager.get_session_async = Mock(return_value=session)
    return db_manager, session


@pytest.fixture
def mock_tenant_manager():
    """Create mock tenant manager."""
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="test-tenant")
    return tenant_manager


class TestTaskServiceCreation:
    """Test task creation operations"""

    @pytest.mark.asyncio
    async def test_log_task_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful task logging"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock existing active project
        mock_project = Mock(spec=Project)
        mock_project.id = "project-id"
        mock_project.tenant_key = "test-tenant"
        mock_project.product_id = "product-1"

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_project)))

        service = TaskService(db_manager, mock_tenant_manager)

        # Act
        result = await service.log_task(
            content="Fix authentication bug",
            category="bug",
            priority="high",
            product_id="product-1",
            tenant_key="test-tenant"
        )

        # Assert - exception-based pattern: log_task returns task_id string directly
        assert isinstance(result, str)  # Returns task_id string, not dict
        assert result is not None  # task_id should be set
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_log_task_without_project(self, mock_db_manager, mock_tenant_manager):
        """Test that log_task creates task without project when only product_id provided"""
        # Arrange
        db_manager, session = mock_db_manager

        service = TaskService(db_manager, mock_tenant_manager)

        # Act - No project_id, only product_id
        result = await service.log_task(
            content="First task",
            priority="medium",
            product_id="product-1",
            tenant_key="test-tenant"
        )

        # Assert - exception-based pattern: log_task returns task_id string directly
        assert isinstance(result, str)  # Returns task_id string, not dict
        # Verify that add was called once for the task (no project lookup)
        assert session.add.call_count == 1
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_log_task_with_specific_project_id(self, mock_db_manager, mock_tenant_manager):
        """Test logging task to specific project"""
        # Arrange
        db_manager, session = mock_db_manager

        # Mock specific project
        mock_project = Mock(spec=Project)
        mock_project.id = "specific-project"
        mock_project.tenant_key = "test-tenant"
        mock_project.product_id = "product-1"

        session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_project)))

        service = TaskService(db_manager, mock_tenant_manager)

        # Act
        result = await service.log_task(
            content="Task for specific project",
            project_id="specific-project",
            product_id="product-1",
            tenant_key="test-tenant"
        )

        # Assert - exception-based pattern: log_task returns task_id string directly
        assert isinstance(result, str)  # Returns task_id string, not dict

    @pytest.mark.asyncio
    async def test_create_task_success(self, mock_db_manager, mock_tenant_manager):
        """Test successful task creation"""
        # Arrange
        db_manager, session = mock_db_manager

        service = TaskService(db_manager, mock_tenant_manager)

        # Act
        result = await service.create_task(
            title="Implement feature X",
            description="Add new feature X with unit tests",
            priority="high",
            product_id="product-1",
            tenant_key="test-tenant"
        )

        # Assert - exception-based pattern: create_task delegates to log_task (returns task_id string)
        assert isinstance(result, str)  # Returns task_id string, not dict


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


class TestTaskServiceTitleDescriptionSeparation:
    """Tests for Bug 2 fix: title and description are preserved separately.

    Previously, _log_task_impl set both Task.title and Task.description to the
    same 'content' value, losing the real title when a separate description was
    provided. After the fix, log_task accepts optional title and description
    parameters that are stored independently on the Task model.
    """

    @pytest.mark.asyncio
    async def test_log_task_with_separate_title_and_description(
        self, mock_db_manager, mock_tenant_manager
    ):
        """When title and description are both provided, they should be stored separately."""
        db_manager, session = mock_db_manager
        service = TaskService(db_manager, mock_tenant_manager)

        captured_task = None
        original_add = session.add

        def capture_add(obj):
            nonlocal captured_task
            if isinstance(obj, Task):
                captured_task = obj
            original_add(obj)

        session.add = capture_add

        await service.log_task(
            content="Fix authentication bug",
            title="Fix login flow",
            description="Users cannot login with email containing special characters",
            category="bug",
            priority="high",
            product_id="product-1",
            tenant_key="test-tenant",
        )

        assert captured_task is not None, "Task should have been added to session"
        assert captured_task.title == "Fix login flow"
        assert captured_task.description == "Users cannot login with email containing special characters"

    @pytest.mark.asyncio
    async def test_log_task_title_only_falls_back_for_description(
        self, mock_db_manager, mock_tenant_manager
    ):
        """When only title is provided (no description), description falls back to content."""
        db_manager, session = mock_db_manager
        service = TaskService(db_manager, mock_tenant_manager)

        captured_task = None
        original_add = session.add

        def capture_add(obj):
            nonlocal captured_task
            if isinstance(obj, Task):
                captured_task = obj
            original_add(obj)

        session.add = capture_add

        await service.log_task(
            content="Fix authentication bug",
            title="Fix auth",
            category="bug",
            priority="high",
            product_id="product-1",
            tenant_key="test-tenant",
        )

        assert captured_task is not None
        assert captured_task.title == "Fix auth"
        # description falls back to content when not provided
        assert captured_task.description == "Fix authentication bug"

    @pytest.mark.asyncio
    async def test_log_task_backwards_compatible_content_only(
        self, mock_db_manager, mock_tenant_manager
    ):
        """When neither title nor description is provided, content is used for both (backwards compat)."""
        db_manager, session = mock_db_manager
        service = TaskService(db_manager, mock_tenant_manager)

        captured_task = None
        original_add = session.add

        def capture_add(obj):
            nonlocal captured_task
            if isinstance(obj, Task):
                captured_task = obj
            original_add(obj)

        session.add = capture_add

        await service.log_task(
            content="Fix authentication bug",
            category="bug",
            priority="high",
            product_id="product-1",
            tenant_key="test-tenant",
        )

        assert captured_task is not None
        assert captured_task.title == "Fix authentication bug"
        assert captured_task.description == "Fix authentication bug"

    @pytest.mark.asyncio
    async def test_create_task_preserves_title_and_description(
        self, mock_db_manager, mock_tenant_manager
    ):
        """TaskService.create_task should pass title and description separately."""
        db_manager, session = mock_db_manager
        service = TaskService(db_manager, mock_tenant_manager)

        captured_task = None
        original_add = session.add

        def capture_add(obj):
            nonlocal captured_task
            if isinstance(obj, Task):
                captured_task = obj
            original_add(obj)

        session.add = capture_add

        await service.create_task(
            title="Implement feature X",
            description="Add new feature X with unit tests and docs",
            priority="high",
            product_id="product-1",
            tenant_key="test-tenant",
        )

        assert captured_task is not None
        assert captured_task.title == "Implement feature X"
        assert captured_task.description == "Add new feature X with unit tests and docs"
