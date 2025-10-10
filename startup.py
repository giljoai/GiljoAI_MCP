#!/usr/bin/env python3
"""
GiljoAI MCP - Unified Startup Script

This is the primary entry point for running GiljoAI MCP.
It handles:
- PostgreSQL detection and validation
- Python version checking
- Database connectivity verification
- First-run detection
- Service startup (API + Frontend)
- Browser launching (setup wizard or dashboard)

Usage:
    python startup.py              # Start services
    python startup.py --help       # Show help
    python startup.py --check-only # Only check dependencies

Cross-platform: Works on Windows, Linux, and macOS
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
from typing import Optional, Tuple

import click
from colorama import Fore, Style, init


# Initialize colorama for cross-platform colored output
init(autoreset=True)


# Constants
MIN_PYTHON_VERSION = (3, 10)
REQUIRED_POSTGRESQL_VERSION = 18
DEFAULT_API_PORT = 7272
DEFAULT_FRONTEND_PORT = 7274
POSTGRESQL_DOWNLOAD_URL = "https://www.postgresql.org/download/"


def print_header(text: str) -> None:
    """Print a styled section header."""
    separator = "=" * 70
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{separator}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}  {text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{separator}{Style.RESET_ALL}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Fore.GREEN}[OK]{Style.RESET_ALL} {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {text}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Fore.BLUE}[INFO]{Style.RESET_ALL} {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {text}")


def check_python_version() -> bool:
    """
    Check if Python version meets minimum requirements.

    Returns:
        True if version is compatible, False otherwise
    """
    current_version = sys.version_info
    is_compatible = current_version >= MIN_PYTHON_VERSION

    if is_compatible:
        version_str = f"{current_version.major}.{current_version.minor}.{current_version.micro}"
        print_success(f"Python {version_str} detected")
    else:
        current_str = f"{current_version.major}.{current_version.minor}.{current_version.micro}"
        required_str = f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}"
        print_error(f"Python {current_str} detected, but {required_str}+ is required")

    return is_compatible


def check_postgresql_installed() -> bool:
    """
    Check if PostgreSQL is installed and accessible.

    We use a multi-layered approach:
    1. Check if psql is in PATH
    2. Check common Windows installation paths
    3. Try to connect via Python (most reliable)

    Returns:
        True if PostgreSQL is available, False otherwise
    """
    # Method 1: Check PATH
    psql_path = shutil.which("psql")
    if psql_path:
        print_success(f"PostgreSQL detected at: {psql_path}")
        return True

    # Method 2: Check common installation paths on Windows
    if platform.system() == "Windows":
        common_paths = [
            Path("C:/Program Files/PostgreSQL/18/bin/psql.exe"),
            Path("C:/Program Files/PostgreSQL/17/bin/psql.exe"),
            Path("C:/Program Files/PostgreSQL/16/bin/psql.exe"),
            Path("C:/Program Files (x86)/PostgreSQL/18/bin/psql.exe"),
            Path("C:/Program Files (x86)/PostgreSQL/17/bin/psql.exe"),
        ]

        for path in common_paths:
            if path.exists():
                print_success(f"PostgreSQL detected at: {path}")
                print_warning("PostgreSQL not in PATH - consider adding to environment variables")
                return True

    # Method 3: Try to connect via Python (most reliable)
    # This will be tested in the database connectivity check
    print_warning("PostgreSQL command-line tools not found in PATH")
    print_info("Will verify PostgreSQL via database connectivity check...")
    return True  # Allow to proceed to database connectivity check


def check_pip_available() -> bool:
    """
    Check if pip is available.

    Returns:
        True if pip is available, False otherwise
    """
    pip_path = shutil.which("pip")

    if pip_path:
        print_success(f"pip detected at: {pip_path}")
        return True
    else:
        print_error("pip not found in system PATH")
        return False


def check_npm_available() -> bool:
    """
    Check if npm is available (for frontend).

    Returns:
        True if npm is available, False otherwise
    """
    npm_path = shutil.which("npm")

    if npm_path:
        print_success(f"npm detected at: {npm_path}")
        return True
    else:
        print_warning("npm not found - frontend will not be available")
        print_info("Install Node.js from: https://nodejs.org/")
        return False


def check_database_connectivity() -> Tuple[bool, Optional[str]]:
    """
    Check if database connection can be established.

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Load environment variables
        from dotenv import load_dotenv

        load_dotenv()

        # Get database URL from environment or use default
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            # Try to construct from individual components
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "giljo_mcp")
            db_user = os.getenv("DB_USER", "postgres")
            db_password = os.getenv("DB_PASSWORD", "4010")

            from urllib.parse import quote_plus

            password_encoded = quote_plus(db_password)
            database_url = f"postgresql://{db_user}:{password_encoded}@{db_host}:{db_port}/{db_name}"

        # Attempt connection
        from src.giljo_mcp.database import DatabaseManager

        db_manager = DatabaseManager(database_url=database_url, is_async=False)

        # Try to create a session to verify connection
        with db_manager.get_session() as session:
            # Simple query to verify connection
            from sqlalchemy import text
            session.execute(text("SELECT 1"))

        print_success("Database connection successful")
        return True, None

    except ImportError as e:
        error_msg = f"Missing required dependencies: {e}"
        print_error(error_msg)
        print_info("Run: pip install -r requirements.txt")
        return False, error_msg

    except Exception as e:
        error_msg = f"Database connection failed: {e}"
        print_error(error_msg)
        print_info("Verify PostgreSQL is running and credentials are correct")
        print_info("Check .env file or environment variables")
        return False, error_msg


