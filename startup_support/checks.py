# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Pre-boot dependency / environment checks for startup.py (BE-9060 split).

Extracted verbatim from startup.py: interpreter/PostgreSQL/pip/npm detection,
database connectivity, first-run detection, default-settings seeding, and
the requirements self-heal. startup.py re-imports every public name so
`startup.<name>` remains a stable seam for tests and callers.
"""

import contextlib
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from startup_support.console import print_error, print_header, print_info, print_success, print_warning


# Minimum Python version for the CE runtime (moved with check_python_version).
MIN_PYTHON_VERSION = (3, 10)


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


def load_postgresql_config() -> dict | None:
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


def check_database_connectivity() -> tuple[bool, str | None]:
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


def check_first_run() -> tuple[bool, dict | None]:
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
    Seed default Settings rows for new categories (integrations, security).

    Reads current values from config.yaml for upgrade path, or uses defaults
    for fresh installs. Idempotent: skips categories that already have rows.

    BE-9148: the ``runtime`` category and the ``security.ssl_*``/``rate_limiting``
    and ``git_integration.include_commit_history``/``branch_strategy`` keys were
    retired here — they were seeded but never read. Existing installs keep any
    rows/keys already seeded (idempotent skip; the dead keys are simply never
    read); fresh installs no longer receive them.

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
                # BE-9103/BE-9148: no max_commits / include_commit_history / branch_strategy —
                # commit depth is the per-user Context-tab knob; only ``enabled`` gates fetch.
            },
            "serena_mcp": {
                "use_in_prompts": features.get("serena_mcp", {}).get("use_in_prompts", False),
            },
        }

        security_data = {
            # BE-9148: ssl_* is owned by the file-based ConfigManager and rate limiting by the
            # env-configured limiter; only cookie_domain_whitelist is a live DB-backed setting.
            "cookie_domain_whitelist": security_cfg.get("cookie_domain_whitelist", []),
        }

        import json

        categories_to_seed = {
            "integrations": json.dumps(integrations_data),
            "security": json.dumps(security_data),
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
        # PostgreSQL gets a pass here because we verify via DB connection
        if not result and required and "PostgreSQL" not in check_name:
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
    for module_name, _package_name in critical_packages:
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
        # Run pip install. Let pip stream live to the terminal (no capture_output)
        # so a 2-3 minute install does not look frozen, and so wheel-compile errors
        # (missing libpq-dev / gcc on Linux) are visible instead of black-holed.
        # --timeout 60 bounds each connection so a slow/dead PyPI mirror cannot wedge
        # the install indefinitely.
        # INF-9057: constrain to the shipped pinned tree when present, so a
        # boot-time self-heal cannot resolve a breaking upstream release from
        # the >= floors. Tolerates absence (older extracted release).
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_path), "--timeout", "60"]
        constraints_path = Path.cwd() / "requirements.lock"
        if constraints_path.exists():
            cmd += ["-c", str(constraints_path)]
        subprocess.run(
            cmd,
            check=True,
            timeout=300,  # 5 minute overall timeout
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
