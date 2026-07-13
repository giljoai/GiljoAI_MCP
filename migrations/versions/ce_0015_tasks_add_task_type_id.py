# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add tasks.task_type_id FK to taxonomy_types and backfill from category.

Revision ID: ce_0015_tasks_add_task_type_id
Revises: ce_0014_rename_project_types_to_taxonomy_types
Create Date: 2026-05-05

Phase B step 1 of agent-parity + unified taxonomy. Adds a nullable
foreign key from tasks to taxonomy_types so tasks can be classified
the same way projects are. Backfills the new column from the existing
free-form ``category`` column when the value matches a TaxonomyType
abbreviation or label within the same tenant. Rows whose ``category``
does not match any taxonomy_types row are left NULL -- a separate
follow-up task / UI flow can resolve those.

The ``category`` column itself is dropped in ce_0016 once this
migration has soaked. Splitting the change into two migrations lets
operators inspect the backfill outcome before the irreversible drop.

Idempotent: column add and FK creation are guarded by
information_schema lookups; backfill UPDATE is naturally idempotent
and additionally guarded on ``tasks.category`` existing (the column is
dropped in ce_0016, so a replay over an at-head schema must no-op --
INF-9113).
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0015_tasks_add_task_type_id"
down_revision = "ce_0014_rename_project_types_to_taxonomy_types"
branch_labels = None
depends_on = None


TASKS_TABLE = "tasks"
NEW_COL = "task_type_id"
NEW_FK = "tasks_task_type_id_fkey"
NEW_IDX = "idx_task_task_type_id"


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.first() is not None


def _has_constraint(conn, table: str, constraint: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = :table AND constraint_name = :constraint"
        ),
        {"table": table, "constraint": constraint},
    )
    return result.first() is not None


def _has_index(conn, index: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :index"),
        {"index": index},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, TASKS_TABLE, NEW_COL):
        op.add_column(
            TASKS_TABLE,
            sa.Column(NEW_COL, sa.String(36), nullable=True),
        )

    if not _has_constraint(conn, TASKS_TABLE, NEW_FK):
        op.create_foreign_key(
            NEW_FK,
            TASKS_TABLE,
            "taxonomy_types",
            [NEW_COL],
            ["id"],
            ondelete="SET NULL",
        )

    if not _has_index(conn, NEW_IDX):
        op.create_index(NEW_IDX, TASKS_TABLE, [NEW_COL])

    # Backfill: match category against taxonomy_types within the same tenant.
    # Try abbreviation first (case-insensitive), then label. Rows with no
    # match remain NULL.
    #
    # Guarded on the source column existing: ce_0016 drops ``category``, so a
    # replay over an already-at-head schema (INF-9113) must no-op here instead
    # of crashing with UndefinedColumn. Also self-heals DBs wedged by the
    # INF-9113 installer stamp-down on their next upgrade.
    if _has_column(conn, TASKS_TABLE, "category"):
        conn.execute(
            sa.text(
                """
                UPDATE tasks t
                SET task_type_id = tt.id
                FROM taxonomy_types tt
                WHERE t.task_type_id IS NULL
                  AND t.category IS NOT NULL
                  AND t.tenant_key = tt.tenant_key
                  AND UPPER(t.category) = UPPER(tt.abbreviation)
                """
            )
        )
        conn.execute(
            sa.text(
                """
                UPDATE tasks t
                SET task_type_id = tt.id
                FROM taxonomy_types tt
                WHERE t.task_type_id IS NULL
                  AND t.category IS NOT NULL
                  AND t.tenant_key = tt.tenant_key
                  AND LOWER(t.category) = LOWER(tt.label)
                """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_index(conn, NEW_IDX):
        op.drop_index(NEW_IDX, table_name=TASKS_TABLE)

    if _has_constraint(conn, TASKS_TABLE, NEW_FK):
        op.drop_constraint(NEW_FK, TASKS_TABLE, type_="foreignkey")

    if _has_column(conn, TASKS_TABLE, NEW_COL):
        op.drop_column(TASKS_TABLE, NEW_COL)
