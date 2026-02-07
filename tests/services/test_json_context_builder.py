"""TDD tests for JSONContextBuilder utility class.

Tests structured JSON context building with priority framing for
orchestrator missions. Uses only stdlib json (no PyYAML dependency).

Handover: 0347a - JSON Context Builder
"""

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

    def test_add_field_none_raises_error(self):
        """Should raise ValueError for None field name."""
        builder = JSONContextBuilder()
        with pytest.raises(ValueError, match="Field name cannot be empty"):
            builder.add_critical(None)

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

    def test_add_field_critical_to_reference_raises_error(self):
        """Should raise ValueError for critical field added to reference."""
        builder = JSONContextBuilder()
        builder.add_critical("shared_field")
        with pytest.raises(ValueError, match="already exists"):
            builder.add_reference("shared_field")


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

    def test_add_content_integer(self):
        """Should add integer content to field."""
        builder = JSONContextBuilder()
        builder.add_critical("version")
        builder.add_critical_content("version", 42)
        assert builder.critical_content["version"] == 42

    def test_add_content_boolean(self):
        """Should add boolean content to field."""
        builder = JSONContextBuilder()
        builder.add_important("enabled")
        builder.add_important_content("enabled", True)
        assert builder.important_content["enabled"] is True

    def test_add_content_null(self):
        """Should add None/null content to field."""
        builder = JSONContextBuilder()
        builder.add_reference("optional")
        builder.add_reference_content("optional", None)
        assert builder.reference_content["optional"] is None

    def test_add_content_to_nonexistent_field_raises_error(self):
        """Should raise ValueError when adding content to unregistered field."""
        builder = JSONContextBuilder()
        with pytest.raises(ValueError, match="not in critical_fields"):
            builder.add_critical_content("unknown_field", {"data": "test"})

    def test_add_content_to_nonexistent_important_field_raises_error(self):
        """Should raise ValueError for unregistered important field."""
        builder = JSONContextBuilder()
        with pytest.raises(ValueError, match="not in important_fields"):
            builder.add_important_content("unknown", {"data": "test"})

    def test_add_content_to_nonexistent_reference_field_raises_error(self):
        """Should raise ValueError for unregistered reference field."""
        builder = JSONContextBuilder()
        with pytest.raises(ValueError, match="not in reference_fields"):
            builder.add_reference_content("unknown", {"data": "test"})

    def test_add_non_serializable_content_raises_error(self):
        """Should raise TypeError for non-JSON-serializable content."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")

        # Try to add non-serializable object (e.g., function)
        with pytest.raises(TypeError):
            builder.add_critical_content("product_core", lambda x: x)

    def test_add_non_serializable_set_raises_error(self):
        """Should raise TypeError for set (not JSON-serializable)."""
        builder = JSONContextBuilder()
        builder.add_critical("tags")

        with pytest.raises(TypeError):
            builder.add_critical_content("tags", {"tag1", "tag2"})


class TestBuild:
    """Test building the complete JSON structure."""

    def test_build_empty_structure(self):
        """Should build valid structure with empty content."""
        builder = JSONContextBuilder()
        result = builder.build()

        assert "priority_map" in result
        assert result["priority_map"] == {"critical": [], "important": [], "reference": []}
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

    def test_build_preserves_order(self):
        """Should preserve field order in priority_map."""
        builder = JSONContextBuilder()
        builder.add_critical("field_a")
        builder.add_critical("field_b")
        builder.add_critical("field_c")

        result = builder.build()
        assert result["priority_map"]["critical"] == ["field_a", "field_b", "field_c"]


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
        builder.add_critical_content(
            "product_core",
            {
                "name": "GiljoAI MCP",
                "description": "Multi-tenant agent orchestration server",
                "features": ["context prioritization", "agent coordination"],
            },
        )

        tokens = builder.estimate_tokens()

        # Should be proportional to content (1 token ~ 4 chars)
        json_str = json.dumps(builder.build())
        expected_tokens = len(json_str) // 4

        # Allow 10% margin for approximation
        assert abs(tokens - expected_tokens) <= expected_tokens * 0.1 + 1

    def test_estimate_tokens_large_structure(self):
        """Should handle token estimation for large structures."""
        builder = JSONContextBuilder()

        # Add multiple fields with substantial content
        for i in range(5):
            field_name = f"field_{i}"
            builder.add_critical(field_name)
            builder.add_critical_content(
                field_name,
                {
                    "data": ["item"] * 100,  # Large list
                    "description": "x" * 1000,  # Long string
                },
            )

        tokens = builder.estimate_tokens()

        # Should be substantial (>1000 tokens)
        assert tokens > 1000

    def test_estimate_tokens_matches_json_length(self):
        """Token estimate should match len(json.dumps()) // 4."""
        builder = JSONContextBuilder()
        builder.add_critical("test")
        builder.add_critical_content("test", {"key": "value"})

        result = builder.build()
        expected = len(json.dumps(result)) // 4
        actual = builder.estimate_tokens()

        assert actual == expected


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_multiple_fields_same_tier(self):
        """Should support multiple fields in same tier."""
        builder = JSONContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical("tech_stack")
        builder.add_critical("project_description")

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
            "level1": {"level2": {"level3": {"data": ["item1", "item2"], "metadata": {"count": 2, "valid": True}}}}
        }

        builder.add_critical_content("complex", nested_content)
        result = builder.build()

        assert result["critical"]["complex"]["level1"]["level2"]["level3"]["data"] == ["item1", "item2"]

    def test_unicode_content(self):
        """Should handle Unicode content correctly."""
        builder = JSONContextBuilder()
        builder.add_critical("i18n")
        builder.add_critical_content("i18n", {"greeting": "Hello World", "japanese": "こんにちは", "emoji": "Test"})

        result = builder.build()
        json_str = json.dumps(result, ensure_ascii=False)
        assert "こんにちは" in json_str

    def test_empty_dict_content(self):
        """Should accept empty dict as valid content."""
        builder = JSONContextBuilder()
        builder.add_critical("empty")
        builder.add_critical_content("empty", {})

        result = builder.build()
        assert result["critical"]["empty"] == {}

    def test_empty_list_content(self):
        """Should accept empty list as valid content."""
        builder = JSONContextBuilder()
        builder.add_important("items")
        builder.add_important_content("items", [])

        result = builder.build()
        assert result["important"]["items"] == []

    def test_overwrite_content(self):
        """Should allow overwriting existing content."""
        builder = JSONContextBuilder()
        builder.add_critical("field")
        builder.add_critical_content("field", {"version": 1})
        builder.add_critical_content("field", {"version": 2})

        result = builder.build()
        assert result["critical"]["field"]["version"] == 2


