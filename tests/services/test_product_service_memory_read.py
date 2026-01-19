"""
Tests for ProductService reading from product_memory_entries table.

Verifies that services use ProductMemoryRepository for reads instead of JSONB.
Handover 0390b Phase 3.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.giljo_mcp.models import Product
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository


@pytest.mark.asyncio
async def test_product_memory_entries_available_via_repository(
    db_session, test_tenant_key, test_product
):
    """
    Test that memory entries can be fetched via repository and match expected structure.
    This validates the repository interface for service layer integration.
    """
    # Arrange - Create memory entries
    repo = ProductMemoryRepository()

    entries_data = [
        {
            "sequence": 1,
            "entry_type": "project_closeout",
            "source": "close_project_tool",
            "project_name": "Project Alpha",
            "summary": "Completed authentication system",
            "key_outcomes": ["Auth implemented", "Tests passing"],
            "decisions_made": ["Use JWT tokens"],
        },
        {
            "sequence": 2,
            "entry_type": "project_closeout",
            "source": "close_project_tool",
            "project_name": "Project Beta",
            "summary": "Implemented payment processing",
            "key_outcomes": ["Stripe integration", "Webhook handling"],
            "decisions_made": ["Use Stripe for payments"],
        },
    ]

    for data in entries_data:
        await repo.create_entry(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            timestamp=datetime.utcnow(),
            **data,
        )

    await db_session.commit()

    # Act - Fetch via repository
    entries = await repo.get_entries_by_product(
        session=db_session,
        product_id=test_product.id,
        tenant_key=test_tenant_key,
        include_deleted=False,
    )

    # Assert - Verify structure
    assert len(entries) == 2
    assert entries[0].sequence == 2  # Descending order
    assert entries[1].sequence == 1

    # Verify to_dict() returns compatible structure
    entry_dict = entries[0].to_dict()
    assert "sequence" in entry_dict
    assert "entry_type" in entry_dict
    assert "project_name" in entry_dict
    assert "summary" in entry_dict
    assert "key_outcomes" in entry_dict
    assert "decisions_made" in entry_dict


@pytest.mark.asyncio
async def test_get_entries_for_context_returns_lightweight_dicts(
    db_session, test_tenant_key, test_product
):
    """
    Test that get_entries_for_context returns lightweight dicts suitable for context injection.
    This is the primary interface services will use for orchestrator context.
    """
    # Arrange
    repo = ProductMemoryRepository()

    for i in range(3):
        await repo.create_entry(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            sequence=i + 1,
            entry_type="project_closeout",
            source="test",
            timestamp=datetime.utcnow(),
            project_name=f"Project {i+1}",
            summary=f"Summary {i+1}",
            key_outcomes=[f"Outcome {i+1}"],
        )

    await db_session.commit()

    # Act - Use context method
    context_entries = await repo.get_entries_for_context(
        session=db_session,
        product_id=test_product.id,
        tenant_key=test_tenant_key,
        limit=5,
    )

    # Assert
    assert len(context_entries) == 3
    assert all(isinstance(e, dict) for e in context_entries)
    assert context_entries[0]["sequence"] == 3  # Descending order


@pytest.mark.asyncio
async def test_repository_respects_include_deleted_flag(
    db_session, test_tenant_key, test_product
):
    """
    Test that repository correctly filters deleted entries.
    """
    # Arrange
    repo = ProductMemoryRepository()
    project_id = str(uuid4())

    # Create 2 entries, mark one as deleted
    entry1 = await repo.create_entry(
        session=db_session,
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        project_id=project_id,
        sequence=1,
        entry_type="project_closeout",
        source="test",
        timestamp=datetime.utcnow(),
        summary="Entry 1",
    )

    entry2 = await repo.create_entry(
        session=db_session,
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        sequence=2,
        entry_type="project_closeout",
        source="test",
        timestamp=datetime.utcnow(),
        summary="Entry 2",
    )

    await db_session.commit()

    # Mark entry1 as deleted
    await repo.mark_entries_deleted(
        session=db_session,
        project_id=project_id,
        tenant_key=test_tenant_key,
    )
    await db_session.commit()

    # Act - Fetch without deleted
    active_entries = await repo.get_entries_by_product(
        session=db_session,
        product_id=test_product.id,
        tenant_key=test_tenant_key,
        include_deleted=False,
    )

    # Act - Fetch with deleted
    all_entries = await repo.get_entries_by_product(
        session=db_session,
        product_id=test_product.id,
        tenant_key=test_tenant_key,
        include_deleted=True,
    )

    # Assert
    assert len(active_entries) == 1
    assert active_entries[0].sequence == 2

    assert len(all_entries) == 2
