# Handover 0347a: JSON Context Builder

**Date**: 2025-12-14
**Agent**: Documentation Manager
**Priority**: High
**Estimated Effort**: 1.5 hours
**Status**: Pending Implementation

## Task Summary

Create a `JSONContextBuilder` utility class to build structured JSON context with priority framing for orchestrator missions. This replaces the reverted YAML approach with a pure JSON solution using only stdlib.

**Key Deliverables**:
1. `src/giljo_mcp/json_context_builder.py` - Core utility class
2. `tests/services/test_json_context_builder.py` - TDD test suite (>80% coverage)
3. No external dependencies (PyYAML removed) - stdlib `json` only

## Context

**Background**: The YAML-based mission response structuring approach (from early 0347 exploration) was reverted. We need a clean JSON-based solution that:
- Organizes context fields by priority (critical/important/reference)
- Provides token estimation for context budget management
- Uses only Python stdlib (no PyYAML dependency)
- Supports the orchestrator's 2-dimensional context management model

**Related Systems**:
- Context Management v2.0 (Priority × Depth dimensions)
- Orchestrator Staging Workflow (0246a - 931 token budget)
- MCP Context Tools (9 tools with priority/depth configuration)

## Technical Details

### Class API

```python
class JSONContextBuilder:
    """
    Builds structured JSON context with priority framing for orchestrator missions.

    Organizes context fields into three priority tiers:
    - critical: Always included (e.g., product_core, tech_stack)
    - important: High priority (e.g., architecture, testing)
    - reference: Medium priority (e.g., vision_documents, memory_360)

    Usage:
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical_content("product_core", {"name": "GiljoAI", ...})
        builder.add_important("architecture")
        builder.add_important_content("architecture", {"patterns": [...]})
        result = builder.build()
        tokens = builder.estimate_tokens()
    """

    def __init__(self):
        """Initialize empty builder with three priority tiers."""
        self.critical_fields: list[str] = []
        self.important_fields: list[str] = []
        self.reference_fields: list[str] = []
        self.critical_content: dict = {}
        self.important_content: dict = {}
        self.reference_content: dict = {}

    def add_critical(self, field_name: str) -> None:
        """
        Add a field to the critical priority tier.

        Args:
            field_name: Name of the context field (e.g., "product_core")

        Raises:
            ValueError: If field_name is empty or already exists in any tier
        """
        ...

    def add_important(self, field_name: str) -> None:
        """
        Add a field to the important priority tier.

        Args:
            field_name: Name of the context field (e.g., "architecture")

        Raises:
            ValueError: If field_name is empty or already exists in any tier
        """
        ...

    def add_reference(self, field_name: str) -> None:
        """
        Add a field to the reference priority tier.

        Args:
            field_name: Name of the context field (e.g., "vision_documents")

        Raises:
            ValueError: If field_name is empty or already exists in any tier
        """
        ...

    def add_critical_content(self, field_name: str, content: Any) -> None:
        """
        Add content for a critical field.

        Args:
            field_name: Name of the field (must be in critical_fields)
            content: Any JSON-serializable content (dict, list, str, int, etc.)

        Raises:
            ValueError: If field_name not in critical_fields
            TypeError: If content is not JSON-serializable
        """
        ...

    def add_important_content(self, field_name: str, content: Any) -> None:
        """
        Add content for an important field.

        Args:
            field_name: Name of the field (must be in important_fields)
            content: Any JSON-serializable content

        Raises:
            ValueError: If field_name not in important_fields
            TypeError: If content is not JSON-serializable
        """
        ...

    def add_reference_content(self, field_name: str, content: Any) -> None:
        """
        Add content for a reference field.

        Args:
            field_name: Name of the field (must be in reference_fields)
            content: Any JSON-serializable content

        Raises:
            ValueError: If field_name not in reference_fields
            TypeError: If content is not JSON-serializable
        """
        ...

    def build(self) -> dict:
        """
        Build the complete JSON structure with priority framing.

        Returns:
            dict: Structured JSON with format:
                {
                    "priority_map": {
                        "critical": ["field1", "field2"],
                        "important": ["field3"],
                        "reference": ["field4", "field5"]
                    },
                    "critical": {
                        "field1": <content>,
                        "field2": <content>
                    },
                    "important": {
                        "field3": <content>
                    },
                    "reference": {
                        "field4": <content>,
                        "field5": <content>
                    }
                }

        Note:
            - Fields without content are omitted from tier dicts
            - priority_map always includes all registered fields
            - Result is always JSON-serializable
        """
        ...

    def estimate_tokens(self) -> int:
        """
        Estimate total token count for the built JSON structure.

        Uses approximation: 1 token ≈ 4 characters

        Returns:
            int: Estimated token count

        Note:
            - Estimates based on JSON-serialized output
            - Includes all formatting (whitespace, brackets, quotes)
            - Useful for context budget management
        """
        ...
```

