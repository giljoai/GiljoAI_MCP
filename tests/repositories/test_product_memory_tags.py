# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
TDD tests for 360 Memory Action Tags feature.

Tests cover:
1. Write path: tags parameter on write_360_memory
2. Read path: get_entries_by_tag_prefix repository method
3. Resolve path: tag clearing via complete_job
4. Validation: invalid tags rejected cleanly

Run with: pytest tests/repositories/test_product_memory_tags.py -v
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository


class TestWriteTagsPersistence:
    """WI-1: Tags are persisted when writing 360 memory entries."""

    @pytest.mark.asyncio
    async def test_write_360_memory_with_tags(self, db_session: AsyncSession, test_product):
        """Write entry with tags, verify tags persisted."""
        repo = ProductMemoryRepository()
        tags = ["action_required:fix auth regression", "priority:high"]

        entry = await repo.create_entry(
            session=db_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Test summary with tags",
            key_outcomes=["outcome1"],
            decisions_made=["decision1"],
            tags=tags,
        )
        assert entry.tags == tags
        assert len(entry.tags) == 2
        assert "action_required:fix auth regression" in entry.tags

    @pytest.mark.asyncio
    async def test_write_360_memory_without_tags_defaults_empty(self, db_session: AsyncSession, test_product):
        """Write entry without tags defaults to empty list."""
        repo = ProductMemoryRepository()
        entry = await repo.create_entry(
            session=db_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="No tags entry",
        )
        assert entry.tags == []


