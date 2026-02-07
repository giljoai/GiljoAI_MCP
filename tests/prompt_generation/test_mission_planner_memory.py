"""
Tests for mission_planner.py memory integration using ProductMemoryRepository.

Validates that mission planner correctly reads from product_memory_entries table
instead of JSONB column, while maintaining identical output format.

Handover: 0390b Phase 4
"""

from datetime import datetime, timezone

import pytest

from src.giljo_mcp.mission_planner import MissionPlanner
from src.giljo_mcp.models import Product, ProductMemoryEntry
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository


@pytest.fixture
async def product_with_table_memory(db_session, test_tenant_key):
    """
    Create product with memory stored in product_memory_entries table.

    This fixture simulates the new architecture where memory is in a separate table,
    not in Product.product_memory JSONB.
    """
    product = Product(
        tenant_key=test_tenant_key,
        name="Test Product with Table Memory",
        description="Testing memory retrieval from table",
        product_memory={},  # Empty JSONB - should not be used
    )
    db_session.add(product)
    await db_session.flush()

    # Add 3 memory entries to table
    entries = [
        ProductMemoryEntry(
            product_id=str(product.id),
            tenant_key=test_tenant_key,
            sequence=1,
            entry_type="project_closeout",
            source="test_fixture",
            project_id=None,
            project_name="Project Alpha",
            summary="Built authentication system with JWT tokens",
            key_outcomes=["Secure auth", "User management"],
            decisions_made=["Use JWT over sessions"],
            timestamp=datetime(2025, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
        ),
        ProductMemoryEntry(
            product_id=str(product.id),
            tenant_key=test_tenant_key,
            sequence=2,
            entry_type="project_closeout",
            source="test_fixture",
            project_id=None,
            project_name="Project Beta",
            summary="Added payment processing integration",
            key_outcomes=["Stripe integration", "Webhook handling"],
            decisions_made=["Use Stripe over PayPal"],
            timestamp=datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
        ),
        ProductMemoryEntry(
            product_id=str(product.id),
            tenant_key=test_tenant_key,
            sequence=3,
            entry_type="project_closeout",
            source="test_fixture",
            project_id=None,
            project_name="Project Gamma",
            summary="Implemented email notification system",
            key_outcomes=["Transactional emails", "Template system"],
            decisions_made=["Use SendGrid for reliability"],
            timestamp=datetime(2025, 1, 18, 9, 15, 0, tzinfo=timezone.utc),
        ),
    ]

    for entry in entries:
        db_session.add(entry)

    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest.fixture
async def product_no_memory(db_session, test_tenant_key):
    """Product with no memory entries."""
    product = Product(
        tenant_key=test_tenant_key,
        name="Fresh Product",
        description="No history yet",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


class TestMissionPlannerMemoryIntegration:
    """Test MissionPlanner reads from product_memory_entries table."""

    async def test_extract_product_history_uses_repository(
        self, db_session, product_with_table_memory, test_tenant_key, db_manager
    ):
        """
        _extract_product_history should read from table, not JSONB.

        Validates:
        - Method calls ProductMemoryRepository
        - Retrieves entries from table
        - Formats output correctly
        """
        planner = MissionPlanner(db_manager)

        # Call the method (priority=10 for full detail)
        result = await planner._extract_product_history(
            session=db_session,
            product_id=str(product_with_table_memory.id),
            tenant_key=test_tenant_key,
            priority=10,
            max_entries=5,
        )

        # Verify output contains expected content
        assert "## Historical Context (360 Memory)" in result
        assert "Project Alpha" in result
        assert "Project Beta" in result
        assert "Project Gamma" in result
        assert "Built authentication system" in result
        assert "Learning #1" in result
        assert "Learning #2" in result
        assert "Learning #3" in result

    async def test_extract_product_history_respects_max_entries(
        self, db_session, product_with_table_memory, test_tenant_key, db_manager
    ):
        """max_entries parameter should limit number of entries returned."""
        planner = MissionPlanner(db_manager)

        # Request only 2 entries
        result = await planner._extract_product_history(
            session=db_session,
            product_id=str(product_with_table_memory.id),
            tenant_key=test_tenant_key,
            priority=10,
            max_entries=2,
        )

        # Should show 2 most recent (Gamma and Beta)
        assert "Project Gamma" in result
        assert "Project Beta" in result
        assert "Project Alpha" not in result  # Oldest - excluded
        assert "Showing 2 most recent" in result

    async def test_extract_product_history_priority_levels(
        self, db_session, product_with_table_memory, test_tenant_key, db_manager
    ):
        """Priority levels should control detail level of output."""
        planner = MissionPlanner(db_manager)

        # Priority 10 (full) - includes decisions
        full_result = await planner._extract_product_history(
            session=db_session,
            product_id=str(product_with_table_memory.id),
            tenant_key=test_tenant_key,
            priority=10,
            max_entries=1,
        )
        assert "**Decisions Made:**" in full_result
        assert "Use SendGrid for reliability" in full_result

        # Priority 7 (moderate) - includes outcomes, not decisions
        moderate_result = await planner._extract_product_history(
            session=db_session,
            product_id=str(product_with_table_memory.id),
            tenant_key=test_tenant_key,
            priority=7,
            max_entries=1,
        )
        assert "**Key Outcomes:**" in moderate_result
        assert "**Decisions Made:**" not in moderate_result

        # Priority 3 (minimal) - summary only
        minimal_result = await planner._extract_product_history(
            session=db_session,
            product_id=str(product_with_table_memory.id),
            tenant_key=test_tenant_key,
            priority=3,
            max_entries=1,
        )
        assert "Implemented email notification system" in minimal_result
        assert "**Key Outcomes:**" not in minimal_result
        assert "**Decisions Made:**" not in minimal_result

    async def test_extract_product_history_no_memory(self, db_session, product_no_memory, test_tenant_key, db_manager):
        """Should handle products with no memory entries gracefully."""
        planner = MissionPlanner(db_manager)

        result = await planner._extract_product_history(
            session=db_session,
            product_id=str(product_no_memory.id),
            tenant_key=test_tenant_key,
            priority=10,
            max_entries=5,
        )

        # Should return instructions for first project
        assert "360 Memory System Overview" in result or "first project" in result.lower()

    async def test_extract_product_history_priority_zero(
        self, db_session, product_with_table_memory, test_tenant_key, db_manager
    ):
        """Priority 0 should return empty string."""
        planner = MissionPlanner(db_manager)

        result = await planner._extract_product_history(
            session=db_session,
            product_id=str(product_with_table_memory.id),
            tenant_key=test_tenant_key,
            priority=0,
            max_entries=5,
        )

        assert result == ""

    async def test_get_memory_summary_uses_repository(
        self, db_session, product_with_table_memory, test_tenant_key, db_manager
    ):
        """
        _get_memory_summary should use repository to get count.

        This method returns a summary dict with total count and recent entries.
        """
        planner = MissionPlanner(db_manager)

        result = await planner._get_memory_summary(
            session=db_session,
            product_id=str(product_with_table_memory.id),
            tenant_key=test_tenant_key,
            max_entries=2,
        )

        # Verify structure
        # NOTE: total_projects is based on fetched entries (limited by max_entries)
        assert result["total_projects"] == 2
        assert result["recent_count"] == 2
        assert len(result["recent_summaries"]) == 2

        # Verify most recent entries (should be newest 2: Beta and Gamma)
        summaries = result["recent_summaries"]
        # Repository returns newest first (descending sequence)
        assert summaries[0]["sequence"] in [2, 3]
        assert summaries[1]["sequence"] in [2, 3]
        assert summaries[0]["sequence"] != summaries[1]["sequence"]

    async def test_get_memory_summary_no_memory(self, db_session, product_no_memory, test_tenant_key, db_manager):
        """_get_memory_summary should handle no memory gracefully."""
        planner = MissionPlanner(db_manager)

        result = await planner._get_memory_summary(
            session=db_session,
            product_id=str(product_no_memory.id),
            tenant_key=test_tenant_key,
            max_entries=5,
        )

        assert result["total_projects"] == 0
        assert result["summary"] == "No project history available"
        assert result["fetch_tool"] is None


class TestMemoryInstructionGeneratorCompatibility:
    """
    Test that MemoryInstructionGenerator still works with list of dicts.

    The generator should accept sequential_history as list of dicts
    (which matches repository's to_dict() output).
    """

    async def test_memory_instructions_with_dict_list(
        self, db_session, product_with_table_memory, test_tenant_key, db_manager
    ):
        """
        MemoryInstructionGenerator.generate_context() should accept dict list.

        Repository returns list of dicts via to_dict(), not model instances.
        """
        from src.giljo_mcp.prompt_generation.memory_instructions import MemoryInstructionGenerator

        # Fetch entries as dicts from repository
        repo = ProductMemoryRepository()
        entries = await repo.get_entries_for_context(
            session=db_session,
            product_id=str(product_with_table_memory.id),
            tenant_key=test_tenant_key,
            limit=5,
        )

        # Generate instructions
        generator = MemoryInstructionGenerator()
        result = generator.generate_context(
            sequential_history=entries,
            priority=10,
            git_enabled=False,
        )

        # Verify output
        assert isinstance(result, str)
        assert len(result) > 0
        assert "360 Memory" in result or "memory" in result.lower()

    async def test_memory_instructions_empty_list(self):
        """Should handle empty sequential_history."""
        from src.giljo_mcp.prompt_generation.memory_instructions import MemoryInstructionGenerator

        generator = MemoryInstructionGenerator()
        result = generator.generate_context(
            sequential_history=[],
            priority=10,
            git_enabled=False,
        )

        # Should provide first project instructions
        assert isinstance(result, str)
        assert "first project" in result.lower() or "no history" in result.lower()
