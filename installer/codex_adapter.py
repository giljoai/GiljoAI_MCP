# ============================================================================
# DEPRECATED: MCP registration moved to frontend setup wizard
# This file is no longer used and will be removed in future versions.
#
# All MCP registration is now handled by the frontend setup wizard at /setup.
# See: docs/IMPLEMENTATION_PLAN.md Phase 0
#
# Multi-tool support (Codex, Gemini) coming in 2026
# ============================================================================

#!/usr/bin/env python3
"""
GiljoAI MCP - Codex CLI Adapter

DEPRECATED: MCP registration moved to frontend setup wizard.
Use the web-based setup wizard at http://localhost:7274/setup
"""

import warnings
import toml
from pathlib import Path
from typing import Dict, List, Optional

from installer.mcp_adapter_base import MCPAdapterBase


# Issue deprecation warning when module is imported
warnings.warn(
    "CodexAdapter is deprecated. MCP registration is now handled by the "
    "frontend setup wizard at /setup. This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)


class CodexAdapter(MCPAdapterBase):
    """
    Adapter for Codex CLI MCP registration.

    DEPRECATED: Use the frontend setup wizard at /setup instead.
    """

    @staticmethod
    def get_cli_name() -> str:
        """Return the CLI command name."""
        return "codex"

    @staticmethod
    def get_config_path() -> Path:
        """Return platform-specific config file path."""
        return Path.home() / ".codex" / "config.toml"

    def register(self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> bool:
        """
        Register MCP server with Codex CLI.

        Codex CLI only supports file-based registration (no CLI commands).
        Uses TOML format with [mcp_servers.servername] section.

        Args:
            server_name: Name of the MCP server
            command: Command to execute (e.g., path to Python)
            args: Command arguments
            env: Optional environment variables

        Returns:
            bool: True if registration successful, False otherwise
        """
        try:
            config_path = self.get_config_path()

            # Ensure directory exists
            if not self.ensure_config_directory(config_path):
                return False

            # Read existing config or create new
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = toml.load(f)
            else:
                config = {}

            # Ensure mcp_servers section exists
            if "mcp_servers" not in config:
                config["mcp_servers"] = {}

            # Add or update server configuration
            # Note: Codex uses underscore notation (mcp_servers) not camelCase
            server_config = {"command": command, "args": args}
            if env:
                server_config["env"] = env

            config["mcp_servers"][server_name] = server_config

            # Write back to file
            with open(config_path, "w", encoding="utf-8") as f:
                toml.dump(config, f)

            print(f"Successfully registered {server_name} with Codex CLI")
            return True

        except Exception as e:
            print(f"Failed to register {server_name} with Codex CLI: {e}")
            return False

    def verify(self, server_name: str) -> bool:
        """
        Verify MCP server is registered.

        Codex CLI has no verification command, so we check the config file directly.

        Args:
            server_name: Name of the MCP server to verify

        Returns:
            bool: True if server is registered
        """
        try:
            config_path = self.get_config_path()

            if not config_path.exists():
                return False

            with open(config_path, "r", encoding="utf-8") as f:
                config = toml.load(f)

            return "mcp_servers" in config and server_name in config["mcp_servers"]

        except Exception:
            return False

    def unregister(self, server_name: str) -> bool:
        """
        Remove MCP server registration.

        Args:
            server_name: Name of the MCP server to unregister

        Returns:
            bool: True if unregistration successful
        """
        try:
            config_path = self.get_config_path()

            if not config_path.exists():
                return True

            with open(config_path, "r", encoding="utf-8") as f:
                config = toml.load(f)

            if "mcp_servers" in config and server_name in config["mcp_servers"]:
                del config["mcp_servers"][server_name]

                with open(config_path, "w", encoding="utf-8") as f:
                    toml.dump(config, f)

            return True

        except Exception as e:
            print(f"Unregistration error: {e}")
            return False
