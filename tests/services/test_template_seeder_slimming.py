"""
Test suite for template slimming (Handover 0353).

Tests cover:
- Seeded templates contain MCP wiring section
- Seeded templates contain role-specific guidance
- Seeded templates reference get_agent_mission + full_protocol
- Seeded templates DO NOT contain embedded lifecycle phases
- Seeded templates DO NOT contain detailed check-in pseudo-code
- Seeded templates DO NOT contain inter-agent messaging pseudo-code

TDD Approach:
- RED: Write failing tests first (this file)
- GREEN: Implement minimal code to pass
- REFACTOR: Clean up while keeping tests green
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Import functions under test
from src.giljo_mcp.template_seeder import (
    _get_mcp_coordination_section,
    _get_check_in_protocol_section,
    _get_agent_messaging_protocol_section,
    _get_default_templates_v103,
)


class TestMCPCoordinationSectionSlimming:
    """Test MCP coordination section keeps essential wiring, removes lifecycle duplication."""

    def test_mcp_section_contains_critical_native_tools_warning(self):
        """MCP section must contain the CRITICAL native tools warning."""
        section = _get_mcp_coordination_section()
        assert "CRITICAL" in section
        assert "MCP TOOLS ARE NATIVE" in section or "MCP tools" in section.lower()
        assert "native" in section.lower()

    def test_mcp_section_contains_get_agent_mission_reference(self):
        """MCP section must reference get_agent_mission tool."""
        section = _get_mcp_coordination_section()
        assert "get_agent_mission" in section

    def test_mcp_section_contains_full_protocol_reference(self):
        """MCP section must reference full_protocol for lifecycle behavior."""
        section = _get_mcp_coordination_section()
        assert "full_protocol" in section

    def test_mcp_section_contains_bootstrap_sequence(self):
        """MCP section must contain bootstrap sequence pointing to get_agent_mission."""
        section = _get_mcp_coordination_section()
        # Should have a bootstrap/startup section
        assert "bootstrap" in section.lower() or "startup" in section.lower() or "before any work" in section.lower()

    def test_mcp_section_references_key_mcp_tools(self):
        """MCP section should list key MCP tools (report_progress, complete_job, etc.)."""
        section = _get_mcp_coordination_section()
        assert "report_progress" in section
        assert "complete_job" in section


class TestCheckInProtocolSectionSlimming:
    """Test check-in protocol section is slimmed (no detailed pseudo-code)."""

    def test_check_in_section_does_not_contain_detailed_python_code(self):
        """
        Check-in section should NOT contain detailed Python pseudo-code.

        Per Handover 0353: Remove CHECK-IN PROTOCOL pseudo-code, behavior now in full_protocol.
        """
        section = _get_check_in_protocol_section()

        # Should NOT have detailed Python code blocks with imports
        assert "import time" not in section, "Check-in section should not contain Python import statements"

        # Should NOT have Python while loops
        assert "while True:" not in section, "Check-in section should not contain Python while loops"

        # Should NOT have Python for loops with detailed logic
        detailed_loop_indicators = [
            "for attempt in range",
            "for msg in messages",
        ]
        for indicator in detailed_loop_indicators:
            assert indicator not in section, f"Check-in section should not contain '{indicator}'"

    def test_check_in_section_references_full_protocol_for_behavior(self):
        """Check-in section should direct agents to full_protocol for detailed behavior."""
        section = _get_check_in_protocol_section()
        # Should mention that behavior is in full_protocol, or be very brief
        assert "full_protocol" in section or len(section) < 500, \
            "Check-in section should either reference full_protocol or be very brief"


class TestAgentMessagingProtocolSlimming:
    """Test agent messaging protocol is slimmed (no detailed pseudo-code)."""

    def test_messaging_section_does_not_contain_detailed_python_code(self):
        """
        Messaging section should NOT contain detailed Python pseudo-code.

        Per Handover 0353: Remove inter-agent messaging pseudo-code, behavior now in full_protocol.
        """
        section = _get_agent_messaging_protocol_section()

        # Should NOT have Python import statements
        assert "import time" not in section, "Messaging section should not contain Python imports"

        # Should NOT have detailed Python loops with sleep
        assert "time.sleep" not in section, "Messaging section should not contain time.sleep"

        # Should NOT have multi-line Python code blocks with complex logic
        complex_indicators = [
            "for attempt in range(10):",
            "while True:",
            "for msg in messages.get",
        ]
        for indicator in complex_indicators:
            assert indicator not in section, f"Messaging section should not contain '{indicator}'"

    def test_messaging_section_does_not_duplicate_checkpoint_protocol(self):
        """
        Messaging section should NOT have CHECKPOINT 1-4 detailed pseudo-code.

        Per Handover 0353: Behavior now in full_protocol.
        """
        section = _get_agent_messaging_protocol_section()

        # Should NOT have detailed CHECKPOINT sections with code
        checkpoint_markers = [
            "### CHECKPOINT 1:",
            "### CHECKPOINT 2:",
            "### CHECKPOINT 3:",
            "### CHECKPOINT 4:",
        ]
        for marker in checkpoint_markers:
            assert marker not in section, f"Messaging section should not contain '{marker}'"

    def test_messaging_section_references_full_protocol_or_is_brief(self):
        """Messaging section should reference full_protocol or be very brief."""
        section = _get_agent_messaging_protocol_section()
        # Either it mentions full_protocol, or it's very brief (< 500 chars)
        assert "full_protocol" in section or len(section) < 500, \
            "Messaging section should either reference full_protocol or be very brief"


class TestDefaultTemplatesSlimming:
    """Test that default template definitions are appropriately slim."""

    def test_implementer_template_contains_role_guidance(self):
        """Implementer template must contain role-specific guidance."""
        templates = _get_default_templates_v103()
        implementer = next((t for t in templates if t["role"] == "implementer"), None)
        assert implementer is not None, "Implementer template must exist"

        content = implementer["template_content"]
        # Should have role-specific text
        assert "implement" in content.lower() or "code" in content.lower()

    def test_tester_template_contains_role_guidance(self):
        """Tester template must contain role-specific guidance."""
        templates = _get_default_templates_v103()
        tester = next((t for t in templates if t["role"] == "tester"), None)
        assert tester is not None, "Tester template must exist"

        content = tester["template_content"]
        # Should have role-specific text
        assert "test" in content.lower()

    def test_analyzer_template_contains_role_guidance(self):
        """Analyzer template must contain role-specific guidance."""
        templates = _get_default_templates_v103()
        analyzer = next((t for t in templates if t["role"] == "analyzer"), None)
        assert analyzer is not None, "Analyzer template must exist"

        content = analyzer["template_content"]
        # Should have role-specific text
        assert "analy" in content.lower()  # analyze, analysis

    def test_documenter_template_contains_role_guidance(self):
        """Documenter template must contain role-specific guidance."""
        templates = _get_default_templates_v103()
        documenter = next((t for t in templates if t["role"] == "documenter"), None)
        assert documenter is not None, "Documenter template must exist"

        content = documenter["template_content"]
        # Should have role-specific text
        assert "document" in content.lower()

    def test_templates_do_not_embed_full_lifecycle_phases(self):
        """
        Templates should NOT embed full lifecycle phases.

        Per Handover 0353: Lifecycle phases belong in full_protocol, not templates.
        """
        templates = _get_default_templates_v103()

        for template in templates:
            if template["role"] == "orchestrator":
                continue  # Orchestrator is system-managed, skip

            content = template["template_content"]

            # Templates should NOT have Phase 1-5 headers
            lifecycle_headers = [
                "### Phase 1:",
                "### Phase 2:",
                "### Phase 3:",
                "### Phase 4:",
                "### Phase 5:",
                "### Phase 6:",
            ]
            for header in lifecycle_headers:
                assert header not in content, \
                    f"Template '{template['role']}' should not contain lifecycle header '{header}'"


class TestTeamContextNote:
    """Test that templates mention team context comes from mission."""

    def test_mcp_section_mentions_team_info_from_mission(self):
        """
        MCP section should mention that team information comes from mission text.

        Per Handover 0353: Templates should note that team/dependency info is in mission.
        """
        section = _get_mcp_coordination_section()

        # Should mention that mission contains team info, or reference full_protocol/mission
        team_related_phrases = [
            "team",
            "mission",
            "full_protocol",
        ]
        has_team_reference = any(phrase in section.lower() for phrase in team_related_phrases)
        assert has_team_reference, \
            "MCP section should reference mission/team context or full_protocol"
