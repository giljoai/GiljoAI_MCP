# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Make projects.execution_mode nullable and drop its server default.

Revision ID: ce_0043_projects_execution_mode_nullable
Revises: ce_0042_staged_agent_mailboxes
Create Date: 2026-06-07

The execution-mode NULL-state redesign removes the implicit 'multi_terminal'
default. A NULL execution_mode must mean 'not yet chosen' (the user has not
picked an orchestration mode) -- it must NOT silently coerce back to
'multi_terminal'. Two DB-level forces did that coercion: the NOT NULL constraint
and the server_default 'multi_terminal'. Both are removed here so the column can
hold NULL and so a default-less INSERT lands a real NULL instead of a fabricated
mode. Boundary gates (prompt-gen, spawn_job, get_orchestrator_instructions,
get_agent_mission) reject a NULL before any agent runs.

Existing rows are untouched: they already hold a concrete mode and keep it. Only
NEW projects (and any pre-default legacy rows) can now be NULL.

Idempotent: the ALTER fires only while the column is still NOT NULL or still
carries a server default (information_schema-gated). Postgres DROP NOT NULL /
DROP DEFAULT are themselves no-ops on re-run -- this is belt-and-suspenders, as
the CE installer reruns ``alembic upgrade head`` on every boot.

Edition Scope: CE -- ``projects`` is a CE table (src/giljo_mcp/models/projects.py);
this migration lives in ``migrations/versions/`` (NOT ``saas_versions/``). SaaS
inherits the change unchanged.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0043_projects_execution_mode_nullable"
down_revision = "ce_0042_staged_agent_mailboxes"
branch_labels = None
depends_on = None


_TABLE = "projects"
_COLUMN = "execution_mode"
_OLD_DEFAULT = "multi_terminal"


def _column_is_nullable(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT is_nullable FROM information_schema.columns WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    row = result.first()
    return row is not None and row[0] == "YES"


def _column_has_server_default(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    row = result.first()
    return row is not None and row[0] is not None


def upgrade() -> None:
    conn = op.get_bind()

    # Fire only if there is still something to change (NOT NULL or a default).
    if not _column_is_nullable(conn, _TABLE, _COLUMN) or _column_has_server_default(conn, _TABLE, _COLUMN):
        # One ALTER drops NOT NULL + the server default. server_default=None must
        # be passed EXPLICITLY to drop it -- omitting the kwarg leaves it in place
        # (Alembic treats a missing server_default kwarg as 'unchanged').
        op.alter_column(
            _TABLE,
            _COLUMN,
            existing_type=sa.String(length=20),
            nullable=True,
            server_default=None,
        )


def downgrade() -> None:
    conn = op.get_bind()

    # By downgrade time NULL rows can exist (that was the point of the change).
    # Backfill them to the legacy default BEFORE re-imposing NOT NULL, or
    # SET NOT NULL aborts. UPDATE (not DELETE) -- these are live user projects.
    conn.execute(
        sa.text(f"UPDATE {_TABLE} SET {_COLUMN} = :val WHERE {_COLUMN} IS NULL"),
        {"val": _OLD_DEFAULT},
    )

    if _column_is_nullable(conn, _TABLE, _COLUMN) or not _column_has_server_default(conn, _TABLE, _COLUMN):
        op.alter_column(
            _TABLE,
            _COLUMN,
            existing_type=sa.String(length=20),
            nullable=False,
            server_default=sa.text(f"'{_OLD_DEFAULT}'"),
        )