### Output Structure

```json
{
  "priority_map": {
    "critical": ["product_core", "tech_stack"],
    "important": ["architecture", "testing"],
    "reference": ["vision_documents", "memory_360"]
  },
  "critical": {
    "product_core": {
      "name": "GiljoAI MCP",
      "description": "Multi-tenant agent orchestration server",
      "features": ["context prioritization", "agent coordination"]
    },
    "tech_stack": {
      "backend": ["Python 3.11+", "FastAPI", "PostgreSQL 18"],
      "frontend": ["Vue 3", "Vuetify"]
    }
  },
  "important": {
    "architecture": {
      "patterns": ["Service Layer", "Multi-Tenant Isolation"],
      "api_style": "RESTful + WebSockets"
    },
    "testing": {
      "strategy": "TDD with >80% coverage",
      "frameworks": ["pytest", "pytest-asyncio"]
    }
  },
  "reference": {
    "vision_documents": {
      "count": 3,
      "total_tokens": 15000
    },
    "memory_360": {
      "project_count": 5,
      "total_tokens": 2500
    }
  }
}
```

## TDD Test Cases

### Test Suite: `tests/services/test_json_context_builder.py`

```python
"""TDD tests for JSONContextBuilder utility class."""

import json
import pytest
from src.giljo_mcp.json_context_builder import JSONContextBuilder


class TestJSONContextBuilderInit:
    """Test JSONContextBuilder initialization."""

    def test_init_creates_empty_builder(self):
        """Should initialize with empty fields and content."""
        builder = JSONContextBuilder()
        assert builder.critical_fields == []
        assert builder.important_fields == []
        assert builder.reference_fields == []
        assert builder.critical_content == {}
        assert builder.important_content == {}
        assert builder.reference_content == {}


class TestAddFields:
    """Test adding fields to priority tiers."""

    def test_add_critical_field(self):
        """Should add field to critical tier."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        assert "product_core" in builder.critical_fields

    def test_add_important_field(self):
        """Should add field to important tier."""
        builder = JSONContextBuilder()
        builder.add_important("architecture")
        assert "architecture" in builder.important_fields

    def test_add_reference_field(self):
        """Should add field to reference tier."""
        builder = JSONContextBuilder()
        builder.add_reference("vision_documents")
        assert "vision_documents" in builder.reference_fields

    def test_add_field_empty_name_raises_error(self):
        """Should raise ValueError for empty field name."""
        builder = JSONContextBuilder()
        with pytest.raises(ValueError, match="Field name cannot be empty"):
            builder.add_critical("")

    def test_add_duplicate_field_raises_error(self):
        """Should raise ValueError for duplicate field in same tier."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        with pytest.raises(ValueError, match="already exists"):
            builder.add_critical("product_core")

    def test_add_field_across_tiers_raises_error(self):
        """Should raise ValueError for field existing in different tier."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        with pytest.raises(ValueError, match="already exists"):
            builder.add_important("product_core")


class TestAddContent:
    """Test adding content to fields."""

    def test_add_critical_content_dict(self):
        """Should add dict content to critical field."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        content = {"name": "GiljoAI", "version": "3.2"}
        builder.add_critical_content("product_core", content)
        assert builder.critical_content["product_core"] == content

    def test_add_important_content_list(self):
        """Should add list content to important field."""
        builder = JSONContextBuilder()
        builder.add_important("architecture")
        content = ["Service Layer", "Multi-Tenant"]
        builder.add_important_content("architecture", content)
        assert builder.important_content["architecture"] == content

    def test_add_reference_content_string(self):
        """Should add string content to reference field."""
        builder = JSONContextBuilder()
        builder.add_reference("vision_summary")
        content = "Project vision overview"
        builder.add_reference_content("vision_summary", content)
        assert builder.reference_content["vision_summary"] == content

    def test_add_content_to_nonexistent_field_raises_error(self):
        """Should raise ValueError when adding content to unregistered field."""
        builder = JSONContextBuilder()
        with pytest.raises(ValueError, match="not in critical_fields"):
            builder.add_critical_content("unknown_field", {"data": "test"})

    def test_add_non_serializable_content_raises_error(self):
        """Should raise TypeError for non-JSON-serializable content."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")

        # Try to add non-serializable object (e.g., function)
        with pytest.raises(TypeError):
            builder.add_critical_content("product_core", lambda x: x)


class TestBuild:
    """Test building the complete JSON structure."""

    def test_build_empty_structure(self):
        """Should build valid structure with empty content."""
        builder = JSONContextBuilder()
        result = builder.build()

        assert "priority_map" in result
        assert result["priority_map"] == {
            "critical": [],
            "important": [],
            "reference": []
        }
        assert result["critical"] == {}
        assert result["important"] == {}
        assert result["reference"] == {}

    def test_build_with_fields_no_content(self):
        """Should include fields in priority_map even without content."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        builder.add_important("architecture")

        result = builder.build()
        assert "product_core" in result["priority_map"]["critical"]
        assert "architecture" in result["priority_map"]["important"]
        assert "product_core" not in result["critical"]  # No content added
        assert "architecture" not in result["important"]

    def test_build_complete_structure(self):
        """Should build complete structure with all tiers populated."""
        builder = JSONContextBuilder()

        # Critical
        builder.add_critical("product_core")
        builder.add_critical_content("product_core", {"name": "GiljoAI"})

        # Important
        builder.add_important("architecture")
        builder.add_important_content("architecture", {"patterns": ["Service Layer"]})

        # Reference
        builder.add_reference("vision_documents")
        builder.add_reference_content("vision_documents", {"count": 3})

        result = builder.build()

        # Verify priority_map
        assert result["priority_map"]["critical"] == ["product_core"]
        assert result["priority_map"]["important"] == ["architecture"]
        assert result["priority_map"]["reference"] == ["vision_documents"]

        # Verify content
        assert result["critical"]["product_core"] == {"name": "GiljoAI"}
        assert result["important"]["architecture"] == {"patterns": ["Service Layer"]}
        assert result["reference"]["vision_documents"] == {"count": 3}

    def test_build_output_is_json_serializable(self):
        """Should produce JSON-serializable output."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical_content("product_core", {"name": "GiljoAI", "version": 3.2})

        result = builder.build()

        # Should not raise exception
        json_str = json.dumps(result)
        assert isinstance(json_str, str)

        # Should deserialize to same structure
        deserialized = json.loads(json_str)
        assert deserialized == result


class TestEstimateTokens:
    """Test token estimation for context budget management."""

    def test_estimate_tokens_empty_builder(self):
        """Should estimate tokens for empty structure."""
        builder = JSONContextBuilder()
        tokens = builder.estimate_tokens()

        # Empty structure has minimal tokens (priority_map structure)
        assert tokens > 0
        assert tokens < 100  # Should be small

    def test_estimate_tokens_with_content(self):
        """Should estimate tokens based on content size."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical_content("product_core", {
            "name": "GiljoAI MCP",
            "description": "Multi-tenant agent orchestration server",
            "features": ["context prioritization", "agent coordination"]
        })

        tokens = builder.estimate_tokens()

        # Should be proportional to content (1 token ≈ 4 chars)
        json_str = json.dumps(builder.build())
        expected_tokens = len(json_str) // 4

        # Allow 10% margin for approximation
        assert abs(tokens - expected_tokens) < expected_tokens * 0.1

    def test_estimate_tokens_large_structure(self):
        """Should handle token estimation for large structures."""
        builder = JSONContextBuilder()

        # Add multiple fields with substantial content
        for i in range(5):
            field_name = f"field_{i}"
            builder.add_critical(field_name)
            builder.add_critical_content(field_name, {
                "data": ["item"] * 100,  # Large list
                "description": "x" * 1000  # Long string
            })

        tokens = builder.estimate_tokens()

        # Should be substantial (>1000 tokens)
        assert tokens > 1000
```

