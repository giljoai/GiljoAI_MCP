"""
Simplified unit tests for fetch_context (Handover 0350a).
Focuses on dispatcher logic without deep mocking.
"""

import pytest
from src.giljo_mcp.tools.context_tools.fetch_context import (
    fetch_context,
    ALL_CATEGORIES,
    DEFAULT_DEPTHS,
    _flatten_results
)


def test_all_categories_constant():
    """Test ALL_CATEGORIES contains all 10 expected categories (Handover 0430)."""
    expected = [
        "product_core", "vision_documents", "tech_stack",
        "architecture", "testing", "memory_360",
        "git_history", "agent_templates", "project",
        "self_identity"
    ]
    assert set(ALL_CATEGORIES) == set(expected)
    assert len(ALL_CATEGORIES) == 10


def test_default_depths_constant():
    """Test DEFAULT_DEPTHS has correct structure (Handover 0430)."""
    assert len(DEFAULT_DEPTHS) == 10
    assert DEFAULT_DEPTHS["product_core"] is None
    assert DEFAULT_DEPTHS["vision_documents"] == "medium"
    assert DEFAULT_DEPTHS["tech_stack"] is None  # Updated in Handover 0351
    assert DEFAULT_DEPTHS["architecture"] is None  # Updated in Handover 0351
    assert DEFAULT_DEPTHS["testing"] is None  # Updated in Handover 0351
    assert DEFAULT_DEPTHS["memory_360"] == 5
    assert DEFAULT_DEPTHS["git_history"] == 25
    assert DEFAULT_DEPTHS["agent_templates"] == "type_only"  # Updated in Handover 0351
    assert DEFAULT_DEPTHS["project"] is None
    assert DEFAULT_DEPTHS["self_identity"] is None  # New in Handover 0430


@pytest.mark.asyncio
async def test_fetch_context_invalid_category():
    """Test invalid category returns error without calling tools (Handover 0351 multi-category enforcement)."""
    from unittest.mock import MagicMock

    result = await fetch_context(
        product_id="test-uuid",
        tenant_key="tenant-abc",
        categories=["invalid_cat"],  # Single category (enforced in 0351)
        db_manager=MagicMock()
    )

    assert "error" in result
    assert "invalid_cat" in result["error"]
    assert "valid_categories" in result


def test_flatten_results():
    """Test _flatten_results correctly flattens nested dicts."""
    nested = {
        "product_core": {"name": "Test", "features": ["A", "B"]},
        "tech_stack": {"languages": ["Python"]}
    }
    
    flat = _flatten_results(nested)
    
    assert "product_core_name" in flat
    assert flat["product_core_name"] == "Test"
    assert "product_core_features" in flat
    assert flat["product_core_features"] == ["A", "B"]
    assert "tech_stack_languages" in flat
    assert flat["tech_stack_languages"] == ["Python"]


def test_flatten_results_with_non_dict():
    """Test _flatten_results handles non-dict values."""
    nested = {
        "category1": {"key": "value"},
        "category2": "simple_string"
    }
    
    flat = _flatten_results(nested)
    
    assert "category1_key" in flat
    assert flat["category1_key"] == "value"
    assert "category2" in flat
    assert flat["category2"] == "simple_string"
