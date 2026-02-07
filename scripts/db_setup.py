"""
DB Setup & Migration Helper

Safely creates a PostgreSQL database (if missing) and runs Alembic migrations.
Designed for zero-drama local installs and CI.

Usage examples (PowerShell):

  # Use DATABASE_URL from env (recommended)
  # e.g. $env:DATABASE_URL = "postgresql://postgres:***@localhost:5432/giljo_mcp"
  python scripts/db_setup.py

  # Or pass an explicit URL
  python scripts/db_setup.py --url postgresql://postgres:***@localhost:5432/giljo_mcp

Behavior:
- Ensures the target database exists (connects to 'postgres' db to create if needed)
- Runs `alembic upgrade head`
- If schema exists without Alembic version (legacy), stamps baseline then upgrades
- Prints clear, concise status messages
"""

from __future__ import annotations

import os
import subprocess
import sys
from contextlib import suppress
from dataclasses import dataclass
from typing import Optional


try:
    # SQLAlchemy URL parser is convenient and already a dependency
    from sqlalchemy.engine.url import make_url
except Exception:
    make_url = None  # type: ignore

try:
    import psycopg2  # type: ignore
    from psycopg2 import sql  # type: ignore
except Exception as e:  # pragma: no cover
    print(f"[ERROR] psycopg2 not available: {e}")
    sys.exit(1)


BASELINE_REVISION = os.getenv("ALEMBIC_BASELINE", "631adb011a79")


@dataclass
class DbConn:
    user: str
    password: str
    host: str
    port: int
    database: str


def parse_url(url: str) -> DbConn:
    if make_url is None:
        # Fallback minimal parser (postgresql://user:pass@host:port/db)
        import re

        m = re.match(r"^postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(\S+)$", url)
        if not m:
            raise ValueError("Unsupported DATABASE_URL format")
        return DbConn(
            user=m.group(1),
            password=m.group(2),
            host=m.group(3),
            port=int(m.group(4)),
            database=m.group(5),
        )

    u = make_url(url)
    return DbConn(
        user=str(u.username or "postgres"),
        password=str(u.password or ""),
        host=str(u.host or "localhost"),
        port=int(u.port or 5432),
        database=str(u.database or "postgres"),
    )


def ensure_database_exists(conn: DbConn) -> None:
    """Create the target database if it does not exist."""
    admin_db = DbConn(user=conn.user, password=conn.password, host=conn.host, port=conn.port, database="postgres")
    dsn_admin = f"dbname={admin_db.database} user={admin_db.user} password={admin_db.password} host={admin_db.host} port={admin_db.port}"
    try:
        with psycopg2.connect(dsn_admin) as cx:
            cx.autocommit = True
            with cx.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (conn.database,))
                exists = cur.fetchone() is not None
                if not exists:
                    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(conn.database)))
                    print(f"[OK] Created database: {conn.database}")
                else:
                    print(f"[OK] Database exists: {conn.database}")
    except psycopg2.Error as e:
        print(f"[ERROR] Failed to ensure database exists: {e}")
        sys.exit(1)


def run(cmd: list[str], env: Optional[dict[str, str]] = None) -> tuple[int, str, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    out, err = p.communicate()
    return p.returncode, out.strip(), err.strip()


def alembic_upgrade_head(env_vars: dict[str, str]) -> bool:
    code, out, err = run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env_vars)
    if code == 0:
        print("[OK] Alembic upgrade head completed")
        return True
    print("[WARN] Alembic upgrade failed. Output:")
    if out:
        print(out)
    if err:
        print(err)
    return False


def alembic_stamp_baseline(env_vars: dict[str, str], revision: str) -> bool:
    code, out, err = run([sys.executable, "-m", "alembic", "stamp", revision], env=env_vars)
    if code == 0:
        print(f"[OK] Alembic stamped baseline: {revision}")
        return True
    print("[ERROR] Alembic stamp failed. Output:")
    if out:
        print(out)
    if err:
        print(err)
    return False


def main() -> int:
    # Prefer explicit --url, else DATABASE_URL
    import argparse

    parser = argparse.ArgumentParser(description="Create DB if missing and run Alembic migrations")
    parser.add_argument("--url", dest="url", default=os.getenv("DATABASE_URL"), help="Postgres DATABASE_URL")
    args = parser.parse_args()

    if not args.url:
        print("[ERROR] DATABASE_URL not provided. Set env or pass --url.")
        return 2

    try:
        conn = parse_url(args.url)
    except Exception as e:
        print(f"[ERROR] Failed to parse DATABASE_URL: {e}")
        return 2

    # Ensure DB exists
    ensure_database_exists(conn)

    # Run migrations with env-provided DATABASE_URL
    env_vars = os.environ.copy()
    env_vars["DATABASE_URL"] = args.url

    if alembic_upgrade_head(env_vars):
        return 0

    # Retry: stamp baseline then upgrade (for legacy schemas without alembic_version)
    print("[INFO] Attempting baseline stamp then upgrade...")
    if not alembic_stamp_baseline(env_vars, BASELINE_REVISION):
        return 1
    if not alembic_upgrade_head(env_vars):
        return 1
    return 0


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        sys.exit(main())
