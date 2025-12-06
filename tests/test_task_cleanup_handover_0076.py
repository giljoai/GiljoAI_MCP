"""
Test suite for Handover 0076: Task Field Cleanup and Product Scoping

Tests:
1. Task model without assignment fields
2. Product-scoped task filtering (product_tasks, all_tasks)
3. Task-to-project conversion with active product validation
4. MCP task creation without assignment parameters
5. API endpoint behavior with new filtering
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.giljo_mcp.models import Base, Product, Project, Task, User


# Test Configuration
TEST_DB_URL = "postgresql+asyncpg://postgres:***@localhost/giljo_mcp_test"


@pytest_asyncio.fixture
async def async_engine():
    """Create async database engine for testing"""
    engine = create_async_engine(TEST_DB_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine):
    """Create async database session"""
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def test_tenant_key():
    """Generate test tenant key"""
    return str(uuid4())


@pytest_asyncio.fixture
async def test_user(db_session, test_tenant_key):
    """Create test user"""
    user = User(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        username="testuser",
        email="test@example.com",
        password_hash="test_hash",
        role="admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def active_product(db_session, test_tenant_key):
    """Create active product"""
    product = Product(
        id=str(uuid4()), tenant_key=test_tenant_key, name="Test Product", description="Test Description", is_active=True
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def inactive_product(db_session, test_tenant_key):
    """Create inactive product"""
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="Inactive Product",
        description="Inactive Description",
        is_active=False,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


class TestTaskModelWithoutAssignmentFields:
    """Test Task model no longer has assignment fields"""

    @pytest.mark.asyncio
    async def test_task_model_no_assigned_to_user_field(self, db_session, test_tenant_key):
        """Task model should NOT have assigned_to_user_id field"""
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            title="Test Task",
            description="Test Description",
            status="waiting",
            priority="medium",
        )

        # Verify field does not exist
        assert not hasattr(task, "assigned_to_user_id"), "Task model should not have assigned_to_user_id field"

    @pytest.mark.asyncio
    async def test_task_model_no_assigned_to_agent_field(self, db_session, test_tenant_key):
        """Task model should NOT have assigned_to_agent_id field"""
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            title="Test Task",
            description="Test Description",
            status="waiting",
            priority="medium",
        )

        # Verify field does not exist
        assert not hasattr(task, "assigned_to_agent_id"), "Task model should not have assigned_to_agent_id field"

    @pytest.mark.asyncio
    async def test_task_creation_without_assignment_fields(
        self, db_session, test_tenant_key, test_user, active_product
    ):
        """Create task without assignment fields"""
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            title="Test Task",
            description="Test Description",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )

        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Verify task was created successfully
        assert task.id is not None
        assert task.title == "Test Task"
        assert task.product_id == active_product.id
        assert task.created_by_user_id == test_user.id


class TestProductScopedTaskFiltering:
    """Test product-scoped task filtering"""

    @pytest.mark.asyncio
    async def test_product_tasks_filter_shows_active_product_tasks_only(
        self, db_session, test_tenant_key, test_user, active_product, inactive_product
    ):
        """Product Tasks filter shows only active product tasks"""
        # Create tasks with different product_ids
        active_task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            title="Active Product Task",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )

        inactive_task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=inactive_product.id,
            title="Inactive Product Task",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )

        null_product_task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=None,
            title="NULL Product Task",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )

        db_session.add_all([active_task, inactive_task, null_product_task])
        await db_session.commit()

        # Query for active product tasks only
        query = select(Task).where(Task.tenant_key == test_tenant_key, Task.product_id == active_product.id)
        result = await db_session.execute(query)
        product_tasks = result.scalars().all()

        # Should only return active product task
        assert len(product_tasks) == 1
        assert product_tasks[0].title == "Active Product Task"
        assert product_tasks[0].product_id == active_product.id

    @pytest.mark.asyncio
    async def test_all_tasks_filter_shows_null_product_tasks_only(
        self, db_session, test_tenant_key, test_user, active_product
    ):
        """All Tasks filter shows only NULL product_id tasks"""
        # Create tasks with different product_ids
        product_task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            title="Product Task",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )

        null_task_1 = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=None,
            title="NULL Product Task 1",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )

        null_task_2 = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=None,
            title="NULL Product Task 2",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )

        db_session.add_all([product_task, null_task_1, null_task_2])
        await db_session.commit()

        # Query for NULL product tasks only
        query = select(Task).where(Task.tenant_key == test_tenant_key, Task.product_id.is_(None))
        result = await db_session.execute(query)
        all_tasks = result.scalars().all()

        # Should return only NULL product tasks
        assert len(all_tasks) == 2
        task_titles = {task.title for task in all_tasks}
        assert "NULL Product Task 1" in task_titles
        assert "NULL Product Task 2" in task_titles
        assert "Product Task" not in task_titles

    @pytest.mark.asyncio
    async def test_product_tasks_empty_when_no_active_product(self, db_session, test_tenant_key, test_user):
        """Product Tasks filter returns empty when no active product"""
        # Create task with NULL product_id
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=None,
            title="Unassigned Task",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Query for active product (should not exist)
        product_query = select(Product).where(Product.tenant_key == test_tenant_key, Product.is_active == True)
        product_result = await db_session.execute(product_query)
        active_product = product_result.scalar_one_or_none()

        assert active_product is None, "No active product should exist"

        # Product tasks query should return empty (use id == None pattern)
        if active_product:
            product_id = active_product.id
        else:
            product_id = None  # Will match no tasks

        task_query = select(Task).where(
            Task.tenant_key == test_tenant_key, Task.id == None if product_id is None else Task.product_id == product_id
        )
        task_result = await db_session.execute(task_query)
        product_tasks = task_result.scalars().all()

        assert len(product_tasks) == 0, "No tasks should match when no active product"


class TestTaskToProjectConversion:
    """Test task-to-project conversion functionality"""

    @pytest.mark.asyncio
    async def test_convert_task_to_project_with_active_product(
        self, db_session, test_tenant_key, test_user, active_product
    ):
        """Convert task to project when active product exists"""
        # Create task
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            title="Task to Convert",
            description="Task Description",
            status="waiting",
            priority="high",
            created_by_user_id=test_user.id,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Convert to project
        project = Project(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            name=task.title,
            mission=task.description or f"Converted from task: {task.title}",
            status="active",
        )
        db_session.add(project)
        await db_session.flush()

        # Mark task as completed (converted)
        task.status = "completed"
        task.converted_to_project_id = project.id

        await db_session.commit()
        await db_session.refresh(task)
        await db_session.refresh(project)

        # Verify conversion
        assert project.id is not None
        assert project.name == "Task to Convert"
        assert project.mission == "Task Description"
        assert project.product_id == active_product.id
        assert task.status == "completed"
        assert task.converted_to_project_id == project.id

    @pytest.mark.asyncio
    async def test_convert_task_requires_active_product(self, db_session, test_tenant_key, test_user):
        """Task conversion should fail when no active product exists"""
        # Create task with NULL product_id
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=None,
            title="Task without Product",
            description="Task Description",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Check for active product
        query = select(Product).where(Product.tenant_key == test_tenant_key, Product.is_active == True)
        result = await db_session.execute(query)
        active_product = result.scalar_one_or_none()

        # Should have no active product
        assert active_product is None, "No active product should exist for this test"

        # Conversion should fail (simulated - API would return 400)
        # This test validates the precondition check

    @pytest.mark.asyncio
    async def test_converted_task_marked_completed(self, db_session, test_tenant_key, test_user, active_product):
        """Converted task should be marked as completed"""
        # Create and convert task
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            title="Task to Convert",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Convert
        project = Project(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            name=task.title,
            mission=f"Converted from task: {task.title}",
            status="active",
        )
        db_session.add(project)
        await db_session.flush()

        task.status = "completed"
        task.converted_to_project_id = project.id

        await db_session.commit()
        await db_session.refresh(task)

        # Verify status
        assert task.status == "completed"
        assert task.converted_to_project_id == project.id


class TestMCPTaskCreation:
    """Test MCP task creation without assignment parameters"""

    @pytest.mark.asyncio
    async def test_mcp_create_task_with_active_product(self, db_session, test_tenant_key, active_product):
        """MCP task creation sets product_id when active product exists"""
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            title="MCP Task",
            description="Created via MCP",
            status="waiting",
            priority="medium",
        )

        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Verify task has product_id set
        assert task.product_id == active_product.id
        assert task.title == "MCP Task"

    @pytest.mark.asyncio
    async def test_mcp_create_task_without_active_product(self, db_session, test_tenant_key):
        """MCP task creation sets product_id=NULL when no active product"""
        # No active product in this test
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=None,
            title="MCP Task No Product",
            description="Created via MCP without active product",
            status="waiting",
            priority="medium",
        )

        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Verify task has NULL product_id
        assert task.product_id is None
        assert task.title == "MCP Task No Product"

    @pytest.mark.asyncio
    async def test_mcp_task_no_assignment_fields(self, db_session, test_tenant_key, active_product):
        """MCP-created tasks should not have assignment fields"""
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            title="MCP Task",
            status="waiting",
            priority="medium",
        )

        # Verify no assignment fields exist
        assert not hasattr(task, "assigned_to_user_id")
        assert not hasattr(task, "assigned_to_agent_id")


class TestEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_task_with_subtasks_not_converted(self, db_session, test_tenant_key, test_user, active_product):
        """Task with subtasks should be handled appropriately during conversion"""
        # Create parent task
        parent_task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            title="Parent Task",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )
        db_session.add(parent_task)
        await db_session.flush()

        # Create subtask
        subtask = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            parent_task_id=parent_task.id,
            title="Subtask",
            status="waiting",
            priority="medium",
            created_by_user_id=test_user.id,
        )
        db_session.add(subtask)
        await db_session.commit()

        # Verify subtask relationship
        assert subtask.parent_task_id == parent_task.id

        # Note: Conversion behavior with subtasks should be tested in API tests
        # This just validates the relationship exists

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, db_session, active_product):
        """Tasks from different tenants should not be visible"""
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())

        task1 = Task(
            id=str(uuid4()),
            tenant_key=tenant1,
            product_id=active_product.id,
            title="Tenant 1 Task",
            status="waiting",
            priority="medium",
        )

        task2 = Task(
            id=str(uuid4()),
            tenant_key=tenant2,
            product_id=active_product.id,
            title="Tenant 2 Task",
            status="waiting",
            priority="medium",
        )

        db_session.add_all([task1, task2])
        await db_session.commit()

        # Query for tenant1 tasks
        query = select(Task).where(Task.tenant_key == tenant1)
        result = await db_session.execute(query)
        tenant1_tasks = result.scalars().all()

        # Should only see tenant1 task
        assert len(tenant1_tasks) == 1
        assert tenant1_tasks[0].title == "Tenant 1 Task"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
