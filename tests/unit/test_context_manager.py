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
            "database_type": "PostgreSQL 18",
            "backend_framework": "FastAPI",
            "frontend_framework": "Vue 3",
            "deployment_modes": ["localhost", "server"],
            "known_issues": ["Issue 1", "Issue 2"],
            "serena_mcp_enabled": True
        }
    )
    return product


@pytest.fixture
def empty_product():
    """Create product with no config_data"""
    product = Product(
        id="test-product-2",
        tenant_key="test-tenant",
        name="Empty Product",
        config_data=None
    )
    return product


# Test is_orchestrator function
def test_is_orchestrator_by_name():
    """Test orchestrator detection by name"""
    assert is_orchestrator("orchestrator") is True
    assert is_orchestrator("Orchestrator-Agent-1") is True
    assert is_orchestrator("ORCHESTRATOR_MAIN") is True
    assert is_orchestrator("implementer") is False
    assert is_orchestrator("tester") is False


def test_is_orchestrator_by_role():
    """Test orchestrator detection by role"""
    assert is_orchestrator("agent-1", agent_role="orchestrator") is True
    assert is_orchestrator("agent-1", agent_role="Orchestrator") is True
    assert is_orchestrator("agent-1", agent_role="implementer") is False
    assert is_orchestrator("random-name", agent_role="orchestrator") is True


def test_is_orchestrator_name_takes_precedence():
    """Test that name check works even without role"""
    assert is_orchestrator("orchestrator-main") is True
    assert is_orchestrator("orchestrator-main", agent_role="implementer") is True


# Test get_full_config function
def test_get_full_config_returns_all_fields(sample_product):
    """Test full config retrieval for orchestrator"""
    config = get_full_config(sample_product)

    assert "architecture" in config
    assert "tech_stack" in config
    assert "test_commands" in config
    assert "api_docs" in config
    assert "codebase_structure" in config
    assert "critical_features" in config
    assert len(config) == len(sample_product.config_data)


def test_get_full_config_with_empty_product(empty_product):
    """Test full config with no config_data"""
    config = get_full_config(empty_product)
    assert config == {}


# Test get_filtered_config function - Orchestrator
def test_get_filtered_config_orchestrator_gets_all(sample_product):
    """Test orchestrator gets full config through filtering"""
    config = get_filtered_config("orchestrator", sample_product)
    
    assert len(config) == len(sample_product.config_data)
    assert "architecture" in config
    assert "test_commands" in config
    assert "api_docs" in config


def test_get_filtered_config_orchestrator_by_role(sample_product):
    """Test orchestrator role gets full config"""
    config = get_filtered_config("agent-1", sample_product, agent_role="orchestrator")
    
    assert len(config) == len(sample_product.config_data)


# Test get_filtered_config function - Implementer
def test_get_filtered_config_implementer(sample_product):
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
    assert "deployment_modes" in config

    # Should NOT have tester/documenter-specific fields
    assert "test_commands" not in config
    assert "test_config" not in config
    assert "api_docs" not in config
    assert "documentation_style" not in config

    # Should always have serena flag
    assert "serena_mcp_enabled" in config


# Test get_filtered_config function - Developer (alias for implementer)
def test_get_filtered_config_developer(sample_product):
    """Test filtered config for developer role (alias)"""
    config = get_filtered_config("developer-agent", sample_product)

    # Should have developer fields
    assert "architecture" in config
    assert "tech_stack" in config
    assert "codebase_structure" in config
    assert "critical_features" in config
    assert "database_type" in config
    assert "backend_framework" in config
    assert "frontend_framework" in config

    # Developer doesn't get deployment_modes (difference from implementer)
    assert "deployment_modes" not in config


# Test get_filtered_config function - Tester
def test_get_filtered_config_tester(sample_product):
    """Test filtered config for tester role"""
    config = get_filtered_config("tester-qa-1", sample_product)

    # Should have tester fields
    assert "test_commands" in config
    assert "test_config" in config
    assert "critical_features" in config
    assert "known_issues" in config
    assert "tech_stack" in config

    # Should NOT have implementer-specific fields
    assert "codebase_structure" not in config
    assert "backend_framework" not in config
    assert "api_docs" not in config


# Test get_filtered_config function - QA (alias for tester)
def test_get_filtered_config_qa(sample_product):
    """Test filtered config for qa role (alias)"""
    config = get_filtered_config("qa-engineer", sample_product)

    # Should have qa fields
    assert "test_commands" in config
    assert "test_config" in config
    assert "critical_features" in config
    assert "known_issues" in config

    # QA doesn't get tech_stack (difference from tester)
    assert "tech_stack" not in config


# Test get_filtered_config function - Documenter
def test_get_filtered_config_documenter(sample_product):
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


# Test get_filtered_config function - Analyzer
def test_get_filtered_config_analyzer(sample_product):
    """Test filtered config for analyzer role"""
    config = get_filtered_config("analyzer-bot", sample_product)

    # Should have analyzer fields
    assert "architecture" in config
    assert "tech_stack" in config
    assert "codebase_structure" in config
    assert "critical_features" in config
    assert "known_issues" in config

    # Should NOT have test/doc-specific fields
    assert "test_commands" not in config
    assert "api_docs" not in config


