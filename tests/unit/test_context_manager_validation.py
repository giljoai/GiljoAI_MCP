"""
Unit tests for context_manager module - roles and orchestrator detection

Split from test_context_manager.py. Tests cover:
- is_orchestrator
- ROLE_CONFIG_FILTERS

Handover 0840c: Removed tests for validate_config_data and merge_config_updates
(both functions deleted in context_manager.py normalization).
"""


from src.giljo_mcp.context_manager import (
    ROLE_CONFIG_FILTERS,
    is_orchestrator,
)


class TestIsOrchestrator:
    """Tests for is_orchestrator function"""

    def test_is_orchestrator_by_name_lowercase(self):
        """Test orchestrator detection by name (lowercase)"""
        assert is_orchestrator("orchestrator") is True

    def test_is_orchestrator_by_name_capitalized(self):
        """Test orchestrator detection by name (capitalized)"""
        assert is_orchestrator("Orchestrator-Agent-1") is True

    def test_is_orchestrator_by_name_mixed_case(self):
        """Test orchestrator detection by name (mixed case)"""
        assert is_orchestrator("Project-ORCHESTRATOR") is True

    def test_is_orchestrator_by_role(self):
        """Test orchestrator detection by role"""
        assert is_orchestrator("agent-1", agent_role="orchestrator") is True

    def test_is_orchestrator_by_role_case_insensitive(self):
        """Test orchestrator detection by role (case insensitive)"""
        assert is_orchestrator("agent-1", agent_role="ORCHESTRATOR") is True

    def test_not_orchestrator_implementer(self):
        """Test non-orchestrator agent (implementer)"""
        assert is_orchestrator("implementer") is False

    def test_not_orchestrator_by_role(self):
        """Test non-orchestrator by role"""
        assert is_orchestrator("agent-1", agent_role="implementer") is False

    def test_not_orchestrator_similar_name(self):
        """Test agent with similar but not matching name"""
        assert is_orchestrator("orchestra-player") is False


class TestRoleConfigFilters:
    """Tests for ROLE_CONFIG_FILTERS constant"""

    def test_all_roles_have_filters(self):
        """Test that all expected roles have filter definitions"""
        expected_roles = [
            "orchestrator",
            "implementer",
            "developer",
            "tester",
            "qa",
            "documenter",
            "analyzer",
            "reviewer",
        ]

        for role in expected_roles:
            assert role in ROLE_CONFIG_FILTERS, f"Missing filter for role: {role}"

    def test_orchestrator_gets_all(self):
        """Test that orchestrator filter is set to 'all'"""
        assert ROLE_CONFIG_FILTERS["orchestrator"] == "all"

    def test_all_other_roles_have_lists(self):
        """Test that all non-orchestrator roles have list of fields"""
        for role, fields in ROLE_CONFIG_FILTERS.items():
            if role != "orchestrator":
                assert isinstance(fields, list), f"Role {role} should have list of fields"
                assert len(fields) > 0, f"Role {role} should have at least one field"

    def test_no_duplicate_fields_per_role(self):
        """Test that each role's field list has no duplicates"""
        for role, fields in ROLE_CONFIG_FILTERS.items():
            if isinstance(fields, list):
                assert len(fields) == len(set(fields)), f"Role {role} has duplicate fields"

    def test_implementer_has_architecture_and_tech_stack(self):
        """Test that implementer has essential normalized relation keys"""
        impl_fields = ROLE_CONFIG_FILTERS["implementer"]
        assert "architecture" in impl_fields
        assert "tech_stack" in impl_fields

    def test_tester_has_test_config_and_tech_stack(self):
        """Test that tester has essential normalized relation keys"""
        tester_fields = ROLE_CONFIG_FILTERS["tester"]
        assert "test_config" in tester_fields
        assert "tech_stack" in tester_fields

    def test_documenter_has_architecture(self):
        """Test that documenter has architecture access"""
        doc_fields = ROLE_CONFIG_FILTERS["documenter"]
        assert "architecture" in doc_fields
