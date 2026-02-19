"""
Test suite for MCP installer script templates
Phase 2: v3.0 Consolidation - MCP Tool Integration Scripts

Tests validate that installer templates:
- Contain all required placeholders
- Have valid shell/batch syntax
- Include proper error handling
- Create backups before modifications
- Merge JSON configurations safely
"""

from pathlib import Path

import pytest


class TestMCPTemplateStructure:
    """Test MCP installer template file structure and existence"""

    def test_windows_template_exists(self):
        """Test that Windows template file exists"""
        template_path = Path("installer/templates/giljo-mcp-setup.bat.template")
        assert template_path.exists(), f"Windows template should exist at {template_path}"

    def test_unix_template_exists(self):
        """Test that Unix template file exists"""
        template_path = Path("installer/templates/giljo-mcp-setup.sh.template")
        assert template_path.exists(), f"Unix template should exist at {template_path}"


class TestWindowsTemplatePlaceholders:
    """Test Windows template contains all required placeholders"""

    @pytest.fixture
    def windows_template(self):
        """Load Windows template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.bat.template")
        return template_path.read_text(encoding="utf-8")

    def test_server_url_placeholder(self, windows_template):
        """Test template contains {server_url} placeholder"""
        assert "{server_url}" in windows_template, "Template must contain {server_url} placeholder"

    def test_api_key_placeholder(self, windows_template):
        """Test template contains {api_key} placeholder"""
        assert "{api_key}" in windows_template, "Template must contain {api_key} placeholder"

    def test_username_placeholder(self, windows_template):
        """Test template contains {username} placeholder"""
        assert "{username}" in windows_template, "Template must contain {username} placeholder"

    def test_organization_placeholder(self, windows_template):
        """Test template contains {organization} placeholder"""
        assert "{organization}" in windows_template, "Template must contain {organization} placeholder"

    def test_timestamp_placeholder(self, windows_template):
        """Test template contains {timestamp} placeholder"""
        assert "{timestamp}" in windows_template, "Template must contain {timestamp} placeholder"


class TestUnixTemplatePlaceholders:
    """Test Unix template contains all required placeholders"""

    @pytest.fixture
    def unix_template(self):
        """Load Unix template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.sh.template")
        return template_path.read_text(encoding="utf-8")

    def test_server_url_placeholder(self, unix_template):
        """Test template contains {server_url} placeholder"""
        assert "{server_url}" in unix_template, "Template must contain {server_url} placeholder"

    def test_api_key_placeholder(self, unix_template):
        """Test template contains {api_key} placeholder"""
        assert "{api_key}" in unix_template, "Template must contain {api_key} placeholder"

    def test_username_placeholder(self, unix_template):
        """Test template contains {username} placeholder"""
        assert "{username}" in unix_template, "Template must contain {username} placeholder"

    def test_organization_placeholder(self, unix_template):
        """Test template contains {organization} placeholder"""
        assert "{organization}" in unix_template, "Template must contain {organization} placeholder"

    def test_timestamp_placeholder(self, unix_template):
        """Test template contains {timestamp} placeholder"""
        assert "{timestamp}" in unix_template, "Template must contain {timestamp} placeholder"


