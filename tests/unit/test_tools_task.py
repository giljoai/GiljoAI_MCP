"""
Comprehensive tests for task.py tools
Target: 3.02% → 95%+ coverage

Tests all task tool functions:
- register_task_tools
- create_task
- list_tasks
- update_task
- get_product_task_summary
- get_task_dependencies
- bulk_update_tasks
- create_task_conversion_history
- get_conversion_history
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio

from src.giljo_mcp.models import Task
from src.giljo_mcp.tools.task import register_task_tools
from tests.utils.tools_helpers import (
    AssertionHelpers,
    MockMCPToolRegistrar,
    ToolsTestHelper,
)


class TestTaskTools:
    """Test class for task tools"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]
        self.mock_server = tools_test_setup["mcp_server"]

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Task Test Project")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_register_task_tools(self):
        """Test that all task tools are registered properly"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Register tools
        register_task_tools(mock_server, self.db_manager, self.tenant_manager)

        # Verify all expected tools are registered
        expected_tools = [
            "create_task",
            "list_tasks",
            "update_task",
            "get_product_task_summary",
            "get_task_dependencies",
            "bulk_update_tasks",
            "create_task_conversion_history",
            "get_conversion_history",
        ]

        registered_tools = registrar.get_all_tools()
        for tool in expected_tools:
            AssertionHelpers.assert_tool_registered(registrar, tool)

        assert len(registered_tools) >= len(expected_tools)

    # create_task tests
    @pytest.mark.asyncio
    async def test_create_task_success(self):
        """Test successful task creation"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        create_task = registrar.get_registered_tool("create_task")

        result = await create_task(
            title="Test Task", description="Test task description", priority="high", status="waiting"
        )

        AssertionHelpers.assert_success_response(result, ["task_id", "created"])
        assert result["task"]["title"] == "Test Task"
        assert result["task"]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_create_task_with_parent(self):
        """Test creating task with parent relationship"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create parent task first
        async with self.db_manager.get_session_async() as session:
            parent_task = await ToolsTestHelper.create_test_task(session, self.project.id, "Parent Task", "pending")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        create_task = registrar.get_registered_tool("create_task")

        result = await create_task(title="Child Task", description="Child task description", parent_id=parent_task.id)

        AssertionHelpers.assert_success_response(result, ["task_id", "created"])
        assert result["task"]["parent_id"] == parent_task.id

    @pytest.mark.asyncio
    async def test_create_task_missing_title(self):
        """Test creating task without required title"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        create_task = registrar.get_registered_tool("create_task")

        result = await create_task(description="Task without title")

        AssertionHelpers.assert_error_response(result, "Title is required")

    @pytest.mark.asyncio
    async def test_create_task_invalid_parent(self):
        """Test creating task with invalid parent ID"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        create_task = registrar.get_registered_tool("create_task")

        result = await create_task(
            title="Test Task",
            parent_id=str(uuid.uuid4()),  # Non-existent parent
        )

        AssertionHelpers.assert_error_response(result, "Parent task not found")

    # list_tasks tests
    @pytest.mark.asyncio
    async def test_list_tasks_all(self):
        """Test listing all tasks"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test tasks
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_task(session, self.project.id, "Task 1", "pending")
            await ToolsTestHelper.create_test_task(session, self.project.id, "Task 2", "in_progress")
            await ToolsTestHelper.create_test_task(session, self.project.id, "Task 3", "database_initialized")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        list_tasks = registrar.get_registered_tool("list_tasks")

        result = await list_tasks()

        AssertionHelpers.assert_success_response(result, ["tasks", "total", "filters"])
        assert result["total"] == 3
        assert len(result["tasks"]) == 3

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(self):
        """Test listing tasks with status filter"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test tasks with different statuses
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_task(session, self.project.id, "Task 1", "pending")
            await ToolsTestHelper.create_test_task(session, self.project.id, "Task 2", "pending")
            await ToolsTestHelper.create_test_task(session, self.project.id, "Task 3", "database_initialized")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        list_tasks = registrar.get_registered_tool("list_tasks")

        result = await list_tasks(status="waiting")

        AssertionHelpers.assert_success_response(result, ["tasks", "total"])
        assert result["total"] == 2
        assert all(task["status"] == "pending" for task in result["tasks"])

    @pytest.mark.asyncio
    async def test_list_tasks_with_priority_filter(self):
        """Test listing tasks with priority filter"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test tasks with different priorities
        async with self.db_manager.get_session_async() as session:
            task1 = Task(
                id=str(uuid.uuid4()),
                title="High Priority Task",
                description="Test task",
                priority="high",
                status="waiting",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )
            task2 = Task(
                id=str(uuid.uuid4()),
                title="Low Priority Task",
                description="Test task",
                priority="low",
                status="waiting",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )
            session.add_all([task1, task2])
            await session.commit()

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        list_tasks = registrar.get_registered_tool("list_tasks")

        result = await list_tasks(priority="high")

        AssertionHelpers.assert_success_response(result, ["tasks", "total"])
        assert result["total"] == 1
        assert result["tasks"][0]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_list_tasks_with_pagination(self):
        """Test listing tasks with pagination"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create multiple test tasks
        async with self.db_manager.get_session_async() as session:
            for i in range(5):
                await ToolsTestHelper.create_test_task(session, self.project.id, f"Task {i + 1}", "pending")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        list_tasks = registrar.get_registered_tool("list_tasks")

        result = await list_tasks(limit=2, offset=1)

        AssertionHelpers.assert_success_response(result, ["tasks", "total"])
        assert result["total"] == 5
        assert len(result["tasks"]) == 2

    # update_task tests
    @pytest.mark.asyncio
    async def test_update_task_status(self):
        """Test updating task status"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test task
        async with self.db_manager.get_session_async() as session:
            task = await ToolsTestHelper.create_test_task(session, self.project.id, "Test Task", "pending")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        update_task = registrar.get_registered_tool("update_task")

        result = await update_task(task_id=task.id, status="in_progress")

        AssertionHelpers.assert_success_response(result, ["task"])
        assert result["task"]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_update_task_multiple_fields(self):
        """Test updating multiple task fields"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test task
        async with self.db_manager.get_session_async() as session:
            task = await ToolsTestHelper.create_test_task(session, self.project.id, "Test Task", "pending")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        update_task = registrar.get_registered_tool("update_task")

        result = await update_task(
            task_id=task.id, status="in_progress", priority="high", description="Updated description"
        )

        AssertionHelpers.assert_success_response(result, ["task"])
        assert result["task"]["status"] == "in_progress"
        assert result["task"]["priority"] == "high"
        assert result["task"]["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_update_task_not_found(self):
        """Test updating non-existent task"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        update_task = registrar.get_registered_tool("update_task")

        result = await update_task(task_id=str(uuid.uuid4()), status="database_initialized")

        AssertionHelpers.assert_error_response(result, "Task not found")

    # get_product_task_summary tests
    @pytest.mark.asyncio
    async def test_get_product_task_summary(self):
        """Test getting product task summary"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create tasks with different statuses
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_task(session, self.project.id, "Task 1", "pending")
            await ToolsTestHelper.create_test_task(session, self.project.id, "Task 2", "in_progress")
            await ToolsTestHelper.create_test_task(session, self.project.id, "Task 3", "database_initialized")
            await ToolsTestHelper.create_test_task(session, self.project.id, "Task 4", "database_initialized")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        get_summary = registrar.get_registered_tool("get_product_task_summary")

        result = await get_summary()

        AssertionHelpers.assert_success_response(result, ["summary", "statistics"])
        assert result["summary"]["total_tasks"] == 4
        assert result["summary"]["pending"] == 1
        assert result["summary"]["in_progress"] == 1
        assert result["summary"]["database_initialized"] == 2

    # get_task_dependencies tests
    @pytest.mark.asyncio
    async def test_get_task_dependencies_with_children(self):
        """Test getting task dependencies with child tasks"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create parent and child tasks
        async with self.db_manager.get_session_async() as session:
            parent_task = await ToolsTestHelper.create_test_task(session, self.project.id, "Parent Task", "pending")

            child_task = Task(
                id=str(uuid.uuid4()),
                title="Child Task",
                description="Child task description",
                status="waiting",
                priority="medium",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                parent_id=parent_task.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(child_task)
            await session.commit()

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        get_dependencies = registrar.get_registered_tool("get_task_dependencies")

        result = await get_dependencies(task_id=parent_task.id)

        AssertionHelpers.assert_success_response(result, ["task", "children", "parent_chain"])
        assert len(result["children"]) == 1
        assert result["children"][0]["title"] == "Child Task"

    @pytest.mark.asyncio
    async def test_get_task_dependencies_with_parent(self):
        """Test getting task dependencies with parent chain"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create grandparent, parent, and child tasks
        async with self.db_manager.get_session_async() as session:
            grandparent = await ToolsTestHelper.create_test_task(
                session, self.project.id, "Grandparent Task", "pending"
            )

            parent = Task(
                id=str(uuid.uuid4()),
                title="Parent Task",
                description="Parent task",
                status="waiting",
                priority="medium",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                parent_id=grandparent.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(parent)
            await session.commit()
            await session.refresh(parent)

            child = Task(
                id=str(uuid.uuid4()),
                title="Child Task",
                description="Child task",
                status="waiting",
                priority="medium",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                parent_id=parent.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(child)
            await session.commit()
            await session.refresh(child)

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        get_dependencies = registrar.get_registered_tool("get_task_dependencies")

        result = await get_dependencies(task_id=child.id)

        AssertionHelpers.assert_success_response(result, ["task", "parent_chain"])
        assert len(result["parent_chain"]) == 2
        assert result["parent_chain"][0]["title"] == "Parent Task"
        assert result["parent_chain"][1]["title"] == "Grandparent Task"

    # bulk_update_tasks tests
    @pytest.mark.asyncio
    async def test_bulk_update_tasks_success(self):
        """Test bulk updating multiple tasks"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test tasks
        async with self.db_manager.get_session_async() as session:
            task1 = await ToolsTestHelper.create_test_task(session, self.project.id, "Task 1", "pending")
            task2 = await ToolsTestHelper.create_test_task(session, self.project.id, "Task 2", "pending")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        bulk_update = registrar.get_registered_tool("bulk_update_tasks")

        updates = [
            {"task_id": task1.id, "status": "in_progress", "priority": "high"},
            {"task_id": task2.id, "status": "database_initialized", "priority": "medium"},
        ]

        result = await bulk_update(updates=updates)

        AssertionHelpers.assert_success_response(result, ["updated_count", "updated_tasks"])
        assert result["updated_count"] == 2
        assert len(result["updated_tasks"]) == 2

    @pytest.mark.asyncio
    async def test_bulk_update_tasks_partial_failure(self):
        """Test bulk update with some invalid task IDs"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create one valid task
        async with self.db_manager.get_session_async() as session:
            task1 = await ToolsTestHelper.create_test_task(session, self.project.id, "Task 1", "pending")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        bulk_update = registrar.get_registered_tool("bulk_update_tasks")

        updates = [
            {"task_id": task1.id, "status": "in_progress"},
            {"task_id": str(uuid.uuid4()), "status": "database_initialized"},  # Invalid ID
        ]

        result = await bulk_update(updates=updates)

        AssertionHelpers.assert_success_response(result, ["updated_count", "errors"])
        assert result["updated_count"] == 1
        assert len(result["errors"]) == 1

    # create_task_conversion_history tests
    @pytest.mark.asyncio
    async def test_create_task_conversion_history(self):
        """Test creating task conversion history"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test task
        async with self.db_manager.get_session_async() as session:
            task = await ToolsTestHelper.create_test_task(session, self.project.id, "Test Task", "pending")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        create_history = registrar.get_registered_tool("create_task_conversion_history")

        result = await create_history(
            task_id=task.id,
            conversion_type="template_to_task",
            original_data={"template_id": "test_template"},
            conversion_metadata={"agent": "test_agent"},
        )

        AssertionHelpers.assert_success_response(result, ["history_id", "created"])
        assert result["history"]["conversion_type"] == "template_to_task"

    # get_conversion_history tests
    @pytest.mark.asyncio
    async def test_get_conversion_history(self):
        """Test getting conversion history for a task"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test task and history
        async with self.db_manager.get_session_async() as session:
            task = await ToolsTestHelper.create_test_task(session, self.project.id, "Test Task", "pending")

            # TaskConversionHistory model not available - skip this test section
            # history = TaskConversionHistory(
            #     id=str(uuid.uuid4()),
            #     task_id=task.id,
            #     conversion_type="template_to_task",
            #     original_data={"template_id": "test_template"},
            #     conversion_metadata={"agent": "test_agent"},
            #     tenant_key=self.project.tenant_key,
            #     created_at=datetime.now(timezone.utc)
            # )
            # session.add(history)
            await session.commit()

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        get_history = registrar.get_registered_tool("get_conversion_history")

        result = await get_history(task_id=task.id)

        AssertionHelpers.assert_success_response(result, ["task_id", "history"])
        assert len(result["history"]) == 1
        assert result["history"][0]["conversion_type"] == "template_to_task"

    # Error handling and edge cases
    @pytest.mark.asyncio
    async def test_task_tools_no_active_project(self):
        """Test task tools with no active project"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        self.tenant_manager.clear_current_tenant()

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        create_task = registrar.get_registered_tool("create_task")

        result = await create_task(title="Test Task")

        AssertionHelpers.assert_error_response(result, "No active project")

    @pytest.mark.asyncio
    async def test_task_tools_database_error_handling(self):
        """Test that task tools handle database errors gracefully"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database to raise exception
        with patch.object(self.db_manager, "get_session_async") as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            register_task_tools(mock_server, self.db_manager, self.tenant_manager)
            list_tasks = registrar.get_registered_tool("list_tasks")

            result = await list_tasks()

        AssertionHelpers.assert_error_response(result, "Database connection failed")

    @pytest.mark.asyncio
    async def test_task_circular_dependency_prevention(self):
        """Test prevention of circular dependencies in parent-child relationships"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create parent and child tasks
        async with self.db_manager.get_session_async() as session:
            parent = await ToolsTestHelper.create_test_task(session, self.project.id, "Parent Task", "pending")

            child = Task(
                id=str(uuid.uuid4()),
                title="Child Task",
                description="Child task",
                status="waiting",
                priority="medium",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                parent_id=parent.id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(child)
            await session.commit()

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        update_task = registrar.get_registered_tool("update_task")

        # Try to make parent a child of its own child (should fail)
        result = await update_task(task_id=parent.id, parent_id=child.id)

        AssertionHelpers.assert_error_response(result, "circular dependency")

    @pytest.mark.asyncio
    async def test_task_status_transitions(self):
        """Test valid and invalid task status transitions"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test task
        async with self.db_manager.get_session_async() as session:
            task = await ToolsTestHelper.create_test_task(session, self.project.id, "Test Task", "pending")

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        update_task = registrar.get_registered_tool("update_task")

        # Valid transitions
        result1 = await update_task(task_id=task.id, status="in_progress")
        AssertionHelpers.assert_success_response(result1)

        result2 = await update_task(task_id=task.id, status="database_initialized")
        AssertionHelpers.assert_success_response(result2)

        # Test that completed tasks can be reopened
        result3 = await update_task(task_id=task.id, status="in_progress")
        AssertionHelpers.assert_success_response(result3)

    @pytest.mark.asyncio
    async def test_task_search_and_filtering(self):
        """Test advanced task search and filtering capabilities"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test tasks with various attributes
        async with self.db_manager.get_session_async() as session:
            task1 = Task(
                id=str(uuid.uuid4()),
                title="Bug Fix: Authentication Issue",
                description="Fix login authentication bug",
                status="waiting",
                priority="high",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )
            task2 = Task(
                id=str(uuid.uuid4()),
                title="Feature: Add Dark Mode",
                description="Implement dark mode theme",
                status="in_progress",
                priority="medium",
                project_id=self.project.id,
                tenant_key=self.project.tenant_key,
                created_at=datetime.now(timezone.utc),
            )
            session.add_all([task1, task2])
            await session.commit()

        register_task_tools(mock_server, self.db_manager, self.tenant_manager)
        list_tasks = registrar.get_registered_tool("list_tasks")

        # Test search by title
        result = await list_tasks(search="Bug Fix")
        AssertionHelpers.assert_success_response(result)
        assert result["total"] == 1
        assert "Bug Fix" in result["tasks"][0]["title"]

        # Test combined filters
        result2 = await list_tasks(status="in_progress", priority="medium")
        AssertionHelpers.assert_success_response(result2)
        assert result2["total"] == 1
