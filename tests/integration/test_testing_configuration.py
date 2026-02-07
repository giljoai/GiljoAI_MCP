"""
Integration tests for Testing Configuration Context (Handover 0271)

Tests verify that testing configuration is properly extracted from Product
and included in orchestrator context based on field priority settings.

Test Coverage:
- Configuration inclusion based on priority (1-4)
- Detail level varies by priority
- Graceful handling of missing configuration
- Agent-specific guidance (tester vs others)
- Formatting and markdown structure
"""

from typing import Any, Dict
from uuid import uuid4

import pytest

from src.giljo_mcp.models.products import Product
from src.giljo_mcp.prompt_generation.testing_config_generator import TestingConfigGenerator


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_testing_config() -> Dict[str, Any]:
    """Sample complete testing configuration"""
    return {
        "coverage_target": 80,
        "quality_standards": "TDD required with >80% coverage, all tests passing before merge",
        "strategy": "Unit tests for services, integration tests for endpoints, E2E for workflows",
        "frameworks": {
            "backend": ["pytest", "pytest-asyncio", "httpx"],
            "frontend": ["vitest", "vue-test-utils", "cypress"],
        },
        "test_types": ["unit", "integration", "e2e"],
        "requirements": [
            "Write tests first (TDD)",
            "All tests must pass",
            "No bandaid fixes",
            "Test behavior not implementation",
            "Maintain >80% coverage",
        ],
    }


@pytest.fixture
def minimal_testing_config() -> Dict[str, Any]:
    """Minimal testing configuration with only coverage target"""
    return {"coverage_target": 85}


@pytest.fixture
async def test_product_with_config(db_session, sample_testing_config) -> Product:
    """Create a test product with testing configuration"""
    tenant_key = str(uuid4())
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Product for testing config tests",
        is_active=False,
        config_data={"testing_config": sample_testing_config},
    )
    db_session.add(product)
    await db_session.commit()
    return product


@pytest.fixture
async def test_product_minimal(db_session, minimal_testing_config) -> Product:
    """Create a test product with minimal testing configuration"""
    tenant_key = str(uuid4())
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Minimal Test Product",
        description="Product with minimal testing config",
        is_active=False,
        config_data={"testing_config": minimal_testing_config},
    )
    db_session.add(product)
    await db_session.commit()
    return product


@pytest.fixture
async def test_product_no_config(db_session) -> Product:
    """Create a test product with no testing configuration"""
    tenant_key = str(uuid4())
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="No Config Product",
        description="Product without testing config",
        is_active=False,
        config_data={},
    )
    db_session.add(product)
    await db_session.commit()
    return product


# ============================================================================
# GENERATOR TESTS - TestingConfigGenerator
# ============================================================================


