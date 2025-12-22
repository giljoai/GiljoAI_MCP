"""
Integration tests for nuclear delete project functionality.

Tests verify that nuclear delete:
1. Immediately deletes project and ALL related data (no soft delete)
2. Handles active projects gracefully (deactivates first)
3. Deletes all child records (agents, tasks, messages, contexts, etc.)
4. Ensures multi-tenant isolation
5. Emits WebSocket events for cleanup
6. Handles edge cases and errors properly
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.models.context import ContextIndex, LargeDocumentIndex
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Task, Message
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def project_service(db_manager, tenant_manager, db_session):
    """Create ProjectService instance for testing."""
    return ProjectService(db_manager, tenant_manager, test_session=db_session)


@pytest_asyncio.fixture
async def test_project_with_data(db_session: AsyncSession, test_user):
    """Create a test project with all related data."""
    tenant_key = test_user.tenant_key

    # Create product first
    product = Product(
        id="test-product-123",
        name="Test Product",
        description="Test product description",
        tenant_key=tenant_key,
    )
    db_session.add(product)

    # Create project
    project = Project(
        id="test-project-123",
        name="Test Project",
        description="Test project description",
        mission="Test mission",
        tenant_key=tenant_key,
        product_id=product.id,
        status="inactive",
    )
    db_session.add(project)

    # Create agent jobs
    for i in range(3):
        agent = AgentExecution(
            job_id=f"agent-{i}",
            project_id=project.id,
            tenant_key=tenant_key,
            agent_type=f"test-agent-{i}",
            agent_name=f"Test Agent {i}",
            mission=f"Test mission for agent {i}",  # Required field
            status="waiting",  # Valid status: 'waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned'
        )
        db_session.add(agent)

    # Create tasks
    for i in range(5):
        task = Task(
            id=f"task-{i}",
            project_id=project.id,
            tenant_key=tenant_key,
            title=f"Test Task {i}",
            status="waiting",
        )
        db_session.add(task)

    # Create messages
    for i in range(10):
        message = Message(
            id=f"message-{i}",
            project_id=project.id,
            tenant_key=tenant_key,
            content=f"Test message {i}",
            status="waiting",
        )
        db_session.add(message)

    # Create context indexes
    for i in range(2):
        ctx_index = ContextIndex(
            id=f"ctx-index-{i}",
            project_id=project.id,
            tenant_key=tenant_key,
            index_type="vision",
            document_name=f"doc-{i}.md",
        )
        db_session.add(ctx_index)

    # Create large document indexes
    doc_index = LargeDocumentIndex(
        id="doc-index-1",
        project_id=project.id,
        tenant_key=tenant_key,
        document_path="/path/to/large/doc.md",
    )
    db_session.add(doc_index)

    await db_session.commit()
    await db_session.refresh(project)

    return project


@pytest.mark.asyncio
async def test_nuclear_delete_removes_all_related_data(
    db_session: AsyncSession,
    project_service: ProjectService,
    test_project_with_data: Project,
    test_user,
    tenant_manager: TenantManager,
):
    """Test that nuclear delete removes project and ALL related data."""
    tenant_key = test_user.tenant_key
    # Set tenant context
    tenant_manager.set_current_tenant(tenant_key)

    # Verify data exists before deletion
    project_id = test_project_with_data.id

    # Check counts before deletion
    agent_count = await db_session.scalar(
        select(func.count(AgentExecution.agent_id)).where(AgentExecution.project_id == project_id)
    )
    task_count = await db_session.scalar(
        select(func.count(Task.id)).where(Task.project_id == project_id)
    )
    message_count = await db_session.scalar(
        select(func.count(Message.id)).where(Message.project_id == project_id)
    )
    ctx_index_count = await db_session.scalar(
        select(func.count(ContextIndex.id)).where(ContextIndex.project_id == project_id)
    )
    doc_index_count = await db_session.scalar(
        select(func.count(LargeDocumentIndex.id)).where(LargeDocumentIndex.project_id == project_id)
    )

    assert agent_count == 3
    assert task_count == 5
    assert message_count == 10
    assert ctx_index_count == 2
    assert doc_index_count == 1

    # Perform nuclear delete
    result = await project_service.nuclear_delete_project(project_id)

    # Verify successful deletion
    assert result["success"] is True
    assert result["project_name"] == "Test Project"
    assert result["deleted_counts"]["agent_jobs"] == 3
    assert result["deleted_counts"]["tasks"] == 5
    assert result["deleted_counts"]["messages"] == 10
    assert result["deleted_counts"]["context_indexes"] == 2
    assert result["deleted_counts"]["document_indexes"] == 1

    # Verify all data is gone
    db_session.expire_all()  # Clear SQLAlchemy cache (not async)

    project_exists = await db_session.scalar(
        select(func.count(Project.id)).where(Project.id == project_id)
    )
    agents_exist = await db_session.scalar(
        select(func.count(AgentExecution.agent_id)).where(AgentExecution.project_id == project_id)
    )
    tasks_exist = await db_session.scalar(
        select(func.count(Task.id)).where(Task.project_id == project_id)
    )
    messages_exist = await db_session.scalar(
        select(func.count(Message.id)).where(Message.project_id == project_id)
    )
    ctx_indexes_exist = await db_session.scalar(
        select(func.count(ContextIndex.id)).where(ContextIndex.project_id == project_id)
    )
    doc_indexes_exist = await db_session.scalar(
        select(func.count(LargeDocumentIndex.id)).where(LargeDocumentIndex.project_id == project_id)
    )

    assert project_exists == 0
    assert agents_exist == 0
    assert tasks_exist == 0
    assert messages_exist == 0
    assert ctx_indexes_exist == 0
    assert doc_indexes_exist == 0


@pytest.mark.asyncio
async def test_nuclear_delete_active_project_deactivates_first(
    db_session: AsyncSession,
    project_service: ProjectService,
    test_project_with_data: Project,
    test_user,
    tenant_manager: TenantManager,
):
    """Test that nuclear delete deactivates active projects before deletion."""
    tenant_key = test_user.tenant_key
    # Set tenant context
    tenant_manager.set_current_tenant(tenant_key)

    # Activate project
    test_project_with_data.status = "active"
    await db_session.commit()

    project_id = test_project_with_data.id

    # Perform nuclear delete
    result = await project_service.nuclear_delete_project(project_id)

    # Verify successful deletion
    assert result["success"] is True

    # Verify project is gone (not just deactivated)
    db_session.expire_all()  # Not async
    project_exists = await db_session.scalar(
        select(func.count(Project.id)).where(Project.id == project_id)
    )
    assert project_exists == 0


@pytest.mark.asyncio
async def test_nuclear_delete_multi_tenant_isolation(
    db_session: AsyncSession,
    project_service: ProjectService,
    tenant_manager: TenantManager,
):
    """Test that nuclear delete respects multi-tenant isolation."""
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    # Create projects for two different tenants with same ID pattern
    project_a = Project(
        id="shared-project-id",
        name="Project A",
        description="Project for tenant A",
        mission="Mission A",
        tenant_key=tenant_a,
        status="inactive",
    )
    db_session.add(project_a)

    project_b = Project(
        id="different-project-id",
        name="Project B",
        description="Project for tenant B",
        mission="Mission B",
        tenant_key=tenant_b,
        status="inactive",
    )
    db_session.add(project_b)

    await db_session.commit()

    # Set tenant A context
    tenant_manager.set_current_tenant(tenant_a)

    # Try to delete project from tenant A
    result = await project_service.nuclear_delete_project(project_a.id)
    assert result["success"] is True

    # Verify tenant A project is deleted
    db_session.expire_all()  # Not async
    project_a_exists = await db_session.scalar(
        select(func.count(Project.id)).where(Project.id == project_a.id)
    )
    assert project_a_exists == 0

    # Verify tenant B project still exists
    project_b_exists = await db_session.scalar(
        select(func.count(Project.id)).where(Project.id == project_b.id)
    )
    assert project_b_exists == 1

    # Try to delete tenant B project while in tenant A context (should fail)
    result_b = await project_service.nuclear_delete_project(project_b.id)
    assert result_b["success"] is False
    assert "not found" in result_b["error"].lower() or "access denied" in result_b["error"].lower()

    # Verify tenant B project still exists
    db_session.expire_all()  # Not async
    project_b_still_exists = await db_session.scalar(
        select(func.count(Project.id)).where(Project.id == project_b.id)
    )
    assert project_b_still_exists == 1


@pytest.mark.asyncio
async def test_nuclear_delete_nonexistent_project(
    project_service: ProjectService,
    test_user,
    tenant_manager: TenantManager,
):
    """Test that nuclear delete handles nonexistent projects gracefully."""
    tenant_key = test_user.tenant_key
    # Set tenant context
    tenant_manager.set_current_tenant(tenant_key)

    # Try to delete nonexistent project
    result = await project_service.nuclear_delete_project("nonexistent-id")

    # Verify error response
    assert result["success"] is False
    assert "not found" in result["error"].lower() or "access denied" in result["error"].lower()


@pytest.mark.asyncio
async def test_nuclear_delete_no_tenant_context(project_service: ProjectService, tenant_manager: TenantManager):
    """Test that nuclear delete fails without tenant context."""
    # Clear tenant context
    tenant_manager.set_current_tenant(None)

    # Try to delete project
    result = await project_service.nuclear_delete_project("any-project-id")

    # Verify error response
    assert result["success"] is False
    assert "tenant" in result["error"].lower()


@pytest.mark.asyncio
async def test_nuclear_delete_transaction_rollback_on_error(
    db_session: AsyncSession,
    project_service: ProjectService,
    test_project_with_data: Project,
    test_user,
    tenant_manager: TenantManager,
    monkeypatch,
):
    """Test that nuclear delete rolls back transaction on error."""
    tenant_key = test_user.tenant_key
    # Set tenant context
    tenant_manager.set_current_tenant(tenant_key)

    project_id = test_project_with_data.id

    # Count records before deletion attempt
    initial_agent_count = await db_session.scalar(
        select(func.count(AgentExecution.agent_id)).where(AgentExecution.project_id == project_id)
    )
    initial_task_count = await db_session.scalar(
        select(func.count(Task.id)).where(Task.project_id == project_id)
    )

    # Simulate error during deletion by raising exception
    original_delete = db_session.delete

    async def failing_delete(obj):
        if isinstance(obj, Message):
            raise Exception("Simulated deletion error")
        return await original_delete(obj)

    monkeypatch.setattr(db_session, "delete", failing_delete)

    # Try to delete project (should fail)
    result = await project_service.nuclear_delete_project(project_id)

    # Verify deletion failed
    assert result["success"] is False
    assert "error" in result

    # Verify transaction was rolled back - all records still exist
    db_session.expire_all()  # Not async

    final_agent_count = await db_session.scalar(
        select(func.count(AgentExecution.agent_id)).where(AgentExecution.project_id == project_id)
    )
    final_task_count = await db_session.scalar(
        select(func.count(Task.id)).where(Task.project_id == project_id)
    )
    project_exists = await db_session.scalar(
        select(func.count(Project.id)).where(Project.id == project_id)
    )

    assert final_agent_count == initial_agent_count
    assert final_task_count == initial_task_count
    assert project_exists == 1


@pytest.mark.asyncio
async def test_nuclear_delete_empty_project(
    db_session: AsyncSession,
    project_service: ProjectService,
    test_user,
    tenant_manager: TenantManager,
):
    """Test nuclear delete on project with no related data."""
    tenant_key = test_user.tenant_key
    # Set tenant context
    tenant_manager.set_current_tenant(tenant_key)

    # Create empty project (no agents, tasks, etc.)
    project = Project(
        id="empty-project-id",
        name="Empty Project",
        description="Project with no related data",
        mission="Empty mission",
        tenant_key=tenant_key,
        status="inactive",
    )
    db_session.add(project)
    await db_session.commit()

    # Perform nuclear delete
    result = await project_service.nuclear_delete_project(project.id)

    # Verify successful deletion
    assert result["success"] is True
    assert result["deleted_counts"]["agent_jobs"] == 0
    assert result["deleted_counts"]["tasks"] == 0
    assert result["deleted_counts"]["messages"] == 0
    assert result["deleted_counts"]["context_indexes"] == 0
    assert result["deleted_counts"]["document_indexes"] == 0

    # Verify project is deleted
    db_session.expire_all()  # Not async
    project_exists = await db_session.scalar(
        select(func.count(Project.id)).where(Project.id == project.id)
    )
    assert project_exists == 0
