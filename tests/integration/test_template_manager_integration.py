"""
Integration tests for template manager with real config.yaml.

Tests the full pipeline: config reading -> template generation -> Serena injection.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.template_manager import UnifiedTemplateManager


class TestTemplateManagerIntegration:
    """Integration test suite for template manager"""

    @pytest.mark.asyncio
    async def test_template_generation_with_real_config(self):
        """Test template generation works with actual project config."""
        # Use real config.yaml from project root
        manager = UnifiedTemplateManager()

        template = await manager.get_template(
            role="orchestrator",
            variables={
                "project_name": "Integration Test",
                "project_mission": "Test the template system",
                "product_name": "GiljoAI-MCP",
            },
        )

        # Should have base template content
        assert "You are the Project Orchestrator" in template
        assert "Integration Test" in template

        # Serena content presence depends on actual config.yaml
        # Just verify it doesn't crash

    @pytest.mark.asyncio
    async def test_all_roles_generate_successfully(self):
        """Test that all standard roles generate templates without errors."""
        manager = UnifiedTemplateManager()

        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter"]

        for role in roles:
            template = await manager.get_template(
                role=role,
                variables={
                    "project_name": "Test Project",
                    "project_mission": "Test mission",
                    "product_name": "Test Product",
                    "custom_mission": "Custom mission for role",
                },
            )

            # Basic validation
            assert len(template) > 0
            assert "Test Project" in template or "Test mission" in template or "Custom mission" in template

    @pytest.mark.asyncio
    async def test_augmentation_system_works_end_to_end(self):
        """Test that augmentation system works with real templates."""
        manager = UnifiedTemplateManager()

        # Custom augmentation
        custom_aug = {"type": "append", "content": "\n\nCUSTOM FOOTER CONTENT"}

        template = await manager.get_template(
            role="implementer",
            variables={"project_name": "Test", "custom_mission": "Test mission"},
            augmentations=[custom_aug],
        )

        # Should have custom content
        assert "CUSTOM FOOTER CONTENT" in template

    @pytest.mark.asyncio
    async def test_variables_substitution_works(self):
        """Test that variable substitution works correctly."""
        manager = UnifiedTemplateManager()

        template = await manager.get_template(
            role="orchestrator",
            variables={
                "project_name": "UNIQUE_PROJECT_123",
                "project_mission": "UNIQUE_MISSION_456",
                "product_name": "UNIQUE_PRODUCT_789",
            },
        )

        # Variables should be substituted
        assert "UNIQUE_PROJECT_123" in template
        assert "UNIQUE_MISSION_456" in template
        assert "UNIQUE_PRODUCT_789" in template

        # Placeholders should be gone
        assert "{project_name}" not in template
        assert "{project_mission}" not in template
        assert "{product_name}" not in template
