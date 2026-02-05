"""
Integration tests for Serena services working together.

Tests the orchestration of multiple services:
- SerenaDetector
- ClaudeConfigManager
- ConfigService
- Template integration

These tests verify transactional behavior, rollback mechanisms,
and proper service coordination.
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import yaml


class TestSerenaDetectorService:
    """Tests for SerenaDetector service in isolation."""

    def test_detector_uvx_check_success(self, monkeypatch):
        """Test successful uvx detection."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        def mock_run(cmd, *args, **kwargs):
            if "uvx" in cmd and "--version" in cmd:
                return MagicMock(returncode=0, stdout="uvx 0.1.0")
            return MagicMock(returncode=1)

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        result = detector.detect()

        assert result["uvx_available"] is True

    def test_detector_uvx_not_found(self, monkeypatch):
        """Test uvx not found handling."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("uvx not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        result = detector.detect()

        assert result["uvx_available"] is False
        assert result["installed"] is False
        assert "uvx not found" in result["error"].lower()

    def test_detector_serena_installed(self, monkeypatch):
        """Test complete detection flow when Serena installed."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        def mock_run(cmd, *args, **kwargs):
            if "uvx" in cmd and "--version" in cmd:
                return MagicMock(returncode=0, stdout="uvx 0.1.0")
            if "serena" in cmd:
                return MagicMock(returncode=0, stdout="Serena MCP v1.2.3")
            return MagicMock(returncode=1)

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        result = detector.detect()

        assert result["uvx_available"] is True
        assert result["installed"] is True
        assert result["version"] == "1.2.3"
        assert result["error"] is None

    def test_detector_timeout_handling(self, monkeypatch):
        """Test timeout handling."""
        from src.giljo_mcp.services.serena_detector import SerenaDetector

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="uvx", timeout=5)

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        result = detector.detect()

        assert result["installed"] is False
        assert "timeout" in result["error"].lower()


class TestClaudeConfigManagerService:
    """Tests for ClaudeConfigManager service."""

    def test_inject_serena_success(self, tmp_path):
        """Test successful Serena injection."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        # Create temp .claude.json
        claude_config_path = tmp_path / ".claude.json"
        initial_config = {"mcpServers": {"existing": {"command": "test"}}}
        claude_config_path.write_text(json.dumps(initial_config))

        # Initialize manager with custom path
        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        project_root = Path("/test/project")

        result = manager.inject_serena(project_root)

        assert result["success"] is True
        assert result["backup_path"] is not None

        # Verify config updated
        with open(claude_config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert "serena" in config["mcpServers"]
        assert config["mcpServers"]["serena"]["command"] == "uvx"
        assert config["mcpServers"]["serena"]["args"] == ["serena"]
        assert "SERENA_PROJECT_ROOT" in config["mcpServers"]["serena"]["env"]

        # Verify existing server preserved
        assert "existing" in config["mcpServers"]

    def test_inject_serena_creates_backup(self, tmp_path):
        """Test backup creation during injection."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        initial_config = {"mcpServers": {}}
        claude_config_path.write_text(json.dumps(initial_config))

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        result = manager.inject_serena(Path("/test"))

        assert result["success"] is True

        # Verify backup exists
        backup_dir = tmp_path / ".claude_backups"
        assert backup_dir.exists()
        backups = list(backup_dir.glob("*.json"))
        assert len(backups) > 0

    def test_inject_serena_rollback_on_error(self, tmp_path, monkeypatch):
        """Test rollback on injection error."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        initial_config = {"mcpServers": {"original": {"command": "test"}}}
        claude_config_path.write_text(json.dumps(initial_config))

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        # Mock atomic write to fail
        original_atomic_write = manager._atomic_write

        def mock_atomic_write(*args, **kwargs):
            raise OSError("Write failed")

        monkeypatch.setattr(manager, "_atomic_write", mock_atomic_write)

        result = manager.inject_serena(Path("/test"))

        assert result["success"] is False
        assert "error" in result

        # Verify original config restored
        with open(claude_config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert config == initial_config

    def test_remove_serena_success(self, tmp_path):
        """Test successful Serena removal."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        initial_config = {"mcpServers": {"serena": {"command": "uvx"}, "other": {"command": "test"}}}
        claude_config_path.write_text(json.dumps(initial_config))

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        result = manager.remove_serena()

        assert result["success"] is True

        # Verify serena removed
        with open(claude_config_path, encoding="utf-8") as f:
            config = json.load(f)

        assert "serena" not in config["mcpServers"]
        assert "other" in config["mcpServers"]

    def test_remove_serena_when_not_present(self, tmp_path):
        """Test removing when Serena not present."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        initial_config = {"mcpServers": {"other": {"command": "test"}}}
        claude_config_path.write_text(json.dumps(initial_config))

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        result = manager.remove_serena()

        assert result["success"] is True
        assert "not found" in result["message"].lower()

    def test_remove_serena_when_file_not_exists(self, tmp_path):
        """Test removing when config file doesn't exist."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.claude_config_path = tmp_path / ".claude.json"  # Doesn't exist

        result = manager.remove_serena()

        assert result["success"] is True
        assert "not found" in result["message"].lower()


