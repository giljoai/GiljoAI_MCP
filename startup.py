#!/usr/bin/env python3

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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

import atexit
import contextlib
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import IO, Optional, Tuple


# NOTE: Third-party imports (click, colorama) are deferred until AFTER
# ensure_project_virtualenv() runs below. Otherwise `python startup.py`
# from a fresh shell (no venv activated) crashes with ModuleNotFoundError
# before the venv-relaunch guard ever fires. Keep this module's top section
# stdlib-only.


# ExitStack for managing log file handles that must outlive the function scope
# (passed to subprocess.Popen). Registered with atexit so handles close on exit.
_log_file_stack = contextlib.ExitStack()
atexit.register(_log_file_stack.close)


# ---------------------------------------------------------------------------
# Virtualenv guard: always relaunch inside the project-managed interpreter
# ---------------------------------------------------------------------------


def ensure_project_virtualenv() -> None:
    """Re-exec inside the installer-managed virtualenv when available.

    Uses subprocess.run() instead of os.execv() for cross-platform compatibility.

    Why not os.execv()?
    - On Unix: os.execv() replaces the current process (works correctly)
    - On Windows: os.execv() spawns a new process and exits immediately,
      losing the child's exit code and running the child in "background"

    The subprocess.run() + sys.exit() pattern works identically on all platforms:
    parent waits for child, then exits with child's return code.

    References:
    - https://github.com/python/cpython/issues/101191
    - https://bugs.python.org/issue19124
    """
    try:
        project_root = Path(__file__).resolve().parent
        venv_dir = project_root / "venv"

        if not venv_dir.exists():
            return

        # If we're already inside the project virtualenv, no action needed
        if Path(sys.prefix).resolve() == venv_dir.resolve():
            return

        # Find venv Python executable (platform-specific paths)
        if platform.system() == "Windows":
            venv_python = venv_dir / "Scripts" / "python.exe"
        else:
            # Try python first, fallback to python3
            venv_python = venv_dir / "bin" / "python"
            if not venv_python.exists():
                venv_python = venv_dir / "bin" / "python3"

        if not venv_python.exists():
            return

        print("Re-launching GiljoAI MCP startup inside project virtual environment...")

        # Cross-platform process replacement:
        # subprocess.run() waits for child and captures exit code
        # sys.exit() propagates the exit code to parent/shell
        result = subprocess.run([str(venv_python)] + sys.argv, check=False)
        sys.exit(result.returncode)

    except Exception as e:
        # Log error but continue - don't block startup entirely
        print(f"Warning: Could not activate venv: {e}", file=sys.stderr)
        return


if "pytest" not in sys.modules:
    ensure_project_virtualenv()

# Third-party imports — safe now that the venv guard above has re-executed
# us inside the project venv (when one exists). E402 is intentional: these
# MUST stay below ensure_project_virtualenv() or fresh-shell installs crash
# with ModuleNotFoundError before the relaunch guard can fire.
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


def load_postgresql_config() -> Optional[dict]:
    """
    Load PostgreSQL configuration from config.yaml if available.

    Returns:
        PostgreSQL config dict or None if not available
    """
    try:
        import yaml

        config_path = Path.cwd() / "config.yaml"

        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)

            # Get PostgreSQL configuration from database section
            return config.get("database", {}).get("postgresql")
    except Exception as e:
        print_warning(f"Could not read PostgreSQL config from config.yaml: {e}")

    return None


def check_postgresql_installed() -> bool:
    """
    Check if PostgreSQL is installed and accessible.

    We use a multi-layered approach:
    1. Check saved PostgreSQL paths from config.yaml (if available)
    2. Check if psql is in PATH
    3. Check common Windows installation paths
    4. Try to connect via Python (most reliable)

    Returns:
        True if PostgreSQL is available, False otherwise
    """
    # Method 1: Check saved PostgreSQL paths from installation
    postgresql_config = load_postgresql_config()
    if postgresql_config:
        psql_path = postgresql_config.get("psql_path")
        bin_path = postgresql_config.get("bin_path")
        discovery_method = postgresql_config.get("discovery_method", "UNKNOWN")

        if psql_path and Path(psql_path).exists():
            print_success(f"PostgreSQL detected from saved config: {psql_path}")
            print_info(f"Originally discovered via: {discovery_method}")

            # Add bin directory to PATH for session if needed
            if bin_path and bin_path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = f"{bin_path}{os.pathsep}{os.environ['PATH']}"
                print_info("Added PostgreSQL bin directory to PATH for this session")

            return True
        if psql_path:
            print_warning(f"Saved PostgreSQL path no longer exists: {psql_path}")
            print_info("Falling back to standard discovery methods...")

    # Method 2: Check PATH
    psql_path = shutil.which("psql")
    if psql_path:
        print_success(f"PostgreSQL detected at: {psql_path}")
        return True

    # Method 3: Check common installation paths on Windows
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

    # Method 4: Try to connect via Python (most reliable)
    # This will be tested in the database connectivity check
    print_warning("PostgreSQL command-line tools not found in PATH")
    print_info("Will verify PostgreSQL via database connectivity check...")
    return True  # Allow to proceed to database connectivity check


