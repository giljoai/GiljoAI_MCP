"""
Minimal CLI Installer for GiljoAI MCP

Performs only essential setup tasks:
1. Detect Python and PostgreSQL
2. Create virtual environment
3. Install dependencies
4. Create minimal config
5. Start services
6. Open browser to setup wizard

All configuration moved to frontend wizard at /setup
No MCP registration or complex configuration logic.
"""

import sys
import subprocess
import webbrowser
from pathlib import Path
from typing import Dict, Tuple, Optional
import yaml


class MinimalInstaller:
    """
    Minimal installer - configuration moved to frontend wizard.

    This installer performs only the bare minimum setup required to launch
    the application. All configuration is handled by the frontend wizard.
    """

    def __init__(self, install_dir: Optional[Path] = None):
        """
        Initialize minimal installer.

        Args:
            install_dir: Installation directory (defaults to current directory)
        """
        self.install_dir = install_dir if install_dir else Path.cwd()
        self.venv_dir = self.install_dir / "venv"
        self.config_path = self.install_dir / "config.yaml"
        self.python_version: Optional[Tuple[int, int]] = None
        self.postgres_version: Optional[int] = None

    def run(self) -> Dict:
        """
        Execute minimal installation.

        Returns:
            Dict with 'success' (bool) and 'next_step' or 'error' message
        """
        print("=" * 60)
        print("GiljoAI MCP Minimal Installer")
        print("=" * 60)
        print()

        # Step 1: Detect Python
        if not self.detect_python():
            return self._error("Python 3.11+ required")

        # Step 2: Detect PostgreSQL
        if not self.detect_postgresql():
            self.handle_missing_postgresql()
            return self._error("PostgreSQL 18 required. Install and re-run.")

        # Step 3: Create venv
        print("Creating virtual environment...")
        self.create_venv()

        # Step 4: Install dependencies
        print("Installing Python dependencies...")
        self.install_dependencies()

        # Step 5: Create minimal config
        print("Creating minimal configuration...")
        self.create_minimal_config()

        # Step 6: Start services
        print("Starting backend service...")
        self.start_backend()

        # Step 7: Open setup wizard
        print()
        print("=" * 60)
        print("Installation Complete!")
        print("=" * 60)
        print()
        print("Opening setup wizard in your browser...")
        print("URL: http://localhost:7274/setup")
        print()
        self.open_setup_wizard()

        return {"success": True, "next_step": "Open browser to http://localhost:7274/setup"}

    def detect_python(self) -> bool:
        """
        Detect Python 3.11+.

        Returns:
            True if Python 3.11+ detected, False otherwise
        """
        version = sys.version_info
        # Handle both version_info objects and tuples (for testing)
        if isinstance(version, tuple):
            self.python_version = (version[0], version[1])
        else:
            self.python_version = (version.major, version.minor)

        if self.python_version < (3, 11):
            print(f"ERROR: Python {self.python_version[0]}.{self.python_version[1]} detected")
            print("Python 3.11 or higher required")
            return False

        print(f"✓ Python {self.python_version[0]}.{self.python_version[1]} detected")
        return True

    def detect_postgresql(self) -> bool:
        """
        Detect PostgreSQL 18+.

        Returns:
            True if PostgreSQL detected, False otherwise
        """
        try:
            result = subprocess.run(["psql", "--version"], capture_output=True, text=True, check=True)

            # Parse version from output (e.g., "psql (PostgreSQL) 18.0")
            version_str = result.stdout.split()[2]
            self.postgres_version = int(version_str.split(".")[0])

            if self.postgres_version < 18:
                print(f"WARNING: PostgreSQL {self.postgres_version} detected")
                print("PostgreSQL 18 recommended")
            else:
                print(f"✓ PostgreSQL {self.postgres_version} detected")

            return True

        except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError):
            print("✗ PostgreSQL not found")
            return False

    def handle_missing_postgresql(self) -> None:
        """
        Open browser to PostgreSQL download page.
        """
        print()
        print("PostgreSQL 18 is required but not installed.")
        print()
        print("Opening download page in browser...")
        print("After installing PostgreSQL, re-run this installer.")
        print()

        webbrowser.open("https://www.postgresql.org/download/")
        input("Press Enter after installing PostgreSQL...")

    def create_venv(self) -> None:
        """
        Create Python virtual environment.
        """
        subprocess.run([sys.executable, "-m", "venv", str(self.venv_dir)], check=True)
        print(f"✓ Virtual environment created at {self.venv_dir}")

    def install_dependencies(self) -> None:
        """
        Install Python dependencies via pip.
        """
        pip_exe = self._get_pip_path()
        requirements = self.install_dir / "requirements.txt"

        subprocess.run([str(pip_exe), "install", "-r", str(requirements)], check=True)
        print("✓ Dependencies installed")

    def create_minimal_config(self) -> None:
        """
        Create minimal localhost configuration.
        """
        config = {
            "mode": "localhost",
            "api": {"host": "127.0.0.1", "port": 7272},
            "frontend": {"host": "127.0.0.1", "port": 7274},
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "giljo_mcp",
                "user": "postgres",
                # Password will be set by wizard
            },
            "setup_complete": False,
        }

        with open(self.config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        print(f"✓ Configuration created at {self.config_path}")

    def start_backend(self) -> None:
        """
        Start backend service in background.
        """
        python_exe = self._get_python_path()

        # Start backend in background
        subprocess.Popen(
            [str(python_exe), "-m", "uvicorn", "api.app:app", "--host", "127.0.0.1", "--port", "7272"],
            cwd=self.install_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("✓ Backend started on http://localhost:7272")

    def open_setup_wizard(self) -> None:
        """
        Open browser to setup wizard.
        """
        webbrowser.open("http://localhost:7274/setup")

    def _get_python_path(self) -> Path:
        """
        Get venv Python executable path.

        Returns:
            Path to Python executable in virtual environment
        """
        if sys.platform == "win32":
            return self.venv_dir / "Scripts" / "python.exe"
        return self.venv_dir / "bin" / "python"

    def _get_pip_path(self) -> Path:
        """
        Get venv pip executable path.

        Returns:
            Path to pip executable in virtual environment
        """
        if sys.platform == "win32":
            return self.venv_dir / "Scripts" / "pip.exe"
        return self.venv_dir / "bin" / "pip"

    def _error(self, message: str) -> Dict:
        """
        Return error result.

        Args:
            message: Error message

        Returns:
            Dict with success=False and error message
        """
        return {"success": False, "error": message}


if __name__ == "__main__":
    installer = MinimalInstaller()
    result = installer.run()

    if not result["success"]:
        print(f"Installation failed: {result['error']}")
        sys.exit(1)
