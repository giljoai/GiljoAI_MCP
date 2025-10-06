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
        print("Press Enter to begin installation...")
        input()
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

        # Step 4: Install Python dependencies
        print("Installing Python dependencies...")
        self.install_dependencies()

        # Step 5: Install frontend dependencies
        print("Installing frontend dependencies...")
        self.install_frontend_dependencies()

        # Step 6: Create minimal config
        print("Creating minimal configuration...")
        self.create_minimal_config()

        # Step 6: Start services
        print()
        print("=" * 60)
        print("STARTING SERVICES")
        print("=" * 60)
        print()
        print("Starting backend service...")
        self.start_backend()

        print()
        print("Starting frontend service...")
        self.start_frontend()

        # Step 7: Wait for services to be ready
        print()
        print("Waiting for services to start...")
        if self.wait_for_services():
            print("[OK] Services are ready!")
        else:
            print()
            print("WARNING: Services may still be starting.")
            print("Check the console windows for any errors.")
            print()

        # Step 8: Open setup wizard
        print()
        print("=" * 60)
        print("Installation Complete!")
        print("=" * 60)
        print()
        print("Opening setup wizard in your browser...")
        print("URL: http://localhost:7274/setup")
        print()
        print("Backend console: http://localhost:7272")
        print("Frontend console: http://localhost:7274")
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

        print(f"[OK] Python {self.python_version[0]}.{self.python_version[1]} detected")
        return True

    def detect_postgresql(self) -> bool:
        """
        Detect PostgreSQL 17+ using OS-appropriate methods.

        Returns:
            True if PostgreSQL detected, False otherwise
        """
        import os
        import platform
        from pathlib import Path

        system = platform.system()
        psql_paths = []

        # 1. Check if psql is in PATH (works on all platforms)
        psql_paths.append("psql")

        # 2. Platform-specific detection
        if system == "Windows":
            # Check Windows Registry for PostgreSQL installations
            try:
                import winreg

                # Check both 64-bit and 32-bit registry
                registry_paths = [
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\PostgreSQL\Installations"),
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\PostgreSQL\Installations"),
                ]

                for hkey, subkey_path in registry_paths:
                    try:
                        with winreg.OpenKey(hkey, subkey_path) as key:
                            i = 0
                            while True:
                                try:
                                    install_name = winreg.EnumKey(key, i)
                                    with winreg.OpenKey(key, install_name) as install_key:
                                        base_dir, _ = winreg.QueryValueEx(install_key, "Base Directory")
                                        psql_path = Path(base_dir) / "bin" / "psql.exe"
                                        if psql_path.exists():
                                            psql_paths.append(str(psql_path))
                                    i += 1
                                except OSError:
                                    break
                    except FileNotFoundError:
                        continue
            except ImportError:
                pass  # winreg not available (not on Windows)

            # Fallback: Check common installation directories on all drives
            for drive in ["C:", "D:", "E:", "F:", "G:"]:
                # Standard EDB installer locations
                for version in range(20, 14, -1):  # Check versions 20 down to 15
                    path = Path(f"{drive}\\Program Files\\PostgreSQL\\{version}\\bin\\psql.exe")
                    if path.exists():
                        psql_paths.append(str(path))

                # Custom installation at root
                path = Path(f"{drive}\\PostgreSQL\\bin\\psql.exe")
                if path.exists():
                    psql_paths.append(str(path))

        elif system == "Linux":
            # Check common Linux PostgreSQL locations
            linux_paths = [
                "/usr/bin/psql",
                "/usr/local/bin/psql",
                "/usr/pgsql-17/bin/psql",
                "/usr/pgsql-18/bin/psql",
                "/opt/postgresql/bin/psql",
            ]
            psql_paths.extend([p for p in linux_paths if Path(p).exists()])

        elif system == "Darwin":  # macOS
            # Check common macOS PostgreSQL locations
            macos_paths = [
                "/usr/local/bin/psql",
                "/opt/homebrew/bin/psql",
                "/Library/PostgreSQL/17/bin/psql",
                "/Library/PostgreSQL/18/bin/psql",
                "/Applications/Postgres.app/Contents/Versions/latest/bin/psql",
            ]
            psql_paths.extend([p for p in macos_paths if Path(p).exists()])

        # 3. Try each discovered path
        for psql_path in psql_paths:
            try:
                result = subprocess.run(
                    [str(psql_path), "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5
                )

                # Parse version from output (e.g., "psql (PostgreSQL) 17.5")
                version_str = result.stdout.split()[2]
                self.postgres_version = int(version_str.split(".")[0])

                if self.postgres_version < 17:
                    print(f"WARNING: PostgreSQL {self.postgres_version} detected")
                    print("PostgreSQL 17+ required")
                    return False
                elif self.postgres_version < 18:
                    print(f"[OK] PostgreSQL {self.postgres_version} detected (version {version_str})")
                    print("  Note: PostgreSQL 18 is latest, but 17+ works fine")
                else:
                    print(f"[OK] PostgreSQL {self.postgres_version} detected (version {version_str})")

                return True

            except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError, subprocess.TimeoutExpired):
                continue  # Try next path

        # 4. Not found
        print("[ERROR] PostgreSQL not found")
        print(f"  Searched using {system} detection methods:")
        if system == "Windows":
            print("  - Windows Registry (SOFTWARE\\PostgreSQL\\Installations)")
            print("  - Program Files\\PostgreSQL\\[version]\\bin")
            print("  - Custom installations on C:, D:, E:, F:, G: drives")
        elif system == "Linux":
            print("  - /usr/bin, /usr/local/bin, /usr/pgsql-*/bin")
        elif system == "Darwin":
            print("  - Homebrew, Postgres.app, /Library/PostgreSQL")
        print("  - System PATH")
        return False

    def handle_missing_postgresql(self) -> None:
        """
        Open browser to PostgreSQL download page.
        """
        print()
        print("PostgreSQL 17+ is required but not installed.")
        print()
        print("Opening download page in browser...")
        print("After installing PostgreSQL, re-run this installer.")
        print()
        print("NOTE: Install to F:\\PostgreSQL or add to system PATH")

        webbrowser.open("https://www.postgresql.org/download/")
        input("Press Enter after installing PostgreSQL...")

    def create_venv(self) -> None:
        """
        Create Python virtual environment.
        """
        subprocess.run([sys.executable, "-m", "venv", str(self.venv_dir)], check=True)
        print(f"[OK] Virtual environment created at {self.venv_dir}")

    def install_dependencies(self) -> None:
        """
        Install Python dependencies via pip with progress bar.
        """
        pip_exe = self._get_pip_path()
        requirements = self.install_dir / "requirements.txt"

        print()
        print("Installing dependencies (this may take a few minutes)...")
        print()

        # Run pip with progress output
        process = subprocess.Popen(
            [str(pip_exe), "install", "-r", str(requirements), "--progress-bar", "on"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Stream output in real-time
        if process.stdout:
            for line in process.stdout:
                print(line, end='', flush=True)

        process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)

        print()
        print("[OK] Dependencies installed")

    def install_frontend_dependencies(self) -> None:
        """
        Install frontend npm dependencies with progress output.
        """
        frontend_dir = self.install_dir / "frontend"

        if not frontend_dir.exists():
            print(f"[WARNING] Frontend directory not found at {frontend_dir}")
            return

        print()
        print("Installing frontend dependencies (this may take a few minutes)...")
        print()

        # Run npm install with progress output
        import platform
        if platform.system() == "Windows":
            npm_cmd = "npm.cmd"
        else:
            npm_cmd = "npm"

        process = subprocess.Popen(
            [npm_cmd, "install"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Stream output in real-time
        if process.stdout:
            for line in process.stdout:
                print(line, end='', flush=True)

        process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)

        print()
        print("[OK] Frontend dependencies installed")

    def create_minimal_config(self) -> None:
        """
        Create minimal localhost configuration with setup mode flag.
        """
        config = {
            "mode": "localhost",
            "setup_mode": True,  # Flag to skip validation during initial setup
            "api": {"host": "127.0.0.1", "port": 7272},
            "frontend": {"host": "127.0.0.1", "port": 7274},
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "giljo_mcp",
                "user": "postgres",
                "password": "SETUP_REQUIRED",  # Placeholder to satisfy validation
            },
            "setup_complete": False,
        }

        with open(self.config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        print(f"[OK] Configuration created at {self.config_path}")

    def start_backend(self) -> None:
        """
        Start backend service with visible output in new window.
        """
        python_exe = self._get_python_path()

        print()
        print("Starting backend in new console window...")
        print("The backend console will show startup logs and errors.")
        print()

        import platform
        if platform.system() == "Windows":
            # Start backend in new visible console window
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k",
                 str(python_exe), "-m", "uvicorn", "api.app:app",
                 "--host", "127.0.0.1", "--port", "7272", "--reload"],
                cwd=self.install_dir,
                shell=True
            )
        else:
            # For Linux/Mac, start in background with output visible
            subprocess.Popen(
                [str(python_exe), "-m", "uvicorn", "api.app:app",
                 "--host", "127.0.0.1", "--port", "7272", "--reload"],
                cwd=self.install_dir
            )

        print("[OK] Backend starting on http://localhost:7272")
        print("    Check the backend console window for status")

    def start_frontend(self) -> None:
        """
        Start frontend service with visible output in new window.
        """
        print()
        print("Starting frontend in new console window...")
        print("The frontend console will show Vite dev server logs.")
        print()

        import platform
        if platform.system() == "Windows":
            # Start frontend in new visible console window
            subprocess.Popen(
                ["cmd", "/c", "start", "cmd", "/k", "npm", "run", "dev"],
                cwd=self.install_dir / "frontend",
                shell=True
            )
        else:
            # For Linux/Mac
            subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=self.install_dir / "frontend"
            )

        print("[OK] Frontend starting on http://localhost:7274")
        print("    Check the frontend console window for status")

    def wait_for_services(self, timeout: int = 30) -> bool:
        """
        Wait for backend and frontend to be ready.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if both services are ready, False if timeout
        """
        import time
        import socket

        def check_port(port: int) -> bool:
            """Check if a port is open."""
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    return True
            except (socket.timeout, ConnectionRefusedError, OSError):
                return False

        backend_ready = False
        frontend_ready = False
        start_time = time.time()

        print("Waiting for backend (port 7272)...", end="", flush=True)
        while time.time() - start_time < timeout:
            if check_port(7272):
                backend_ready = True
                print(" Ready!")
                break
            print(".", end="", flush=True)
            time.sleep(1)

        if not backend_ready:
            print(" Timeout!")
            return False

        print("Waiting for frontend (port 7274)...", end="", flush=True)
        while time.time() - start_time < timeout:
            if check_port(7274):
                frontend_ready = True
                print(" Ready!")
                break
            print(".", end="", flush=True)
            time.sleep(1)

        if not frontend_ready:
            print(" Timeout!")
            return False

        return True

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