def check_pip_available() -> bool:
    """
    Check if pip is available (system PATH or venv).

    Returns:
        True if pip is available, False otherwise
    """
    pip_path = shutil.which("pip")

    if pip_path:
        print_success(f"pip detected at: {pip_path}")
        return True

    # Check venv pip (pip may not be on system PATH but exists in venv)
    venv_pip = Path.cwd() / "venv" / "Scripts" / "pip.exe"
    if not venv_pip.exists():
        venv_pip = Path.cwd() / "venv" / "bin" / "pip"
    if venv_pip.exists():
        print_success(f"pip detected in venv: {venv_pip}")
        return True

    print_error("pip not found in system PATH or venv")
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
            db_password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")

            if not db_password:
                raise SystemExit("Database password not configured. Run install.py or set POSTGRES_PASSWORD in .env")

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

    Queries the setup_state table directly for any row with
    first_admin_created=True. This is the definitive signal that
    install.py completed and the admin account was created via the
    setup wizard.

    Returns:
        Tuple of (is_first_run, state_dict)
    """
    try:
        import os

        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            # Try reading from config.yaml
            from src.giljo_mcp._config_io import read_config

            config = read_config()
            db_cfg = config.get("database", {})
            host = db_cfg.get("host", "127.0.0.1")
            port = db_cfg.get("port", 5432)
            user = db_cfg.get("user") or db_cfg.get("username", "")
            password = db_cfg.get("password", "")
            name = db_cfg.get("name") or db_cfg.get("database", "")
            if user and name:
                db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"

        if not db_url:
            print_warning("No database URL available - assuming first run")
            return True, None

        from sqlalchemy import create_engine, text

        engine = create_engine(db_url, connect_args={"connect_timeout": 5})
        try:
            with engine.connect() as conn:
                # Check if setup_state table exists and has a completed row
                row = conn.execute(
                    text(
                        "SELECT first_admin_created, database_initialized "
                        "FROM setup_state "
                        "WHERE first_admin_created = true "
                        "LIMIT 1"
                    )
                ).fetchone()

                if row is not None:
                    print_success("Setup completed previously - launching dashboard")
                    return False, {"first_admin_created": True, "database_initialized": True}

                print_info("First-run detected - setup wizard will open")
                return True, None
        finally:
            engine.dispose()

    except Exception as e:
        print_warning(f"Could not determine setup status: {e}")
        print_info("Assuming first-run - setup wizard will open")
        return True, None


def seed_default_settings() -> bool:
    """
    Seed default Settings rows for new categories (integrations, security, runtime).

    Reads current values from config.yaml for upgrade path, or uses defaults
    for fresh installs. Idempotent: skips categories that already have rows.

    Returns:
        True if seed completed (or no-op), False on error
    """
    import os

    try:
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            from src.giljo_mcp._config_io import read_config

            config = read_config()
            db_cfg = config.get("database", {})
            host = db_cfg.get("host", "127.0.0.1")
            port = db_cfg.get("port", 5432)
            user = db_cfg.get("user") or db_cfg.get("username", "")
            password = db_cfg.get("password", "")
            name = db_cfg.get("name") or db_cfg.get("database", "")
            if user and name:
                db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"

        if not db_url:
            return True  # No DB yet, skip silently

        from sqlalchemy import create_engine, text

        # Read config.yaml values for migration (defaults if missing)
        config = {}
        with contextlib.suppress(Exception):
            from src.giljo_mcp._config_io import read_config

            config = read_config()

        features = config.get("features", {})
        security_cfg = config.get("security", {})

        # Build seed data from config.yaml or defaults
        integrations_data = {
            "git_integration": {
                "enabled": features.get("git_integration", {}).get("enabled", False),
                "use_in_prompts": features.get("git_integration", {}).get("use_in_prompts", False),
                "include_commit_history": features.get("git_integration", {}).get("include_commit_history", True),
                "max_commits": features.get("git_integration", {}).get("max_commits", 50),
                "branch_strategy": features.get("git_integration", {}).get("branch_strategy", "main"),
            },
            "serena_mcp": {
                "use_in_prompts": features.get("serena_mcp", {}).get("use_in_prompts", False),
            },
        }

        security_data = {
            "ssl_enabled": features.get("ssl_enabled", False),
            "ssl_cert_path": config.get("paths", {}).get("ssl_cert"),
            "ssl_key_path": config.get("paths", {}).get("ssl_key"),
            "cookie_domain_whitelist": security_cfg.get("cookie_domain_whitelist", []),
            "rate_limiting": {"enabled": False, "requests_per_minute": 60},
        }

        runtime_data = {
            "agent": {
                "max_agents": config.get("agent", {}).get("max_agents", 10),
                "default_context_budget": config.get("agent", {}).get("default_context_budget", 200000),
                "context_warning_threshold": config.get("agent", {}).get("context_warning_threshold", 0.8),
            },
            "session": {
                "timeout_seconds": config.get("session", {}).get("timeout_seconds", 3600),
                "max_concurrent": config.get("session", {}).get("max_concurrent", 5),
                "cleanup_interval": config.get("session", {}).get("cleanup_interval", 300),
            },
        }

        import json

        categories_to_seed = {
            "integrations": json.dumps(integrations_data),
            "security": json.dumps(security_data),
            "runtime": json.dumps(runtime_data),
        }

        engine = create_engine(db_url, connect_args={"connect_timeout": 5})
        try:
            with engine.connect() as conn:
                # Check if settings table exists
                table_check = conn.execute(
                    text("SELECT EXISTS (  SELECT FROM information_schema.tables   WHERE table_name = 'settings')")
                ).scalar()
                if not table_check:
                    return True  # Table doesn't exist yet (fresh install, migrations not run)

                # Get all tenant keys (from users table — exists in both CE and SaaS)
                tenants = conn.execute(text("SELECT DISTINCT tenant_key FROM users")).fetchall()
                if not tenants:
                    return True  # No tenants yet

                seeded = 0
                for (tenant_key,) in tenants:
                    for category, data_json in categories_to_seed.items():
                        # Idempotency: only insert if row doesn't exist
                        exists = conn.execute(
                            text("SELECT 1 FROM settings WHERE tenant_key = :tk AND category = :cat LIMIT 1"),
                            {"tk": tenant_key, "cat": category},
                        ).scalar()

                        if not exists:
                            import uuid

                            conn.execute(
                                text(
                                    "INSERT INTO settings (id, tenant_key, category, settings_data) "
                                    "VALUES (:id, :tk, :cat, CAST(:data AS jsonb))"
                                ),
                                {
                                    "id": str(uuid.uuid4()),
                                    "tk": tenant_key,
                                    "cat": category,
                                    "data": data_json,
                                },
                            )
                            seeded += 1

                conn.commit()
                if seeded > 0:
                    print_success(f"Seeded {seeded} default settings row(s)")
                return True
        finally:
            engine.dispose()

    except Exception as e:
        print_warning(f"Settings seed failed (non-fatal): {e}")
        return True  # Non-fatal, startup continues


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """
    Check if a port is available.

    Args:
        port: Port number to check
        host: Host to check on

    Returns:
        True if port is available, False otherwise
    """
    with contextlib.suppress(Exception), socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        return result != 0  # Non-zero means port is available
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


def _get_network_mode() -> str:
    """Read security.network.mode from config.yaml. Returns 'localhost' if not set."""
    with contextlib.suppress(Exception):
        import yaml

        config_path = Path.cwd() / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            return config.get("security", {}).get("network", {}).get("mode", "localhost")
    return "localhost"


def get_deployment_context() -> str:
    """Read top-level `deployment_context` from config.yaml.

    Returns one of: 'localhost' (default), 'lan', 'demo', 'saas-production'.
    Controls browser auto-open host and status banner content.
    """
    with contextlib.suppress(Exception):
        import yaml

        config_path = Path.cwd() / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            return config.get("deployment_context", "localhost")
    return "localhost"


def _get_external_host() -> str:
    """Read services.external_host from config.yaml. Empty string if absent."""
    with contextlib.suppress(Exception):
        import yaml

        config_path = Path.cwd() / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            return config.get("services", {}).get("external_host", "") or ""
    return ""


def get_ssl_enabled() -> bool:
    """
    Check if SSL is enabled in config.yaml.
    Always returns False for localhost mode — SSL is only for LAN/WAN.

    Returns:
        True if ssl_enabled is set in features config AND not localhost mode
    """
    if _get_network_mode() == "localhost":
        return False
    with contextlib.suppress(Exception):
        import yaml

        config_path = Path.cwd() / "config.yaml"

        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)

            return bool(config.get("features", {}).get("ssl_enabled", False))

    return False


def get_network_ip() -> Optional[str]:
    """
    Get network IP address for display purposes.

    Respects the user's install-time network mode choice:
    - localhost mode → always returns None (caller falls back to "localhost")
    - auto/static/custom → reads from config or detects at runtime

    Returns:
        Network IP address or None if localhost mode
    """
    network_mode = _get_network_mode()

    # Localhost mode: honor the user's choice, don't detect LAN IPs
    if network_mode == "localhost":
        return None

    # LAN/WAN modes: try config.yaml first
    try:
        import yaml

        config_path = Path.cwd() / "config.yaml"

        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)

            # Prefer installer-configured external host for browser launch
            external_host = config.get("services", {}).get("external_host")
            if external_host and external_host not in ("localhost", "127.0.0.1", "0.0.0.0"):
                return external_host

            # Try server.ip first (legacy), then security.network.initial_ip
            network_ip = config.get("server", {}).get("ip")
            if not network_ip:
                network_ip = config.get("security", {}).get("network", {}).get("initial_ip")

            if network_ip:
                return network_ip

    except Exception as e:
        print_warning(f"Could not read network IP from config.yaml: {e}")

    # Fallback: Detect primary network IP at runtime (for LAN/WAN installs)
    try:
        import psutil

        # Virtual adapter patterns (reuse from api/endpoints/network.py)
        virtual_patterns = [
            "docker",
            "veth",
            "br-",
            "vmnet",
            "vboxnet",
            "virbr",
            "tun",
            "tap",
            "vEthernet",
            "Hyper-V",
            "WSL",
        ]
        loopback_patterns = ["lo", "Loopback"]

        interfaces = psutil.net_if_addrs()
        interface_stats = psutil.net_if_stats()

        candidates = []

        for interface_name, addresses in interfaces.items():
            # Check if virtual or loopback
            is_virtual = any(pattern.lower() in interface_name.lower() for pattern in virtual_patterns)
            is_loopback = any(pattern.lower() in interface_name.lower() for pattern in loopback_patterns)

            # Check if interface is active
            stats = interface_stats.get(interface_name)
            is_active = stats.isup if stats else False

            # Get IPv4 addresses
            for addr in addresses:
                if addr.family == 2:  # AF_INET (IPv4)
                    ip = addr.address

                    # Filter out loopback and link-local
                    if not ip.startswith("127.") and not ip.startswith("169.254.") and is_active and not is_loopback:
                        candidates.append({"name": interface_name, "ip": ip, "is_virtual": is_virtual})

        if candidates:
            # Prefer physical adapters over virtual ones
            physical = [c for c in candidates if not c["is_virtual"]]

            if physical:
                selected = physical[0]
                print_info(f"Detected primary network adapter: {selected['name']} ({selected['ip']})")
                return selected["ip"]
            # Fall back to first virtual adapter if no physical found
            selected = candidates[0]
            print_info(f"Detected network adapter: {selected['name']} ({selected['ip']})")
            return selected["ip"]

    except ImportError:
        print_warning("psutil not available for network detection")
    except Exception as e:
        print_warning(f"Could not detect network IP: {e}")

    return None


def start_api_server(verbose: bool = False) -> Optional[subprocess.Popen]:
    """
    Start the API server.

    Args:
        verbose: If True, show console window with output (Windows only)

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

        # Configure process creation for verbose mode
        popen_kwargs = {
            "cwd": str(Path.cwd()),
        }

        if verbose:
            if platform.system() == "Windows":
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
                print_success("API server will open in new console window")
            else:
                print_success("API server output will stream to this terminal (verbose mode)")
        else:
            # Background mode: hide output for quiet startup
            logs_dir = Path.cwd() / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            api_stdout: IO[str] = _log_file_stack.enter_context(
                open(logs_dir / "api_stdout.log", "a", buffering=1, encoding="utf-8")  # noqa: SIM115
            )
            api_stderr: IO[str] = _log_file_stack.enter_context(
                open(logs_dir / "api_stderr.log", "a", buffering=1, encoding="utf-8")  # noqa: SIM115
            )
            popen_kwargs["stdout"] = api_stdout
            popen_kwargs["stderr"] = api_stderr

        # Start API server
        process = subprocess.Popen([python_executable, str(api_script)], **popen_kwargs)

        print_success(f"API server started (PID: {process.pid})")
        if not verbose:
            print_info(f"API logs: {(Path.cwd() / 'logs' / 'api_stdout.log').resolve()!s}")
            print_info(f"API errors: {(Path.cwd() / 'logs' / 'api_stderr.log').resolve()!s}")
        return process

    except Exception as e:
        print_error(f"Failed to start API server: {e}")
        return None


