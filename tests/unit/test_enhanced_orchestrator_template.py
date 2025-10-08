"""
Test suite for enhanced orchestrator template.
Tests ensure the template includes discovery-first workflow,
30-80-10 principle, 3-tool rule, and after-action documentation.
"""

import pytest
from pathlib import Path

from src.giljo_mcp.template_manager import UnifiedTemplateManager


class TestEnhancedOrchestratorTemplate:
    """Test enhanced orchestrator template features."""

    @pytest.fixture
    def template_manager(self):
        """Create template manager instance."""
        return UnifiedTemplateManager(db_manager=None)

    @pytest.fixture
    def orchestrator_template(self, template_manager):
        """Get orchestrator template content."""
        return template_manager._legacy_templates["orchestrator"]

    def test_template_has_discovery_first_workflow(self, orchestrator_template):
        """Test that template includes discovery-first workflow."""
        # Discovery steps should be present and in correct order
        assert "Step 1: Serena MCP First" in orchestrator_template
        assert "Step 2: Vision Document" in orchestrator_template
        assert "Step 3: Product Settings Review" in orchestrator_template
        assert "Step 4: Create SPECIFIC Missions" in orchestrator_template

        # Verify order (Step 1 should come before Step 2, etc.)
        step1_pos = orchestrator_template.find("Step 1: Serena MCP First")
        step2_pos = orchestrator_template.find("Step 2: Vision Document")
        step3_pos = orchestrator_template.find("Step 3: Product Settings Review")
        step4_pos = orchestrator_template.find("Step 4: Create SPECIFIC Missions")

        assert step1_pos < step2_pos < step3_pos < step4_pos

    def test_template_has_30_80_10_principle(self, orchestrator_template):
        """Test that template includes 30-80-10 principle."""
        assert "THE 30-80-10 PRINCIPLE" in orchestrator_template
        assert "DISCOVERY PHASE (30% of your effort)" in orchestrator_template
        assert "DELEGATION PLANNING (80% of your effort)" in orchestrator_template
        assert "PROJECT CLOSURE (10% of your effort)" in orchestrator_template

    def test_template_has_3_tool_rule(self, orchestrator_template):
        """Test that template includes 3-tool delegation rule."""
        assert "THE 3-TOOL RULE" in orchestrator_template
        assert "more than 3 tools" in orchestrator_template
        assert "delegate to a worker agent" in orchestrator_template

        # Check for examples of wrong vs correct behavior
        assert "❌ WRONG:" in orchestrator_template
        assert "✅ CORRECT:" in orchestrator_template

    def test_template_has_serena_mcp_guidance(self, orchestrator_template):
        """Test that template includes Serena MCP as primary tool."""
        # Serena should be emphasized as FIRST tool
        assert "Serena MCP First" in orchestrator_template or "FIRST tool" in orchestrator_template

        # Specific Serena tools mentioned
        assert "list_dir" in orchestrator_template
        assert "get_symbols_overview" in orchestrator_template
        assert "find_symbol" in orchestrator_template
        assert "search_for_pattern" in orchestrator_template

    def test_template_has_vision_complete_reading(self, orchestrator_template):
        """Test that template requires reading ALL vision parts."""
        assert "COMPLETE vision" in orchestrator_template or "ALL parts" in orchestrator_template
        assert "get_vision()" in orchestrator_template
        assert "total_parts" in orchestrator_template

        # Check for instruction to read all parts
        assert "read ALL" in orchestrator_template or "Read ALL" in orchestrator_template

    def test_template_has_specific_mission_requirement(self, orchestrator_template):
        """Test that template requires SPECIFIC missions, not generic ones."""
        assert "SPECIFIC Missions" in orchestrator_template or "SPECIFIC missions" in orchestrator_template
        assert "NEVER" in orchestrator_template or "never generic" in orchestrator_template

        # Check for examples
        assert "❌ NEVER:" in orchestrator_template or "WRONG:" in orchestrator_template
        assert "✅ ALWAYS:" in orchestrator_template or "CORRECT:" in orchestrator_template

    def test_template_has_documentation_requirements(self, orchestrator_template):
        """Test that template includes after-action documentation requirements."""
        assert "PROJECT CLOSURE" in orchestrator_template
        assert "Completion Report" in orchestrator_template or "completion report" in orchestrator_template
        assert "Devlog Entry" in orchestrator_template or "devlog" in orchestrator_template
        assert "Session Memory" in orchestrator_template or "session memory" in orchestrator_template

        # Should require three artifacts
        assert "three" in orchestrator_template.lower() or "3" in orchestrator_template

    def test_template_has_validation_before_closure(self, orchestrator_template):
        """Test that template requires validation before project closure."""
        assert "validate" in orchestrator_template.lower() or "verification" in orchestrator_template.lower()
        assert "before" in orchestrator_template.lower()
        assert "close" in orchestrator_template.lower() or "closing" in orchestrator_template.lower()

    def test_template_has_vision_guardian_role(self, orchestrator_template):
        """Test that template includes Vision Guardian responsibilities."""
        assert "VISION GUARDIAN" in orchestrator_template
        assert "align with the vision" in orchestrator_template.lower()
        assert "challenge" in orchestrator_template.lower()

    def test_template_has_scope_sheriff_role(self, orchestrator_template):
        """Test that template includes Scope Sheriff responsibilities."""
        assert "SCOPE SHERIFF" in orchestrator_template
        assert "narrowly focused" in orchestrator_template or "narrow" in orchestrator_template
        assert "scope" in orchestrator_template.lower()

    def test_template_has_strategic_architect_role(self, orchestrator_template):
        """Test that template includes Strategic Architect responsibilities."""
        assert "STRATEGIC ARCHITECT" in orchestrator_template
        assert "sequence" in orchestrator_template or "optimal" in orchestrator_template
        assert "agent" in orchestrator_template

    def test_template_has_progress_tracker_role(self, orchestrator_template):
        """Test that template includes Progress Tracker responsibilities."""
        assert "PROGRESS TRACKER" in orchestrator_template
        assert "check-in" in orchestrator_template or "check in" in orchestrator_template
        assert "escalate" in orchestrator_template.lower()

    def test_template_has_context_management_section(self, orchestrator_template):
        """Test that template includes context management guidance."""
        assert "CONTEXT MANAGEMENT" in orchestrator_template
        assert "orchestrator" in orchestrator_template.lower()
        assert "worker agent" in orchestrator_template.lower() or "Worker Agent" in orchestrator_template

    def test_template_has_role_specific_config_filtering(self, orchestrator_template):
        """Test that template includes role-specific config filtering."""
        assert "Role-Specific Config" in orchestrator_template or "role-specific" in orchestrator_template.lower()
        assert "Implementer" in orchestrator_template or "implementer" in orchestrator_template
        assert "Tester" in orchestrator_template or "tester" in orchestrator_template

    def test_template_has_success_criteria_checklist(self, orchestrator_template):
        """Test that template includes success criteria checklist."""
        assert "SUCCESS CRITERIA" in orchestrator_template

        # Check for checkbox format
        assert "[ ]" in orchestrator_template

        # Key success criteria
        assert "Vision document fully read" in orchestrator_template
        assert "config_data reviewed" in orchestrator_template or "product config" in orchestrator_template
        assert "Serena MCP discoveries" in orchestrator_template or "discoveries documented" in orchestrator_template
        assert "documentation artifacts" in orchestrator_template or "Three documentation" in orchestrator_template

    def test_template_encourages_delegation_not_implementation(self, orchestrator_template):
        """Test that template discourages orchestrator doing implementation work."""
        assert "NOT CEO" in orchestrator_template or "PROJECT MANAGER" in orchestrator_template
        assert "DELEGATION" in orchestrator_template or "delegation" in orchestrator_template
        assert "NEVER do implementation" in orchestrator_template or "not by doing implementation" in orchestrator_template

    def test_template_has_agent_coordination_rules(self, orchestrator_template):
        """Test that template includes agent coordination rules."""
        assert "AGENT COORDINATION" in orchestrator_template or "coordination" in orchestrator_template.lower()
        assert "send_message" in orchestrator_template or "message queue" in orchestrator_template.lower()
        assert "acknowledge" in orchestrator_template.lower()

    def test_template_has_handoff_guidance(self, orchestrator_template):
        """Test that template includes handoff guidance."""
        assert "handoff" in orchestrator_template.lower()
        assert "context limit" in orchestrator_template.lower()

    def test_behavioral_rules_updated(self, template_manager):
        """Test that behavioral rules are updated for orchestrator."""
        rules = template_manager.get_behavioral_rules("orchestrator")

        # Should include new rules
        assert any("3-tool" in rule.lower() for rule in rules), "Missing 3-tool rule"
        assert any("specific mission" in rule.lower() or "discoveries" in rule.lower() for rule in rules), "Missing specific missions rule"
        assert any("documentation" in rule.lower() and "artifact" in rule.lower() for rule in rules), "Missing documentation artifacts rule"

    def test_success_criteria_updated(self, template_manager):
        """Test that success criteria are updated for orchestrator."""
        criteria = template_manager.get_success_criteria("orchestrator")

        # Should include new criteria
        assert any("vision" in c.lower() and ("all parts" in c.lower() or "fully read" in c.lower()) for c in criteria), "Missing vision reading criterion"
        assert any("config_data" in c.lower() or "product config" in c.lower() for c in criteria), "Missing config review criterion"
        assert any("serena" in c.lower() and "discover" in c.lower() for c in criteria), "Missing Serena discoveries criterion"
        assert any("specific mission" in c.lower() for c in criteria), "Missing specific missions criterion"
        assert any("documentation" in c.lower() and ("three" in c.lower() or "3" in c.lower()) for c in criteria), "Missing documentation artifacts criterion"

    def test_template_includes_project_variables(self, orchestrator_template):
        """Test that template includes project variable placeholders."""
        assert "{project_name}" in orchestrator_template
        assert "{project_mission}" in orchestrator_template
        assert "{product_name}" in orchestrator_template