# Test get_filtered_config function - Reviewer
def test_get_filtered_config_reviewer(sample_product):
    """Test filtered config for reviewer role"""
    config = get_filtered_config("reviewer-agent", sample_product)

    # Should have reviewer fields
    assert "architecture" in config
    assert "tech_stack" in config
    assert "critical_features" in config
    assert "documentation_style" in config

    # Should NOT have test/implementation-specific fields
    assert "test_commands" not in config
    assert "codebase_structure" not in config


# Test get_filtered_config function - Unknown role
def test_get_filtered_config_unknown_role_defaults_to_analyzer(sample_product):
    """Test unknown role defaults to analyzer filtering"""
    config = get_filtered_config("unknown-role-agent", sample_product)

    # Should use analyzer fields as default
    assert "architecture" in config
    assert "tech_stack" in config
    assert "codebase_structure" in config
    assert "critical_features" in config
    assert "known_issues" in config


# Test get_filtered_config function - Empty product
def test_get_filtered_config_empty_product(empty_product):
    """Test filtered config with no config_data"""
    config = get_filtered_config("implementer-1", empty_product)
    assert config == {}


# Test validate_config_data function
def test_validate_config_data_valid():
    """Test validation with valid config"""
    config = {
        "architecture": "FastAPI",
        "serena_mcp_enabled": True,
        "tech_stack": ["Python"],
        "test_commands": ["pytest"],
        "critical_features": ["Feature1"],
        "codebase_structure": {"src": "code"},
        "test_config": {"coverage": 80}
    }

    is_valid, errors = validate_config_data(config)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_config_data_missing_architecture():
    """Test validation with missing architecture"""
    config = {
        "serena_mcp_enabled": True,
        "tech_stack": ["Python"]
    }

    is_valid, errors = validate_config_data(config)
    assert is_valid is False
    assert "Missing required field: architecture" in errors


def test_validate_config_data_missing_serena_flag():
    """Test validation with missing serena_mcp_enabled"""
    config = {
        "architecture": "FastAPI",
        "tech_stack": ["Python"]
    }

    is_valid, errors = validate_config_data(config)
    assert is_valid is False
    assert "Missing required field: serena_mcp_enabled" in errors


def test_validate_config_data_wrong_type_tech_stack():
    """Test validation with wrong type for tech_stack"""
    config = {
        "architecture": "FastAPI",
        "serena_mcp_enabled": True,
        "tech_stack": "Python"  # Should be array
    }

    is_valid, errors = validate_config_data(config)
    assert is_valid is False
    assert "tech_stack must be an array" in errors


def test_validate_config_data_wrong_type_test_commands():
    """Test validation with wrong type for test_commands"""
    config = {
        "architecture": "FastAPI",
        "serena_mcp_enabled": True,
        "test_commands": {"cmd": "pytest"}  # Should be array
    }

    is_valid, errors = validate_config_data(config)
    assert is_valid is False
    assert "test_commands must be an array" in errors


def test_validate_config_data_wrong_type_critical_features():
    """Test validation with wrong type for critical_features"""
    config = {
        "architecture": "FastAPI",
        "serena_mcp_enabled": True,
        "critical_features": "Feature"  # Should be array
    }

    is_valid, errors = validate_config_data(config)
    assert is_valid is False
    assert "critical_features must be an array" in errors


def test_validate_config_data_wrong_type_codebase_structure():
    """Test validation with wrong type for codebase_structure"""
    config = {
        "architecture": "FastAPI",
        "serena_mcp_enabled": True,
        "codebase_structure": ["src", "api"]  # Should be object
    }

    is_valid, errors = validate_config_data(config)
    assert is_valid is False
    assert "codebase_structure must be an object" in errors


def test_validate_config_data_wrong_type_test_config():
    """Test validation with wrong type for test_config"""
    config = {
        "architecture": "FastAPI",
        "serena_mcp_enabled": True,
        "test_config": ["pytest"]  # Should be object
    }

    is_valid, errors = validate_config_data(config)
    assert is_valid is False
    assert "test_config must be an object" in errors


def test_validate_config_data_wrong_type_serena_flag():
    """Test validation with wrong type for serena_mcp_enabled"""
    config = {
        "architecture": "FastAPI",
        "serena_mcp_enabled": "yes"  # Should be bool
    }

    is_valid, errors = validate_config_data(config)
    assert is_valid is False
    assert "serena_mcp_enabled must be a boolean" in errors


def test_validate_config_data_multiple_errors():
    """Test validation with multiple errors"""
    config = {
        # Missing: architecture, serena_mcp_enabled
        "tech_stack": "Python",  # Should be array
        "test_commands": {"cmd": "pytest"},  # Should be array
        "codebase_structure": ["src"]  # Should be object
    }

    is_valid, errors = validate_config_data(config)
    assert is_valid is False
    assert len(errors) >= 5  # Multiple validation errors


