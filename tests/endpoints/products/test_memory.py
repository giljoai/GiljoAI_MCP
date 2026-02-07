"""
Tests for product memory entries endpoint (Handover 0490 Phase 1).

Tests ensure backend API correctly fetches 360 memory entries from
the normalized product_memory_entries table with proper tenant isolation.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text

from src.giljo_mcp.models import Product
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository
from tests.fixtures.base_fixtures import TestData


@pytest_asyncio.fixture
async def test_tenant_key() -> str:
    """Generate a test tenant key."""
    return TestData.generate_tenant_key()


@pytest_asyncio.fixture
async def test_product(db_session, test_tenant_key):
    """Create a test product."""
    product_id = str(uuid.uuid4())
    product = Product(
        id=product_id,
        tenant_key=test_tenant_key,
        name="Test Product",
        description="Test product for memory entries",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(product)
    await db_session.flush()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def second_tenant_key() -> str:
    """Generate a second tenant key for isolation testing."""
    return TestData.generate_tenant_key()


@pytest_asyncio.fixture
async def second_tenant_product(db_session, second_tenant_key):
    """Create a product for a different tenant."""
    product_id = str(uuid.uuid4())
    product = Product(
        id=product_id,
        tenant_key=second_tenant_key,
        name="Second Tenant Product",
        description="Product for tenant isolation testing",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(product)
    await db_session.flush()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def memory_repository():
    """Get ProductMemoryRepository instance."""
    return ProductMemoryRepository()


@pytest_asyncio.fixture
async def sample_memory_entries(
    db_session, test_product, test_tenant_key, memory_repository
):
    """Create sample memory entries for testing."""
    entries = []

    # Create 3 entries for different projects
    for i in range(1, 4):
        project_id = str(uuid.uuid4())
        entry = await memory_repository.create_entry(
            session=db_session,
            tenant_key=test_tenant_key,
            product_id=uuid.UUID(test_product.id),
            sequence=i,
            entry_type="project_closeout",
            source="closeout_v1",
            timestamp=datetime.now(timezone.utc),
            project_id=uuid.UUID(project_id),
            project_name=f"Test Project {i}",
            summary=f"Summary for project {i}",
            key_outcomes=[f"Outcome {i}.1", f"Outcome {i}.2"],
            decisions_made=[f"Decision {i}.1"],
            git_commits=[],
            priority=3,
            significance_score=0.5,
        )
        entries.append(entry)

    await db_session.commit()
    return entries


@pytest_asyncio.fixture
async def deleted_memory_entry(
    db_session, test_product, test_tenant_key, memory_repository
):
    """Create a deleted memory entry for testing exclusion."""
    project_id = str(uuid.uuid4())
    entry = await memory_repository.create_entry(
        session=db_session,
        tenant_key=test_tenant_key,
        product_id=uuid.UUID(test_product.id),
        sequence=99,
        entry_type="project_closeout",
        source="closeout_v1",
        timestamp=datetime.now(timezone.utc),
        project_id=uuid.UUID(project_id),
        project_name="Deleted Project",
        summary="This entry should be excluded",
    )

    # Mark as deleted
    entry.deleted_by_user = True
    entry.user_deleted_at = datetime.now(timezone.utc)
    await db_session.commit()
    await db_session.refresh(entry)
    return entry


class TestGetMemoryEntriesEndpoint:
    """Test suite for GET /api/v1/products/{product_id}/memory-entries endpoint."""

    @pytest.mark.asyncio
    async def test_get_memory_entries_success(
        self, db_session, test_product, test_tenant_key, sample_memory_entries
    ):
        """Should successfully fetch memory entries for a product."""
        # This test will use the API client once the endpoint is implemented
        # For now, we verify the repository works correctly
        repo = ProductMemoryRepository()
        entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=uuid.UUID(test_product.id),
            tenant_key=test_tenant_key,
        )

        assert len(entries) == 3
        assert entries[0].sequence == 3  # Descending order
        assert entries[1].sequence == 2
        assert entries[2].sequence == 1
        assert all(e.tenant_key == test_tenant_key for e in entries)
        assert all(e.product_id == test_product.id for e in entries)

    @pytest.mark.asyncio
    async def test_get_memory_entries_filter_by_project(
        self, db_session, test_product, test_tenant_key, sample_memory_entries
    ):
        """Should filter memory entries by project_id."""
        # Get the first entry's project_id
        target_project_id = sample_memory_entries[0].project_id

        # Filter entries by project_id (simulating API query parameter)
        stmt = text("""
            SELECT * FROM product_memory_entries
            WHERE product_id = :product_id
            AND tenant_key = :tenant_key
            AND project_id = :project_id
            AND deleted_by_user = false
            ORDER BY sequence DESC
        """)
        result = await db_session.execute(
            stmt,
            {
                "product_id": test_product.id,
                "tenant_key": test_tenant_key,
                "project_id": target_project_id,
            },
        )
        entries = result.fetchall()

        assert len(entries) == 1
        assert entries[0].project_id == target_project_id

    @pytest.mark.asyncio
    async def test_get_memory_entries_limit(
        self, db_session, test_product, test_tenant_key, sample_memory_entries
    ):
        """Should respect limit parameter."""
        repo = ProductMemoryRepository()
        entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=uuid.UUID(test_product.id),
            tenant_key=test_tenant_key,
            limit=2,
        )

        assert len(entries) == 2
        assert entries[0].sequence == 3  # Most recent first
        assert entries[1].sequence == 2

    @pytest.mark.asyncio
    async def test_get_memory_entries_tenant_isolation(
        self,
        db_session,
        test_product,
        test_tenant_key,
        second_tenant_product,
        second_tenant_key,
        sample_memory_entries,
    ):
        """Should enforce tenant isolation - no cross-tenant leakage."""
        # Create an entry for the second tenant
        repo = ProductMemoryRepository()
        await repo.create_entry(
            session=db_session,
            tenant_key=second_tenant_key,
            product_id=uuid.UUID(second_tenant_product.id),
            sequence=1,
            entry_type="project_closeout",
            source="closeout_v1",
            timestamp=datetime.now(timezone.utc),
            project_id=uuid.UUID(str(uuid.uuid4())),
            project_name="Second Tenant Project",
            summary="This should not be visible to first tenant",
        )
        await db_session.commit()

        # Query first tenant's entries
        first_tenant_entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=uuid.UUID(test_product.id),
            tenant_key=test_tenant_key,
        )

        # Query second tenant's entries
        second_tenant_entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=uuid.UUID(second_tenant_product.id),
            tenant_key=second_tenant_key,
        )

        # Verify isolation
        assert len(first_tenant_entries) == 3  # Only original entries
        assert len(second_tenant_entries) == 1  # Only new entry
        assert all(e.tenant_key == test_tenant_key for e in first_tenant_entries)
        assert all(e.tenant_key == second_tenant_key for e in second_tenant_entries)

    @pytest.mark.asyncio
    async def test_get_memory_entries_exclude_deleted(
        self,
        db_session,
        test_product,
        test_tenant_key,
        sample_memory_entries,
        deleted_memory_entry,
    ):
        """Should exclude deleted entries by default."""
        repo = ProductMemoryRepository()

        # Fetch entries without include_deleted flag
        entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=uuid.UUID(test_product.id),
            tenant_key=test_tenant_key,
            include_deleted=False,
        )

        # Should only get the 3 non-deleted entries
        assert len(entries) == 3
        assert all(not e.deleted_by_user for e in entries)
        assert deleted_memory_entry.id not in [str(e.id) for e in entries]

        # Verify deleted entry exists but is excluded
        entries_with_deleted = await repo.get_entries_by_product(
            session=db_session,
            product_id=uuid.UUID(test_product.id),
            tenant_key=test_tenant_key,
            include_deleted=True,
        )
        assert len(entries_with_deleted) == 4  # 3 + 1 deleted

    @pytest.mark.asyncio
    async def test_get_memory_entries_empty_results(
        self, db_session, test_product, test_tenant_key
    ):
        """Should return empty array when no entries exist."""
        repo = ProductMemoryRepository()
        entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=uuid.UUID(test_product.id),
            tenant_key=test_tenant_key,
        )

        assert entries == []
        assert isinstance(entries, list)

    @pytest.mark.asyncio
    async def test_get_memory_entries_invalid_product_404(
        self, db_session, test_tenant_key
    ):
        """Should return empty results for non-existent product_id."""
        # With repository pattern, non-existent product returns empty list
        # The API endpoint should return 404 if product doesn't exist
        repo = ProductMemoryRepository()
        fake_product_id = uuid.uuid4()
        entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=fake_product_id,
            tenant_key=test_tenant_key,
        )

        # Repository returns empty list (API will check if product exists first)
        assert entries == []

    @pytest.mark.asyncio
    async def test_memory_entry_to_dict_format(
        self, db_session, test_product, test_tenant_key, sample_memory_entries
    ):
        """Should convert entries to dict format matching API response schema."""
        entry = sample_memory_entries[0]
        entry_dict = entry.to_dict()

        # Verify all required fields are present
        assert "id" in entry_dict
        assert "sequence" in entry_dict
        assert "entry_type" in entry_dict
        assert "source" in entry_dict
        assert "timestamp" in entry_dict
        assert "project_id" in entry_dict
        assert "project_name" in entry_dict
        assert "summary" in entry_dict
        assert "key_outcomes" in entry_dict
        assert "decisions_made" in entry_dict
        assert "git_commits" in entry_dict
        assert "deliverables" in entry_dict
        assert "metrics" in entry_dict
        assert "priority" in entry_dict
        assert "significance_score" in entry_dict
        assert "tags" in entry_dict
        assert "deleted_by_user" in entry_dict

        # Verify data types
        assert isinstance(entry_dict["id"], str)
        assert isinstance(entry_dict["sequence"], int)
        assert isinstance(entry_dict["key_outcomes"], list)
        assert isinstance(entry_dict["decisions_made"], list)
        assert isinstance(entry_dict["git_commits"], list)
        assert isinstance(entry_dict["metrics"], dict)
        assert isinstance(entry_dict["deleted_by_user"], bool)
