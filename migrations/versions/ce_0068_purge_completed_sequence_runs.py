# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Auto-purge sequence_runs on chain completion (Option A) — one-time backfill.

Revision ID: ce_0068_purge_completed_sequence_runs
Revises: ce_0067_tsk_task_exclusive
Create Date: 2026-07-01

Runtime code now DELETES a chain's ``sequence_runs`` row (plus the conductor's
project-less agent rows) when the chain finishes, instead of leaving a dead
``completed`` row forever — the project row is the durable record; the chain
GROUPING is ephemeral. This migration backfills the change for existing DBs:
it removes rows already left behind by the old flip-to-completed path.

Per the runtime purge, this deletes — tenant-scoped by the JSON link, never
crossing tenants:

  Step A. Orphaned conductor ``agent_executions`` — the project-less executions
          whose ``agent_jobs`` row links (via ``job_metadata->>'run_id'``, a JSON
          link, NOT an FK — so nothing cascades) to a ``completed`` run.
  Step B. Those orphaned conductor ``agent_jobs`` (``project_id IS NULL``);
          ``agent_todo_items`` cascade at the DB level.
  Step C. The ``completed`` ``sequence_runs`` rows themselves. No FK references
          ``sequence_runs``, so the delete cascades to nothing.

SCOPE: ``status = 'completed'`` ONLY. ``terminated`` / ``cancelled`` runs are an
audit signal (user-bounded) and are LEFT UNTOUCHED.

Idempotent: a second run finds no ``completed`` runs (and no linked orphans), so
every step is a clean no-op — the "CE reruns upgrade head on every boot" case.
Existence-guarded by the ``status = 'completed'`` predicate; a fresh install has
no such rows and this is a no-op.

Edition Scope: CE (``sequence_runs`` / ``agent_jobs`` / ``agent_executions`` are
CE core tables; startup runs ``alembic upgrade head`` on the CE chain, SaaS
inherits). Data-only — no schema change, no schema-drift impact.
"""

from alembic import op
from sqlalchemy import text


revision = "ce_0068_purge_completed_sequence_runs"
down_revision = "ce_0067_tsk_task_exclusive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step A: orphaned conductor executions linked to a completed run. Joined on
    # tenant_key across all three tables so a tenant can never reach another's rows.
    op.execute(
        text(
            """
            DELETE FROM agent_executions ae
            USING agent_jobs aj, sequence_runs sr
            WHERE ae.job_id = aj.job_id
              AND ae.tenant_key = aj.tenant_key
              AND aj.tenant_key = sr.tenant_key
              AND aj.project_id IS NULL
              AND aj.job_metadata->>'run_id' = sr.id
              AND sr.status = 'completed'
            """
        )
    )

    # Step B: the orphaned conductor jobs themselves (agent_todo_items cascade).
    op.execute(
        text(
            """
            DELETE FROM agent_jobs aj
            USING sequence_runs sr
            WHERE aj.tenant_key = sr.tenant_key
              AND aj.project_id IS NULL
              AND aj.job_metadata->>'run_id' = sr.id
              AND sr.status = 'completed'
            """
        )
    )

    # Step C: the completed run rows (nothing FK-references sequence_runs).
    op.execute(text("DELETE FROM sequence_runs WHERE status = 'completed'"))


def downgrade() -> None:
    # Not reversed: the purged completed runs and their conductor rows are gone and
    # carry no restorable state (the durable record is each project row + its 360
    # memory). Mirrors ce_0023 / ce_0067's one-way data migrations. (No-op downgrade
    # so the chain stays walkable.)
    pass
