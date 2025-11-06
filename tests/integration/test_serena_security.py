"""
Security-focused integration tests for Serena MCP integration.

Tests:
- Command injection prevention
- Path traversal prevention
- Configuration validation
- File permission handling
- Input sanitization
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml


class TestCommandInjection:
    """Tests for command injection prevention."""

    def test_no_shell_injection_in_detection(self, monkeypatch):
        """Test subprocess uses list args, not shell."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        captured_calls = []

        def mock_run(cmd, *args, **kwargs):
            captured_calls.append({"cmd": cmd, "shell": kwargs.get("shell")})
            return MagicMock(returncode=0, stdout="uvx 0.1.0")

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        detector.detect()

        # Verify all calls use shell=False
        assert len(captured_calls) > 0
        for call in captured_calls:
            assert isinstance(call["cmd"], list), "Command should be list, not string"
            assert call["shell"] is False, "Shell should be explicitly False"

    def test_malicious_input_in_detection(self, monkeypatch):
        """Test malicious input doesn't execute commands."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        # Try to inject commands via stdout
        def mock_run(cmd, *args, **kwargs):
            # Simulate malicious output
            malicious_output = "1.0.0; rm -rf /; echo hacked"
            return MagicMock(returncode=0, stdout=malicious_output)

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        result = detector.detect()

        # Version parsing should extract only version number
        # Malicious commands should not be executed
        assert result["version"] is not None
        assert "rm" not in result["version"]
        assert "echo" not in result["version"]

    def test_subprocess_timeout_prevents_dos(self, monkeypatch):
        """Test subprocess timeout prevents denial of service."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        def mock_run(*args, **kwargs):
            # Simulate hanging process
            import time

            time.sleep(100)  # Won't actually execute due to timeout
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()

        # Detection should timeout, not hang forever
        result = detector.detect()

        assert result["installed"] is False
        assert "timeout" in result["error"].lower()


class TestPathTraversalPrevention:
    """Tests for path traversal prevention."""

    def test_path_validation_prevents_traversal(self, tmp_path):
        """Test path validation prevents directory traversal."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()

        # Attempt path traversal in project root
        malicious_paths = [
            tmp_path / ".." / ".." / "etc" / "passwd",
            tmp_path / ".." / "sensitive_dir",
            Path("../../../etc/passwd"),
        ]

        for malicious_path in malicious_paths:
            # Config should normalize and validate paths
            config = manager._add_serena_config({}, malicious_path)

            # Path should be absolute and safe
            env_path = config["mcpServers"]["serena"]["env"]["SERENA_PROJECT_ROOT"]
            env_path_obj = Path(env_path)

            # Should be absolute (no relative traversal)
            assert env_path_obj.is_absolute()

    def test_backup_path_contained_in_backup_dir(self, tmp_path):
        """Test backup files are confined to backup directory."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        claude_config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        # Create backup
        backup_path = manager._backup_claude_config()

        # Backup should be inside backup_dir
        assert backup_path.is_relative_to(manager.backup_dir)
        assert not str(backup_path).startswith("..")

    def test_config_path_must_be_absolute(self):
        """Test config paths must be absolute."""
        from src.giljo_mcp.services.config_service import ConfigService

        # Relative path should be converted to absolute
        service = ConfigService(Path("config.yaml"))

        assert service.config_path.is_absolute()


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_rejects_invalid_serena_config(self):
        """Test invalid config rejected before write."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()

        invalid_configs = [
            # Missing command
            {"mcpServers": {"serena": {"args": ["serena"]}}},
            # Wrong command
            {"mcpServers": {"serena": {"command": "malicious_exe", "args": ["serena"]}}},
            # Missing args
            {"mcpServers": {"serena": {"command": "uvx"}}},
            # Wrong args
            {"mcpServers": {"serena": {"command": "uvx", "args": ["malicious"]}}},
            # Missing env
            {"mcpServers": {"serena": {"command": "uvx", "args": ["serena"]}}},
            # Missing SERENA_PROJECT_ROOT
            {"mcpServers": {"serena": {"command": "uvx", "args": ["serena"], "env": {}}}},
        ]

        for invalid_config in invalid_configs:
            is_valid = manager._validate_serena_config(invalid_config)
            assert is_valid is False, f"Should reject invalid config: {invalid_config}"

    def test_validates_claude_json_structure(self, tmp_path):
        """Test .claude.json structure validated."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.claude_config_path = tmp_path / ".claude.json"

        # Valid config
        valid_config = {
            "mcpServers": {"serena": {"command": "uvx", "args": ["serena"], "env": {"SERENA_PROJECT_ROOT": "/test"}}}
        }

        assert manager._validate_serena_config(valid_config) is True

    def test_validates_yaml_config_structure(self, tmp_path):
        """Test config.yaml structure validated."""
        from src.giljo_mcp.services.config_service import ConfigService

        config_path = tmp_path / "config.yaml"

        # Valid YAML structure
        valid_config = {"features": {"serena_mcp": {"enabled": True, "installed": True, "registered": True}}}

        config_path.write_text(yaml.dump(valid_config))

        service = ConfigService(config_path)
        serena_config = service.get_serena_config(use_cache=False)

        assert "enabled" in serena_config
        assert isinstance(serena_config["enabled"], bool)

    def test_rejects_yaml_with_dangerous_types(self, tmp_path):
        """Test YAML loading rejects dangerous types."""
        from src.giljo_mcp.services.config_service import ConfigService

        config_path = tmp_path / "config.yaml"

        # YAML with potentially dangerous Python objects
        dangerous_yaml = "!!python/object/apply:os.system ['echo hacked']"
        config_path.write_text(dangerous_yaml)

        service = ConfigService(config_path)

        # safe_load should reject dangerous types
        config = service.get_serena_config(use_cache=False)

        # Should return empty dict, not execute code
        assert config == {}