class TestTagsValidation:
    """WI-1: Tags input validation (untrusted agent input)."""

    @pytest.mark.asyncio
    async def test_tags_validation_too_many(self):
        """More than 10 tags raises ValidationError."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        tags = [f"tag_{i}" for i in range(11)]
        with pytest.raises(ValidationError, match="maximum 10 tags"):
            _validate_tags(tags)

    @pytest.mark.asyncio
    async def test_tags_validation_too_long(self):
        """Tag exceeding 200 chars raises ValidationError."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        tags = ["a" * 201]
        with pytest.raises(ValidationError, match="200 characters"):
            _validate_tags(tags)

    @pytest.mark.asyncio
    async def test_tags_validation_wrong_type(self):
        """Non-string items in tags raises ValidationError."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        with pytest.raises(ValidationError, match="must be strings"):
            _validate_tags([123, "valid_tag"])

    @pytest.mark.asyncio
    async def test_tags_validation_valid(self):
        """Valid tags pass validation without error."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        tags = ["action_required:fix bug", "priority:high"]
        result = _validate_tags(tags)
        assert result == tags

    @pytest.mark.asyncio
    async def test_tags_validation_none_returns_empty(self):
        """None tags returns empty list."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        assert _validate_tags(None) == []


class TestGetEntriesByTagPrefix:
    """WI-2: Repository method for fetching entries by tag prefix."""

    @pytest.mark.asyncio
    async def test_get_entries_by_tag_prefix(self, db_session: AsyncSession, test_product):
        """Repo method returns only entries with matching tag prefix."""
        repo = ProductMemoryRepository()
        tenant_key = "test_tenant"

        # Entry with action_required tag
        await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Has action tag",
            tags=["action_required:fix auth", "other:tag"],
        )

        # Entry without action_required tag
        await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=test_product.id,
            sequence=2,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="No action tag",
            tags=["priority:high"],
        )

        # Entry with no tags
        await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=test_product.id,
            sequence=3,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Empty tags",
            tags=[],
        )

        results = await repo.get_entries_by_tag_prefix(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key=tenant_key,
            prefix="action_required",
        )
        assert len(results) == 1
        assert results[0].summary == "Has action tag"

    @pytest.mark.asyncio
    async def test_get_entries_by_tag_prefix_tenant_isolation(self, db_session: AsyncSession, test_product):
        """Tag prefix query must respect tenant isolation."""
        repo = ProductMemoryRepository()

        # Create entry with correct tenant
        await repo.create_entry(
            session=db_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Correct tenant",
            tags=["action_required:fix bug"],
        )

        # Query with wrong tenant
        results = await repo.get_entries_by_tag_prefix(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key="wrong_tenant",
            prefix="action_required",
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_entries_by_tag_prefix_excludes_deleted(self, db_session: AsyncSession, test_product):
        """Soft-deleted entries excluded by default."""
        repo = ProductMemoryRepository()
        tenant_key = "test_tenant"

        entry = await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Deleted entry",
            tags=["action_required:fix bug"],
        )
        # Soft-delete the entry
        entry.deleted_by_user = True
        await db_session.flush()

        results = await repo.get_entries_by_tag_prefix(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key=tenant_key,
            prefix="action_required",
        )
        assert len(results) == 0

        # With include_deleted=True
        results_with_deleted = await repo.get_entries_by_tag_prefix(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key=tenant_key,
            prefix="action_required",
            include_deleted=True,
        )
        assert len(results_with_deleted) == 1


class TestResolveActionTags:
    """WI-3: Tag clearing via resolve_action_tags."""

    @pytest.mark.asyncio
    async def test_resolve_action_tags_clears_matching(self, db_session: AsyncSession, test_product):
        """Resolving action items clears matching action_required tags."""
        repo = ProductMemoryRepository()
        tenant_key = "test_tenant"

        await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Entry with tags",
            tags=[
                "action_required:fix auth regression",
                "action_required:update docs",
                "priority:high",
            ],
        )

        count = await repo.resolve_action_tags(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key=tenant_key,
            resolved_items=["fix auth regression"],
        )
        assert count == 1

        # Verify the tag was removed but others remain
        entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=test_product.id,
            tenant_key=tenant_key,
        )
        assert len(entries) == 1
        remaining_tags = entries[0].tags
        assert "action_required:fix auth regression" not in remaining_tags
        assert "action_required:update docs" in remaining_tags
        assert "priority:high" in remaining_tags

    @pytest.mark.asyncio
    async def test_resolve_action_tags_case_insensitive(self, db_session: AsyncSession, test_product):
        """Resolution matching is case-insensitive substring match."""
        repo = ProductMemoryRepository()
        tenant_key = "test_tenant"

        await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Case test",
            tags=["action_required:Fix Auth Regression"],
        )

        count = await repo.resolve_action_tags(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key=tenant_key,
            resolved_items=["fix auth regression"],
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_resolve_action_tags_no_match_unchanged(self, db_session: AsyncSession, test_product):
        """When no tags match, nothing changes."""
        repo = ProductMemoryRepository()
        tenant_key = "test_tenant"

        await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="No match",
            tags=["action_required:fix auth regression"],
        )

        count = await repo.resolve_action_tags(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key=tenant_key,
            resolved_items=["something completely different"],
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_resolve_action_tags_tenant_isolation(self, db_session: AsyncSession, test_product):
        """Resolve only affects entries for the correct tenant."""
        repo = ProductMemoryRepository()

        await repo.create_entry(
            session=db_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Correct tenant",
            tags=["action_required:fix bug"],
        )

        count = await repo.resolve_action_tags(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key="wrong_tenant",
            resolved_items=["fix bug"],
        )
        assert count == 0


class TestTagsValidationEdgeCases:
    """Additional edge-case tests for tags validation."""

    @pytest.mark.asyncio
    async def test_tags_validation_empty_list_accepted(self):
        """Empty list [] is valid and passes without error."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        result = _validate_tags([])
        assert result == []

    @pytest.mark.asyncio
    async def test_tags_validation_non_list_type_rejected(self):
        """Non-list type (string) raises ValidationError."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        with pytest.raises(ValidationError, match="must be a list"):
            _validate_tags("not_a_list")

    @pytest.mark.asyncio
    async def test_tags_with_colons_and_special_chars(self):
        """Tags containing colons, slashes, and other special chars are valid."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        tags = [
            "action_required:fix auth/regression",
            "priority:high:urgent",
            "scope:backend/api",
        ]
        result = _validate_tags(tags)
        assert result == tags

    @pytest.mark.asyncio
    async def test_tags_with_unicode_characters(self):
        """Tags with unicode characters pass validation."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        tags = ["action_required:fix regression", "note:uppgift"]
        result = _validate_tags(tags)
        assert result == tags

    @pytest.mark.asyncio
    async def test_tags_at_exact_max_count(self):
        """Exactly 10 tags (the maximum) is accepted."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        tags = [f"tag_{i}" for i in range(10)]
        result = _validate_tags(tags)
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_tags_at_exact_max_length(self):
        """Tag at exactly 200 characters (the maximum) is accepted."""
        from src.giljo_mcp.tools.write_360_memory import _validate_tags

        tags = ["a" * 200]
        result = _validate_tags(tags)
        assert len(result[0]) == 200


