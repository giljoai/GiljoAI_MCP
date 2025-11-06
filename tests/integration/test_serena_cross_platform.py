"""
Cross-platform compatibility tests for Serena MCP integration.

Tests path handling, subprocess calls, and file operations
across Windows, Linux, and macOS.
"""

import platform
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestCrossPlatformPaths:
    """Tests for cross-platform path handling."""

    def test_claude_json_path_windows(self, monkeypatch):
        """Test .claude.json path on Windows."""
        if platform.system() != "Windows":
            pytest.skip("Windows-only test")

        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()

        # Path should use Windows home directory
        assert manager.claude_config_path.is_absolute()
        assert manager.claude_config_path.name == ".claude.json"

        # Should be in user's home directory
        home = Path.home()
        assert manager.claude_config_path.parent == home

    def test_claude_json_path_linux(self, monkeypatch):
        """Test .claude.json path on Linux."""
        if platform.system() != "Linux":
            pytest.skip("Linux-only test")

        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()

        # Path should use Linux home directory
        assert manager.claude_config_path.is_absolute()
        assert manager.claude_config_path.name == ".claude.json"

        home = Path.home()
        assert manager.claude_config_path.parent == home

    def test_claude_json_path_macos(self, monkeypatch):
        """Test .claude.json path on macOS."""
        if platform.system() != "Darwin":
            pytest.skip("macOS-only test")

        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()

        # Path should use macOS home directory
        assert manager.claude_config_path.is_absolute()
        assert manager.claude_config_path.name == ".claude.json"

        home = Path.home()
        assert manager.claude_config_path.parent == home

    def test_config_yaml_path_cross_platform(self):
        """Test config.yaml path works on all platforms."""
        from src.giljo_mcp.services.config_service import ConfigService

        service = ConfigService()

        # Should use pathlib.Path for cross-platform compatibility
        assert isinstance(service.config_path, Path)
        assert service.config_path.is_absolute()
        assert service.config_path.name == "config.yaml"

    def test_backup_directory_creation_cross_platform(self, tmp_path):
        """Test backup directory creation works on all platforms."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.backup_dir = tmp_path / ".claude_backups"

        # Create backup directory
        manager.backup_dir.mkdir(parents=True, exist_ok=True)

        assert manager.backup_dir.exists()
        assert manager.backup_dir.is_dir()

    def test_path_separator_independence(self, tmp_path):
        """Test code doesn't depend on specific path separators."""
        # Create nested structure
        nested_path = tmp_path / "level1" / "level2" / "config.yaml"
        nested_path.parent.mkdir(parents=True, exist_ok=True)
        nested_path.write_text("test: data")

        # Should work regardless of OS path separator
        assert nested_path.exists()
        assert nested_path.read_text() == "test: data"


class TestCrossPlatformDetection:
    """Tests for detection across platforms."""

    def test_uvx_detection_command_format(self, monkeypatch):
        """Test uvx detection uses list args (not shell string)."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        captured_calls = []

        def mock_run(cmd, *args, **kwargs):
            captured_calls.append((cmd, kwargs))
            return MagicMock(returncode=0, stdout="uvx 0.1.0")

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        detector.detect()

        # Verify command passed as list, not string
        assert len(captured_calls) > 0
        cmd, kwargs = captured_calls[0]
        assert isinstance(cmd, list)
        assert "shell" in kwargs
        assert kwargs["shell"] is False

    def test_subprocess_no_shell_injection(self, monkeypatch):
        """Test subprocess uses shell=False to prevent injection."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        captured_kwargs = []

        def mock_run(cmd, *args, **kwargs):
            captured_kwargs.append(kwargs)
            raise FileNotFoundError

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        detector.detect()

        # All subprocess calls should have shell=False
        for kwargs in captured_kwargs:
            assert kwargs.get("shell") is False

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_windows_executable_extension_handling(self, monkeypatch):
        """Test Windows executable extensions handled correctly."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        # Windows may find uvx.exe or uvx
        def mock_run(cmd, *args, **kwargs):
            # Should work with or without .exe
            if "uvx" in cmd[0]:
                return MagicMock(returncode=0, stdout="uvx 0.1.0")
            return MagicMock(returncode=1)

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        result = detector.detect()

        assert result["uvx_available"] is True

    @pytest.mark.skipif(platform.system() != "Linux", reason="Linux-specific test")
    def test_linux_executable_permissions(self, tmp_path):
        """Test Linux executable permission handling."""
        # Create a mock executable
        mock_exe = tmp_path / "mock_uvx"
        mock_exe.write_text("#!/bin/bash\necho 'uvx 0.1.0'")
        mock_exe.chmod(0o755)

        assert mock_exe.exists()
        assert mock_exe.stat().st_mode & 0o111  # Executable bits set

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS-specific test")
    def test_macos_path_resolution(self, monkeypatch):
        """Test macOS PATH resolution works correctly."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        # macOS may have executables in /usr/local/bin, /opt/homebrew/bin, etc.
        def mock_run(cmd, *args, **kwargs):
            return MagicMock(returncode=0, stdout="uvx 0.1.0")

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        result = detector.detect()

        assert result["uvx_available"] is True