class TestOtherAgentTemplatesPreserved:
    """Test that other agent templates are preserved and not broken."""

    @pytest.fixture
    def template_manager(self):
        """Create template manager instance."""
        return UnifiedTemplateManager(db_manager=None)

    def test_analyzer_template_exists(self, template_manager):
        """Test analyzer template still exists."""
        assert "analyzer" in template_manager._legacy_templates
        template = template_manager._legacy_templates["analyzer"]
        assert "{project_name}" in template
        assert "{custom_mission}" in template

    def test_implementer_template_exists(self, template_manager):
        """Test implementer template still exists."""
        assert "implementer" in template_manager._legacy_templates
        template = template_manager._legacy_templates["implementer"]
        assert "{project_name}" in template
        assert "{custom_mission}" in template

    def test_tester_template_exists(self, template_manager):
        """Test tester template still exists."""
        assert "tester" in template_manager._legacy_templates
        template = template_manager._legacy_templates["tester"]
        assert "{project_name}" in template

    def test_reviewer_template_exists(self, template_manager):
        """Test reviewer template still exists."""
        assert "reviewer" in template_manager._legacy_templates
        template = template_manager._legacy_templates["reviewer"]
        assert "{project_name}" in template

    def test_documenter_template_exists(self, template_manager):
        """Test documenter template still exists."""
        assert "documenter" in template_manager._legacy_templates
        template = template_manager._legacy_templates["documenter"]
        assert "{project_name}" in template
