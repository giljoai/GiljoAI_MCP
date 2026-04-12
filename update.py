#!/usr/bin/env python3

# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Post-update script: apply pending database migrations after git pull.

Usage:
    python update.py

Does NOT touch config.yaml, agent templates, SSL certificates, or seed data.
"""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.resolve()


def _bootstrap_colorama() -> None:
    try:
        import colorama  # noqa: F401
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "colorama"],
            stdout=subprocess.DEVNULL,
        )


_bootstrap_colorama()

from colorama import Fore, Style  # noqa: E402
from colorama import init as colorama_init  # noqa: E402


colorama_init(autoreset=True)


def ok(msg: str) -> None:
    print(f"{Fore.GREEN}  [ok] {msg}{Style.RESET_ALL}")


def info(msg: str) -> None:
    print(f"{Fore.YELLOW}  [..] {msg}{Style.RESET_ALL}")


def err(msg: str) -> None:
    print(f"{Fore.RED}  [!!] {msg}{Style.RESET_ALL}")


def _build_db_url() -> str | None:
    """Return a DATABASE_URL, preferring the env var then falling back to config.yaml."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url

    config_path = ROOT / "config.yaml"
    if not config_path.exists():
        return None

    # Import here so we don't fail if src package isn't on the path yet
    sys.path.insert(0, str(ROOT))
    try:
        from src.giljo_mcp._config_io import read_config
    except ImportError:
        err("Could not import src.giljo_mcp._config_io. Is the virtual environment active?")
        return None

    config = read_config(config_path)
    db = config.get("database", {})

    host = db.get("host", "127.0.0.1")
    port = db.get("port", 5432)
    user = db.get("user") or db.get("username")
    password = db.get("password", "")
    name = db.get("name") or db.get("database")

    if not (user and name):
        return None

    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def _load_revision_registry() -> set[str]:
    """Load known revision IDs from the revision registry."""
    registry_path = ROOT / "migrations" / "revision_registry.json"
    if not registry_path.exists():
        return set()
    try:
        import json

        with open(registry_path) as f:
            data = json.load(f)
        return set(data.get("known_revisions", []))
    except (json.JSONDecodeError, OSError):
        return set()


def _get_revisions(db_url: str) -> tuple[str | None, str | None]:
    """Return (current_revision, head_revision). Either may be None on failure."""
    alembic_ini = ROOT / "alembic.ini"
    if not alembic_ini.exists():
        return None, None

    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from sqlalchemy import create_engine, text

        alembic_cfg = Config(str(alembic_ini))
        script = ScriptDirectory.from_config(alembic_cfg)
        head = script.get_current_head()

        engine = create_engine(db_url, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))  # Verify connectivity
            ctx = MigrationContext.configure(conn)
            current = ctx.get_current_revision()

        return current, head

    except Exception as exc:
        err(f"Could not read Alembic revision: {exc}")
        return None, None


def _stamp_bridge(db_url: str, current: str, head: str) -> bool:
    """Stamp the DB to the current head if the current revision is a known old one.

    After a baseline squash, old incremental revision IDs no longer exist in the
    migration chain. Alembic would fail trying to find an upgrade path. Instead,
    we stamp directly to the new head -- the schema is already correct because the
    squash absorbed all incrementals.

    Returns True if a stamp was applied, False otherwise.
    """
    known = _load_revision_registry()
    if not known:
        return False

    if current not in known:
        return False

    # Current revision is a known old one that's no longer in the active chain.
    # Check if Alembic can find it -- if not, we need to stamp.
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        alembic_cfg = Config(str(ROOT / "alembic.ini"))
        script = ScriptDirectory.from_config(alembic_cfg)

        # Try to get the revision object -- if it exists in the chain, no stamp needed
        try:
            script.get_revision(current)
            return False  # Revision exists in chain, normal upgrade will work
        except Exception:
            pass  # Revision not in chain -- need to stamp

        info(f"Bridging old revision {current} -> {head} (baseline was squashed)")

        proc = subprocess.run(
            [sys.executable, "-m", "alembic", "stamp", head],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(ROOT),
            env={**os.environ, "DATABASE_URL": db_url},
            check=False,
        )

        if proc.returncode == 0:
            ok(f"Stamped database to {head}")
            return True
        err(f"Stamp failed: {proc.stderr}")
        return False

    except Exception as exc:
        err(f"Stamp bridge error: {exc}")
        return False


def main() -> int:
    print()
    print(f"{Fore.YELLOW}  GiljoAI MCP — post-update{Style.RESET_ALL}")
    print()

    # --- Locate alembic.ini ---
    alembic_ini = ROOT / "alembic.ini"
    if not alembic_ini.exists():
        err("alembic.ini not found. Run from the project root.")
        return 1

    # --- Build database URL ---
    config_path = ROOT / "config.yaml"
    if not config_path.exists() and not os.environ.get("DATABASE_URL"):
        err("config.yaml not found and DATABASE_URL not set.")
        err("Run install.py first to generate your configuration.")
        return 1

    db_url = _build_db_url()
    if not db_url:
        err("Could not construct a database URL from config.yaml or DATABASE_URL env var.")
        err("Check that config.yaml contains a [database] section with host/port/user/name.")
        return 1

    # --- Check current vs head revision ---
    info("Checking database migration status...")
    current, head = _get_revisions(db_url)

    if head is None:
        err("Could not determine Alembic head revision. Check that alembic.ini is valid.")
        return 1

    if current is None and head is not None:
        info("Database has no recorded revision. Migrations will run from the beginning.")
    elif current == head:
        ok("Database is up to date.")
        print()
        return 0
    else:
        info(f"Current revision : {current or '(none)'}")
        info(f"Target revision  : {head}")

    # --- Stamp bridge for squashed baselines ---
    if current and current != head:
        stamped = _stamp_bridge(db_url, current, head)
        if stamped:
            # Re-check after stamp -- may already be at head
            current, head = _get_revisions(db_url)
            if current == head:
                ok("Database is up to date (after stamp bridge).")
                print()
                return 0

    # --- Run migrations ---
    info("Running database migrations...")
    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(ROOT),
        env={**os.environ, "DATABASE_URL": db_url},
        check=False,
    )

    if proc.returncode != 0:
        err("Migration failed.")
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)
        return 1

    applied = [line.strip() for line in proc.stdout.splitlines() if "Running upgrade" in line]
    if applied:
        ok(f"Applied {len(applied)} migration(s):")
        for migration in applied:
            info(f"  {migration}")
    else:
        ok("Migrations completed (nothing new to apply).")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
