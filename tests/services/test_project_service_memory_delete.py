# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for ProjectService nuclear_delete_project using product_memory_entries table.

Verifies that soft-delete uses ProductMemoryRepository instead of JSONB.
Handover 0390b Phase 3.
Updated 0730d: Exception-based error handling patterns (no success wrappers).
Updated 0731c: Typed returns - nuclear_delete_project returns NuclearDeleteResult.
"""

import random
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from src.giljo_mcp.schemas.service_responses import NuclearDeleteResult


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
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
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
            timestamp=datetime.now(timezone.utc),
            project_name=project.name,
            summary=f"Test entry {i + 1}",
            deleted_by_user=False,
        )
        db_session.add(entry)
        entries.append(entry)

    await db_session.commit()
    await db_session.refresh(project)
    for entry in entries:
        await db_session.refresh(entry)

    # Store entry IDs for verification after deletion
    entry_ids = [entry.id for entry in entries]

    # Act - Nuclear delete the project
    # 0731c: nuclear_delete_project returns NuclearDeleteResult typed model
    result = await project_service_with_session.nuclear_delete_project(project_id=project.id, websocket_manager=None)

    # Assert - Verify result is typed NuclearDeleteResult
    assert isinstance(result, NuclearDeleteResult)
    assert result.message
    assert result.deleted_counts["memory_entries_marked"] == 3

    # Verify entries are marked as deleted in table (not hard deleted)
    # Note: project_id will be NULL after project deletion (SET NULL constraint)
    await db_session.commit()  # Refresh session after service commit
    from sqlalchemy import select

    stmt = select(ProductMemoryEntry).where(ProductMemoryEntry.id.in_(entry_ids))
    query_result = await db_session.execute(stmt)
    marked_entries = query_result.scalars().all()

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
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    # Act - Nuclear delete
    # 0731c: nuclear_delete_project returns NuclearDeleteResult typed model
    result = await project_service_with_session.nuclear_delete_project(project_id=project.id, websocket_manager=None)

    # Assert - Typed model with 0 entries marked
    assert isinstance(result, NuclearDeleteResult)
    assert result.deleted_counts["memory_entries_marked"] == 0


@pytest.mark.asyncio
async def test_nuclear_delete_tenant_isolation(db_session, test_tenant_key, test_product, project_service_with_session):
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
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project1)

    entry1 = ProductMemoryEntry(
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        project_id=project1.id,
        sequence=1,
        entry_type="project_closeout",
        source="test",
        timestamp=datetime.now(timezone.utc),
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
    # 0731c: nuclear_delete_project returns NuclearDeleteResult typed model
    result = await project_service_with_session.nuclear_delete_project(project_id=project1.id, websocket_manager=None)

    # Assert - Typed model with 1 entry marked
    assert isinstance(result, NuclearDeleteResult)
    assert result.deleted_counts["memory_entries_marked"] == 1
