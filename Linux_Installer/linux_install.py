#!/usr/bin/env python3
"""
GiljoAI MCP v3.0 - Linux Installer

Single-file installer tailored for Linux environments. Handles PostgreSQL
discovery, dependency management, database setup, config generation, and
service launching using Linux-friendly defaults.

Usage:
    python linux_install.py              # Interactive installation
    python linux_install.py --headless   # Non-interactive (CI/CD)
    python linux_install.py --help       # Show help

Architecture:
    1. Welcome screen with yellow branding
    2. Check Python version (3.10+)
    3. Discover PostgreSQL (Linux)
    4. Install dependencies (venv + requirements.txt)
    5. Generate configs (.env + config.yaml v3.0) - BEFORE table creation!
    6. Setup database (create DB, roles, tables via DatabaseManager) - needs .env from step 5
    7. Launch services (API + Frontend)
    8. Open browser (http://localhost:7274)
"""

import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from colorama import Fore, Style, init


# Ensure project root is on sys.path so Linux_Installer package is importable
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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
        self.settings.setdefault("install_dir", str(Path.cwd()))
        self.settings.setdefault("pg_host", "localhost")
        self.settings.setdefault("pg_port", 5432)
        self.settings.setdefault("api_port", DEFAULT_API_PORT)
        self.settings.setdefault("dashboard_port", DEFAULT_FRONTEND_PORT)
        self.settings.setdefault("bind", "0.0.0.0")  # Bind address derived from install-time network choice (localhost=127.0.0.1/HTTP, LAN/WAN=0.0.0.0/HTTPS via mkcert)

        # Paths
        self.install_dir = Path(self.settings["install_dir"])
        self.venv_dir = self.install_dir / "venv"
        self.requirements_file = self.install_dir / "requirements.txt"

        # State
        self.postgresql_found = False
        self.psql_path: Optional[Path] = None
        self.venv_created = False
        self.database_credentials: Optional[Dict[str, str]] = None

    def _ensure_venv_site_packages(self) -> None:
        """Ensure virtualenv site-packages are available on sys.path."""
        venv_paths = []

        # Windows site-packages
        venv_paths.append(self.venv_dir / "Lib" / "site-packages")

        # POSIX site-packages with python version
        py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        venv_paths.append(self.venv_dir / "lib" / py_version / "site-packages")

        for path in venv_paths:
            if path.exists():
                str_path = str(path)
                if str_path not in sys.path:
                    sys.path.insert(0, str_path)

    def run(self) -> Dict[str, Any]:
        """
        Execute complete installation workflow

        Returns:
            Result dictionary with success status and details
        """
        result = {"success": False, "steps": []}

        try:
            # Step 1: Welcome screen
            self.welcome_screen()
            result["steps"].append("welcome_shown")

            # Step 1.5: Ask installation questions (NEW)
            if not self.settings.get("headless"):
                self._print_header("Installation Configuration")
                self.ask_installation_questions()
                result["steps"].append("configuration_gathered")

            # Step 2: Check Python version
            self._print_header("Checking Python Version")
            if not self.check_python_version():
                self._print_error("Python version check failed")
                result["error"] = "Python 3.10+ required"
                return result
            result["steps"].append("python_verified")

            # Step 3: Discover PostgreSQL
            self._print_header("Discovering PostgreSQL")
            pg_result = self.discover_postgresql()
            if not pg_result["found"]:
                self._print_error("PostgreSQL not found")
                self._print_postgresql_install_guide()
                result["error"] = "PostgreSQL 18 required"
                return result
            result["steps"].append("postgresql_found")

            # Step 4: Install dependencies
            self._print_header("Installing Dependencies")
            dep_result = self.install_dependencies()
            if not dep_result["success"]:
                self._print_error("Dependency installation failed")
                result["error"] = dep_result.get("error", "Unknown error")
                return result
            result["steps"].append("dependencies_installed")

            # Step 5: Generate configs (MUST happen before database setup!)
            # Table creation in step 6 needs .env file with DATABASE_URL
            self._print_header("Generating Configuration Files")
            config_result = self.generate_configs()
            if not config_result["success"]:
                self._print_error("Configuration generation failed")
                result["error"] = "; ".join(config_result.get("errors", ["Unknown error"]))
                return result
            result["steps"].append("configs_generated")

            # Step 6: Setup database (create DB, roles, tables, admin user, setup_state)
            self._print_header("Setting Up Database")
            db_result = self.setup_database()
            if not db_result["success"]:
                self._print_error("Database setup failed")
                result["error"] = "; ".join(db_result.get("errors", ["Unknown error"]))
                return result
            self.database_credentials = db_result.get("credentials", {})
            result["steps"].append("database_created")
            result["steps"].append("tables_created")  # Added by inline table creation

            # REMOVED: Service launching - services will not auto-start after installation

            # Step 7: Create desktop shortcuts (Linux .desktop launchers)
            if self.settings.get("create_shortcuts", False):
                self._print_header("Creating Desktop Shortcuts")
                self.create_desktop_shortcuts()
                result["steps"].append("shortcuts_created")

            # Success
            result["success"] = True
            self._print_success_summary()

            return result

        except KeyboardInterrupt:
            self._print_warning("\nInstallation cancelled by user")
            result["error"] = "User cancelled"
            return result

        except Exception as e:
            self._print_error(f"Installation failed: {e}")
            result["error"] = str(e)
            return result

    def welcome_screen(self) -> None:
        """Display welcome screen with yellow branding and Ubuntu detection"""
        separator = "=" * 70

        print(f"\n{Fore.YELLOW}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}  GiljoAI MCP - Linux Installer v3.0{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")

        print(f"{Fore.CYAN}Welcome to GiljoAI MCP!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}This installer will set up your coding orchestrator.{Style.RESET_ALL}\n")

        print(f"{Fore.WHITE}What will be installed:{Style.RESET_ALL}")
        print("  • PostgreSQL database (giljo_mcp)")
        print("  • Python dependencies (FastAPI, SQLAlchemy, etc.)")
        print("  • Configuration files (.env, config.yaml)")
        print("  • API server + Frontend dashboard")
        print("  • MCP server integration\n")

        # Detect and display Ubuntu information
        platform_info = f"Platform: {platform.system()} {platform.release()}"
        try:
            dist_info = platform.freedesktop_os_release()
            if dist_info.get("ID") == "ubuntu":
                ubuntu_version = dist_info.get("VERSION_ID", "")
                ubuntu_name = dist_info.get("NAME", "Ubuntu")
                platform_info = f"Platform: {ubuntu_name} {ubuntu_version} ({platform.machine()})"
                print(f"{Fore.GREEN}✓ Ubuntu detected - installer optimized for your system{Style.RESET_ALL}")
        except:
            pass

        print(f"{Fore.YELLOW}{platform_info}{Style.RESET_ALL}")
        print(
            f"{Fore.YELLOW}Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}{Style.RESET_ALL}\n"
        )

    def ask_installation_questions(self) -> None:
        """Gather user preferences for installation"""
        import getpass

        # Network Configuration (NEW)
        print(f"\n{Fore.CYAN}[Network Configuration]{Style.RESET_ALL}")
        print("Configuring external access for frontend connections...")

        # Detect network interfaces
        network_ips = self._get_all_network_ips()

        print("\nDetected network interfaces:")
        print("  1. localhost (local access only)")

        # Add detected IPs
        for i, ip in enumerate(network_ips, 2):
            print(f"  {i}. {ip}")

        # Add custom option
        custom_option = len(network_ips) + 2
        print(f"  {custom_option}. Enter custom address (domain or IP)")

        # Get user choice
        while True:
            choice = input(f"\n{Fore.YELLOW}Select network interface [1]: {Style.RESET_ALL}").strip()

            if not choice:
                # Default to localhost
                self.settings["external_host"] = "localhost"
                self._print_info("Using localhost for frontend connections")
                break

            try:
                choice_num = int(choice)
                if choice_num == 1:
                    self.settings["external_host"] = "localhost"
                    self._print_info("Using localhost for frontend connections")
                    break
                if 2 <= choice_num < custom_option:
                    selected_ip = network_ips[choice_num - 2]
                    self.settings["external_host"] = selected_ip
                    self._print_success(f"Using {selected_ip} for frontend connections")
                    break
                if choice_num == custom_option:
                    custom_addr = input(f"{Fore.YELLOW}Enter custom address (IP or domain): {Style.RESET_ALL}").strip()
                    if custom_addr:
                        self.settings["external_host"] = custom_addr
                        self._print_success(f"Using {custom_addr} for frontend connections")
                        break
                    self._print_warning("Empty address provided")
                else:
                    self._print_warning(f"Invalid choice. Please select 1-{custom_option}")
            except ValueError:
                self._print_warning(f"Invalid input. Please enter a number 1-{custom_option}")

        # PostgreSQL password (with verification)
        print(f"\n{Fore.CYAN}[PostgreSQL Configuration]{Style.RESET_ALL}")
        print("Enter the password for PostgreSQL 'postgres' user")
        print(f"{Fore.RED}(Required - no defaults allowed){Style.RESET_ALL}")

        # Ask twice to confirm
        max_attempts = 3
        for attempt in range(max_attempts):
            pg_pass = getpass.getpass(f"{Fore.YELLOW}Password: {Style.RESET_ALL}")

            # Require password - no defaults
            if not pg_pass:
                self._print_error("Password cannot be empty. Please enter your actual PostgreSQL admin password.")
                continue

            # Ask for confirmation
            pg_pass_confirm = getpass.getpass(f"{Fore.YELLOW}Confirm password: {Style.RESET_ALL}")

            # Check if they match
            if pg_pass == pg_pass_confirm:
                self.settings["pg_password"] = pg_pass
                self._print_success("Password confirmed")
                break
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                self._print_error(f"Passwords do not match. {remaining} attempt(s) remaining.")
            else:
                self._print_error(
                    "Too many failed attempts. Installation cannot continue without valid PostgreSQL password."
                )
                raise ValueError("PostgreSQL password required for installation")

        # REMOVED: Start services prompt - services will not auto-start

        # REMOVED: Database table creation prompt - table creation is now MANDATORY

        # Set defaults for MCP and Serena (will be configured in setup wizard)
        self.settings["register_mcp_tools"] = False
        self.settings["enable_serena"] = False

        # Create desktop shortcuts (Linux .desktop launchers)
        if platform.system() == "Linux":
            print(f"\n{Fore.CYAN}[Post-Installation Options]{Style.RESET_ALL}")
            print("Would you like to create desktop launchers in ~/Desktop and ~/.local/share/applications?")
            shortcuts_response = input(f"{Fore.YELLOW}Create launchers? (Y/n): {Style.RESET_ALL}").strip().lower()
            self.settings["create_shortcuts"] = shortcuts_response != "n"
        else:
            self.settings["create_shortcuts"] = False

        # Summary
        print(f"\n{Fore.GREEN}Configuration Summary:{Style.RESET_ALL}")
        print(f"  • External access host: {self.settings.get('external_host', 'localhost')}")
        print(f"  • PostgreSQL password: {'*' * 8} (secured)")
        if platform.system() == "Linux":
            print(f"  • Create desktop launchers: {self.settings['create_shortcuts']}")

    def check_python_version(self) -> bool:
        """
        Check if Python version meets requirements

        Returns:
            True if version is compatible, False otherwise
        """
        current_version = sys.version_info
        is_compatible = current_version >= MIN_PYTHON_VERSION

        # Handle both sys.version_info (named tuple) and regular tuple
        if hasattr(current_version, "major"):
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
        3. User-provided custom path (if auto-discovery fails)

        Returns:
            Discovery result with found status and paths
        """
        result = {"found": False, "psql_path": None, "scanned_paths": []}

        # Method 1: Check PATH
        self._print_info("Checking PATH for psql...")
        psql_path = shutil.which("psql")

        if psql_path:
            self._print_success(f"PostgreSQL detected in PATH: {psql_path}")
            result["found"] = True
            result["psql_path"] = psql_path
            self.psql_path = Path(psql_path)
            self.postgresql_found = True
            return result

        # Method 2: Scan platform-specific locations
        self._print_info("Scanning common installation locations...")
        scan_paths = self._get_postgresql_scan_paths()

        for path in scan_paths:
            result["scanned_paths"].append(str(path))

            if path.exists():
                self._print_success(f"PostgreSQL detected: {path}")
                result["found"] = True
                result["psql_path"] = str(path)
                self.psql_path = path
                self.postgresql_found = True

                # Add to PATH for session
                bin_dir = path.parent
                os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"

                return result

        # Method 3: Ask user about installation status
        self._print_warning("PostgreSQL not found in PATH or common Linux locations")

        # Skip prompt in headless mode
        if self.settings.get("headless"):
            return result

        print(f"\n{Fore.YELLOW}Do you have PostgreSQL installed on this system? (y/N): {Style.RESET_ALL}", end="")
        response = input().strip().lower() or "n"

        if response in ["n", "no"]:
            self._print_warning("PostgreSQL must be installed before continuing.")
            print(f"{Fore.CYAN}Download the installer here: {POSTGRESQL_DOWNLOAD_URL}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}Please install PostgreSQL 18, then re-run this installer.{Style.RESET_ALL}\n")
            print(
                f"{Fore.YELLOW}Press Ctrl+C to cancel this installer, install PostgreSQL, and then run it again.{Style.RESET_ALL}"
            )
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print()
                raise
            return result

        # Method 4: Ask for custom path
        print(f"\n{Fore.YELLOW}PostgreSQL detection failed. Let's try a custom path...{Style.RESET_ALL}")

        # Prompt for custom path (max 3 attempts)
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"\n{Fore.YELLOW}Enter the full path to your PostgreSQL bin directory{Style.RESET_ALL}")
            print(f"{Fore.WHITE}Example: /usr/lib/postgresql/18/bin or /opt/postgresql/bin{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Path: {Style.RESET_ALL}", end="")

            custom_path = input().strip()

            if not custom_path:
                self._print_warning("Empty path provided")
                continue

            # Validate custom path
            if self.check_custom_postgresql_path(custom_path):
                # Custom path is valid
                psql_path = Path(custom_path) / "psql"

                result["found"] = True
                result["psql_path"] = str(psql_path)
                self.psql_path = psql_path
                self.postgresql_found = True

                # Add to PATH for session
                os.environ["PATH"] = f"{custom_path}{os.pathsep}{os.environ['PATH']}"

                return result

            # Invalid path - show remaining attempts
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                self._print_warning(f"Invalid path. {remaining} attempt(s) remaining.")
            else:
                self._print_error("Maximum attempts exceeded.")

        # All attempts failed
        return result

    def check_custom_postgresql_path(self, path_str: str) -> bool:
        """
        Check if custom PostgreSQL path is valid

        Validates:
        1. Path exists
        2. Contains psql or psql.exe executable

        Args:
            path_str: Path to PostgreSQL bin directory

        Returns:
            True if path is valid, False otherwise
        """
        try:
            # Normalize path (handle backslashes, forward slashes, quotes, etc.)
            path_str = path_str.strip().strip('"').strip("'")
            path = Path(path_str).resolve()

            # Check if directory exists
            if not path.exists():
                self._print_error(f"Path does not exist: {path}")
                # Try to be helpful
                parent = path.parent
                if parent.exists():
                    self._print_info(f"Parent directory exists: {parent}")
                    self._print_info("Did you mean to include the 'bin' subdirectory?")
                return False

            # Check if it's a directory
            if not path.is_dir():
                self._print_error(f"Path is not a directory: {path}")
                return False

            # Check for psql executable (Linux expects 'psql')
            psql_path = path / "psql"

            if not psql_path.exists():
                self._print_error(f"psql executable not found in: {path}")
                if path.name == "psql":
                    self._print_info("You provided the path to the psql executable directly.")
                    self._print_info(f"Please provide the bin directory instead: {path.parent}")
                return False

            self._print_success(f"Valid PostgreSQL installation found: {psql_path}")
            return True

        except Exception as e:
            self._print_error(f"Invalid path: {e}")
            return False

    def _get_postgresql_scan_paths(self) -> List[Path]:
        """
        Get platform-specific PostgreSQL scan paths

        Returns:
            List of paths to check for psql
        """
        paths = []

        # Standard system paths
        paths.extend(
            [
                Path("/usr/bin/psql"),
                Path("/usr/local/bin/psql"),
            ]
        )

        # Version-specific paths (Debian/Ubuntu layout)
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
        result = {"success": False}

        try:
            # Step 1: Create venv if needed
            if self.venv_dir.exists():
                self._print_info(f"Virtual environment already exists: {self.venv_dir}")
                result["venv_existed"] = True
            else:
                self._print_info(f"Creating virtual environment: {self.venv_dir}")
                subprocess.run([sys.executable, "-m", "venv", str(self.venv_dir)], check=True, capture_output=True)
                self._print_success("Virtual environment created")
                result["venv_created"] = True
                self.venv_created = True

            # Determine pip executable for Linux virtualenv
            pip_executable = self.venv_dir / "bin" / "pip"

            # Step 2: Install requirements
            if not self.requirements_file.exists():
                self._print_error(f"requirements.txt not found: {self.requirements_file}")
                result["error"] = "requirements.txt missing"
                return result

            self._print_info("Installing Python packages (this may take 2-3 minutes)...")

            subprocess.run(
                [str(pip_executable), "install", "-r", str(self.requirements_file)],
                check=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            self._print_success("Dependencies installed successfully")
            result["success"] = True
            return result

        except subprocess.TimeoutExpired:
            self._print_error("Installation timed out (exceeded 5 minutes)")
            result["error"] = "Timeout"
            return result

        except subprocess.CalledProcessError as e:
            self._print_error(f"pip install failed: {e}")
            result["error"] = str(e)
            return result

        except Exception as e:
            self._print_error(f"Dependency installation failed: {e}")
            result["error"] = str(e)
            return result

    def setup_database(self) -> Dict[str, Any]:
        """
        Setup PostgreSQL database with correct credential flow

        Sequence:
        1. Create database and roles (DatabaseInstaller)
        2. Update .env with REAL credentials
        3. Reload environment variables
        4. Create tables using DatabaseManager (MANDATORY)
        5. Create admin account and setup_state

        Returns:
            Database setup result
        """
        try:
            self._ensure_venv_site_packages()
            from Linux_Installer.core.database import DatabaseInstaller

            # Prepare settings for DatabaseInstaller
            db_settings = {
                "pg_host": self.settings.get("pg_host", "localhost"),
                "pg_port": self.settings.get("pg_port", 5432),
                "pg_password": self.settings.get("pg_password"),
                "pg_user": self.settings.get("pg_user", "postgres"),
            }

            db_installer = DatabaseInstaller(settings=db_settings)

            # STEP 1: Create database and roles
            self._print_info("Creating database and roles...")
            result = db_installer.setup()

            if not result["success"]:
                self._print_error("Database creation failed")
                for error in result.get("errors", []):
                    self._print_error(f"  • {error}")
                return result

            self._print_success("Database and roles created successfully")

            # STEP 2: Store real credentials
            self.database_credentials = result.get("credentials", {})

            if not self.database_credentials:
                result["errors"] = ["Database credentials not returned by DatabaseInstaller"]
                result["success"] = False
                return result

            # STEP 3: Update .env with REAL database credentials
            self._print_info("Generating .env with real database credentials...")
            env_result = self.update_env_with_real_credentials()

            if not env_result["success"]:
                self._print_error("Failed to generate .env file")
                for error in env_result.get("errors", []):
                    self._print_error(f"  • {error}")
                result["success"] = False
                return result

            self._print_success(".env file generated with database credentials")

            # STEP 4: Reload environment variables
            import os

            from dotenv import load_dotenv

            load_dotenv(override=True)  # Force reload to pick up new DATABASE_URL

            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                result["errors"] = ["DATABASE_URL not found in .env after regeneration"]
                result["success"] = False
                return result

            self._print_info(f"Loaded DATABASE_URL from .env: {db_url.split('@')[0]}@...")

            # STEP 5: Create tables using DatabaseManager (MANDATORY - always happens)
            self._print_info("Creating database tables...")
            import asyncio
            import sys
            from pathlib import Path

            # Add project src to path
            project_root = Path(__file__).resolve().parent.parent
            sys.path.insert(0, str(project_root / "src"))

            from datetime import datetime, timezone
            from uuid import uuid4

            from giljo_mcp.database import DatabaseManager
            from giljo_mcp.models import SetupState
            from giljo_mcp.tenant import TenantManager

            # Generate proper tenant key for default installation
            default_tenant_key = TenantManager.generate_tenant_key("default_admin")

            # Store tenant key in instance variable for .env generation
            self.default_tenant_key = default_tenant_key

            # Create tables using async DatabaseManager
            async def create_tables_and_init():
                db_manager = DatabaseManager(db_url, is_async=True)

                # Create all tables (SAME AS api/app.py:186)
                await db_manager.create_tables_async()

                # REMOVED (Handover 0034): Default admin user creation
                # Fresh installs now use /welcome page to create first admin account
                # This eliminates the legacy admin/admin default credentials security risk
                async with db_manager.get_session_async() as session:
                    from sqlalchemy import select

                    # Skip admin creation - let user create via web UI on first run

                    # Create setup_state
                    stmt = select(SetupState).where(SetupState.tenant_key == default_tenant_key)
                    result_state = await session.execute(stmt)
                    existing_state = result_state.scalar_one_or_none()

                    if not existing_state:
                        setup_state = SetupState(
                            id=str(uuid4()),
                            tenant_key=default_tenant_key,  # Use generated tenant key
                            database_initialized=True,
                            database_initialized_at=datetime.now(
                                timezone.utc
                            ),  # REQUIRED by ck_database_initialized_at_required constraint
                            # REMOVED (Handover 0034): default_password_active and password_changed_at
                            # These fields have been removed from the model
                            setup_version="3.0.0",
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                        )
                        session.add(setup_state)
                        await session.commit()

                await db_manager.close_async()
                return True

            # Run async table creation
            tables_created = asyncio.run(create_tables_and_init())

            if tables_created:
                self._print_success("Database tables created successfully")
                self._print_success("Setup state initialized (Handover 0034: No default admin - create via web UI)")
                result["tables_created"] = True
                result["admin_created"] = False  # Handover 0034: No default admin
                result["setup_state_created"] = True
            else:
                self._print_error("Table creation failed")
                result["success"] = False
                return result

            return result

        except Exception as e:
            import traceback

            self._print_error(f"Database setup failed: {e}")
            traceback.print_exc()
            return {"success": False, "errors": [str(e)]}

    def generate_configs(self) -> Dict[str, Any]:
        """
        Generate configuration files (config.yaml ONLY)

        .env generation happens AFTER database setup when real credentials exist.

        Returns:
            Configuration generation result
        """
        try:
            self._ensure_venv_site_packages()
            from Linux_Installer.core.config import ConfigManager

            # Prepare settings for ConfigManager (v3.0: NO mode field)
            config_settings = {
                "pg_host": self.settings.get("pg_host", "localhost"),
                "pg_port": self.settings.get("pg_port", 5432),
                "api_port": self.settings.get("api_port", DEFAULT_API_PORT),
                "dashboard_port": self.settings.get("dashboard_port", DEFAULT_FRONTEND_PORT),
                "install_dir": str(self.install_dir),
                "bind": "0.0.0.0",  # Bind address derived from install-time network choice
                "external_host": self.settings.get("external_host", "localhost"),
            }

            config_manager = ConfigManager(settings=config_settings)

            # Generate config.yaml ONLY (no .env yet)
            self._print_info("Generating config.yaml...")
            yaml_result = config_manager.generate_config_yaml()

            if yaml_result["success"]:
                self._print_success("Configuration file generated (config.yaml)")
            else:
                self._print_error("Configuration generation failed")
                for error in yaml_result.get("errors", []):
                    self._print_error(f"  • {error}")

            return yaml_result

        except Exception as e:
            self._print_error(f"Config generation failed: {e}")
            return {"success": False, "errors": [str(e)]}

    def update_env_with_real_credentials(self) -> Dict[str, Any]:
        """
        Update .env file with real database credentials after database setup

        This fixes the password synchronization bug where .env was generated
        with admin password instead of the randomly-generated database passwords.

        Returns:
            Update result with success status
        """
        try:
            self._ensure_venv_site_packages()
            # Import ConfigManager from existing module
            from Linux_Installer.core.config import ConfigManager

            # Prepare settings with REAL database credentials
            config_settings = {
                "pg_host": self.settings.get("pg_host", "localhost"),
                "pg_port": self.settings.get("pg_port", 5432),
                "api_port": self.settings.get("api_port", DEFAULT_API_PORT),
                "dashboard_port": self.settings.get("dashboard_port", DEFAULT_FRONTEND_PORT),
                "install_dir": str(self.install_dir),
                "owner_password": self.database_credentials.get("owner_password"),
                "user_password": self.database_credentials.get("user_password"),
                "default_tenant_key": getattr(
                    self, "default_tenant_key", None
                ),  # Pass generated tenant key (from seed_initial_data)
                "bind": "0.0.0.0",  # Bind address derived from install-time network choice
            }

            # Create config manager
            config_manager = ConfigManager(settings=config_settings)

            # Regenerate .env with real credentials
            self._print_info("Regenerating .env with real database passwords...")
            env_result = config_manager.generate_env_file()

            if env_result["success"]:
                self._print_success("Configuration updated with database credentials")
            else:
                self._print_error("Failed to update configuration")
                for error in env_result.get("errors", []):
                    self._print_error(f"  • {error}")

            return env_result

        except Exception as e:
            self._print_error(f"Credential update failed: {e}")
            return {"success": False, "errors": [str(e)]}

    def launch_services(self) -> Dict[str, Any]:
        """
        Launch API and Frontend services

        Returns:
            Launch result with process IDs
        """
        result = {"success": False}

        try:
            # Check port availability
            api_port = self.settings.get("api_port", DEFAULT_API_PORT)
            frontend_port = self.settings.get("dashboard_port", DEFAULT_FRONTEND_PORT)

            if not self._is_port_available(api_port):
                self._print_warning(f"Port {api_port} is in use - finding alternative...")
                api_port = self._find_available_port(api_port)
                if not api_port:
                    result["error"] = "No available port for API"
                    return result
                self._print_info(f"Using alternative API port: {api_port}")

            if not self._is_port_available(frontend_port):
                self._print_warning(f"Port {frontend_port} is in use - finding alternative...")
                frontend_port = self._find_available_port(frontend_port)
                if not frontend_port:
                    self._print_warning("No available port for frontend - skipping")
                    frontend_port = None

            # Determine Python executable for Linux virtualenv
            python_executable = self.venv_dir / "bin" / "python"

            # Get ports from settings
            api_port = self.settings.get("api_port", DEFAULT_API_PORT)
            frontend_port = self.settings.get("dashboard_port", DEFAULT_FRONTEND_PORT)

            # Launch API server
            api_script = self.install_dir / "api" / "run_api.py"

            if not api_script.exists():
                self._print_error(f"API script not found: {api_script}")
                result["error"] = "API script missing"
                return result

            self._print_info("Starting API server...")

            api_process = subprocess.Popen(
                [str(python_executable), str(api_script), "--port", str(api_port)],
                cwd=str(self.install_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._print_success(f"API server started (PID: {api_process.pid})")

            result["api_pid"] = api_process.pid

            # Launch frontend (if npm available)
            frontend_process = None
            if shutil.which("npm"):
                frontend_dir = self.install_dir / "frontend"

                if frontend_dir.exists():
                    # Check if node_modules exists
                    if not (frontend_dir / "node_modules").exists():
                        self._print_info("Installing frontend dependencies...")

                        subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=True, capture_output=True)

                    self._print_info("Starting frontend server...")

                    npm_cmd = ["npm", "run", "dev", "--", "--port", str(frontend_port), "--strictPort"]

                    frontend_process = subprocess.Popen(
                        npm_cmd, cwd=str(frontend_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    self._print_success(f"Frontend server started (PID: {frontend_process.pid})")

                    result["frontend_pid"] = frontend_process.pid
                else:
                    self._print_warning("Frontend directory not found")
            else:
                self._print_warning("npm not found - frontend not started")

            # Wait for services to initialize
            self._print_info("Waiting for services to initialize...")
            time.sleep(3)

            result["success"] = True
            return result

        except Exception as e:
            self._print_error(f"Service launch failed: {e}")
            result["error"] = str(e)
            return result

    def create_desktop_shortcuts(self) -> None:
        """Create .desktop launchers for Linux desktops"""
        if platform.system() != "Linux":
            self._print_warning("Desktop launchers are only generated on Linux")
            return

        try:
            desktop_dir = Path.home() / "Desktop"
            applications_dir = Path.home() / ".local" / "share" / "applications"
            desktop_dir.mkdir(parents=True, exist_ok=True)
            applications_dir.mkdir(parents=True, exist_ok=True)

            icon_candidates = [
                self.install_dir / "giljo.ico",
                self.install_dir / "frontend" / "public" / "giljologo_full.png",
                self.install_dir / "frontend" / "public" / "favicon.ico",
                self.install_dir / "frontend" / "public" / "favicon.png",
            ]
            icon_path: Optional[Path] = next((path for path in icon_candidates if path.exists()), None)

            python_exec = self.venv_dir / "bin" / "python"
            if not python_exec.exists():
                python_exec = Path(sys.executable).resolve()

            control_panel = self.install_dir / "dev_tools" / "control_panel.py"
            if not control_panel.exists():
                self._print_warning("Developer control panel not found; skipping launcher creation.")
                return

            launcher_name = "GiljoAI MCP Dev Control Panel"

            desktop_entry = [
                "[Desktop Entry]",
                "Version=1.0",
                "Type=Application",
                f"Name={launcher_name}",
                "Comment=Launch the GiljoAI MCP developer control panel",
                f"TryExec={python_exec}",
                f"Exec={python_exec} {control_panel}",
                f"Path={self.install_dir}",
                "Terminal=false",
                "StartupNotify=false",
                "Categories=Development;Utility;",
            ]

            if icon_path:
                desktop_entry.append(f"Icon={icon_path}")

            desktop_entry_content = "\n".join(desktop_entry) + "\n"

            desktop_shortcut = desktop_dir / "GiljoAI_Dev_Control_Panel.desktop"
            applications_shortcut = applications_dir / desktop_shortcut.name

            for target in (desktop_shortcut, applications_shortcut):
                target.write_text(desktop_entry_content)
                os.chmod(target, 0o755)
                try:
                    subprocess.run(
                        ["gio", "set", "-t", "string", str(target), "metadata::trusted", "true"],
                        check=True,
                        capture_output=True,
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    self._print_warning(
                        f"Launcher created at {target}, but trust flag could not be set automatically."
                        " You may need to right-click the file and choose 'Allow Launching'."
                    )

            self._print_success(f"Created desktop launcher: {desktop_shortcut}")
            self._print_success(f"Registered launcher: {applications_shortcut}")

        except Exception as e:
            self._print_error(f"Failed to create desktop launchers: {e}")
            self._print_info(
                "You can manually create a .desktop file pointing to "
                f"venv/bin/python {self.install_dir / 'dev_tools' / 'control_panel.py'}"
            )

    def _get_all_network_ips(self) -> List[str]:
        """Get all non-loopback IPv4 addresses with graceful fallbacks"""
        ips: List[str] = []

        # Primary method: psutil for detailed interface inspection
        try:
            import psutil

            for interface_name, addresses in psutil.net_if_addrs().items():
                for addr in addresses:
                    if addr.family == 2:  # IPv4
                        ip = addr.address
                        if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                            ips.append(ip)
        except Exception:
            pass

        # Fallback 1: socket hostname lookup
        if not ips:
            try:
                host_ips = socket.gethostbyname_ex(socket.gethostname())[2]
                for ip in host_ips:
                    if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                        ips.append(ip)
            except Exception:
                pass

        # Fallback 2: use `ip -4 addr` command (available on most Linux distros)
        if not ips:
            try:
                result = subprocess.run(["ip", "-4", "addr", "show"], check=True, capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("inet "):
                        parts = line.split()
                        if len(parts) >= 2:
                            ip = parts[1].split("/")[0]
                            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                                ips.append(ip)
            except Exception:
                pass

        return sorted(set(ips))  # Deduplicate and sort

    def _print_success_summary(self) -> None:
        """Print installation success summary with manual start instructions"""
        separator = "=" * 70

        print(f"\n{Fore.GREEN}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{Style.BRIGHT}  Installation Complete!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")

        # Database credentials
        if self.database_credentials:
            print(f"{Fore.YELLOW}Database Credentials (SAVE THESE):{Style.RESET_ALL}")
            print("  • Database: giljo_mcp")
            print("  • Owner: giljo_owner")
            print("  • User: giljo_user")
            print("  • Host: localhost")
            print("  • Port: 5432")
            print()

        # Startup guidance
        print(f"{Fore.CYAN}{Style.BRIGHT}Recommended startup:{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}python startup.py{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}(Automatically uses the installer virtual environment){Style.RESET_ALL}")
        print(f"  {Fore.GREEN}./start_giljo.sh{Style.RESET_ALL}  (optional launcher)")
        print()

        # Manual start instructions
        print(f"{Fore.CYAN}{Style.BRIGHT}Manual control (separate terminals):{Style.RESET_ALL}\n")

        print(f"{Fore.WHITE}1. Start the API server:{Style.RESET_ALL}")
        print(f"   {Fore.GREEN}venv/bin/python api/run_api.py{Style.RESET_ALL}")
        print()

        print(f"{Fore.WHITE}2. Start the frontend (in a new terminal):{Style.RESET_ALL}")
        print(f"   {Fore.GREEN}cd frontend{Style.RESET_ALL}")
        print(f"   {Fore.GREEN}npm run dev{Style.RESET_ALL}")
        print()

        print(f"{Fore.WHITE}3. Open your browser:{Style.RESET_ALL}")

        # Detect network IPs
        network_ips = self._get_all_network_ips()
        frontend_port = self.settings.get("dashboard_port", DEFAULT_FRONTEND_PORT)
        api_port = self.settings.get("api_port", DEFAULT_API_PORT)

        # Show localhost first (most common)
        print(f"   {Fore.CYAN}http://localhost:{frontend_port}{Style.RESET_ALL}")

        # Show network IPs if detected
        if network_ips:
            print(f"\n   {Fore.WHITE}Or from other devices on your network:{Style.RESET_ALL}")
            for ip in network_ips:
                print(f"   {Fore.CYAN}http://{ip}:{frontend_port}{Style.RESET_ALL}")

        print()

        # API documentation
        print(f"{Fore.YELLOW}API Documentation:{Style.RESET_ALL}")
        print(f"  {Fore.CYAN}http://localhost:{api_port}/docs{Style.RESET_ALL}")
        print()

        # Next steps
        print(f"{Fore.WHITE}{Style.BRIGHT}Next Steps:{Style.RESET_ALL}")
        print("  1. Start the services with python startup.py (or the manual commands above)")
        print("  2. Open your browser to the frontend URL")
        print("  3. Complete the first-time setup wizard:")
        print("     • Change default admin password")
        print("     • Configure MCP integration (optional)")
        print("     • Configure Serena (optional)")
        print("  4. Create your first product and start orchestrating!")
        print()

        # Firewall configuration note
        print(f"{Fore.YELLOW}Network Access (Optional):{Style.RESET_ALL}")
        print("  To allow access from other devices on your network:")
        print("  1. Configure your OS firewall (see docs/guides/FIREWALL_CONFIGURATION.md)")
        print("  2. Update config.yaml: firewall_configured: true")
        print()

        print(f"{Fore.GREEN}Installation successful! Start the services to continue.{Style.RESET_ALL}\n")

    def _print_postgresql_install_guide(self) -> None:
        """Print platform-specific PostgreSQL installation guide with Ubuntu focus"""
        import platform

        print(f"\n{Fore.YELLOW}PostgreSQL Installation Required{Style.RESET_ALL}\n")

        # Detect Ubuntu version for more specific instructions
        try:
            dist_info = platform.freedesktop_os_release()
            if dist_info.get("ID") == "ubuntu":
                ubuntu_version = dist_info.get("VERSION_ID", "")
                print(f"{Fore.GREEN}Ubuntu {ubuntu_version} Detected - Optimized Instructions:{Style.RESET_ALL}")

                print(f"\n{Fore.CYAN}Method 1 - Official PostgreSQL APT Repository (Recommended):{Style.RESET_ALL}")
                print("  # Install the repository signing key")
                print("  wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -")
                print(
                    '  echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" | sudo tee /etc/apt/sources.list.d/pgdg.list'
                )
                print("  sudo apt update")
                print("  sudo apt install postgresql-18 postgresql-client-18 postgresql-contrib-18")
                print("  sudo systemctl enable --now postgresql")
                print("  # Set password for postgres user")
                print("  sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'your_password';\"")

                print(f"\n{Fore.CYAN}Method 2 - Ubuntu Default Repository (May have older version):{Style.RESET_ALL}")
                print("  sudo apt update")
                print("  sudo apt install postgresql postgresql-contrib")
                print("  sudo systemctl enable --now postgresql")
                print("  # Set password for postgres user")
                print("  sudo -u postgres psql -c \"ALTER USER postgres PASSWORD 'your_password';\"")

                print(f"\n{Fore.CYAN}Method 3 - Docker (Development Only):{Style.RESET_ALL}")
                print("  # Install Docker if not already installed")
                print("  sudo apt update && sudo apt install docker.io")
                print("  sudo systemctl enable --now docker")
                print("  # Run PostgreSQL 18 in Docker")
                print(
                    "  sudo docker run --name giljo-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:18"
                )

            else:
                print(f"{Fore.CYAN}Linux Distribution: {dist_info.get('NAME', 'Unknown')}{Style.RESET_ALL}")
        except:
            pass

        print(f"\n{Fore.CYAN}General Linux Installation:{Style.RESET_ALL}")
        print("  Ubuntu/Debian:")
        print("     sudo apt update")
        print("     sudo apt install postgresql-18 postgresql-client-18")
        print("     sudo systemctl enable --now postgresql")
        print("  RHEL/CentOS/Fedora:")
        print("     sudo dnf install postgresql18-server postgresql18")
        print("     sudo /usr/pgsql-18/bin/postgresql-18-setup initdb")
        print("     sudo systemctl enable --now postgresql-18")
        print("  Arch:")
        print("     sudo pacman -S postgresql")
        print("     sudo -iu postgres initdb -D /var/lib/postgres/data")
        print("     sudo systemctl enable --now postgresql")

        print(f"\n{Fore.YELLOW}Important for Ubuntu Users:{Style.RESET_ALL}")
        print("  • After installation, PostgreSQL runs on port 5432")
        print("  • Default admin user is 'postgres'")
        print("  • You MUST set a password for the postgres user")
        print("  • Use 'sudo systemctl status postgresql' to check service status")
        print("  • Logs are in /var/log/postgresql/")

        print(f"\n{Fore.RED}If you need help:{Style.RESET_ALL}")
        print("  • PostgreSQL Ubuntu documentation: https://help.ubuntu.com/community/PostgreSQL")
        print(f"  • Official docs: {POSTGRESQL_DOWNLOAD_URL}")

        print()

    def _is_port_available(self, port: int, host: str = "127.0.0.1") -> bool:
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
@click.option("--headless", is_flag=True, help="Non-interactive mode (use defaults)")
@click.option("--pg-password", default=None, help="PostgreSQL admin password (REQUIRED)")
@click.option("--api-port", default=DEFAULT_API_PORT, type=int, help="API server port")
@click.option("--frontend-port", default=DEFAULT_FRONTEND_PORT, type=int, help="Frontend port")
def main(headless: bool, pg_password: str, api_port: int, frontend_port: int) -> None:
    """
    GiljoAI MCP v3.0 - Linux Installer

    Single-command installation tailored for Linux environments.
    """
    try:
        # Prepare settings
        settings = {
            "install_dir": str(Path.cwd()),
            "pg_password": pg_password,
            "api_port": api_port,
            "dashboard_port": frontend_port,
            "headless": headless,
        }

        # Create installer
        installer = UnifiedInstaller(settings=settings)

        # Run installation
        result = installer.run()

        # Exit with appropriate code
        sys.exit(0 if result["success"] else 1)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Installation cancelled{Style.RESET_ALL}")
        sys.exit(0)

    except Exception as e:
        print(f"\n{Fore.RED}Installation failed: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
