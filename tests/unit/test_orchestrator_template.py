"""
Test suite for enhanced orchestrator template
Phase 3: Orchestrator Upgrade - TDD Implementation
"""

import pytest

from src.giljo_mcp.template_manager import UnifiedTemplateManager


class TestOrchestratorTemplateContent:
    """Test that orchestrator template contains all critical sections"""

    @pytest.fixture
    def template_manager(self):
        """Create template manager without database"""
        return UnifiedTemplateManager(db_manager=None)

    @pytest.fixture
    def orchestrator_template(self, template_manager):
        """Get orchestrator template content"""
        return template_manager._legacy_templates.get("orchestrator", "")

    def test_template_exists(self, orchestrator_template):
        """Test that orchestrator template is loaded"""
        assert orchestrator_template, "Orchestrator template should not be empty"
        assert len(orchestrator_template) > 100, "Template should have substantial content"

    def test_contains_30_80_10_principle(self, orchestrator_template):
        """Test that template contains 30-80-10 principle"""
        # Check for exact phrase
        assert "30-80-10" in orchestrator_template, "Template must contain '30-80-10' principle"
        # Check for the principle explained
        assert "DISCOVERY PHASE (30%" in orchestrator_template, "Template must explain discovery phase"
        assert "DELEGATION PLANNING (80%" in orchestrator_template, "Template must explain delegation phase"
        assert "PROJECT CLOSURE (10%" in orchestrator_template, "Template must explain closure phase"

    def test_contains_3_tool_rule(self, orchestrator_template):
        """Test that template contains 3-tool rule"""
        # Case insensitive search
        template_lower = orchestrator_template.lower()
        assert "3-tool" in template_lower or "3 tool" in template_lower, "Template must contain 3-tool rule reference"
        assert "more than 3 tools" in template_lower, "Template must explain the 3-tool limit"

    def test_contains_serena_mcp_references(self, orchestrator_template):
        """Test that template mentions Serena MCP"""
        template_lower = orchestrator_template.lower()
        assert "serena" in template_lower, "Template must reference Serena MCP"
        assert "mcp" in template_lower, "Template must mention MCP tools"

    def test_contains_serena_tools(self, orchestrator_template):
        """Test that template lists Serena MCP tools"""
        # Check for key Serena tool names
        assert "list_dir" in orchestrator_template, "Template should mention list_dir tool"
        assert "get_symbols_overview" in orchestrator_template, "Template should mention get_symbols_overview"
        assert "find_symbol" in orchestrator_template, "Template should mention find_symbol"
        assert "find_referencing_symbols" in orchestrator_template, "Template should mention find_referencing_symbols"
        assert "search_for_pattern" in orchestrator_template, "Template should mention search_for_pattern"

    def test_contains_vision_document_workflow(self, orchestrator_template):
        """Test that template includes vision document reading workflow"""
        assert "get_vision" in orchestrator_template, "Template must mention get_vision tool"
        assert "get_vision_index" in orchestrator_template, "Template should explain vision index"
        assert "total_parts" in orchestrator_template, "Template should explain multi-part vision handling"
        assert "ALL parts" in orchestrator_template or "all parts" in orchestrator_template, (
            "Template must emphasize reading all vision parts"
        )

    def test_contains_product_settings(self, orchestrator_template):
        """Test that template includes product settings review"""
        assert "get_product_settings" in orchestrator_template, "Template must mention get_product_settings"
        assert "config_data" in orchestrator_template or "config" in orchestrator_template.lower(), (
            "Template should reference configuration data"
        )

    def test_contains_discovery_keyword(self, orchestrator_template):
        """Test that template emphasizes discovery"""
        template_lower = orchestrator_template.lower()
        assert "discovery" in template_lower, "Template must contain 'discovery' concept"
        # Count occurrences - should appear multiple times
        discovery_count = template_lower.count("discovery")
        assert discovery_count >= 3, (
            f"Template should emphasize discovery (found {discovery_count} times, expected >= 3)"
        )

    def test_contains_delegation_keyword(self, orchestrator_template):
        """Test that template emphasizes delegation"""
        template_lower = orchestrator_template.lower()
        assert "delegation" in template_lower or "delegate" in template_lower, (
            "Template must contain 'delegation' concept"
        )
        # Count occurrences - should appear multiple times
        delegate_count = template_lower.count("delegate")
        assert delegate_count >= 3, (
            f"Template should emphasize delegation (found {delegate_count} times, expected >= 3)"
        )

    def test_contains_specific_mission_examples(self, orchestrator_template):
        """Test that template includes specific vs generic mission examples"""
        assert "❌" in orchestrator_template or "NEVER:" in orchestrator_template, "Template should show anti-patterns"
        assert "✅" in orchestrator_template or "ALWAYS:" in orchestrator_template, (
            "Template should show correct patterns"
        )

    def test_contains_project_closure_requirements(self, orchestrator_template):
        """Test that template specifies project closure documentation"""
        assert "PROJECT CLOSURE" in orchestrator_template, "Template must have project closure section"
        assert "Completion Report" in orchestrator_template or "completion report" in orchestrator_template, (
            "Template must mention completion report"
        )
        assert "Devlog" in orchestrator_template or "devlog" in orchestrator_template, "Template must mention devlog"
        assert "Session Memory" in orchestrator_template or "session memory" in orchestrator_template, (
            "Template must mention session memory"
        )
        # Should require THREE artifacts
        assert "three" in orchestrator_template.lower() or "3" in orchestrator_template, (
            "Template should specify three documentation artifacts"
        )

    def test_role_definition_not_ceo(self, orchestrator_template):
        """Test that orchestrator role is properly scoped (not CEO)"""
        assert "Project Manager" in orchestrator_template or "Team Lead" in orchestrator_template, (
            "Template should define role as Project Manager/Team Lead"
        )
        assert (
            "NOT CEO" in orchestrator_template
            or "not CEO" in orchestrator_template
            or "(not solo developer)" in orchestrator_template.lower()
        ), "Template should clarify not CEO/solo developer"

    def test_contains_context_management(self, orchestrator_template):
        """Test that template includes context management guidance"""
        template_lower = orchestrator_template.lower()
        assert "context" in template_lower, "Template should mention context management"
        # Should differentiate between orchestrator and worker context
        assert "worker" in template_lower or "agent" in template_lower, (
            "Template should distinguish worker agent context"
        )

    def test_contains_success_criteria_section(self, orchestrator_template):
        """Test that template has success criteria section"""
        assert "SUCCESS CRITERIA" in orchestrator_template, "Template must have success criteria section"
        # Should be a checklist format
        assert "[ ]" in orchestrator_template or "- [ ]" in orchestrator_template, (
            "Success criteria should use checkbox format"
        )


