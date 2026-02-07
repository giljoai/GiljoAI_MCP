"""
Integration tests for context tools reading from product_memory_entries table.

Handover 0390b Phase 2: Verify get_360_memory and get_git_history use ProductMemoryRepository.
"""

import uuid
from datetime import datetime, timezone

import pytest_asyncio

from src.giljo_mcp.models import Product
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository
from src.giljo_mcp.tools.context_tools.get_360_memory import get_360_memory
from src.giljo_mcp.tools.context_tools.get_git_history import get_git_history


@pytest_asyncio.fixture(scope="function")
async def test_product_with_table_data(db_manager, db_session):
    """
    Create a test product with memory entries in the table (NOT in JSONB).

    This fixture:
    1. Creates a product with git integration enabled
    2. Creates 5 memory entries in product_memory_entries table
    3. Does NOT populate product.product_memory.sequential_history (deprecated)
    """
    tenant_key = f"tenant_{uuid.uuid4().hex[:8]}"
    product_id = str(uuid.uuid4())

    # Create product with git integration enabled (still in JSONB)
    product = Product(
        id=product_id,
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product with table-based memory",
        product_memory={
            "git_integration": {"enabled": True, "repo_url": "https://github.com/test/repo"}
            # Note: sequential_history is DEPRECATED - not populated
        },
    )
    db_session.add(product)
    await db_session.flush()

    # Create 5 memory entries in the TABLE (normalized storage)
    repo = ProductMemoryRepository()
    entries = []

    for i in range(1, 6):
        entry = await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=uuid.UUID(product_id),  # Convert string to UUID (repository expects UUID)
            sequence=i,
            entry_type="project_closeout",
            source="test_fixture",
            timestamp=datetime(2025, 1, i, 10, 0, 0, tzinfo=timezone.utc),
            project_name=f"Project {i}",
            summary=f"Summary of project {i} work",
            key_outcomes=[f"Outcome {i}.1", f"Outcome {i}.2"],
            decisions_made=[f"Decision {i}.1"],
            git_commits=[
                {
                    "sha": f"abc{i}23",
                    "message": f"feat: Add feature {i}",
                    "author": "test@example.com",
                    "date": f"2025-01-{i:02d}T10:00:00Z",
                }
            ]
            if i <= 3
            else [],  # Only first 3 have commits
            priority=3,
            significance_score=0.5,
            token_estimate=100 * i,
        )
        entries.append(entry)

    await db_session.flush()  # Flush but don't commit - keeps data in transaction
    await db_session.refresh(product)

    yield {
        "product": product,
        "entries": entries,
        "tenant_key": tenant_key,
        "product_id": product_id,
        "session": db_session,  # Pass session for tools to use
    }