class TestGetEntriesByTagPrefixEdgeCases:
    """Additional edge-case tests for get_entries_by_tag_prefix."""

    @pytest.mark.asyncio
    async def test_no_entries_returns_empty_list(self, db_session: AsyncSession, test_product):
        """When no entries exist at all, returns empty list."""
        repo = ProductMemoryRepository()
        results = await repo.get_entries_by_tag_prefix(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key="test_tenant",
            prefix="action_required",
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_entries_exist_but_no_matching_prefix(self, db_session: AsyncSession, test_product):
        """Entries exist but none match the prefix -- returns empty list."""
        repo = ProductMemoryRepository()
        await repo.create_entry(
            session=db_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Unrelated tags",
            tags=["priority:high", "scope:backend"],
        )
        results = await repo.get_entries_by_tag_prefix(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key="test_tenant",
            prefix="action_required",
        )
        assert results == []


class TestResolveActionTagsEdgeCases:
    """Additional edge-case tests for resolve_action_tags."""

    @pytest.mark.asyncio
    async def test_empty_resolved_items_is_noop(self, db_session: AsyncSession, test_product):
        """Empty resolved_items list returns 0 without touching DB."""
        repo = ProductMemoryRepository()
        await repo.create_entry(
            session=db_session,
            tenant_key="test_tenant",
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Has tags",
            tags=["action_required:fix bug"],
        )
        count = await repo.resolve_action_tags(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key="test_tenant",
            resolved_items=[],
        )
        assert count == 0

        # Verify tag was NOT removed
        entries = await repo.get_entries_by_product(
            session=db_session,
            product_id=test_product.id,
            tenant_key="test_tenant",
        )
        assert "action_required:fix bug" in entries[0].tags

    @pytest.mark.asyncio
    async def test_resolve_clears_all_matching_tags_across_entries(self, db_session: AsyncSession, test_product):
        """Resolve clears matching tags from multiple entries at once."""
        repo = ProductMemoryRepository()
        tenant_key = "test_tenant"

        await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Entry 1",
            tags=["action_required:fix auth"],
        )
        await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=test_product.id,
            sequence=2,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Entry 2",
            tags=["action_required:fix auth", "priority:high"],
        )

        count = await repo.resolve_action_tags(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key=tenant_key,
            resolved_items=["fix auth"],
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_write_entry_with_tags_containing_colons(self, db_session: AsyncSession, test_product):
        """Tags with multiple colons persist and query correctly."""
        repo = ProductMemoryRepository()
        tenant_key = "test_tenant"
        tags = ["action_required:fix:auth:regression"]

        entry = await repo.create_entry(
            session=db_session,
            tenant_key=tenant_key,
            product_id=test_product.id,
            sequence=1,
            entry_type="project_completion",
            source="test_v1",
            timestamp=datetime.now(timezone.utc),
            summary="Multi-colon tag",
            tags=tags,
        )
        assert entry.tags == tags

        results = await repo.get_entries_by_tag_prefix(
            session=db_session,
            product_id=uuid.UUID(str(test_product.id)),
            tenant_key=tenant_key,
            prefix="action_required",
        )
        assert len(results) == 1