def start_frontend_server(verbose: bool = False) -> Optional[subprocess.Popen]:
    """
    Start the frontend development server.

    In production mode (frontend/dist/ exists and --dev not set), returns None
    so FastAPI serves the pre-built frontend. In development mode, launches
    the Vite dev server as before.

    Args:
        verbose: If True, show console window with output (Windows only)

    Returns:
        Popen process object, or None if production mode or failed
    """
    dev_mode = "--dev" in sys.argv

    if dev_mode:
        print_info("Development mode (--dev): launching Vite dev server")
    else:
        dist_index = Path.cwd() / "frontend" / "dist" / "index.html"
        if dist_index.exists():
            api_port, _ = get_config_ports()
            print_success("Production frontend detected (frontend/dist/)")
            print_info(f"Frontend served by FastAPI on port {api_port}")
            return None

    try:
        frontend_dir = Path.cwd() / "frontend"

        if not frontend_dir.exists():
            print_warning("Frontend directory not found - skipping frontend")
            return None

        # Get full path to npm executable (required for Windows subprocess)
        npm_executable = shutil.which("npm")
        if not npm_executable:
            print_warning("npm not found in PATH - skipping frontend server")
            return None

        # Check if node_modules is properly installed (.package-lock.json is written by npm install)
        if not (frontend_dir / "node_modules" / ".package-lock.json").exists():
            print_info("Installing frontend dependencies...")
            subprocess.run([npm_executable, "install"], cwd=str(frontend_dir), check=True)

        # Configure process creation for verbose mode
        popen_kwargs = {
            "cwd": str(frontend_dir),
        }

        if verbose:
            if platform.system() == "Windows":
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
                print_success("Frontend server will open in new console window")
            else:
                print_success("Frontend output will stream to this terminal (verbose mode)")
        else:
            # Background mode: hide output for quiet startup
            logs_dir = Path.cwd() / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            fe_stdout: IO[str] = _log_file_stack.enter_context(
                open(logs_dir / "frontend_stdout.log", "a", buffering=1, encoding="utf-8")  # noqa: SIM115
            )
            fe_stderr: IO[str] = _log_file_stack.enter_context(
                open(logs_dir / "frontend_stderr.log", "a", buffering=1, encoding="utf-8")  # noqa: SIM115
            )
            popen_kwargs["stdout"] = fe_stdout
            popen_kwargs["stderr"] = fe_stderr

        # Start frontend server (use full path to npm on Windows)
        process = subprocess.Popen([npm_executable, "run", "dev"], **popen_kwargs)

        print_success(f"Frontend server started (PID: {process.pid})")
        if not verbose:
            print_info(f"Frontend logs: {(Path.cwd() / 'logs' / 'frontend_stdout.log').resolve()!s}")
            print_info(f"Frontend errors: {(Path.cwd() / 'logs' / 'frontend_stderr.log').resolve()!s}")
        return process

    except FileNotFoundError:
        print_warning("npm not found - skipping frontend server")
        return None
    except Exception as e:
        print_error(f"Failed to start frontend server: {e}")
        return None


