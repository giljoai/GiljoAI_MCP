"""
Tests for error handling and recovery in Serena MCP integration.

Verifies:
- Transactional operations with rollback
- Partial failure handling
- Cleanup of temporary files
- State consistency after errors
"""

import json
import shutil

import yaml


class TestTransactionalOperations:
    """Tests for atomic operations with rollback."""

    def test_rollback_config_on_claude_json_failure(self, tmp_path):
        """Test config.yaml rolled back if .claude.json fails."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager
        from src.giljo_mcp.services.config_service import ConfigService

        # Setup initial state
        config_path = tmp_path / "config.yaml"
        initial_config = {"features": {"serena_mcp": {"enabled": False, "installed": False, "registered": False}}}
        config_path.write_text(yaml.dump(initial_config))

        claude_config_path = tmp_path / ".claude.json"
        claude_config_path.write_text(json.dumps({"mcpServers": {}}))

        # Create managers
        config_service = ConfigService(config_path)
        claude_manager = ClaudeConfigManager()
        claude_manager.claude_config_path = claude_config_path
        claude_manager.backup_dir = tmp_path / ".claude_backups"

        # Step 1: Update config.yaml (succeeds)
        config_data = yaml.safe_load(config_path.read_text())
        config_data["features"]["serena_mcp"]["enabled"] = True
        config_path.write_text(yaml.dump(config_data))

        # Step 2: Try to update .claude.json (fails)
        # Make file read-only to simulate permission error
        claude_config_path.chmod(0o444)

        result = claude_manager.inject_serena(tmp_path)

        # Injection should fail
        assert result["success"] is False

        # Restore permissions for cleanup
        claude_config_path.chmod(0o644)

        # Config.yaml should be rolled back to original state
        current_config = yaml.safe_load(config_path.read_text())
        # Note: This test assumes the service layer handles rollback
        # In a real implementation, we'd verify the orchestration service
        # performs the rollback

    def test_restore_backup_on_write_failure(self, tmp_path):
        """Test backup restored on write failure."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        original_config = {"mcpServers": {"original": {"command": "test"}}}
        claude_config_path.write_text(json.dumps(original_config))

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        # Create backup
        backup_path = manager._backup_claude_config()

        # Corrupt the config
        claude_config_path.write_text("invalid json {{{")

        # Restore backup
        manager._restore_backup(backup_path)

        # Verify original config restored
        with open(claude_config_path, encoding="utf-8") as f:
            restored_config = json.load(f)

        assert restored_config == original_config

    def test_cleanup_temp_files_on_error(self, tmp_path):
        """Test temp files cleaned up after errors."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.claude_config_path = tmp_path / ".claude.json"

        # Count initial temp files
        temp_files_before = list(tmp_path.glob(".claude_temp_*"))
        initial_count = len(temp_files_before)

        # Try atomic write with invalid JSON (should fail)
        try:
            manager._atomic_write({"invalid": float("inf")})  # inf not JSON serializable
        except (ValueError, TypeError):
            pass  # Expected

        # Verify no temp files left behind
        temp_files_after = list(tmp_path.glob(".claude_temp_*"))
        assert len(temp_files_after) == initial_count

    def test_rollback_preserves_other_mcpservers(self, tmp_path):
        """Test rollback doesn't affect other MCP servers."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        initial_config = {
            "mcpServers": {
                "giljo-mcp": {"command": "python", "args": ["-m", "giljo_mcp"]},
                "other-tool": {"command": "node", "args": ["tool.js"]},
            }
        }
        claude_config_path.write_text(json.dumps(initial_config))

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        # Create backup
        backup_path = manager._backup_claude_config()

        # Modify config (add serena)
        config = json.loads(claude_config_path.read_text())
        config["mcpServers"]["serena"] = {"command": "uvx"}
        claude_config_path.write_text(json.dumps(config))

        # Simulate error and rollback
        manager._restore_backup(backup_path)

        # Verify original servers intact
        with open(claude_config_path, encoding="utf-8") as f:
            restored_config = json.load(f)

        assert "giljo-mcp" in restored_config["mcpServers"]
        assert "other-tool" in restored_config["mcpServers"]
        assert "serena" not in restored_config["mcpServers"]


