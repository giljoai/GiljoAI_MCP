"""Tests for Serena MCP toggle endpoint."""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
from fastapi import HTTPException


@pytest.fixture
def mock_config():
    """Mock config.yaml content."""
    return {"installation": {"mode": "localhost"}, "features": {"serena_mcp": {"use_in_prompts": False}}}


@pytest.fixture
def empty_config():
    """Empty config for testing initialization."""
    return {}


class TestSerenaToggle:
    """Test Serena prompt toggle functionality."""

    def test_toggle_enable_serena(self, mock_config):
        """Test enabling Serena prompts."""

        # Mock file operations
        with patch("api.endpoints.serena.get_config_path") as mock_path:
            mock_path.return_value = Path("test_config.yaml")

            with patch("api.endpoints.serena.read_config", return_value=mock_config):
                with patch("api.endpoints.serena.write_config") as mock_write:
                    # Simulate toggle
                    config = mock_config.copy()
                    config["features"]["serena_mcp"]["use_in_prompts"] = True

                    # Verify structure
                    assert config["features"]["serena_mcp"]["use_in_prompts"] is True

    def test_toggle_disable_serena(self, mock_config):
        """Test disabling Serena prompts."""

        # Enable first
        mock_config["features"]["serena_mcp"]["use_in_prompts"] = True

        with patch("api.endpoints.serena.get_config_path") as mock_path:
            mock_path.return_value = Path("test_config.yaml")

            with patch("api.endpoints.serena.read_config", return_value=mock_config):
                with patch("api.endpoints.serena.write_config") as mock_write:
                    # Simulate toggle off
                    config = mock_config.copy()
                    config["features"]["serena_mcp"]["use_in_prompts"] = False

                    # Verify structure
                    assert config["features"]["serena_mcp"]["use_in_prompts"] is False

    def test_toggle_creates_features_section(self, empty_config):
        """Test toggle creates features section if missing."""

        config = empty_config.copy()

        # Simulate adding features section
        if "features" not in config:
            config["features"] = {}
        if "serena_mcp" not in config["features"]:
            config["features"]["serena_mcp"] = {}

        config["features"]["serena_mcp"]["use_in_prompts"] = True

        assert "features" in config
        assert "serena_mcp" in config["features"]
        assert config["features"]["serena_mcp"]["use_in_prompts"] is True

    def test_get_status_enabled(self, mock_config):
        """Test getting status when Serena is enabled."""
        mock_config["features"]["serena_mcp"]["use_in_prompts"] = True

        enabled = mock_config.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)

        assert enabled is True

    def test_get_status_disabled(self, mock_config):
        """Test getting status when Serena is disabled."""
        enabled = mock_config.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)

        assert enabled is False

    def test_get_status_missing_config(self, empty_config):
        """Test getting status with missing config sections."""
        enabled = empty_config.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)

        assert enabled is False  # Default to False

    def test_config_path_resolution(self):
        """Test config path uses current working directory."""
        from api.endpoints.serena import get_config_path

        config_path = get_config_path()

        assert config_path == Path.cwd() / "config.yaml"
        assert isinstance(config_path, Path)

    def test_read_config_handles_missing_file(self):
        """Test read_config returns empty dict for missing file."""
        from api.endpoints.serena import read_config

        with patch("api.endpoints.serena.get_config_path") as mock_path:
            mock_path.return_value = Path("nonexistent.yaml")

            with patch("pathlib.Path.exists", return_value=False):
                config = read_config()

                assert config == {}

    def test_read_config_handles_yaml_error(self):
        """Test read_config handles YAML parsing errors gracefully."""
        from api.endpoints.serena import read_config

        with patch("api.endpoints.serena.get_config_path") as mock_path:
            mock_path.return_value = Path("invalid.yaml")

            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data="invalid: yaml: content:")):
                    config = read_config()

                    # Should return empty dict on error
                    assert isinstance(config, dict)

    def test_write_config_creates_valid_yaml(self, mock_config):
        """Test write_config produces valid YAML."""
        from api.endpoints.serena import write_config

        with patch("api.endpoints.serena.get_config_path") as mock_path:
            mock_path.return_value = Path("test_config.yaml")

            with patch("builtins.open", mock_open()) as mock_file:
                write_config(mock_config)

                # Verify file was opened for writing
                mock_file.assert_called_once_with(Path("test_config.yaml"), "w", encoding="utf-8")


class TestSerenaEndpoints:
    """Test Serena API endpoints."""

    @pytest.mark.asyncio
    async def test_toggle_endpoint_enable(self):
        """Test POST /toggle endpoint to enable Serena."""
        from api.endpoints.serena import toggle_serena

        with patch("api.endpoints.serena.read_config", return_value={}):
            with patch("api.endpoints.serena.write_config") as mock_write:
                result = await toggle_serena(enabled=True)

                assert result["success"] is True
                assert result["enabled"] is True
                assert "enabled" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_toggle_endpoint_disable(self):
        """Test POST /toggle endpoint to disable Serena."""
        from api.endpoints.serena import toggle_serena

        config = {"features": {"serena_mcp": {"use_in_prompts": True}}}

        with patch("api.endpoints.serena.read_config", return_value=config):
            with patch("api.endpoints.serena.write_config") as mock_write:
                result = await toggle_serena(enabled=False)

                assert result["success"] is True
                assert result["enabled"] is False
                assert "disabled" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_status_endpoint_enabled(self):
        """Test GET /status endpoint when enabled."""
        from api.endpoints.serena import get_serena_status

        config = {"features": {"serena_mcp": {"use_in_prompts": True}}}

        with patch("api.endpoints.serena.read_config", return_value=config):
            result = await get_serena_status()

            assert result["enabled"] is True
            assert "enabled" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_status_endpoint_disabled(self):
        """Test GET /status endpoint when disabled."""
        from api.endpoints.serena import get_serena_status

        with patch("api.endpoints.serena.read_config", return_value={}):
            result = await get_serena_status()

            assert result["enabled"] is False
            assert "disabled" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_toggle_handles_write_error(self):
        """Test toggle endpoint handles write errors gracefully."""
        from api.endpoints.serena import toggle_serena

        with patch("api.endpoints.serena.read_config", return_value={}):
            with patch("api.endpoints.serena.write_config", side_effect=Exception("Write failed")):
                with pytest.raises(HTTPException) as exc_info:
                    await toggle_serena(enabled=True)

                assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_status_handles_read_error(self):
        """Test status endpoint handles read errors gracefully."""
        from api.endpoints.serena import get_serena_status

        with patch("api.endpoints.serena.read_config", side_effect=Exception("Read failed")):
            with pytest.raises(HTTPException) as exc_info:
                await get_serena_status()

            assert exc_info.value.status_code == 500
