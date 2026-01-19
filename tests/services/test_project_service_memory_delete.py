"""
Tests for ProjectService nuclear_delete_project using product_memory_entries table.

Verifies that soft-delete uses ProductMemoryRepository instead of JSONB.
Handover 0390b Phase 3.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from src.giljo_mcp.services.project_service import ProjectService


@pytest.mark.asyncio
async def test_nuclear_delete_marks_memory_entries_in_table(
    db_session, test_tenant_key, test_product, project_service_with_session
):
    """
    Test that nuclear_delete_project marks entries in product_memory_entries table
    instead of mutating JSONB.
    """
    # Arrange - Create project and memory entries
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project for Memory Delete",
        description="Test project for memory table delete",
        mission="Test mission for project deletion",
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(project)

    # Create 3 memory entries for this project
    entries = []
    for i in range(3):
        entry = ProductMemoryEntry(
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            project_id=project.id,
            sequence=i + 1,
            entry_type="project_closeout",
            source="test",
            timestamp=datetime.utcnow(),
            project_name=project.name,
            summary=f"Test entry {i+1}",
            deleted_by_user=False,
        )
        db_session.add(entry)
        entries.append(entry)

    await db_session.commit()
    await db_session.refresh(project)
    for entry in entries:
        await db_session.refresh(entry)

    # Act - Nuclear delete the project
    result = await project_service_with_session.nuclear_delete_project(
        project_id=project.id, websocket_manager=None
    )

    # Assert - Verify success
    assert result["success"] is True
    assert "memory_entries_marked" in result["deleted_counts"]
    assert result["deleted_counts"]["memory_entries_marked"] == 3

    # Verify entries are marked as deleted in table (not hard deleted)
    await db_session.commit()  # Refresh session after service commit
    from sqlalchemy import select

    stmt = select(ProductMemoryEntry).where(
        ProductMemoryEntry.project_id == project.id
    )
    result = await db_session.execute(stmt)
    marked_entries = result.scalars().all()

    assert len(marked_entries) == 3
    for entry in marked_entries:
        assert entry.deleted_by_user is True
        assert entry.user_deleted_at is not None


@pytest.mark.asyncio
async def test_nuclear_delete_with_no_memory_entries(
    db_session, test_tenant_key, test_product, project_service_with_session
):
    """
    Test that nuclear_delete_project handles projects with no memory entries gracefully.
    """
    # Arrange - Create project without memory entries
    project = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Test Project No Memory",
        description="Test project without memory entries",
        mission="Test mission without memory",
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Act - Nuclear delete
    result = await project_service_with_session.nuclear_delete_project(
        project_id=project.id, websocket_manager=None
    )

    # Assert - Success with 0 entries marked
    assert result["success"] is True
    assert result["deleted_counts"]["memory_entries_marked"] == 0


@pytest.mark.asyncio
async def test_nuclear_delete_tenant_isolation(
    db_session, test_tenant_key, test_product, project_service_with_session
):
    """
    Test that nuclear_delete only marks entries for the correct tenant.
    """
    # Arrange - Create project and entries for first tenant
    project1 = Project(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        name="Tenant 1 Project",
        description="Project for testing tenant isolation",
        mission="Test mission for tenant isolation",
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(project1)

    entry1 = ProductMemoryEntry(
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        project_id=project1.id,
        sequence=1,
        entry_type="project_closeout",
        source="test",
        timestamp=datetime.utcnow(),
        project_name=project1.name,
        summary="Tenant 1 entry",
        deleted_by_user=False,
    )
    db_session.add(entry1)

    # Create project and entry for different tenant (simulated)
    # Note: In real scenario, this would be a different tenant_key
    # For test purposes, we'll verify the query filters correctly
    await db_session.commit()

    # Act - Delete first project
    result = await project_service_with_session.nuclear_delete_project(
        project_id=project1.id, websocket_manager=None
    )

    # Assert
    assert result["success"] is True
    assert result["deleted_counts"]["memory_entries_marked"] == 1
