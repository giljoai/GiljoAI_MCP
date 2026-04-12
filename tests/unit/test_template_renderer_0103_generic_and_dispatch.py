# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Unit tests for render_generic_agent() and render_template() dispatcher.

Split from test_template_renderer_0103.py (Handover 0103 Phase 8).
Tests generic plaintext format rendering and the dispatcher logic that
routes to the correct renderer based on cli_tool.
"""

import yaml

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_renderer import (
    render_generic_agent,
    render_template,
)


class TestRenderGenericAgent:
    """Test generic plaintext format rendering."""

    def test_basic_render_all_fields(self):
        """Test complete generic template with all fields."""
        template = AgentTemplate(
            name="codex-implementer",
            role="implementer",
            cli_tool="codex",
            description="Codex implementer agent",
            system_instructions="Implement features with TDD approach.",
            behavioral_rules=["Rule 1: Write tests first", "Rule 2: Keep code clean"],
            success_criteria=["Criterion 1: All tests pass"],
        )

        result = render_generic_agent(template)

        # Verify plaintext format (no YAML)
        assert result.startswith("# codex-implementer")
        assert "**Role:**implementer" in result
        assert "Implement features with TDD approach." in result
        assert "## Behavioral Rules" in result
        assert "- Rule 1: Write tests first" in result
        assert "- Rule 2: Keep code clean" in result
        assert "## Success Criteria" in result
        assert "- Criterion 1: All tests pass" in result
        assert "---" not in result  # No YAML delimiters

    def test_without_behavioral_rules(self):
        """Test generic template without behavioral rules."""
        template = AgentTemplate(
            name="gemini-tester",
            role="tester",
            cli_tool="gemini",
            system_instructions="Write comprehensive tests.",
            behavioral_rules=[],
            success_criteria=["Tests cover edge cases"],
        )

        result = render_generic_agent(template)

        assert "# gemini-tester" in result
        assert "**Role:**tester" in result
        assert "Write comprehensive tests." in result
        assert "## Behavioral Rules" not in result
        assert "## Success Criteria" in result

    def test_without_success_criteria(self):
        """Test generic template without success criteria."""
        template = AgentTemplate(
            name="generic-analyzer",
            role="analyzer",
            cli_tool="generic",
            system_instructions="Analyze code quality.",
            behavioral_rules=["Follow coding standards"],
            success_criteria=[],
        )

        result = render_generic_agent(template)

        assert "# generic-analyzer" in result
        assert "## Behavioral Rules" in result
        assert "- Follow coding standards" in result
        assert "## Success Criteria" not in result

    def test_minimal_template(self):
        """Test minimal generic template."""
        template = AgentTemplate(
            name="simple",
            role="simple",
            cli_tool="codex",
            system_instructions="Simple content.",
            behavioral_rules=None,
            success_criteria=None,
        )

        result = render_generic_agent(template)

        assert result.startswith("# simple")
        assert "**Role:**simple" in result
        assert "Simple content." in result
        assert "## Behavioral Rules" not in result
        assert "## Success Criteria" not in result

    def test_plaintext_format_no_yaml(self):
        """Verify output is plaintext with no YAML structure."""
        template = AgentTemplate(
            name="test-agent",
            role="test",
            cli_tool="generic",
            system_instructions="Test content",
        )

        result = render_generic_agent(template)

        # No YAML delimiters
        assert not result.startswith("---")
        assert "---\n" not in result
        # No model field
        assert "model:" not in result
        # Has plaintext header
        assert result.startswith("# test-agent")


class TestRenderTemplate:
    """Test dispatcher logic for render_template()."""

    def test_dispatch_claude(self):
        """Test cli_tool='claude' dispatches to render_claude_agent()."""
        template = AgentTemplate(
            name="orchestrator",
            role="orchestrator",
            cli_tool="claude",
            description="Test",
            system_instructions="Orchestrate projects.",
            model="sonnet",
        )

        result = render_template(template)

        # Should be YAML format
        assert result.startswith("---\n")
        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)
        assert frontmatter["name"] == "orchestrator"
        assert frontmatter["model"] == "sonnet"

    def test_dispatch_codex(self):
        """Test cli_tool='codex' dispatches to render_generic_agent()."""
        template = AgentTemplate(
            name="implementer",
            role="implementer",
            cli_tool="codex",
            system_instructions="Implement features.",
        )

        result = render_template(template)

        # Should be plaintext format
        assert result.startswith("# implementer")
        assert "**Role:**implementer" in result
        assert "---" not in result  # No YAML

    def test_dispatch_gemini(self):
        """Test cli_tool='gemini' dispatches to render_generic_agent()."""
        template = AgentTemplate(
            name="tester",
            role="tester",
            cli_tool="gemini",
            system_instructions="Write tests.",
        )

        result = render_template(template)

        # Should be plaintext format
        assert result.startswith("# tester")
        assert "**Role:**tester" in result
        assert "---" not in result

    def test_dispatch_generic(self):
        """Test cli_tool='generic' dispatches to render_generic_agent()."""
        template = AgentTemplate(
            name="analyzer",
            role="analyzer",
            cli_tool="generic",
            system_instructions="Analyze code.",
        )

        result = render_template(template)

        # Should be plaintext format
        assert result.startswith("# analyzer")
        assert "**Role:**analyzer" in result
        assert "---" not in result

    def test_dispatch_none_fallback(self):
        """Test cli_tool=None falls back to render_claude_agent()."""
        template = AgentTemplate(
            name="fallback-agent",
            role="fallback",
            cli_tool=None,  # No CLI tool specified
            description="Fallback test",
            system_instructions="Fallback content.",
            model="sonnet",
        )

        result = render_template(template)

        # Should use Claude format (fallback)
        assert result.startswith("---\n")
        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)
        assert frontmatter["name"] == "fallback-agent"

    def test_dispatch_unknown_fallback(self):
        """Test unknown cli_tool falls back to render_claude_agent()."""
        template = AgentTemplate(
            name="unknown-agent",
            role="unknown",
            cli_tool="unknown-tool",  # Unknown tool
            description="Unknown test",
            system_instructions="Unknown content.",
            model="sonnet",
        )

        result = render_template(template)

        # Should use Claude format (fallback)
        assert result.startswith("---\n")
        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)
        assert frontmatter["name"] == "unknown-agent"

    def test_dispatch_empty_string_fallback(self):
        """Test cli_tool='' (empty string) falls back to render_claude_agent()."""
        template = AgentTemplate(
            name="empty-agent",
            role="empty",
            cli_tool="",  # Empty string
            description="Empty test",
            system_instructions="Empty content.",
            model="sonnet",
        )

        result = render_template(template)

        # Should use Claude format (fallback)
        assert result.startswith("---\n")
        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)
        assert frontmatter["name"] == "empty-agent"
