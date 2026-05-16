# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Backfill project_phase='staging' for active staging orchestrators.

Revision ID: ce_0027_backfill_active_staging_orch_phase
Revises: ce_0026_agent_executions_add_project_phase
Create Date: 2026-05-16

CE-0026 added ``agent_executions.project_phase`` with DEFAULT 'implementation'.
That default is correct for completed historical executions (most existing rows
fall into this bucket — old projects whose implementation phase finished long
ago) and for non-orchestrator agents (which never had phase semantics anyway).

But for orchestrator executions that were mid-staging at the moment CE-0026
ran, the default is wrong — they should have been 'staging'. Symptoms in the
field were: complete_job at staging-end returned no staging_directive,
returned an implementation-phase closeout_checklist, and the Implement-button
launch couldn't spawn a fresh impl execution.

This migration corrects those rows in place. Idempotent — runs once on every
existing DB during the v1.2.x → v1.3.0 upgrade, no-op on fresh installs (zero
matching rows), no-op on already-correct rows.

Targets only orchestrators because:
  - Non-orchestrator agents have no phase semantics; 'implementation' is fine.
  - Completed/closed/decommissioned orchs are historical; their phase reflects
    the phase in which they last ran.

The downgrade is intentionally a no-op: this is a data fix, not a schema
change. Reverting to the buggy 'implementation' state for active staging
orchestrators is never desirable.

Edition Scope: CE — ``agent_executions`` is a CE table.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0027_backfill_active_staging_orch_phase"
down_revision = "ce_0026_agent_executions_add_project_phase"
branch_labels = None
depends_on = None


# Active orchestrator executions whose parent project is still staging
# (NULL = not yet staged, 'staging' = orch is mid-staging, 'staged' = prompt
# generated but agent hasn't contacted server). 'staging_complete' is
# excluded — those orchs have already moved past staging, and the default
# 'implementation' is correct for them.
_BACKFILL_SQL = sa.text(
    """
    UPDATE agent_executions ae
    SET project_phase = 'staging'
    FROM agent_jobs aj
    JOIN projects p ON aj.project_id = p.id
    WHERE ae.job_id = aj.job_id
      AND ae.agent_display_name = 'orchestrator'
      AND ae.status NOT IN ('complete', 'closed', 'decommissioned')
      AND ae.project_phase != 'staging'
      AND (p.staging_status IS NULL OR p.staging_status IN ('staging', 'staged'))
    """
)


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(_BACKFILL_SQL)
    # Alembic's logger picks this up via the standard stream.
    op.execute(
        sa.text(
            "DO $$ BEGIN RAISE NOTICE "
            "'[CE-0027] Backfilled % active staging orchestrator execution(s) "
            "to project_phase=staging', "
            f"{result.rowcount}; END $$"
        )
    )


def downgrade() -> None:
    # Data fix — intentional no-op. See module docstring.
    pass
