#!/usr/bin/env python3
"""
GiljoAI MCP - Base MCP Adapter

DEPRECATED: MCP registration moved to frontend setup wizard.

This file is no longer used and will be removed in future versions.
All MCP registration is now handled by the frontend setup wizard at /setup.

See:
- docs/IMPLEMENTATION_PLAN.md Phase 0
- docs/architecture/installer_responsibilities.md
- docs/guides/SETUP_WIZARD_GUIDE.md
"""

import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
import shutil
import sys


# Issue deprecation warning when module is imported
warnings.warn(
    "MCPAdapterBase is deprecated. MCP registration is now handled by the "
    "frontend setup wizard at /setup. This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)


class MCPAdapterBase(ABC):
    """
    Base class for AI CLI MCP registration adapters.

    DEPRECATED: Use the frontend setup wizard at /setup instead.
    """

    def __init__(self):
        """Initialize the adapter."""
        self.server_name = "giljo-mcp"
        self.install_dir = Path(__file__).parent.parent.resolve()

    @staticmethod
    @abstractmethod
    def get_cli_name() -> str:
        """
        Return the CLI command name (e.g., 'claude', 'codex', 'gemini').

        Returns:
            str: The CLI command name
        """
        pass

    @staticmethod
    @abstractmethod
    def get_config_path() -> Path:
        """
        Return platform-specific config file path.

        Returns:
            Path: The configuration file path
        """
        pass

    @classmethod
    def is_installed(cls) -> bool:
        """
        Check if CLI tool is installed.

        Returns:
            bool: True if the CLI tool is installed, False otherwise
        """
        return shutil.which(cls.get_cli_name()) is not None

    @abstractmethod
    def register(self, server_name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> bool:
        """
        Register MCP server.

        Args:
            server_name: Name of the MCP server
            command: Command to execute (e.g., path to Python)
            args: Command arguments
            env: Optional environment variables

        Returns:
            bool: True if registration successful, False otherwise
        """
        pass

    @abstractmethod
    def verify(self, server_name: str) -> bool:
        """
        Verify MCP server is registered.

        Args:
            server_name: Name of the MCP server to verify

        Returns:
            bool: True if server is registered, False otherwise
        """
        pass

    @abstractmethod
    def unregister(self, server_name: str) -> bool:
        """
        Remove MCP server registration.

        Args:
            server_name: Name of the MCP server to unregister

        Returns:
            bool: True if unregistration successful, False otherwise
        """
        pass

    def get_python_path(self) -> Path:
        """
        Get path to Python executable in venv.

        Returns:
            Path: Path to the Python executable
        """
        if sys.platform == "win32":
            python_path = self.install_dir / "venv" / "Scripts" / "python.exe"
        else:
            python_path = self.install_dir / "venv" / "bin" / "python"

        return python_path

    def get_default_command_args(self) -> tuple[str, List[str]]:
        """
        Get default command and args for MCP server.

        Returns:
            tuple: (command, args) where command is the Python path and args is the module invocation
        """
        python_path = self.get_python_path()
        command = str(python_path).replace("\\", "/")
        args = ["-m", "giljo_mcp.mcp_adapter"]

        return command, args

    def get_default_env(self) -> Dict[str, str]:
        """
        Get default environment variables for MCP server.

        Returns:
            dict: Environment variables
        """
        install_dir_str = str(self.install_dir).replace("\\", "/")
        return {"GILJO_MCP_HOME": install_dir_str, "GILJO_SERVER_URL": "http://localhost:7272"}

    def ensure_config_directory(self, config_path: Path) -> bool:
        """
        Ensure the configuration directory exists.

        Args:
            config_path: Path to the configuration file

        Returns:
            bool: True if directory exists or was created successfully
        """
        try:
            config_dir = config_path.parent
            config_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating config directory: {e}")
            return False