class TestConfigService:
    """Tests for ConfigService with real config.yaml."""

    def test_read_serena_config_from_file(self, tmp_path):
        """Test reading Serena config from real file."""
        from src.giljo_mcp.services.config_service import ConfigService

        config_path = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"enabled": True, "installed": True, "registered": True}}}
        config_path.write_text(yaml.dump(config_data))

        service = ConfigService(config_path)
        serena_config = service.get_serena_config(use_cache=False)

        assert serena_config["enabled"] is True
        assert serena_config["installed"] is True
        assert serena_config["registered"] is True

    def test_config_service_caching(self, tmp_path):
        """Test caching behavior."""
        from src.giljo_mcp.services.config_service import ConfigService

        config_path = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"enabled": True}}}
        config_path.write_text(yaml.dump(config_data))

        service = ConfigService(config_path)

        # First read (from file)
        config1 = service.get_serena_config(use_cache=False)
        assert config1["enabled"] is True

        # Modify file
        config_data["features"]["serena_mcp"]["enabled"] = False
        config_path.write_text(yaml.dump(config_data))

        # Second read (from cache)
        config2 = service.get_serena_config(use_cache=True)
        assert config2["enabled"] is True  # Still cached value

        # Third read (no cache)
        config3 = service.get_serena_config(use_cache=False)
        assert config3["enabled"] is False  # Updated value

    def test_cache_invalidation(self, tmp_path):
        """Test manual cache invalidation."""
        from src.giljo_mcp.services.config_service import ConfigService

        config_path = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"enabled": True}}}
        config_path.write_text(yaml.dump(config_data))

        service = ConfigService(config_path)

        # Read and cache
        config1 = service.get_serena_config()
        assert config1["enabled"] is True

        # Modify file
        config_data["features"]["serena_mcp"]["enabled"] = False
        config_path.write_text(yaml.dump(config_data))

        # Invalidate cache
        service.invalidate_cache()

        # Read again (should get fresh data)
        config2 = service.get_serena_config()
        assert config2["enabled"] is False

    def test_concurrent_reads_thread_safe(self, tmp_path):
        """Test thread safety of ConfigService."""
        import threading

        from src.giljo_mcp.services.config_service import ConfigService

        config_path = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"enabled": True}}}
        config_path.write_text(yaml.dump(config_data))

        service = ConfigService(config_path)
        results = []
        errors = []

        def read_config():
            try:
                config = service.get_serena_config(use_cache=False)
                results.append(config)
            except Exception as e:
                errors.append(e)

        # Spawn multiple threads
        threads = [threading.Thread(target=read_config) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All reads should succeed
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r["enabled"] is True for r in results)

    def test_config_file_not_found(self, tmp_path):
        """Test handling of missing config file."""
        from src.giljo_mcp.services.config_service import ConfigService

        config_path = tmp_path / "nonexistent.yaml"
        service = ConfigService(config_path)

        config = service.get_serena_config()

        # Should return empty dict, not crash
        assert config == {}

    def test_invalid_yaml_handling(self, tmp_path):
        """Test handling of invalid YAML."""
        from src.giljo_mcp.services.config_service import ConfigService

        config_path = tmp_path / "config.yaml"
        config_path.write_text("invalid: yaml: content: [[[")

        service = ConfigService(config_path)
        config = service.get_serena_config()

        # Should return empty dict, not crash
        assert config == {}


