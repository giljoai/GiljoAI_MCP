#!/usr/bin/env python3
"""
GiljoAI MCP - Claude CLI Adapter
Handles MCP registration for Claude Code CLI
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from installer.mcp_adapter_base import MCPAdapterBase


class ClaudeAdapter(MCPAdapterBase):
    """Adapter for Claude Code CLI MCP registration."""

    @staticmethod
    def get_cli_name() -> str:
        """Return the CLI command name."""
        return "claude"

    @staticmethod
    def get_config_path() -> Path:
        """Return platform-specific config file path."""
        return Path.home() / ".claude.json"

    def register(self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> bool:
        """
        Register MCP server with Claude CLI.

        First attempts to use `claude mcp add-json` command.
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
            print(f"Successfully registered {server_name} with Claude CLI via command")
            return True

        # Fallback to file-based registration
        print("Command-based registration failed, falling back to file editing...")
        if self._register_via_file(server_name, command, args, env):
            print(f"Successfully registered {server_name} with Claude CLI via file editing")
            return True

        print(f"Failed to register {server_name} with Claude CLI")
        return False

    def _register_via_command(
        self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]]
    ) -> bool:
        """
        Register using `claude mcp add-json` command.

        Args:
            server_name: Name of the MCP server
            command: Command to execute
            args: Command arguments
            env: Optional environment variables

        Returns:
            bool: True if successful
        """
        try:
            # Build the JSON config
            config = {"command": command, "args": args}
            if env:
                config["env"] = env

            config_json = json.dumps(config)

            # Run the command
            result = subprocess.run(
                ["claude", "mcp", "add-json", server_name, config_json, "--scope", "user"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            return result.returncode == 0

        except FileNotFoundError:
            print("Claude CLI command not found")
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
        Register by directly editing ~/.claude.json.

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

        First attempts to use `claude mcp list` command.
        Falls back to checking config file if command fails.

        Args:
            server_name: Name of the MCP server to verify

        Returns:
            bool: True if server is registered
        """
        # Try command-based verification first
        try:
            result = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True, timeout=30)

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
