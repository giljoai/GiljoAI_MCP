"""
Critical test coverage for framing_helpers.py functions with 0% coverage.

This test module focuses on achieving >80% coverage by testing:
- apply_rich_entry_framing() and its error paths
- build_priority_excluded_response()
- Error paths in build_framed_context_response()
"""

import pytest
from uuid import uuid4
from typing import Any, Dict

from src.giljo_mcp.tools.context_tools.framing_helpers import (
    apply_rich_entry_framing,
    build_priority_excluded_response,
    build_framed_context_response,
)


# ============================================================================
# Tests for apply_rich_entry_framing() - Currently 0% coverage
# ============================================================================


def test_apply_rich_entry_framing_valid_all_fields():
    """Test rich entry framing with all fields populated."""
    entry = {
        "sequence": 42,
        "project_name": "Test Project Alpha",
        "summary": "Implemented authentication system with JWT",
        "key_outcomes": [
            "User login flow completed",
            "Token refresh mechanism implemented",
            "Session management added"
        ],
        "decisions_made": [
            "Chose JWT over session cookies",
            "Selected bcrypt for password hashing"
        ],
        "priority": 1,
        "significance_score": 0.95
    }

    result = apply_rich_entry_framing(entry)

    # Verify framing structure
    assert "## CRITICAL: Project Memory (Sequence 42)" in result
    assert "**Project**: Test Project Alpha" in result
    assert "**Summary**: Implemented authentication system with JWT" in result
    assert "**Key Outcomes**:" in result
    assert "- User login flow completed" in result
    assert "- Token refresh mechanism implemented" in result
    assert "- Session management added" in result
    assert "**Decisions Made**:" in result
    assert "- Chose JWT over session cookies" in result
    assert "- Selected bcrypt for password hashing" in result
    assert "**Significance**: 0.95" in result


def test_apply_rich_entry_framing_minimal_valid():
    """Test rich entry framing with only required fields."""
    entry = {
        "sequence": 1,
        "project_name": "Minimal Project",
        "summary": "Basic summary"
    }

    result = apply_rich_entry_framing(entry)

    # Should use defaults for missing fields
    assert "## REFERENCE: Project Memory (Sequence 1)" in result  # Default priority 3
    assert "**Project**: Minimal Project" in result
    assert "**Summary**: Basic summary" in result
    assert "**Key Outcomes**:" in result
    assert "- (None)" in result  # Empty list formatted
    assert "**Decisions Made**:" in result
    assert "**Significance**: 0.50" in result  # Default significance


def test_apply_rich_entry_framing_missing_sequence():
    """Test that missing 'sequence' field raises ValueError."""
    entry = {
        "project_name": "Test Project",
        "summary": "Test summary"
    }

    with pytest.raises(ValueError, match="Invalid entry: missing sequence"):
        apply_rich_entry_framing(entry)


def test_apply_rich_entry_framing_missing_project_name():
    """Test that missing 'project_name' field raises ValueError."""
    entry = {
        "sequence": 1,
        "summary": "Test summary"
    }

    with pytest.raises(ValueError, match="Invalid entry: missing project_name"):
        apply_rich_entry_framing(entry)


def test_apply_rich_entry_framing_missing_summary():
    """Test that missing 'summary' field raises ValueError."""
    entry = {
        "sequence": 1,
        "project_name": "Test Project"
    }

    with pytest.raises(ValueError, match="Invalid entry: missing summary"):
        apply_rich_entry_framing(entry)


def test_apply_rich_entry_framing_malformed_key_outcomes():
    """Test handling of malformed key_outcomes (not a list)."""
    entry = {
        "sequence": 1,
        "project_name": "Test Project",
        "summary": "Test summary",
        "key_outcomes": "This should be a list but is a string",
        "decisions_made": ["Valid decision"]
    }

    result = apply_rich_entry_framing(entry)

    # Should handle gracefully by converting to empty list
    assert "**Key Outcomes**:" in result
    assert "- (None)" in result  # Malformed data treated as empty
    assert "**Decisions Made**:" in result
    assert "- Valid decision" in result


