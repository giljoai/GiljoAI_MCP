"""
Test template manager with Serena enabled in config.yaml.

This test temporarily modifies config.yaml to test the enabled flow.
"""

import sys
from pathlib import Path
import shutil

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.template_manager import UnifiedTemplateManager


class TestSerenaEnabledFlow:
    """Test Serena-enabled template generation flow"""

    @pytest.fixture
    def config_backup(self):
        """Backup and restore config.yaml."""
        config_path = Path.cwd() / "config.yaml"
        backup_path = Path.cwd() / "config.yaml.backup"

        # Backup original config
        if config_path.exists():
            shutil.copy(config_path, backup_path)

        yield config_path

        # Restore original config
        if backup_path.exists():
            shutil.copy(backup_path, config_path)
            backup_path.unlink()

    @pytest.mark.asyncio
    async def test_serena_enabled_produces_guidance(self, config_backup, tmp_path):
        """Test that enabling Serena adds guidance to templates."""
        # Create test config with Serena enabled
        config_path = tmp_path / "config.yaml"
        config_data = {
            "features": {
                "serena_mcp": {
                    "enabled": True,
                    "installed": True,
                    "registered": True,
                }
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        # Use ConfigService with test config
        from src.giljo_mcp.services.config_service import ConfigService

        config_service = ConfigService(config_path=config_path)
        serena_config = config_service.get_serena_config()

        # Verify config reads correctly
        assert serena_config["enabled"] is True

        # Test template generation with mocked ConfigService
        from unittest.mock import patch

        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_config.return_value = config_service

            manager = UnifiedTemplateManager()
            template = await manager.get_template(
                role="orchestrator",
                variables={
                    "project_name": "Test Project",
                    "project_mission": "Test Mission",
                    "product_name": "Test Product",
                },
            )

            # Should have Serena guidance
            assert "SERENA MCP TOOLS" in template
            assert "get_symbols_overview" in template

    @pytest.mark.asyncio
    async def test_serena_disabled_omits_guidance(self, tmp_path):
        """Test that disabling Serena omits guidance from templates."""
        # Create test config with Serena disabled
        config_path = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"enabled": False}}}

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        from src.giljo_mcp.services.config_service import ConfigService
        from unittest.mock import patch

        config_service = ConfigService(config_path=config_path)

        with patch("src.giljo_mcp.template_manager.ConfigService") as mock_config:
            mock_config.return_value = config_service

            manager = UnifiedTemplateManager()
            template = await manager.get_template(
                role="orchestrator",
                variables={
                    "project_name": "Test Project",
                    "project_mission": "Test Mission",
                    "product_name": "Test Product",
                },
            )

            # Should NOT have Serena guidance
            assert "SERENA MCP TOOLS" not in template
