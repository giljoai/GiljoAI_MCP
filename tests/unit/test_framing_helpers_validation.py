"""
Unit tests for framing_helpers.py validation constants.

Tests that ALLOWED_PRIORITY_CATEGORIES includes all valid context fields
from Context Management v2.0.

Following TDD principles: Tests written BEFORE implementation.
"""

import pytest
from src.giljo_mcp.tools.context_tools.framing_helpers import get_user_priority


class TestAllowedPriorityCategoriesValidation:
    """Test that ALLOWED_PRIORITY_CATEGORIES accepts all valid v2.0 categories."""

    @pytest.mark.asyncio
    async def test_get_user_priority_accepts_tech_stack(self):
        """get_user_priority should accept 'tech_stack' category."""
        # Should not raise ValueError
        priority = await get_user_priority(
            category="tech_stack",
            tenant_key="test-tenant",
            user_id=None,
            db_manager=None,
        )

        # Should return default priority (not raise exception)
        assert isinstance(priority, int)
        assert 1 <= priority <= 4

    @pytest.mark.asyncio
    async def test_get_user_priority_accepts_architecture(self):
        """get_user_priority should accept 'architecture' category."""
        # Should not raise ValueError
        priority = await get_user_priority(
            category="architecture",
            tenant_key="test-tenant",
            user_id=None,
            db_manager=None,
        )

        # Should return default priority (not raise exception)
        assert isinstance(priority, int)
        assert 1 <= priority <= 4

    @pytest.mark.asyncio
    async def test_get_user_priority_accepts_testing(self):
        """get_user_priority should accept 'testing' category."""
        # Should not raise ValueError
        priority = await get_user_priority(
            category="testing",
            tenant_key="test-tenant",
            user_id=None,
            db_manager=None,
        )

        # Should return default priority (not raise exception)
        assert isinstance(priority, int)
        assert 1 <= priority <= 4

    @pytest.mark.asyncio
    async def test_get_user_priority_accepts_all_original_categories(self):
        """get_user_priority should accept all original v2.0 categories."""
        original_categories = [
            "product_core",
            "vision_documents",
            "agent_templates",
            "project_context",
            "memory_360",
            "git_history",
        ]

        for category in original_categories:
            # Should not raise ValueError
            priority = await get_user_priority(
                category=category,
                tenant_key="test-tenant",
                user_id=None,
                db_manager=None,
            )

            assert isinstance(priority, int)
            assert 1 <= priority <= 4

    @pytest.mark.asyncio
    async def test_get_user_priority_rejects_invalid_category(self):
        """get_user_priority should reject invalid category names."""
        with pytest.raises(ValueError, match="Invalid category 'invalid_cat'"):
            await get_user_priority(
                category="invalid_cat",
                tenant_key="test-tenant",
                user_id=None,
                db_manager=None,
            )

    @pytest.mark.asyncio
    async def test_error_message_shows_all_valid_categories(self):
        """Error message should list all 9 valid categories."""
        with pytest.raises(ValueError) as exc_info:
            await get_user_priority(
                category="bad_category",
                tenant_key="test-tenant",
                user_id=None,
                db_manager=None,
            )

        error_message = str(exc_info.value)

        # Should mention all 9 valid categories
        expected_categories = [
            "agent_templates",
            "architecture",
            "git_history",
            "memory_360",
            "product_core",
            "project_context",
            "tech_stack",
            "testing",
            "vision_documents",
        ]

        for category in expected_categories:
            assert category in error_message, f"Error message should mention '{category}'"
