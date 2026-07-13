# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add nullable conductor-identity columns to sequence_runs (BE-6165b).

Revision ID: ce_0062_sequence_run_conductor_columns
Revises: ce_0061_message_loop_interval
Create Date: 2026-06-21

The Sequential Multi-Project Runner cockpit's ChainDirectiveComposer reads
``conductor_agent_id`` / ``conductor_project_id`` / ``conductor_label`` off the
SequenceRun to address steering directives at the chain's conductor. Those
columns did not exist, so the composer was permanently dormant. This adds them
as the keystone gap-fill; the sequence driver (BE-6165c) self-registers the
head-of-order orchestrator into them on its first staging/mission call.

Nullable, no backfill: existing rows carry NULL and the composer already
tolerates NULL by rendering dormant (data-shape self-heal, tolerance not
surgery). Idempotent (existence-checked per column) because the CE installer
reruns migrations on every boot; reversible (downgrade drops the columns).
``sequence_runs`` is a CE table (created in ce_0058), so this belongs in the CE
``versions/`` chain.

Note: sequence_runs is NOT part of baseline_v37_unified (it is created post-
baseline in ce_0058), so there is no baseline block to mirror — a fresh install
runs baseline -> ... -> ce_0058 (creates the table) -> ce_0062 (adds these
columns) and converges to the same shape as an upgraded deployment.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0062_sequence_run_conductor_columns"
down_revision = "ce_0061_message_loop_interval"
branch_labels = None
depends_on = None


_COLUMNS = (
    ("conductor_agent_id", sa.String(36)),
    ("conductor_project_id", sa.String(36)),
    ("conductor_label", sa.String(80)),
)


def _column_exists(conn, column_name: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.columns"
                "  WHERE table_name = 'sequence_runs'"
                "  AND column_name = :col"
                ")"
            ),
            {"col": column_name},
        ).scalar()
    )


def upgrade() -> None:
    # Idempotency guard: add each column only if absent (CE reruns on boot).
    conn = op.get_bind()
    for name, coltype in _COLUMNS:
        if not _column_exists(conn, name):
            op.add_column("sequence_runs", sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    for name, _coltype in reversed(_COLUMNS):
        op.drop_column("sequence_runs", name)