class TestTestingConfigGenerator:
    """Unit tests for TestingConfigGenerator class"""

    def test_generate_context_priority_1_full_config(self, sample_testing_config):
        """Priority 1 (CRITICAL) should return full configuration with all details"""
        context = TestingConfigGenerator.generate_context(testing_config=sample_testing_config, priority=1)

        # Verify full context is generated
        assert len(context) > 0
        assert "testing configuration" in context.lower()
        assert "coverage" in context.lower()
        assert "80" in context  # Coverage target
        assert "quality standards" in context.lower()
        assert "strategy" in context.lower()
        assert "pytest" in context  # Framework mentioned
        assert "tdd" in context.lower()  # TDD workflow

    def test_generate_context_priority_2_standards_only(self, sample_testing_config):
        """Priority 2 (IMPORTANT) should return quality standards and frameworks only"""
        context = TestingConfigGenerator.generate_context(testing_config=sample_testing_config, priority=2)

        # Verify standards and frameworks present
        assert len(context) > 0
        assert "testing configuration" in context.lower()
        assert "coverage" in context.lower()
        assert "80" in context
        assert "quality standards" in context.lower()
        assert "pytest" in context
        # Full strategy should not be included
        assert context.count("strategy") == 0  # Not in priority 2

    def test_generate_context_priority_3_summary(self, sample_testing_config):
        """Priority 3 (NICE_TO_HAVE) should return summary only"""
        context = TestingConfigGenerator.generate_context(testing_config=sample_testing_config, priority=3)

        # Verify summary
        assert len(context) > 0
        assert "testing configuration" in context.lower()
        assert "80" in context  # Coverage target must be present
        assert "coverage" in context.lower()
        # Full details should not be included
        assert "pytest" not in context
        assert context.count("strategy") == 0

    def test_generate_context_priority_4_excluded(self, sample_testing_config):
        """Priority 4 (EXCLUDED) should return empty string"""
        context = TestingConfigGenerator.generate_context(testing_config=sample_testing_config, priority=4)

        # Verify nothing returned
        assert context == ""

    def test_generate_context_empty_config_priority_4(self):
        """Empty config with priority 4 should return empty string"""
        context = TestingConfigGenerator.generate_context(testing_config={}, priority=4)
        assert context == ""

    def test_generate_context_none_config(self):
        """None config should be handled gracefully"""
        context = TestingConfigGenerator.generate_context(testing_config=None, priority=2)
        # Should handle None without error
        assert context == ""

    def test_generate_context_empty_config_priority_1(self):
        """Empty config with priority > 0 should be handled"""
        context = TestingConfigGenerator.generate_context(testing_config={}, priority=1)
        # Should generate something with defaults
        assert "testing configuration" in context.lower()
        assert "coverage" in context.lower()  # Default included

    def test_generate_context_minimal_config(self, minimal_testing_config):
        """Minimal config should still generate proper context"""
        context = TestingConfigGenerator.generate_context(testing_config=minimal_testing_config, priority=1)

        # Verify coverage target included
        assert "85" in context
        assert "testing configuration" in context.lower()

    def test_generate_context_preserves_coverage_target(self, sample_testing_config):
        """Coverage target should be preserved across all priorities"""
        for priority in [1, 2, 3]:
            context = TestingConfigGenerator.generate_context(testing_config=sample_testing_config, priority=priority)
            assert "80" in context, f"Priority {priority} should include coverage target"

    def test_generate_context_markdown_formatting(self, sample_testing_config):
        """Context should be properly formatted as markdown"""
        context = TestingConfigGenerator.generate_context(testing_config=sample_testing_config, priority=1)

        # Verify markdown structure
        assert "## Testing Configuration" in context
        assert "**" in context  # Bold formatting
        assert context.count("\n") > 5  # Multiple lines

    def test_generate_context_priority_1_includes_tdd_workflow(self, sample_testing_config):
        """Priority 1 should include detailed TDD workflow"""
        context = TestingConfigGenerator.generate_context(testing_config=sample_testing_config, priority=1)

        # Verify TDD workflow present
        assert "tdd" in context.lower()
        assert "red" in context.lower() or "red" in context  # RED state
        assert "green" in context.lower() or "green" in context  # GREEN state
        assert "refactor" in context.lower()  # REFACTOR step


# ============================================================================
# AGENT-SPECIFIC GUIDANCE TESTS
# ============================================================================


