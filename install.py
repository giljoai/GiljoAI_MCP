#!/usr/bin/env python3
"""
GiljoAI MCP v3.0 - Unified Installer

Single-file installer that replaces the entire installer/cli/ system.
Handles cross-platform PostgreSQL discovery, dependency management,
database setup, config generation, and service launching.

Usage:
    python install.py              # Interactive installation
    python install.py --headless   # Non-interactive (CI/CD)
    python install.py --help       # Show help

Architecture:
    1. Welcome screen with yellow branding
    2. Check Python version (3.10+)
    3. Discover PostgreSQL (cross-platform)
    4. Install dependencies (venv + requirements.txt)
    5. Setup database (create DB, roles, migrations)
    6. Generate configs (.env + config.yaml v3.0)
    7. Launch services (API + Frontend)
    8. Open browser (http://localhost:7274)

Cross-platform: Windows, Linux, macOS
"""

import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import click
from colorama import Fore, Style, init


# Initialize colorama for cross-platform colored output
init(autoreset=True)


# Constants
MIN_PYTHON_VERSION = (3, 10)
MIN_POSTGRESQL_VERSION = 14
RECOMMENDED_POSTGRESQL_VERSION = 18
DEFAULT_API_PORT = 7272
DEFAULT_FRONTEND_PORT = 7274
POSTGRESQL_DOWNLOAD_URL = "https://www.postgresql.org/download/"