class TestCrossPlatformFileOperations:
    """Tests for cross-platform file operations."""

    def test_atomic_write_cross_platform(self, tmp_path):
        """Test atomic write works on all platforms."""
        import json

        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.claude_config_path = tmp_path / ".claude.json"

        test_config = {"mcpServers": {"test": {"command": "test"}}}

        # Atomic write should work on all platforms
        manager._atomic_write(test_config)

        assert manager.claude_config_path.exists()

        with open(manager.claude_config_path, encoding="utf-8") as f:
            written_config = json.load(f)

        assert written_config == test_config

    def test_backup_file_naming_cross_platform(self, tmp_path):
        """Test backup file naming uses safe characters."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.claude_config_path = tmp_path / ".claude.json"
        manager.backup_dir = tmp_path / ".claude_backups"

        # Create initial file
        manager.claude_config_path.write_text("{}")

        # Create backup
        backup_path = manager._backup_claude_config()

        # Backup filename should be safe on all platforms
        # No colons (Windows), no special chars
        assert backup_path.exists()
        assert backup_path.parent == manager.backup_dir
        assert "claude_config_backup_" in backup_path.name

    def test_file_encoding_cross_platform(self, tmp_path):
        """Test UTF-8 encoding works on all platforms."""
        import json

        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.claude_config_path = tmp_path / ".claude.json"

        # Test with Unicode characters (emoji, various languages)
        test_config = {
            "mcpServers": {
                "test": {
                    "command": "test",
                    "description": "Test with 日本語 and emoji 🚀",
                }
            }
        }

        manager._atomic_write(test_config)

        # Read back and verify
        with open(manager.claude_config_path, encoding="utf-8") as f:
            read_config = json.load(f)

        assert read_config == test_config
        assert "日本語" in read_config["mcpServers"]["test"]["description"]
        assert "🚀" in read_config["mcpServers"]["test"]["description"]

    def test_line_ending_independence(self, tmp_path):
        """Test YAML parsing works with any line endings."""

        from src.giljo_mcp.services.config_service import ConfigService

        config_path = tmp_path / "config.yaml"

        # Write with Windows line endings
        config_text = "features:\r\n  serena_mcp:\r\n    enabled: true\r\n"
        config_path.write_bytes(config_text.encode("utf-8"))

        service = ConfigService(config_path)
        config = service.get_serena_config(use_cache=False)

        assert config["enabled"] is True

        # Write with Unix line endings
        config_text = "features:\n  serena_mcp:\n    enabled: false\n"
        config_path.write_bytes(config_text.encode("utf-8"))

        service.invalidate_cache()
        config = service.get_serena_config(use_cache=False)

        assert config["enabled"] is False


class TestCrossPlatformEnvironment:
    """Tests for environment variable handling."""

    def test_env_variable_serena_project_root(self, tmp_path):
        """Test SERENA_PROJECT_ROOT env var uses cross-platform paths."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()

        # Create config with path
        project_root = tmp_path / "project"
        project_root.mkdir()

        config = manager._add_serena_config({}, project_root)

        # Verify env var uses string path
        env_path = config["mcpServers"]["serena"]["env"]["SERENA_PROJECT_ROOT"]
        assert isinstance(env_path, str)

        # Should be convertible back to Path
        reconstructed_path = Path(env_path)
        assert reconstructed_path.is_absolute()

    def test_python_executable_path_detection(self):
        """Test Python executable path works on all platforms."""
        import sys

        # sys.executable should work on all platforms
        python_exe = Path(sys.executable)

        assert python_exe.exists()
        assert python_exe.is_file()

        # Should be executable
        if platform.system() != "Windows":
            assert python_exe.stat().st_mode & 0o111
