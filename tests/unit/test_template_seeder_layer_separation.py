"""
Tests for Template Seeder Layer 3 separation.

This test verifies that database templates focus on role-specific
expertise and DO NOT contain MCP protocol details, which are handled
separately by the MCP coordination section.

Handover 0371a: Template Dead Code Removal & Test Remediation
"""

from src.giljo_mcp.template_seeder import _get_template_metadata


class TestLayer3TemplateSeparation:
    """Test that templates don't contain MCP protocol details in role-specific content."""

    def test_templates_have_no_mcp_commands(self):
        """Database templates should NOT contain MCP command references.

        Layer 3 (database templates) should focus on:
        - WHAT to do (role-specific expertise)
        - Success criteria for the role
        - Behavioral expectations

        MCP coordination section handles:
        - HOW to communicate (MCP commands)
        - Communication with orchestrator
        """
        templates = _get_template_metadata()

        # MCP commands that should NOT appear in Layer 3 templates
        mcp_commands = [
            "acknowledge_job",
            "report_progress",
            "get_next_instruction",
            "complete_job",
            "report_error",
            "send_message",
            "receive_messages",  # obsolete command
            "update_job_progress",  # obsolete command
        ]

        # Check each template's content
        for agent_display_name, template_def in templates.items():
            behavioral_rules = template_def.get("behavioral_rules", [])
            success_criteria = template_def.get("success_criteria", [])

            # Convert to strings for checking
            rules_text = " ".join(behavioral_rules)
            criteria_text = " ".join(success_criteria)
            combined_text = rules_text + " " + criteria_text

            for command in mcp_commands:
                assert command not in combined_text.lower(), (
                    f"Found MCP command '{command}' in {agent_display_name} template. "
                    f"Templates should focus on role expertise, not MCP protocol. "
                    f"MCP commands belong in the MCP coordination section."
                )

    def test_templates_focus_on_role_expertise(self):
        """Templates should contain role-specific guidance, not protocol details."""
        templates = _get_template_metadata()

        # Each template should have role-specific behavioral rules
        for agent_display_name, template_def in templates.items():
            behavioral_rules = template_def.get("behavioral_rules", [])

            assert len(behavioral_rules) > 0, f"{agent_display_name} has no behavioral rules"

            # Rules should focus on "what to do" not "how to communicate"
            # Check for role-specific keywords (not exhaustive, just examples)
            rules_text = " ".join(behavioral_rules).lower()

            # Should NOT be all about MCP protocol
            protocol_keywords = ["mcp", "tool", "call", "checkpoint"]
            protocol_count = sum(1 for keyword in protocol_keywords if keyword in rules_text)

            # Should have role-specific content
            assert protocol_count < len(behavioral_rules), (
                f"{agent_display_name} template is too focused on protocol, not role expertise"
            )