def wait_for_api_ready(port: int, max_attempts: int = 60, interval: float = 0.5, ssl_enabled: bool = False) -> bool:
    """
    Wait for API server to be ready by checking /health endpoint.

    Args:
        port: API port number
        max_attempts: Maximum number of attempts (default 60 = 30 seconds)
        interval: Interval between attempts in seconds
        ssl_enabled: If True, use https:// for health check

    Returns:
        True if API is ready, False if timeout
    """
    import ssl
    import urllib.error
    import urllib.request

    protocol = "https" if ssl_enabled else "http"
    url = f"{protocol}://localhost:{port}/health"
    print_info(f"Waiting for API to be ready (max {max_attempts * interval:.0f}s)...")

    # For HTTPS with mkcert self-signed certs, skip certificate verification
    ssl_context = None
    if ssl_enabled:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=1, context=ssl_context) as response:
                if response.status == 200:
                    print_success(f"API ready after {attempt * interval:.1f}s")
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            if attempt % 10 == 0:
                print_info(f"Still waiting... ({attempt * interval:.0f}s elapsed)")
            time.sleep(interval)
        except Exception as e:
            print_warning(f"Unexpected error checking API health: {e}")
            time.sleep(interval)

    print_error(f"API did not become ready within {max_attempts * interval:.0f}s timeout")
    return False


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


