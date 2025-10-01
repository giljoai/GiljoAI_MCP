# ============================================================================
# DISABLED: Multi-tool support temporarily disabled
# See docs/Techdebt.md and CLAUDE_CODE_EXCLUSIVITY_INVESTIGATION.md
# This module will be re-enabled when Gemini CLI gains subagent capabilities
# or when hybrid orchestrator is implemented (Q2 2025)
# ============================================================================

#!/usr/bin/env python3
"""
GiljoAI MCP - Gemini CLI Adapter
Handles MCP registration for Google Gemini CLI
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from installer.mcp_adapter_base import MCPAdapterBase


class GeminiAdapter(MCPAdapterBase):
    """Adapter for Gemini CLI MCP registration."""

    @staticmethod
    def get_cli_name() -> str:
        """Return the CLI command name."""
        return "gemini"

    @staticmethod
    def get_config_path() -> Path:
        """Return platform-specific config file path."""
        return Path.home() / ".gemini" / "settings.json"

    def register(self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> bool:
        """
        Register MCP server with Gemini CLI.

        First attempts to use `gemini mcp add` command.
        Falls back to direct file editing if command fails.

        Args:
            server_name: Name of the MCP server
            command: Command to execute (e.g., path to Python)
            args: Command arguments
            env: Optional environment variables

        Returns:
            bool: True if registration successful, False otherwise
        """
        # Try command-based registration first
        if self._register_via_command(server_name, command, args, env):
            print(f"Successfully registered {server_name} with Gemini CLI via command")
            return True

        # Fallback to file-based registration
        print("Command-based registration failed, falling back to file editing...")
        if self._register_via_file(server_name, command, args, env):
            print(f"Successfully registered {server_name} with Gemini CLI via file editing")
            return True

        print(f"Failed to register {server_name} with Gemini CLI")
        return False

    def _register_via_command(
        self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]]
    ) -> bool:
        """
        Register using `gemini mcp add` command.

        Args:
            server_name: Name of the MCP server
            command: Command to execute
            args: Command arguments
            env: Optional environment variables

        Returns:
            bool: True if successful
        """
        try:
            # Build command arguments for gemini mcp add
            # Format: gemini mcp add <name> --command <cmd> --args <args> [--env <env>]
            cmd_args = ["gemini", "mcp", "add", server_name, "--command", command]

            # Add args
            if args:
                cmd_args.extend(["--args", json.dumps(args)])

            # Add env if provided
            if env:
                cmd_args.extend(["--env", json.dumps(env)])

            # Run the command
            result = subprocess.run(cmd_args, capture_output=True, text=True, timeout=30)

            return result.returncode == 0

        except FileNotFoundError:
            print("Gemini CLI command not found")
            return False
        except subprocess.TimeoutExpired:
            print("Command timed out")
            return False
        except Exception as e:
            print(f"Command execution error: {e}")
            return False

    def _register_via_file(
        self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]]
    ) -> bool:
        """
        Register by directly editing ~/.gemini/settings.json.

        Args:
            server_name: Name of the MCP server
            command: Command to execute
            args: Command arguments
            env: Optional environment variables

        Returns:
            bool: True if successful
        """
        try:
            config_path = self.get_config_path()

            # Ensure directory exists
            if not self.ensure_config_directory(config_path):
                return False

            # Read existing config or create new
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = {}

            # Ensure mcpServers section exists
            if "mcpServers" not in config:
                config["mcpServers"] = {}

            # Add or update server configuration
            server_config = {"command": command, "args": args}
            if env:
                server_config["env"] = env

            config["mcpServers"][server_name] = server_config

            # Write back to file
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            return True

        except Exception as e:
            print(f"File editing error: {e}")
            return False

    def verify(self, server_name: str) -> bool:
        """
        Verify MCP server is registered.

        First attempts to use `gemini mcp list` command.
        Falls back to checking config file if command fails.

        Args:
            server_name: Name of the MCP server to verify

        Returns:
            bool: True if server is registered
        """
        # Try command-based verification first
        try:
            result = subprocess.run(["gemini", "mcp", "list"], capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and server_name in result.stdout:
                return True

        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass

        # Fallback to file-based verification
        try:
            config_path = self.get_config_path()

            if not config_path.exists():
                return False

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            return "mcpServers" in config and server_name in config["mcpServers"]

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
                config = json.load(f)

            if "mcpServers" in config and server_name in config["mcpServers"]:
                del config["mcpServers"][server_name]

                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)

            return True

        except Exception as e:
            print(f"Unregistration error: {e}")
            return False
