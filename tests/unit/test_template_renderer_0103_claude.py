# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Unit tests for render_claude_agent() — YAML frontmatter + markdown body.

Split from test_template_renderer_0103.py (Handover 0103 Phase 8).
Tests Claude Code YAML format rendering with comprehensive coverage of
defaults, edge cases, and structural validation.
"""

import yaml

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.template_renderer import render_claude_agent


class TestRenderClaudeAgent:
    """Test Claude Code YAML format rendering."""

    def test_basic_render_all_fields(self):
        """Test complete template with all fields populated."""
        template = AgentTemplate(
            name="orchestrator",
            role="orchestrator",
            cli_tool="claude",
            description="Test orchestrator agent",
            system_instructions="You are an orchestrator managing complex projects.",
            model="sonnet",
            behavioral_rules=["Rule 1: Plan first", "Rule 2: Communicate clearly"],
            success_criteria=["Criterion 1: All tests pass", "Criterion 2: Code is clean"],
        )

        result = render_claude_agent(template)

        # Verify YAML frontmatter structure
        assert result.startswith("---\n")
        assert "---\n\n" in result  # Closing delimiter with body separator

        # Extract frontmatter for detailed verification
        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)

        assert frontmatter["name"] == "orchestrator"
        assert frontmatter["description"] == "Test orchestrator agent"
        assert frontmatter["model"] == "sonnet"
        assert "tools" not in frontmatter  # CRITICAL: tools field omitted

        # Verify markdown body
        assert "You are an orchestrator managing complex projects." in result
        assert "## Behavioral Rules" in result
        assert "- Rule 1: Plan first" in result
        assert "- Rule 2: Communicate clearly" in result
        assert "## Success Criteria" in result
        assert "- Criterion 1: All tests pass" in result
        assert "- Criterion 2: Code is clean" in result

    def test_default_description(self):
        """Test description defaults to 'Subagent for {role}' when not provided."""
        template = AgentTemplate(
            name="tester",
            role="tester",
            cli_tool="claude",
            description=None,  # Should default
            system_instructions="Test all code thoroughly.",
            model="sonnet",
        )

        result = render_claude_agent(template)

        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)

        assert frontmatter["description"] == "Subagent for tester"

    def test_default_description_empty_string(self):
        """Test description defaults when empty string provided."""
        template = AgentTemplate(
            name="reviewer",
            role="reviewer",
            cli_tool="claude",
            description="",  # Empty string should default
            system_instructions="Review code for quality.",
            model="sonnet",
        )

        result = render_claude_agent(template)

        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)

        assert frontmatter["description"] == "Subagent for reviewer"

    def test_default_model(self):
        """Test model defaults to 'sonnet' when not provided."""
        template = AgentTemplate(
            name="implementer",
            role="implementer",
            cli_tool="claude",
            description="Implementer agent",
            system_instructions="Implement features following TDD.",
            model=None,  # Should default to sonnet
        )

        result = render_claude_agent(template)

        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)

        assert frontmatter["model"] == "sonnet"

    def test_default_model_empty_string(self):
        """Test model defaults to sonnet when empty string provided."""
        template = AgentTemplate(
            name="analyzer",
            role="analyzer",
            cli_tool="claude",
            description="Analyzer agent",
            system_instructions="Analyze code for issues.",
            model="",  # Empty string should default
        )

        result = render_claude_agent(template)

        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)

        assert frontmatter["model"] == "sonnet"

    def test_custom_model_opus(self):
        """Test custom model 'opus' is preserved."""
        template = AgentTemplate(
            name="complex-analyzer",
            role="analyzer",
            cli_tool="claude",
            description="Complex analysis agent",
            system_instructions="Perform deep analysis.",
            model="opus",
        )

        result = render_claude_agent(template)

        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)

        assert frontmatter["model"] == "opus"

    def test_custom_model_haiku(self):
        """Test custom model 'haiku' is preserved."""
        template = AgentTemplate(
            name="quick-checker",
            role="checker",
            cli_tool="claude",
            description="Quick checker agent",
            system_instructions="Perform quick checks.",
            model="haiku",
        )

        result = render_claude_agent(template)

        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)

        assert frontmatter["model"] == "haiku"

    def test_without_behavioral_rules(self):
        """Test template without behavioral_rules section."""
        template = AgentTemplate(
            name="analyzer",
            role="analyzer",
            cli_tool="claude",
            description="Analyzer agent",
            system_instructions="Analyze code patterns.",
            model="opus",
            behavioral_rules=[],  # Empty list
            success_criteria=["Criterion 1: Report generated"],
        )

        result = render_claude_agent(template)

        assert "## Behavioral Rules" not in result
        assert "## Success Criteria" in result
        assert "- Criterion 1: Report generated" in result

    def test_without_behavioral_rules_none(self):
        """Test template with behavioral_rules as None."""
        template = AgentTemplate(
            name="simple-agent",
            role="simple",
            cli_tool="claude",
            description="Simple agent",
            system_instructions="Perform simple tasks.",
            model="sonnet",
            behavioral_rules=None,  # None instead of empty list
            success_criteria=["Done"],
        )

        result = render_claude_agent(template)

        assert "## Behavioral Rules" not in result
        assert "## Success Criteria" in result

    def test_without_success_criteria(self):
        """Test template without success_criteria section."""
        template = AgentTemplate(
            name="builder",
            role="builder",
            cli_tool="claude",
            description="Builder agent",
            system_instructions="Build components.",
            model="sonnet",
            behavioral_rules=["Rule 1: Follow standards"],
            success_criteria=[],  # Empty list
        )

        result = render_claude_agent(template)

        assert "## Behavioral Rules" in result
        assert "- Rule 1: Follow standards" in result
        assert "## Success Criteria" not in result

    def test_without_success_criteria_none(self):
        """Test template with success_criteria as None."""
        template = AgentTemplate(
            name="another-agent",
            role="worker",
            cli_tool="claude",
            description="Worker agent",
            system_instructions="Do work.",
            model="sonnet",
            behavioral_rules=["Work hard"],
            success_criteria=None,  # None instead of empty list
        )

        result = render_claude_agent(template)

        assert "## Behavioral Rules" in result
        assert "## Success Criteria" not in result

    def test_without_both_rules_and_criteria(self):
        """Test minimal template without behavioral rules or success criteria."""
        template = AgentTemplate(
            name="minimal",
            role="minimal",
            cli_tool="claude",
            description="Minimal agent",
            system_instructions="Minimal prompt content.",
            model="sonnet",
            behavioral_rules=[],
            success_criteria=[],
        )

        result = render_claude_agent(template)

        # Verify structure
        assert result.startswith("---\n")
        assert "Minimal prompt content." in result
        assert "## Behavioral Rules" not in result
        assert "## Success Criteria" not in result

    def test_yaml_frontmatter_structure(self):
        """Test YAML frontmatter has correct triple-dash delimiters."""
        template = AgentTemplate(
            name="test",
            role="test",
            cli_tool="claude",
            description="Test",
            system_instructions="Content",
            model="sonnet",
        )

        result = render_claude_agent(template)

        lines = result.split("\n")
        assert lines[0] == "---"  # Opening delimiter
        # Find closing delimiter
        closing_idx = None
        for i, line in enumerate(lines[1:], 1):
            if line == "---":
                closing_idx = i
                break
        assert closing_idx is not None
        assert lines[closing_idx + 1] == ""  # Empty line after closing

    def test_tools_field_omitted_not_null(self):
        """CRITICAL: Verify tools field is completely omitted, not set to null."""
        template = AgentTemplate(
            name="test",
            role="test",
            cli_tool="claude",
            description="Test",
            system_instructions="Content",
            model="sonnet",
        )

        result = render_claude_agent(template)

        # Extract YAML frontmatter
        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)

        # Verify tools key does not exist at all
        assert "tools" not in frontmatter
        assert "tools" not in yaml_section  # Not even in raw text

    def test_empty_system_instructions(self):
        """Test template with empty system_instructions."""
        template = AgentTemplate(
            name="empty-content",
            role="empty",
            cli_tool="claude",
            description="Empty content test",
            system_instructions="",  # Empty string
            model="sonnet",
        )

        result = render_claude_agent(template)

        # Should still have YAML header
        assert result.startswith("---\n")
        # Body should just be empty or whitespace
        body_section = result.split("---\n\n")[1]
        assert body_section.strip() == ""

    def test_none_system_instructions(self):
        """Test template with None system_instructions."""
        template = AgentTemplate(
            name="none-content",
            role="none",
            cli_tool="claude",
            description="None content test",
            system_instructions=None,  # None
            model="sonnet",
        )

        result = render_claude_agent(template)

        # Should still have YAML header
        assert result.startswith("---\n")
        # Body should be empty
        body_section = result.split("---\n\n")[1]
        assert body_section.strip() == ""

    def test_description_without_role(self):
        """Test default description when role is None."""
        template = AgentTemplate(
            name="no-role",
            role=None,  # No role
            cli_tool="claude",
            description=None,  # Should default
            system_instructions="Content",
            model="sonnet",
        )

        result = render_claude_agent(template)

        yaml_section = result.split("---\n")[1]
        frontmatter = yaml.safe_load(yaml_section)

        # Should fallback to "Subagent" when no role
        assert frontmatter["description"] == "Subagent"