def _choose_browser_target(deployment_context: str, is_first_run: bool) -> str | None:
    """Pure helper: pick the auto-open route based on deployment_context.

    Branch order is load-bearing — demo/saas must win over the CE first-run and
    dashboard fallbacks, so demo installs never flash `/welcome` before the
    frontend `route_signal` bounce.

    Args:
        deployment_context: Value from config.yaml top-level `deployment_context`
            (one of 'localhost', 'lan', 'demo', 'saas-production').
        is_first_run: True when the CE first-run wizard has not yet completed.

    Returns:
        - "/demo-landing" for demo deployments.
        - `None` for saas-production (signals the caller to suppress auto-open).
        - "/welcome" for CE first-run (localhost / lan).
        - "" (dashboard root) for any other CE launch.

    No side effects; safe to call from tests.
    """
    if deployment_context == "saas-production":
        return None
    if deployment_context == "demo":
        return "/demo-landing"
    if is_first_run:
        return "/welcome"
    return ""


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
        subprocess.run(
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


def _patch_env_from_config() -> None:
    """Check .env for missing variables and patch them from config.yaml.

    Runs once per startup. Reads config.yaml to derive values that the
    installer should have written but didn't (e.g., GILJO_PUBLIC_URL on
    LAN/WAN installs before this fix shipped). Appends missing entries
    to .env so they persist across restarts.
    """
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return

    try:
        env_text = env_path.read_text(encoding="utf-8")
    except OSError:
        return

    patches: list[str] = []

    # --- GILJO_PUBLIC_URL: required for MCP tool download links on LAN/WAN ---
    if "GILJO_PUBLIC_URL" not in env_text:
        external_host = _get_external_host()
        if external_host and external_host != "localhost":
            ssl_enabled = get_ssl_enabled()
            api_port, _ = get_config_ports()
            proto = "https" if ssl_enabled else "http"
            public_url = f"{proto}://{external_host}:{api_port}"
            patches.append(f"GILJO_PUBLIC_URL={public_url}")
            os.environ["GILJO_PUBLIC_URL"] = public_url
            print_info(f"Patched .env: GILJO_PUBLIC_URL={public_url}")

    if patches:
        try:
            with open(env_path, "a", encoding="utf-8") as f:
                f.write("\n# Auto-patched by startup.py\n")
                for patch in patches:
                    f.write(f"{patch}\n")
            print_success(f"Added {len(patches)} missing variable(s) to .env")
        except OSError as e:
            print_warning(f"Could not patch .env: {e}")


def _check_and_stamp_migration_version() -> None:
    """Detect old migration revisions and stamp to baseline_v37.

    After a CE export squash, the old revision IDs no longer exist as files.
    This bridges existing databases to the new baseline so alembic upgrade head works.

    Stamping only updates alembic_version — it does NOT run DDL. So we also
    apply any missing columns/tables that were added between the old revision
    and baseline_v37, using IF NOT EXISTS / IF EXISTS for idempotency.
    """
    try:
        from sqlalchemy import text

        from src.giljo_mcp.database import DatabaseManager

        db_url = _get_database_url()
        if not db_url:
            return

        db_manager = DatabaseManager(database_url=db_url, is_async=False)
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            current = result.scalar()

            if not current or current == "baseline_v37":
                # Even at baseline_v37, schema may be incomplete if a prior
                # stamp jumped ahead without DDL. Run the heal pass anyway.
                _heal_schema_to_v37(session)
                return

            # Any revision that is not baseline_v37 needs stamping forward
            print_info(f"Stamping migration: {current} -> baseline_v37")
            _heal_schema_to_v37(session)
            session.execute(text("UPDATE alembic_version SET version_num = 'baseline_v37'"))
            session.commit()
            print_success("Migration version updated to baseline_v37")

    except Exception as e:
        print_warning(f"Migration version check skipped: {e}")


def _heal_schema_to_v37(session) -> None:
    """Apply any DDL that baseline_v37 expects but may be missing.

    Every statement is idempotent (IF NOT EXISTS / IF EXISTS) so it is safe
    to run on databases that are already fully up-to-date.
    """
    from sqlalchemy import text

    heal_statements = [
        # Columns added between baseline_v36 and baseline_v37
        "ALTER TABLE agent_templates ADD COLUMN IF NOT EXISTS user_managed_export BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS org_setup_complete BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE projects ADD COLUMN IF NOT EXISTS hidden BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE agent_executions ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ",
        # Table added in baseline_v37
        (
            "CREATE TABLE IF NOT EXISTS product_agent_assignments ("
            "  id VARCHAR(36) PRIMARY KEY,"
            "  product_id VARCHAR(36) NOT NULL REFERENCES products(id) ON DELETE CASCADE,"
            "  template_id VARCHAR(36) NOT NULL REFERENCES agent_templates(id) ON DELETE CASCADE,"
            "  is_active BOOLEAN NOT NULL DEFAULT true,"
            "  tenant_key VARCHAR(36) NOT NULL,"
            "  created_at TIMESTAMPTZ DEFAULT now(),"
            "  updated_at TIMESTAMPTZ"
            ")"
        ),
        # Indexes and constraints for the new table (IF NOT EXISTS)
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_product_template_assignment ON product_agent_assignments (product_id, template_id)",
        "CREATE INDEX IF NOT EXISTS idx_assignment_tenant ON product_agent_assignments (tenant_key)",
        "CREATE INDEX IF NOT EXISTS idx_assignment_product ON product_agent_assignments (product_id)",
        "CREATE INDEX IF NOT EXISTS idx_assignment_template ON product_agent_assignments (template_id)",
        "CREATE INDEX IF NOT EXISTS idx_assignment_active ON product_agent_assignments (is_active)",
        # Orphan tables dropped in baseline_v37
        "DROP TABLE IF EXISTS discovery_config CASCADE",
        "DROP TABLE IF EXISTS git_configs CASCADE",
        "DROP TABLE IF EXISTS optimization_rules CASCADE",
        "DROP TABLE IF EXISTS optimization_metrics CASCADE",
        # Unique constraint swap on agent_templates (product-scoped -> tenant-scoped)
        "ALTER TABLE agent_templates DROP CONSTRAINT IF EXISTS uq_template_product_name_version",
        "DROP INDEX IF EXISTS idx_template_product",
    ]

    # Tenant-scoped unique constraint (idempotent via existence check)
    heal_statements.append(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_template_tenant_name_version') THEN "
        "ALTER TABLE agent_templates ADD CONSTRAINT uq_template_tenant_name_version UNIQUE (tenant_key, name, version); "
        "END IF; END $$"
    )

    applied = 0
    for stmt in heal_statements:
        try:
            session.execute(text(stmt))
            applied += 1
        except Exception as e:
            print_warning(f"Schema heal skipped: {e}")
    session.commit()
    if applied:
        print_info(f"Schema heal: {applied}/{len(heal_statements)} statements applied")


def _get_database_url() -> Optional[str]:
    """Build database URL from environment (same source as check_database_connectivity)."""
    with contextlib.suppress(Exception):
        from dotenv import load_dotenv

        load_dotenv()

        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url

        from urllib.parse import quote_plus

        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "giljo_mcp")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "")
        if not db_password:
            return None
        return f"postgresql://{db_user}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"
    return None