class TestAgentSpecificGuidance:
    """Tests for agent-specific testing guidance"""

    def test_generate_for_agent_tester_full_config(self, sample_testing_config):
        """Tester agents should receive full testing configuration"""
        context = TestingConfigGenerator.generate_for_agent(
            testing_config=sample_testing_config, agent_display_name="tester"
        )

        # Tester should get full priority 1 config
        assert "testing configuration" in context.lower()
        assert "pytest" in context
        assert "tdd" in context.lower()
        assert len(context) > 300  # Full config is substantial

    def test_generate_for_agent_implementer_full_config(self, sample_testing_config):
        """Implementer agents should receive full testing configuration"""
        context = TestingConfigGenerator.generate_for_agent(
            testing_config=sample_testing_config, agent_display_name="implementer"
        )

        # Implementer should get full priority 1 config
        assert "testing configuration" in context.lower()
        assert "pytest" in context
        assert "tdd" in context.lower()

    def test_generate_for_agent_reviewer_standards_only(self, sample_testing_config):
        """Reviewer agents should receive standards and frameworks only"""
        context = TestingConfigGenerator.generate_for_agent(
            testing_config=sample_testing_config, agent_display_name="reviewer"
        )

        # Reviewer should get priority 2 (standards)
        assert "testing configuration" in context.lower()
        assert "80" in context
        assert "quality standards" in context.lower()
        # Should not have full TDD details
        assert context.count("tdd") == 0 or "tdd" not in context.lower()

    def test_generate_for_agent_architect_summary(self, sample_testing_config):
        """Architect agents should receive summary"""
        context = TestingConfigGenerator.generate_for_agent(
            testing_config=sample_testing_config, agent_display_name="architect"
        )

        # Architect should get priority 3 (summary)
        assert "testing configuration" in context.lower()
        assert "80" in context  # Coverage target
        # Should not have framework details
        assert "pytest" not in context or context.count("pytest") == 0

    def test_generate_for_agent_unknown_type_summary(self, sample_testing_config):
        """Unknown agent types should receive summary"""
        context = TestingConfigGenerator.generate_for_agent(
            testing_config=sample_testing_config, agent_display_name="unknown_agent"
        )

        # Unknown should default to priority 3
        assert "80" in context
        assert "testing configuration" in context.lower()


# ============================================================================
# INTEGRATION TESTS - Context Inclusion Based on Priority
# ============================================================================


@pytest.mark.asyncio
class TestTestingConfigContextIntegration:
    """Integration tests for testing config in orchestrator context"""

    async def test_testing_config_included_when_priority_set(self, db_session, test_product_with_config):
        """Testing config should be included when priority > 0"""
        # Extract config from product
        config_data = test_product_with_config.config_data or {}
        testing_config = config_data.get("testing_config", {})

        # Generate context with priority 2
        context = TestingConfigGenerator.generate_context(testing_config=testing_config, priority=2)

        # Verify included
        assert context != ""
        assert "testing configuration" in context.lower()
        assert "80" in context

    async def test_testing_config_excluded_when_priority_4(self, test_product_with_config):
        """Testing config should be excluded when priority = 4"""
        config_data = test_product_with_config.config_data or {}
        testing_config = config_data.get("testing_config", {})

        # Generate context with priority 4
        context = TestingConfigGenerator.generate_context(testing_config=testing_config, priority=4)

        # Verify excluded
        assert context == ""

    async def test_testing_config_detail_varies_by_priority(self, test_product_with_config):
        """Testing config detail should vary based on priority"""
        config_data = test_product_with_config.config_data or {}
        testing_config = config_data.get("testing_config", {})

        # Priority 1: Full
        context_full = TestingConfigGenerator.generate_context(testing_config=testing_config, priority=1)
        full_len = len(context_full)

        # Priority 3: Summary
        context_summary = TestingConfigGenerator.generate_context(testing_config=testing_config, priority=3)
        summary_len = len(context_summary)

        # Full should be longer than summary
        assert full_len > summary_len
        # Full should have more details
        assert "pytest" in context_full
        assert "pytest" not in context_summary or context_summary.count("pytest") == 0

    async def test_testing_config_handles_missing_config(self, test_product_no_config):
        """Testing config should handle missing configuration gracefully"""
        config_data = test_product_no_config.config_data or {}
        testing_config = config_data.get("testing_config", {})

        # Should not crash, should use defaults
        context = TestingConfigGenerator.generate_context(testing_config=testing_config, priority=1)

        # Should still generate something
        assert "testing configuration" in context.lower()

    async def test_testing_config_for_tester_agents(self, test_product_with_config):
        """Tester agents should receive full testing configuration"""
        config_data = test_product_with_config.config_data or {}
        testing_config = config_data.get("testing_config", {})

        context = TestingConfigGenerator.generate_for_agent(testing_config=testing_config, agent_display_name="tester")

        # Should have full config
        assert "pytest" in context
        assert "tdd" in context.lower()
        assert "red" in context.lower() or "green" in context.lower()

    async def test_testing_config_with_all_fields(self, db_session, sample_testing_config):
        """Test with complete testing configuration structure"""
        context = TestingConfigGenerator.generate_context(testing_config=sample_testing_config, priority=1)

        # All key fields should be represented
        assert "coverage" in context.lower()
        assert "quality" in context.lower()
        assert "strategy" in context.lower()
        assert "framework" in context.lower()
        assert "pytest" in context
        assert "vitest" in context

    async def test_testing_config_with_minimal_fields(self, test_product_minimal):
        """Test with minimal testing configuration"""
        config_data = test_product_minimal.config_data or {}
        testing_config = config_data.get("testing_config", {})

        context = TestingConfigGenerator.generate_context(testing_config=testing_config, priority=1)

        # Even minimal config should work
        assert "85" in context
        assert "testing configuration" in context.lower()

    async def test_testing_config_formatting_valid_markdown(self, test_product_with_config):
        """Testing config should produce valid markdown"""
        config_data = test_product_with_config.config_data or {}
        testing_config = config_data.get("testing_config", {})

        context = TestingConfigGenerator.generate_context(testing_config=testing_config, priority=1)

        # Verify markdown structure
        assert "## Testing Configuration" in context
        assert "**" in context  # At least one bold element
        assert "\n" in context  # Multiple lines
        # Verify no broken markdown
        bold_count = context.count("**")
        assert bold_count % 2 == 0  # Balanced bold markers

    async def test_testing_config_priority_boundaries(self, test_product_with_config):
        """Test boundary conditions for all priority levels"""
        config_data = test_product_with_config.config_data or {}
        testing_config = config_data.get("testing_config", {})

        # All valid priorities should work without error
        for priority in [1, 2, 3, 4]:
            context = TestingConfigGenerator.generate_context(testing_config=testing_config, priority=priority)
            # Should return string (even if empty)
            assert isinstance(context, str)


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


