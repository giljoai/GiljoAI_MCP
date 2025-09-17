"""
Comprehensive test suite for UnifiedTemplateManager.

Tests template generation, role-specific templates, variable substitution,
behavioral rules, and success criteria for the new template system.
"""

import asyncio

import pytest

from src.giljo_mcp.template_manager import UnifiedTemplateManager, get_template_manager


class TestUnifiedTemplateManager:
    """Unit tests for UnifiedTemplateManager class."""

    @pytest.fixture
    async def template_manager(self):
        """Create a UnifiedTemplateManager instance."""
        return get_template_manager()

    @pytest.fixture
    def sample_variables(self):
        """Create sample template variables."""
        return {
            "project_name": "Test Project",
            "project_mission": "Build a comprehensive test system",
            "custom_mission": "Implement and test the template system",
            "product_name": "GiljoAI MCP",
        }

    @pytest.mark.asyncio
    async def test_orchestrator_template_generation(self, template_manager, sample_variables):
        """Test orchestrator template generation."""
        template = await template_manager.get_template(role="orchestrator", variables=sample_variables)

        assert isinstance(template, str)
        assert len(template) > 100  # Should be substantial
        assert "orchestrator" in template.lower() or "project orchestrator" in template.lower()
        assert sample_variables["project_name"] in template
        assert sample_variables["project_mission"] in template
        assert "VISION GUARDIAN" in template
        assert "SCOPE SHERIFF" in template

    @pytest.mark.asyncio
    async def test_analyzer_template_generation(self, template_manager, sample_variables):
        """Test analyzer template generation."""
        template = await template_manager.get_template(role="analyzer", variables=sample_variables)

        assert isinstance(template, str)
        assert len(template) > 50
        assert "analyzer" in template.lower() or "system analyzer" in template.lower()
        assert sample_variables["custom_mission"] in template
        assert "DISCOVERY WORKFLOW" in template

    @pytest.mark.asyncio
    async def test_implementer_template_generation(self, template_manager, sample_variables):
        """Test implementer template generation."""
        template = await template_manager.get_template(role="implementer", variables=sample_variables)

        assert isinstance(template, str)
        assert len(template) > 50
        assert "implementer" in template.lower() or "system implementer" in template.lower()
        assert sample_variables["custom_mission"] in template
        assert "IMPLEMENTATION WORKFLOW" in template

    @pytest.mark.asyncio
    async def test_all_agent_roles(self, template_manager, sample_variables):
        """Test template generation for all agent roles."""
        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter"]

        for role in roles:
            template = await template_manager.get_template(role=role, variables=sample_variables)

            assert isinstance(template, str)
            assert len(template) > 20
            assert role.lower() in template.lower() or "agent" in template.lower()

    @pytest.mark.asyncio
    async def test_variable_substitution(self, template_manager):
        """Test that variables are properly substituted in templates."""
        variables = {
            "project_name": "Variable Test Project",
            "custom_mission": "Test variable substitution functionality",
        }

        template = await template_manager.get_template(role="analyzer", variables=variables)

        assert variables["project_name"] in template
        assert variables["custom_mission"] in template

    def test_behavioral_rules_generation(self, template_manager):
        """Test behavioral rules for different roles."""
        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter"]

        for role in roles:
            rules = template_manager.get_behavioral_rules(role)

            assert isinstance(rules, list)
            assert len(rules) > 0
            assert all(isinstance(rule, str) for rule in rules)
            assert all(len(rule) > 10 for rule in rules)  # Rules should be meaningful

    def test_success_criteria_generation(self, template_manager):
        """Test success criteria for different roles."""
        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter"]

        for role in roles:
            criteria = template_manager.get_success_criteria(role)

            assert isinstance(criteria, list)
            assert len(criteria) > 0
            assert all(isinstance(criterion, str) for criterion in criteria)
            assert all(len(criterion) > 10 for criterion in criteria)  # Criteria should be meaningful

    @pytest.mark.asyncio
    async def test_template_without_variables(self, template_manager):
        """Test template generation without variables (should not crash)."""
        template = await template_manager.get_template(role="tester")

        assert isinstance(template, str)
        assert len(template) > 20
        assert "tester" in template.lower()

    @pytest.mark.asyncio
    async def test_invalid_role_fallback(self, template_manager):
        """Test that invalid roles get fallback templates."""
        template = await template_manager.get_template(role="nonexistent_role", variables={"project_name": "Test"})

        assert isinstance(template, str)
        assert len(template) > 0  # Should get some fallback content

    def test_cache_functionality(self, template_manager):
        """Test template caching functionality."""
        # Clear cache first
        template_manager.clear_cache()
        assert len(template_manager.get_cached_templates()) == 0

        # Cache should be empty initially
        cached = template_manager.get_cached_templates()
        assert isinstance(cached, list)

    @pytest.mark.asyncio
    async def test_concurrent_template_generation(self, template_manager, sample_variables):
        """Test concurrent template generation doesn't cause issues."""

        async def generate_template(role):
            return await template_manager.get_template(role=role, variables=sample_variables)

        # Generate multiple templates concurrently
        tasks = [
            generate_template("orchestrator"),
            generate_template("analyzer"),
            generate_template("implementer"),
            generate_template("tester"),
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 4
        assert all(isinstance(result, str) for result in results)
        assert all(len(result) > 20 for result in results)


class TestTemplateManagerIntegration:
    """Integration tests for template manager with database."""

    @pytest.mark.asyncio
    async def test_database_template_fallback(self):
        """Test that template manager falls back to legacy templates when DB is unavailable."""
        # Create template manager without database
        tm = UnifiedTemplateManager(db_manager=None)

        template = await tm.get_template(role="orchestrator", variables={"project_name": "Test"})

        assert isinstance(template, str)
        assert len(template) > 100
        assert "Test" in template

    @pytest.mark.asyncio
    async def test_template_manager_singleton(self):
        """Test that get_template_manager returns the same instance."""
        tm1 = get_template_manager()
        tm2 = get_template_manager()

        assert tm1 is tm2  # Should be the same instance


if __name__ == "__main__":
    pytest.main([__file__])
