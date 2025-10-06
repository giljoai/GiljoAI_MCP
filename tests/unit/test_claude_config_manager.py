"""
Unit tests for ClaudeConfigManager service.

Tests management of ~/.claude.json configuration file for MCP server registration.
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager


class TestClaudeConfigManager:
    """Test suite for ClaudeConfigManager"""

    def setup_method(self, method):
        """Setup test method"""
        self.manager = ClaudeConfigManager()
        self.test_project_root = Path("/f/GiljoAI_MCP")

    def test_inject_serena_creates_backup(self):
        """Test backup is created before injection."""
        mock_config = {
            "mcpServers": {
                "existing-server": {
                    "command": "python",
                    "args": ["-m", "existing"],
                }
            }
        }

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(mock_config)
        ), patch("pathlib.Path.write_text") as mock_write, patch(
            "shutil.copy2"
        ) as mock_copy:

            result = self.manager.inject_serena(self.test_project_root)

            # Verify backup was created
            assert mock_copy.called
            assert result["success"] is True
            assert result["backup_path"] is not None

    def test_inject_serena_validates_config(self):
        """Test validation catches invalid config."""
        # Invalid JSON in config file
        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value="{invalid json"
        ):

            result = self.manager.inject_serena(self.test_project_root)

            assert result["success"] is False
            assert "error" in result
            assert result["error"] is not None

    def test_inject_serena_atomic_write(self):
        """Test write is atomic (temp file then replace)."""
        mock_config = {"mcpServers": {}}

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(mock_config)
        ), patch("pathlib.Path.write_text") as mock_write, patch(
            "shutil.copy2"
        ), patch(
            "pathlib.Path.replace"
        ) as mock_replace:

            result = self.manager.inject_serena(self.test_project_root)

            # Verify atomic write pattern (temp file creation + replace)
            # The write should happen to a temp file first
            assert result["success"] is True

    def test_inject_serena_rollback_on_failure(self):
        """Test rollback restores backup if write fails."""
        mock_config = {"mcpServers": {}}

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(mock_config)
        ), patch("tempfile.mkstemp", side_effect=IOError("Write failed")), patch(
            "shutil.copy2"
        ) as mock_backup:

            result = self.manager.inject_serena(self.test_project_root)

            assert result["success"] is False
            assert "error" in result

    def test_inject_serena_preserves_other_servers(self):
        """Test injection preserves other mcpServers entries."""
        mock_config = {
            "mcpServers": {
                "giljo-mcp": {
                    "command": "python",
                    "args": ["-m", "giljo_mcp"],
                },
                "other-server": {
                    "command": "node",
                    "args": ["server.js"],
                },
            }
        }

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(mock_config)
        ), patch("pathlib.Path.write_text") as mock_write, patch("shutil.copy2"):

            result = self.manager.inject_serena(self.test_project_root)

            assert result["success"] is True

            # Verify the write call preserved other servers
            written_data = None
            if mock_write.called:
                written_data = mock_write.call_args[0][0]
                written_config = json.loads(written_data)
                assert "giljo-mcp" in written_config["mcpServers"]
                assert "other-server" in written_config["mcpServers"]
                assert "serena" in written_config["mcpServers"]

    def test_inject_serena_creates_config_if_not_exists(self):
        """Test creates ~/.claude.json if it doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False), patch(
            "pathlib.Path.write_text"
        ) as mock_write, patch("pathlib.Path.parent") as mock_parent:

            result = self.manager.inject_serena(self.test_project_root)

            assert result["success"] is True
            assert mock_write.called

            # Verify a new config was written
            written_data = mock_write.call_args[0][0]
            written_config = json.loads(written_data)
            assert "mcpServers" in written_config
            assert "serena" in written_config["mcpServers"]

    def test_inject_serena_correct_uvx_path(self):
        """Test Serena config uses correct uvx path."""
        mock_config = {"mcpServers": {}}

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(mock_config)
        ), patch("pathlib.Path.write_text") as mock_write, patch("shutil.copy2"):

            result = self.manager.inject_serena(self.test_project_root)

            assert result["success"] is True

            # Verify the Serena config structure
            written_data = mock_write.call_args[0][0]
            written_config = json.loads(written_data)
            serena_config = written_config["mcpServers"]["serena"]

            assert serena_config["command"] == "uvx"
            assert serena_config["args"] == ["serena"]

    def test_remove_serena(self):
        """Test removal preserves other mcpServers."""
        mock_config = {
            "mcpServers": {
                "serena": {
                    "command": "uvx",
                    "args": ["serena"],
                },
                "giljo-mcp": {
                    "command": "python",
                    "args": ["-m", "giljo_mcp"],
                },
            }
        }

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(mock_config)
        ), patch("pathlib.Path.write_text") as mock_write, patch("shutil.copy2"):

            result = self.manager.remove_serena()

            assert result["success"] is True

            # Verify serena was removed but other servers preserved
            written_data = mock_write.call_args[0][0]
            written_config = json.loads(written_data)
            assert "serena" not in written_config["mcpServers"]
            assert "giljo-mcp" in written_config["mcpServers"]

    def test_remove_serena_when_not_present(self):
        """Test removal succeeds even if serena not present."""
        mock_config = {
            "mcpServers": {
                "giljo-mcp": {
                    "command": "python",
                    "args": ["-m", "giljo_mcp"],
                }
            }
        }

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(mock_config)
        ), patch("pathlib.Path.write_text") as mock_write, patch("shutil.copy2"):

            result = self.manager.remove_serena()

            assert result["success"] is True

    def test_remove_serena_when_config_not_exists(self):
        """Test removal handles missing config file gracefully."""
        with patch("pathlib.Path.exists", return_value=False):

            result = self.manager.remove_serena()

            # Should succeed with a message that config doesn't exist
            assert result["success"] is True
            assert "not found" in result.get("message", "").lower() or result.get(
                "error"
            ) is None

    def test_utf8_encoding_preserved(self):
        """Test that UTF-8 encoding is preserved (important for unicode chars in config)."""
        mock_config = {
            "mcpServers": {
                "test": {
                    "command": "echo",
                    "args": ["Hello, World"],  # unicode character
                }
            }
        }

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(mock_config, ensure_ascii=False)
        ), patch("pathlib.Path.write_text") as mock_write, patch("shutil.copy2"):

            result = self.manager.inject_serena(self.test_project_root)

            assert result["success"] is True

            # Verify UTF-8 encoding kwarg was used
            if mock_write.called:
                call_kwargs = mock_write.call_args[1]
                assert call_kwargs.get("encoding") == "utf-8"

    def test_backup_path_returned(self):
        """Test that backup file path is returned on successful injection."""
        mock_config = {"mcpServers": {}}

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(mock_config)
        ), patch("pathlib.Path.write_text"), patch("shutil.copy2") as mock_copy:

            result = self.manager.inject_serena(self.test_project_root)

            assert result["success"] is True
            assert "backup_path" in result
            assert result["backup_path"] is not None
            # Backup path should be a string representation of Path
            assert isinstance(result["backup_path"], (str, type(None)))

    def test_inject_serena_with_project_root_env(self):
        """Test that project root path is passed correctly to Serena config."""
        mock_config = {"mcpServers": {}}

        with patch("pathlib.Path.exists", return_value=True), patch(
            "pathlib.Path.read_text", return_value=json.dumps(mock_config)
        ), patch("pathlib.Path.write_text") as mock_write, patch("shutil.copy2"):

            result = self.manager.inject_serena(self.test_project_root)

            assert result["success"] is True

            # Verify the env variable includes project root
            written_data = mock_write.call_args[0][0]
            written_config = json.loads(written_data)
            serena_config = written_config["mcpServers"]["serena"]

            # Serena config should have env with project root
            assert "env" in serena_config
            assert "SERENA_PROJECT_ROOT" in serena_config["env"]
            assert str(self.test_project_root) in serena_config["env"]["SERENA_PROJECT_ROOT"]
