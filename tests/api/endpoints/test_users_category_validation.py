"""
Tests for category validation in FieldPriorityConfig (Handover 0248a Task 1).

Tests ensure backend only accepts valid backend categories:
- product_core
- vision_documents
- agent_templates
- project_description
- memory_360
- git_history
- tech_stack (added for frontend integration)
- architecture (added for frontend integration)
- testing (added for frontend integration)

UI-only categories should still be REJECTED:
- product_description (UI-only field)
"""

import pytest
from pydantic import ValidationError

from api.endpoints.users import FieldPriorityConfig


class TestFieldPriorityConfigCategoryValidation:
    """Test category validation for FieldPriorityConfig."""

    def test_accepts_valid_backend_categories(self):
        """Should accept all valid backend categories."""
        valid_config = {
            "product_core": 1,
            "vision_documents": 2,
            "agent_templates": 3,
            "project_description": 2,
            "memory_360": 3,
            "git_history": 3,
        }

        config = FieldPriorityConfig(priorities=valid_config)
        assert config.priorities == valid_config
        assert config.version == "2.0"

    def test_rejects_ui_category_product_description(self):
        """Should reject UI category 'product_description'."""
        invalid_config = {
            "product_core": 1,
            "product_description": 2,  # UI category - should fail
        }

        with pytest.raises(ValidationError) as exc_info:
            FieldPriorityConfig(priorities=invalid_config)

        error_msg = str(exc_info.value)
        assert "product_description" in error_msg
        assert "Invalid category names" in error_msg

    def test_accepts_tech_stack_category(self):
        """Should accept 'tech_stack' category (frontend integration)."""
        valid_config = {
            "product_core": 1,
            "tech_stack": 2,
        }

        config = FieldPriorityConfig(priorities=valid_config)
        assert config.priorities == valid_config
        assert config.version == "2.0"

    def test_accepts_architecture_category(self):
        """Should accept 'architecture' category (frontend integration)."""
        valid_config = {
            "product_core": 1,
            "architecture": 2,
        }

        config = FieldPriorityConfig(priorities=valid_config)
        assert config.priorities == valid_config
        assert config.version == "2.0"

    def test_accepts_testing_category(self):
        """Should accept 'testing' category (frontend integration)."""
        valid_config = {
            "product_core": 1,
            "testing": 2,
        }

        config = FieldPriorityConfig(priorities=valid_config)
        assert config.priorities == valid_config
        assert config.version == "2.0"

    def test_rejects_ui_only_category_product_description(self):
        """Should reject configuration with UI-only category 'product_description'."""
        invalid_config = {
            "product_core": 1,
            "product_description": 2,  # UI-only category - should fail
        }

        with pytest.raises(ValidationError) as exc_info:
            FieldPriorityConfig(priorities=invalid_config)

        error_msg = str(exc_info.value)
        assert "Invalid category names" in error_msg
        assert "product_description" in error_msg

    def test_rejects_unknown_category(self):
        """Should reject completely unknown category names."""
        invalid_config = {
            "product_core": 1,
            "unknown_category": 2,
        }

        with pytest.raises(ValidationError) as exc_info:
            FieldPriorityConfig(priorities=invalid_config)

        error_msg = str(exc_info.value)
        assert "unknown_category" in error_msg
        assert "Invalid category names" in error_msg

    def test_accepts_subset_of_valid_categories(self):
        """Should accept any subset of valid backend categories."""
        # Test with just 2 categories
        minimal_config = {
            "product_core": 1,
            "vision_documents": 2,
        }

        config = FieldPriorityConfig(priorities=minimal_config)
        assert config.priorities == minimal_config

    def test_priority_range_validation_still_works(self):
        """Should still validate priority values are in range [1,4]."""
        invalid_priority_config = {
            "product_core": 5,  # Invalid priority
        }

        with pytest.raises(ValidationError) as exc_info:
            FieldPriorityConfig(priorities=invalid_priority_config)

        error_msg = str(exc_info.value)
        assert "Invalid priority 5" in error_msg

    def test_requires_at_least_one_critical_category(self):
        """Should require at least one category with Priority 1 (CRITICAL)."""
        no_critical_config = {
            "product_core": 2,  # No Priority 1
            "vision_documents": 3,
        }

        with pytest.raises(ValidationError) as exc_info:
            FieldPriorityConfig(priorities=no_critical_config)

        error_msg = str(exc_info.value)
        assert "At least one category must have Priority 1 (CRITICAL)" in error_msg

    def test_rejects_all_excluded_categories(self):
        """Should reject configuration where all categories are excluded."""
        all_excluded_config = {
            "product_core": 4,
            "vision_documents": 4,
            "agent_templates": 4,
        }

        with pytest.raises(ValidationError) as exc_info:
            FieldPriorityConfig(priorities=all_excluded_config)

        error_msg = str(exc_info.value)
        # Both error messages are valid (CRITICAL check runs first, but logically equivalent)
        assert (
            "Cannot exclude all categories" in error_msg
            or "At least one category must have Priority 1 (CRITICAL)" in error_msg
        )