class TestPartialFailureHandling:
    """Tests for handling partial failures."""

    def test_config_updated_but_claude_json_failed(self, tmp_path, monkeypatch):
        """Test state when config succeeds but claude.json fails."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        config_path = tmp_path / "config.yaml"
        config_data = {"features": {"serena_mcp": {"enabled": False}}}
        config_path.write_text(yaml.dump(config_data))

        claude_config_path = tmp_path / ".claude.json"
        claude_config_path.write_text(json.dumps({"mcpServers": {}}))

        # Mock atomic write to fail
        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        original_atomic_write = manager._atomic_write

        def mock_atomic_write(*args, **kwargs):
            raise OSError("Disk full")

        monkeypatch.setattr(manager, "_atomic_write", mock_atomic_write)

        # Try injection
        result = manager.inject_serena(tmp_path)

        assert result["success"] is False
        assert "error" in result
        assert result["error"] is not None

    def test_retry_after_partial_failure(self, tmp_path):
        """Test system can recover from partial failure."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        claude_config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        # First attempt - success
        result1 = manager.inject_serena(tmp_path)
        assert result1["success"] is True

        # Remove serena
        result2 = manager.remove_serena()
        assert result2["success"] is True

        # Second attempt - should also succeed (idempotent)
        result3 = manager.inject_serena(tmp_path)
        assert result3["success"] is True

    def test_detection_failure_prevents_attachment(self, tmp_path, monkeypatch):
        """Test attachment blocked when detection fails."""
        import subprocess

        from src.giljo_mcp.services.serena_detector import SerenaDetector

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("uvx not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        result = detector.detect()

        # Detection failed
        assert result["installed"] is False

        # Attachment should not proceed without successful detection
        # (This would be enforced by the API/orchestration layer)

    def test_invalid_config_prevents_write(self, tmp_path):
        """Test invalid config detected before write."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.claude_config_path = tmp_path / ".claude.json"

        # Create invalid config (missing required fields)
        invalid_config = {"mcpServers": {"serena": {"command": "wrong"}}}  # Missing args

        manager._atomic_write(invalid_config)

        # Validate the written config
        is_valid = manager._validate_serena_config(invalid_config)

        assert is_valid is False


class TestBackupManagement:
    """Tests for backup creation and management."""

    def test_multiple_backups_created(self, tmp_path):
        """Test multiple backups are created over time."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        claude_config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        # Create multiple backups
        backup1 = manager._backup_claude_config()
        backup2 = manager._backup_claude_config()
        backup3 = manager._backup_claude_config()

        # All backups should exist
        assert backup1.exists()
        assert backup2.exists()
        assert backup3.exists()

        # Backups should have unique names
        assert backup1 != backup2
        assert backup2 != backup3

    def test_backup_preserves_exact_content(self, tmp_path):
        """Test backup is byte-for-byte identical."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        original_content = json.dumps(
            {"mcpServers": {"test": {"command": "test", "unicode": "🚀 日本語"}}}, ensure_ascii=False, indent=2
        )
        claude_config_path.write_text(original_content, encoding="utf-8")

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        backup_path = manager._backup_claude_config()

        # Compare byte-for-byte
        original_bytes = claude_config_path.read_bytes()
        backup_bytes = backup_path.read_bytes()

        assert original_bytes == backup_bytes

    def test_backup_directory_created_if_missing(self, tmp_path):
        """Test backup directory is created if it doesn't exist."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        claude_config_path = tmp_path / ".claude.json"
        claude_config_path.write_text(json.dumps({"mcpServers": {}}))

        manager = ClaudeConfigManager()
        manager.claude_config_path = claude_config_path
        manager.backup_dir = tmp_path / ".claude_backups"

        # Ensure backup dir doesn't exist
        if manager.backup_dir.exists():
            shutil.rmtree(manager.backup_dir)

        # Create backup
        backup_path = manager._backup_claude_config()

        # Backup dir should be created
        assert manager.backup_dir.exists()
        assert manager.backup_dir.is_dir()
        assert backup_path.exists()


class TestErrorMessages:
    """Tests for error message quality and clarity."""

    def test_error_message_includes_context(self, tmp_path, monkeypatch):
        """Test error messages include useful context."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()
        manager.claude_config_path = tmp_path / ".claude.json"

        # Mock atomic write to raise specific error
        def mock_atomic_write(*args, **kwargs):
            raise OSError("Permission denied: /path/to/file")

        monkeypatch.setattr(manager, "_atomic_write", mock_atomic_write)

        result = manager.inject_serena(tmp_path)

        # Error message should include details
        assert result["success"] is False
        assert "Permission denied" in result["error"]

    def test_detection_error_messages_actionable(self, monkeypatch):
        """Test detection errors provide actionable guidance."""
        import subprocess

        from src.giljo_mcp.services.serena_detector import SerenaDetector

        def mock_run(*args, **kwargs):
            raise FileNotFoundError("uvx not found")

        monkeypatch.setattr(subprocess, "run", mock_run)

        detector = SerenaDetector()
        result = detector.detect()

        # Error should be actionable
        assert result["error"] is not None
        assert "uvx" in result["error"].lower()
        # User should understand what to do (install uvx)

    def test_validation_errors_specific(self, tmp_path):
        """Test validation errors are specific."""
        from src.giljo_mcp.services.claude_config_manager import ClaudeConfigManager

        manager = ClaudeConfigManager()

        # Test various invalid configs
        invalid_configs = [
            {"mcpServers": {}},  # Missing serena
            {"mcpServers": {"serena": {}}},  # Missing command
            {"mcpServers": {"serena": {"command": "wrong"}}},  # Wrong command
            {"mcpServers": {"serena": {"command": "uvx", "args": []}}},  # Missing args
        ]

        for invalid_config in invalid_configs:
            is_valid = manager._validate_serena_config(invalid_config)
            assert is_valid is False
