#!/usr/bin/env python3
"""
GiljoAI MCP Setup Base Module - v2.0 HTTP Architecture
Base classes and utilities for installation scripts
"""

import json
import os
import platform
import secrets
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Updated port assignments for v2.0 architecture
PORT_ASSIGNMENTS = {
    # New unified architecture - single server
    "GiljoAI Orchestrator": 7272,  # Main HTTP server (API + MCP tools + WebSocket)

    # Required services
    "PostgreSQL": 5432,  # Required database service

    # Optional development services
    "Frontend Dev Server": 6000,  # Vite dev server (optional)

    # Alternative ports if 7272 is occupied
    "alternatives": [7273, 7274, 8747, 8823, 9456, 9789],

    # Deprecated ports (no longer used in v2.0)
    # "GiljoAI MCP Server": 6001,  # REMOVED - stdio server deprecated
    # "GiljoAI REST API": 6002,    # REMOVED - merged into port 8000
    # "GiljoAI WebSocket": 6003,   # REMOVED - merged into port 8000
}

def check_port(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0  # True if port is in use
    except Exception:
        return False


def find_available_port(preferred: int = 7272, alternatives: List[int] = None) -> Optional[int]:
    """
    Find an available port, starting with preferred.

    Args:
        preferred: The preferred port to use (default: 7272)
        alternatives: List of alternative ports to try

    Returns:
        Available port number, or None if all are occupied
    """
    if alternatives is None:
        alternatives = PORT_ASSIGNMENTS.get("alternatives", [7273, 7274, 8747, 8823, 9456])

    # Check preferred first
    if not check_port(preferred):
        return preferred

    # Try alternatives
    for port in alternatives:
        if not check_port(port):
            return port

    # Last resort: find random available in safe range
    import random
    for _ in range(10):
        port = random.randint(7200, 9999)
        if not check_port(port):
            return port

    return None


class GiljoSetup:
    """Base setup class for GiljoAI MCP installation"""

    def __init__(self):
        self.root_path = Path(__file__).parent
        self.config = {}
        self.env_vars = {}
        self.platform_info = self._detect_platform()

        # v2.0 Architecture defaults
        self.server_port = 7272  # Single unified server (changed from 8000)
        self.deployment_mode = "LOCAL"  # LOCAL, LAN, or WAN
        self.selected_port = None  # Will be set during setup

    def _detect_platform(self) -> Dict[str, Any]:
        """Detect platform and environment details"""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
            "arch": platform.machine(),
            "is_windows": platform.system() == "Windows",
            "is_mac": platform.system() == "Darwin",
            "is_linux": platform.system() == "Linux",
        }

    def check_python_version(self) -> bool:
        """Verify Python version is 3.10+"""
        return sys.version_info >= (3, 10)

    def check_system_requirements(self) -> List[str]:
        """Check system requirements and return list of issues"""
        issues = []

        # Python version
        if not self.check_python_version():
            issues.append(f"Python 3.10+ required, found {sys.version}")

        # Check for pip
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"],
                         capture_output=True, check=True)
        except:
            issues.append("pip is not installed or not accessible")

        # Check for git (optional but recommended)
        try:
            subprocess.run(["git", "--version"], capture_output=True, check=True)
        except:
            issues.append("git is not installed (optional but recommended)")

        return issues

    def select_port(self, preferred: int = None) -> int:
        """
        Select an available port for the server.

        Args:
            preferred: Preferred port (defaults to self.server_port)

        Returns:
            Selected available port

        Raises:
            RuntimeError: If no available port can be found
        """
        if preferred is None:
            preferred = self.server_port

        available_port = find_available_port(preferred)

        if available_port is None:
            raise RuntimeError("No available ports found in range 7200-9999")

        self.selected_port = available_port
        self.server_port = available_port
        return available_port

    def validate_ports(self) -> List[Tuple[str, int, bool]]:
        """Check port availability for v2.0 architecture"""
        results = []

        # Main server port (required) - use selected_port if available
        port_to_check = self.selected_port or self.server_port
        is_used = check_port(port_to_check)
        results.append(("GiljoAI Orchestrator", port_to_check, is_used))

        # Optional frontend dev server
        if self.config.get("enable_frontend_dev", False):
            is_used = check_port(6000)
            results.append(("Frontend Dev Server", 6000, is_used))

        # PostgreSQL if not using SQLite
        if self.config.get("database_type") == "postgresql":
            is_used = check_port(5432)
            results.append(("PostgreSQL", 5432, is_used))

        return results

    def create_venv(self) -> bool:
        """Create virtual environment"""
        venv_path = self.root_path / "venv"

        if venv_path.exists():
            print("Virtual environment already exists")
            return True

        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)],
                         check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def install_requirements(self) -> bool:
        """Install Python requirements"""
        req_file = self.root_path / "requirements.txt"
        if not req_file.exists():
            print("requirements.txt not found")
            return False

        # Determine pip path
        if self.platform_info["is_windows"]:
            pip_path = self.root_path / "venv" / "Scripts" / "pip.exe"
        else:
            pip_path = self.root_path / "venv" / "bin" / "pip"

        if not pip_path.exists():
            pip_path = sys.executable.replace("python", "pip")

        try:
            subprocess.run([str(pip_path), "install", "-r", str(req_file)],
                         check=True)

            # Install package in development mode (skip if during installation)
            if not os.environ.get('GILJO_SKIP_EDITABLE_INSTALL'):
                subprocess.run([str(pip_path), "install", "-e", "."],
                             check=True, cwd=str(self.root_path))
            return True
        except subprocess.CalledProcessError:
            return False

    def generate_api_key(self) -> str:
        """Generate a secure API key"""
        return secrets.token_urlsafe(32)

    def create_config_file(self) -> bool:
        """Create configuration file for v2.0 architecture - PostgreSQL only"""
        config_data = {
            "version": "2.0.0",
            "server": {
                "mode": self.deployment_mode,
                "host": "0.0.0.0" if self.deployment_mode != "LOCAL" else "127.0.0.1",
                "port": self.server_port,
                "api_port": self.server_port,  # Same as main port in v2.0
            },
            "database": {
                "type": "postgresql",  # Always PostgreSQL now
                "postgresql": {
                    "host": self.config.get("pg_host", "localhost"),
                    "port": self.config.get("pg_port", 5432),
                    "database": self.config.get("pg_database", "giljo_mcp"),
                    "username": self.config.get("pg_user", "postgres"),
                    "password": self.config.get("pg_password", ""),
                }
            },
            "security": {
                "api_key": self.generate_api_key() if self.deployment_mode != "LOCAL" else None,
                "require_auth": self.deployment_mode != "LOCAL",
            },
            "features": {
                "mcp_stdio_adapter": True,  # New in v2.0
                "http_api": True,
                "websocket": True,
                "multi_user": True,
            }
        }

        # Write config file
        config_path = self.root_path / "config.yaml"
        try:
            import yaml
            with open(config_path, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False)
            return True
        except ImportError:
            # Fallback to JSON if yaml not available
            config_path = self.root_path / "config.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error creating config: {e}")
            return False

    def create_directories(self) -> bool:
        """Create necessary directories"""
        dirs = [
            "data",
            "logs",
            "backups",
            ".giljo_mcp/locks",
            ".giljo_mcp/cache",
        ]

        try:
            for dir_name in dirs:
                dir_path = self.root_path / dir_name
                dir_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directories: {e}")
            return False

    def create_desktop_shortcuts(self) -> bool:
        """Create desktop shortcuts for v2.0"""
        if not self.platform_info["is_windows"]:
            return True  # Skip for non-Windows

        try:
            # Import shortcut creator
            from create_shortcuts import DesktopShortcutCreator
            creator = DesktopShortcutCreator()

            shortcuts = [
                ("Start GiljoAI Server", "start_giljo.bat",
                 "Start the GiljoAI orchestration server"),
                ("Stop GiljoAI Server", "stop_giljo.bat",
                 "Stop the GiljoAI orchestration server"),
                ("GiljoAI Dashboard", f"http://localhost:{self.server_port}",
                 "Open the GiljoAI dashboard in browser"),
            ]

            for name, target, desc in shortcuts:
                creator.create_shortcut(name, target, desc)

            return True
        except Exception as e:
            print(f"Could not create shortcuts: {e}")
            return False

    def display_summary(self):
        """Display installation summary for v2.0"""
        print("\n" + "="*60)
        print("GiljoAI MCP v2.0 Installation Complete!")
        print("="*60)
        print("\nArchitecture: Unified HTTP Server")
        print(f"Server Port: {self.server_port}")
        print(f"Deployment Mode: {self.deployment_mode}")
        print("Database: PostgreSQL")

        print("\nKey Features:")
        print("✓ Multi-user support (multiple concurrent connections)")
        print("✓ Persistent server (stays running between sessions)")
        print("✓ HTTP/REST API for all operations")
        print("✓ WebSocket for real-time updates")
        print("✓ Claude compatibility via stdio adapter")

        print("\nNext Steps:")
        print("1. Start the server: run start_giljo.bat")
        print("2. For Claude: run register_claude.bat (one-time)")
        print(f"3. Access dashboard: http://localhost:{self.server_port}")
        print(f"4. API documentation: http://localhost:{self.server_port}/docs")

        if self.deployment_mode != "LOCAL":
            print(f"\nAPI Key: {self.config.get('api_key', 'Check config.yaml')}")
            print("Save this key - you'll need it for remote connections")


