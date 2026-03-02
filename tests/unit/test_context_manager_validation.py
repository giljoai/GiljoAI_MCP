"""
Unit tests for context_manager module - validation, merging, roles, and orchestrator detection

Split from test_context_manager.py. Tests cover:
- is_orchestrator
- validate_config_data
- merge_config_updates
- ROLE_CONFIG_FILTERS
"""

import pytest

from src.giljo_mcp.context_manager import (
    ROLE_CONFIG_FILTERS,
    is_orchestrator,
    merge_config_updates,
    validate_config_data,
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


class TestValidateConfigData:
    """Tests for validate_config_data function"""

    def test_validate_config_data_valid_complete(self):
        """Test validation with valid complete config"""
        config = {
            "architecture": "FastAPI + PostgreSQL",
            "serena_mcp_enabled": True,
            "tech_stack": ["Python 3.11", "PostgreSQL"],
            "test_commands": ["pytest tests/"],
            "critical_features": ["Multi-tenant isolation"],
            "codebase_structure": {"api": "REST endpoints"},
            "test_config": {"coverage_threshold": 80},
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_data_valid_minimal(self):
        """Test validation with minimal valid config"""
        config = {"architecture": "Simple App", "serena_mcp_enabled": False}

        is_valid, errors = validate_config_data(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_data_missing_architecture(self):
        """Test validation with missing architecture"""
        config = {"serena_mcp_enabled": True, "tech_stack": ["Python"]}

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("architecture" in err.lower() for err in errors)

    def test_validate_config_data_missing_serena_flag(self):
        """Test validation with missing serena_mcp_enabled"""
        config = {"architecture": "FastAPI", "tech_stack": ["Python"]}

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("serena_mcp_enabled" in err.lower() for err in errors)

    def test_validate_config_data_wrong_type_tech_stack(self):
        """Test validation with wrong type for tech_stack"""
        config = {
            "architecture": "FastAPI",
            "serena_mcp_enabled": True,
            "tech_stack": "Python",  # Should be array
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("tech_stack" in err.lower() and "array" in err.lower() for err in errors)

    def test_validate_config_data_wrong_type_test_commands(self):
        """Test validation with wrong type for test_commands"""
        config = {
            "architecture": "FastAPI",
            "serena_mcp_enabled": True,
            "test_commands": {"cmd": "pytest"},  # Should be array
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("test_commands" in err.lower() for err in errors)

    def test_validate_config_data_wrong_type_serena_flag(self):
        """Test validation with wrong type for serena_mcp_enabled"""
        config = {
            "architecture": "FastAPI",
            "serena_mcp_enabled": "yes",  # Should be boolean
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("serena_mcp_enabled" in err.lower() and "boolean" in err.lower() for err in errors)

    def test_validate_config_data_wrong_type_codebase_structure(self):
        """Test validation with wrong type for codebase_structure"""
        config = {
            "architecture": "FastAPI",
            "serena_mcp_enabled": True,
            "codebase_structure": ["api", "frontend"],  # Should be object
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("codebase_structure" in err.lower() for err in errors)

    def test_validate_config_data_multiple_errors(self):
        """Test validation with multiple errors"""
        config = {
            "tech_stack": "Python",  # Missing architecture, serena_mcp_enabled; wrong type
            "test_commands": "pytest",  # Wrong type
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert len(errors) >= 3  # At least: missing architecture, missing serena, wrong tech_stack type


class TestMergeConfigUpdates:
    """Tests for merge_config_updates function"""

    def test_merge_config_updates_shallow(self):
        """Test shallow merge of config updates"""
        existing = {"architecture": "Old Architecture", "tech_stack": ["Python 3.10"]}

        updates = {"architecture": "New Architecture", "test_commands": ["pytest"]}

        merged = merge_config_updates(existing, updates)

        assert merged["architecture"] == "New Architecture"
        assert merged["tech_stack"] == ["Python 3.10"]
        assert merged["test_commands"] == ["pytest"]

    def test_merge_config_updates_deep(self):
        """Test deep merge of nested objects"""
        existing = {"test_config": {"coverage_threshold": 80, "framework": "pytest"}}

        updates = {
            "test_config": {
                "coverage_threshold": 90  # Update existing field
                # framework should be preserved
            }
        }

        merged = merge_config_updates(existing, updates)

        assert merged["test_config"]["coverage_threshold"] == 90
        assert merged["test_config"]["framework"] == "pytest"

    def test_merge_config_updates_array_replacement(self):
        """Test that arrays are replaced, not merged"""
        existing = {"tech_stack": ["Python 3.10", "PostgreSQL 14"]}

        updates = {"tech_stack": ["Python 3.11", "PostgreSQL 18"]}

        merged = merge_config_updates(existing, updates)

        # Array should be completely replaced
        assert merged["tech_stack"] == ["Python 3.11", "PostgreSQL 18"]

    def test_merge_config_updates_empty_existing(self):
        """Test merge with empty existing config"""
        existing = {}

        updates = {"architecture": "FastAPI", "serena_mcp_enabled": True}

        merged = merge_config_updates(existing, updates)

        assert merged == updates

    def test_merge_config_updates_empty_updates(self):
        """Test merge with empty updates"""
        existing = {"architecture": "FastAPI", "serena_mcp_enabled": True}

        updates = {}

        merged = merge_config_updates(existing, updates)

        assert merged == existing

    def test_merge_config_updates_preserves_existing(self):
        """Test that merge doesn't modify original existing dict"""
        existing = {"architecture": "Old", "tech_stack": ["Python"]}

        updates = {"architecture": "New"}

        merged = merge_config_updates(existing, updates)

        # Original should be unchanged
        assert existing["architecture"] == "Old"
        assert merged["architecture"] == "New"


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

    def test_critical_fields_in_implementer(self):
        """Test that implementer has essential fields"""
        impl_fields = ROLE_CONFIG_FILTERS["implementer"]
        essential_fields = ["architecture", "tech_stack", "codebase_structure"]

        for field in essential_fields:
            assert field in impl_fields, f"Implementer missing essential field: {field}"

    def test_critical_fields_in_tester(self):
        """Test that tester has essential fields"""
        tester_fields = ROLE_CONFIG_FILTERS["tester"]
        essential_fields = ["test_commands", "test_config"]

        for field in essential_fields:
            assert field in tester_fields, f"Tester missing essential field: {field}"

    def test_critical_fields_in_documenter(self):
        """Test that documenter has essential fields"""
        doc_fields = ROLE_CONFIG_FILTERS["documenter"]
        essential_fields = ["api_docs", "documentation_style"]

        for field in essential_fields:
            assert field in doc_fields, f"Documenter missing essential field: {field}"
