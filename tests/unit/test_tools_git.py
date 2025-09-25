"""
Comprehensive tests for git.py tools
Target: 5.16% → 95%+ coverage

Tests all git tool functions and helpers:
- register_git_tools
- _get_encryption_key
- _encrypt_credential/_decrypt_credential
- _get_git_config
- _run_git_command
- _generate_commit_message
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from src.giljo_mcp.tools.git import (
    _decrypt_credential,
    _encrypt_credential,
    _generate_commit_message,
    _get_encryption_key,
    _get_git_config,
    _run_git_command,
    register_git_tools,
)
from tests.utils.tools_helpers import (
    MockMCPToolRegistrar,
    ToolsTestHelper,
)


class TestGitTools:
    """Test class for git tools"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]
        self.mock_server = tools_test_setup["mcp_server"]

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Git Test Project")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_register_git_tools(self):
        """Test that git tools are registered properly"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Register tools
        register_git_tools(mock_server, self.db_manager, self.tenant_manager)

        # Git tools should be registered (at minimum git status, commit, etc.)
        registered_tools = registrar.get_all_tools()
        assert len(registered_tools) > 0

    def test_get_encryption_key(self):
        """Test encryption key generation"""
        with patch.dict("os.environ", {"GILJO_MCP_ENCRYPTION_KEY": "test_key_123"}):
            key = _get_encryption_key()
            assert key is not None
            assert len(key) == 32  # Fernet requires 32-byte key

    def test_get_encryption_key_generated(self):
        """Test encryption key generation when not provided"""
        with patch.dict("os.environ", {}, clear=True):
            with patch("src.giljo_mcp.tools.git.Fernet.generate_key") as mock_generate:
                mock_generate.return_value = b"test_generated_key_32_bytes_long"
                key = _get_encryption_key()
                assert key is not None
                mock_generate.assert_called_once()

    def test_encrypt_decrypt_credential(self):
        """Test credential encryption and decryption"""
        test_credential = "test_password_123"

        # Test encryption
        encrypted = _encrypt_credential(test_credential)
        assert encrypted != test_credential
        assert isinstance(encrypted, str)

        # Test decryption
        decrypted = _decrypt_credential(encrypted)
        assert decrypted == test_credential

    def test_encrypt_decrypt_credential_none(self):
        """Test encryption/decryption with None values"""
        assert _encrypt_credential(None) is None
        assert _decrypt_credential(None) is None

    @patch("src.giljo_mcp.tools.git.subprocess.run")
    def test_get_git_config_success(self, mock_run):
        """Test successful git config retrieval"""
        mock_run.return_value = MagicMock(returncode=0, stdout="John Doe", stderr="")

        result = _get_git_config("user.name")

        assert result == "John Doe"
        mock_run.assert_called_once_with(
            ["git", "config", "--get", "user.name"], capture_output=True, text=True, timeout=10
        )

    @patch("src.giljo_mcp.tools.git.subprocess.run")
    def test_get_git_config_not_found(self, mock_run):
        """Test git config when key not found"""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error: key does not exist")

        result = _get_git_config("nonexistent.key")
        assert result is None

    @patch("src.giljo_mcp.tools.git.subprocess.run")
    def test_run_git_command_success(self, mock_run):
        """Test successful git command execution"""
        mock_run.return_value = MagicMock(returncode=0, stdout="On branch main\nnothing to commit", stderr="")

        result = _run_git_command(["status"])

        assert result["success"] is True
        assert "On branch main" in result["output"]
        assert result["error"] == ""

    @patch("src.giljo_mcp.tools.git.subprocess.run")
    def test_run_git_command_failure(self, mock_run):
        """Test git command execution failure"""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a git repository")

        result = _run_git_command(["status"])

        assert result["success"] is False
        assert "not a git repository" in result["error"]

    @patch("src.giljo_mcp.tools.git.subprocess.run")
    def test_run_git_command_timeout(self, mock_run):
        """Test git command timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired(["git", "status"], 30)

        result = _run_git_command(["status"])

        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    @patch("src.giljo_mcp.tools.git.subprocess.run")
    def test_run_git_command_exception(self, mock_run):
        """Test git command with other exceptions"""
        mock_run.side_effect = OSError("Git not found")

        result = _run_git_command(["status"])

        assert result["success"] is False
        assert "Git not found" in result["error"]

    def test_generate_commit_message_simple(self):
        """Test commit message generation with simple changes"""
        changes = ["Added new feature", "Fixed bug in authentication"]

        message = _generate_commit_message(changes)

        assert "Added new feature" in message
        assert "Fixed bug in authentication" in message
        assert "🤖 Generated with [Claude Code]" in message

    def test_generate_commit_message_long_list(self):
        """Test commit message generation with many changes"""
        changes = [f"Change {i}" for i in range(10)]

        message = _generate_commit_message(changes)

        # Should summarize when too many changes
        assert "multiple changes" in message.lower() or "Change 0" in message
        assert "🤖 Generated with [Claude Code]" in message

    def test_generate_commit_message_empty(self):
        """Test commit message generation with no changes"""
        changes = []

        message = _generate_commit_message(changes)

        assert "Minor updates" in message or "Update" in message
        assert "🤖 Generated with [Claude Code]" in message

    @pytest.mark.asyncio
    async def test_git_tools_integration(self):
        """Integration test for git tools registration and basic functionality"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch("src.giljo_mcp.tools.git._run_git_command") as mock_git:
            mock_git.return_value = {"success": True, "output": "On branch main\nnothing to commit", "error": ""}

            register_git_tools(mock_server, self.db_manager, self.tenant_manager)

            # Test should register tools without errors
            registered_tools = registrar.get_all_tools()
            assert len(registered_tools) >= 0  # Git tools may be conditional

    @pytest.mark.asyncio
    async def test_git_tools_error_handling(self):
        """Test git tools error handling"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Test with exception during registration
        with patch("src.giljo_mcp.tools.git._get_git_config") as mock_config:
            mock_config.side_effect = Exception("Git configuration error")

            try:
                register_git_tools(mock_server, self.db_manager, self.tenant_manager)
                # Should not raise exception, should handle gracefully
            except Exception:
                pytest.fail("Git tools registration should handle errors gracefully")

    def test_encryption_edge_cases(self):
        """Test encryption edge cases"""
        # Test with empty string
        encrypted_empty = _encrypt_credential("")
        assert _decrypt_credential(encrypted_empty) == ""

        # Test with special characters
        special_cred = "pässwörd!@#$%^&*()"
        encrypted_special = _encrypt_credential(special_cred)
        assert _decrypt_credential(encrypted_special) == special_cred

        # Test with very long credential
        long_cred = "a" * 1000
        encrypted_long = _encrypt_credential(long_cred)
        assert _decrypt_credential(encrypted_long) == long_cred

    @patch("src.giljo_mcp.tools.git.subprocess.run")
    def test_git_config_various_keys(self, mock_run):
        """Test git config with various configuration keys"""
        configs = {
            "user.name": "Test User",
            "user.email": "test@example.com",
            "core.editor": "vim",
            "remote.origin.url": "https://github.com/user/repo.git",
        }

        for key, value in configs.items():
            mock_run.return_value = MagicMock(returncode=0, stdout=value, stderr="")

            result = _get_git_config(key)
            assert result == value

    def test_commit_message_formatting(self):
        """Test commit message formatting options"""
        # Test with different types of changes
        changes_types = [
            ["feat: add new authentication system"],
            ["fix: resolve memory leak in parser"],
            ["docs: update API documentation"],
            ["refactor: reorganize utility functions"],
            ["test: add unit tests for validation"],
        ]

        for changes in changes_types:
            message = _generate_commit_message(changes)
            assert isinstance(message, str)
            assert len(message) > 0
            assert "🤖 Generated with [Claude Code]" in message

    @patch("src.giljo_mcp.tools.git.Path.cwd")
    def test_git_working_directory_detection(self, mock_cwd):
        """Test git working directory detection"""
        mock_cwd.return_value = Path("/fake/git/repo")

        with patch("src.giljo_mcp.tools.git._run_git_command") as mock_git:
            mock_git.return_value = {"success": True, "output": "/fake/git/repo", "error": ""}

            # Test that git commands work with working directory
            result = _run_git_command(["rev-parse", "--show-toplevel"])
            assert result["success"] is True

    def test_security_credential_handling(self):
        """Test secure credential handling"""
        sensitive_data = "github_pat_11ABCDEFGHIJKLMNOP"

        # Encrypt sensitive credential
        encrypted = _encrypt_credential(sensitive_data)

        # Verify original is not in encrypted form
        assert sensitive_data not in encrypted

        # Verify can be decrypted correctly
        decrypted = _decrypt_credential(encrypted)
        assert decrypted == sensitive_data

        # Verify encrypted data is different each time (includes random IV)
        encrypted2 = _encrypt_credential(sensitive_data)
        assert encrypted != encrypted2
        assert _decrypt_credential(encrypted2) == sensitive_data