### Additional Edge Case Tests

```python
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_multiple_fields_same_tier(self):
        """Should support multiple fields in same tier."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical("tech_stack")
        builder.add_critical("project_context")

        assert len(builder.critical_fields) == 3
        result = builder.build()
        assert len(result["priority_map"]["critical"]) == 3

    def test_partial_content_population(self):
        """Should handle partial content population gracefully."""
        builder = JSONContextBuilder()
        builder.add_critical("field1")
        builder.add_critical("field2")
        builder.add_critical_content("field1", {"data": "test"})
        # field2 has no content

        result = builder.build()
        assert "field1" in result["critical"]
        assert "field2" not in result["critical"]  # Omitted when no content
        assert "field2" in result["priority_map"]["critical"]  # Still in map

    def test_nested_complex_structures(self):
        """Should handle deeply nested JSON structures."""
        builder = JSONContextBuilder()
        builder.add_critical("complex")

        nested_content = {
            "level1": {
                "level2": {
                    "level3": {
                        "data": ["item1", "item2"],
                        "metadata": {"count": 2, "valid": True}
                    }
                }
            }
        }

        builder.add_critical_content("complex", nested_content)
        result = builder.build()

        assert result["critical"]["complex"]["level1"]["level2"]["level3"]["data"] == ["item1", "item2"]
```