def test_apply_rich_entry_framing_malformed_decisions_made():
    """Test handling of malformed decisions_made (not a list)."""
    entry = {
        "sequence": 1,
        "project_name": "Test Project",
        "summary": "Test summary",
        "key_outcomes": ["Valid outcome"],
        "decisions_made": {"invalid": "structure"}
    }

    result = apply_rich_entry_framing(entry)

    # Should handle gracefully by converting to empty list
    assert "**Key Outcomes**:" in result
    assert "- Valid outcome" in result
    assert "**Decisions Made**:" in result
    assert "- (None)" in result  # Malformed data treated as empty


def test_apply_rich_entry_framing_empty_lists():
    """Test handling of empty key_outcomes and decisions_made lists."""
    entry = {
        "sequence": 5,
        "project_name": "Empty Lists Project",
        "summary": "Project with no outcomes or decisions tracked",
        "key_outcomes": [],
        "decisions_made": [],
        "priority": 2
    }

    result = apply_rich_entry_framing(entry)

    assert "## IMPORTANT: Project Memory (Sequence 5)" in result
    assert "**Key Outcomes**:" in result
    assert "- (None)" in result
    assert "**Decisions Made**:" in result


def test_apply_rich_entry_framing_priority_levels():
    """Test different priority levels produce correct labels."""
    base_entry = {
        "sequence": 1,
        "project_name": "Test",
        "summary": "Test"
    }

    # Priority 1: CRITICAL
    entry_p1 = {**base_entry, "priority": 1}
    result_p1 = apply_rich_entry_framing(entry_p1)
    assert "## CRITICAL:" in result_p1

    # Priority 2: IMPORTANT
    entry_p2 = {**base_entry, "priority": 2}
    result_p2 = apply_rich_entry_framing(entry_p2)
    assert "## IMPORTANT:" in result_p2

    # Priority 3: REFERENCE
    entry_p3 = {**base_entry, "priority": 3}
    result_p3 = apply_rich_entry_framing(entry_p3)
    assert "## REFERENCE:" in result_p3

    # Priority 4 or unknown: Defaults to REFERENCE
    entry_p4 = {**base_entry, "priority": 4}
    result_p4 = apply_rich_entry_framing(entry_p4)
    assert "## REFERENCE:" in result_p4


def test_apply_rich_entry_framing_empty_string_items():
    """Test that empty strings in lists are filtered out."""
    entry = {
        "sequence": 1,
        "project_name": "Test",
        "summary": "Test",
        "key_outcomes": ["Valid outcome", "", "Another valid outcome", ""],
        "decisions_made": ["", "Valid decision", ""]
    }

    result = apply_rich_entry_framing(entry)

    # Empty strings should be filtered by format_list_safely
    assert "- Valid outcome" in result
    assert "- Another valid outcome" in result
    assert "- Valid decision" in result
    # Should not have consecutive empty bullet points


# ============================================================================
# Tests for build_priority_excluded_response() - Currently 0% coverage
# ============================================================================


def test_build_priority_excluded_response_structure():
    """Test that build_priority_excluded_response returns correct structure."""
    result = build_priority_excluded_response(
        source="test_source",
        category="git_history",
        tenant_key="tenant_123",
        priority=4
    )

    # Verify all required fields
    assert result["source"] == "test_source"
    assert result["category"] == "git_history"
    assert result["data"] == []
    assert result["framed_content"] == ""
    assert result["priority"] == 4

    # Verify metadata
    assert result["metadata"]["tenant_key"] == "tenant_123"
    assert result["metadata"]["priority"] == 4
    assert result["metadata"]["excluded_by_priority"] is True


def test_build_priority_excluded_response_different_categories():
    """Test excluded response for various categories."""
    categories = [
        "product_core",
        "vision_documents",
        "agent_templates",
        "project_context",
        "memory_360",
        "git_history"
    ]

    for category in categories:
        result = build_priority_excluded_response(
            source=f"{category}_source",
            category=category,
            tenant_key="tenant_test",
            priority=4
        )

        assert result["category"] == category
        assert result["metadata"]["excluded_by_priority"] is True
        assert result["framed_content"] == ""


def test_build_priority_excluded_response_maintains_priority():
    """Test that excluded response preserves the priority value."""
    result = build_priority_excluded_response(
        source="test",
        category="test_category",
        tenant_key="tenant_999",
        priority=4
    )

    # Priority should be in both top-level and metadata
    assert result["priority"] == 4
    assert result["metadata"]["priority"] == 4


# ============================================================================
# Tests for build_framed_context_response() error paths
# ============================================================================


