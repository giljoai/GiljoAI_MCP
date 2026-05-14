# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Extend download_tokens.download_type allowlist to include 'tenant_export'.

Revision ID: ce_0025_export_extend_download_type_allowlist
Revises: ce_0024_tasks_add_hidden
Create Date: 2026-05-14

BE-5062 (Export My Data, GDPR portability): the tenant-data export reuses the
existing DownloadToken + /api/download/temp/{token}/{filename} pipeline. The
baseline CHECK constraint on ``download_tokens.download_type`` only permits
``slash_commands`` and ``agent_templates``; the export feature needs a third
value, ``tenant_export``.

Idempotent: drops the old CHECK if present, recreates with the extended
allowlist. Re-running on a partially-migrated DB is safe.

Downgrade restores the original two-value allowlist. Rows with
``download_type = 'tenant_export'`` will violate the original constraint, so
the downgrade deletes those rows first (export tokens are 15-minute ephemera
— losing a handful on a rollback is acceptable).

Edition Scope: CE — ``download_tokens`` is a CE table.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0025_export_extend_download_type_allowlist"
down_revision = "ce_0024_tasks_add_hidden"
branch_labels = None
depends_on = None


TABLE = "download_tokens"
CONSTRAINT = "ck_download_token_type"
OLD_ALLOWLIST = ("slash_commands", "agent_templates")
NEW_ALLOWLIST = ("slash_commands", "agent_templates", "tenant_export")


def _has_constraint(conn, table: str, constraint: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = :table AND constraint_name = :constraint"
        ),
        {"table": table, "constraint": constraint},
    )
    return result.first() is not None


def _check_clause(values: tuple[str, ...]) -> str:
    rendered = ", ".join(f"'{v}'" for v in values)
    return f"download_type IN ({rendered})"


def upgrade() -> None:
    conn = op.get_bind()

    if _has_constraint(conn, TABLE, CONSTRAINT):
        op.drop_constraint(CONSTRAINT, TABLE, type_="check")

    op.create_check_constraint(CONSTRAINT, TABLE, _check_clause(NEW_ALLOWLIST))


def downgrade() -> None:
    conn = op.get_bind()

    # Remove rows whose value would violate the narrower constraint.
    # TABLE is a module-level constant (not user input), so the f-string here
    # is safe; bandit/ruff S608 is a false positive.
    conn.execute(
        sa.text(f"DELETE FROM {TABLE} WHERE download_type = 'tenant_export'")  # noqa: S608
    )

    if _has_constraint(conn, TABLE, CONSTRAINT):
        op.drop_constraint(CONSTRAINT, TABLE, type_="check")

    op.create_check_constraint(CONSTRAINT, TABLE, _check_clause(OLD_ALLOWLIST))