def check_first_run() -> Tuple[bool, Optional[dict]]:
    """
    Check if this is the first run (setup not completed).

    Returns:
        Tuple of (is_first_run, state_dict)
    """
    try:
        from src.giljo_mcp.setup.state_manager import SetupStateManager

        # Get setup state
        state_manager = SetupStateManager.get_instance(tenant_key="default")
        state = state_manager.get_state()

        is_first_run = not state.get("completed", False)

        if is_first_run:
            print_info("First-run detected - setup wizard will open")
        else:
            print_success("Setup completed previously - launching dashboard")

        return is_first_run, state

    except Exception as e:
        print_warning(f"Could not determine setup status: {e}")
        print_info("Assuming first-run - setup wizard will open")
        return True, None


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """
    Check if a port is available.

    Args:
        port: Port number to check
        host: Host to check on

    Returns:
        True if port is available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result != 0  # Non-zero means port is available
    except Exception:
        return False


def find_available_port(preferred_port: int, max_attempts: int = 10) -> Optional[int]:
    """
    Find an available port starting from preferred port.

    Args:
        preferred_port: Preferred port number
        max_attempts: Maximum number of ports to try

    Returns:
        Available port number or None if none found
    """
    for offset in range(max_attempts):
        port = preferred_port + offset
        if is_port_available(port):
            return port

    return None


def get_config_ports() -> Tuple[int, int]:
    """
    Get API and Frontend ports from config.yaml.

    Returns:
        Tuple of (api_port, frontend_port)
    """
    try:
        import yaml

        config_path = Path.cwd() / "config.yaml"

        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)

            api_port = config.get("services", {}).get("api", {}).get("port", DEFAULT_API_PORT)
            frontend_port = config.get("services", {}).get("frontend", {}).get("port", DEFAULT_FRONTEND_PORT)

            return api_port, frontend_port

    except Exception as e:
        print_warning(f"Could not read config.yaml: {e}")

    # Fallback to defaults
    return DEFAULT_API_PORT, DEFAULT_FRONTEND_PORT


def start_api_server() -> Optional[subprocess.Popen]:
    """
    Start the API server.

    Returns:
        Popen process object or None if failed
    """
    try:
        api_script = Path.cwd() / "api" / "run_api.py"

        if not api_script.exists():
            print_error(f"API script not found: {api_script}")
            return None

        # Determine Python executable (prefer venv)
        venv_python = Path.cwd() / "venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            venv_python = Path.cwd() / "venv" / "bin" / "python"

        if venv_python.exists():
            python_executable = str(venv_python)
        else:
            python_executable = sys.executable

        # Start API server
        process = subprocess.Popen(
            [python_executable, str(api_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(Path.cwd()),
        )

        print_success(f"API server started (PID: {process.pid})")
        return process

    except Exception as e:
        print_error(f"Failed to start API server: {e}")
        return None


def start_frontend_server() -> Optional[subprocess.Popen]:
    """
    Start the frontend development server.

    Returns:
        Popen process object or None if failed
    """
    try:
        frontend_dir = Path.cwd() / "frontend"

        if not frontend_dir.exists():
            print_warning("Frontend directory not found - skipping frontend")
            return None

        # Check if node_modules exists
        node_modules = frontend_dir / "node_modules"
        if not node_modules.exists():
            print_info("Installing frontend dependencies...")
            subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=True)

        # Start frontend server
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(frontend_dir),
        )

        print_success(f"Frontend server started (PID: {process.pid})")
        return process

    except FileNotFoundError:
        print_warning("npm not found - skipping frontend server")
        return None
    except Exception as e:
        print_error(f"Failed to start frontend server: {e}")
        return None


def open_browser(url: str, delay: int = 3) -> None:
    """
    Open browser to specified URL after a delay.

    Args:
        url: URL to open
        delay: Delay in seconds before opening
    """
    try:
        print_info(f"Opening browser to {url} in {delay} seconds...")
        time.sleep(delay)
        webbrowser.open(url)
        print_success("Browser opened")
    except Exception as e:
        print_error(f"Failed to open browser: {e}")
        print_info(f"Please manually open: {url}")


def check_dependencies() -> bool:
    """
    Check all required dependencies.

    Returns:
        True if all checks pass, False otherwise
    """
    print_header("Checking Dependencies")

    checks = [
        ("Python Version", check_python_version, True),  # Required
        ("PostgreSQL", check_postgresql_installed, True),  # Required (but verified via DB connection)
        ("pip", check_pip_available, True),  # Required
        ("npm (optional)", check_npm_available, False),  # Optional
    ]

    all_passed = True
    for check_name, check_func, required in checks:
        print_info(f"Checking {check_name}...")
        result = check_func()
        if not result and required:
            # PostgreSQL gets a pass here because we verify via DB connection
            if "PostgreSQL" not in check_name:
                all_passed = False

    return all_passed


def install_requirements() -> bool:
    """
    Install Python requirements from requirements.txt.

    Checks if critical packages are already installed before attempting
    installation. Uses pip to install from requirements.txt if needed.

    Returns:
        True if requirements are installed (or were already installed)
        False if installation failed
    """
    # Define critical packages to check
    critical_packages = [
        ("fastapi", "FastAPI"),
        ("sqlalchemy", "SQLAlchemy"),
        ("psycopg2", "psycopg2"),
        ("dotenv", "python-dotenv"),
        ("yaml", "pyyaml"),
    ]

    print_info("Checking if requirements are already installed...")

    # Check if critical packages are already installed
    all_installed = True
    for module_name, package_name in critical_packages:
        try:
            __import__(module_name)
        except ImportError:
            all_installed = False
            break

    if all_installed:
        print_success("Requirements already installed")
        return True

    # Need to install requirements
    print_info("Installing requirements from requirements.txt...")

    # Check if requirements.txt exists
    requirements_path = Path.cwd() / "requirements.txt"
    if not requirements_path.exists():
        print_error("requirements.txt not found")
        print_info(f"Expected at: {requirements_path}")
        return False

    print_warning("This may take 2-3 minutes on first install...")

    try:
        # Run pip install
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,  # 5 minute timeout
        )

        print_success("Requirements installed successfully")

        # Verify critical packages can now be imported
        print_info("Verifying installation...")
        failed_packages = []

        for module_name, package_name in critical_packages:
            try:
                __import__(module_name)
            except ImportError:
                failed_packages.append(package_name)

        if failed_packages:
            print_error(f"Some packages failed to install: {', '.join(failed_packages)}")
            return False

        print_success("All critical packages verified")
        return True

    except subprocess.TimeoutExpired:
        print_error("Installation timed out (exceeded 5 minutes)")
        print_info("Try installing manually: pip install -r requirements.txt")
        return False

    except subprocess.CalledProcessError as e:
        print_error(f"pip install failed with return code {e.returncode}")
        if e.stderr:
            print_info(f"Error details: {e.stderr[:500]}")  # Limit error output
        print_info("Try installing manually: pip install -r requirements.txt")
        return False

    except Exception as e:
        print_error(f"Unexpected error during installation: {e}")
        return False


def run_startup(check_only: bool = False) -> int:
    """
    Main startup function.

    Args:
        check_only: If True, only check dependencies without starting services

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    print_header("GiljoAI MCP - Unified Startup v3.0")

    # Step 1: Check dependencies (Python, PostgreSQL, pip)
    if not check_dependencies():
        print_error("Dependency checks failed")
        return 1

    if check_only:
        print_success("All dependency checks passed")
        return 0

    # Step 2: Install requirements
    print_header("Installing Requirements")
    if not install_requirements():
        print_error("Failed to install requirements")
        print_info("Please install manually: pip install -r requirements.txt")
        return 1

    # Step 3: Check database connectivity
    print_header("Database Connectivity")
    print_info("Checking database connection...")
    db_success, db_error = check_database_connectivity()

    if not db_success:
        print_error("Database connectivity check failed")
        print_info("Please ensure PostgreSQL is running and configured correctly")
        return 1

    # Step 4: Check first-run status
    print_header("Setup Status")
    print_info("Checking setup completion status...")
    is_first_run, state = check_first_run()

    # Step 5: Get ports from config
    api_port, frontend_port = get_config_ports()

    # Step 6: Check port availability
    print_header("Port Availability")
    print_info(f"Checking API port {api_port}...")
    if not is_port_available(api_port):
        print_warning(f"Port {api_port} is occupied - finding alternative...")
        new_api_port = find_available_port(api_port)
        if new_api_port:
            print_success(f"Using alternative port {new_api_port}")
            api_port = new_api_port
        else:
            print_error("Could not find available port for API")
            return 1

    print_info(f"Checking frontend port {frontend_port}...")
    if not is_port_available(frontend_port):
        print_warning(f"Port {frontend_port} is occupied - finding alternative...")
        new_frontend_port = find_available_port(frontend_port)
        if new_frontend_port:
            print_success(f"Using alternative port {new_frontend_port}")
            frontend_port = new_frontend_port
        else:
            print_warning("Could not find available port for frontend")

    # Step 7: Start services
    print_header("Starting Services")

    print_info("Starting API server...")
    api_process = start_api_server()

    if not api_process:
        print_error("Failed to start API server")
        return 1

    print_info("Starting frontend server...")
    frontend_process = start_frontend_server()

    # Step 8: Open browser
    print_header("Opening Browser")

    if is_first_run:
        # Open setup wizard
        setup_url = f"http://localhost:{frontend_port}/setup"
        print_info("First-run detected - opening setup wizard...")
        open_browser(setup_url)
    else:
        # Open dashboard
        dashboard_url = f"http://localhost:{frontend_port}"
        print_info("Opening dashboard...")
        open_browser(dashboard_url)

    # Step 9: Display status
    print_header("Services Running")
    print_success(f"API Server: http://localhost:{api_port}")
    print_success(f"API Docs: http://localhost:{api_port}/docs")

    if frontend_process:
        print_success(f"Frontend: http://localhost:{frontend_port}")

    print_info("\nPress Ctrl+C to stop all services")

    # Wait for processes
    try:
        api_process.wait()
    except KeyboardInterrupt:
        print_info("\nShutting down services...")
        api_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        print_success("Services stopped")

    return 0


@click.command()
@click.option("--check-only", is_flag=True, help="Only check dependencies without starting services")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def main(check_only: bool, verbose: bool) -> None:
    """
    GiljoAI MCP - Unified Startup Script

    This script handles the complete startup process for GiljoAI MCP,
    including dependency checking, database verification, and service launching.
    """
    try:
        exit_code = run_startup(check_only=check_only)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_info("\nStartup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
