# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Drop orphan projects.activated_at and projects.deactivation_reason columns.

Revision ID: ce_0038_drop_projects_activated_at_deactivation_reason
Revises: ce_0037_seed_agent_silence_threshold_system_setting
Create Date: 2026-06-02

BE-5102: both columns are dead data with no live consumer.

- ``activated_at`` was written only on first activation; nothing reads it for a
  decision. The frontend duration timer uses per-job ``agent.started_at``, not
  ``project.activated_at``.
- ``deactivation_reason`` was populated only by an internal archive call and is
  never surfaced. User-facing reason capture on cancel/terminate is tracked in a
  separate project.

Scaffolding check passed (feedback_scaffolding_vs_orphans.md): no planning-stage
project references either column.

Idempotent: re-applying is a no-op (DROP guarded by information_schema check).

Edition Scope: CE -- ``projects`` is a CE model.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0038_drop_projects_activated_at_deactivation_reason"
down_revision = "ce_0037_seed_agent_silence_threshold_system_setting"
branch_labels = None
depends_on = None


PROJECTS_TABLE = "projects"
COL_ACTIVATED_AT = "activated_at"
COL_DEACTIVATION_REASON = "deactivation_reason"


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, PROJECTS_TABLE, COL_ACTIVATED_AT):
        op.drop_column(PROJECTS_TABLE, COL_ACTIVATED_AT)
    if _has_column(conn, PROJECTS_TABLE, COL_DEACTIVATION_REASON):
        op.drop_column(PROJECTS_TABLE, COL_DEACTIVATION_REASON)


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, PROJECTS_TABLE, COL_ACTIVATED_AT):
        op.add_column(
            PROJECTS_TABLE,
            sa.Column(
                COL_ACTIVATED_AT,
                sa.DateTime(timezone=True),
                nullable=True,
                comment="First activation timestamp (only set once on first activation)",
            ),
        )
    if not _has_column(conn, PROJECTS_TABLE, COL_DEACTIVATION_REASON):
        op.add_column(
            PROJECTS_TABLE,
            sa.Column(
                COL_DEACTIVATION_REASON,
                sa.Text(),
                nullable=True,
                comment="Reason for project deactivation",
            ),
        )
