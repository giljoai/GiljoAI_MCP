"""
Unit tests for context_manager module - config retrieval, filtering, and summary

Split from test_context_manager.py. Tests cover:
- get_full_config
- get_filtered_config
- get_config_summary

Handover 0840c: Rewritten for normalized product config tables
(ProductTechStack, ProductArchitecture, ProductTestConfig).
"""


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
        assert "test_config" in config
        assert "core_features" in config

        # Verify nested structure
        assert config["tech_stack"]["programming_languages"] == "Python 3.11"
        assert config["architecture"]["primary_pattern"] == "FastAPI + PostgreSQL"
        assert config["test_config"]["test_strategy"] == "TDD"
        assert config["core_features"] == "Multi-tenant, Agent coordination"

    def test_get_full_config_minimal(self, minimal_product):
        """Test full config with minimal data (only architecture)"""
        config = get_full_config(minimal_product)

        assert "architecture" in config
        assert config["architecture"]["primary_pattern"] == "Simple App"
        # Should not have tech_stack or test_config keys since those are None
        assert "tech_stack" not in config
        assert "test_config" not in config

    def test_get_full_config_empty(self, empty_product):
        """Test full config with no normalized config data"""
        config = get_full_config(empty_product)

        assert config == {}

    def test_get_full_config_returns_independent_dict(self, sample_product):
        """Test that get_full_config returns a dict that does not mutate the product"""
        config = get_full_config(sample_product)
        config["new_field"] = "test"

        # A second call should not include the injected field
        config2 = get_full_config(sample_product)
        assert "new_field" not in config2


class TestGetFilteredConfig:
    """Tests for get_filtered_config function"""

    def test_get_filtered_config_implementer(self, sample_product):
        """Test filtered config for implementer role"""
        config = get_filtered_config("implementer-1", sample_product)

        # Should have implementer fields (architecture, tech_stack)
        assert "architecture" in config
        assert "tech_stack" in config

        # Should NOT have tester-specific fields
        assert "test_config" not in config

    def test_get_filtered_config_tester(self, sample_product):
        """Test filtered config for tester role"""
        config = get_filtered_config("tester-qa-1", sample_product)

        # Should have tester fields (test_config, tech_stack)
        assert "test_config" in config
        assert "tech_stack" in config

        # Should NOT have architecture
        assert "architecture" not in config

    def test_get_filtered_config_documenter(self, sample_product):
        """Test filtered config for documenter role"""
        config = get_filtered_config("documenter-agent", sample_product)

        # Should have documenter fields (architecture)
        assert "architecture" in config

        # Should NOT have test or tech fields
        assert "test_config" not in config
        assert "tech_stack" not in config

    def test_get_filtered_config_analyzer(self, sample_product):
        """Test filtered config for analyzer role"""
        config = get_filtered_config("analyzer-code", sample_product)

        # Should have analyzer fields (architecture, tech_stack)
        assert "architecture" in config
        assert "tech_stack" in config

        # Should NOT have test config
        assert "test_config" not in config

    def test_get_filtered_config_reviewer(self, sample_product):
        """Test filtered config for reviewer role"""
        config = get_filtered_config("reviewer-1", sample_product)

        # Should have reviewer fields (architecture, tech_stack)
        assert "architecture" in config
        assert "tech_stack" in config

        # Should NOT have test config
        assert "test_config" not in config

    def test_get_filtered_config_orchestrator_gets_all(self, sample_product):
        """Test orchestrator gets full config through filtering"""
        config = get_filtered_config("orchestrator", sample_product)
        full_config = get_full_config(sample_product)

        assert config == full_config

    def test_get_filtered_config_unknown_role_defaults_analyzer(self, sample_product):
        """Test unknown role defaults to analyzer filtering"""
        config = get_filtered_config("unknown-agent-123", sample_product)

        # Should have analyzer fields (architecture, tech_stack)
        assert "architecture" in config
        assert "tech_stack" in config

    def test_get_filtered_config_developer_alias(self, sample_product):
        """Test 'developer' role alias for implementer"""
        config = get_filtered_config("developer-1", sample_product)

        # Should behave like implementer
        assert "architecture" in config
        assert "tech_stack" in config

    def test_get_filtered_config_qa_alias(self, sample_product):
        """Test 'qa' role alias for tester"""
        config = get_filtered_config("qa-engineer", sample_product)

        # Should behave like tester (test_config)
        assert "test_config" in config

    def test_filtered_config_token_reduction(self, sample_product):
        """Test that filtering reduces the config payload"""
        full_config = get_full_config(sample_product)
        filtered_config = get_filtered_config("documenter-agent", sample_product)

        # Documenter should get fewer sections than orchestrator
        assert len(filtered_config) < len(full_config)

    def test_filtered_config_empty_product(self, empty_product):
        """Test filtering with empty config data"""
        config = get_filtered_config("implementer-1", empty_product)
        assert config == {}


class TestGetConfigSummary:
    """Tests for get_config_summary function"""

    def test_get_config_summary_complete(self, sample_product):
        """Test summary with complete normalized config"""
        summary = get_config_summary(sample_product)

        assert "Architecture:" in summary
        assert "FastAPI + PostgreSQL" in summary
        assert "Tech Stack:" in summary
        assert "Python 3.11" in summary
        assert "Core Features:" in summary
        assert "Test Strategy:" in summary
        assert "TDD" in summary

    def test_get_config_summary_minimal(self, minimal_product):
        """Test summary with minimal config (only architecture)"""
        summary = get_config_summary(minimal_product)

        assert "Architecture:" in summary
        assert "Simple App" in summary

    def test_get_config_summary_empty(self, empty_product):
        """Test summary with no config data"""
        summary = get_config_summary(empty_product)

        assert summary == "No configuration data available"

    def test_get_config_summary_no_relations(self):
        """Test summary with a product that has no normalized config at all"""
        product = Product(
            id="test-product-none",
            tenant_key="test-tenant",
            name="None Product",
        )

        summary = get_config_summary(product)

        assert summary == "No configuration data available"