## Implementation Steps

1. **Create utility class** (`src/giljo_mcp/json_context_builder.py`):
   - Implement `__init__()` with six empty containers
   - Implement `add_critical/important/reference()` with duplicate checks
   - Implement `add_critical/important/reference_content()` with validation
   - Implement `build()` to construct priority-framed JSON
   - Implement `estimate_tokens()` using 1 token ≈ 4 chars approximation

2. **Create TDD test suite** (`tests/services/test_json_context_builder.py`):
   - Write all 20+ test cases from above specification
   - Verify >80% code coverage
   - Test edge cases (empty fields, large structures, nested content)

3. **Validation**:
   - Run `pytest tests/services/test_json_context_builder.py -v`
   - Verify all tests pass
   - Run `pytest tests/services/test_json_context_builder.py --cov=src/giljo_mcp/json_context_builder --cov-report=term-missing`
   - Confirm >80% coverage

## Success Criteria

- ✅ `JSONContextBuilder` class created with complete API
- ✅ All 20+ TDD tests pass
- ✅ Test coverage >80%
- ✅ No PyYAML dependency (stdlib `json` only)
- ✅ Output structure matches specification
- ✅ Token estimation accurate within 10% margin
- ✅ Proper error handling (ValueError, TypeError)
- ✅ All methods properly documented with docstrings

## Files to Create

1. **`src/giljo_mcp/json_context_builder.py`** (150-200 lines)
   - Core utility class
   - Six instance variables (fields + content dicts)
   - Eight public methods
   - Comprehensive docstrings

2. **`tests/services/test_json_context_builder.py`** (300-400 lines)
   - Six test classes (Init, AddFields, AddContent, Build, EstimateTokens, EdgeCases)
   - 20+ test cases
   - Fixtures if needed for complex test data

## Integration Points

**Future Use Cases**:
- `get_orchestrator_instructions()` MCP tool (mission response structuring)
- `get_agent_mission()` MCP tool (agent-specific mission framing)
- Context prioritization service (priority × depth configuration)
- Token budget management (orchestrator context tracking)

**Related Handovers**:
- 0246a: Staging Workflow (931 token budget)
- 0312-0318: Context Management v2.0 (priority × depth model)
- 0347b: Mission Planner YAML Refactor (superseded - reverted to JSON)

## Notes

- **No YAML**: The YAML approach was explored and reverted. This handover uses pure JSON.
- **Stdlib Only**: Uses only `json` module from Python stdlib. No external dependencies.
- **Priority Framing**: The `priority_map` helps orchestrators understand field importance.
- **Token Estimation**: Simple 4-char-per-token heuristic. Sufficient for budget management.
- **Omit Empty**: Fields without content are omitted from tier dicts to reduce token usage.

---

**Next Steps After 0347a**:
- 0347b: Integrate JSONContextBuilder into mission planner
- 0347c: Add response fields to MCP tool outputs
- 0347d: Add depth toggle to agent templates (minimal/standard/full)