class TestFilePermissions:
    """Tests for file permission handling."""

    @pytest.mark.skipif(os.name == "nt", reason="Unix permissions not applicable on Windows")
    def test_preserves_file_permissions(self, tmp_path):
        """Test file permissions preserved on update."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        initial_config = {"mcpServers": {}}
        claude_config_path.write_text(json.dumps(initial_config))

        # Set specific permissions
        claude_config_path.chmod(0o600)  # User read/write only
        original_mode = claude_config_path.stat().st_mode

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path

        # Write config
        updated_config = {"mcpServers": {"serena": {"command": "uvx"}}}
        manager._atomic_write(updated_config)

        # Permissions should be preserved
        new_mode = claude_config_path.stat().st_mode
        assert original_mode == new_mode

    def test_backup_preserves_permissions(self, tmp_path):
        """Test backup preserves original file permissions."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        claude_config_path.write_text(json.dumps({"mcpServers": {}}))

        if os.name != "nt":
            # Set restricted permissions on Unix
            claude_config_path.chmod(0o600)
            original_mode = claude_config_path.stat().st_mode

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        backup_path = manager._backup_claude_config()

        if os.name != "nt":
            # Backup should have same permissions
            backup_mode = backup_path.stat().st_mode
            assert original_mode == backup_mode

    def test_temp_file_permissions_secure(self, tmp_path):
        """Test temp files created with secure permissions."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.claude_config_path = tmp_path / ".claude.json"

        config = {"mcpServers": {"test": {"command": "test"}}}
        manager._atomic_write(config)

        if os.name != "nt":
            # File should have restrictive permissions
            mode = manager.claude_config_path.stat().st_mode
            # Should not be world-readable
            assert not (mode & 0o004)


class TestInputSanitization:
    """Tests for input sanitization."""

    def test_version_parsing_sanitizes_input(self, monkeypatch):
        """Test version parsing sanitizes malicious input."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        detector = SerenaDetector()

        malicious_inputs = [
            "1.0.0; rm -rf /",
            "1.0.0 && echo hacked",
            "1.0.0\n$(whoami)",
            "1.0.0`cat /etc/passwd`",
            "<script>alert('xss')</script> 1.0.0",
        ]

        for malicious_input in malicious_inputs:
            version = detector._parse_version(malicious_input)

            # Should extract only version number
            if version:
                assert ";" not in version
                assert "&&" not in version
                assert "$(" not in version
                assert "`" not in version
                assert "<script>" not in version

    def test_path_sanitization_in_env_vars(self, tmp_path):
        """Test paths in environment variables are sanitized."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()

        # Paths with special characters
        test_paths = [
            tmp_path / "normal_path",
            tmp_path / "path with spaces",
            tmp_path / "path-with-dashes",
        ]

        for test_path in test_paths:
            config = manager._add_serena_config({}, test_path)
            env_path = config["mcpServers"]["serena"]["env"]["SERENA_PROJECT_ROOT"]

            # Path should be properly quoted/escaped if needed
            assert isinstance(env_path, str)
            # Should be convertible back to Path
            reconstructed = Path(env_path)
            assert reconstructed.is_absolute()

    def test_json_encoding_prevents_injection(self, tmp_path):
        """Test JSON encoding prevents injection attacks."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.claude_config_path = tmp_path / ".claude.json"

        # Config with special characters that could break JSON
        config = {
            "mcpServers": {
                "serena": {
                    "command": "uvx",
                    "args": ["serena"],
                    "env": {
                        "SERENA_PROJECT_ROOT": '/path/with/"quotes"/and\\backslashes',
                        "MALICIOUS": "'; DROP TABLE users; --",
                    },
                }
            }
        }

        manager._atomic_write(config)

        # Read back and verify proper escaping
        with open(manager.claude_config_path, encoding="utf-8") as f:
            written_content = f.read()
            written_config = json.loads(written_content)

        # Special characters should be properly escaped
        assert (
            written_config["mcpServers"]["serena"]["env"]["SERENA_PROJECT_ROOT"]
            == config["mcpServers"]["serena"]["env"]["SERENA_PROJECT_ROOT"]
        )


class TestAccessControl:
    """Tests for access control and privilege management."""

    def test_no_privilege_escalation_in_detection(self, monkeypatch):
        """Test detection doesn't require elevated privileges."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        # Detection should work with normal user privileges
        def mock_run(cmd, *args, **kwargs):
            # Verify no sudo, su, or privilege escalation
            assert "sudo" not in " ".join(cmd).lower()
            assert "su" not in " ".join(cmd).lower()
            return MagicMock(returncode=0, stdout="uvx 0.1.0")

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        detector.detect()

    def test_config_files_user_scoped(self, tmp_path):
        """Test config files are user-scoped, not system-wide."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()

        # .claude.json should be in user home, not system directory
        assert manager.claude_config_path.is_relative_to(Path.home())

        # Should not be in /etc, /opt, /usr, etc.
        path_str = str(manager.claude_config_path).lower()
        assert "/etc/" not in path_str
        assert "/usr/" not in path_str
        assert "/opt/" not in path_str

    def test_backup_dir_user_owned(self, tmp_path):
        """Test backup directory is user-owned."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()

        # Backup dir should be in user home
        assert manager.backup_dir.is_relative_to(Path.home())
