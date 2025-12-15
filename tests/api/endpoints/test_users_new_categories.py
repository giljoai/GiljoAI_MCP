"""
Test that tech_stack, architecture, and testing categories are accepted by backend validator.

This test verifies that the backend accepts the new category names that the frontend
is sending when users toggle context fields in My Settings → Context.

Related Files:
- api/endpoints/users.py (FieldPriorityConfig validator)
- frontend/src/components/settings/ContextPriorityConfig.vue (lines 131-133)
"""

import pytest
from pydantic import ValidationError

from api.endpoints.users import FieldPriorityConfig


class TestNewCategoryValidation:
    """Test that new category names (tech_stack, architecture, testing) are accepted."""

    def test_accepts_tech_stack_category(self):
        """Should accept 'tech_stack' as a valid category."""
        config_with_tech_stack = {
            "product_core": 1,
            "tech_stack": 2,
        }

        # This should NOT raise ValidationError
        config = FieldPriorityConfig(priorities=config_with_tech_stack)
        assert config.priorities == config_with_tech_stack
        assert config.version == "2.0"

    def test_accepts_architecture_category(self):
        """Should accept 'architecture' as a valid category."""
        config_with_architecture = {
            "product_core": 1,
            "architecture": 2,
        }

        # This should NOT raise ValidationError
        config = FieldPriorityConfig(priorities=config_with_architecture)
        assert config.priorities == config_with_architecture
        assert config.version == "2.0"

    def test_accepts_testing_category(self):
        """Should accept 'testing' as a valid category."""
        config_with_testing = {
            "product_core": 1,
            "testing": 3,
        }

        # This should NOT raise ValidationError
        config = FieldPriorityConfig(priorities=config_with_testing)
        assert config.priorities == config_with_testing
        assert config.version == "2.0"

    def test_accepts_all_three_new_categories(self):
        """Should accept all three new categories together."""
        config_with_all_new = {
            "product_core": 1,
            "tech_stack": 2,
            "architecture": 2,
            "testing": 3,
        }

        # This should NOT raise ValidationError
        config = FieldPriorityConfig(priorities=config_with_all_new)
        assert config.priorities == config_with_all_new
        assert config.version == "2.0"

    def test_accepts_all_nine_categories(self):
        """Should accept all 9 valid categories (6 old + 3 new)."""
        config_with_all = {
            # Original 6 categories
            "product_core": 1,
            "vision_documents": 1,
            "agent_templates": 2,
            "project_description": 2,
            "memory_360": 2,
            "git_history": 3,
            # New 3 categories
            "tech_stack": 2,
            "architecture": 2,
            "testing": 3,
        }

        # This should NOT raise ValidationError
        config = FieldPriorityConfig(priorities=config_with_all)
        assert config.priorities == config_with_all
        assert config.version == "2.0"

    def test_priority_range_validation_still_works(self):
        """Should still validate priority values are in range [1,4] for new categories."""
        invalid_priority_config = {
            "product_core": 1,
            "tech_stack": 5,  # Invalid priority
        }

        with pytest.raises(ValidationError) as exc_info:
            FieldPriorityConfig(priorities=invalid_priority_config)

        error_msg = str(exc_info.value)
        assert "Invalid priority 5" in error_msg

    def test_still_rejects_unknown_categories(self):
        """Should still reject completely unknown category names."""
        invalid_config = {
            "product_core": 1,
            "unknown_category": 2,
        }

        with pytest.raises(ValidationError) as exc_info:
            FieldPriorityConfig(priorities=invalid_config)

        error_msg = str(exc_info.value)
        assert "unknown_category" in error_msg
        assert "Invalid category names" in error_msg