class TestEdgeCases:
    """Edge case tests for robustness"""

    def test_testing_config_with_special_characters(self):
        """Handle special characters in config"""
        config = {"coverage_target": 80, "quality_standards": "Code must be 'production-grade' & \"tested\""}

        context = TestingConfigGenerator.generate_context(testing_config=config, priority=1)

        assert "production-grade" in context
        assert "tested" in context

    def test_testing_config_with_empty_frameworks(self):
        """Handle empty frameworks dict"""
        config = {"coverage_target": 80, "frameworks": {}}

        context = TestingConfigGenerator.generate_context(testing_config=config, priority=1)

        # Should still generate valid context
        assert "testing configuration" in context.lower()

    def test_testing_config_with_malformed_coverage(self):
        """Handle invalid coverage targets"""
        config = {
            "coverage_target": "eighty"  # Not a number
        }

        # Should not crash
        context = TestingConfigGenerator.generate_context(testing_config=config, priority=1)

        assert isinstance(context, str)

    def test_testing_config_with_very_long_standards(self):
        """Handle very long quality standards text"""
        config = {
            "coverage_target": 90,
            "quality_standards": "A" * 1000,  # Very long string
        }

        context = TestingConfigGenerator.generate_context(testing_config=config, priority=1)

        # Should handle without truncation
        assert "A" * 100 in context

    def test_testing_config_multiple_frameworks(self):
        """Handle multiple frameworks in different platforms"""
        config = {
            "frameworks": {
                "backend": ["pytest", "unittest", "nose"],
                "frontend": ["vitest", "jest", "mocha"],
                "integration": ["cypress", "playwright"],
                "load": ["locust", "k6"],
            }
        }

        context = TestingConfigGenerator.generate_context(testing_config=config, priority=1)

        # All frameworks should be mentioned
        assert "pytest" in context
        assert "vitest" in context
        assert "cypress" in context
        assert "locust" in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
