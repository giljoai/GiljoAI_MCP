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
    5. Generate configs (.env + config.yaml v3.0) - BEFORE table creation!
    6. Setup database (create DB, roles, tables via DatabaseManager) - needs .env from step 5
    7. Launch services (API + Frontend)
    8. Open browser (http://localhost:7274)

Cross-platform: Windows, Linux, macOS
"""

import subprocess
import sys


def _bootstrap_dependencies():
    """Ensure click and colorama are available before main imports.

    This solves the bootstrap problem where install.py needs these packages
    to run, but is also responsible for installing them.

    On Ubuntu 24.04+, system Python is externally-managed (PEP 668),
    so we use --user flag when not inside a virtual environment.
    """
    required = ["click", "colorama"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Installing bootstrap dependencies: {', '.join(missing)}...")
        cmd = [sys.executable, "-m", "pip", "install", "-q"] + missing

        # If not in a venv, use --user to avoid PEP 668 restriction on Linux/macOS
        if sys.prefix == sys.base_prefix:
            cmd.insert(5, "--user")

        try:
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("\nERROR: Could not install bootstrap dependencies.")
            print("Please install manually:")
            print("  pip install --user click colorama")
            print("  or: sudo apt install python3-click python3-colorama  (Ubuntu/Debian)")
            sys.exit(1)


_bootstrap_dependencies()

# Standard library imports
import os
import platform
import shutil
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports (safe after bootstrap)
import click
from colorama import Fore, Style, init

# Import unified platform handlers and core modules
from installer.platforms import get_platform_handler


# Initialize colorama for cross-platform colored output
init(autoreset=True)


# Constants
MIN_PYTHON_VERSION = (3, 10)
MIN_POSTGRESQL_VERSION = 14
RECOMMENDED_POSTGRESQL_VERSION = 18
DEFAULT_API_PORT = 7272
DEFAULT_FRONTEND_PORT = 7274
POSTGRESQL_DOWNLOAD_URL = "https://www.postgresql.org/download/"
MIN_DISK_SPACE_MB = 500
NPM_INSTALL_TIMEOUT = 300
NPM_MAX_RETRIES = 3


def getpass_with_asterisks(prompt: str = "Password: ") -> str:
    """Cross-platform password input that shows asterisks as user types.

    Works on Windows (msvcrt) and Unix/Linux/Mac (termios).

    Args:
        prompt: The prompt to display before password input

    Returns:
        The entered password as a string
    """
    print(prompt, end="", flush=True)
    password = []

    if platform.system() == "Windows":
        import msvcrt

        while True:
            char = msvcrt.getch()
            # Enter key
            if char in (b"\r", b"\n"):
                print()
                break
            # Backspace
            if char == b"\x08":
                if password:
                    password.pop()
                    # Move cursor back, overwrite with space, move back again
                    print("\b \b", end="", flush=True)
            # Ctrl+C
            elif char == b"\x03":
                raise KeyboardInterrupt
            # Regular character
            else:
                try:
                    password.append(char.decode("utf-8"))
                    print("*", end="", flush=True)
                except UnicodeDecodeError:
                    pass  # Ignore non-UTF8 characters
    else:
        # Unix/Linux/Mac
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                char = sys.stdin.read(1)
                # Enter key
                if char in ("\r", "\n"):
                    # Raw mode: \n only moves down, need \r to return to column 0
                    sys.stdout.write("\r\n")
                    sys.stdout.flush()
                    break
                # Backspace (DEL or BS)
                if char in ("\x7f", "\x08"):
                    if password:
                        password.pop()
                        print("\b \b", end="", flush=True)
                # Ctrl+C
                elif char == "\x03":
                    raise KeyboardInterrupt
                # Regular character
                else:
                    password.append(char)
                    print("*", end="", flush=True)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return "".join(password)


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
        self.settings.setdefault("bind", "0.0.0.0")  # v3.0: Always bind all interfaces

        # Initialize platform handler (auto-detects Windows/Linux/macOS)
        self.platform = get_platform_handler()

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
        """Ensure virtualenv site-packages and src/ are available on sys.path."""
        paths_to_add = []

        # Windows site-packages
        paths_to_add.append(self.venv_dir / "Lib" / "site-packages")

        # POSIX site-packages with python version
        py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        paths_to_add.append(self.venv_dir / "lib" / py_version / "site-packages")

        # Add src/ directory for giljo_mcp package imports
        paths_to_add.append(self.install_dir / "src")

        for path in paths_to_add:
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

            # Step 6.5: Run Alembic migrations (CRITICAL - applies constraints & backfills)
            self._print_header("Applying Database Migrations")
            migration_result = self.run_database_migrations()
            if not migration_result["success"]:
                # Check if this is a fresh install or upgrade
                is_fresh_install = not (self.install_dir / ".env").exists()

                # For fresh installs, migration failure is CRITICAL
                if is_fresh_install and migration_result.get("migrations_applied", []):
                    self._print_error("Migration failed on fresh install - this is a critical error")
                    result["error"] = migration_result.get("error", "Unknown migration error")
                    return result

                # For upgrades, log warning but continue (may be expected)
                self._print_warning("Database migration encountered issues")
                self._print_warning(f"Error: {migration_result.get('error', 'Unknown error')}")
                self._print_info("Continuing installation - manual migration may be required")
            result["steps"].append("migrations_applied")

            # Step 6.6: Seed demo AgentJob and AgentExecution data (Handover 0366d-4)
            if migration_result["success"]:
                self._print_info("Seeding demo data for agent succession...")
                try:
                    import asyncio

                    demo_seeded = asyncio.run(self._seed_agent_job_demo_data())
                    if demo_seeded:
                        self._print_success("Demo data seeded successfully")
                    else:
                        self._print_warning("Demo data seeding skipped (already exists or failed)")
                except Exception as e:
                    self._print_warning(f"Failed to seed demo data: {e}")

            # Step 7: Install frontend dependencies (NEW - using production-grade npm system)
            self._print_header("Installing Frontend Dependencies")
            frontend_result = self.install_frontend_dependencies()
            if not frontend_result["success"] and not frontend_result.get("skipped", False):
                self._print_error("Frontend dependency installation failed")
                result["error"] = frontend_result.get("error", "Frontend dependencies failed")
                return result
            result["steps"].append("frontend_dependencies_installed")

            # Step 8: Create desktop shortcuts (if requested - Windows only)
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
        """Display welcome screen with yellow branding"""
        separator = "=" * 70

        print(f"\n{Fore.YELLOW}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}  GiljoAI MCP - Unified Installer v3.0{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")

        print(f"{Fore.CYAN}Welcome to GiljoAI MCP!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}This installer will set up your coding orchestrator.{Style.RESET_ALL}\n")

        print(f"{Fore.WHITE}What will be installed:{Style.RESET_ALL}")
        print("  • PostgreSQL database (giljo_mcp)")
        print("  • Python dependencies (FastAPI, SQLAlchemy, etc.)")
        print("  • Configuration files (.env, config.yaml)")
        print("  • API server + Frontend dashboard")
        print("  • MCP server integration\n")

        print(f"{Fore.YELLOW}Platform: {platform.system()} {platform.release()}{Style.RESET_ALL}")
        print(
            f"{Fore.YELLOW}Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}{Style.RESET_ALL}\n"
        )

    def ask_installation_questions(self) -> None:
        """Gather user preferences for installation"""
        # Network Configuration
        print(f"\n{Fore.CYAN}[Network Configuration]{Style.RESET_ALL}")
        print("Configuring external access for frontend connections...")

        # Detect network adapters (with names for tracking)
        from installer.shared.network import get_network_adapters

        network_adapters = get_network_adapters()

        # Build options list
        print("\nNetwork access options:")
        print(f"  1. {Fore.GREEN}Auto-detect (recommended for development){Style.RESET_ALL}")
        print("     → Dynamically detects IP on each startup")
        print("  2. localhost (local access only)")

        # Add detected adapters with their IPs
        for i, adapter in enumerate(network_adapters, 3):
            virtual_tag = " (virtual)" if adapter.get("is_virtual") else ""
            print(f"  {i}. {adapter['ip']} [{adapter['name']}{virtual_tag}]")

        # Add custom option
        custom_option = len(network_adapters) + 3
        print(f"  {custom_option}. Enter custom address (domain or IP)")

        # Get user choice
        while True:
            choice = input(f"\n{Fore.YELLOW}Select network option [1]: {Style.RESET_ALL}").strip()

            if not choice or choice == "1":
                # Auto-detect mode (development default)
                if network_adapters:
                    # Use first physical adapter for initial config
                    best_adapter = network_adapters[0]
                    self.settings["external_host"] = best_adapter["ip"]
                    self.settings["network_mode"] = "auto"
                    self.settings["selected_adapter"] = best_adapter["name"]
                    self.settings["initial_ip"] = best_adapter["ip"]
                    self._print_success(f"Auto-detect mode: Using {best_adapter['name']} ({best_adapter['ip']})")
                    self._print_info("IP will be re-detected on each server startup")
                else:
                    # Fallback if no adapters detected
                    self.settings["external_host"] = "localhost"
                    self.settings["network_mode"] = "localhost"
                    self._print_warning("No network adapters detected, using localhost")
                break

            try:
                choice_num = int(choice)
                if choice_num == 2:
                    # Localhost mode
                    self.settings["external_host"] = "localhost"
                    self.settings["network_mode"] = "localhost"
                    self._print_info("Using localhost for frontend connections")
                    break
                if 3 <= choice_num < custom_option:
                    # Specific adapter selected
                    selected = network_adapters[choice_num - 3]
                    self.settings["external_host"] = selected["ip"]
                    self.settings["network_mode"] = "static"
                    self.settings["selected_adapter"] = selected["name"]
                    self.settings["initial_ip"] = selected["ip"]
                    self._print_success(f"Using {selected['ip']} [{selected['name']}] for frontend connections")
                    break
                if choice_num == custom_option:
                    custom_addr = input(f"{Fore.YELLOW}Enter custom address (IP or domain): {Style.RESET_ALL}").strip()
                    if custom_addr:
                        self.settings["external_host"] = custom_addr
                        self.settings["network_mode"] = "custom"
                        self._print_success(f"Using {custom_addr} for frontend connections")
                        break
                    self._print_warning("Empty address provided")
                else:
                    self._print_warning(f"Invalid choice. Please select 1-{custom_option}")
            except ValueError:
                self._print_warning(f"Invalid input. Please enter a number 1-{custom_option}")

        # PostgreSQL password (with verification)
        print(f"\n{Fore.CYAN}[PostgreSQL Configuration]{Style.RESET_ALL}")

        if platform.system() == "Windows":
            # Windows: PostgreSQL installer already set a password
            print(f"\n{Fore.WHITE}PostgreSQL Admin Password Required{Style.RESET_ALL}")
            print("This is the password for the 'postgres' superuser account")
            print("(The password you set when you first installed PostgreSQL)")
            print(f"{Fore.RED}Required - no defaults allowed{Style.RESET_ALL}")

            max_attempts = 3
            for attempt in range(max_attempts):
                pg_pass = getpass_with_asterisks(f"{Fore.YELLOW}Password: {Style.RESET_ALL}")
                if not pg_pass:
                    self._print_error("Password cannot be empty.")
                    continue
                pg_pass_confirm = getpass_with_asterisks(f"{Fore.YELLOW}Confirm password: {Style.RESET_ALL}")
                if pg_pass == pg_pass_confirm:
                    self.settings["pg_password"] = pg_pass
                    self._print_success("Password confirmed")
                    break
                remaining = max_attempts - attempt - 1
                if remaining > 0:
                    self._print_error(f"Passwords do not match. {remaining} attempt(s) remaining.")
                else:
                    raise ValueError("PostgreSQL password required for installation")
        else:
            # Linux/macOS: PostgreSQL likely has no TCP password set
            # Try to set one automatically via peer/trust auth
            print(f"\n{Fore.WHITE}PostgreSQL Password Setup{Style.RESET_ALL}")
            print("Setting up a password for the PostgreSQL 'postgres' account...")
            print(f"{Fore.RED}Required - no defaults allowed{Style.RESET_ALL}")

            max_attempts = 3
            for attempt in range(max_attempts):
                pg_pass = getpass_with_asterisks(f"{Fore.YELLOW}Choose a PostgreSQL password: {Style.RESET_ALL}")
                if not pg_pass:
                    self._print_error("Password cannot be empty.")
                    continue
                pg_pass_confirm = getpass_with_asterisks(f"{Fore.YELLOW}Confirm password: {Style.RESET_ALL}")
                if pg_pass != pg_pass_confirm:
                    remaining = max_attempts - attempt - 1
                    if remaining > 0:
                        self._print_error(f"Passwords do not match. {remaining} attempt(s) remaining.")
                        continue
                    else:
                        raise ValueError("PostgreSQL password required for installation")

                # Try setting the password via peer auth (local socket)
                if self._set_postgres_password_via_peer(pg_pass):
                    self.settings["pg_password"] = pg_pass
                    self._print_success("PostgreSQL password set and confirmed")
                    break
                else:
                    # Peer auth failed — maybe user already set a password manually
                    print(f"\n{Fore.YELLOW}Could not set password automatically.{Style.RESET_ALL}")
                    print("If you already set a PostgreSQL password, enter it now.")
                    pg_pass = getpass_with_asterisks(f"{Fore.YELLOW}Existing password: {Style.RESET_ALL}")
                    if pg_pass:
                        self.settings["pg_password"] = pg_pass
                        self._print_success("Password accepted")
                        break
                    else:
                        self._print_error("Password cannot be empty.")
            else:
                raise ValueError("PostgreSQL password required for installation")

        # REMOVED: Start services prompt - services will not auto-start

        # REMOVED: Database table creation prompt - table creation is now MANDATORY

        # Set defaults for MCP and Serena (will be configured in setup wizard)
        self.settings["register_mcp_tools"] = False
        self.settings["enable_serena"] = False

        # Create desktop shortcuts
        if platform.system() == "Windows":
            print(f"\n{Fore.CYAN}[Post-Installation Options]{Style.RESET_ALL}")
            print("Would you like to create desktop shortcuts?")
            shortcuts_response = input(f"{Fore.YELLOW}Create shortcuts? (Y/n): {Style.RESET_ALL}").strip().lower()
            self.settings["create_shortcuts"] = shortcuts_response != "n"
        else:
            self.settings["create_shortcuts"] = False

        # Summary
        print(f"\n{Fore.GREEN}Configuration Summary:{Style.RESET_ALL}")
        network_mode = self.settings.get("network_mode", "localhost")
        if network_mode == "auto":
            adapter = self.settings.get("selected_adapter", "unknown")
            print(f"  • Network mode: {Fore.GREEN}Auto-detect{Style.RESET_ALL} ({adapter})")
            print("    → IP will be re-detected on each startup")
        elif network_mode == "static":
            adapter = self.settings.get("selected_adapter", "")
            print(f"  • Network mode: Static [{adapter}]")
        else:
            print(f"  • Network mode: {network_mode}")
        print(f"  • External access host: {self.settings.get('external_host', 'localhost')}")
        print(f"  • PostgreSQL password: {'*' * 8} (secured)")
        if platform.system() == "Windows":
            print(f"  • Create shortcuts: {self.settings['create_shortcuts']}")

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

            # Store PostgreSQL paths in settings for config.yaml persistence
            psql_path_obj = Path(psql_path)
            self.settings["postgresql_psql_path"] = str(psql_path_obj)
            self.settings["postgresql_bin_path"] = str(psql_path_obj.parent)
            self.settings["postgresql_installation_path"] = (
                str(psql_path_obj.parent.parent) if psql_path_obj.parent.name == "bin" else str(psql_path_obj.parent)
            )
            self.settings["postgresql_discovered_at"] = datetime.now(timezone.utc).isoformat()
            self.settings["postgresql_custom_path"] = False
            self.settings["postgresql_discovery_method"] = "PATH"

            return result

        # Method 2: Scan platform-specific locations
        self._print_info("Scanning common installation locations...")
        scan_paths = self._get_postgresql_scan_paths()

        for path in scan_paths:
            result["scanned_paths"].append(str(path))
            print(f"{Fore.WHITE}  Checking: {path}{Style.RESET_ALL}")

            if path.exists():
                self._print_success(f"PostgreSQL detected: {path}")
                result["found"] = True
                result["psql_path"] = str(path)
                self.psql_path = path
                self.postgresql_found = True

                # Store PostgreSQL paths in settings for config.yaml persistence
                bin_dir = path.parent
                self.settings["postgresql_psql_path"] = str(path)
                self.settings["postgresql_bin_path"] = str(bin_dir)
                self.settings["postgresql_installation_path"] = (
                    str(bin_dir.parent) if bin_dir.name == "bin" else str(bin_dir)
                )
                self.settings["postgresql_discovered_at"] = datetime.now(timezone.utc).isoformat()
                self.settings["postgresql_custom_path"] = False
                self.settings["postgresql_discovery_method"] = "COMMON_LOCATION"

                # Add to PATH for session
                os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"

                return result

        # Method 3: Ask for custom path
        self._print_warning("PostgreSQL not found in common locations")

        # Skip prompt in headless mode
        if self.settings.get("headless"):
            return result

        print(f"\n{Fore.YELLOW}Do you have PostgreSQL installed at a custom location? (y/n): {Style.RESET_ALL}", end="")
        response = input().strip().lower()

        if response not in ["y", "yes"]:
            return result

        # Prompt for custom path (max 3 attempts)
        max_attempts = 3
        for attempt in range(max_attempts):
            print(f"\n{Fore.YELLOW}Enter the full path to your PostgreSQL bin directory{Style.RESET_ALL}")
            print(f"{Fore.WHITE}Example: C:\\custom\\postgres\\bin or /opt/custom/postgres/bin{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Path: {Style.RESET_ALL}", end="")

            custom_path = input().strip()

            if not custom_path:
                self._print_warning("Empty path provided")
                continue

            # Validate custom path
            if self.check_custom_postgresql_path(custom_path):
                # Custom path is valid
                if self.platform.platform_name == "Windows":
                    psql_path = Path(custom_path) / "psql.exe"
                else:
                    psql_path = Path(custom_path) / "psql"

                result["found"] = True
                result["psql_path"] = str(psql_path)
                self.psql_path = psql_path
                self.postgresql_found = True

                # Store PostgreSQL paths in settings for config.yaml persistence
                custom_path_obj = Path(custom_path)
                self.settings["postgresql_psql_path"] = str(psql_path)
                self.settings["postgresql_bin_path"] = str(custom_path_obj)
                self.settings["postgresql_installation_path"] = (
                    str(custom_path_obj.parent) if custom_path_obj.name == "bin" else str(custom_path_obj)
                )
                self.settings["postgresql_discovered_at"] = datetime.now(timezone.utc).isoformat()
                self.settings["postgresql_custom_path"] = True
                self.settings["postgresql_discovery_method"] = "CUSTOM"

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

            # Check for psql executable (platform-specific)
            # Windows uses .exe extension, Linux/macOS don't
            if self.platform.platform_name == "Windows":
                psql_path = path / "psql.exe"
            else:
                psql_path = path / "psql"

            if not psql_path.exists():
                self._print_error(f"psql executable not found in: {path}")
                # Try to be helpful - check if psql exists without extension
                psql_no_ext = path / "psql"
                if psql_no_ext.exists() and self.platform.platform_name == "Windows":
                    self._print_info("Found 'psql' without .exe extension - this may not work on Windows")
                # Check if user provided the full path to psql.exe instead of bin directory
                if path.name == "psql.exe" and path.exists():
                    self._print_info("You provided the path to psql.exe directly")
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

        Delegates to platform handler to eliminate hardcoded OS-specific paths.

        Returns:
            List of paths to check for psql
        """
        return self.platform.get_postgresql_scan_paths()

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

            # Determine pip executable (platform-specific)
            pip_executable = self.platform.get_venv_pip(self.venv_dir)

            # Step 2: Install requirements
            if not self.requirements_file.exists():
                self._print_error(f"requirements.txt not found: {self.requirements_file}")
                result["error"] = "requirements.txt missing"
                return result

            self._print_info("Installing Python packages (this may take 2-3 minutes)...")
            print(f"{Fore.WHITE}You will see pip's progress output below...{Style.RESET_ALL}\n")

            subprocess.run(
                [str(pip_executable), "install", "-r", str(self.requirements_file)],
                check=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            self._print_success("Dependencies installed successfully")

            # Download NLTK data for vision summarization (Handover 0345b)
            self._print_info("Downloading NLTK data for vision summarization...")
            try:
                nltk_result = self._download_nltk_data(pip_executable)
                if nltk_result["success"]:
                    self._print_success("NLTK data downloaded successfully")
                else:
                    self._print_warning(f"NLTK data download failed: {nltk_result.get('error', 'Unknown error')}")
                    self._print_warning("Vision summarization may not work correctly")
            except Exception as e:
                self._print_warning(f"NLTK data download failed: {e}")
                self._print_warning("Vision summarization may not work correctly")

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
        Setup PostgreSQL database using Alembic-first strategy (v3.1.0+)

        PRODUCTION-GRADE APPROACH:
        All schema changes MUST go through Alembic migrations.
        NO direct create_all() calls - this ensures:
        - Version control for schema changes
        - Rollback safety
        - Upgrade path for existing installations
        - Consistent schema across environments

        Sequence:
        1. Create database and roles (DatabaseInstaller)
        2. Update .env with REAL credentials
        3. Reload environment variables
        4. Run Alembic migrations to create schema (REPLACES create_all())
        5. Seed initial data (SetupState ONLY - no admin user per Handover 0034)

        Returns:
            Database setup result with migrations_applied list
        """
        try:
            # Ensure venv site-packages are available before imports
            self._ensure_venv_site_packages()
            from installer.core.database import DatabaseInstaller

            # Prepare settings for DatabaseInstaller
            # Keys must match DatabaseInstaller.__init__ expectations
            db_settings = {
                "host": self.settings.get("pg_host", "localhost"),
                "port": self.settings.get("pg_port", 5432),
                "password": self.settings.get("pg_password"),
                "username": self.settings.get("pg_user", "postgres"),
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

            # STEP 5: Run Alembic migrations to create schema (REPLACES create_all())
            self._print_info("Running database migrations to create schema...")
            migration_result = self.run_database_migrations()

            if not migration_result["success"]:
                self._print_error("Database migration failed")
                for error in migration_result.get("errors", []):
                    self._print_error(f"  • {error}")
                result["success"] = False
                result["migration_error"] = migration_result.get("error", "Unknown error")
                return result

            self._print_success("Database schema created via Alembic migrations")

            # Store migration results in main result
            result["migrations_applied"] = migration_result.get("migrations_applied", [])

            # STEP 6: Seed initial data (SetupState ONLY - no admin user per Handover 0034)
            self._print_info("Creating setup state...")
            import asyncio
            import sys
            from pathlib import Path

            # Add src to path
            sys.path.insert(0, str(Path(__file__).parent / "src"))

            from datetime import datetime, timezone
            from uuid import uuid4

            from giljo_mcp.database import DatabaseManager
            from giljo_mcp.models import SetupState
            from giljo_mcp.tenant import TenantManager

            # Generate proper tenant key for default installation
            default_tenant_key = TenantManager.generate_tenant_key("default_installation")

            # Store tenant key in instance variable for .env generation
            self.default_tenant_key = default_tenant_key

            async def seed_initial_data():
                """Seed SetupState record for tracking installation."""
                db_manager = DatabaseManager(db_url, is_async=True)

                async with db_manager.get_session_async() as session:
                    from sqlalchemy import select

                    # Check if setup_state exists
                    stmt = select(SetupState).where(SetupState.tenant_key == default_tenant_key)
                    result_state = await session.execute(stmt)
                    existing_state = result_state.scalar_one_or_none()

                    if not existing_state:
                        setup_state = SetupState(
                            id=str(uuid4()),
                            tenant_key=default_tenant_key,
                            database_initialized=True,
                            database_initialized_at=datetime.now(timezone.utc),
                            setup_version="3.1.0",  # Updated to track Alembic-first architecture
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                        )
                        session.add(setup_state)
                        await session.commit()

                await db_manager.close_async()
                return True

            # Run async seeding
            seeded = asyncio.run(seed_initial_data())

            if seeded:
                self._print_success("Setup state initialized")
                result["setup_state_created"] = True
                result["admin_created"] = False  # Explicitly mark as not created (Handover 0034)
            else:
                self._print_error("Setup state creation failed")
                result["success"] = False
                return result

            # STEP 6.5: Seed demo AgentJob and AgentExecution data (Handover 0366d-4)
            self._print_info("Seeding demo data for agent succession...")
            try:
                demo_seeded = asyncio.run(self._seed_agent_job_demo_data(default_tenant_key))
                if demo_seeded:
                    self._print_success("Demo data seeded successfully")
                else:
                    self._print_info("Demo data seeding skipped (already exists)")
            except Exception as e:
                self._print_warning(f"Failed to seed demo data: {e}")

            return result

        except Exception as e:
            import traceback

            self._print_error(f"Database setup failed: {e}")
            traceback.print_exc()
            return {"success": False, "errors": [str(e)]}

    async def _seed_agent_job_demo_data(self, tenant_key: str = "default") -> bool:
        """
        Seed sample AgentJob and AgentExecution records to demonstrate succession.

        Creates a demo orchestrator job with two executions showing succession chain:
        - First execution: completed at 85% context usage (triggered succession)
        - Second execution: active, continuing work from predecessor

        Args:
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            bool - True if seeding succeeded, False otherwise

        Note:
            Idempotent - checks for existing demo data before inserting.
        """
        try:
            import sys
            from pathlib import Path

            # Add src to path
            sys.path.insert(0, str(Path(__file__).parent / "src"))

            # Get database URL from environment
            import os
            from datetime import datetime, timedelta, timezone
            from uuid import uuid4

            from dotenv import load_dotenv
            from sqlalchemy import select

            from giljo_mcp.database import DatabaseManager
            from giljo_mcp.models.agent_identity import AgentExecution, AgentJob

            load_dotenv(override=True)
            db_url = os.getenv("DATABASE_URL")

            if not db_url:
                self._print_warning("DATABASE_URL not found - skipping demo data seeding")
                return False

            db_manager = DatabaseManager(db_url, is_async=True)

            async with db_manager.get_session_async() as session:
                # Check if demo data already exists (idempotent)
                stmt = select(AgentJob).where(
                    AgentJob.tenant_key == tenant_key,
                    AgentJob.mission.contains("Demo: Orchestrator with Succession"),
                )
                result = await session.execute(stmt)
                existing_job = result.scalar_one_or_none()

                if existing_job:
                    self._print_info("Demo data already exists - skipping seed")
                    return True

                # Create demo AgentJob
                job_id = str(uuid4())
                demo_job = AgentJob(
                    job_id=job_id,
                    tenant_key=tenant_key,
                    project_id=None,  # Not associated with a project
                    mission="Demo: Orchestrator with Succession - This is a sample job showing how orchestrator succession works when context limits are approached.",
                    job_type="orchestrator",
                    status="active",
                    created_at=datetime.now(timezone.utc) - timedelta(hours=2),
                    job_metadata={
                        "demo": True,
                        "description": "Demonstrates succession workflow",
                    },
                )
                session.add(demo_job)

                # Create first execution (completed after reaching 85% context)
                first_agent_id = str(uuid4())
                # Create orchestrator execution (active)
                orchestrator_execution = AgentExecution(
                    agent_id=first_agent_id,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    agent_display_name="orchestrator",
                    status="working",
                    started_at=datetime.now(timezone.utc) - timedelta(hours=1),
                    completed_at=None,
                    progress=35,
                    current_task="Monitoring implementation agents and coordinating integration testing",
                    context_used=35000,
                    context_budget=100000,
                    health_status="healthy",
                    last_progress_at=datetime.now(timezone.utc),  # Current time to avoid immediate staleness alert
                    agent_name="Orchestrator",
                )
                session.add(orchestrator_execution)

                # Update first execution to point to successor
                first_execution.succeeded_by = second_agent_id

                await session.commit()

            await db_manager.close_async()
            return True

        except Exception as e:
            self._print_warning(f"Failed to seed demo data: {e}")
            import traceback

            traceback.print_exc()
            return False

    def generate_configs(self) -> Dict[str, Any]:
        """
        Generate configuration files (config.yaml ONLY)

        .env generation happens AFTER database setup when real credentials exist.

        Returns:
            Configuration generation result
        """
        try:
            # Ensure venv site-packages are available before imports
            self._ensure_venv_site_packages()
            from installer.core.config import ConfigManager

            # Prepare settings for ConfigManager (v3.0: NO mode field)
            config_settings = {
                "pg_host": self.settings.get("pg_host", "localhost"),
                "pg_port": self.settings.get("pg_port", 5432),
                "api_port": self.settings.get("api_port", DEFAULT_API_PORT),
                "dashboard_port": self.settings.get("dashboard_port", DEFAULT_FRONTEND_PORT),
                "install_dir": str(self.install_dir),
                "bind": "0.0.0.0",
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
            # Ensure venv site-packages are available before imports
            self._ensure_venv_site_packages()
            # Import ConfigManager from existing module
            from installer.core.config import ConfigManager

            # Prepare settings with REAL database credentials
            config_settings = {
                "pg_host": self.settings.get("pg_host", "localhost"),
                "pg_port": self.settings.get("pg_port", 5432),
                "pg_password": self.settings.get("pg_password"),
                "api_port": self.settings.get("api_port", DEFAULT_API_PORT),
                "dashboard_port": self.settings.get("dashboard_port", DEFAULT_FRONTEND_PORT),
                "install_dir": str(self.install_dir),
                "owner_password": self.database_credentials.get("owner_password"),
                "user_password": self.database_credentials.get("user_password"),
                "default_tenant_key": getattr(
                    self, "default_tenant_key", "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd"
                ),  # Pass generated tenant key
                "bind": "0.0.0.0",  # v3.0: Always bind all interfaces
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

    def _ensure_logs_dir(self) -> Path:
        """
        Ensure logs directory exists and return its path.

        Returns:
            Path object pointing to logs directory
        """
        logs_dir = self.install_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir

    def _npm_preflight_checks(self, frontend_dir: Path) -> Dict[str, Any]:
        """
        Run pre-flight checks before npm installation.

        Checks:
        1. npm registry accessibility (npm ping)
        2. Disk space (minimum 500MB)
        3. package-lock.json existence (warning if missing)

        Args:
            frontend_dir: Path to frontend directory

        Returns:
            Dict with 'healthy' (bool), 'issues' (list), 'warnings' (list)
        """
        result = {"healthy": True, "issues": [], "warnings": []}

        # Check 1: npm registry accessibility
        try:
            npm_ping = self.platform.run_npm_command(cmd=["npm", "ping"], cwd=frontend_dir, timeout=30)

            if not npm_ping["success"]:
                result["healthy"] = False
                result["issues"].append(f"npm registry unreachable: {npm_ping.get('stderr', 'Unknown error')}")
        except FileNotFoundError:
            result["healthy"] = False
            result["issues"].append("npm is not installed or not in PATH")
        except Exception as e:
            result["healthy"] = False
            result["issues"].append(f"npm registry check failed: {e!s}")

        # Check 2: Disk space
        try:
            disk_usage = shutil.disk_usage(frontend_dir)
            free_mb = disk_usage.free / (1024 * 1024)

            if free_mb < MIN_DISK_SPACE_MB:
                result["healthy"] = False
                result["issues"].append(
                    f"Insufficient disk space: {free_mb:.0f}MB available, {MIN_DISK_SPACE_MB}MB required"
                )
        except Exception as e:
            result["warnings"].append(f"Could not check disk space: {e!s}")

        # Check 3: package-lock.json existence
        lockfile = frontend_dir / "package-lock.json"
        if not lockfile.exists():
            result["warnings"].append("package-lock.json not found - will use 'npm install' instead of 'npm ci'")

        return result

    def _verify_npm_dependencies(self, frontend_dir: Path) -> bool:
        """
        Verify that critical npm dependencies are installed.

        Checks for presence of key packages that are imported by the frontend.
        This prevents false positives where node_modules exists but is incomplete.

        Args:
            frontend_dir: Path to frontend directory

        Returns:
            True if all critical dependencies are present, False otherwise
        """
        node_modules = frontend_dir / "node_modules"

        if not node_modules.exists():
            return False

        # Critical dependencies that must be present
        critical_deps = [
            "vue",
            "vuetify",
            "vue-router",
            "pinia",
            "axios",
            "lodash-es",  # Imported by useAutoSave.js
            "vuedraggable",  # Imported by UserSettings.vue
            "socket.io-client",
        ]

        for dep in critical_deps:
            dep_path = node_modules / dep
            if not dep_path.exists():
                self._print_warning(f"Missing dependency: {dep}")
                return False

        return True

    def _install_npm_dependencies_with_retry(self, frontend_dir: Path, max_retries: int = NPM_MAX_RETRIES) -> bool:
        """
        Install npm dependencies with production-grade retry logic.

        Strategy:
        1. Run pre-flight checks (npm registry, disk space, lockfile)
        2. Try npm ci (if package-lock.json exists)
        3. Fallback to npm install (if lockfile missing/corrupted)
        4. Two-tier verification (folder check + npm list)
        5. Clear cache on final retry
        6. Log all attempts to logs/install_npm.log

        Args:
            frontend_dir: Path to frontend directory
            max_retries: Maximum number of retry attempts (default: NPM_MAX_RETRIES)

        Returns:
            True if installation succeeded, False otherwise
        """
        # Ensure logs directory exists
        logs_dir = self._ensure_logs_dir()
        log_file = logs_dir / "install_npm.log"

        # Run pre-flight checks
        self._print_info("Running npm pre-flight checks...")
        preflight = self._npm_preflight_checks(frontend_dir)

        if not preflight["healthy"]:
            self._print_error("Pre-flight checks failed:")
            for issue in preflight["issues"]:
                self._print_error(f"  • {issue}")
            # Store pre-flight results for error reporting
            self._npm_preflight_results = preflight
            return False

        if preflight["warnings"]:
            for warning in preflight["warnings"]:
                self._print_warning(f"  • {warning}")

        # Store pre-flight results for error reporting
        self._npm_preflight_results = preflight

        # Determine strategy: npm ci vs npm install
        lockfile = frontend_dir / "package-lock.json"
        use_npm_ci = lockfile.exists()

        for attempt in range(max_retries):
            if attempt > 0:
                self._print_info(f"Retrying npm install (attempt {attempt + 1}/{max_retries})...")
            else:
                self._print_info("Installing frontend dependencies...")

            # Clear cache on final retry
            if attempt == max_retries - 1 and attempt > 0:
                self._print_info("Clearing npm cache before final attempt...")
                cache_result = self.platform.run_npm_command(
                    cmd=["npm", "cache", "clean", "--force"], cwd=frontend_dir, timeout=60
                )
                if cache_result["success"]:
                    self._print_success("npm cache cleared")

            # Choose npm command
            if use_npm_ci and attempt == 0:
                npm_cmd = ["npm", "ci"]
                cmd_name = "npm ci"
            else:
                npm_cmd = ["npm", "install"]
                cmd_name = "npm install"
                use_npm_ci = False  # Switch to npm install after first failure

            # Log attempt
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 70}\n")
                f.write(f"Attempt {attempt + 1}/{max_retries} - {datetime.now(timezone.utc).isoformat()}\n")
                f.write(f"Command: {' '.join(npm_cmd)}\n")
                f.write(f"{'=' * 70}\n\n")

            # Run npm command
            npm_result = self.platform.run_npm_command(cmd=npm_cmd, cwd=frontend_dir, timeout=NPM_INSTALL_TIMEOUT)

            # Log output
            with open(log_file, "a", encoding="utf-8") as f:
                f.write("STDOUT:\n")
                f.write(npm_result.get("stdout", "") + "\n\n")
                f.write("STDERR:\n")
                f.write(npm_result.get("stderr", "") + "\n\n")

            if npm_result["success"]:
                # First tier verification: folder check
                if not self._verify_npm_dependencies(frontend_dir):
                    self._print_warning(f"{cmd_name} succeeded but folder verification failed")
                    continue

                # Second tier verification: npm list
                self._print_info("Verifying installation integrity...")
                list_result = self.platform.run_npm_command(
                    cmd=["npm", "list", "--depth=0"], cwd=frontend_dir, timeout=30
                )

                # npm list can return non-zero even for valid installs (peer deps warnings)
                # So we just check that it doesn't completely fail
                if "ENOENT" in list_result.get("stderr", "") or "ERR!" in list_result.get("stderr", ""):
                    self._print_warning(f"{cmd_name} succeeded but npm list verification failed")
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write("NPM LIST VERIFICATION FAILED:\n")
                        f.write(list_result.get("stderr", "") + "\n\n")
                    continue

                # Both tiers passed
                self._print_success("Frontend dependencies installed and verified successfully")
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write("SUCCESS: Installation verified\n")
                return True
            # npm command failed
            error_msg = npm_result.get("stderr", npm_result.get("error", "Unknown error"))
            self._print_warning(f"Attempt {attempt + 1} failed: {error_msg[:100]}...")

            # If npm ci failed, try npm install next
            if "ci" in npm_cmd and attempt == 0:
                self._print_info("npm ci failed, will try npm install next")
                use_npm_ci = False

            # Wait before retry (exponential backoff: 2s, 4s, 8s)
            if attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)
                self._print_info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

        # All retries exhausted
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\nFAILURE: All {max_retries} attempts exhausted\n")
        return False

    def install_frontend_dependencies(self) -> Dict[str, Any]:
        """
        Install frontend dependencies during the main installation process.

        This method handles npm dependency installation with production-grade
        retry logic, pre-flight checks, and comprehensive error handling.

        Returns:
            Result dictionary with success status and details
        """
        result = {"success": False}

        try:
            # Check if npm is available
            if not shutil.which("npm"):
                self._print_warning("npm not found - skipping frontend dependencies")
                self._print_info("Install Node.js from: https://nodejs.org/")
                result["success"] = True  # Not a failure - just skipped
                result["skipped"] = True
                result["reason"] = "npm not available"
                return result

            # Check if frontend directory exists
            frontend_dir = self.install_dir / "frontend"
            if not frontend_dir.exists():
                self._print_warning("Frontend directory not found - skipping frontend dependencies")
                result["success"] = True  # Not a failure - just skipped
                result["skipped"] = True
                result["reason"] = "frontend directory not found"
                return result

            self._print_info("Installing frontend dependencies...")

            # Check if dependencies are already installed and verified
            if self._verify_npm_dependencies(frontend_dir):
                self._print_success("Frontend dependencies already installed and verified")
                result["success"] = True
                result["already_installed"] = True
                return result

            # Install dependencies with retry logic
            if self._install_npm_dependencies_with_retry(frontend_dir):
                self._print_success("Frontend dependencies installed successfully")
                result["success"] = True
                return result
            # CRITICAL: Frontend dependencies failed after retries - FAIL HARD
            self._print_error("=" * 70)
            self._print_error("INSTALLATION FAILED: Frontend dependencies could not be installed")
            self._print_error("=" * 70)
            self._print_error("")

            # Show pre-flight check results if available
            if hasattr(self, "_npm_preflight_results"):
                preflight = self._npm_preflight_results
                if preflight.get("issues"):
                    self._print_error("Pre-flight check issues detected:")
                    for issue in preflight["issues"]:
                        self._print_error(f"  • {issue}")
                    self._print_error("")

            # Show log file location
            log_file = self.install_dir / "logs" / "install_npm.log"
            if log_file.exists():
                self._print_error(f"Detailed logs: {log_file}")
                self._print_error("")

            self._print_error("Troubleshooting steps:")
            self._print_error("  1. Check network connectivity to npm registry:")
            self._print_error("     npm ping")
            self._print_error("     curl https://registry.npmjs.org/")
            self._print_error("")
            self._print_error(f"  2. Verify disk space (need ~{MIN_DISK_SPACE_MB}MB):")
            if self.platform.platform_name == "Windows":
                self._print_error("     dir")
            else:
                self._print_error("     df -h")
            self._print_error("")
            self._print_error("  3. Clear npm cache and retry manually:")
            self._print_error(f"     cd {frontend_dir}")
            self._print_error("     npm cache clean --force")
            self._print_error("     npm cache verify")
            self._print_error("     npm install --verbose")
            self._print_error("")
            self._print_error("  4. Check for proxy/firewall blocking npm registry:")
            self._print_error("     npm config get proxy")
            self._print_error("     npm config get https-proxy")
            self._print_error("")
            self._print_error("  5. If behind corporate proxy, configure npm:")
            self._print_error("     npm config set proxy http://proxy.company.com:8080")
            self._print_error("     npm config set https-proxy http://proxy.company.com:8080")
            self._print_error("")
            self._print_error("=" * 70)

            result["error"] = f"npm install failed after {NPM_MAX_RETRIES} retry attempts"
            result["success"] = False
            return result

        except Exception as e:
            self._print_error(f"Frontend dependency installation failed: {e}")
            result["error"] = str(e)
            result["success"] = False
            return result

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

            # Determine Python executable (platform-specific)
            python_executable = self.platform.get_venv_python(self.venv_dir)

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
                    # Verify dependencies were installed during installation phase
                    if not self._verify_npm_dependencies(frontend_dir):
                        self._print_error("Frontend dependencies not found!")
                        self._print_error("Dependencies should have been installed during 'python install.py'")
                        self._print_error("Please run installation again:")
                        self._print_error("  python install.py")
                        result["error"] = "Frontend dependencies missing - run python install.py first"
                        result["success"] = False
                        return result

                    self._print_info("Starting frontend server...")

                    # Delegate to platform handler for npm command execution
                    # Note: For background processes, we still use subprocess.Popen directly
                    # but use platform handler to determine shell setting
                    npm_cmd = ["npm", "run", "dev", "--", "--port", str(frontend_port), "--strictPort"]

                    # No shell needed - using array of predefined args (secure)

                    frontend_process = subprocess.Popen(
                        npm_cmd,
                        cwd=str(frontend_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        shell=False,  # nosec B602 - Safe: using array of predefined args
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
        """Create desktop shortcuts (delegates to platform handler)"""
        # Check if platform supports shortcuts
        if not self.platform.supports_desktop_shortcuts():
            self._print_info(f"Desktop shortcuts not supported on {self.platform.platform_name}")
            return

        # Delegate to platform handler
        result = self.platform.create_desktop_shortcuts(install_dir=self.install_dir, venv_dir=self.venv_dir)

        if result["success"]:
            for shortcut in result.get("shortcuts_created", []):
                self._print_success(f"Created shortcut: {shortcut}")
        else:
            self._print_warning(f"Shortcut creation: {result.get('message', 'Unknown result')}")

    def _get_all_network_ips(self) -> List[str]:
        """Get all non-loopback IPv4 addresses"""
        # Delegate to platform handler for network interface detection
        return self.platform.get_network_ips()

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

        # REMOVED (Handover 0034): Default admin account messaging
        # Fresh installs will create admin via CreateAdminAccount.vue

        # Startup guidance
        print(f"{Fore.CYAN}{Style.BRIGHT}Recommended startup:{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}python startup.py{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}(Automatically uses the installer virtual environment){Style.RESET_ALL}")
        if platform.system() == "Windows":
            print(f"  {Fore.GREEN}start_giljo.bat{Style.RESET_ALL}  (optional launcher)")
        else:
            print(f"  {Fore.GREEN}./start_giljo.sh{Style.RESET_ALL}  (optional launcher)")
        print()

        # Manual start instructions
        print(f"{Fore.CYAN}{Style.BRIGHT}Manual control (separate terminals):{Style.RESET_ALL}\n")

        print(f"{Fore.WHITE}1. Start the API server:{Style.RESET_ALL}")
        if platform.system() == "Windows":
            print(f"   {Fore.GREEN}venv\\Scripts\\python.exe api\\run_api.py{Style.RESET_ALL}")
        else:
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

        # Next steps (updated for Handover 0034)
        print(f"{Fore.WHITE}{Style.BRIGHT}Next Steps:{Style.RESET_ALL}")
        print("  1. Start the services with python startup.py (or the manual commands above)")
        print("  2. Open your browser to the frontend URL")
        print(f"  3. {Fore.YELLOW}Create your administrator account{Style.RESET_ALL} (first-run only)")
        print("  4. Configure optional features:")
        print("     • MCP integration")
        print("     • Serena integration")
        print("  5. Create your first product and start orchestrating!")
        print()

        # Firewall configuration note
        print(f"{Fore.YELLOW}Network Access (Optional):{Style.RESET_ALL}")
        print("  To allow access from other devices on your network:")
        print("  1. Configure your OS firewall (see docs/guides/FIREWALL_CONFIGURATION.md)")
        print("  2. Update config.yaml: firewall_configured: true")
        print()

        print(f"{Fore.GREEN}Installation successful! Start the services to continue.{Style.RESET_ALL}\n")

    def _print_postgresql_install_guide(self) -> None:
        """Print platform-specific PostgreSQL installation guide"""
        print(f"\n{Fore.YELLOW}PostgreSQL Installation Required{Style.RESET_ALL}\n")

        # Delegate to platform handler for OS-specific instructions
        guide = self.platform.get_postgresql_install_guide(recommended_version=RECOMMENDED_POSTGRESQL_VERSION)
        print(guide)
        print()

    def run_database_migrations(self) -> Dict[str, Any]:
        """
        Run Alembic database migrations (alembic upgrade head)

        PRODUCTION-GRADE APPROACH (v3.1.0+):
        This is the PRIMARY method for schema creation and updates.
        All schema changes MUST go through Alembic migrations.

        Handles both:
        - Fresh installs (no existing alembic_version table) - runs all migrations
        - Upgrades (existing alembic_version table) - runs only pending migrations

        Returns:
            Result dictionary with success status and details
        """
        result = {"success": False, "migrations_applied": []}

        try:
            # Ensure we're in the install directory
            cwd = Path.cwd()

            # Check if alembic.ini exists
            alembic_ini = cwd / "alembic.ini"
            if not alembic_ini.exists():
                self._print_error(f"alembic.ini not found at {alembic_ini}")
                result["error"] = "Alembic configuration file missing"
                return result

            # Check if migrations directory exists
            migrations_dir = cwd / "migrations"
            if not migrations_dir.exists():
                self._print_error(f"Migrations directory not found at {migrations_dir}")
                result["error"] = "Migrations directory missing"
                return result

            # Check database state before running migrations
            import asyncio
            import os

            async def check_and_stamp_base():
                """Check if alembic_version table exists, create and stamp if needed."""
                try:
                    from sqlalchemy import text

                    from giljo_mcp.database import DatabaseManager

                    db_url = os.getenv("DATABASE_URL")
                    if not db_url:
                        return False

                    db_manager = DatabaseManager(db_url, is_async=True)

                    async with db_manager.get_session_async() as session:
                        # Check if alembic_version table exists
                        check_query = text("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables
                                WHERE table_name = 'alembic_version'
                            )
                        """)
                        result_check = await session.execute(check_query)
                        table_exists = result_check.scalar()

                        if not table_exists:
                            self._print_info("Fresh install detected - will run all migrations from scratch")
                            await db_manager.close_async()
                            return True

                        # Check if version is stamped
                        version_query = text("SELECT version_num FROM alembic_version LIMIT 1")
                        result_version = await session.execute(version_query)
                        current_version = result_version.scalar()

                        if current_version:
                            self._print_info(f"Existing database detected - current version: {current_version}")
                        else:
                            self._print_info("Empty alembic_version table - will stamp and run migrations")

                        await db_manager.close_async()
                        return True

                except Exception as e:
                    self._print_warning(f"Could not check alembic version: {e}")
                    return True  # Proceed with migrations anyway

            # Check database state
            asyncio.run(check_and_stamp_base())

            self._print_info("Running database migrations (alembic upgrade head)...")

            # Run alembic upgrade head
            # Use venv Python to ensure alembic is available (not system Python)
            venv_python = self.platform.get_venv_python(self.venv_dir)
            proc = subprocess.run(
                [str(venv_python), "-m", "alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                cwd=str(cwd),
                check=False,  # Ensure correct working directory
            )

            if proc.returncode == 0:
                self._print_success("Database migrations completed successfully")
                result["success"] = True
                result["output"] = proc.stdout

                # Parse output to see which migrations ran
                for line in proc.stdout.split("\n"):
                    if "Running upgrade" in line:
                        result["migrations_applied"].append(line.strip())

                if result["migrations_applied"]:
                    self._print_info(f"Applied {len(result['migrations_applied'])} migration(s)")
                    for migration in result["migrations_applied"]:
                        self._print_info(f"  {migration}")
                else:
                    self._print_info("No new migrations to apply (database already up to date)")

                # CRITICAL: Verify essential tables were actually created
                # This catches the case where migrations "succeed" but no tables exist
                # (e.g., empty migrations/versions folder)
                self._print_info("Verifying database schema...")
                verification_result = asyncio.run(self._verify_essential_tables())

                if not verification_result["success"]:
                    self._print_error("Schema verification failed!")
                    self._print_error("Migrations ran but essential tables are missing.")
                    for missing in verification_result.get("missing_tables", []):
                        self._print_error(f"  Missing: {missing}")
                    self._print_error("")
                    self._print_error("This usually means:")
                    self._print_error("  1. migrations/versions/ folder is empty")
                    self._print_error("  2. Migration files are corrupted or orphaned")
                    self._print_error("")
                    self._print_error("Solution: Ensure baseline migration exists in migrations/versions/")
                    result["success"] = False
                    result["error"] = f"Missing tables: {', '.join(verification_result.get('missing_tables', []))}"
                    return result

                self._print_success(f"Schema verified: {verification_result['tables_found']} essential tables present")
            else:
                self._print_error("Database migration failed")
                self._print_error(f"STDOUT: {proc.stdout}")
                self._print_error(f"STDERR: {proc.stderr}")
                result["error"] = f"Migration failed: {proc.stderr}"
                result["output"] = proc.stdout
                result["stderr"] = proc.stderr

        except subprocess.TimeoutExpired:
            self._print_error("Database migration timed out after 120 seconds")
            result["error"] = "Migration timeout"
        except Exception as e:
            self._print_error(f"Database migration error: {e}")
            import traceback

            traceback.print_exc()
            result["error"] = str(e)

        return result

    async def _verify_essential_tables(self) -> Dict[str, Any]:
        """
        Verify that essential tables were created by migrations.

        This catches the scenario where alembic upgrade succeeds but no tables
        were actually created (e.g., empty migrations/versions folder).

        Essential tables checked:
        - setup_state: Required for installation tracking
        - users: Required for authentication
        - products: Core business entity
        - projects: Core business entity
        - messages: Agent communication

        Returns:
            Dict with success status and details about missing tables
        """
        result = {"success": False, "tables_found": 0, "missing_tables": []}

        # Essential tables that MUST exist for a valid installation
        essential_tables = [
            "setup_state",
            "users",
            "products",
            "projects",
            "messages",
            "agent_jobs",  # 0371: renamed from mcp_agent_jobs
            "agent_executions",
        ]

        try:
            import os

            from sqlalchemy import text

            from giljo_mcp.database import DatabaseManager

            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                result["error"] = "DATABASE_URL not found"
                return result

            db_manager = DatabaseManager(db_url, is_async=True)

            async with db_manager.get_session_async() as session:
                # Query information_schema for existing tables
                check_query = text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_type = 'BASE TABLE'
                """)
                query_result = await session.execute(check_query)
                existing_tables = {row[0] for row in query_result.fetchall()}

            await db_manager.close_async()

            # Check which essential tables exist
            for table in essential_tables:
                if table in existing_tables:
                    result["tables_found"] += 1
                else:
                    result["missing_tables"].append(table)

            # Success if all essential tables exist
            result["success"] = len(result["missing_tables"]) == 0
            result["existing_tables"] = list(existing_tables)

            return result

        except Exception as e:
            result["error"] = str(e)
            return result

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

    def _download_nltk_data(self, python_executable: Path) -> Dict[str, Any]:
        """
        Download required NLTK data for vision summarization (Handover 0345b).

        Downloads:
        - punkt: Tokenizer models
        - stopwords: Stopword corpus for multiple languages

        Args:
            python_executable: Path to venv python executable

        Returns:
            Result dictionary with success status
        """
        result = {"success": False}

        try:
            # Download NLTK data using Python subprocess
            # This ensures it's installed in the correct venv
            nltk_code = """
import nltk
import sys

try:
    # Download punkt_tab tokenizer (required for sentence splitting in NLTK 3.9+)
    nltk.download('punkt_tab', quiet=True)

    # Download stopwords (required for LSA summarization)
    nltk.download('stopwords', quiet=True)

    print("NLTK data downloaded successfully")
    sys.exit(0)
except Exception as e:
    print(f"NLTK download failed: {e}", file=sys.stderr)
    sys.exit(1)
"""
            # Run NLTK download in venv
            process_result = subprocess.run(
                [str(python_executable), "-c", nltk_code],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,  # 1 minute timeout
            )

            if process_result.returncode == 0:
                result["success"] = True
            else:
                result["error"] = process_result.stderr or "Unknown error"

            return result

        except subprocess.TimeoutExpired:
            result["error"] = "Download timed out"
            return result
        except Exception as e:
            result["error"] = str(e)
            return result

    # Output helpers
    def _print_header(self, text: str) -> None:
        """Print section header"""
        separator = "=" * 70
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}  {text}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")

    def _set_postgres_password_via_peer(self, password: str) -> bool:
        """Set PostgreSQL password using local peer/trust authentication.

        On Linux: uses sudo -u postgres psql (peer auth over Unix socket)
        On macOS: uses psql -U postgres directly (Homebrew trust auth)

        Returns True if password was set successfully.
        """
        # Escape single quotes in password for SQL
        safe_password = password.replace("'", "''")
        sql = f"ALTER USER postgres PASSWORD '{safe_password}';"

        system = platform.system()
        try:
            if system == "Darwin":
                # macOS (Homebrew): postgres runs as current user
                cmd = ["psql", "-U", "postgres", "-d", "postgres", "-c", sql]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=10
                )
            else:
                # Linux: use sudo -u postgres for peer auth
                cmd = ["sudo", "-u", "postgres", "psql", "-c", sql]
                self._print_info("Setting PostgreSQL password (sudo may ask for your password)...")
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=30
                )

            if result.returncode == 0:
                return True

            self._print_warning(f"Peer auth password set failed: {result.stderr.strip()}")
            return False

        except subprocess.TimeoutExpired:
            self._print_warning("Password set timed out")
            return False
        except FileNotFoundError:
            self._print_warning("psql not found in PATH")
            return False
        except Exception as e:
            self._print_warning(f"Peer auth password set failed: {e}")
            return False

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
    GiljoAI MCP v3.0 - Unified Installer

    Single-command installation for all platforms.
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