class Test360MemoryReadsFromTable:
    """Test get_360_memory reads from product_memory_entries table."""

    async def test_get_360_memory_uses_repository(self, db_manager, test_product_with_table_data):
        """Verify get_360_memory returns data from table, not JSONB."""
        data = test_product_with_table_data

        # Call the tool (pass session for test isolation)
        result = await get_360_memory(
            product_id=data["product_id"],
            tenant_key=data["tenant_key"],
            last_n_projects=3,
            session=data["session"],
        )

        # Verify response structure
        assert result["source"] == "360_memory"
        assert result["depth"] == 3
        assert len(result["data"]) == 3
        assert result["metadata"]["total_projects"] == 5
        assert result["metadata"]["returned_projects"] == 3

        # Verify data comes from table (sorted by sequence DESC)
        assert result["data"][0]["sequence"] == 5
        assert result["data"][1]["sequence"] == 4
        assert result["data"][2]["sequence"] == 3

        # Verify data structure matches JSONB format (backward compatible)
        first_entry = result["data"][0]
        assert "sequence" in first_entry
        assert "project_name" in first_entry
        assert "summary" in first_entry
        assert "key_outcomes" in first_entry
        assert "decisions_made" in first_entry
        assert "git_commits" in first_entry

    async def test_get_360_memory_pagination(self, db_manager, test_product_with_table_data):
        """Verify pagination works correctly."""
        data = test_product_with_table_data

        # Fetch first 2 projects
        result1 = await get_360_memory(
            product_id=data["product_id"],
            tenant_key=data["tenant_key"],
            last_n_projects=5,
            offset=0,
            limit=2,
            session=data["session"],
        )

        assert len(result1["data"]) == 2
        assert result1["data"][0]["sequence"] == 5
        assert result1["data"][1]["sequence"] == 4
        assert result1["metadata"]["has_more"] is True
        assert result1["metadata"]["next_offset"] == 2

        # Fetch next 2 projects
        result2 = await get_360_memory(
            product_id=data["product_id"],
            tenant_key=data["tenant_key"],
            last_n_projects=5,
            offset=2,
            limit=2,
            session=data["session"],
        )

        assert len(result2["data"]) == 2
        assert result2["data"][0]["sequence"] == 3
        assert result2["data"][1]["sequence"] == 2

    async def test_get_360_memory_empty_table(self, db_manager, db_session):
        """Verify behavior when table is empty."""
        tenant_key = f"tenant_{uuid.uuid4().hex[:8]}"
        product_id = str(uuid.uuid4())

        # Create product with empty memory
        product = Product(
            id=product_id,
            tenant_key=tenant_key,
            name="Empty Product",
            description="Product with no memory",
            product_memory={},
        )
        db_session.add(product)
        await db_session.flush()

        # Call the tool (pass session for test isolation)
        result = await get_360_memory(
            product_id=product_id,
            tenant_key=tenant_key,
            last_n_projects=3,
            session=db_session,
        )

        # Verify empty response
        assert result["source"] == "360_memory"
        assert result["data"] == []
        assert result["metadata"]["total_projects"] == 0
        assert result["metadata"]["returned_projects"] == 0

    async def test_get_360_memory_tenant_isolation(self, db_manager, test_product_with_table_data):
        """Verify tenant isolation - wrong tenant gets no data."""
        data = test_product_with_table_data

        # Try with wrong tenant_key
        result = await get_360_memory(
            product_id=data["product_id"],
            tenant_key="wrong_tenant",
            last_n_projects=3,
            session=data["session"],
        )

        # Verify product not found (tenant mismatch)
        assert result["data"] == []
        assert result["metadata"]["error"] == "product_not_found"


class TestGitHistoryReadsFromTable:
    """Test get_git_history reads from product_memory_entries table."""

    async def test_get_git_history_uses_repository(self, db_manager, test_product_with_table_data):
        """Verify get_git_history returns data from table, not JSONB."""
        data = test_product_with_table_data

        # Call the tool
        result = await get_git_history(
            product_id=data["product_id"],
            tenant_key=data["tenant_key"],
            commits=25,
            session=data["session"],
        )

        # Verify response structure
        assert result["source"] == "git_history"
        assert result["depth"] == 25
        assert result["metadata"]["git_integration_enabled"] is True

        # Verify commits from table (only first 3 entries have commits)
        assert len(result["data"]) == 3
        assert result["metadata"]["total_commits"] == 3
        assert result["metadata"]["returned_commits"] == 3

        # Verify commits are sorted newest first
        assert result["data"][0]["sha"] == "abc323"
        assert result["data"][1]["sha"] == "abc223"
        assert result["data"][2]["sha"] == "abc123"

    async def test_get_git_history_disabled_integration(self, db_manager, db_session):
        """Verify behavior when git integration is disabled."""
        tenant_key = f"tenant_{uuid.uuid4().hex[:8]}"
        product_id = str(uuid.uuid4())

        # Create product with git disabled
        product = Product(
            id=product_id,
            tenant_key=tenant_key,
            name="No Git Product",
            description="Product with git disabled",
            product_memory={"git_integration": {"enabled": False}},
        )
        db_session.add(product)
        await db_session.flush()

        # Call the tool (pass session for test isolation)
        result = await get_git_history(
            product_id=product_id,
            tenant_key=tenant_key,
            commits=25,
            session=db_session,
        )

        # Verify empty response
        assert result["source"] == "git_history"
        assert result["data"] == []
        assert result["metadata"]["git_integration_enabled"] is False
        assert result["metadata"]["reason"] == "git_integration_disabled"

    async def test_get_git_history_limit(self, db_manager, test_product_with_table_data):
        """Verify commit limit works correctly."""
        data = test_product_with_table_data

        # Request only 2 commits
        result = await get_git_history(
            product_id=data["product_id"],
            tenant_key=data["tenant_key"],
            commits=2,
            session=data["session"],
        )

        # Should return 2 most recent commits
        assert len(result["data"]) == 2
        assert result["data"][0]["sha"] == "abc323"
        assert result["data"][1]["sha"] == "abc223"

    async def test_get_git_history_no_commits(self, db_manager, db_session):
        """Verify behavior when entries exist but have no commits."""
        tenant_key = f"tenant_{uuid.uuid4().hex[:8]}"
        product_id = str(uuid.uuid4())

        # Create product with git enabled
        product = Product(
            id=product_id,
            tenant_key=tenant_key,
            name="No Commits Product",
            description="Product with entries but no commits",
            product_memory={"git_integration": {"enabled": True}},
        )
        db_session.add(product)
        await db_session.flush()

        # Create entry without git commits
        repo = ProductMemoryRepository()
        await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=uuid.UUID(product_id),  # Repository expects UUID
            sequence=1,
            entry_type="project_closeout",
            source="test",
            timestamp=datetime.now(timezone.utc),
            project_name="Project 1",
            summary="Summary",
            git_commits=[],  # Empty commits
        )
        await db_session.flush()

        # Call the tool (pass session for test isolation)
        result = await get_git_history(
            product_id=product_id,
            tenant_key=tenant_key,
            commits=25,
            session=db_session,
        )

        # Verify empty commits response
        assert result["source"] == "git_history"
        assert result["data"] == []
        assert result["metadata"]["total_commits"] == 0
        assert result["metadata"]["git_integration_enabled"] is True

    async def test_get_git_history_tenant_isolation(self, db_manager, test_product_with_table_data):
        """Verify tenant isolation - wrong tenant gets no data."""
        data = test_product_with_table_data

        # Try with wrong tenant_key (pass session for test isolation)
        result = await get_git_history(
            product_id=data["product_id"],
            tenant_key="wrong_tenant",
            commits=25,
            session=data["session"],
        )

        # Verify product not found (tenant mismatch)
        assert result["data"] == []
        assert result["metadata"]["error"] == "product_not_found"