@pytest.mark.asyncio
async def test_build_framed_context_response_empty_content(db_manager):
    """Test build_framed_context_response with empty content."""
    raw_result = {
        "source": "test_source",
        "data": [],
        "metadata": {}
    }

    result = await build_framed_context_response(
        raw_result=raw_result,
        category="product_core",
        tenant_key="tenant_empty",
        user_id=None,
        db_manager=db_manager
    )

    # Should handle empty content gracefully
    assert "priority" in result
    assert "framed_content" in result
    assert "metadata" in result
    assert result["metadata"]["framing_applied"] is True


@pytest.mark.asyncio
async def test_build_framed_context_response_framing_error(db_manager):
    """Test build_framed_context_response when content_formatter raises ValueError."""
    raw_result = {
        "source": "test_source",
        "data": {"test": "data"},
        "metadata": {"existing": "value"}
    }

    def failing_formatter(raw: Dict[str, Any]) -> str:
        """Formatter that always raises ValueError."""
        raise ValueError("Simulated formatting error")

    result = await build_framed_context_response(
        raw_result=raw_result,
        category="vision_documents",
        tenant_key="tenant_error",
        user_id="user_123",
        db_manager=db_manager,
        content_formatter=failing_formatter
    )

    # Should handle error gracefully
    assert result["framed_content"] == ""
    assert result["metadata"]["framing_applied"] is False
    assert result["metadata"]["framing_error"] == "Simulated formatting error"
    assert result["priority"] is not None
    assert result["category"] == "vision_documents"


@pytest.mark.asyncio
async def test_build_framed_context_response_preserves_existing_metadata(db_manager):
    """Test that build_framed_context_response preserves existing metadata fields."""
    raw_result = {
        "source": "test_source",
        "data": [],
        "metadata": {
            "existing_field": "existing_value",
            "another_field": 123
        }
    }

    result = await build_framed_context_response(
        raw_result=raw_result,
        category="agent_templates",
        tenant_key="tenant_preserve",
        user_id=None,
        db_manager=db_manager
    )

    # Original metadata should be preserved
    assert result["metadata"]["existing_field"] == "existing_value"
    assert result["metadata"]["another_field"] == 123
    # New fields should be added
    assert "priority" in result["metadata"]
    assert "framing_applied" in result["metadata"]


@pytest.mark.asyncio
async def test_build_framed_context_response_with_priority_override(db_manager):
    """Test that priority_override takes precedence over user config."""
    raw_result = {
        "source": "test_source",
        "data": [],
        "metadata": {}
    }

    result = await build_framed_context_response(
        raw_result=raw_result,
        category="project_context",
        tenant_key="tenant_override",
        user_id="user_override",
        db_manager=db_manager,
        priority_override=1  # Force CRITICAL priority
    )

    # Should use override priority
    assert result["priority"] == 1
    assert result["metadata"]["priority"] == 1


@pytest.mark.asyncio
async def test_build_framed_context_response_none_metadata(db_manager):
    """Test handling of None metadata in raw_result."""
    raw_result = {
        "source": "test_source",
        "data": [],
        "metadata": None  # Edge case: None instead of dict
    }

    result = await build_framed_context_response(
        raw_result=raw_result,
        category="git_history",
        tenant_key="tenant_none",
        user_id=None,
        db_manager=db_manager
    )

    # Should handle None gracefully by creating new metadata dict
    assert isinstance(result["metadata"], dict)
    assert result["metadata"]["priority"] is not None
    assert result["metadata"]["tenant_key"] == "tenant_none"


@pytest.mark.asyncio
async def test_build_framed_context_response_custom_formatter(db_manager):
    """Test build_framed_context_response with custom content_formatter."""
    raw_result = {
        "source": "custom_source",
        "data": [{"item": "test"}],
        "metadata": {}
    }

    def custom_formatter(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Custom formatter that restructures content."""
        return {
            "source": raw.get("source"),
            "formatted": True,
            "data": raw.get("data")
        }

    result = await build_framed_context_response(
        raw_result=raw_result,
        category="memory_360",
        tenant_key="tenant_custom",
        user_id=None,
        db_manager=db_manager,
        content_formatter=custom_formatter
    )

    # Should successfully apply custom formatter
    assert result["metadata"]["framing_applied"] is True
    assert "framed_content" in result