class TestTemplateManagerIntegration:
    """Tests for template manager with Serena."""

    def test_template_includes_serena_when_enabled(self, tmp_path):
        """Test Serena guidance appears in templates."""
        from src.giljo_mcp.services.config_service import ConfigService
        from src.giljo_mcp.template_manager import UnifiedTemplateManager

        # Create config with serena enabled
        config_path = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"enabled": True, "installed": True, "registered": True}}}
        config_path.write_text(yaml.dump(config_data))

        # Initialize services
        config_service = ConfigService(config_path)
        template_manager = UnifiedTemplateManager(config_service=config_service)

        # Get orchestrator template
        template = template_manager.get_role_template("orchestrator")

        # Verify SERENA MCP TOOLS section present
        assert "SERENA" in template or "serena" in template.lower()
        assert "mcp__serena" in template.lower()

    def test_template_excludes_serena_when_disabled(self, tmp_path):
        """Test no Serena guidance when disabled."""
        from src.giljo_mcp.services.config_service import ConfigService
        from src.giljo_mcp.template_manager import UnifiedTemplateManager

        # Create config with serena disabled
        config_path = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"enabled": False, "installed": False, "registered": False}}}
        config_path.write_text(yaml.dump(config_data))

        config_service = ConfigService(config_path)
        template_manager = UnifiedTemplateManager(config_service=config_service)

        template = template_manager.get_role_template("orchestrator")

        # Verify SERENA section NOT present
        assert "mcp__serena" not in template.lower()

    def test_all_roles_have_serena_guidance(self, tmp_path):
        """Test all 6 roles get appropriate Serena guidance."""
        from src.giljo_mcp.services.config_service import ConfigService
        from src.giljo_mcp.template_manager import UnifiedTemplateManager

        config_path = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"enabled": True, "installed": True, "registered": True}}}
        config_path.write_text(yaml.dump(config_data))

        config_service = ConfigService(config_path)
        template_manager = UnifiedTemplateManager(config_service=config_service)

        roles = ["orchestrator", "analyzer", "implementer", "tester", "reviewer", "documenter"]

        for role in roles:
            template = template_manager.get_role_template(role)
            # Each role should have Serena guidance when enabled
            assert "serena" in template.lower(), f"Role {role} missing Serena guidance"

    def test_cache_key_differentiates_serena_state(self, tmp_path):
        """Test templates cached separately for enabled/disabled."""
        from src.giljo_mcp.services.config_service import ConfigService
        from src.giljo_mcp.template_manager import UnifiedTemplateManager

        config_path = tmp_path / "config.yaml"

        # First: enabled
        config_data = {"features": {"serena_mcp": {"enabled": True}}}
        config_path.write_text(yaml.dump(config_data))

        config_service = ConfigService(config_path)
        template_manager = UnifiedTemplateManager(config_service=config_service)

        template_enabled = template_manager.get_role_template("orchestrator")

        # Change to disabled
        config_data["features"]["serena_mcp"]["enabled"] = False
        config_path.write_text(yaml.dump(config_data))

        # Invalidate config cache to pick up change
        config_service.invalidate_cache()

        # Get new template (should be different)
        template_manager_2 = UnifiedTemplateManager(config_service=config_service)
        template_disabled = template_manager_2.get_role_template("orchestrator")

        # Templates should differ based on Serena state
        assert template_enabled != template_disabled