class TestOrchestratorTemplateMetadata:
    """Test orchestrator template metadata and configuration"""

    @pytest.fixture
    def template_manager(self):
        """Create template manager without database"""
        return UnifiedTemplateManager(db_manager=None)

    def test_orchestrator_template_role(self, template_manager):
        """Test that orchestrator template is registered for orchestrator role"""
        assert "orchestrator" in template_manager._legacy_templates, "Orchestrator template must be registered"

    def test_template_has_variable_placeholders(self, template_manager):
        """Test that template has variable placeholders"""
        template = template_manager._legacy_templates["orchestrator"]
        # Should have these key variables
        assert "{project_name}" in template, "Template should have project_name variable"
        assert "{project_mission}" in template, "Template should have project_mission variable"
        assert "{product_name}" in template, "Template should have product_name variable"

    def test_behavioral_rules_defined(self, template_manager):
        """Test that behavioral rules are defined for orchestrator"""
        rules = template_manager.get_behavioral_rules("orchestrator")
        assert len(rules) > 0, "Orchestrator should have behavioral rules"
        # Check for specific rules
        rule_text = " ".join(rules).lower()
        assert "delegate" in rule_text or "delegation" in rule_text, "Rules should mention delegation"
        assert "3-tool" in rule_text or "3 tools" in rule_text, "Rules should include 3-tool rule"

    def test_success_criteria_defined(self, template_manager):
        """Test that success criteria are defined for orchestrator"""
        criteria = template_manager.get_success_criteria("orchestrator")
        assert len(criteria) > 0, "Orchestrator should have success criteria"
        # Check for specific criteria
        criteria_text = " ".join(criteria).lower()
        assert "vision" in criteria_text, "Criteria should mention vision document"
        assert "documentation" in criteria_text, "Criteria should mention documentation artifacts"


