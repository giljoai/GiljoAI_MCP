#!/usr/bin/env python3
"""
GiljoAI MCP - Universal MCP Installer
Universal MCP server installer for multiple AI CLI tools

IMPORTANT: Multi-tool support temporarily disabled for Claude Code exclusivity.
See CLAUDE_CODE_EXCLUSIVITY_INVESTIGATION.md and docs/Techdebt.md for details.
"""

from typing import Dict, List, Optional
from pathlib import Path

from installer.claude_adapter import ClaudeAdapter
# TECHDEBT: Multi-tool support disabled - see docs/Techdebt.md and CLAUDE_CODE_EXCLUSIVITY_INVESTIGATION.md
# from installer.codex_adapter import CodexAdapter
# TECHDEBT: Multi-tool support disabled - see docs/Techdebt.md and CLAUDE_CODE_EXCLUSIVITY_INVESTIGATION.md
# from installer.gemini_adapter import GeminiAdapter

# Feature flag for multi-tool support - set to True to re-enable Codex/Gemini
ENABLE_MULTI_TOOL_SUPPORT = False

class UniversalMCPInstaller:
    """Universal MCP server installer for multiple AI CLI tools."""

    def __init__(self):
        """Initialize the universal installer with adapters for supported AI CLI tools."""
        self.adapters = {
            "claude": ClaudeAdapter(),
        }

        self.tool_names = {
            "claude": "Claude Code",
        }

        if ENABLE_MULTI_TOOL_SUPPORT:
            # TECHDEBT: Multi-tool support disabled - Claude Code exclusivity
            # See CLAUDE_CODE_EXCLUSIVITY_INVESTIGATION.md for details
            # Uncomment to re-enable:
            # from installer.codex_adapter import CodexAdapter
            # from installer.gemini_adapter import GeminiAdapter
            # self.adapters["codex"] = CodexAdapter()
            # self.adapters["gemini"] = GeminiAdapter()
            # self.tool_names["codex"] = "Codex CLI (OpenAI)"
            # self.tool_names["gemini"] = "Gemini CLI (Google)"
            pass
    def detect_installed_tools(self) -> List[str]:
        """
        Detect which AI CLI tools are installed.

        Returns:
            list: List of installed tool names
        """
        installed = []
        for name, adapter in self.adapters.items():
            if adapter.is_installed():
                installed.append(name)
        return installed

    def get_tool_status(self) -> Dict[str, bool]:
        """
        Get installation status for all tools.

        Returns:
            dict: Mapping of tool name to installation status
        """
        status = {}
        for name, adapter in self.adapters.items():
            status[name] = adapter.is_installed()
        return status

    def register_all(
        self,
        server_name: Optional[str] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, bool]:
        """
        Register MCP server with all detected tools.

        Args:
            server_name: Name of the MCP server (default: 'giljo-mcp')
            command: Command to execute (default: auto-detected Python path)
            args: Command arguments (default: ['-m', 'giljo_mcp.mcp_adapter'])
            env: Environment variables (default: auto-detected)

        Returns:
            dict: Mapping of tool name to success status
        """
        results = {}
        installed = self.detect_installed_tools()

        if not installed:
            print("No AI CLI tools detected")
            return results

        for tool_name in installed:
            adapter = self.adapters[tool_name]

            # Use defaults if not provided
            if server_name is None:
                server_name = "giljo-mcp"

            if command is None or args is None:
                cmd, arg_list = adapter.get_default_command_args()
            else:
                cmd, arg_list = command, args

            if env is None:
                environment = adapter.get_default_env()
            else:
                environment = env

            try:
                print(f"\nRegistering with {self.tool_names[tool_name]}...")
                success = adapter.register(server_name, cmd, arg_list, environment)
                results[tool_name] = success

                if success:
                    print(f"  Successfully registered with {self.tool_names[tool_name]}")
                else:
                    print(f"  Failed to register with {self.tool_names[tool_name]}")

            except Exception as e:
                print(f"  Error registering with {self.tool_names[tool_name]}: {e}")
                results[tool_name] = False

        return results

    def register_single(
        self,
        tool_name: str,
        server_name: Optional[str] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Register MCP server with a specific tool.

        Args:
            tool_name: Name of the tool ('claude')
            server_name: Name of the MCP server (default: 'giljo-mcp')
            command: Command to execute (default: auto-detected)
            args: Command arguments (default: auto-detected)
            env: Environment variables (default: auto-detected)

        Returns:
            bool: True if successful, False otherwise
        """
        if tool_name not in self.adapters:
            print(f"Unknown tool: {tool_name}")
            return False

        adapter = self.adapters[tool_name]

        if not adapter.is_installed():
            print(f"{self.tool_names[tool_name]} is not installed")
            return False

        # Use defaults if not provided
        if server_name is None:
            server_name = "giljo-mcp"

        if command is None or args is None:
            cmd, arg_list = adapter.get_default_command_args()
        else:
            cmd, arg_list = command, args

        if env is None:
            environment = adapter.get_default_env()
        else:
            environment = env

        try:
            print(f"Registering with {self.tool_names[tool_name]}...")
            success = adapter.register(server_name, cmd, arg_list, environment)

            if success:
                print(f"Successfully registered with {self.tool_names[tool_name]}")
            else:
                print(f"Failed to register with {self.tool_names[tool_name]}")

            return success

        except Exception as e:
            print(f"Error registering with {self.tool_names[tool_name]}: {e}")
            return False

    def verify_all(self, server_name: str = "giljo-mcp") -> Dict[str, bool]:
        """
        Verify MCP server registration for all tools.

        Args:
            server_name: Name of the MCP server to verify

        Returns:
            dict: Mapping of tool name to verification status
        """
        results = {}
        installed = self.detect_installed_tools()

        for tool_name in installed:
            adapter = self.adapters[tool_name]
            try:
                verified = adapter.verify(server_name)
                results[tool_name] = verified
            except Exception as e:
                print(f"Error verifying {self.tool_names[tool_name]}: {e}")
                results[tool_name] = False

        return results

    def unregister_all(self, server_name: str = "giljo-mcp") -> Dict[str, bool]:
        """
        Unregister MCP server from all detected tools.

        Args:
            server_name: Name of the MCP server to unregister

        Returns:
            dict: Mapping of tool name to unregistration success status
        """
        results = {}
        installed = self.detect_installed_tools()

        if not installed:
            print("No AI CLI tools detected")
            return results

        for tool_name in installed:
            adapter = self.adapters[tool_name]
            try:
                print(f"Unregistering from {self.tool_names[tool_name]}...")
                success = adapter.unregister(server_name)
                results[tool_name] = success

                if success:
                    print(f"  Successfully unregistered from {self.tool_names[tool_name]}")
                else:
                    print(f"  Failed to unregister from {self.tool_names[tool_name]}")

            except Exception as e:
                print(f"  Error unregistering from {self.tool_names[tool_name]}: {e}")
                results[tool_name] = False

        return results

    def verify_single(self, tool_name: str, server_name: str = "giljo-mcp") -> bool:
        """
        Verify MCP server registration for a specific tool.

        Args:
            tool_name: Name of the tool to verify
            server_name: Name of the MCP server to verify

        Returns:
            bool: True if verified, False otherwise
        """
        if tool_name not in self.adapters:
            print(f"Unknown tool: {tool_name}")
            return False

        adapter = self.adapters[tool_name]

        if not adapter.is_installed():
            print(f"{self.tool_names[tool_name]} is not installed")
            return False

        try:
            return adapter.verify(server_name)
        except Exception as e:
            print(f"Error verifying {self.tool_names[tool_name]}: {e}")
            return False

    def unregister_all(self, server_name: str = "giljo-mcp") -> Dict[str, bool]:
        """
        Unregister MCP server from all tools.

        Args:
            server_name: Name of the MCP server to unregister

        Returns:
            dict: Mapping of tool name to unregistration status
        """
        results = {}
        installed = self.detect_installed_tools()

        for tool_name in installed:
            adapter = self.adapters[tool_name]
            try:
                success = adapter.unregister(server_name)
                results[tool_name] = success

                if success:
                    print(f"Unregistered from {self.tool_names[tool_name]}")
                else:
                    print(f"Failed to unregister from {self.tool_names[tool_name]}")

            except Exception as e:
                print(f"Error unregistering from {self.tool_names[tool_name]}: {e}")
                results[tool_name] = False

        return results

    def print_summary(self, results: Dict[str, bool], operation: str = "registration"):
        """
        Print a summary of operation results.

        Args:
            results: Dictionary mapping tool names to success status
            operation: Name of the operation (e.g., 'registration', 'verification')
        """
        print(f"\n{'='*60}")
        print(f"{operation.capitalize()} Summary")
        print("=" * 60)

        if not results:
            print("No AI CLI tools detected")
            return

        successful = [tool for tool, status in results.items() if status]
        failed = [tool for tool, status in results.items() if not status]

        if successful:
            print(f"\nSuccessful ({len(successful)}):")
            for tool in successful:
                print(f"  - {self.tool_names[tool]}")

        if failed:
            print(f"\nFailed ({len(failed)}):")
            for tool in failed:
                print(f"  - {self.tool_names[tool]}")

        print("=" * 60)
