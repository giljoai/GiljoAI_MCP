"""
Integration tests for Serena MCP API endpoints.

These tests verify the complete API integration including:
- Detection endpoint
- Attachment endpoint
- Detachment endpoint
- Status endpoint

All tests follow production-grade standards with proper mocking,
error handling, and transactional behavior verification.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestSerenaDetectionEndpoint:
    """Tests for POST /api/setup/detect-serena"""

    def test_detect_serena_not_installed(self, api_client, monkeypatch):
        """Test detection when Serena not installed."""
        # Mock subprocess to simulate uvx not found
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("uvx not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        response = api_client.post("/api/setup/detect-serena")

        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is False
        assert data["uvx_available"] is False
        assert data["error"] is not None
        assert "uvx not found" in data["error"].lower()

    def test_detect_serena_installed(self, api_client, monkeypatch):
        """Test detection when Serena installed."""
        # Mock successful uvx and serena checks
        def mock_run(cmd, *args, **kwargs):
            if "uvx" in cmd and "--version" in cmd:
                return MagicMock(returncode=0, stdout="uvx 0.1.0")
            elif "uvx" in cmd and "serena" in cmd:
                return MagicMock(returncode=0, stdout="Serena MCP v1.2.3")
            return MagicMock(returncode=1)

        monkeypatch.setattr(subprocess, "run", mock_run)

        response = api_client.post("/api/setup/detect-serena")

        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is True
        assert data["uvx_available"] is True
        assert data["version"] == "1.2.3"
        assert data["error"] is None

    def test_detect_serena_uvx_available_but_serena_missing(self, api_client, monkeypatch):
        """Test when uvx exists but Serena package missing."""

        def mock_run(cmd, *args, **kwargs):
            if "uvx" in cmd and "--version" in cmd:
                return MagicMock(returncode=0, stdout="uvx 0.1.0")
            elif "uvx" in cmd and "serena" in cmd:
                return MagicMock(returncode=1, stderr="Package not found")
            return MagicMock(returncode=1)

        monkeypatch.setattr(subprocess, "run", mock_run)

        response = api_client.post("/api/setup/detect-serena")

        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is False
        assert data["uvx_available"] is True
        assert data["error"] is not None
        assert "serena" in data["error"].lower()

    def test_detect_serena_timeout(self, api_client, monkeypatch):
        """Test detection handles subprocess timeout."""

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="uvx", timeout=5)

        monkeypatch.setattr(subprocess, "run", mock_run)

        response = api_client.post("/api/setup/detect-serena")

        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is False
        assert data["error"] is not None
        assert "timeout" in data["error"].lower()

    def test_detect_serena_version_parsing(self, api_client, monkeypatch):
        """Test version is parsed correctly from output."""
        test_cases = [
            ("Serena MCP v1.2.3", "1.2.3"),
            ("serena 2.0.0", "2.0.0"),
            ("v3.1.4-beta", "3.1.4-beta"),
            ("1.5.0", "1.5.0"),
        ]

        for output, expected_version in test_cases:

            def mock_run(cmd, *args, **kwargs):
                if "uvx" in cmd and "--version" in cmd:
                    return MagicMock(returncode=0, stdout="uvx 0.1.0")
                elif "uvx" in cmd and "serena" in cmd:
                    return MagicMock(returncode=0, stdout=output)
                return MagicMock(returncode=1)

            monkeypatch.setattr(subprocess, "run", mock_run)

            response = api_client.post("/api/setup/detect-serena")
            data = response.json()

            assert data["version"] == expected_version, f"Failed to parse version from: {output}"


class TestSerenaAttachmentEndpoint:
    """Tests for POST /api/setup/attach-serena"""

    def test_attach_serena_success(self, api_client, temp_config_path, temp_claude_json, monkeypatch):
        """Test successful Serena attachment."""
        # Mock detection as success
        def mock_run(cmd, *args, **kwargs):
            if "uvx" in cmd and "--version" in cmd:
                return MagicMock(returncode=0, stdout="uvx 0.1.0")
            elif "uvx" in cmd and "serena" in cmd:
                return MagicMock(returncode=0, stdout="Serena MCP v1.2.3")
            return MagicMock(returncode=1)

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Mock Path.home() to use temp directory
        monkeypatch.setattr(Path, "home", lambda: temp_claude_json.parent)

        response = api_client.post("/api/setup/attach-serena")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "attached" in data["message"].lower()

        # Verify config.yaml updated
        import yaml

        with open(temp_config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert config["features"]["serena_mcp"]["enabled"] is True
        assert config["features"]["serena_mcp"]["registered"] is True

        # Verify .claude.json updated
        with open(temp_claude_json, encoding="utf-8") as f:
            claude_config = json.load(f)

        assert "serena" in claude_config["mcpServers"]
        assert claude_config["mcpServers"]["serena"]["command"] == "uvx"

    def test_attach_serena_not_detected(self, api_client, monkeypatch):
        """Test attachment fails when Serena not detected."""

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("uvx not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        response = api_client.post("/api/setup/attach-serena")

        assert response.status_code == 400
        data = response.json()
        assert "not detected" in data["detail"].lower() or "not found" in data["detail"].lower()

    def test_attach_serena_config_write_failure(self, api_client, temp_claude_json, monkeypatch):
        """Test rollback when config write fails."""
        # Mock successful detection
        def mock_run(cmd, *args, **kwargs):
            if "uvx" in cmd:
                return MagicMock(returncode=0, stdout="uvx 0.1.0")
            return MagicMock(returncode=0, stdout="Serena v1.0.0")

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Mock config write to fail
        original_open = open

        def mock_open(*args, **kwargs):
            if "config.yaml" in str(args[0]) and "w" in str(args[1] if len(args) > 1 else kwargs.get("mode", "")):
                raise IOError("Permission denied")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        response = api_client.post("/api/setup/attach-serena")

        # Should fail gracefully
        assert response.status_code >= 400

    def test_attach_serena_claude_json_write_failure(self, api_client, temp_config_path, monkeypatch):
        """Test rollback when .claude.json write fails."""
        # Mock successful detection
        def mock_run(cmd, *args, **kwargs):
            return MagicMock(returncode=0, stdout="OK")

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Read original config state
        import yaml

        with open(temp_config_path, encoding="utf-8") as f:
            original_config = yaml.safe_load(f)

        # Mock .claude.json write to fail but config.yaml succeeds
        original_open = open

        def mock_open(*args, **kwargs):
            if ".claude.json" in str(args[0]) and "w" in str(args[1] if len(args) > 1 else kwargs.get("mode", "")):
                raise IOError("Permission denied")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        response = api_client.post("/api/setup/attach-serena")

        assert response.status_code >= 400

        # Verify config.yaml was rolled back
        with open(temp_config_path, encoding="utf-8") as f:
            current_config = yaml.safe_load(f)

        assert current_config == original_config

    def test_attach_serena_idempotent(self, api_client, temp_claude_json, monkeypatch):
        """Test calling attach twice is safe."""
        # Mock successful detection
        def mock_run(cmd, *args, **kwargs):
            return MagicMock(returncode=0, stdout="Serena v1.0.0")

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(Path, "home", lambda: temp_claude_json.parent)

        # First call
        response1 = api_client.post("/api/setup/attach-serena")
        assert response1.status_code == 200

        # Second call should also succeed
        response2 = api_client.post("/api/setup/attach-serena")
        assert response2.status_code == 200

        data = response2.json()
        assert data["success"] is True

    def test_attach_serena_creates_backup(self, api_client, temp_claude_json, monkeypatch):
        """Test .claude.json backup created before modification."""
        # Write initial config
        initial_config = {"mcpServers": {"existing": {"command": "test"}}}
        temp_claude_json.write_text(json.dumps(initial_config))

        # Mock successful detection
        def mock_run(cmd, *args, **kwargs):
            return MagicMock(returncode=0, stdout="Serena v1.0.0")

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(Path, "home", lambda: temp_claude_json.parent)

        response = api_client.post("/api/setup/attach-serena")

        assert response.status_code == 200

        # Verify backup was created
        backup_dir = temp_claude_json.parent / ".claude_backups"
        assert backup_dir.exists()
        backups = list(backup_dir.glob("claude_config_backup_*.json"))
        assert len(backups) > 0

        # Verify backup contains original config
        with open(backups[0], encoding="utf-8") as f:
            backup_config = json.load(f)

        assert backup_config == initial_config


class TestSerenaDetachmentEndpoint:
    """Tests for POST /api/setup/detach-serena"""

    def test_detach_serena_success(self, api_client, temp_config_path, temp_claude_json, monkeypatch):
        """Test successful Serena detachment."""
        # Setup: Serena already attached
        import yaml

        config = yaml.safe_load(temp_config_path.read_text())
        config["features"]["serena_mcp"] = {"enabled": True, "registered": True, "installed": True}
        temp_config_path.write_text(yaml.dump(config))

        claude_config = {"mcpServers": {"serena": {"command": "uvx", "args": ["serena"]}}}
        temp_claude_json.write_text(json.dumps(claude_config))

        monkeypatch.setattr(Path, "home", lambda: temp_claude_json.parent)

        # Detach
        response = api_client.post("/api/setup/detach-serena")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify removed from .claude.json
        with open(temp_claude_json, encoding="utf-8") as f:
            claude_config_after = json.load(f)

        assert "serena" not in claude_config_after["mcpServers"]

        # Verify config.yaml updated
        with open(temp_config_path, encoding="utf-8") as f:
            config_after = yaml.safe_load(f)

        assert config_after["features"]["serena_mcp"]["enabled"] is False
        assert config_after["features"]["serena_mcp"]["registered"] is False

    def test_detach_serena_preserves_other_mcp_servers(self, api_client, temp_claude_json, monkeypatch):
        """Test other mcpServers remain in .claude.json."""
        # Setup with multiple MCP servers
        claude_config = {
            "mcpServers": {
                "serena": {"command": "uvx", "args": ["serena"]},
                "giljo-mcp": {"command": "python", "args": ["-m", "giljo_mcp"]},
                "other-tool": {"command": "node", "args": ["tool.js"]},
            }
        }
        temp_claude_json.write_text(json.dumps(claude_config))

        monkeypatch.setattr(Path, "home", lambda: temp_claude_json.parent)

        response = api_client.post("/api/setup/detach-serena")

        assert response.status_code == 200

        # Verify only serena removed
        with open(temp_claude_json, encoding="utf-8") as f:
            claude_config_after = json.load(f)

        assert "serena" not in claude_config_after["mcpServers"]
        assert "giljo-mcp" in claude_config_after["mcpServers"]
        assert "other-tool" in claude_config_after["mcpServers"]

    def test_detach_serena_when_not_attached(self, api_client, temp_claude_json, monkeypatch):
        """Test detaching when not attached is safe."""
        # Setup without serena
        claude_config = {"mcpServers": {"giljo-mcp": {"command": "python"}}}
        temp_claude_json.write_text(json.dumps(claude_config))

        monkeypatch.setattr(Path, "home", lambda: temp_claude_json.parent)

        response = api_client.post("/api/setup/detach-serena")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "not found" in data["message"].lower() or "already detached" in data["message"].lower()

    def test_detach_serena_config_write_failure(self, api_client, temp_config_path, monkeypatch):
        """Test partial failure handling."""
        import yaml

        # Read original state
        original_config = yaml.safe_load(temp_config_path.read_text())

        # Mock config write to fail
        original_open = open

        def mock_open(*args, **kwargs):
            if "config.yaml" in str(args[0]) and "w" in str(args[1] if len(args) > 1 else kwargs.get("mode", "")):
                raise IOError("Write failed")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        response = api_client.post("/api/setup/detach-serena")

        # Should handle error gracefully
        assert response.status_code >= 400


class TestSerenaStatusEndpoint:
    """Tests for GET /api/setup/serena-status"""

    def test_status_not_installed(self, api_client, temp_config_path, monkeypatch):
        """Test status when Serena not installed."""
        import yaml

        # Mock detection as not installed
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("uvx not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Set config to not installed
        config = yaml.safe_load(temp_config_path.read_text())
        config["features"] = {"serena_mcp": {"enabled": False, "installed": False, "registered": False}}
        temp_config_path.write_text(yaml.dump(config))

        response = api_client.get("/api/setup/serena-status")

        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is False
        assert data["enabled"] is False
        assert data["registered"] is False

    def test_status_installed_not_configured(self, api_client, temp_config_path, monkeypatch):
        """Test status when installed but not attached."""
        import yaml

        # Mock detection as installed
        def mock_run(cmd, *args, **kwargs):
            return MagicMock(returncode=0, stdout="Serena v1.0.0")

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Set config to installed but not enabled
        config = yaml.safe_load(temp_config_path.read_text())
        config["features"] = {"serena_mcp": {"enabled": False, "installed": True, "registered": False}}
        temp_config_path.write_text(yaml.dump(config))

        response = api_client.get("/api/setup/serena-status")

        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is True
        assert data["enabled"] is False
        assert data["registered"] is False

    def test_status_fully_configured(self, api_client, temp_config_path, monkeypatch):
        """Test status when fully configured."""
        import yaml

        # Set config to fully configured
        config = yaml.safe_load(temp_config_path.read_text())
        config["features"] = {"serena_mcp": {"enabled": True, "installed": True, "registered": True}}
        temp_config_path.write_text(yaml.dump(config))

        response = api_client.get("/api/setup/serena-status")

        assert response.status_code == 200
        data = response.json()
        assert data["installed"] is True
        assert data["enabled"] is True
        assert data["registered"] is True
