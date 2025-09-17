#!/usr/bin/env python3
"""
Platform detection and system information utilities for GiljoAI MCP
Provides comprehensive platform detection including package managers, Python environments, etc.
"""

import os
import platform
import shutil
import subprocess
import sys
from typing import Optional


class PlatformDetector:
    """Enhanced platform detection with package manager support"""

    def __init__(self):
        self.system = platform.system()
        self.is_windows = self.system == "Windows"
        self.is_mac = self.system == "Darwin"
        self.is_linux = self.system == "Linux"

    def get_full_info(self) -> dict:
        """Get comprehensive platform information"""
        info = {
            # Basic system info
            "system": self.system,
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": platform.architecture(),
            "node": platform.node(),

            # OS flags
            "is_windows": self.is_windows,
            "is_mac": self.is_mac,
            "is_linux": self.is_linux,

            # Python environment
            "python": self._get_python_info(),

            # Package managers
            "package_managers": self._detect_package_managers(),

            # Virtual environment
            "virtual_env": self._detect_virtual_env(),

            # Additional capabilities
            "capabilities": self._detect_capabilities(),

            # System resources
            "resources": self._get_system_resources()
        }

        # Linux-specific
        if self.is_linux:
            info["linux_distro"] = self._get_linux_distro()

        # Windows-specific
        if self.is_windows:
            info["windows"] = self._get_windows_info()

        # macOS-specific
        if self.is_mac:
            info["macos"] = self._get_macos_info()

        return info

    def _get_python_info(self) -> dict:
        """Get Python environment details"""
        return {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler(),
            "executable": sys.executable,
            "prefix": sys.prefix,
            "base_prefix": getattr(sys, "base_prefix", sys.prefix),
            "path": sys.path[:5],  # First 5 paths
            "version_info": {
                "major": sys.version_info.major,
                "minor": sys.version_info.minor,
                "micro": sys.version_info.micro,
                "releaselevel": sys.version_info.releaselevel
            },
            "pip_version": self._get_pip_version(),
            "installed_packages": self._get_key_packages()
        }

    def _get_pip_version(self) -> Optional[str]:
        """Get pip version"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                check=False, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Format: "pip X.Y.Z from /path/to/pip (python X.Y)"
                return result.stdout.split()[1]
        except:
            pass
        return None

    def _get_key_packages(self) -> list[str]:
        """Get list of key installed packages"""
        key_packages = [
            "fastmcp", "fastapi", "sqlalchemy", "pydantic",
            "rich", "httpx", "websockets", "psycopg2",
            "alembic", "pytest", "black", "ruff"
        ]

        installed = []
        try:
            import importlib.metadata
            for pkg in key_packages:
                try:
                    version = importlib.metadata.version(pkg)
                    installed.append(f"{pkg}=={version}")
                except:
                    pass
        except ImportError:
            # Fallback for older Python
            try:
                import pkg_resources
                for pkg in key_packages:
                    try:
                        version = pkg_resources.get_distribution(pkg).version
                        installed.append(f"{pkg}=={version}")
                    except:
                        pass
            except:
                pass

        return installed

    def _detect_package_managers(self) -> dict[str, dict]:
        """Detect available package managers"""
        managers = {}

        if self.is_windows:
            # Check for Chocolatey
            if shutil.which("choco"):
                managers["chocolatey"] = {
                    "available": True,
                    "command": "choco",
                    "version": self._get_command_version("choco", "--version")
                }

            # Check for Scoop
            if shutil.which("scoop"):
                managers["scoop"] = {
                    "available": True,
                    "command": "scoop",
                    "version": self._get_command_version("scoop", "--version")
                }

            # Check for winget
            if shutil.which("winget"):
                managers["winget"] = {
                    "available": True,
                    "command": "winget",
                    "version": self._get_command_version("winget", "--version")
                }

        elif self.is_mac:
            # Check for Homebrew
            if shutil.which("brew"):
                managers["homebrew"] = {
                    "available": True,
                    "command": "brew",
                    "version": self._get_command_version("brew", "--version")
                }

            # Check for MacPorts
            if shutil.which("port"):
                managers["macports"] = {
                    "available": True,
                    "command": "port",
                    "version": self._get_command_version("port", "version")
                }

        elif self.is_linux:
            # Check for APT (Debian/Ubuntu)
            if shutil.which("apt"):
                managers["apt"] = {
                    "available": True,
                    "command": "apt",
                    "distro": "debian-based"
                }

            # Check for YUM (RHEL/CentOS/Fedora old)
            if shutil.which("yum"):
                managers["yum"] = {
                    "available": True,
                    "command": "yum",
                    "distro": "rhel-based"
                }

            # Check for DNF (Fedora new)
            if shutil.which("dnf"):
                managers["dnf"] = {
                    "available": True,
                    "command": "dnf",
                    "distro": "fedora"
                }

            # Check for Pacman (Arch)
            if shutil.which("pacman"):
                managers["pacman"] = {
                    "available": True,
                    "command": "pacman",
                    "distro": "arch-based"
                }

            # Check for Zypper (openSUSE)
            if shutil.which("zypper"):
                managers["zypper"] = {
                    "available": True,
                    "command": "zypper",
                    "distro": "opensuse"
                }

            # Check for Snap
            if shutil.which("snap"):
                managers["snap"] = {
                    "available": True,
                    "command": "snap",
                    "version": self._get_command_version("snap", "--version")
                }

            # Check for Flatpak
            if shutil.which("flatpak"):
                managers["flatpak"] = {
                    "available": True,
                    "command": "flatpak",
                    "version": self._get_command_version("flatpak", "--version")
                }

        # Python package managers
        if shutil.which("pip"):
            managers["pip"] = {
                "available": True,
                "command": "pip",
                "version": self._get_pip_version()
            }

        if shutil.which("conda"):
            managers["conda"] = {
                "available": True,
                "command": "conda",
                "version": self._get_command_version("conda", "--version")
            }

        if shutil.which("poetry"):
            managers["poetry"] = {
                "available": True,
                "command": "poetry",
                "version": self._get_command_version("poetry", "--version")
            }

        if shutil.which("pipenv"):
            managers["pipenv"] = {
                "available": True,
                "command": "pipenv",
                "version": self._get_command_version("pipenv", "--version")
            }

        return managers

    def _detect_virtual_env(self) -> dict:
        """Detect if running in a virtual environment"""
        info = {
            "active": False,
            "type": None,
            "path": None
        }

        # Check for virtualenv/venv
        if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix):
            info["active"] = True
            info["type"] = "venv"
            info["path"] = sys.prefix

        # Check for conda
        if os.environ.get("CONDA_DEFAULT_ENV"):
            info["active"] = True
            info["type"] = "conda"
            info["path"] = os.environ.get("CONDA_PREFIX")
            info["env_name"] = os.environ.get("CONDA_DEFAULT_ENV")

        # Check for pipenv
        if os.environ.get("PIPENV_ACTIVE"):
            info["active"] = True
            info["type"] = "pipenv"

        # Check for poetry
        if os.environ.get("POETRY_ACTIVE"):
            info["active"] = True
            info["type"] = "poetry"

        return info

    def _detect_capabilities(self) -> dict:
        """Detect system capabilities"""
        caps = {
            "docker": shutil.which("docker") is not None,
            "docker_compose": shutil.which("docker-compose") is not None,
            "git": shutil.which("git") is not None,
            "make": shutil.which("make") is not None,
            "gcc": shutil.which("gcc") is not None,
            "node": shutil.which("node") is not None,
            "npm": shutil.which("npm") is not None,
            "yarn": shutil.which("yarn") is not None,
            "postgresql": False,
            "mysql": False,
            "redis": False
        }

        # Check for PostgreSQL
        if shutil.which("psql") or shutil.which("postgres"):
            caps["postgresql"] = True
            caps["postgresql_version"] = self._get_command_version("psql", "--version")

        # Check for MySQL
        if shutil.which("mysql"):
            caps["mysql"] = True
            caps["mysql_version"] = self._get_command_version("mysql", "--version")

        # Check for Redis
        if shutil.which("redis-server"):
            caps["redis"] = True
            caps["redis_version"] = self._get_command_version("redis-server", "--version")

        # Windows specific checks
        if self.is_windows:
            caps["wsl"] = self._check_wsl()
            caps["powershell"] = shutil.which("powershell") is not None

        return caps

    def _check_wsl(self) -> bool:
        """Check if WSL is available on Windows"""
        if not self.is_windows:
            return False

        try:
            result = subprocess.run(
                ["wsl", "--list"],
                check=False, capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def _get_system_resources(self) -> dict:
        """Get system resource information"""
        resources = {}

        try:
            import psutil
            resources["cpu_count"] = psutil.cpu_count()
            resources["cpu_percent"] = psutil.cpu_percent(interval=1)

            mem = psutil.virtual_memory()
            resources["memory"] = {
                "total": mem.total,
                "available": mem.available,
                "percent": mem.percent
            }

            disk = psutil.disk_usage("/")
            resources["disk"] = {
                "total": disk.total,
                "free": disk.free,
                "percent": disk.percent
            }
        except ImportError:
            # Fallback if psutil not available
            import os
            resources["cpu_count"] = os.cpu_count()

        return resources

    def _get_linux_distro(self) -> dict:
        """Get Linux distribution information"""
        distro_info = {}

        # Try to read from /etc/os-release
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        distro_info[key.lower()] = value.strip('"')
        except:
            pass

        # Try lsb_release command
        if not distro_info and shutil.which("lsb_release"):
            try:
                result = subprocess.run(
                    ["lsb_release", "-a"],
                    check=False, capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            distro_info[key.strip().lower().replace(" ", "_")] = value.strip()
            except:
                pass

        return distro_info

    def _get_windows_info(self) -> dict:
        """Get Windows-specific information"""
        win_info = {}

        try:
            # Windows version
            win_info["edition"] = platform.win32_edition()

            # Check if running as admin
            import ctypes
            win_info["is_admin"] = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            pass

        return win_info

    def _get_macos_info(self) -> dict:
        """Get macOS-specific information"""
        mac_info = {}

        try:
            # macOS version
            result = subprocess.run(
                ["sw_vers"],
                check=False, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        mac_info[key.strip().lower().replace(" ", "_")] = value.strip()
        except:
            pass

        # Check for Xcode tools
        if shutil.which("xcode-select"):
            try:
                result = subprocess.run(
                    ["xcode-select", "--version"],
                    check=False, capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    mac_info["xcode_tools"] = True
            except:
                mac_info["xcode_tools"] = False

        return mac_info

    def _get_command_version(self, command: str, version_flag: str) -> Optional[str]:
        """Get version of a command"""
        try:
            result = subprocess.run(
                [command, version_flag],
                check=False, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                # Return first line, cleaned up
                return result.stdout.split("\n")[0].strip()
        except:
            pass
        return None

    def get_package_manager_commands(self, package: str) -> dict[str, str]:
        """Get install commands for a package across different package managers"""
        commands = {}
        managers = self._detect_package_managers()

        if "apt" in managers:
            commands["apt"] = f"sudo apt install {package}"

        if "yum" in managers:
            commands["yum"] = f"sudo yum install {package}"

        if "dnf" in managers:
            commands["dnf"] = f"sudo dnf install {package}"

        if "pacman" in managers:
            commands["pacman"] = f"sudo pacman -S {package}"

        if "zypper" in managers:
            commands["zypper"] = f"sudo zypper install {package}"

        if "homebrew" in managers:
            commands["brew"] = f"brew install {package}"

        if "macports" in managers:
            commands["port"] = f"sudo port install {package}"

        if "chocolatey" in managers:
            commands["choco"] = f"choco install {package}"

        if "scoop" in managers:
            commands["scoop"] = f"scoop install {package}"

        if "winget" in managers:
            commands["winget"] = f"winget install {package}"

        return commands


def detect_platform() -> dict:
    """Main function to detect platform"""
    detector = PlatformDetector()
    return detector.get_full_info()


def print_platform_info():
    """Print platform information in a readable format"""
    info = detect_platform()

    # Import rich for pretty printing
    try:
        from rich import print
        from rich.console import Console
        from rich.table import Table

        console = Console()

        console.print("\n[bold cyan]Platform Detection Report[/bold cyan]\n")

        # Basic system info
        table = Table(title="System Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("System", info["system"])
        table.add_row("Release", info["release"])
        table.add_row("Architecture", str(info["architecture"]))
        table.add_row("Python Version", info["python"]["version"])
        table.add_row("Python Executable", info["python"]["executable"])

        console.print(table)

        # Package managers
        if info["package_managers"]:
            console.print("\n[bold green]Available Package Managers:[/bold green]")
            for name, details in info["package_managers"].items():
                if details.get("available"):
                    version = details.get("version", "Unknown version")
                    console.print(f"  • {name}: {version}")

        # Virtual environment
        if info["virtual_env"]["active"]:
            console.print("\n[bold yellow]Virtual Environment:[/bold yellow]")
            console.print(f"  Type: {info['virtual_env']['type']}")
            console.print(f"  Path: {info['virtual_env']['path']}")

        # Capabilities
        console.print("\n[bold blue]System Capabilities:[/bold blue]")
        caps = info["capabilities"]
        for cap, available in caps.items():
            if isinstance(available, bool):
                status = "[green]✓[/green]" if available else "[red]✗[/red]"
                console.print(f"  {status} {cap}")

    except ImportError:
        # Fallback to regular print
        import json
        print(json.dumps(info, indent=2))


if __name__ == "__main__":
    print_platform_info()