class TestRealWorldScenarios:
    """Test real-world usage scenarios from the orchestrator."""

    def test_orchestrator_mission_structure(self):
        """Should build a complete orchestrator mission structure."""
        builder = JSONContextBuilder()

        # Critical fields (always inline)
        builder.add_critical("product_core")
        builder.add_critical("tech_stack")
        builder.add_critical_content(
            "product_core",
            {
                "name": "TinyContacts",
                "type": "Contact management application",
                "key_features": ["Photo uploads", "Date tracking", "Tags", "Fuzzy search"],
            },
        )
        builder.add_critical_content(
            "tech_stack",
            {
                "languages": ["Python 3.11+", "TypeScript 5.0+"],
                "backend": ["FastAPI", "SQLAlchemy"],
                "frontend": ["React 18", "Tailwind CSS"],
                "database": {"dev": "SQLite", "prod": "PostgreSQL"},
            },
        )

        # Important fields (condensed)
        builder.add_important("architecture")
        builder.add_important("testing")
        builder.add_important("agent_templates")
        builder.add_important_content(
            "architecture",
            {
                "pattern": "Modular monolith with service layer",
                "api": "REST + OpenAPI 3.0",
                "fetch_details": "fetch_architecture()",
            },
        )
        builder.add_important_content("testing", {"target": "80% coverage", "approach": "TDD"})
        builder.add_important_content(
            "agent_templates", {"discovery_tool": "get_available_agents()", "note": "Fetch agent details on-demand"}
        )

        # Reference fields (summary + fetch pointer)
        builder.add_reference("vision_documents")
        builder.add_reference("memory_360")
        builder.add_reference("git_history")
        builder.add_reference_content(
            "vision_documents",
            {
                "available": True,
                "depth_setting": "moderate",
                "estimated_tokens": 12500,
                "summary": "40K word product vision - UX, specs, benefits",
                "fetch_tool": "fetch_vision_document(page=N)",
            },
        )
        builder.add_reference_content(
            "memory_360",
            {"projects": 3, "status": "3 completed projects in history", "fetch_tool": "fetch_360_memory(limit=5)"},
        )
        builder.add_reference_content("git_history", {"commits": 25, "fetch_tool": "fetch_git_history(limit=25)"})

        result = builder.build()

        # Verify structure
        assert "priority_map" in result
        assert len(result["priority_map"]["critical"]) == 2
        assert len(result["priority_map"]["important"]) == 3
        assert len(result["priority_map"]["reference"]) == 3

        # Verify critical content
        assert result["critical"]["product_core"]["name"] == "TinyContacts"
        assert "FastAPI" in result["critical"]["tech_stack"]["backend"]

        # Verify reference has fetch pointers
        assert "fetch_tool" in result["reference"]["vision_documents"]

        # Verify token budget (should be < 2000 tokens)
        tokens = builder.estimate_tokens()
        assert tokens < 2000, f"Token count {tokens} exceeds 2000 budget"

    def test_minimal_mission_structure(self):
        """Should build a minimal mission for lightweight agents."""
        builder = JSONContextBuilder()

        builder.add_critical("task")
        builder.add_critical_content("task", {"action": "Fix typo in README", "file": "README.md", "line": 42})

        result = builder.build()
        tokens = builder.estimate_tokens()

        assert tokens < 100
        assert result["priority_map"]["important"] == []
        assert result["priority_map"]["reference"] == []
