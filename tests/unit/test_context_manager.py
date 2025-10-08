"""
Unit tests for context_manager module
"""

import pytest
from src.giljo_mcp.context_manager import (
    is_orchestrator,
    get_full_config,
    get_filtered_config,
    validate_config_data,
    merge_config_updates,
    get_config_summary,
    ROLE_CONFIG_FILTERS
)
from src.giljo_mcp.models import Product


@pytest.fixture
def sample_product():
    """Create sample product with config_data"""
    product = Product(
        id="test-product-1",
        tenant_key="test-tenant",
        name="Test Product",
        config_data={
            "architecture": "FastAPI + PostgreSQL",
            "tech_stack": ["Python 3.11", "PostgreSQL 18"],
            "codebase_structure": {
                "api": "REST endpoints",
                "core": "Orchestration"
            },
            "critical_features": ["Multi-tenant", "Agent coordination"],
            "test_commands": ["pytest tests/"],
            "test_config": {"coverage_threshold": 80},
            "api_docs": "/docs/api.md",
            "documentation_style": "Markdown",
            "serena_mcp_enabled": True,
            "database_type": "postgresql",
            "frontend_framework": "Vue 3",
            "backend_framework": "FastAPI"
        }
    )
    return product


@pytest.fixture
def minimal_product():
    """Create product with minimal config_data"""
    product = Product(
        id="test-product-minimal",
        tenant_key="test-tenant",
        name="Minimal Product",
        config_data={
            "architecture": "Simple App",
            "serena_mcp_enabled": False
        }
    )
    return product


@pytest.fixture
def empty_product():
    """Create product with no config_data"""
    product = Product(
        id="test-product-empty",
        tenant_key="test-tenant",
        name="Empty Product",
        config_data={}
    )
    return product


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


class TestGetFullConfig:
    """Tests for get_full_config function"""

    def test_get_full_config_complete(self, sample_product):
        """Test full config retrieval for orchestrator"""
        config = get_full_config(sample_product)

        assert "architecture" in config
        assert "tech_stack" in config
        assert "test_commands" in config
        assert "api_docs" in config
        assert "serena_mcp_enabled" in config
        assert len(config) == len(sample_product.config_data)

    def test_get_full_config_minimal(self, minimal_product):
        """Test full config with minimal data"""
        config = get_full_config(minimal_product)

        assert "architecture" in config
        assert "serena_mcp_enabled" in config
        assert len(config) == 2

    def test_get_full_config_empty(self, empty_product):
        """Test full config with empty config_data"""
        config = get_full_config(empty_product)

        assert config == {}

    def test_get_full_config_returns_copy(self, sample_product):
        """Test that get_full_config returns a copy, not reference"""
        config = get_full_config(sample_product)
        config["new_field"] = "test"

        # Original should be unchanged
        assert "new_field" not in sample_product.config_data