class TestBackwardCompatibility:
    """Test that response formats remain backward compatible."""

    async def test_360_memory_response_format(self, db_manager, test_product_with_table_data):
        """Verify get_360_memory returns same format as before (JSONB era)."""
        data = test_product_with_table_data

        result = await get_360_memory(
            product_id=data["product_id"],
            tenant_key=data["tenant_key"],
            last_n_projects=1,
            session=data["session"],  # Pass session for test isolation
        )

        # Verify all expected keys exist
        assert "source" in result
        assert "depth" in result
        assert "data" in result
        assert "metadata" in result

        # Verify metadata keys
        metadata = result["metadata"]
        assert "product_id" in metadata
        assert "tenant_key" in metadata
        assert "total_projects" in metadata
        assert "last_n_projects" in metadata
        assert "offset" in metadata
        assert "limit" in metadata
        assert "returned_projects" in metadata
        assert "has_more" in metadata
        assert "next_offset" in metadata

        # Verify data entry keys (matches JSONB format)
        if result["data"]:
            entry = result["data"][0]
            assert "sequence" in entry
            assert "type" in entry
            assert "project_name" in entry
            assert "summary" in entry
            assert "key_outcomes" in entry
            assert "decisions_made" in entry
            assert "git_commits" in entry

    async def test_git_history_response_format(self, db_manager, test_product_with_table_data):
        """Verify get_git_history returns same format as before (JSONB era)."""
        data = test_product_with_table_data

        result = await get_git_history(
            product_id=data["product_id"],
            tenant_key=data["tenant_key"],
            commits=25,
            session=data["session"],  # Pass session for test isolation
        )

        # Verify all expected keys exist
        assert "source" in result
        assert "depth" in result
        assert "data" in result
        assert "metadata" in result

        # Verify metadata keys
        metadata = result["metadata"]
        assert "product_id" in metadata
        assert "tenant_key" in metadata
        assert "total_commits" in metadata
        assert "returned_commits" in metadata
        assert "git_integration_enabled" in metadata

        # Verify commit format
        if result["data"]:
            commit = result["data"][0]
            assert "sha" in commit
            assert "message" in commit
            assert "author" in commit
            assert "date" in commit
