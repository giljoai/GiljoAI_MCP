# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Projects: add ``superseded`` status value + ``successor_project_id`` pointer.

Revision ID: ce_0078_projects_superseded_status_and_successor
Revises: baseline_v38
Create Date: 2026-07-13

BE-9157 -- "superseded" project status + successor linking (roadmap audit trail).

Operations
----------
1. **Append ``'superseded'`` to the ``project_status`` ENUM** via
   ``ALTER TYPE ... ADD VALUE IF NOT EXISTS``. Postgres appends new ENUM values
   to the END of the type, which matches the canonical declaration order in
   ``giljo_mcp.domain.project_status.ProjectStatus`` (SUPERSEDED is declared
   last) and the baseline's ``CREATE TYPE`` list. The value is NOT referenced
   anywhere else in this migration, so the PG12+ "cannot use a new ENUM value in
   the same transaction" restriction does not apply.
2. **Add the nullable ``successor_project_id`` column** (existence-guarded).
3. **Add the self-referential FK** ``projects_successor_project_id_fkey``
   (``ON DELETE SET NULL``), guarded by constraint name.

Chain routing
-------------
``status`` and ``successor_project_id`` are columns on the CE ``Project`` model,
so this lives in ``migrations/versions/`` (the CE chain), NEVER
``saas_versions/``. Paired with a parity edit to ``baseline_v38_unified.py`` so a
fresh install gets the ENUM value + column directly (the FK is created here on
BOTH paths -- see below). The baseline's guarded ``create_table`` only runs on a
fresh DB, so the successor FK is deliberately kept OUT of the baseline's
``_FOREIGN_KEYS`` list: that list runs unconditionally on an existing mid-chain
DB where the column does not exist yet (this migration runs AFTER baseline_v38),
which would crash. Creating the FK here instead converges both paths.

Idempotency
-----------
* ``ADD VALUE IF NOT EXISTS`` is a no-op when the value already exists (fresh
  install, where the baseline's ``CREATE TYPE`` already included it).
* The column add is guarded by an ``inspect()`` column-existence check.
* The FK is guarded by a ``pg_constraint`` name check.
The CE installer reruns the chain on every boot, so every step must be re-runnable.

Data-facing DoD
---------------
Additive only: a new ENUM value + a nullable column. Every existing row is
untouched and remains valid -- tolerant by construction, no backfill needed.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "ce_0078_projects_superseded_status_and_successor"
down_revision = "baseline_v38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Step 1: Append the 'superseded' ENUM value (idempotent).
    # ------------------------------------------------------------------
    op.execute("ALTER TYPE project_status ADD VALUE IF NOT EXISTS 'superseded'")

    bind = op.get_bind()
    inspector = inspect(bind)

    # ------------------------------------------------------------------
    # Step 2: Add the nullable successor pointer column (guarded).
    # ------------------------------------------------------------------
    columns = [c["name"] for c in inspector.get_columns("projects")]
    if "successor_project_id" not in columns:
        op.add_column(
            "projects",
            sa.Column(
                "successor_project_id",
                sa.String(length=36),
                nullable=True,
                comment="FK to the project that supersedes this one (audit trail for replaced work)",
            ),
        )

    # ------------------------------------------------------------------
    # Step 3: Add the self-referential FK (guarded by constraint name).
    # ON DELETE SET NULL: deleting the successor clears the pointer.
    # ------------------------------------------------------------------
    # Static SQL (no interpolation) -- the constraint name is a fixed literal,
    # matching the baseline's guarded-DO-block FK style.
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'projects_successor_project_id_fkey') THEN
                ALTER TABLE ONLY public.projects
                    ADD CONSTRAINT projects_successor_project_id_fkey
                    FOREIGN KEY (successor_project_id)
                    REFERENCES public.projects(id) ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Drop the FK and the column. The ENUM value 'superseded' is intentionally
    # NOT removed: Postgres has no ``ALTER TYPE ... DROP VALUE``, and leaving an
    # unused ENUM value is harmless. Guarded so the downgrade is re-runnable.
    op.execute("ALTER TABLE ONLY public.projects DROP CONSTRAINT IF EXISTS projects_successor_project_id_fkey")

    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("projects")]
    if "successor_project_id" in columns:
        op.drop_column("projects", "successor_project_id")