class UnifiedInstaller:
    """
    Unified installer for GiljoAI MCP v3.0

    Handles complete installation workflow:
    - PostgreSQL discovery
    - Dependency management
    - Database setup
    - Configuration generation
    - Service launching
    """

    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        """
        Initialize installer with settings

        Args:
            settings: Installation settings (defaults applied if not provided)
        """
        self.settings = settings or {}

        # Apply defaults
        self.settings.setdefault('install_dir', str(Path.cwd()))
        self.settings.setdefault('pg_host', 'localhost')
        self.settings.setdefault('pg_port', 5432)
        self.settings.setdefault('api_port', DEFAULT_API_PORT)
        self.settings.setdefault('dashboard_port', DEFAULT_FRONTEND_PORT)
        self.settings.setdefault('bind', '0.0.0.0')  # v3.0: Always bind all interfaces

        # Paths
        self.install_dir = Path(self.settings['install_dir'])
        self.venv_dir = self.install_dir / 'venv'
        self.requirements_file = self.install_dir / 'requirements.txt'

        # State
        self.postgresql_found = False
        self.psql_path: Optional[Path] = None
        self.venv_created = False
        self.database_credentials: Optional[Dict[str, str]] = None

    def run(self) -> Dict[str, Any]:
        """
        Execute complete installation workflow

        Returns:
            Result dictionary with success status and details
        """
        result = {'success': False, 'steps': []}

        try:
            # Step 1: Welcome screen
            self.welcome_screen()
            result['steps'].append('welcome_shown')

            # Step 2: Check Python version
            self._print_header("Checking Python Version")
            if not self.check_python_version():
                self._print_error("Python version check failed")
                result['error'] = "Python 3.10+ required"
                return result
            result['steps'].append('python_verified')

            # Step 3: Discover PostgreSQL
            self._print_header("Discovering PostgreSQL")
            pg_result = self.discover_postgresql()
            if not pg_result['found']:
                self._print_error("PostgreSQL not found")
                self._print_postgresql_install_guide()
                result['error'] = "PostgreSQL 18 required"
                return result
            result['steps'].append('postgresql_found')

            # Step 4: Install dependencies
            self._print_header("Installing Dependencies")
            dep_result = self.install_dependencies()
            if not dep_result['success']:
                self._print_error("Dependency installation failed")
                result['error'] = dep_result.get('error', 'Unknown error')
                return result
            result['steps'].append('dependencies_installed')

            # Step 5: Setup database
            self._print_header("Setting Up Database")
            db_result = self.setup_database()
            if not db_result['success']:
                self._print_error("Database setup failed")
                result['error'] = '; '.join(db_result.get('errors', ['Unknown error']))
                return result
            self.database_credentials = db_result.get('credentials', {})
            result['steps'].append('database_created')

            # Step 6: Generate configs
            self._print_header("Generating Configuration Files")
            config_result = self.generate_configs()
            if not config_result['success']:
                self._print_error("Configuration generation failed")
                result['error'] = '; '.join(config_result.get('errors', ['Unknown error']))
                return result
            result['steps'].append('configs_generated')

            # Step 7: Launch services
            self._print_header("Launching Services")
            launch_result = self.launch_services()
            if not launch_result['success']:
                self._print_error("Service launch failed")
                result['error'] = launch_result.get('error', 'Unknown error')
                return result
            result['steps'].append('services_launched')
            result['api_pid'] = launch_result.get('api_pid')
            result['frontend_pid'] = launch_result.get('frontend_pid')

            # Step 8: Open browser
            self._print_header("Opening Dashboard")
            self.open_browser()
            result['steps'].append('browser_opened')

            # Success
            result['success'] = True
            self._print_success_summary()

            return result

        except KeyboardInterrupt:
            self._print_warning("\nInstallation cancelled by user")
            result['error'] = 'User cancelled'
            return result

        except Exception as e:
            self._print_error(f"Installation failed: {e}")
            result['error'] = str(e)
            return result

    def welcome_screen(self) -> None:
        """Display welcome screen with yellow branding"""
        separator = "=" * 70

        print(f"\n{Fore.YELLOW}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}  GiljoAI MCP - Unified Installer v3.0{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")

        print(f"{Fore.CYAN}Welcome to GiljoAI MCP!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}This installer will set up your coding orchestrator.{Style.RESET_ALL}\n")

        print(f"{Fore.WHITE}What will be installed:{Style.RESET_ALL}")
        print(f"  • PostgreSQL database (giljo_mcp)")
        print(f"  • Python dependencies (FastAPI, SQLAlchemy, etc.)")
        print(f"  • Configuration files (.env, config.yaml)")
        print(f"  • API server + Frontend dashboard")
        print(f"  • MCP server integration\n")

        print(f"{Fore.YELLOW}Platform: {platform.system()} {platform.release()}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}{Style.RESET_ALL}\n")

    def check_python_version(self) -> bool:
        """
        Check if Python version meets requirements

        Returns:
            True if version is compatible, False otherwise
        """
        current_version = sys.version_info
        is_compatible = current_version >= MIN_PYTHON_VERSION

        # Handle both sys.version_info (named tuple) and regular tuple
        if hasattr(current_version, 'major'):
            version_str = f"{current_version.major}.{current_version.minor}.{current_version.micro}"
        else:
            version_str = f"{current_version[0]}.{current_version[1]}.{current_version[2]}"

        if is_compatible:
            self._print_success(f"Python {version_str} detected")
        else:
            required_str = f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}"
            self._print_error(f"Python {version_str} detected, but {required_str}+ required")

        return is_compatible

    def discover_postgresql(self) -> Dict[str, Any]:
        """
        Discover PostgreSQL installation across platforms

        Checks:
        1. psql in PATH
        2. Platform-specific common locations

        Returns:
            Discovery result with found status and paths
        """
        result = {
            'found': False,
            'psql_path': None,
            'scanned_paths': []
        }

        # Method 1: Check PATH
        self._print_info("Checking PATH for psql...")
        psql_path = shutil.which('psql')

        if psql_path:
            self._print_success(f"PostgreSQL detected in PATH: {psql_path}")
            result['found'] = True
            result['psql_path'] = psql_path
            self.psql_path = Path(psql_path)
            self.postgresql_found = True
            return result

        # Method 2: Scan platform-specific locations
        self._print_info("Scanning common installation locations...")
        scan_paths = self._get_postgresql_scan_paths()

        for path in scan_paths:
            result['scanned_paths'].append(str(path))

            if path.exists():
                self._print_success(f"PostgreSQL detected: {path}")
                result['found'] = True
                result['psql_path'] = str(path)
                self.psql_path = path
                self.postgresql_found = True

                # Add to PATH for session
                bin_dir = path.parent
                os.environ['PATH'] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"

                return result

        # Not found
        self._print_warning("PostgreSQL not found in common locations")
        return result

    def _get_postgresql_scan_paths(self) -> List[Path]:
        """
        Get platform-specific PostgreSQL scan paths

        Returns:
            List of paths to check for psql
        """
        system = platform.system()
        paths = []

        if system == "Windows":
            # Windows: C:\Program Files\PostgreSQL\*\bin\psql.exe
            program_files = [
                Path("C:/Program Files/PostgreSQL"),
                Path("C:/Program Files (x86)/PostgreSQL")
            ]

            for base in program_files:
                if base.exists():
                    for version_dir in sorted(base.glob("*"), reverse=True):
                        psql_path = version_dir / "bin" / "psql.exe"
                        paths.append(psql_path)

        elif system == "Darwin":  # macOS
            # Homebrew installations
            paths.extend([
                Path("/usr/local/bin/psql"),
                Path("/opt/homebrew/bin/psql"),
                Path("/usr/local/opt/postgresql@18/bin/psql"),
                Path("/usr/local/opt/postgresql@17/bin/psql"),
                Path("/usr/local/opt/postgresql/bin/psql")
            ])

            # Postgres.app
            paths.append(Path("/Applications/Postgres.app/Contents/Versions/latest/bin/psql"))

        elif system == "Linux":
            # Standard system paths
            paths.extend([
                Path("/usr/bin/psql"),
                Path("/usr/local/bin/psql")
            ])

            # Version-specific paths
            pg_lib = Path("/usr/lib/postgresql")
            if pg_lib.exists():
                for version_dir in sorted(pg_lib.glob("*"), reverse=True):
                    psql_path = version_dir / "bin" / "psql"
                    paths.append(psql_path)

        return paths

    def install_dependencies(self) -> Dict[str, Any]:
        """
        Install Python dependencies

        Steps:
        1. Create virtual environment (if not exists)
        2. Install requirements from requirements.txt

        Returns:
            Installation result with success status
        """
        result = {'success': False}

        try:
            # Step 1: Create venv if needed
            if self.venv_dir.exists():
                self._print_info(f"Virtual environment already exists: {self.venv_dir}")
                result['venv_existed'] = True
            else:
                self._print_info(f"Creating virtual environment: {self.venv_dir}")
                subprocess.run(
                    [sys.executable, '-m', 'venv', str(self.venv_dir)],
                    check=True,
                    capture_output=True
                )
                self._print_success("Virtual environment created")
                result['venv_created'] = True
                self.venv_created = True

            # Determine pip executable
            if platform.system() == "Windows":
                pip_executable = self.venv_dir / 'Scripts' / 'pip.exe'
            else:
                pip_executable = self.venv_dir / 'bin' / 'pip'

            # Step 2: Install requirements
            if not self.requirements_file.exists():
                self._print_error(f"requirements.txt not found: {self.requirements_file}")
                result['error'] = "requirements.txt missing"
                return result

            self._print_info("Installing Python packages (this may take 2-3 minutes)...")

            subprocess.run(
                [str(pip_executable), 'install', '-r', str(self.requirements_file)],
                check=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            self._print_success("Dependencies installed successfully")
            result['success'] = True
            return result

        except subprocess.TimeoutExpired:
            self._print_error("Installation timed out (exceeded 5 minutes)")
            result['error'] = "Timeout"
            return result

        except subprocess.CalledProcessError as e:
            self._print_error(f"pip install failed: {e}")
            result['error'] = str(e)
            return result

        except Exception as e:
            self._print_error(f"Dependency installation failed: {e}")
            result['error'] = str(e)
            return result

    def setup_database(self) -> Dict[str, Any]:
        """
        Setup PostgreSQL database using DatabaseInstaller

        Returns:
            Database setup result from DatabaseInstaller
        """
        try:
            # Import DatabaseInstaller from existing module
            from installer.core.database import DatabaseInstaller

            # Prepare settings for DatabaseInstaller
            db_settings = {
                'pg_host': self.settings.get('pg_host', 'localhost'),
                'pg_port': self.settings.get('pg_port', 5432),
                'pg_password': self.settings.get('pg_password', '4010'),
                'pg_user': self.settings.get('pg_user', 'postgres')
            }

            # Create installer instance
            db_installer = DatabaseInstaller(settings=db_settings)

            # Run database setup
            self._print_info("Creating database and roles...")
            result = db_installer.setup()

            if result['success']:
                self._print_success("Database created successfully")

                # Run migrations if available
                self._print_info("Running database migrations...")
                migration_result = db_installer.run_migrations()

                if migration_result['success']:
                    self._print_success("Migrations completed")
                elif migration_result.get('warnings'):
                    self._print_warning("Migrations skipped: " + migration_result['warnings'][0])
            else:
                self._print_error("Database setup failed")
                for error in result.get('errors', []):
                    self._print_error(f"  • {error}")

            return result

        except Exception as e:
            self._print_error(f"Database setup failed: {e}")
            return {
                'success': False,
                'errors': [str(e)]
            }

    def generate_configs(self) -> Dict[str, Any]:
        """
        Generate configuration files (.env and config.yaml)

        Uses ConfigManager with v3.0 architecture (no mode field)

        Returns:
            Configuration generation result
        """
        try:
            # Import ConfigManager from existing module
            from installer.core.config import ConfigManager

            # Prepare settings for ConfigManager (v3.0: NO mode field)
            config_settings = {
                'pg_host': self.settings.get('pg_host', 'localhost'),
                'pg_port': self.settings.get('pg_port', 5432),
                'api_port': self.settings.get('api_port', DEFAULT_API_PORT),
                'dashboard_port': self.settings.get('dashboard_port', DEFAULT_FRONTEND_PORT),
                'install_dir': str(self.install_dir),
                'owner_password': self.database_credentials.get('owner_password') if self.database_credentials else '4010',
                'user_password': self.database_credentials.get('user_password') if self.database_credentials else '4010',
                'bind': '0.0.0.0',  # v3.0: Always bind all interfaces
                # NO 'mode' field - v3.0 unified architecture
            }

            # Create config manager
            config_manager = ConfigManager(settings=config_settings)

            # Generate all configs
            self._print_info("Generating .env and config.yaml...")
            result = config_manager.generate_all()

            if result['success']:
                self._print_success("Configuration files generated")
            else:
                self._print_error("Configuration generation failed")
                for error in result.get('errors', []):
                    self._print_error(f"  • {error}")

            return result

        except Exception as e:
            self._print_error(f"Config generation failed: {e}")
            return {
                'success': False,
                'errors': [str(e)]
            }

    def launch_services(self) -> Dict[str, Any]:
        """
        Launch API and Frontend services

        Returns:
            Launch result with process IDs
        """
        result = {'success': False}

        try:
            # Check port availability
            api_port = self.settings.get('api_port', DEFAULT_API_PORT)
            frontend_port = self.settings.get('dashboard_port', DEFAULT_FRONTEND_PORT)

            if not self._is_port_available(api_port):
                self._print_warning(f"Port {api_port} is in use - finding alternative...")
                api_port = self._find_available_port(api_port)
                if not api_port:
                    result['error'] = "No available port for API"
                    return result
                self._print_info(f"Using alternative API port: {api_port}")

            if not self._is_port_available(frontend_port):
                self._print_warning(f"Port {frontend_port} is in use - finding alternative...")
                frontend_port = self._find_available_port(frontend_port)
                if not frontend_port:
                    self._print_warning("No available port for frontend - skipping")
                    frontend_port = None

            # Determine Python executable
            if platform.system() == "Windows":
                python_executable = self.venv_dir / 'Scripts' / 'python.exe'
            else:
                python_executable = self.venv_dir / 'bin' / 'python'

            # Launch API server
            api_script = self.install_dir / 'api' / 'run_api.py'

            if not api_script.exists():
                self._print_error(f"API script not found: {api_script}")
                result['error'] = "API script missing"
                return result

            self._print_info("Starting API server...")
            api_process = subprocess.Popen(
                [str(python_executable), str(api_script)],
                cwd=str(self.install_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            self._print_success(f"API server started (PID: {api_process.pid})")
            result['api_pid'] = api_process.pid

            # Launch frontend (if npm available)
            frontend_process = None
            if shutil.which('npm'):
                frontend_dir = self.install_dir / 'frontend'

                if frontend_dir.exists():
                    # Check if node_modules exists
                    if not (frontend_dir / 'node_modules').exists():
                        self._print_info("Installing frontend dependencies...")
                        subprocess.run(
                            ['npm', 'install'],
                            cwd=str(frontend_dir),
                            check=True,
                            capture_output=True
                        )

                    self._print_info("Starting frontend server...")
                    frontend_process = subprocess.Popen(
                        ['npm', 'run', 'dev'],
                        cwd=str(frontend_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )

                    self._print_success(f"Frontend server started (PID: {frontend_process.pid})")
                    result['frontend_pid'] = frontend_process.pid
                else:
                    self._print_warning("Frontend directory not found")
            else:
                self._print_warning("npm not found - frontend not started")

            # Wait for services to initialize
            self._print_info("Waiting for services to initialize...")
            time.sleep(3)

            result['success'] = True
            return result

        except Exception as e:
            self._print_error(f"Service launch failed: {e}")
            result['error'] = str(e)
            return result

    def open_browser(self) -> None:
        """Open browser to dashboard"""
        try:
            frontend_port = self.settings.get('dashboard_port', DEFAULT_FRONTEND_PORT)
            url = f"http://localhost:{frontend_port}"

            self._print_info(f"Opening browser to {url}...")
            time.sleep(2)  # Brief delay for services to fully start

            webbrowser.open(url)
            self._print_success("Browser opened")

        except Exception as e:
            self._print_warning(f"Could not open browser: {e}")
            self._print_info(f"Please manually open: http://localhost:{frontend_port}")

    def _print_success_summary(self) -> None:
        """Print installation success summary"""
        separator = "=" * 70

        print(f"\n{Fore.GREEN}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{Style.BRIGHT}  Installation Complete!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")

        api_port = self.settings.get('api_port', DEFAULT_API_PORT)
        frontend_port = self.settings.get('dashboard_port', DEFAULT_FRONTEND_PORT)

        print(f"{Fore.CYAN}Services Running:{Style.RESET_ALL}")
        print(f"  • API Server:  http://localhost:{api_port}")
        print(f"  • API Docs:    http://localhost:{api_port}/docs")
        print(f"  • Dashboard:   http://localhost:{frontend_port}")
        print()

        print(f"{Fore.YELLOW}Next Steps:{Style.RESET_ALL}")
        print(f"  1. Open the dashboard at http://localhost:{frontend_port}")
        print(f"  2. Create your first project")
        print(f"  3. Start orchestrating your AI coding team!")
        print()

        print(f"{Fore.WHITE}Press Ctrl+C to stop services{Style.RESET_ALL}\n")

    def _print_postgresql_install_guide(self) -> None:
        """Print platform-specific PostgreSQL installation guide"""
        system = platform.system()

        print(f"\n{Fore.YELLOW}PostgreSQL Installation Required{Style.RESET_ALL}\n")

        if system == "Windows":
            print(f"{Fore.CYAN}Windows Installation:{Style.RESET_ALL}")
            print(f"  1. Download PostgreSQL 18 from:")
            print(f"     {POSTGRESQL_DOWNLOAD_URL}")
            print(f"  2. Run installer as Administrator")
            print(f"  3. Remember the 'postgres' user password")
            print(f"  4. Re-run this installer")

        elif system == "Darwin":
            print(f"{Fore.CYAN}macOS Installation:{Style.RESET_ALL}")
            print(f"  Option 1 - Homebrew (recommended):")
            print(f"     brew install postgresql@18")
            print(f"     brew services start postgresql@18")
            print(f"  Option 2 - Official installer:")
            print(f"     Download from: {POSTGRESQL_DOWNLOAD_URL}")

        else:  # Linux
            print(f"{Fore.CYAN}Linux Installation:{Style.RESET_ALL}")
            print(f"  Ubuntu/Debian:")
            print(f"     sudo apt-get update")
            print(f"     sudo apt-get install postgresql-18")
            print(f"  RHEL/CentOS/Fedora:")
            print(f"     sudo dnf install postgresql18-server")
            print(f"  Arch:")
            print(f"     sudo pacman -S postgresql")

        print()

    def _is_port_available(self, port: int, host: str = '127.0.0.1') -> bool:
        """Check if port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0
        except Exception:
            return False

    def _find_available_port(self, start_port: int, max_attempts: int = 10) -> Optional[int]:
        """Find available port starting from start_port"""
        for offset in range(max_attempts):
            port = start_port + offset
            if self._is_port_available(port):
                return port
        return None

    # Output helpers
    def _print_header(self, text: str) -> None:
        """Print section header"""
        separator = "=" * 70
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}  {text}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")

    def _print_success(self, text: str) -> None:
        """Print success message"""
        print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} {text}")

    def _print_error(self, text: str) -> None:
        """Print error message"""
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {text}")

    def _print_warning(self, text: str) -> None:
        """Print warning message"""
        print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {text}")

    def _print_info(self, text: str) -> None:
        """Print info message"""
        print(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} {text}")


@click.command()
@click.option('--headless', is_flag=True, help='Non-interactive mode (use defaults)')
@click.option('--pg-password', default='4010', help='PostgreSQL admin password')
@click.option('--api-port', default=DEFAULT_API_PORT, type=int, help='API server port')
@click.option('--frontend-port', default=DEFAULT_FRONTEND_PORT, type=int, help='Frontend port')
def main(headless: bool, pg_password: str, api_port: int, frontend_port: int) -> None:
    """
    GiljoAI MCP v3.0 - Unified Installer

    Single-command installation for all platforms.
    """
    try:
        # Prepare settings
        settings = {
            'install_dir': str(Path.cwd()),
            'pg_password': pg_password,
            'api_port': api_port,
            'dashboard_port': frontend_port,
            'headless': headless
        }

        # Create installer
        installer = UnifiedInstaller(settings=settings)

        # Run installation
        result = installer.run()

        # Exit with appropriate code
        sys.exit(0 if result['success'] else 1)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Installation cancelled{Style.RESET_ALL}")
        sys.exit(0)

    except Exception as e:
        print(f"\n{Fore.RED}Installation failed: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == '__main__':
    main()
