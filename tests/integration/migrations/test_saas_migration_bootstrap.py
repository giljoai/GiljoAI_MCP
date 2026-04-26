# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [SAAS] SaaS Edition - includes demo bootstrap behavior verification.

"""
Integration tests for the SaaS migration bootstrap fix.

These tests verify the dual-chain (CE + SaaS) Alembic migration behavior
against a REAL scratch PostgreSQL database. They cover the five scenarios
required by mission BE-SaaS-Bootstrap:

    1. Cold demo init   -- empty DB + GILJO_MODE=demo -> heads brings up
                            both CE and SaaS tables.
    2. Warm demo idempotency -- second `alembic upgrade heads` is a no-op.
    3. Cold CE init     -- empty DB + GILJO_MODE unset -> only CE tables;
                            no SaaS tables present.
    4. Warm CE idempotency -- a database already at baseline_v37 (the CE
                              head BEFORE ce_0003) cleanly applies
                              ce_0003 and is idempotent on a second run.
    5. version_num widening idempotency -- ce_0003 detects an existing
                                            VARCHAR(>=64) column and
                                            skips the ALTER without error.

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

# Production DB name we must NEVER touch.
PRODUCTION_DB_NAME = "giljo_mcp"


def _scratch_db_url() -> str:
    """Compose a scratch-DB connection URL and refuse to target production."""
    if SCRATCH_DB == PRODUCTION_DB_NAME:
        raise RuntimeError(
            "SAFETY GUARD: Refusing to run bootstrap tests against the "
            "production DB name 'giljo_mcp'. Override GILJO_BOOTSTRAP_TEST_DB."
        )
    if not ADMIN_PASSWORD:
        raise RuntimeError("POSTGRES_OWNER_PASSWORD is not set; cannot connect to scratch DB.")
    return f"postgresql://{ADMIN_USER}:{ADMIN_PASSWORD}@{DB_HOST}:{DB_PORT}/{SCRATCH_DB}"


def _scratch_engine() -> sa.Engine:
    return sa.create_engine(_scratch_db_url(), poolclass=sa.pool.NullPool)


def _drop_all_objects(engine: sa.Engine) -> None:
    """Drop every public-schema object so the next test starts empty.

    We drop & recreate the public schema -- this is the only reliable
    way to clear a database that has been touched by alembic, given
    the variety of constraint and FK relationships present.
    """
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text(f"GRANT ALL ON SCHEMA public TO {ADMIN_USER}"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        conn.commit()


def _run_alembic_upgrade(
    *,
    giljo_mode: str | None,
    extra_env: dict[str, str] | None = None,
    target: str = "heads",
) -> subprocess.CompletedProcess[str]:
    """Run ``alembic upgrade <target>`` against the scratch DB.

    GILJO_MODE governs whether env.py adds the saas_versions chain to
    version_locations. The alembic CLI itself reads version_locations
    from alembic.ini (which lists both chains), but env.py is what the
    application uses at startup, so we test alignment with both.
    """
    env = os.environ.copy()
    env["DATABASE_URL"] = _scratch_db_url()
    # Keep individual POSTGRES_* in sync so env.py's fallback path is also valid.
    env["POSTGRES_HOST"] = DB_HOST
    env["POSTGRES_PORT"] = DB_PORT
    env["POSTGRES_DB"] = SCRATCH_DB
    env["POSTGRES_USER"] = ADMIN_USER
    env["POSTGRES_PASSWORD"] = ADMIN_PASSWORD
    if giljo_mode is None:
        env.pop("GILJO_MODE", None)
    else:
        env["GILJO_MODE"] = giljo_mode
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), "upgrade", target],
        cwd=str(PROJECT_ROOT),
        env=env,
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
                "WHERE table_name = 'alembic_version' "
                "AND column_name = 'version_num'"
            )
        ).scalar()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def scratch_engine() -> sa.Engine:
    """Connect to the scratch DB once per module."""
    eng = _scratch_engine()
    # Confirm the connection works before running any test.
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    yield eng
    eng.dispose()


@pytest.fixture
def empty_scratch_db(scratch_engine: sa.Engine) -> sa.Engine:
    """Provide a freshly-emptied scratch DB for each test."""
    _drop_all_objects(scratch_engine)
    yield scratch_engine
    # Leave the DB empty for the next test.
    _drop_all_objects(scratch_engine)


# ---------------------------------------------------------------------------
# CE / SaaS table catalogue
# ---------------------------------------------------------------------------

# A representative subset of CE tables from baseline_v37. We don't need to
# enumerate every table -- we just need enough to prove the CE chain ran.
CE_TABLES_SAMPLE = (
    "organizations",
    "users",
    "projects",
    "agent_templates",
    "alembic_version",
)

# Tables that MUST exist after the SaaS chain runs.
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
    """Five real-DB migration scenarios from the bootstrap mission."""

    # --- Scenario 1 -------------------------------------------------------
    def test_cold_demo_init_brings_up_both_chains(self, empty_scratch_db: sa.Engine) -> None:
        """Empty DB + GILJO_MODE=demo -> heads creates CE and SaaS tables."""
        result = _run_alembic_upgrade(giljo_mode="demo")
        assert result.returncode == 0, (
            f"alembic upgrade heads failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

        for tbl in CE_TABLES_SAMPLE:
            assert _table_exists(empty_scratch_db, tbl), f"CE table '{tbl}' missing after cold demo init"
        for tbl in SAAS_TABLES_REQUIRED:
            assert _table_exists(empty_scratch_db, tbl), f"SaaS table '{tbl}' missing after cold demo init"

        # org_setup_complete column added by saas_003 must be present on orgs.
        assert _column_exists(empty_scratch_db, "organizations", "org_setup_complete"), (
            "organizations.org_setup_complete missing after cold demo init"
        )

        # alembic_version should hold both chain heads.
        versions = _stamped_versions(empty_scratch_db)
        assert any(v.startswith("ce_") or v == "baseline_v37" for v in versions), (
            f"No CE head stamped after cold demo init. Got: {versions}"
        )
        assert any(v.startswith("saas_") for v in versions), (
            f"No SaaS head stamped after cold demo init. Got: {versions}"
        )

    # --- Scenario 2 -------------------------------------------------------
    def test_warm_demo_idempotent(self, empty_scratch_db: sa.Engine) -> None:
        """A second `alembic upgrade heads` on an already-migrated demo DB is a no-op."""
        first = _run_alembic_upgrade(giljo_mode="demo")
        assert first.returncode == 0, f"First upgrade failed:\n{first.stdout}\n{first.stderr}"
        versions_after_first = _stamped_versions(empty_scratch_db)

        second = _run_alembic_upgrade(giljo_mode="demo")
        assert second.returncode == 0, (
            f"Second upgrade failed (not idempotent):\nSTDOUT:\n{second.stdout}\nSTDERR:\n{second.stderr}"
        )
        # Heads should be unchanged.
        assert _stamped_versions(empty_scratch_db) == versions_after_first
        # No "already exists" / duplicate-key noise from the second pass.
        combined = (second.stdout + second.stderr).lower()
        assert "duplicatekey" not in combined.replace(" ", "")
        assert "already exists" not in combined or "running upgrade" not in combined, (
            f"Second upgrade emitted DDL it shouldn't have:\n{second.stdout}\n{second.stderr}"
        )

    # --- Scenario 3 -------------------------------------------------------
    def test_cold_ce_init_has_no_saas_tables(self, empty_scratch_db: sa.Engine) -> None:
        """Empty DB + GILJO_MODE unset -> CE tables present, SaaS tables absent."""
        result = _run_alembic_upgrade(giljo_mode=None)
        assert result.returncode == 0, f"CE cold init failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        for tbl in CE_TABLES_SAMPLE:
            assert _table_exists(empty_scratch_db, tbl), f"CE table '{tbl}' missing after cold CE init"
        for tbl in SAAS_TABLES_REQUIRED:
            assert not _table_exists(empty_scratch_db, tbl), (
                f"SaaS table '{tbl}' UNEXPECTEDLY present after cold CE init (GILJO_MODE unset must mean CE-only)"
            )
        versions = _stamped_versions(empty_scratch_db)
        assert not any(v.startswith("saas_") for v in versions), (
            f"SaaS chain unexpectedly stamped on CE-only init: {versions}"
        )

    # --- Scenario 4 -------------------------------------------------------
    def test_warm_ce_at_baseline_v37_applies_ce_0003_then_idempotent(self, empty_scratch_db: sa.Engine) -> None:
        """Stamp at baseline_v37, upgrade to head -> ce_0003 applies cleanly,
        and a second upgrade is a no-op."""
        # Step 1: cold-init then roll back to a state stamped at baseline_v37,
        # i.e. before ce_0001/0002/0003. The cleanest way to recreate that is
        # to upgrade fully then downgrade ce_* to baseline_v37 -- but ce_0003
        # has a no-op downgrade by design. Instead, manually run base ->
        # baseline_v37 only.
        result = _run_alembic_upgrade(giljo_mode=None, target="baseline_v37")
        assert result.returncode == 0, f"baseline_v37 upgrade failed:\n{result.stdout}\n{result.stderr}"
        # Confirm we are at baseline_v37 only.
        versions_at_v37 = _stamped_versions(empty_scratch_db)
        assert "baseline_v37" in versions_at_v37, f"Expected baseline_v37 in heads, got {versions_at_v37}"
        assert not any(v.startswith("ce_") for v in versions_at_v37), (
            f"ce_* unexpectedly already stamped: {versions_at_v37}"
        )

        # Step 2: now upgrade to heads. ce_0001/ce_0002/ce_0003 should apply.
        upgrade_to_head = _run_alembic_upgrade(giljo_mode=None)
        assert upgrade_to_head.returncode == 0, (
            f"Upgrade from baseline_v37 to head failed:\n{upgrade_to_head.stdout}\n{upgrade_to_head.stderr}"
        )
        head_versions = _stamped_versions(empty_scratch_db)
        assert "ce_0003_widen_alembic_version" in head_versions, f"ce_0003 not stamped: {head_versions}"
        # Column should now be widened.
        col_len = _alembic_version_column_length(empty_scratch_db)
        assert col_len is not None and col_len >= 64, f"alembic_version.version_num expected >= 64 chars, got {col_len}"

        # Step 3: second upgrade is a no-op.
        second = _run_alembic_upgrade(giljo_mode=None)
        assert second.returncode == 0, f"Second upgrade failed:\n{second.stdout}\n{second.stderr}"
        assert _stamped_versions(empty_scratch_db) == head_versions

    # --- Scenario 5 -------------------------------------------------------
    def test_ce_0003_skips_when_column_already_widened(self, empty_scratch_db: sa.Engine) -> None:
        """Pre-widen alembic_version.version_num to VARCHAR(128); ce_0003
        must detect >= 64 and skip the ALTER without error."""
        # Stamp at baseline_v37 first (creates alembic_version with default 32).
        result = _run_alembic_upgrade(giljo_mode=None, target="baseline_v37")
        assert result.returncode == 0, f"baseline_v37 upgrade failed:\n{result.stdout}\n{result.stderr}"

        # Pre-widen the column to 128 chars to simulate a manual op.
        with empty_scratch_db.connect() as conn:
            conn.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"))
            conn.commit()
        assert _alembic_version_column_length(empty_scratch_db) == 128

        # Now upgrade to head. ce_0003 should skip the ALTER because >= 64.
        upgrade = _run_alembic_upgrade(giljo_mode=None)
        assert upgrade.returncode == 0, f"Upgrade with pre-widened column failed:\n{upgrade.stdout}\n{upgrade.stderr}"
        # Column must STILL be 128 -- ce_0003 must not have shrunk it.
        assert _alembic_version_column_length(empty_scratch_db) == 128, (
            "ce_0003 unexpectedly resized a pre-widened column"
        )
        # And ce_0003 must be stamped.
        versions = _stamped_versions(empty_scratch_db)
        assert "ce_0003_widen_alembic_version" in versions, f"ce_0003 not stamped on pre-widened DB: {versions}"
