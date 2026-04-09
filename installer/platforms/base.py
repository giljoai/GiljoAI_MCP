# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Abstract base class for platform-specific installation operations.

Defines the Strategy pattern interface that all platform handlers must implement.
Isolates all OS-specific code into concrete implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any


class PlatformHandler(ABC):
    """
    Abstract base class for platform-specific installation operations.

    This class defines the interface for all platform handlers using the Strategy pattern.
    Concrete implementations handle Windows, Linux, and macOS-specific operations.

    All methods must be implemented by concrete classes.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """
        Return the platform name.

        Returns:
            Platform name ('Windows', 'Linux', or 'macOS')
        """
        pass

    @abstractmethod
    def get_venv_python(self, venv_dir: Path) -> Path:
        """
        Get path to Python executable in virtual environment.

        Platform-specific paths:
        - Windows: venv/Scripts/python.exe
        - Linux/macOS: venv/bin/python

        Args:
            venv_dir: Path to virtual environment directory

        Returns:
            Path to Python executable
        """
        pass

    @abstractmethod
    def get_venv_pip(self, venv_dir: Path) -> Path:
        """
        Get path to pip executable in virtual environment.

        Platform-specific paths:
        - Windows: venv/Scripts/pip.exe
        - Linux/macOS: venv/bin/pip

        Args:
            venv_dir: Path to virtual environment directory

        Returns:
            Path to pip executable
        """
        pass

    @abstractmethod
    def get_postgresql_scan_paths(self) -> List[Path]:
        """
        Get list of paths to scan for PostgreSQL installation.

        Platform-specific search locations:
        - Windows: C:\\Program Files\\PostgreSQL\\*\\bin\\psql.exe
        - Linux: /usr/bin/psql, /usr/lib/postgresql/*/bin/psql
        - macOS: Homebrew paths (Intel/ARM), Postgres.app

        Returns:
            List of paths to check for psql executable
        """
        pass

    @abstractmethod
    def get_postgresql_install_guide(self, recommended_version: int = 18) -> str:
        """
        Get platform-specific PostgreSQL installation instructions.

        Args:
            recommended_version: Recommended PostgreSQL version (default: 18)

        Returns:
            Multi-line string with installation instructions
        """
        pass

    @abstractmethod
    def supports_desktop_shortcuts(self) -> bool:
        """
        Check if platform supports desktop shortcuts.

        Returns:
            True if platform supports shortcuts, False otherwise

        Platform support:
        - Windows: True (.lnk files via win32com)
        - Linux: True (.desktop files)
        - macOS: False (future: .app bundles)
        """
        pass

    @abstractmethod
    def create_desktop_shortcuts(self, install_dir: Path, venv_dir: Path) -> Dict[str, Any]:
        """
        Create platform-specific desktop shortcuts/launchers.

        Creates shortcuts for:
        - Main application launcher
        - Developer control panel (if available)

        Args:
            install_dir: Installation directory path
            venv_dir: Virtual environment directory path

        Returns:
            Result dictionary with:
            - success: bool - Whether shortcuts were created
            - method: str - Method used (e.g., 'win32com', 'desktop', 'not_supported')
            - shortcuts_created: List[str] - List of created shortcuts
            - message: str - Status message
        """
        pass

    @abstractmethod
    def run_npm_command(self, cmd: List[str], cwd: Path, timeout: int = 300) -> Dict[str, Any]:
        """
        Run npm command with platform-specific shell handling.

        CRITICAL PLATFORM DIFFERENCES:
        - Windows: MUST use shell=True (npm is a batch file)
        - Linux/macOS: MUST use shell=False (direct execution)

        Args:
            cmd: Command list (e.g., ['npm', 'install'])
            cwd: Working directory for command
            timeout: Timeout in seconds (default: 300)

        Returns:
            Result dictionary with:
            - success: bool - Whether command succeeded
            - stdout: str - Standard output
            - stderr: str - Standard error
            - returncode: int - Process return code
        """
        pass

    @abstractmethod
    def get_network_ips(self) -> List[str]:
        """
        Get non-localhost IPv4 addresses for network interface selection.

        Filters out:
        - Loopback addresses (127.x.x.x)
        - Link-local addresses (169.254.x.x)

        Returns:
            List of IPv4 address strings
        """
        pass

    @abstractmethod
    def welcome_screen(self) -> None:
        """
        Print platform-specific welcome screen.

        Should display:
        - Platform detection (with distro info on Linux)
        - Python version
        - Architecture information
        """
        pass

    @abstractmethod
    def get_platform_specific_warnings(self) -> List[str]:
        """
        Get platform-specific warnings for user.

        Examples:
        - Ubuntu: UFW firewall configuration reminder
        - Windows: Usually none (Windows Firewall prompts user)
        - macOS: Usually none (user-friendly firewall UI)

        Returns:
            List of warning strings (empty if no warnings)
        """
        pass
