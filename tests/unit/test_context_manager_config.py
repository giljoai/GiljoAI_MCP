"""
Unit tests for context_manager module - config retrieval, filtering, and summary

Split from test_context_manager.py. Tests cover:
- get_full_config
- get_filtered_config
- get_config_summary
"""

import pytest

from src.giljo_mcp.context_manager import (
    get_config_summary,
    get_filtered_config,
    get_full_config,
)
from src.giljo_mcp.models import Product


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
        product = Product(id="test-product-none", tenant_key="test-tenant", name="None Product", config_data=None)

        summary = get_config_summary(product)

        assert summary == "No configuration data available"
