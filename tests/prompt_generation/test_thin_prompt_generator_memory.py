"""
Tests for thin_prompt_generator.py memory integration using ProductMemoryRepository.

Validates that thin prompt generator correctly reads from product_memory_entries table
instead of JSONB column, while maintaining identical output format.

Handover: 0390b Phase 4
"""

from datetime import datetime, timezone

import pytest

from src.giljo_mcp.models import Product, ProductMemoryEntry
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


@pytest.fixture
async def product_with_memory(db_session, test_tenant_key):
    """Product with memory in table."""
    product = Product(
        tenant_key=test_tenant_key,
        name="Memory Product",
        description="Has memory entries",
        product_memory={"context": {"objectives": ["Build MVP", "Launch beta"]}},  # Some JSONB data that's still used
    )
    db_session.add(product)
    await db_session.flush()

    # Add memory entries to table
    entries = [
        ProductMemoryEntry(
            product_id=str(product.id),
            tenant_key=test_tenant_key,
            sequence=1,
            entry_type="project_closeout",
            source="test_fixture",
            project_id=None,
            project_name="Setup Project",
            summary="Initial setup and configuration",
            key_outcomes=["Database configured", "Auth setup"],
            decisions_made=["PostgreSQL over MySQL"],
            timestamp=datetime(2025, 1, 12, 8, 0, 0, tzinfo=timezone.utc),
        ),
        ProductMemoryEntry(
            product_id=str(product.id),
            tenant_key=test_tenant_key,
            sequence=2,
            entry_type="project_closeout",
            source="test_fixture",
            project_id=None,
            project_name="Feature Development",
            summary="Core features implemented",
            key_outcomes=["User dashboard", "API endpoints"],
            decisions_made=["REST over GraphQL"],
            timestamp=datetime(2025, 1, 16, 16, 45, 0, tzinfo=timezone.utc),
        ),
    ]

    for entry in entries:
        db_session.add(entry)

    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest.fixture
async def product_no_history(db_session, test_tenant_key):
    """Product with no memory entries."""
    product = Product(
        tenant_key=test_tenant_key,
        name="New Product",
        description="Fresh start",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


class TestThinPromptGeneratorMemoryIntegration:
    """Test ThinClientPromptGenerator reads from product_memory_entries table."""

    async def test_inject_360_memory_uses_repository(self, db_session, product_with_memory, test_tenant_key):
        """
        _inject_360_memory should read from table, not JSONB.

        Validates:
        - Method calls ProductMemoryRepository
        - Retrieves entry count from table
        - Formats output correctly
        """
        generator = ThinClientPromptGenerator()

        result = await generator._inject_360_memory(
            session=db_session,
            product_id=str(product_with_memory.id),
            tenant_key=test_tenant_key,
        )

        # Verify output structure
        assert "## 360 Memory System" in result
        assert "2 previous project history entries" in result
        assert "Review these to inform decisions" in result

    async def test_inject_360_memory_no_history(self, db_session, product_no_history, test_tenant_key):
        """Should handle products with no memory entries."""
        generator = ThinClientPromptGenerator()

        result = await generator._inject_360_memory(
            session=db_session,
            product_id=str(product_no_history.id),
            tenant_key=test_tenant_key,
        )

        # Should show "no history" message
        assert "## 360 Memory System" in result
        assert "No previous project history" in result or "starting fresh" in result.lower()

    async def test_inject_360_memory_preserves_objectives(self, db_session, product_with_memory, test_tenant_key):
        """
        Should still read objectives from product_memory JSONB.

        Note: Only sequential_history moves to table. Other JSONB fields
        like context.objectives remain in JSONB for now.
        """
        generator = ThinClientPromptGenerator()

        # Pass the product model directly (for objectives access)
        # But also pass session/product_id for repository calls
        result = await generator._inject_360_memory(
            session=db_session,
            product_id=str(product_with_memory.id),
            tenant_key=test_tenant_key,
            product=product_with_memory,  # For JSONB access
        )

        # Should include objectives from JSONB
        assert "Product Objectives:" in result
        assert "Build MVP" in result
        assert "Launch beta" in result

    async def test_inject_360_memory_formats_correctly(self, db_session, product_with_memory, test_tenant_key):
        """Output format should match previous JSONB-based format."""
        generator = ThinClientPromptGenerator()

        result = await generator._inject_360_memory(
            session=db_session,
            product_id=str(product_with_memory.id),
            tenant_key=test_tenant_key,
            product=product_with_memory,
        )

        # Verify expected sections
        lines = result.split("\n")
        assert any("## 360 Memory System" in line for line in lines)
        assert any("2 previous project history entries" in line for line in lines)


class TestGitInstructionsCompatibility:
    """
    Test that git instructions still work.

    Git integration config is still in product_memory JSONB,
    not moving to table in this handover.
    """

    async def test_inject_git_instructions_unchanged(self, db_session, test_tenant_key):
        """
        _inject_git_instructions should still read from JSONB.

        Git integration is NOT part of 0390 migration - remains in JSONB.
        """
        # Create product with git integration enabled
        product = Product(
            tenant_key=test_tenant_key,
            name="Git Product",
            description="Has git integration",
            product_memory={
                "git_integration": {
                    "enabled": True,
                    "commit_limit": 25,
                    "default_branch": "main",
                }
            },
        )
        db_session.add(product)
        await db_session.commit()

        generator = ThinClientPromptGenerator()

        # This method doesn't need session/product_id - still uses JSONB
        result = generator._inject_git_instructions(product)

        # Verify git instructions present
        assert "## Git Integration" in result
        assert "git log --oneline -25 main" in result


class TestRepositoryIntegration:
    """Test direct repository usage in prompt generation."""

    async def test_repository_get_entries_for_context(self, db_session, product_with_memory, test_tenant_key):
        """Repository should return lightweight dict format for prompts."""
        repo = ProductMemoryRepository()

        entries = await repo.get_entries_for_context(
            session=db_session,
            product_id=str(product_with_memory.id),
            tenant_key=test_tenant_key,
            limit=5,
        )

        # Verify structure
        assert isinstance(entries, list)
        assert len(entries) == 2

        # Verify dict format
        entry = entries[0]
        assert isinstance(entry, dict)
        assert "sequence" in entry
        assert "project_name" in entry
        assert "summary" in entry
        assert "key_outcomes" in entry
        assert "decisions_made" in entry
        assert "timestamp" in entry

    async def test_repository_respects_tenant_isolation(self, db_session, product_with_memory, test_tenant_key):
        """Repository should filter by tenant_key."""
        # Create entry for different tenant
        other_tenant = "tenant_other"
        other_entry = ProductMemoryEntry(
            product_id=str(product_with_memory.id),
            tenant_key=other_tenant,  # Different tenant
            sequence=999,
            entry_type="project_closeout",
            source="test_fixture",
            project_id=None,
            project_name="Other Tenant Project",
            summary="Should not appear",
            timestamp=datetime.now(timezone.utc),
        )
        db_session.add(other_entry)
        await db_session.commit()

        # Query with original tenant
        repo = ProductMemoryRepository()
        entries = await repo.get_entries_for_context(
            session=db_session,
            product_id=str(product_with_memory.id),
            tenant_key=test_tenant_key,  # Original tenant
            limit=10,
        )

        # Should only return original tenant's entries
        assert len(entries) == 2  # Not 3
        project_names = [e["project_name"] for e in entries]
        assert "Other Tenant Project" not in project_names