class TestOrchestratorTemplateStructure:
    """Test the overall structure and organization of the template"""

    @pytest.fixture
    def template_manager(self):
        """Create template manager without database"""
        return UnifiedTemplateManager(db_manager=None)

    @pytest.fixture
    def orchestrator_template(self, template_manager):
        """Get orchestrator template content"""
        return template_manager._legacy_templates.get("orchestrator", "")

    def test_has_clear_sections(self, orchestrator_template):
        """Test that template has clear section markers"""
        # Should have section headers with === markers
        assert "===" in orchestrator_template, "Template should use === for section headers"
        # Count sections - should have several major sections
        section_count = orchestrator_template.count("===")
        assert section_count >= 10, (
            f"Template should have multiple clear sections (found {section_count}, expected >= 10)"
        )

    def test_workflow_steps_numbered(self, orchestrator_template):
        """Test that workflow steps are clearly numbered"""
        # Should have numbered steps (Step 1, Step 2, etc.)
        assert "Step 1:" in orchestrator_template or "1." in orchestrator_template, (
            "Template should have numbered workflow steps"
        )

    def test_has_examples_section(self, orchestrator_template):
        """Test that template includes examples"""
        # Should have example usage patterns
        assert "Example" in orchestrator_template or "example" in orchestrator_template, (
            "Template should include examples"
        )

    def test_comprehensive_length(self, orchestrator_template):
        """Test that template is comprehensive (not abbreviated)"""
        # Enhanced template should be substantial (800+ lines mentioned in brief)
        line_count = len(orchestrator_template.split("\n"))
        assert line_count >= 200, f"Template should be comprehensive (found {line_count} lines, expected >= 200)"
        # Check character count too
        char_count = len(orchestrator_template)
        assert char_count >= 10000, (
            f"Template should have substantial content (found {char_count} chars, expected >= 10000)"
        )


class TestOrchestratorTemplateIntegration:
    """Test template integration with database and installer"""

    def test_template_can_be_processed(self):
        """Test that template can be processed with variables"""
        from src.giljo_mcp.template_manager import UnifiedTemplateManager, process_template

        manager = UnifiedTemplateManager(db_manager=None)
        template = manager._legacy_templates["orchestrator"]

        # Process with test variables
        variables = {"project_name": "Test Project", "project_mission": "Test mission", "product_name": "Test Product"}

        processed = process_template(template, variables)

        # Check variables were substituted
        assert "Test Project" in processed, "project_name should be substituted"
        assert "Test mission" in processed, "project_mission should be substituted"
        assert "Test Product" in processed, "product_name should be substituted"

        # Original placeholders should be gone
        assert "{project_name}" not in processed, "Placeholders should be substituted"
        assert "{project_mission}" not in processed, "Placeholders should be substituted"
        assert "{product_name}" not in processed, "Placeholders should be substituted"

    def test_extract_variables_from_template(self):
        """Test that template variables can be extracted"""
        from src.giljo_mcp.template_manager import UnifiedTemplateManager, extract_variables

        manager = UnifiedTemplateManager(db_manager=None)
        template = manager._legacy_templates["orchestrator"]

        variables = extract_variables(template)

        # Should include key variables
        assert "project_name" in variables, "Should extract project_name variable"
        assert "project_mission" in variables, "Should extract project_mission variable"
        assert "product_name" in variables, "Should extract product_name variable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
