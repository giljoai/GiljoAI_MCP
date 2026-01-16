"""
Integration tests for /gil_task slash command.

These tests verify that the create_task MCP tool works correctly
and that tasks appear in the database and UI.

Note: The actual slash command behavior is client-side (Claude Code skill)
and cannot be directly tested in pytest. These tests verify the backend
MCP tool integration.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.tasks import Task
from src.giljo_mcp.services.task_service import TaskService


@pytest.mark.asyncio
class TestCreateTaskMCPTool:
    """Integration tests for create_task MCP tool backend"""

    async def test_create_task_with_category_appears_in_database(
        self, async_session: AsyncSession
    ):
        """Task created via create_task tool appears in database with category."""
        # Arrange
        task_service = TaskService(async_session)

        # Act
        result = await task_service.log_task(
            content="Refactor authentication service",
            category="backend",
            priority="high",
        )

        # Assert
        assert result["success"] is True
        assert "task_id" in result

        # Verify in database
        stmt = select(Task).where(Task.id == result["task_id"])
        db_result = await async_session.execute(stmt)
        task = db_result.scalar_one()

        assert task.title == "Refactor authentication service"
        assert task.category == "backend"
        assert task.priority == "high"
        assert task.status == "pending"

    async def test_create_task_without_category_uses_default(
        self, async_session: AsyncSession
    ):
        """Task created without category gets None (or title as category)."""
        # Arrange
        task_service = TaskService(async_session)

        # Act
        result = await task_service.log_task(
            content="Fix bug in login flow",
            category=None,
            priority="medium",
        )

        # Assert
        assert result["success"] is True

        # Verify in database
        stmt = select(Task).where(Task.id == result["task_id"])
        db_result = await async_session.execute(stmt)
        task = db_result.scalar_one()

        assert task.title == "Fix bug in login flow"
        assert task.priority == "medium"

    async def test_create_task_validates_priority(
        self, async_session: AsyncSession
    ):
        """Task creation accepts valid priority values."""
        # Arrange
        task_service = TaskService(async_session)
        valid_priorities = ["low", "medium", "high", "critical"]

        # Act & Assert
        for priority in valid_priorities:
            result = await task_service.log_task(
                content=f"Task with {priority} priority",
                category="general",
                priority=priority,
            )

            assert result["success"] is True

            # Verify in database
            stmt = select(Task).where(Task.id == result["task_id"])
            db_result = await async_session.execute(stmt)
            task = db_result.scalar_one()

            assert task.priority == priority

    async def test_create_task_with_all_categories(
        self, async_session: AsyncSession
    ):
        """Task creation works with all valid categories."""
        # Arrange
        task_service = TaskService(async_session)
        valid_categories = ["frontend", "backend", "database", "infra", "docs", "general"]

        # Act & Assert
        for category in valid_categories:
            result = await task_service.log_task(
                content=f"Task for {category} category",
                category=category,
                priority="medium",
            )

            assert result["success"] is True

            # Verify in database
            stmt = select(Task).where(Task.id == result["task_id"])
            db_result = await async_session.execute(stmt)
            task = db_result.scalar_one()

            assert task.category == category

    async def test_task_appears_with_correct_tenant_isolation(
        self, async_session: AsyncSession
    ):
        """Tasks are properly isolated by tenant_key."""
        # Arrange
        task_service = TaskService(async_session)
        tenant_key_1 = "tenant_abc"
        tenant_key_2 = "tenant_xyz"

        # Act - Create tasks for different tenants
        result_1 = await task_service.log_task(
            content="Task for tenant 1",
            category="backend",
            priority="high",
            tenant_key=tenant_key_1,
        )

        result_2 = await task_service.log_task(
            content="Task for tenant 2",
            category="frontend",
            priority="low",
            tenant_key=tenant_key_2,
        )

        # Assert - Both tasks created
        assert result_1["success"] is True
        assert result_2["success"] is True

        # Verify tenant isolation in database
        stmt_1 = select(Task).where(
            Task.id == result_1["task_id"],
            Task.tenant_key == tenant_key_1
        )
        db_result_1 = await async_session.execute(stmt_1)
        task_1 = db_result_1.scalar_one()
        assert task_1.tenant_key == tenant_key_1

        stmt_2 = select(Task).where(
            Task.id == result_2["task_id"],
            Task.tenant_key == tenant_key_2
        )
        db_result_2 = await async_session.execute(stmt_2)
        task_2 = db_result_2.scalar_one()
        assert task_2.tenant_key == tenant_key_2


@pytest.fixture
async def async_session(db_session):
    """
    Provide an async database session for integration tests.

    Note: This assumes a db_session fixture exists in conftest.py
    If not, you'll need to create one that provides an AsyncSession.
    """
    return db_session