class TestWindowsTemplateSyntax:
    """Test Windows batch script syntax and structure"""

    @pytest.fixture
    def windows_template(self):
        """Load Windows template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.bat.template")
        return template_path.read_text(encoding="utf-8")

    def test_batch_file_header(self, windows_template):
        """Test template starts with proper batch file header"""
        assert windows_template.startswith("@echo off"), "Batch file must start with '@echo off'"

    def test_claude_code_detection(self, windows_template):
        """Test template detects Claude Code config"""
        assert "%APPDATA%\\.claude.json" in windows_template, "Must detect Claude Code at %APPDATA%\\.claude.json"

    def test_windsurf_detection(self, windows_template):
        """Test template detects Windsurf config"""
        assert "Windsurf" in windows_template, "Must detect Windsurf"

    def test_backup_creation(self, windows_template):
        """Test template creates backups before modifying configs"""
        assert "backup" in windows_template.lower(), "Must create backup before modifying config"

    def test_powershell_json_merging(self, windows_template):
        """Test template uses PowerShell for JSON manipulation"""
        assert "powershell" in windows_template.lower(), "Must use PowerShell for JSON operations"
        assert "ConvertFrom-Json" in windows_template, "Must parse JSON with ConvertFrom-Json"
        assert "ConvertTo-Json" in windows_template, "Must serialize JSON with ConvertTo-Json"

    def test_error_handling(self, windows_template):
        """Test template includes error handling"""
        assert "errorlevel" in windows_template.lower() or "if %errorlevel%" in windows_template.lower(), (
            "Must check for errors with errorlevel"
        )

    def test_user_instructions(self, windows_template):
        """Test template provides user instructions"""
        assert "restart" in windows_template.lower(), "Must instruct user to restart tools"
        assert "pause" in windows_template.lower() or "press any key" in windows_template.lower(), (
            "Must pause for user to read output"
        )


class TestUnixTemplateSyntax:
    """Test Unix shell script syntax and structure"""

    @pytest.fixture
    def unix_template(self):
        """Load Unix template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.sh.template")
        return template_path.read_text(encoding="utf-8")

    def test_shebang(self, unix_template):
        """Test template starts with proper shebang"""
        assert unix_template.startswith("#!/bin/bash") or unix_template.startswith("#!/usr/bin/env bash"), (
            "Shell script must start with proper shebang"
        )

    def test_claude_code_detection(self, unix_template):
        """Test template detects Claude Code config"""
        assert "~/.claude.json" in unix_template or "$HOME/.claude.json" in unix_template, (
            "Must detect Claude Code at ~/.claude.json"
        )

    def test_windsurf_detection(self, unix_template):
        """Test template detects Windsurf config"""
        assert "Windsurf" in unix_template, "Must detect Windsurf"

    def test_backup_creation(self, unix_template):
        """Test template creates timestamped backups"""
        assert "backup" in unix_template.lower(), "Must create backup before modifying config"
        # Should use date command for timestamp
        assert "date" in unix_template.lower() or "$(date" in unix_template, (
            "Should use date command for backup timestamp"
        )

    def test_jq_json_merging(self, unix_template):
        """Test template uses jq for JSON manipulation"""
        assert "jq" in unix_template.lower(), "Must use jq for JSON operations"

    def test_dependency_checking(self, unix_template):
        """Test template checks for required dependencies"""
        # Should check if jq is installed
        assert "command -v jq" in unix_template or "which jq" in unix_template or "type jq" in unix_template, (
            "Must check if jq is available"
        )

    def test_error_handling(self, unix_template):
        """Test template includes error handling"""
        assert "$?" in unix_template or "set -e" in unix_template, "Must check command exit codes for error handling"

    def test_color_output(self, unix_template):
        """Test template uses color output for better UX"""
        # Common color codes or tput usage
        has_colors = any(
            [
                "\\033[" in unix_template,  # ANSI color codes
                "\\e[" in unix_template,  # Alternative ANSI codes
                "tput" in unix_template,  # tput color commands
            ]
        )
        assert has_colors, "Should use color output for better user experience"


class TestMCPServerConfiguration:
    """Test that templates generate correct MCP server configuration"""

    @pytest.fixture
    def windows_template(self):
        """Load Windows template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.bat.template")
        return template_path.read_text(encoding="utf-8")

    @pytest.fixture
    def unix_template(self):
        """Load Unix template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.sh.template")
        return template_path.read_text(encoding="utf-8")

    def test_windows_mcp_server_name(self, windows_template):
        """Test Windows template uses correct MCP server name"""
        assert "giljo-mcp" in windows_template, "MCP server must be named 'giljo-mcp'"

    def test_unix_mcp_server_name(self, unix_template):
        """Test Unix template uses correct MCP server name"""
        assert "giljo-mcp" in unix_template, "MCP server must be named 'giljo-mcp'"

    def test_windows_python_command(self, windows_template):
        """Test Windows template uses Python module execution"""
        assert "python" in windows_template.lower(), "Must use python command"
        assert "-m" in windows_template, "Must use python -m module execution"
        assert "giljo_mcp" in windows_template, "Must reference giljo_mcp module"

    def test_unix_python_command(self, unix_template):
        """Test Unix template uses Python module execution"""
        assert "python" in unix_template.lower(), "Must use python command"
        assert "-m" in unix_template, "Must use python -m module execution"
        assert "giljo_mcp" in unix_template, "Must reference giljo_mcp module"

    def test_windows_environment_variables(self, windows_template):
        """Test Windows template sets required environment variables"""
        assert "GILJO_SERVER_URL" in windows_template, "Must set GILJO_SERVER_URL env var"
        assert "GILJO_API_KEY" in windows_template, "Must set GILJO_API_KEY env var"

    def test_unix_environment_variables(self, unix_template):
        """Test Unix template sets required environment variables"""
        assert "GILJO_SERVER_URL" in unix_template, "Must set GILJO_SERVER_URL env var"
        assert "GILJO_API_KEY" in unix_template, "Must set GILJO_API_KEY env var"