def main():
    """Main entry point for setup"""
    # Don't run during pip install
    import sys
    if 'pip' in sys.modules or 'setuptools' in sys.modules:
        return

    # Check if we should use enhanced CLI or basic setup
    try:
        from setup_cli import GiljoCLISetup
        setup = GiljoCLISetup()
        setup.run()
    except ImportError:
        # Fallback to basic setup
        print("Enhanced CLI not available, using basic setup")
        setup = GiljoSetup()

        # Basic interactive setup
        print("GiljoAI MCP Setup - PostgreSQL Edition")
        print("="*40)

        # Check requirements
        issues = setup.check_system_requirements()
        if issues:
            print("\nSystem requirements check found issues:")
            for issue in issues:
                print(f"  - {issue}")

            response = input("\nContinue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)

        # Select deployment mode
        print("\nDeployment Mode:")
        print("1) Local (single user, no auth)")
        print("2) Server (multi-user, API auth)")
        choice = input("Select (1-2): ")

        setup.deployment_mode = "LOCAL" if choice == "1" else "SERVER"

        # Get PostgreSQL config
        print("\nPostgreSQL Configuration:")
        setup.config['database_type'] = 'postgresql'
        setup.config['pg_host'] = input("Host [localhost]: ").strip() or "localhost"
        setup.config['pg_port'] = input("Port [5432]: ").strip() or "5432"
        setup.config['pg_database'] = input("Database [giljo_mcp]: ").strip() or "giljo_mcp"
        setup.config['pg_user'] = input("Username [postgres]: ").strip() or "postgres"
        setup.config['pg_password'] = input("Password: ").strip()

        # Select port
        setup.select_port()

        # Run setup steps
        print("\nRunning setup...")
        if setup.create_venv():
            print("✓ Virtual environment created")

        if setup.install_requirements():
            print("✓ Dependencies installed")

        if setup.create_config_file():
            print("✓ Configuration created")

        if setup.create_directories():
            print("✓ Directories created")

        if setup.platform_info["is_windows"]:
            setup.create_desktop_shortcuts()

        # Show summary
        setup.display_summary()


if __name__ == "__main__":
    main()
