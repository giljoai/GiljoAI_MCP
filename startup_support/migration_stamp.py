# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Installer migration-stamp policy for startup.py (INF-9113 split).

Extracted verbatim from startup.py: the boot-path migration-version bridge
that stamps EXPLICITLY KNOWN legacy revisions up to baseline_v37, heals any
missing baseline_v37 DDL idempotently, and NEVER stamps an unknown or newer
revision downward. startup.py re-imports every name so `startup.<name>`
remains a stable seam for tests and callers.

INF-5060 (squash to baseline_v38): a database with NO alembic_version table
takes the fresh fast path -- the table is created at VARCHAR(64) and stamped
at the squash boundary (baseline_v38's down_revision), so the subsequent
`alembic upgrade head` executes ONLY the guarded baseline_v38 instead of
replaying the full incremental chain. Databases at any chain revision keep
upgrading through the real chain (data backfills intact).
"""

import contextlib
import os

from startup_support.console import print_info, print_success, print_warning


def _check_and_stamp_migration_version() -> None:
    """Detect old migration revisions and stamp to baseline_v37.

    After a CE export squash, the old revision IDs no longer exist as files.
    This bridges existing databases to the new baseline so alembic upgrade head works.

    Stamping only updates alembic_version — it does NOT run DDL. So we also
    apply any missing columns/tables that were added between the old revision
    and baseline_v37, using IF NOT EXISTS / IF EXISTS for idempotency.
    """
    try:
        from sqlalchemy import inspect, text

        from src.giljo_mcp.database import DatabaseManager

        db_url = _get_database_url()
        if not db_url:
            return

        db_manager = DatabaseManager(database_url=db_url, is_async=False)
        with db_manager.get_session() as session:
            if not inspect(session.get_bind()).has_table("alembic_version"):
                # Fresh database (INF-5060 fast path): stamp the squash
                # boundary so `alembic upgrade head` executes ONLY the
                # guarded baseline_v38 -- one baseline instead of replaying
                # the whole incremental chain. The table is created at
                # VARCHAR(64) up front (ce_0003: alembic's default 32 chars
                # truncates long revision IDs).
                _stamp_fresh_database(session)
                return

            result = session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            current = result.scalar()

            if not current or current == "baseline_v37":
                # Even at baseline_v37, schema may be incomplete if a prior
                # stamp jumped ahead without DDL. Run the heal pass anyway.
                _heal_schema_to_v37(session)
                return

            # If `current` is a revision the alembic chain still recognizes
            # (e.g. baseline_v37, ce_0001..ce_0016), do NOT stamp it backward.
            # Doing so would force `alembic upgrade head` to re-run migrations
            # that already executed -- and any non-idempotent step would fail.
            # We bridge ONLY when `current` is an EXPLICITLY KNOWN legacy
            # revision from a pre-v37 baseline (mirrors known_old_revisions in
            # installer/core/database_setup.py -- keep the two sets in sync).
            known_legacy_revisions = {
                "baseline_v33",
                "baseline_v34",
                "baseline_v35",
                "baseline_v36",
                "0855a_setup_state",
                "0904_auto_checkin",
                "0950b_exec_status",
                "0960_checkin_min",
                "0435b_closed_status",
                "0435d_requires_action",
                "bee938301ffa",
            }

            if current in known_legacy_revisions:
                # Legacy revision the squash removed -- bridge to baseline_v37.
                print_info(f"Stamping migration: {current} -> baseline_v37")
                _heal_schema_to_v37(session)
                session.execute(text("UPDATE alembic_version SET version_num = 'baseline_v37'"))
                session.commit()
                print_success("Migration version updated to baseline_v37")
                return

            from pathlib import Path as _Path

            versions_dir = _Path(__file__).parent.parent / "migrations" / "versions"
            # Baseline revision IDs differ from their file stems
            # (baseline_v38_unified.py -> revision "baseline_v38"), so seed
            # them explicitly; ce_0XXX stems ARE the revision IDs.
            known_revisions: set[str] = {"baseline_v37", "baseline_v38"}
            if versions_dir.is_dir():
                for entry in versions_dir.glob("*.py"):
                    if entry.name == "__init__.py":
                        continue
                    # Alembic revision filenames are <rev_id>_<slug>.py; the
                    # full revision ID is the stem.
                    known_revisions.add(entry.stem)

            if current in known_revisions:
                # Modern revision -- alembic upgrade head will handle it.
                return

            # Revision unknown to this build and NOT a known legacy one: the
            # DB was written by a DIFFERENT (likely newer) build -- rollback,
            # restore onto older code, or a partial update. Stamping it down
            # to baseline_v37 would replay the whole chain over an
            # already-migrated schema and wedge the DB exactly like INF-9113
            # Finding #5. Never stamp down; `alembic upgrade head` fails
            # loudly if it cannot locate the revision.
            print_warning(
                f"Revision {current} is not in this build's migration chain - "
                "treating database as already migrated (newer build?). "
                "NOT stamping down to baseline_v37."
            )

    except Exception as e:
        print_warning(f"Migration version check skipped: {e}")


# The squash boundary (INF-5060): baseline_v38's down_revision. A fresh
# database is stamped here so `alembic upgrade head` executes ONLY the
# guarded baseline_v38. Keep in sync with FRESH_INSTALL_STAMP_REVISION in
# installer/core/database_setup.py and with baseline_v38_unified.py.
FRESH_INSTALL_STAMP_REVISION = "ce_0077_sequence_run_reviewed_project_ids"


def _stamp_fresh_database(session) -> None:
    """Stamp a fresh (no alembic_version table) DB at the squash boundary.

    Creates alembic_version at VARCHAR(64) (ce_0003 width fix -- alembic's
    default 32 chars truncates long revision IDs) and records the squash
    boundary revision, so the subsequent `alembic upgrade head` runs ONLY
    baseline_v38 instead of replaying the full incremental chain.
    """
    from sqlalchemy import text

    print_info("Fresh database detected - taking the baseline_v38 fast path")
    session.execute(
        text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(64) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
        )
    )
    session.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:rev) ON CONFLICT DO NOTHING").bindparams(
            rev=FRESH_INSTALL_STAMP_REVISION
        )
    )
    session.commit()
    print_success(f"Stamped fresh database at {FRESH_INSTALL_STAMP_REVISION} (squash boundary)")


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


def _get_database_url() -> str | None:
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