class TestTemplateSafetyFeatures:
    """Test templates include proper safety features"""

    @pytest.fixture
    def windows_template(self):
        """Load Windows template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.bat.template")
        return template_path.read_text(encoding="utf-8")

    @pytest.fixture
    def unix_template(self):
        """Load Unix template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.sh.template")
        return template_path.read_text(encoding="utf-8")

    def test_windows_backup_before_modify(self, windows_template):
        """Test Windows template creates backup before modifying"""
        # Should use 'copy' before any PowerShell ConvertFrom-Json
        assert "copy" in windows_template.lower() or "xcopy" in windows_template.lower(), (
            "Must create backup with copy command"
        )

    def test_unix_backup_before_modify(self, unix_template):
        """Test Unix template creates backup before modifying"""
        # Should use 'cp' before any jq operations
        assert "cp " in unix_template, "Must create backup with cp command"

    def test_windows_preserves_existing_config(self, windows_template):
        """Test Windows template merges rather than replaces config"""
        # Should load existing config, then merge
        assert "ConvertFrom-Json" in windows_template, "Must load existing config"
        # Should use safe write methods (Set-Content or WriteAllText)
        assert "Set-Content" in windows_template or "WriteAllText" in windows_template, (
            "Must use Set-Content or WriteAllText for controlled writes"
        )

    def test_unix_preserves_existing_config(self, unix_template):
        """Test Unix template merges rather than replaces config"""
        # Should use jq to merge configs
        assert "jq" in unix_template.lower(), "Must use jq for safe merging"


class TestTemplateUserExperience:
    """Test templates provide good user experience"""

    @pytest.fixture
    def windows_template(self):
        """Load Windows template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.bat.template")
        return template_path.read_text(encoding="utf-8")

    @pytest.fixture
    def unix_template(self):
        """Load Unix template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.sh.template")
        return template_path.read_text(encoding="utf-8")

    def test_windows_summary_output(self, windows_template):
        """Test Windows template shows configuration summary"""
        assert "Configuration Complete" in windows_template or "summary" in windows_template.lower(), (
            "Must show configuration summary"
        )

    def test_unix_summary_output(self, unix_template):
        """Test Unix template shows configuration summary"""
        assert "Configuration Complete" in unix_template or "summary" in unix_template.lower(), (
            "Must show configuration summary"
        )

    def test_windows_clear_status_messages(self, windows_template):
        """Test Windows template shows clear status messages"""
        assert "[FOUND]" in windows_template or "[OK]" in windows_template, "Must show clear status indicators"
        assert "[SKIP]" in windows_template or "[ERROR]" in windows_template, "Must show skip/error indicators"

    def test_unix_clear_status_messages(self, unix_template):
        """Test Unix template shows clear status messages"""
        assert "[FOUND]" in unix_template or "[OK]" in unix_template, "Must show clear status indicators"
        assert "[SKIP]" in unix_template or "[ERROR]" in unix_template, "Must show skip/error indicators"

    def test_windows_restart_instructions(self, windows_template):
        """Test Windows template instructs user to restart tools"""
        assert "restart" in windows_template.lower(), "Must instruct user to restart development tools"

    def test_unix_restart_instructions(self, unix_template):
        """Test Unix template instructs user to restart tools"""
        assert "restart" in unix_template.lower(), "Must instruct user to restart development tools"


class TestTemplateCrossPlatformSupport:
    """Test templates properly handle cross-platform concerns"""

    @pytest.fixture
    def unix_template(self):
        """Load Unix template content"""
        template_path = Path("installer/templates/giljo-mcp-setup.sh.template")
        return template_path.read_text(encoding="utf-8")

    def test_unix_handles_macos_paths(self, unix_template):
        """Test Unix template handles macOS-specific paths"""
        # macOS uses ~/Library/Application Support
        assert "Library/Application Support" in unix_template or "uname" in unix_template, (
            "Must handle macOS-specific paths or detect OS"
        )

    def test_unix_handles_linux_paths(self, unix_template):
        """Test Unix template handles Linux-specific paths"""
        # Linux uses ~/.config
        assert ".config" in unix_template or "uname" in unix_template, "Must handle Linux-specific paths or detect OS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
