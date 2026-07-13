# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-5065: shared task+project series counter — partial unique index + backfill.

Revision ID: ce_0023_tasks_shared_taxonomy_serial
Revises: ce_0022_oauth_revoked_tokens
Create Date: 2026-05-12

After BE-5058 added ``series_number`` + ``subseries`` to ``tasks`` and BE-5064
plugged the NULL-taxonomy hole on conversions, BE-5065 unifies the counter:
under any ``(tenant_key, product_id, taxonomy_type_id)`` bucket, tasks and
projects share a single monotonic series_number stream, so a project of type
BE created after task ``BE-0017`` becomes ``BE-0018`` rather than colliding.

This migration does two things:

1. Create partial unique index ``uq_task_taxonomy_active`` mirroring
   ``uq_project_taxonomy_active`` (NULLS NOT DISTINCT, partial on
   ``series_number IS NOT NULL`` — tasks have no soft-delete, so the partial
   predicate filters typed rows only and leaves the legacy NULL-type rows
   exempt from the constraint).
2. Backfill: for every ``(tenant_key, product_id, task_type_id)`` bucket where
   ``task_type_id IS NOT NULL``, walk typed tasks ordered by ``created_at ASC``
   and assign the next-free ``series_number`` not already used by tasks OR
   projects in the same bucket. Skip rows that already have a non-NULL
   ``series_number`` (idempotent).

Edition Scope: CE — ``tasks`` is a CE table; ``startup.py`` runs
``alembic upgrade head`` only on the CE chain. SaaS inherits transparently.

Idempotent: index creation + backfill both guard against re-running.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0023_tasks_shared_taxonomy_serial"
down_revision = "ce_0022_oauth_revoked_tokens"
branch_labels = None
depends_on = None


TASK_INDEX = "uq_task_taxonomy_active"


def _has_index(conn, indexname: str) -> bool:
    return (
        conn.execute(
            sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
            {"name": indexname},
        ).first()
        is not None
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Backfill BEFORE creating the unique index so any pre-existing duplicate
    # (tenant_key, product_id, task_type_id, series_number, subseries) rows
    # would surface as a clean integrity error rather than an index build
    # failure. The backfill itself avoids creating duplicates by walking each
    # bucket sequentially and choosing the next-free number across BOTH tables.
    buckets = conn.execute(
        sa.text(
            """
            SELECT DISTINCT tenant_key, product_id, task_type_id
            FROM tasks
            WHERE task_type_id IS NOT NULL AND series_number IS NULL
            """
        )
    ).fetchall()

    for tenant_key, product_id, task_type_id in buckets:
        max_existing = conn.execute(
            sa.text(
                """
                SELECT GREATEST(
                    COALESCE((
                        SELECT MAX(series_number) FROM tasks
                        WHERE tenant_key = :tk AND product_id = :pid
                          AND task_type_id = :ttid
                    ), 0),
                    COALESCE((
                        SELECT MAX(series_number) FROM projects
                        WHERE tenant_key = :tk AND product_id = :pid
                          AND project_type_id = :ttid
                    ), 0)
                )
                """
            ),
            {"tk": tenant_key, "pid": product_id, "ttid": task_type_id},
        ).scalar_one()

        rows = conn.execute(
            sa.text(
                """
                SELECT id FROM tasks
                WHERE tenant_key = :tk AND product_id = :pid
                  AND task_type_id = :ttid AND series_number IS NULL
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"tk": tenant_key, "pid": product_id, "ttid": task_type_id},
        ).fetchall()

        next_n = max_existing + 1
        for (task_id,) in rows:
            conn.execute(
                sa.text("UPDATE tasks SET series_number = :n WHERE id = :id"),
                {"n": next_n, "id": task_id},
            )
            next_n += 1

    if not _has_index(conn, TASK_INDEX):
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX uq_task_taxonomy_active "
                "ON tasks (tenant_key, product_id, task_type_id, series_number, subseries) "
                "NULLS NOT DISTINCT "
                "WHERE series_number IS NOT NULL"
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_index(conn, TASK_INDEX):
        op.execute(sa.text(f"DROP INDEX {TASK_INDEX}"))
    # Series-number backfill is not reversed: the assigned values are valid
    # data and reverting them would re-open the NULL-collision window.