def run_database_migrations() -> bool:
    """
    Run database migrations using Alembic.

    Returns:
        True if migrations are successful, False otherwise
    """
    print_header("Running Database Migrations")

    # Bridge old migration revisions to baseline_v36 before running alembic
    _check_and_stamp_migration_version()

    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,  # 5 minute timeout
        )
        print_success("Database migrations successful")
        return True
    except subprocess.TimeoutExpired:
        print_error("Database migrations timed out (exceeded 5 minutes)")
        return False
    except subprocess.CalledProcessError as e:
        print_error(f"Database migrations failed with return code {e.returncode}")
        if e.stderr:
            print_error(f"Error details: {e.stderr}")
        return False
    except Exception as e:
        print_error(f"Unexpected error during database migrations: {e}")
        return False


def run_startup(
    check_only: bool = False,
    verbose: bool = False,
    no_browser: bool = False,
    no_migrations: bool = False,
    no_ssl: bool = False,
) -> int:
    """
    Main startup function.

    Args:
        check_only: If True, only check dependencies without starting services
        verbose: If True, show console windows for API/frontend (Windows only)
        no_browser: If True, skip automatic browser launch
        no_migrations: If True, skip automatic database migrations
        no_ssl: If True, force HTTP even if HTTPS is configured

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

    # Register giljo_mcp as importable package (editable install, idempotent)
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".", "--quiet"],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as e:
        print_warning(f"Editable install failed (non-fatal): {e.stderr[:200] if e.stderr else e}")
    except Exception as e:
        print_warning(f"Editable install skipped: {e}")

    # Step 2.5: Download NLTK data for vision document summarization
    print_header("Downloading NLTK Data")
    try:
        import nltk

        # Check if punkt_tab is already downloaded
        try:
            nltk.data.find("tokenizers/punkt_tab")
            print_success("NLTK punkt tokenizer already downloaded")
        except LookupError:
            print_info("Downloading NLTK punkt tokenizer...")
            nltk.download("punkt", quiet=True)
            nltk.download("punkt_tab", quiet=True)
            print_success("NLTK data downloaded successfully")
    except Exception as e:
        print_warning(f"Failed to download NLTK data: {e}")
        print_info("Vision document summarization may not work properly")

    # Step 2.9: Patch .env with missing variables derived from config.yaml
    _patch_env_from_config()

    # Step 3: Run database migrations
    if not no_migrations:
        if not run_database_migrations():
            print_error("Database migrations failed")
            return 1
    else:
        print_info("Skipping database migrations as requested")

    # Step 4: Check database connectivity
    print_header("Database Connectivity")
    print_info("Checking database connection...")
    db_success, db_error = check_database_connectivity()

    if not db_success:
        print_error("Database connectivity check failed")
        print_info("Please ensure PostgreSQL is running and configured correctly")
        return 1

    # Step 4b: Seed default settings (idempotent, non-fatal)
    seed_default_settings()

    # Step 5: Check first-run status
    print_header("Setup Status")
    print_info("Checking setup completion status...")
    is_first_run, state = check_first_run()

    # Step 6: Get ports and SSL config
    api_port, frontend_port = get_config_ports()
    ssl_enabled = get_ssl_enabled() and not no_ssl
    if no_ssl and get_ssl_enabled():
        print_warning("SSL disabled via --no-ssl flag (HTTP mode forced)")
    http_proto = "https" if ssl_enabled else "http"

    # Step 7: Check port availability
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

    # Step 8: Start services
    print_header("Starting Services")

    if verbose:
        print_info("Verbose mode enabled - services will open in separate console windows")

    # Always rebuild frontend before starting API so static files are current.
    # Must complete before API starts — the API mounts dist/ at init time.
    dev_mode = "--dev" in sys.argv
    frontend_dir = Path.cwd() / "frontend"
    if not dev_mode and frontend_dir.exists() and (frontend_dir / "package.json").exists():
        print_info("Rebuilding frontend...")
        npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"
        # Ensure node_modules exist
        if not (frontend_dir / "node_modules" / ".package-lock.json").exists():
            print_info("Installing frontend dependencies...")
            subprocess.run([npm_cmd, "install"], cwd=str(frontend_dir), check=True)
        build_result = subprocess.run(
            [npm_cmd, "run", "build"],
            cwd=str(frontend_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if build_result.returncode == 0:
            print_success("Frontend build complete")
        else:
            print_warning("Frontend build failed -- using existing dist/ if available")
            if verbose:
                print_warning(build_result.stderr[:500] if build_result.stderr else "No error output")

    print_info("Starting API server...")
    api_process = start_api_server(verbose=verbose)

    if not api_process:
        print_error("Failed to start API server")
        return 1

    print_info("Starting frontend server...")
    frontend_process = start_frontend_server(verbose=verbose)

    # Step 8.5: Wait for API to be ready before opening browser
    print_header("Waiting for Services")
    api_ready = wait_for_api_ready(api_port, max_attempts=60, interval=0.5, ssl_enabled=ssl_enabled)

    if not api_ready:
        print_warning("API did not respond to health check, but continuing anyway")
        print_warning("You may see connection errors in the browser initially")

    # Step 9: Open browser
    # In production mode (no Vite), browser should point to the API port
    # since FastAPI serves both the API and the frontend static files.
    production_mode = frontend_process is None and (Path.cwd() / "frontend" / "dist" / "index.html").exists()
    browser_port = api_port if production_mode else frontend_port

    print_header("Opening Browser")

    # Determine the correct host for browser URLs based on deployment_context.
    # - localhost / lan: current behavior (network IP if configured, else localhost)
    # - demo: operator is on the host; auto-open always uses 127.0.0.1 (Cloudflare
    #         Tunnel fronts the public URL, not the loopback bind)
    # - saas-production: no desktop browser; auto-open is suppressed entirely
    deployment_context = get_deployment_context()
    external_host = _get_external_host()
    network_host = get_network_ip() or "localhost"

    if deployment_context == "demo":
        server_host = "127.0.0.1"
    else:
        server_host = network_host

    suppress_browser = deployment_context == "saas-production"

    if no_browser or suppress_browser:
        if suppress_browser:
            print_info("saas-production mode: browser auto-open disabled (operator mode)")
        else:
            print_info("Login to your server to begin setup!")
            print_success(f"Setup URL: {http_proto}://{server_host}:{browser_port}/setup")

        print_header("Welcome to GiljoAI MCP! -Gil")
    else:
        # Branch order (demo/saas → CE first-run → dashboard) lives in the pure
        # helper above so tests and production share one source of truth.
        # saas-production returns None defensively; `suppress_browser` above
        # already short-circuits that mode.
        target_route = _choose_browser_target(deployment_context, is_first_run)
        if target_route is None:
            print_info("saas-production mode: browser auto-open disabled (operator mode)")
        else:
            auto_open_url = f"{http_proto}://{server_host}:{browser_port}{target_route}"
            if target_route == "/demo-landing":
                print_info(f"{deployment_context} mode detected - opening demo landing page...")
            elif target_route == "/welcome":
                print_info("First-run detected - opening welcome setup screen...")
            else:
                print_info("Opening dashboard...")
            open_browser(auto_open_url, delay=2)

    # Step 10: Display status
    mode_label = "PRODUCTION" if production_mode else "DEVELOPMENT"
    print_header(f"Services Running ({mode_label})")
    print_success(f"API Server: {http_proto}://{server_host}:{api_port}")
    print_success(f"API Docs: {http_proto}://{server_host}:{api_port}/docs")

    if production_mode:
        print_success(f"Frontend (Production): {http_proto}://{server_host}:{api_port}")
    elif frontend_process:
        print_success(f"Frontend (Dev): {http_proto}://{server_host}:{frontend_port}")

    # Deployment-context-aware banner extras
    if deployment_context == "demo" and external_host:
        # Cloudflare Tunnel terminates TLS; public scheme is always https.
        print_success(f"Public URL (via Cloudflare Tunnel): https://{external_host}")
    elif deployment_context == "saas-production":
        print_info("saas-production mode: operator console only (no auto-open)")

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


def stop_services() -> int:
    """Stop all running GiljoAI MCP services by finding and terminating their processes."""
    print_info("Stopping GiljoAI MCP services...")

    stopped = 0

    # Find and kill API server (run_api.py)
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                [
                    "wmic",
                    "process",
                    "where",
                    "CommandLine like '%run_api.py%' and Name='python.exe'",
                    "get",
                    "ProcessId",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.strip().split("\n")[1:]:
                pid = line.strip()
                if pid.isdigit():
                    subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, timeout=10)
                    print_success(f"Stopped API server (PID: {pid})")
                    stopped += 1
        else:
            result = subprocess.run(
                ["pgrep", "-f", "run_api.py"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for pid in result.stdout.strip().split("\n"):
                if pid.strip().isdigit():
                    subprocess.run(["kill", pid.strip()], capture_output=True, timeout=10)
                    print_success(f"Stopped API server (PID: {pid.strip()})")
                    stopped += 1
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Find and kill frontend dev server (npm/vite)
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["wmic", "process", "where", "CommandLine like '%vite%' and Name='node.exe'", "get", "ProcessId"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.strip().split("\n")[1:]:
                pid = line.strip()
                if pid.isdigit():
                    subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, timeout=10)
                    print_success(f"Stopped frontend server (PID: {pid})")
                    stopped += 1
        else:
            result = subprocess.run(
                ["pgrep", "-f", "vite"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for pid in result.stdout.strip().split("\n"):
                if pid.strip().isdigit():
                    subprocess.run(["kill", pid.strip()], capture_output=True, timeout=10)
                    print_success(f"Stopped frontend server (PID: {pid.strip()})")
                    stopped += 1
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    if stopped == 0:
        print_info("No running GiljoAI services found")
    else:
        print_success(f"Stopped {stopped} service(s)")

    return 0


@click.command()
@click.option("--check-only", is_flag=True, help="Only check dependencies without starting services")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output (show console windows on Windows)")
@click.option("--no-browser", is_flag=True, help="Skip automatic browser launch (show URLs instead)")
@click.option("--no-migrations", is_flag=True, help="Skip automatic database migrations")
@click.option("--no-ssl", is_flag=True, help="Force HTTP even if HTTPS is configured (for Docker/CI/reverse-proxy)")
@click.option("--stop", is_flag=True, help="Stop all running GiljoAI services")
@click.option("--dev", is_flag=True, help="Force development mode (Vite dev server with hot-reload)")
def main(
    check_only: bool, verbose: bool, no_browser: bool, no_migrations: bool, no_ssl: bool, stop: bool, dev: bool
) -> None:
    """
    GiljoAI MCP - Unified Startup Script

    This script handles the complete startup process for GiljoAI MCP,
    including dependency checking, database verification, and service launching.

    Production mode is automatic when frontend/dist/ exists.
    Use --dev to force Vite dev server with hot-reload.
    """
    exit_code = 0
    try:
        if stop:
            exit_code = stop_services()
        else:
            exit_code = run_startup(
                check_only=check_only,
                verbose=verbose,
                no_browser=no_browser,
                no_migrations=no_migrations,
                no_ssl=no_ssl,
            )
    except KeyboardInterrupt:
        print_info("\nStartup cancelled by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        exit_code = 1
    finally:
        # Keep window open on error so the user can read the output
        if exit_code != 0:
            print_error("\nStartup failed. Press Enter to close this window...")
            try:
                input()
            except EOFError:
                pass
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
