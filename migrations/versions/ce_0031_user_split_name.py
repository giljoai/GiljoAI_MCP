# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Split User.full_name into first_name + last_name.

Revision ID: ce_0031_user_split_name
Revises: ce_0030_agent_executions_add_working_started_at
Create Date: 2026-05-25

Adds nullable ``first_name`` and ``last_name`` columns to the ``users``
table. The legacy ``full_name`` column is retained for one release as a
transition shim -- the model exposes a ``display_name`` property that
prefers ``first_name``/``last_name`` and falls back to ``full_name`` or
``username``. A follow-up migration will drop ``full_name`` once all
callers have been migrated.

Backfill: existing rows have ``first_name`` derived from the first
whitespace-delimited token of ``full_name`` and ``last_name`` derived from
the remainder. A single-token full_name yields first_name=<token>,
last_name=NULL.

Idempotency: existence-check both columns before adding, and only run
the backfill on rows where ``first_name`` is still NULL (so re-runs are
no-ops on already-migrated data).

Edition Scope: Both -- the ``users`` table is shared between CE and SaaS.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0031_user_split_name"
down_revision = "ce_0030_agent_executions_add_working_started_at"
branch_labels = None
depends_on = None


TABLE = "users"


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, TABLE, "first_name"):
        op.add_column(
            TABLE,
            sa.Column("first_name", sa.String(length=255), nullable=True),
        )

    if not _has_column(conn, TABLE, "last_name"):
        op.add_column(
            TABLE,
            sa.Column("last_name", sa.String(length=255), nullable=True),
        )

    # Backfill from legacy full_name. Idempotent: only touches rows where
    # first_name has not yet been populated. When full_name has no
    # whitespace, last_name stays NULL (position(' ' in full_name) = 0
    # would otherwise yield the whole string as last_name).
    op.execute(
        sa.text(
            "UPDATE users "
            "SET first_name = split_part(full_name, ' ', 1), "
            "    last_name = CASE "
            "        WHEN position(' ' in full_name) > 0 "
            "        THEN NULLIF(substring(full_name from position(' ' in full_name) + 1), '') "
            "        ELSE NULL "
            "    END "
            "WHERE full_name IS NOT NULL AND first_name IS NULL"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, TABLE, "last_name"):
        op.drop_column(TABLE, "last_name")
    if _has_column(conn, TABLE, "first_name"):
        op.drop_column(TABLE, "first_name")
