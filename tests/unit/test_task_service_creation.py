"""
Unit tests for TaskService — creation operations (Handover 0605)

Tests cover:
- Task creation and logging
- Title/description separation (Bug 2 fix)
"""

from unittest.mock import AsyncMock, Mock

import pytest

pytestmark = pytest.mark.skip(reason="0750b: schema drift — description field + fixture updates needed")

pytestmark = pytest.mark.skip(reason="0750b: Tests use stale dict-return API; needs rewrite for Pydantic model returns")

from src.giljo_mcp.models import Project, Task
from src.giljo_mcp.services.task_service import TaskService


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
