"""
Tests for template manager Serena integration.

Validates conditional injection of Serena MCP guidance based on config.yaml.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.template_manager import UnifiedTemplateManager


class TestTemplateManagerSerenaIntegration:
    """Test suite for template manager Serena integration"""

    @pytest.mark.asyncio
    async def test_template_includes_serena_when_enabled(self, tmp_path):
        """Test Serena guidance appears when enabled in config."""
        # Create mock config
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            """
features:
  serena_mcp:
    enabled: true
    installed: true
"""
        )

        # Patch ConfigService to use test config
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {
                "enabled": True,
                "installed": True,
            }
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()
            template = await manager.get_template(
                role="orchestrator",
                variables={"project_name": "Test", "project_mission": "Test mission", "product_name": "Test product"},
            )

            assert "SERENA MCP TOOLS" in template
            assert "get_symbols_overview" in template
            assert "find_symbol" in template
            assert "find_referencing_symbols" in template

    @pytest.mark.asyncio
    async def test_template_excludes_serena_when_disabled(self, tmp_path):
        """Test no Serena guidance when disabled in config."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            """
features:
  serena_mcp:
    enabled: false
"""
        )

        # Patch ConfigService to use test config
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": False}
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()
            template = await manager.get_template(
                role="orchestrator",
                variables={"project_name": "Test", "project_mission": "Test mission", "product_name": "Test product"},
            )

            assert "SERENA MCP TOOLS" not in template

    @pytest.mark.asyncio
    async def test_analyzer_serena_guidance(self):
        """Test analyzer gets appropriate Serena guidance."""
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": True}
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()
            template = await manager.get_template(
                role="analyzer", variables={"project_name": "Test", "custom_mission": "Analyze system"}
            )

            assert "SERENA MCP FOR ANALYSIS" in template
            assert "get_symbols_overview" in template
            assert "ANALYSIS WORKFLOW:" in template

    @pytest.mark.asyncio
    async def test_implementer_serena_guidance(self):
        """Test implementer gets symbolic editing guidance."""
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": True}
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()
            template = await manager.get_template(
                role="implementer", variables={"project_name": "Test", "custom_mission": "Implement feature"}
            )

            assert "SERENA MCP FOR IMPLEMENTATION" in template
            assert "SYMBOLIC EDITING" in template
            assert "replace_symbol_body" in template
            assert "insert_after_symbol" in template
            assert "insert_before_symbol" in template

    @pytest.mark.asyncio
    async def test_tester_serena_guidance(self):
        """Test tester gets testing-focused guidance."""
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": True}
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()
            template = await manager.get_template(
                role="tester", variables={"project_name": "Test", "custom_mission": "Write tests"}
            )

            assert "SERENA MCP FOR TESTING" in template
            assert "TESTING WORKFLOW:" in template

    @pytest.mark.asyncio
    async def test_reviewer_serena_guidance(self):
        """Test reviewer gets code review guidance."""
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": True}
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()
            template = await manager.get_template(
                role="reviewer", variables={"project_name": "Test", "custom_mission": "Review code"}
            )

            assert "SERENA MCP FOR CODE REVIEW" in template
            assert "REVIEW WORKFLOW:" in template

    @pytest.mark.asyncio
    async def test_documenter_serena_guidance(self):
        """Test documenter gets documentation guidance."""
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": True}
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()
            template = await manager.get_template(
                role="documenter", variables={"project_name": "Test", "custom_mission": "Document API"}
            )

            assert "SERENA MCP FOR DOCUMENTATION" in template
            assert "DOCUMENTATION WORKFLOW:" in template

    @pytest.mark.asyncio
    async def test_injection_target_correct_for_each_role(self):
        """Test injection happens at correct location for each role."""
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": True}
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()

            # Test orchestrator injection
            template = await manager.get_template(
                role="orchestrator",
                variables={"project_name": "Test", "project_mission": "Test mission", "product_name": "Test product"},
            )
            # Serena guidance should appear after "YOUR DISCOVERY APPROACH"
            assert template.find("YOUR DISCOVERY APPROACH") < template.find("SERENA MCP TOOLS")

            # Test analyzer injection
            template = await manager.get_template(
                role="analyzer", variables={"project_name": "Test", "custom_mission": "Analyze"}
            )
            # Serena guidance should appear after "DISCOVERY WORKFLOW:"
            assert template.find("DISCOVERY WORKFLOW:") < template.find("SERENA MCP FOR ANALYSIS")

    @pytest.mark.asyncio
    async def test_serena_enabled_variable_set_in_template(self):
        """Test serena_enabled variable is set correctly."""
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": True}
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()
            template = await manager.get_template(
                role="orchestrator",
                variables={"project_name": "Test", "project_mission": "Test mission", "product_name": "Test product"},
            )

            # Variables are injected, so serena_enabled would be used
            # The presence of Serena content confirms the variable was True
            assert "SERENA MCP TOOLS" in template

    @pytest.mark.asyncio
    async def test_unknown_role_gets_generic_guidance(self):
        """Test unknown roles get generic Serena guidance."""
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": True}
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()

            # Get guidance for unknown role
            guidance = manager._get_serena_guidance("unknown_role")

            assert "SERENA MCP TOOLS AVAILABLE" in guidance
            assert "get_symbols_overview" in guidance
            assert "find_symbol" in guidance

    @pytest.mark.asyncio
    async def test_augmentation_preserves_existing_augmentations(self):
        """Test Serena augmentation doesn't override existing ones."""
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": True}
            mock_config.return_value = mock_instance

            manager = UnifiedTemplateManager()

            # Provide existing augmentation
            existing_aug = {"type": "append", "content": "\nCUSTOM CONTENT"}

            template = await manager.get_template(
                role="orchestrator",
                variables={"project_name": "Test", "project_mission": "Test mission", "product_name": "Test product"},
                augmentations=[existing_aug],
            )

            # Both augmentations should be present
            assert "SERENA MCP TOOLS" in template
            assert "CUSTOM CONTENT" in template

    @pytest.mark.asyncio
    async def test_cache_key_includes_serena_status(self):
        """Test cache key differentiates enabled/disabled Serena."""
        # This test verifies the _get_db_template method includes serena status in cache key
        manager = UnifiedTemplateManager()

        # Test that cache key includes serena status
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            # Mock enabled
            mock_instance = Mock()
            mock_instance.get_serena_config.return_value = {"enabled": True}
            mock_config.return_value = mock_instance

            # Access internal method (would need db_manager for full test)
            # Verify the logic is present by checking the code path
            assert hasattr(manager, "_get_db_template")

            # The key difference is validated by checking different templates are generated
            template1 = await manager.get_template(
                role="orchestrator",
                variables={"project_name": "Test", "project_mission": "Test mission", "product_name": "Test product"},
            )

            # Mock disabled
            mock_instance.get_serena_config.return_value = {"enabled": False}

            template2 = await manager.get_template(
                role="orchestrator",
                variables={"project_name": "Test", "project_mission": "Test mission", "product_name": "Test product"},
            )

            # Templates should be different
            assert "SERENA MCP TOOLS" in template1
            assert "SERENA MCP TOOLS" not in template2

    def test_get_injection_target_returns_correct_targets(self):
        """Test injection targets are correctly mapped for each role."""
        manager = UnifiedTemplateManager()

        assert manager._get_injection_target("orchestrator") == "YOUR DISCOVERY APPROACH"
        assert manager._get_injection_target("analyzer") == "DISCOVERY WORKFLOW:"
        assert manager._get_injection_target("implementer") == "IMPLEMENTATION WORKFLOW:"
        assert manager._get_injection_target("tester") == "TESTING WORKFLOW:"
        assert manager._get_injection_target("reviewer") == "REVIEW WORKFLOW:"
        assert manager._get_injection_target("documenter") == "DOCUMENTATION WORKFLOW:"
        assert manager._get_injection_target("unknown") == "RESPONSIBILITIES:"

    def test_create_serena_augmentation_structure(self):
        """Test Serena augmentation is correctly structured."""
        manager = UnifiedTemplateManager()

        aug = manager._create_serena_augmentation("orchestrator")

        assert aug["type"] == "inject"
        assert aug["target"] == "YOUR DISCOVERY APPROACH"
        assert "SERENA MCP TOOLS" in aug["content"]
        assert isinstance(aug["content"], str)

    @pytest.mark.asyncio
    async def test_error_handling_maintains_fallback(self):
        """Test that errors don't prevent template generation."""
        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            # Simulate ConfigService failure
            mock_config.side_effect = Exception("Config error")

            manager = UnifiedTemplateManager()

            # Should still return a template (fallback)
            template = await manager.get_template(
                role="orchestrator",
                variables={"project_name": "Test", "project_mission": "Test mission", "product_name": "Test product"},
            )

            # Should still have base template content
            assert "You are the Project Orchestrator" in template
