# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [SAAS] SaaS Edition - includes demo bootstrap behavior verification.

"""
Integration tests for the re-architected demo/SaaS migration bootstrap.

The dual-chain (CE + SaaS) Alembic flow now lives in ``demo/startup_demo.py``
(a private demo/SaaS-only entrypoint excluded from CE export). The public
``alembic.ini`` and ``startup.py`` are single-chain CE-only.

These tests verify the new architecture against a REAL scratch PostgreSQL DB:

  Cold demo init     -- empty DB + run_database_migrations_demo() ->
                        both CE and SaaS tables present, alembic_version is
                        VARCHAR(64), both chain heads stamped.
  Warm demo idem.    -- second run_database_migrations_demo() is a no-op.
  Cold CE init       -- empty DB + startup.run_database_migrations() ->
                        only CE tables; no SaaS tables; no errors.
  Warm CE idem.      -- a DB at baseline_v37 cleanly applies ce_0003 then
                        a second run is a no-op.
  Pre-stamp widen    -- pre-create alembic_version VARCHAR(128); calling
                        _ensure_alembic_version_table_widened is a no-op
                        and never narrows.
  Pre-stamp create   -- empty DB; _ensure_alembic_version_table_widened
                        bootstrap-creates alembic_version with VARCHAR(64).

SAFETY: A scratch DB is used (default ``giljo_test_bootstrap``). The live
demo DB ``giljo_mcp`` is NEVER touched. Each test recreates schema state
inside the scratch DB; the DB itself is reused across tests for speed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Module-level configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"

SCRATCH_DB = os.environ.get("GILJO_BOOTSTRAP_TEST_DB", "giljo_test_bootstrap")
ADMIN_USER = os.environ.get("POSTGRES_OWNER_USER", "giljo_owner")
ADMIN_PASSWORD = os.environ.get("POSTGRES_OWNER_PASSWORD", "")
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = os.environ.get("POSTGRES_PORT", "5432")

PRODUCTION_DB_NAME = "giljo_mcp"


def _scratch_db_url() -> str:
    """Compose a scratch-DB connection URL and refuse to target production."""
    if SCRATCH_DB == PRODUCTION_DB_NAME:
        raise RuntimeError(
            "SAFETY GUARD: Refusing to run bootstrap tests against the "
            "production DB name 'giljo_mcp'. Override GILJO_BOOTSTRAP_TEST_DB."
        )
    if not ADMIN_PASSWORD:
        # Fallback: read .env file used by the demo deployment.
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("POSTGRES_OWNER_PASSWORD="):
                    pw = line.split("=", 1)[1].strip()
                    if pw:
                        return f"postgresql://{ADMIN_USER}:{pw}@{DB_HOST}:{DB_PORT}/{SCRATCH_DB}"
        raise RuntimeError("POSTGRES_OWNER_PASSWORD is not set; cannot connect to scratch DB.")
    return f"postgresql://{ADMIN_USER}:{ADMIN_PASSWORD}@{DB_HOST}:{DB_PORT}/{SCRATCH_DB}"


def _scratch_engine() -> sa.Engine:
    return sa.create_engine(_scratch_db_url(), poolclass=sa.pool.NullPool)


def _drop_all_objects(engine: sa.Engine) -> None:
    """Drop every public-schema object so the next test starts empty."""
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text(f"GRANT ALL ON SCHEMA public TO {ADMIN_USER}"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.commit()


def _build_env(*, giljo_mode: str | None) -> dict[str, str]:
    """Build a child-process env that points the demo/CE entrypoints at the scratch DB."""
    env = os.environ.copy()
    url = _scratch_db_url()
    env["DATABASE_URL"] = url
    env["POSTGRES_HOST"] = DB_HOST
    env["POSTGRES_PORT"] = DB_PORT
    env["POSTGRES_DB"] = SCRATCH_DB
    env["POSTGRES_USER"] = ADMIN_USER
    # _get_database_url() in startup.py reads DB_* not POSTGRES_*; mirror them.
    env["DB_HOST"] = DB_HOST
    env["DB_PORT"] = DB_PORT
    env["DB_NAME"] = SCRATCH_DB
    env["DB_USER"] = ADMIN_USER
    # Password may have come from .env -- pull from the URL directly to be safe.
    # postgresql://user:PASS@host:port/db
    pwd = url.split("//", 1)[1].split("@", 1)[0].split(":", 1)[1]
    env["POSTGRES_PASSWORD"] = pwd
    env["DB_PASSWORD"] = pwd
    if giljo_mode is None:
        env.pop("GILJO_MODE", None)
    else:
        env["GILJO_MODE"] = giljo_mode
    return env


def _run_demo_migrations() -> subprocess.CompletedProcess[str]:
    """Invoke ``run_database_migrations_demo`` via a fresh subprocess.

    Subprocess isolation is required because demo/startup_demo.py monkey-patches
    ``startup.run_database_migrations`` at import; we want each test to see a
    pristine import state.
    """
    code = (
        "import sys, os; "
        "sys.path.insert(0, os.getcwd()); "
        "from demo.startup_demo import run_database_migrations_demo; "
        "ok = run_database_migrations_demo(); "
        "sys.exit(0 if ok else 1)"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        env=_build_env(giljo_mode="demo"),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def _run_ce_migrations() -> subprocess.CompletedProcess[str]:
    """Invoke the public single-chain ``startup.run_database_migrations``."""
    code = (
        "import sys, os; "
        "sys.path.insert(0, os.getcwd()); "
        "import startup; "
        "ok = startup.run_database_migrations(); "
        "sys.exit(0 if ok else 1)"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        env=_build_env(giljo_mode=None),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def _run_alembic_target(target: str) -> subprocess.CompletedProcess[str]:
    """Run a single-chain ``alembic upgrade <target>`` against the scratch DB.

    Used only to set up partial CE state for the warm-CE idempotency test.
    """
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), "upgrade", target],
        cwd=str(PROJECT_ROOT),
        env=_build_env(giljo_mode=None),
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


def _table_exists(engine: sa.Engine, name: str) -> bool:
    insp = sa.inspect(engine)
    return name in insp.get_table_names()


def _column_exists(engine: sa.Engine, table: str, column: str) -> bool:
    insp = sa.inspect(engine)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _stamped_versions(engine: sa.Engine) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT version_num FROM alembic_version")).all()
    return sorted(r[0] for r in rows)


def _alembic_version_column_length(engine: sa.Engine) -> int | None:
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "AND table_name = 'alembic_version' "
                "AND column_name = 'version_num'"
            )
        ).scalar()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def scratch_engine():
    eng = _scratch_engine()
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    yield eng
    eng.dispose()


@pytest.fixture
def empty_scratch_db(scratch_engine: sa.Engine):
    _drop_all_objects(scratch_engine)
    yield scratch_engine
    _drop_all_objects(scratch_engine)


# ---------------------------------------------------------------------------
# CE / SaaS table catalogue
# ---------------------------------------------------------------------------

CE_TABLES_SAMPLE = (
    "organizations",
    "users",
    "projects",
    "agent_templates",
    "alembic_version",
)

SAAS_TABLES_REQUIRED = (
    "password_reset_tokens",
    "tenant_trials",
    "ops_actions_log",
    "account_deletion_requests",
)


# ---------------------------------------------------------------------------
# Scenario tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSaasMigrationBootstrap:
    """Six real-DB migration scenarios for the new dual-chain architecture."""

    # --- Scenario 1: cold demo init --------------------------------------
    def test_cold_demo_init_brings_up_both_chains(self, empty_scratch_db: sa.Engine) -> None:
        result = _run_demo_migrations()
        assert result.returncode == 0, (
            f"run_database_migrations_demo() failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

        for tbl in CE_TABLES_SAMPLE:
            assert _table_exists(empty_scratch_db, tbl), f"CE table '{tbl}' missing after cold demo init"
        for tbl in SAAS_TABLES_REQUIRED:
            assert _table_exists(empty_scratch_db, tbl), f"SaaS table '{tbl}' missing after cold demo init"

        assert _column_exists(empty_scratch_db, "organizations", "org_setup_complete"), (
            "organizations.org_setup_complete missing after cold demo init"
        )

        # Dual-chain heads stamped.
        versions = _stamped_versions(empty_scratch_db)
        assert any(v.startswith("ce_") or v == "baseline_v37" for v in versions), (
            f"No CE head stamped after cold demo init. Got: {versions}"
        )
        assert any(v.startswith("saas_") for v in versions), (
            f"No SaaS head stamped after cold demo init. Got: {versions}"
        )

        # Bootstrap widened the column to >= 64.
        col_len = _alembic_version_column_length(empty_scratch_db)
        assert col_len is not None and col_len >= 64, f"alembic_version.version_num expected >= 64 chars, got {col_len}"

    # --- Scenario 2: warm demo idempotency -------------------------------
    def test_warm_demo_idempotent(self, empty_scratch_db: sa.Engine) -> None:
        first = _run_demo_migrations()
        assert first.returncode == 0, f"First demo migrate failed:\n{first.stdout}\n{first.stderr}"
        versions_after_first = _stamped_versions(empty_scratch_db)

        second = _run_demo_migrations()
        assert second.returncode == 0, (
            f"Second demo migrate failed (not idempotent):\nSTDOUT:\n{second.stdout}\nSTDERR:\n{second.stderr}"
        )
        assert _stamped_versions(empty_scratch_db) == versions_after_first

    # --- Scenario 3: cold CE init ----------------------------------------
    def test_cold_ce_init_has_no_saas_tables(self, empty_scratch_db: sa.Engine) -> None:
        result = _run_ce_migrations()
        assert result.returncode == 0, f"CE cold init failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        for tbl in CE_TABLES_SAMPLE:
            assert _table_exists(empty_scratch_db, tbl), f"CE table '{tbl}' missing after cold CE init"
        for tbl in SAAS_TABLES_REQUIRED:
            assert not _table_exists(empty_scratch_db, tbl), (
                f"SaaS table '{tbl}' UNEXPECTEDLY present after cold CE init (public alembic.ini must be single-chain)"
            )
        versions = _stamped_versions(empty_scratch_db)
        assert not any(v.startswith("saas_") for v in versions), (
            f"SaaS chain unexpectedly stamped on CE-only init: {versions}"
        )

    # --- Scenario 4: warm CE idempotency ---------------------------------
    def test_warm_ce_at_baseline_v37_applies_ce_0003_then_idempotent(self, empty_scratch_db: sa.Engine) -> None:
        result = _run_alembic_target("baseline_v37")
        assert result.returncode == 0, f"baseline_v37 upgrade failed:\n{result.stdout}\n{result.stderr}"
        versions_at_v37 = _stamped_versions(empty_scratch_db)
        assert "baseline_v37" in versions_at_v37, f"Expected baseline_v37 in heads, got {versions_at_v37}"
        assert not any(v.startswith("ce_") for v in versions_at_v37), (
            f"ce_* unexpectedly already stamped: {versions_at_v37}"
        )

        upgrade_to_head = _run_ce_migrations()
        assert upgrade_to_head.returncode == 0, (
            f"Upgrade from baseline_v37 to head failed:\n{upgrade_to_head.stdout}\n{upgrade_to_head.stderr}"
        )
        head_versions = _stamped_versions(empty_scratch_db)
        assert "ce_0003_widen_alembic_version" in head_versions, f"ce_0003 not stamped: {head_versions}"
        col_len = _alembic_version_column_length(empty_scratch_db)
        assert col_len is not None and col_len >= 64, f"alembic_version.version_num expected >= 64 chars, got {col_len}"

        second = _run_ce_migrations()
        assert second.returncode == 0, f"Second CE migrate failed:\n{second.stdout}\n{second.stderr}"
        assert _stamped_versions(empty_scratch_db) == head_versions

    # --- Scenario 5: pre-stamp widen idempotency -------------------------
    def test_pre_stamp_widen_is_idempotent_on_already_wide_column(self, empty_scratch_db: sa.Engine) -> None:
        """Pre-create alembic_version VARCHAR(128); pre-stamp DDL must not narrow."""
        with empty_scratch_db.connect() as conn:
            conn.execute(
                text(
                    "CREATE TABLE alembic_version ("
                    "version_num VARCHAR(128) NOT NULL, "
                    "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
                )
            )
            conn.commit()
        assert _alembic_version_column_length(empty_scratch_db) == 128

        # Import inside the test to avoid module-level side effects.
        sys.path.insert(0, str(PROJECT_ROOT))
        try:
            from demo.startup_demo import _ensure_alembic_version_table_widened
        finally:
            sys.path.pop(0)

        _ensure_alembic_version_table_widened(_scratch_db_url())

        # Column must STILL be 128 -- pre-stamp helper must never narrow.
        assert _alembic_version_column_length(empty_scratch_db) == 128, (
            "_ensure_alembic_version_table_widened narrowed a wider column"
        )

    # --- Scenario 6: pre-stamp bootstrap-create --------------------------
    def test_pre_stamp_bootstrap_creates_table_with_varchar_64(self, empty_scratch_db: sa.Engine) -> None:
        """Empty DB -> _ensure_alembic_version_table_widened creates VARCHAR(64)."""
        # Make sure table truly does not exist.
        assert not _table_exists(empty_scratch_db, "alembic_version")

        sys.path.insert(0, str(PROJECT_ROOT))
        try:
            from demo.startup_demo import _ensure_alembic_version_table_widened
        finally:
            sys.path.pop(0)

        _ensure_alembic_version_table_widened(_scratch_db_url())

        assert _table_exists(empty_scratch_db, "alembic_version"), (
            "_ensure_alembic_version_table_widened did not create alembic_version"
        )
        assert _alembic_version_column_length(empty_scratch_db) == 64, (
            "Bootstrap-create did not produce VARCHAR(64) column"
        )
