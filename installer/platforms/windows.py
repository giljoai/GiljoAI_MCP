"""
Windows platform handler implementation.

Handles Windows-specific installation operations including:
- Virtual environment path resolution (Scripts/)
- PostgreSQL discovery in Program Files
- Desktop shortcut creation (.lnk files)
- npm command execution with shell=True
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Any
import sys
import platform

from colorama import Fore, Style

from .base import PlatformHandler


class WindowsPlatformHandler(PlatformHandler):
    """
    Windows-specific platform handler.

    Key Windows behaviors:
    - venv executables in Scripts/ directory
    - PostgreSQL in C:\\Program Files\\PostgreSQL\\
    - Desktop shortcuts via win32com (.lnk files)
    - npm requires shell=True (batch file)
    """

    @property
    def platform_name(self) -> str:
        """Return 'Windows'"""
        return "Windows"

    def get_venv_python(self, venv_dir: Path) -> Path:
        """
        Get Windows Python executable path.

        Args:
            venv_dir: Virtual environment directory

        Returns:
            Path to venv/Scripts/python.exe
        """
        return venv_dir / "Scripts" / "python.exe"

    def get_venv_pip(self, venv_dir: Path) -> Path:
        """
        Get Windows pip executable path.

        Args:
            venv_dir: Virtual environment directory

        Returns:
            Path to venv/Scripts/pip.exe
        """
        return venv_dir / "Scripts" / "pip.exe"

    def get_postgresql_scan_paths(self) -> List[Path]:
        """
        Get Windows PostgreSQL scan paths.

        Scans:
        - C:\\Program Files\\PostgreSQL\\*\\bin\\psql.exe
        - C:\\Program Files (x86)\\PostgreSQL\\*\\bin\\psql.exe

        Returns:
            List of potential psql.exe paths (sorted by version, newest first)
        """
        paths = []

        program_files_locations = [
            Path("C:/Program Files/PostgreSQL"),
            Path("C:/Program Files (x86)/PostgreSQL")
        ]

        for base in program_files_locations:
            if base.exists():
                # Sort versions in reverse order (newest first)
                for version_dir in sorted(base.glob("*"), reverse=True):
                    if version_dir.is_dir():
                        psql_path = version_dir / "bin" / "psql.exe"
                        paths.append(psql_path)

        return paths

    def get_postgresql_install_guide(self, recommended_version: int = 18) -> str:
        """
        Get Windows PostgreSQL installation guide.

        Args:
            recommended_version: Recommended version (default: 18)

        Returns:
            Multi-line installation instructions
        """
        return f"""
{Fore.CYAN}Windows PostgreSQL Installation:{Style.RESET_ALL}

  1. Download PostgreSQL {recommended_version} from:
     https://www.postgresql.org/download/windows/

  2. Run the installer as Administrator

  3. During installation:
     • Remember the 'postgres' user password
     • Accept default port (5432)
     • Install to default location (C:\\Program Files\\PostgreSQL\\{recommended_version})

  4. After installation, re-run this installer

