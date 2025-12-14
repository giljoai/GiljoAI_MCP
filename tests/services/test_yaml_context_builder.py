"""
Test suite for YAMLContextBuilder utility class.

Tests follow RED-GREEN-REFACTOR cycle:
- Test priority map section generation
- Test critical section with inline content
- Test important section with condensed content
- Test reference section with summary only
- Test YAML validity and parseability
- Test token count estimation
"""

import yaml

from src.giljo_mcp.yaml_context_builder import YAMLContextBuilder


class TestYAMLContextBuilder:
    """Test suite for YAMLContextBuilder utility."""

    def test_priority_map_section(self):
        """Priority map lists fields in correct tiers."""
        builder = YAMLContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical("tech_stack")
        builder.add_important("architecture")
        builder.add_reference("vision_documents")

        yaml_output = builder.to_yaml()

        # Parse YAML and verify structure
        data = yaml.safe_load(yaml_output)
        assert "priorities" in data
        assert data["priorities"]["CRITICAL"] == ["product_core", "tech_stack"]
        assert data["priorities"]["IMPORTANT"] == ["architecture"]
        assert data["priorities"]["REFERENCE"] == ["vision_documents"]

    def test_critical_section_inline_content(self):
        """Full nested content in CRITICAL section."""
        builder = YAMLContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical_content(
            "product_core",
            {
                "name": "TinyContacts",
                "description": "Simple contact manager",
                "features": ["Add contacts", "Search contacts", "Export to CSV"],
            },
        )

        yaml_output = builder.to_yaml()

        # Parse and verify critical content is fully inline
        data = yaml.safe_load(yaml_output)
        assert "product_core" in data
        assert data["product_core"]["name"] == "TinyContacts"
        assert data["product_core"]["description"] == "Simple contact manager"
        assert len(data["product_core"]["features"]) == 3
        assert data["product_core"]["features"][0] == "Add contacts"

    def test_important_section_condensed_content(self):
        """Condensed content with fetch_details pointer."""
        builder = YAMLContextBuilder()
        builder.add_important("architecture")
        builder.add_important_content(
            "architecture",
            {"pattern": "Modular monolith", "fetch_details": "fetch_architecture()"},
        )

        yaml_output = builder.to_yaml()

        # Parse and verify important content has fetch pointer
        data = yaml.safe_load(yaml_output)
        assert "architecture" in data
        assert data["architecture"]["pattern"] == "Modular monolith"
        assert data["architecture"]["fetch_details"] == "fetch_architecture()"

    def test_reference_section_summary_only(self):
        """Only summary + fetch_tool in REFERENCE section."""
        builder = YAMLContextBuilder()
        builder.add_reference("vision_documents")
        builder.add_reference_content(
            "vision_documents",
            {
                "summary": "40K word product vision",
                "fetch_tool": "fetch_vision_document(page=N)",
            },
        )

        yaml_output = builder.to_yaml()

        # Parse and verify reference content has summary + fetch_tool
        data = yaml.safe_load(yaml_output)
        assert "vision_documents" in data
        assert data["vision_documents"]["summary"] == "40K word product vision"
        assert data["vision_documents"]["fetch_tool"] == "fetch_vision_document(page=N)"

    def test_yaml_is_valid_parseable(self):
        """PyYAML can parse generated output."""
        builder = YAMLContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical_content("product_core", {"name": "TestApp"})
        builder.add_important("architecture")
        builder.add_important_content("architecture", {"pattern": "Microservices", "fetch_details": "fetch_arch()"})
        builder.add_reference("vision_documents")
        builder.add_reference_content("vision_documents", {"summary": "Vision doc", "fetch_tool": "fetch_vision()"})

        yaml_output = builder.to_yaml()

        # Should not raise exception
        data = yaml.safe_load(yaml_output)

        # Verify all sections present
        assert "priorities" in data
        assert "product_core" in data
        assert "architecture" in data
        assert "vision_documents" in data

    def test_token_count_estimate(self):
        """Token estimate uses 1 token ≈ 4 characters formula."""
        builder = YAMLContextBuilder()
        builder.add_critical("product_core")
        builder.add_critical_content(
            "product_core",
            {
                "name": "TestApp",
                "description": "A test application for token counting",
            },
        )

        yaml_output = builder.to_yaml()
        estimated_tokens = builder.estimate_tokens()

        # Token estimate should be roughly len(yaml_output) // 4
        expected_tokens = len(yaml_output) // 4
        # Allow 10% variance due to rounding
        assert abs(estimated_tokens - expected_tokens) <= max(1, expected_tokens * 0.1)

        # Token count should be reasonable (not zero, not absurd)
        assert estimated_tokens > 0
        assert estimated_tokens < 10000  # Sanity check