class TestGetFilteredConfig:
    """Tests for get_filtered_config function"""

    def test_get_filtered_config_implementer(self, sample_product):
        """Test filtered config for implementer role"""
        config = get_filtered_config("implementer-1", sample_product)

        # Should have implementer fields
        assert "architecture" in config
        assert "tech_stack" in config
        assert "codebase_structure" in config
        assert "critical_features" in config
        assert "database_type" in config
        assert "backend_framework" in config
        assert "frontend_framework" in config

        # Should NOT have tester/documenter-specific fields
        assert "test_commands" not in config
        assert "test_config" not in config
        assert "api_docs" not in config
        assert "documentation_style" not in config

        # Should always have serena flag
        assert "serena_mcp_enabled" in config

    def test_get_filtered_config_tester(self, sample_product):
        """Test filtered config for tester role"""
        config = get_filtered_config("tester-qa-1", sample_product)

        # Should have tester fields
        assert "test_commands" in config
        assert "test_config" in config
        assert "critical_features" in config
        assert "tech_stack" in config

        # Should NOT have implementer-specific fields
        assert "codebase_structure" not in config
        assert "database_type" not in config

        # Should have serena flag
        assert "serena_mcp_enabled" in config

    def test_get_filtered_config_documenter(self, sample_product):
        """Test filtered config for documenter role"""
        config = get_filtered_config("documenter-agent", sample_product)

        # Should have documenter fields
        assert "api_docs" in config
        assert "documentation_style" in config
        assert "architecture" in config
        assert "critical_features" in config
        assert "codebase_structure" in config

        # Should NOT have test-specific fields
        assert "test_commands" not in config
        assert "test_config" not in config

    def test_get_filtered_config_analyzer(self, sample_product):
        """Test filtered config for analyzer role"""
        config = get_filtered_config("analyzer-code", sample_product)

        # Should have analyzer fields
        assert "architecture" in config
        assert "tech_stack" in config
        assert "codebase_structure" in config
        assert "critical_features" in config

        # Should NOT have test or documentation fields
        assert "test_commands" not in config
        assert "api_docs" not in config

    def test_get_filtered_config_reviewer(self, sample_product):
        """Test filtered config for reviewer role"""
        config = get_filtered_config("reviewer-1", sample_product)

        # Should have reviewer fields
        assert "architecture" in config
        assert "tech_stack" in config
        assert "critical_features" in config
        assert "documentation_style" in config

        # Should NOT have implementation details
        assert "codebase_structure" not in config
        assert "test_commands" not in config

    def test_get_filtered_config_orchestrator_gets_all(self, sample_product):
        """Test orchestrator gets full config through filtering"""
        config = get_filtered_config("orchestrator", sample_product)

        assert len(config) == len(sample_product.config_data)

    def test_get_filtered_config_unknown_role_defaults_analyzer(self, sample_product):
        """Test unknown role defaults to analyzer filtering"""
        config = get_filtered_config("unknown-agent-123", sample_product)

        # Should have analyzer fields
        assert "architecture" in config
        assert "tech_stack" in config
        assert "codebase_structure" in config

    def test_get_filtered_config_developer_alias(self, sample_product):
        """Test 'developer' role alias for implementer"""
        config = get_filtered_config("developer-1", sample_product)

        # Should behave like implementer
        assert "architecture" in config
        assert "tech_stack" in config
        assert "codebase_structure" in config

    def test_get_filtered_config_qa_alias(self, sample_product):
        """Test 'qa' role alias for tester"""
        config = get_filtered_config("qa-engineer", sample_product)

        # Should behave like tester
        assert "test_commands" in config
        assert "test_config" in config
        assert "critical_features" in config

    def test_filtered_config_token_reduction(self, sample_product):
        """Test that filtering significantly reduces field count"""
        full_config = get_full_config(sample_product)
        filtered_config = get_filtered_config("implementer-1", sample_product)

        # Filtered should have fewer fields (60%+ reduction is the goal)
        reduction = (len(full_config) - len(filtered_config)) / len(full_config)
        assert reduction > 0.3  # At least 30% reduction

    def test_filtered_config_empty_product(self, empty_product):
        """Test filtering with empty config_data"""
        config = get_filtered_config("implementer-1", empty_product)
        assert config == {}


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
            "test_config": {"coverage_threshold": 80}
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_data_valid_minimal(self):
        """Test validation with minimal valid config"""
        config = {
            "architecture": "Simple App",
            "serena_mcp_enabled": False
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_data_missing_architecture(self):
        """Test validation with missing architecture"""
        config = {
            "serena_mcp_enabled": True,
            "tech_stack": ["Python"]
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("architecture" in err.lower() for err in errors)

    def test_validate_config_data_missing_serena_flag(self):
        """Test validation with missing serena_mcp_enabled"""
        config = {
            "architecture": "FastAPI",
            "tech_stack": ["Python"]
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("serena_mcp_enabled" in err.lower() for err in errors)

    def test_validate_config_data_wrong_type_tech_stack(self):
        """Test validation with wrong type for tech_stack"""
        config = {
            "architecture": "FastAPI",
            "serena_mcp_enabled": True,
            "tech_stack": "Python"  # Should be array
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("tech_stack" in err.lower() and "array" in err.lower() for err in errors)

    def test_validate_config_data_wrong_type_test_commands(self):
        """Test validation with wrong type for test_commands"""
        config = {
            "architecture": "FastAPI",
            "serena_mcp_enabled": True,
            "test_commands": {"cmd": "pytest"}  # Should be array
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("test_commands" in err.lower() for err in errors)

    def test_validate_config_data_wrong_type_serena_flag(self):
        """Test validation with wrong type for serena_mcp_enabled"""
        config = {
            "architecture": "FastAPI",
            "serena_mcp_enabled": "yes"  # Should be boolean
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("serena_mcp_enabled" in err.lower() and "boolean" in err.lower() for err in errors)

    def test_validate_config_data_wrong_type_codebase_structure(self):
        """Test validation with wrong type for codebase_structure"""
        config = {
            "architecture": "FastAPI",
            "serena_mcp_enabled": True,
            "codebase_structure": ["api", "frontend"]  # Should be object
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert any("codebase_structure" in err.lower() for err in errors)

    def test_validate_config_data_multiple_errors(self):
        """Test validation with multiple errors"""
        config = {
            "tech_stack": "Python",  # Missing architecture, serena_mcp_enabled; wrong type
            "test_commands": "pytest"  # Wrong type
        }

        is_valid, errors = validate_config_data(config)
        assert is_valid is False
        assert len(errors) >= 3  # At least: missing architecture, missing serena, wrong tech_stack type


class TestMergeConfigUpdates:
    """Tests for merge_config_updates function"""

    def test_merge_config_updates_shallow(self):
        """Test shallow merge of config updates"""
        existing = {
            "architecture": "Old Architecture",
            "tech_stack": ["Python 3.10"]
        }

        updates = {
            "architecture": "New Architecture",
            "test_commands": ["pytest"]
        }

        merged = merge_config_updates(existing, updates)

        assert merged["architecture"] == "New Architecture"
        assert merged["tech_stack"] == ["Python 3.10"]
        assert merged["test_commands"] == ["pytest"]

    def test_merge_config_updates_deep(self):
        """Test deep merge of nested objects"""
        existing = {
            "test_config": {
                "coverage_threshold": 80,
                "framework": "pytest"
            }
        }

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
        existing = {
            "tech_stack": ["Python 3.10", "PostgreSQL 14"]
        }

        updates = {
            "tech_stack": ["Python 3.11", "PostgreSQL 18"]
        }

        merged = merge_config_updates(existing, updates)

        # Array should be completely replaced
        assert merged["tech_stack"] == ["Python 3.11", "PostgreSQL 18"]

    def test_merge_config_updates_empty_existing(self):
        """Test merge with empty existing config"""
        existing = {}

        updates = {
            "architecture": "FastAPI",
            "serena_mcp_enabled": True
        }

        merged = merge_config_updates(existing, updates)

        assert merged == updates

    def test_merge_config_updates_empty_updates(self):
        """Test merge with empty updates"""
        existing = {
            "architecture": "FastAPI",
            "serena_mcp_enabled": True
        }

        updates = {}

        merged = merge_config_updates(existing, updates)

        assert merged == existing

    def test_merge_config_updates_preserves_existing(self):
        """Test that merge doesn't modify original existing dict"""
        existing = {
            "architecture": "Old",
            "tech_stack": ["Python"]
        }

        updates = {
            "architecture": "New"
        }

        merged = merge_config_updates(existing, updates)

        # Original should be unchanged
        assert existing["architecture"] == "Old"
        assert merged["architecture"] == "New"


class TestGetConfigSummary:
    """Tests for get_config_summary function"""

    def test_get_config_summary_complete(self, sample_product):
        """Test summary with complete config_data"""
        summary = get_config_summary(sample_product)

        assert "Architecture:" in summary
        assert "FastAPI + PostgreSQL" in summary
        assert "Tech Stack:" in summary
        assert "Python 3.11" in summary
        assert "Critical Features:" in summary
        assert "Test Commands:" in summary
        assert "Serena MCP:" in summary
        assert "enabled" in summary

    def test_get_config_summary_minimal(self, minimal_product):
        """Test summary with minimal config_data"""
        summary = get_config_summary(minimal_product)

        assert "Architecture:" in summary
        assert "Simple App" in summary
        assert "Serena MCP:" in summary
        assert "disabled" in summary

    def test_get_config_summary_empty(self, empty_product):
        """Test summary with empty config_data"""
        summary = get_config_summary(empty_product)

        assert summary == "No configuration data available"

    def test_get_config_summary_no_config_data(self):
        """Test summary with None config_data"""
        product = Product(
            id="test-product-none",
            tenant_key="test-tenant",
            name="None Product",
            config_data=None
        )

        summary = get_config_summary(product)

        assert summary == "No configuration data available"


class TestRoleConfigFilters:
    """Tests for ROLE_CONFIG_FILTERS constant"""

    def test_all_roles_have_filters(self):
        """Test that all expected roles have filter definitions"""
        expected_roles = [
            "orchestrator", "implementer", "developer",
            "tester", "qa", "documenter", "analyzer", "reviewer"
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
