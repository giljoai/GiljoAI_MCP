# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6008: staged-agent mailboxes -- nullable job mission + 'staged' status.

Revision ID: ce_0042_staged_agent_mailboxes
Revises: ce_0041_tenant_skills_ack
Create Date: 2026-06-04

Two CE-table changes enabling the two-phase spawn (create messageable agent
first, write the mission second):

1. ``agent_jobs.mission`` becomes nullable. A Phase-1 spawn creates the job row
   (FK target for the execution) before the orchestrator authors the mission.

2. ``agent_executions.status`` gains ``'staged'`` -- the pre-mission state. An
   agent in ``staged`` is messageable (it has an ``agent_id``) but the play
   button is locked until the Phase-2 mission write transitions it to
   ``waiting``.

Idempotent: the mission ALTER is guarded by a NOT NULL inspection; the status
CheckConstraint is dropped-and-recreated (the drop is existence-guarded). The CE
installer reruns ``alembic upgrade head`` on every boot.

Edition Scope: CE -- both ``agent_jobs`` and ``agent_executions`` are CE tables;
this migration lives in ``migrations/versions/`` (NOT ``saas_versions/``). SaaS
inherits both changes unchanged.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0042_staged_agent_mailboxes"
down_revision = "ce_0041_tenant_skills_ack"
branch_labels = None
depends_on = None


_STATUS_CONSTRAINT = "ck_agent_execution_status"

_AGENT_STATUS_CHECK_OLD = (
    "status IN ('waiting', 'working', 'blocked', 'complete', 'closed', 'silent', "
    "'decommissioned', 'idle', 'sleeping', 'awaiting_user')"
)
_AGENT_STATUS_CHECK_NEW = (
    "status IN ('waiting', 'working', 'blocked', 'complete', 'closed', 'silent', "
    "'decommissioned', 'idle', 'sleeping', 'awaiting_user', 'staged')"
)


def _column_is_nullable(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT is_nullable FROM information_schema.columns WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    row = result.first()
    return row is not None and row[0] == "YES"


def _has_check_constraint(conn, name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = :name AND constraint_type = 'CHECK'"
        ),
        {"name": name},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_is_nullable(conn, "agent_jobs", "mission"):
        op.alter_column("agent_jobs", "mission", existing_type=sa.Text(), nullable=True)

    if _has_check_constraint(conn, _STATUS_CONSTRAINT):
        op.drop_constraint(_STATUS_CONSTRAINT, "agent_executions", type_="check")
    op.create_check_constraint(
        _STATUS_CONSTRAINT,
        "agent_executions",
        _AGENT_STATUS_CHECK_NEW,
    )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_check_constraint(conn, _STATUS_CONSTRAINT):
        op.drop_constraint(_STATUS_CONSTRAINT, "agent_executions", type_="check")
    op.create_check_constraint(
        _STATUS_CONSTRAINT,
        "agent_executions",
        _AGENT_STATUS_CHECK_OLD,
    )

    if _column_is_nullable(conn, "agent_jobs", "mission"):
        op.alter_column("agent_jobs", "mission", existing_type=sa.Text(), nullable=False)