{Fore.YELLOW}Important:{Style.RESET_ALL} You will need the postgres password you set during installation.
"""

    def supports_desktop_shortcuts(self) -> bool:
        """Windows supports desktop shortcuts"""
        return True

    def create_desktop_shortcuts(self, install_dir: Path, venv_dir: Path) -> Dict[str, Any]:
        """
        Create Windows desktop shortcuts.

        Creates .lnk files using win32com if available,
        falls back to .bat files if win32com not installed.

        Args:
            install_dir: Installation directory
            venv_dir: Virtual environment directory

        Returns:
            Result dictionary with success status and created shortcuts
        """
        try:
            # Try win32com method first (proper .lnk files)
            try:
                import win32com.client

                result = self._create_shortcuts_win32com(install_dir, venv_dir)
                return result

            except ImportError:
                # Fallback to batch file shortcuts
                result = self._create_shortcuts_batch(install_dir, venv_dir)
                return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to create shortcuts: {e}'
            }

    def _create_shortcuts_win32com(self, install_dir: Path, venv_dir: Path) -> Dict[str, Any]:
        """
        Create .lnk shortcuts using win32com.

        Args:
            install_dir: Installation directory
            venv_dir: Virtual environment directory

        Returns:
            Result dictionary
        """
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = Path(shell.SpecialFolders("Desktop"))

        shortcuts_created = []

        # Main application shortcut
        shortcut_path = desktop / "GiljoAI MCP.lnk"
        shortcut = shell.CreateShortcut(str(shortcut_path))
        shortcut.TargetPath = str(venv_dir / "Scripts" / "python.exe")
        shortcut.Arguments = str(install_dir / "startup.py")
        shortcut.WorkingDirectory = str(install_dir)

        # Try to use favicon as icon
        favicon_path = install_dir / "frontend" / "public" / "favicon.ico"
        if favicon_path.exists():
            shortcut.IconLocation = str(favicon_path)

        shortcut.Description = "Launch GiljoAI MCP Orchestrator"
        shortcut.save()

        shortcuts_created.append(str(shortcut_path))

        # Dashboard-only shortcut
        dashboard_shortcut_path = desktop / "GiljoAI Dashboard.lnk"
        dashboard_shortcut = shell.CreateShortcut(str(dashboard_shortcut_path))
        dashboard_shortcut.TargetPath = str(venv_dir / "Scripts" / "python.exe")
        dashboard_shortcut.Arguments = f"{install_dir / 'startup.py'} --dashboard-only"
        dashboard_shortcut.WorkingDirectory = str(install_dir)

        if favicon_path.exists():
            dashboard_shortcut.IconLocation = str(favicon_path)

        dashboard_shortcut.Description = "Launch GiljoAI Dashboard Only"
        dashboard_shortcut.save()

        shortcuts_created.append(str(dashboard_shortcut_path))

        return {
            'success': True,
            'method': 'win32com',
            'shortcuts_created': shortcuts_created,
            'message': f'Created {len(shortcuts_created)} desktop shortcuts'
        }

    def _create_shortcuts_batch(self, install_dir: Path, venv_dir: Path) -> Dict[str, Any]:
        """
        Create .bat file shortcuts as fallback.

        Args:
            install_dir: Installation directory
            venv_dir: Virtual environment directory

        Returns:
            Result dictionary
        """
        desktop = Path.home() / "Desktop"
        shortcuts_created = []

        # Main application batch file
        main_bat = desktop / "GiljoAI MCP.bat"
        with open(main_bat, 'w') as f:
            f.write('@echo off\n')
            f.write(f'cd /d "{install_dir}"\n')
            f.write(f'"{venv_dir / "Scripts" / "python.exe"}" startup.py\n')
            f.write('pause\n')

        shortcuts_created.append(str(main_bat))

        # Dashboard-only batch file
        dashboard_bat = desktop / "GiljoAI Dashboard.bat"
        with open(dashboard_bat, 'w') as f:
            f.write('@echo off\n')
            f.write(f'cd /d "{install_dir}"\n')
            f.write(f'"{venv_dir / "Scripts" / "python.exe"}" startup.py --dashboard-only\n')
            f.write('pause\n')

        shortcuts_created.append(str(dashboard_bat))

        return {
            'success': True,
            'method': 'batch',
            'shortcuts_created': shortcuts_created,
            'message': f'Created {len(shortcuts_created)} batch file shortcuts (win32com not available)'
        }

    def run_npm_command(
        self,
        cmd: List[str],
        cwd: Path,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Run npm command with Windows-specific shell handling.

        CRITICAL: Windows MUST use shell=True because npm is a batch file.

        Args:
            cmd: Command list (e.g., ['npm', 'install'])
            cwd: Working directory
            timeout: Timeout in seconds

        Returns:
            Result dictionary with success status and output
        """
        try:
            # Windows MUST use shell=True for npm (batch file)
            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                shell=True,  # CRITICAL for Windows
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Command timed out',
                'timeout': timeout
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_network_ips(self) -> List[str]:
        """
        Get non-localhost IPv4 addresses on Windows.

        Returns:
            List of IPv4 address strings
        """
        try:
            import psutil

            ips = []
            for interface_name, addresses in psutil.net_if_addrs().items():
                for addr in addresses:
                    if addr.family == 2:  # AF_INET (IPv4)
                        ip = addr.address
                        # Filter out localhost and link-local
                        if not ip.startswith("127.") and not ip.startswith("169.254."):
                            ips.append(ip)

            return sorted(set(ips))  # Deduplicate and sort

        except ImportError:
            # Fallback if psutil not available
            return []

        except Exception:
            # Graceful failure
            return []

    def welcome_screen(self) -> None:
        """
        Print Windows-specific welcome screen.
        """
        separator = "=" * 70

        print(f"\n{Fore.YELLOW}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}  GiljoAI MCP - Windows Installer v3.0{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")

        print(f"{Fore.CYAN}Welcome to GiljoAI MCP!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}This installer will set up your coding orchestrator.{Style.RESET_ALL}\n")

        print(f"{Fore.WHITE}What will be installed:{Style.RESET_ALL}")
        print(f"  • PostgreSQL database (giljo_mcp)")
        print(f"  • Python dependencies (FastAPI, SQLAlchemy, etc.)")
        print(f"  • Configuration files (.env, config.yaml)")
        print(f"  • API server + Frontend dashboard")
        print(f"  • MCP server integration\n")

        # Windows platform info
        windows_version = platform.win32_ver()[0] if hasattr(platform, 'win32_ver') else platform.release()
        print(f"{Fore.YELLOW}Platform: Windows {windows_version}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}{Style.RESET_ALL}\n")

    def get_platform_specific_warnings(self) -> List[str]:
        """
        Get Windows-specific warnings.

        Windows Firewall will typically prompt the user automatically,
        so no explicit warnings needed.

        Returns:
            Empty list (no warnings needed)
        """
        return []