# Test merge_config_updates function
def test_merge_config_updates_shallow():
    """Test shallow merge of config updates"""
    existing = {
        "architecture": "Old",
        "tech_stack": ["Python 3.10"]
    }

    updates = {
        "architecture": "New",
        "test_commands": ["pytest"]
    }

    merged = merge_config_updates(existing, updates)

    assert merged["architecture"] == "New"
    assert merged["tech_stack"] == ["Python 3.10"]
    assert merged["test_commands"] == ["pytest"]


def test_merge_config_updates_deep():
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


def test_merge_config_updates_array_replacement():
    """Test that arrays are replaced, not merged"""
    existing = {
        "tech_stack": ["Python 3.10", "PostgreSQL 16"]
    }

    updates = {
        "tech_stack": ["Python 3.11", "PostgreSQL 18"]
    }

    merged = merge_config_updates(existing, updates)

    # Arrays should be replaced entirely
    assert merged["tech_stack"] == ["Python 3.11", "PostgreSQL 18"]


def test_merge_config_updates_preserves_existing():
    """Test that existing fields not in updates are preserved"""
    existing = {
        "architecture": "FastAPI",
        "tech_stack": ["Python"],
        "critical_features": ["Feature1"]
    }

    updates = {
        "tech_stack": ["Python 3.11"]
    }

    merged = merge_config_updates(existing, updates)

    assert merged["architecture"] == "FastAPI"
    assert merged["critical_features"] == ["Feature1"]
    assert merged["tech_stack"] == ["Python 3.11"]


# Test get_config_summary function
def test_get_config_summary_full(sample_product):
    """Test config summary with all fields"""
    summary = get_config_summary(sample_product)

    assert "Architecture: FastAPI + PostgreSQL" in summary
    assert "Tech Stack:" in summary
    assert "Python 3.11" in summary
    assert "Critical Features: 2 defined" in summary
    assert "Test Commands: 1 configured" in summary
    assert "Serena MCP: enabled" in summary


def test_get_config_summary_minimal():
    """Test config summary with minimal config"""
    product = Product(
        id="minimal",
        tenant_key="test",
        name="Minimal",
        config_data={
            "architecture": "Simple",
            "serena_mcp_enabled": False
        }
    )

    summary = get_config_summary(product)

    assert "Architecture: Simple" in summary
    assert "Serena MCP: disabled" in summary


def test_get_config_summary_empty_product(empty_product):
    """Test config summary with no config_data"""
    summary = get_config_summary(empty_product)
    assert summary == "No configuration data available"


def test_get_config_summary_tech_stack_truncation():
    """Test that tech stack is truncated to first 3 items"""
    product = Product(
        id="many-tech",
        tenant_key="test",
        name="Many Tech",
        config_data={
            "architecture": "Complex",
            "tech_stack": ["Tech1", "Tech2", "Tech3", "Tech4", "Tech5"],
            "serena_mcp_enabled": True
        }
    )

    summary = get_config_summary(product)

    # Should only show first 3
    assert "Tech1" in summary
    assert "Tech2" in summary
    assert "Tech3" in summary
    # Should use join with comma
    assert "Tech1, Tech2, Tech3" in summary


# Test ROLE_CONFIG_FILTERS constant
def test_all_roles_have_filters():
    """Test that all expected roles have filter definitions"""
    expected_roles = [
        "orchestrator", "implementer", "developer",
        "tester", "qa", "documenter", "analyzer", "reviewer"
    ]

    for role in expected_roles:
        assert role in ROLE_CONFIG_FILTERS, f"Missing filter for role: {role}"


def test_orchestrator_filter_is_all():
    """Test that orchestrator filter is 'all'"""
    assert ROLE_CONFIG_FILTERS["orchestrator"] == "all"


def test_role_filters_are_lists_or_all():
    """Test that all role filters are either 'all' or lists"""
    for role, filter_value in ROLE_CONFIG_FILTERS.items():
        assert filter_value == "all" or isinstance(filter_value, list), \
            f"Role {role} filter must be 'all' or list"


def test_implementer_has_expected_fields():
    """Test implementer role has expected config fields"""
    expected_fields = [
        "architecture", "tech_stack", "codebase_structure",
        "critical_features", "database_type", "backend_framework",
        "frontend_framework", "deployment_modes"
    ]

    implementer_fields = ROLE_CONFIG_FILTERS["implementer"]
    for field in expected_fields:
        assert field in implementer_fields, f"Implementer missing field: {field}"


def test_tester_has_expected_fields():
    """Test tester role has expected config fields"""
    expected_fields = [
        "test_commands", "test_config", "critical_features",
        "known_issues", "tech_stack"
    ]

    tester_fields = ROLE_CONFIG_FILTERS["tester"]
    for field in expected_fields:
        assert field in tester_fields, f"Tester missing field: {field}"


def test_documenter_has_expected_fields():
    """Test documenter role has expected config fields"""
    expected_fields = [
        "api_docs", "documentation_style", "architecture",
        "critical_features", "codebase_structure"
    ]

    documenter_fields = ROLE_CONFIG_FILTERS["documenter"]
    for field in expected_fields:
        assert field in documenter_fields, f"Documenter missing field: {field}"
