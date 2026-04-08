# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
TDD tests for ProductMemoryEntry repository (Handover 0390a).

Run with: pytest tests/repositories/test_product_memory_repository.py -v
"""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository


class TestProductMemoryRepository:
    """Tests for product memory entry CRUD operations."""

    @pytest.mark.asyncio
    async def test_model_exists(self, db_session: AsyncSession):
        """ProductMemoryEntry model should exist with all expected columns."""
        entry = ProductMemoryEntry(
            tenant_key="test_tenant",
            product_id=uuid4(),
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.utcnow(),
        )
        assert hasattr(entry, "id")
        assert hasattr(entry, "tenant_key")
        assert hasattr(entry, "product_id")
        assert hasattr(entry, "project_id")
        assert hasattr(entry, "sequence")
        assert hasattr(entry, "entry_type")
        assert hasattr(entry, "source")
        assert hasattr(entry, "summary")
        assert hasattr(entry, "key_outcomes")
        assert hasattr(entry, "decisions_made")
        assert hasattr(entry, "git_commits")
        assert hasattr(entry, "deleted_by_user")

    @pytest.mark.asyncio
    async def test_create_entry(self, db_session: AsyncSession, test_product):
        """create_entry should insert a new entry and return it."""
        repo = ProductMemoryRepository()
        entry = await repo.create_entry(
            session=db_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.utcnow(),
            summary="Test summary",
            key_outcomes=["outcome1"],
            decisions_made=["decision1"],
        )
        assert entry.id is not None
        assert entry.sequence == 1
        assert entry.summary == "Test summary"

    @pytest.mark.asyncio
    async def test_get_entries_by_product(self, db_session: AsyncSession, test_product):
        """get_entries_by_product should return paginated entries."""
        repo = ProductMemoryRepository()
        # Create 3 entries
        for i in range(3):
            await repo.create_entry(
                session=db_session,
                tenant_key="test_tenant",
                product_id=test_product.id,
                sequence=i + 1,
                entry_type="project_completion",
                source="test_v1",
                timestamp=datetime.utcnow(),
            )

        entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=test_product.id,
            tenant_key="test_tenant",
            limit=2,
        )
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_get_next_sequence(self, db_session: AsyncSession, test_product):
        """get_next_sequence should return max(sequence) + 1."""
        repo = ProductMemoryRepository()
        # Initially should be 1
        seq1 = await repo.get_next_sequence(
            session=db_session,
            product_id=test_product.id,
        )
        assert seq1 == 1

        # After creating entry, should be 2
        await repo.create_entry(
            session=db_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="test",
            source="test_v1",
            timestamp=datetime.utcnow(),
        )
        seq2 = await repo.get_next_sequence(
            session=db_session,
            product_id=test_product.id,
        )
        assert seq2 == 2

    @pytest.mark.asyncio
    async def test_mark_entries_deleted_by_project(self, db_session: AsyncSession, test_product, test_project):
        """mark_entries_deleted should soft-delete entries for a project."""
        repo = ProductMemoryRepository()
        entry = await repo.create_entry(
            session=db_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            project_id=test_project.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.utcnow(),
        )
        assert entry.deleted_by_user is False

        count = await repo.mark_entries_deleted(
            session=db_session,
            project_id=test_project.id,
            tenant_key="test_tenant",
        )
        assert count == 1

        await db_session.refresh(entry)
        assert entry.deleted_by_user is True
        assert entry.user_deleted_at is not None

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, db_session: AsyncSession, test_product):
        """Queries should only return entries for the same tenant."""
        repo = ProductMemoryRepository()
        # Create entry in tenant_a
        await repo.create_entry(
            session=db_session,
            tenant_key="tenant_a",
            product_id=test_product.id,
            sequence=1,
            entry_type="test",
            source="test_v1",
            timestamp=datetime.utcnow(),
        )

        # Query with tenant_b should return nothing
        entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=test_product.id,
            tenant_key="tenant_b",
        )
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_sequence_unique_per_product(self, db_session: AsyncSession, test_product):
        """Duplicate sequence for same product should raise error."""
        repo = ProductMemoryRepository()
        await repo.create_entry(
            session=db_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="test",
            source="test_v1",
            timestamp=datetime.utcnow(),
        )

        with pytest.raises(Exception):  # IntegrityError
            await repo.create_entry(
                session=db_session,
                tenant_key="test_tenant",
                product_id=test_product.id,
                sequence=1,  # Duplicate!
                entry_type="test",
                source="test_v1",
                timestamp=datetime.utcnow(),
            )

    @pytest.mark.asyncio
    async def test_cascade_delete_on_product(self, db_session: AsyncSession):
        """Entries should be deleted when product is deleted (CASCADE)."""
        # This test requires creating and deleting a product
        # Implementation depends on test fixtures

    @pytest.mark.asyncio
    async def test_set_null_on_project_delete(self, db_session: AsyncSession):
        """project_id should become NULL when project is deleted (SET NULL)."""
        # This test requires creating and deleting a project
        # Implementation depends on test fixtures

    @pytest.mark.asyncio
    async def test_entries_ordered_by_sequence_desc(self, db_session: AsyncSession, test_product):
        """get_entries_by_product should return entries in descending sequence order."""
        repo = ProductMemoryRepository()
        # Create entries out of order
        for seq in [3, 1, 2]:
            await repo.create_entry(
                session=db_session,
                tenant_key="test_tenant",
                product_id=test_product.id,
                sequence=seq,
                entry_type="test",
                source="test_v1",
                timestamp=datetime.utcnow(),
            )

        entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=test_product.id,
            tenant_key="test_tenant",
        )
        sequences = [e.sequence for e in entries]
        assert sequences == [3, 2, 1]  # Descending
