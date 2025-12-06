"""
Unit tests for Phase 4 Task MCP Tools - User Assignment and Task-to-Project Conversion

Tests follow TDD approach - written BEFORE implementation.

Test coverage:
- Enhanced task_create with user assignment
- project_from_task conversion tool
- list_my_tasks user-scoped filtering
- Tenant isolation enforcement
- Error handling and edge cases
"""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Product, Project, Task, User


# Fixtures


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session for tests"""
    db_manager = DatabaseManager(is_async=True)
    async with db_manager.get_session_async() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user for Phase 4 tests"""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password",
        tenant_key="tenant1",
        role="developer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create test admin user"""
    user = User(
        username="adminuser",
        email="admin@example.com",
        password_hash="hashed_password",
        tenant_key="tenant1",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_tenant_user(db_session: AsyncSession) -> User:
    """Create user from different tenant for isolation tests"""
    user = User(
        username="otheruser",
        email="other@example.com",
        password_hash="hashed_password",
        tenant_key="tenant2",
        role="developer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_product(db_session: AsyncSession, test_user: User) -> Product:
    """Create test product"""
    product = Product(name="Test Product", description="Test Description", tenant_key=test_user.tenant_key)
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_project(db_session: AsyncSession, test_user: User, test_product: Product) -> Project:
    """Create test project"""
    project = Project(
        name="Test Project", mission="Test Mission", tenant_key=test_user.tenant_key, product_id=test_product.id
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


# Test Suite for Enhanced task_create


class TestTaskCreateWithUserAssignment:
    """Test task_create with user assignment functionality"""

    @pytest.mark.asyncio
    async def test_create_task_with_user_assignment(
        self, db_session: AsyncSession, test_user: User, test_project: Project
    ):
        """Test creating task with user assignment"""
        from giljo_mcp.tools.task import create_task

        # Create task with user assignment
        result = await create_task(
            title="Test Task with Assignment",
            description="Assigned to test user",
            project_id=test_project.id,
            product_id=test_project.product_id,
            assigned_to_user_id=test_user.id,
            tenant_key=test_user.tenant_key,
        )

        assert result["success"] is True
        assert "task_id" in result

        # Verify task in database
        task = await db_session.get(Task, result["task_id"])
        assert task is not None
        assert task.title == "Test Task with Assignment"
        assert task.assigned_to_user_id == test_user.id
        assert task.created_by_user_id is None  # Not set by MCP tool
        assert task.tenant_key == test_user.tenant_key

    @pytest.mark.asyncio
    async def test_create_task_with_created_by(self, db_session: AsyncSession, test_user: User, test_project: Project):
        """Test creating task with created_by tracking"""

        # In MCP context, current_user would be available
        # For now, test direct database insertion
        task = Task(
            title="Task Created by User",
            description="Test",
            project_id=test_project.id,
            product_id=test_project.product_id,
            tenant_key=test_user.tenant_key,
            created_by_user_id=test_user.id,
            assigned_to_user_id=test_user.id,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        assert task.created_by_user_id == test_user.id
        assert task.assigned_to_user_id == test_user.id

    @pytest.mark.asyncio
    async def test_create_task_cross_tenant_assignment_fails(
        self, db_session: AsyncSession, test_user: User, other_tenant_user: User, test_project: Project
    ):
        """Test that assigning task to user in different tenant fails"""
        from giljo_mcp.tools.task import create_task

        # Try to assign task from tenant1 to user in tenant2
        result = await create_task(
            title="Cross-tenant Task",
            description="Should fail",
            project_id=test_project.id,
            product_id=test_project.product_id,
            assigned_to_user_id=other_tenant_user.id,  # Different tenant!
            tenant_key=test_user.tenant_key,
        )

        # Should fail due to tenant mismatch
        assert result["success"] is False
        assert "not found in tenant" in result["error"].lower() or "access denied" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_create_task_without_assignment(
        self, db_session: AsyncSession, test_user: User, test_project: Project
    ):
        """Test creating task without user assignment (backward compatibility)"""
        from giljo_mcp.tools.task import create_task

        result = await create_task(
            title="Unassigned Task",
            description="No user assigned",
            project_id=test_project.id,
            product_id=test_project.product_id,
            tenant_key=test_user.tenant_key,
        )

        assert result["success"] is True

        task = await db_session.get(Task, result["task_id"])
        assert task.assigned_to_user_id is None
        assert task.created_by_user_id is None


# Test Suite for project_from_task conversion


class TestProjectFromTaskConversion:
    """Test project_from_task task-to-project conversion tool"""

    @pytest.mark.asyncio
    async def test_convert_task_to_project_basic(
        self, db_session: AsyncSession, test_user: User, test_project: Project, test_product: Product
    ):
        """Test basic task-to-project conversion"""
        from giljo_mcp.tools.task import project_from_task

        # Create task to convert
        task = Task(
            title="Task to Convert",
            description="This will become a project",
            project_id=test_project.id,
            product_id=test_product.id,
            tenant_key=test_user.tenant_key,
            created_by_user_id=test_user.id,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Convert to project
        result = await project_from_task(
            task_id=task.id, project_name="Converted Project", tenant_key=test_user.tenant_key
        )

        assert result["success"] is True
        assert result["project_name"] == "Converted Project"
        assert result["original_task_id"] == task.id
        assert "project_id" in result

        # Verify project created
        project = await db_session.get(Project, result["project_id"])
        assert project is not None
        assert project.name == "Converted Project"
        assert project.mission == task.description
        assert project.product_id == task.product_id

        # Verify task marked as converted
        await db_session.refresh(task)
        assert task.status == "converted"
        assert task.meta_data.get("converted_to_project") == result["project_id"]

    @pytest.mark.asyncio
    async def test_convert_task_uses_task_title_if_no_name_provided(
        self, db_session: AsyncSession, test_user: User, test_project: Project, test_product: Product
    ):
        """Test conversion uses task title when project name not provided"""
        from giljo_mcp.tools.task import project_from_task

        task = Task(
            title="Auto-Named Project",
            description="Default project name test",
            project_id=test_project.id,
            product_id=test_product.id,
            tenant_key=test_user.tenant_key,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        result = await project_from_task(task_id=task.id, tenant_key=test_user.tenant_key)

        assert result["success"] is True
        assert result["project_name"] == "Auto-Named Project"

    @pytest.mark.asyncio
    async def test_convert_already_converted_task_fails(
        self, db_session: AsyncSession, test_user: User, test_project: Project, test_product: Product
    ):
        """Test that converting already converted task fails"""
        from giljo_mcp.tools.task import project_from_task

        task = Task(
            title="Already Converted",
            description="Test",
            project_id=test_project.id,
            product_id=test_product.id,
            tenant_key=test_user.tenant_key,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # First conversion
        result1 = await project_from_task(task_id=task.id, tenant_key=test_user.tenant_key)
        assert result1["success"] is True

        # Second conversion should fail
        result2 = await project_from_task(task_id=task.id, tenant_key=test_user.tenant_key)
        assert result2["success"] is False
        assert "already converted" in result2["error"].lower()

    @pytest.mark.asyncio
    async def test_convert_task_with_subtasks(
        self, db_session: AsyncSession, test_user: User, test_project: Project, test_product: Product
    ):
        """Test converting task with subtasks includes them"""
        from giljo_mcp.tools.task import project_from_task

        # Parent task
        parent_task = Task(
            title="Parent Task",
            description="Has subtasks",
            project_id=test_project.id,
            product_id=test_product.id,
            tenant_key=test_user.tenant_key,
        )
        db_session.add(parent_task)
        await db_session.flush()

        # Subtasks
        subtask1 = Task(
            title="Subtask 1",
            description="Sub 1",
            project_id=test_project.id,
            product_id=test_product.id,
            tenant_key=test_user.tenant_key,
            parent_task_id=parent_task.id,
        )
        subtask2 = Task(
            title="Subtask 2",
            description="Sub 2",
            project_id=test_project.id,
            product_id=test_product.id,
            tenant_key=test_user.tenant_key,
            parent_task_id=parent_task.id,
        )
        db_session.add_all([subtask1, subtask2])
        await db_session.commit()
        await db_session.refresh(parent_task)

        # Convert with subtasks
        result = await project_from_task(
            task_id=parent_task.id, include_subtasks=True, conversion_strategy="single", tenant_key=test_user.tenant_key
        )

        assert result["success"] is True
        assert len(result.get("converted_subtasks", [])) == 2

    @pytest.mark.asyncio
    async def test_convert_task_tenant_isolation(
        self, db_session: AsyncSession, test_user: User, other_tenant_user: User, test_project: Project
    ):
        """Test tenant isolation in task conversion"""
        from giljo_mcp.tools.task import project_from_task

        # Create task in tenant1
        task = Task(
            title="Tenant 1 Task", description="Test", project_id=test_project.id, tenant_key=test_user.tenant_key
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        # Try to convert from tenant2
        result = await project_from_task(task_id=task.id, tenant_key=other_tenant_user.tenant_key)

        assert result["success"] is False
        assert "not found" in result["error"].lower()


# Test Suite for list_my_tasks filtering


class TestListMyTasks:
    """Test list_my_tasks user-scoped task filtering"""

    @pytest.mark.asyncio
    async def test_list_assigned_tasks(
        self, db_session: AsyncSession, test_user: User, test_admin: User, test_project: Project
    ):
        """Test listing tasks assigned to current user"""
        from giljo_mcp.tools.task import list_my_tasks

        # Create tasks
        task1 = Task(
            title="Assigned to me",
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            assigned_to_user_id=test_user.id,
        )
        task2 = Task(
            title="Assigned to admin",
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            assigned_to_user_id=test_admin.id,
        )
        task3 = Task(title="Unassigned", project_id=test_project.id, tenant_key=test_user.tenant_key)
        db_session.add_all([task1, task2, task3])
        await db_session.commit()

        # List assigned tasks for test_user
        result = await list_my_tasks(
            filter_type="assigned", tenant_key=test_user.tenant_key, current_user_id=test_user.id
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["tasks"][0]["title"] == "Assigned to me"
        assert result["filter_type"] == "assigned"

    @pytest.mark.asyncio
    async def test_list_created_tasks(
        self, db_session: AsyncSession, test_user: User, test_admin: User, test_project: Project
    ):
        """Test listing tasks created by current user"""
        from giljo_mcp.tools.task import list_my_tasks

        task1 = Task(
            title="Created by me",
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            created_by_user_id=test_user.id,
        )
        task2 = Task(
            title="Created by admin",
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            created_by_user_id=test_admin.id,
        )
        db_session.add_all([task1, task2])
        await db_session.commit()

        result = await list_my_tasks(
            filter_type="created", tenant_key=test_user.tenant_key, current_user_id=test_user.id
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["tasks"][0]["title"] == "Created by me"

    @pytest.mark.asyncio
    async def test_list_all_my_tasks(self, db_session: AsyncSession, test_user: User, test_project: Project):
        """Test listing all tasks (assigned OR created by user)"""
        from giljo_mcp.tools.task import list_my_tasks

        task1 = Task(
            title="Assigned to me",
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            assigned_to_user_id=test_user.id,
        )
        task2 = Task(
            title="Created by me",
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            created_by_user_id=test_user.id,
        )
        task3 = Task(
            title="Both",
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            assigned_to_user_id=test_user.id,
            created_by_user_id=test_user.id,
        )
        task4 = Task(title="Someone else's", project_id=test_project.id, tenant_key=test_user.tenant_key)
        db_session.add_all([task1, task2, task3, task4])
        await db_session.commit()

        result = await list_my_tasks(filter_type="all", tenant_key=test_user.tenant_key, current_user_id=test_user.id)

        assert result["success"] is True
        assert result["count"] == 3  # task1, task2, task3

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(
        self, db_session: AsyncSession, test_user: User, test_project: Project
    ):
        """Test filtering by status"""
        from giljo_mcp.tools.task import list_my_tasks

        task1 = Task(
            title="Pending task",
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            assigned_to_user_id=test_user.id,
            status="waiting",
        )
        task2 = Task(
            title="In progress task",
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            assigned_to_user_id=test_user.id,
            status="in_progress",
        )
        db_session.add_all([task1, task2])
        await db_session.commit()

        result = await list_my_tasks(
            filter_type="assigned", status="waiting", tenant_key=test_user.tenant_key, current_user_id=test_user.id
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["tasks"][0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_tasks_tenant_isolation(
        self, db_session: AsyncSession, test_user: User, other_tenant_user: User, test_project: Project
    ):
        """Test tenant isolation in task listing"""
        from giljo_mcp.tools.task import list_my_tasks

        # Create task in test_user's tenant
        task1 = Task(
            title="Tenant 1 task",
            project_id=test_project.id,
            tenant_key=test_user.tenant_key,
            assigned_to_user_id=test_user.id,
        )
        db_session.add(task1)
        await db_session.commit()

        # Query from other tenant
        result = await list_my_tasks(
            filter_type="assigned", tenant_key=other_tenant_user.tenant_key, current_user_id=other_tenant_user.id
        )

        # Should not see task from different tenant
        assert result["success"] is True
        assert result["count"] == 0


# Integration Tests


class TestPhase4Integration:
    """Integration tests for Phase 4 features"""

    @pytest.mark.asyncio
    async def test_full_workflow_create_assign_convert(
        self, db_session: AsyncSession, test_user: User, test_admin: User, test_project: Project, test_product: Product
    ):
        """Test complete workflow: create task → assign → convert to project"""
        from giljo_mcp.tools.task import create_task, list_my_tasks, project_from_task

        # Step 1: Create task
        create_result = await create_task(
            title="Feature Request: Dark Mode",
            description="Implement dark mode toggle",
            project_id=test_project.id,
            product_id=test_product.id,
            assigned_to_user_id=test_user.id,
            tenant_key=test_user.tenant_key,
        )
        assert create_result["success"] is True
        task_id = create_result["task_id"]

        # Step 2: Verify in user's task list
        list_result = await list_my_tasks(
            filter_type="assigned", tenant_key=test_user.tenant_key, current_user_id=test_user.id
        )
        assert list_result["count"] >= 1
        assert any(t["id"] == task_id for t in list_result["tasks"])

        # Step 3: Convert to project
        convert_result = await project_from_task(
            task_id=task_id, project_name="Dark Mode Implementation", tenant_key=test_user.tenant_key
        )
        assert convert_result["success"] is True
        assert convert_result["project_name"] == "Dark Mode Implementation"

        # Step 4: Verify task marked as converted
        task = await db_session.get(Task, task_id)
        assert task.status == "converted"
        assert task.meta_data.get("converted_to_project") == convert_result["project_id"]
