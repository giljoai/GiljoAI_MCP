# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Add idle and sleeping to agent_executions status CheckConstraint

Revision ID: 0950b_exec_status
Revises: baseline_v35
Create Date: 2026-04-05

The orchestration_service.py writes 'idle' and 'sleeping' statuses
(introduced in the auto-checkin feature) but the CheckConstraint on
agent_executions.status did not include them.

Idempotency: drops the old constraint only if it exists, then creates
the new one only if missing.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text as sa_text


revision: str = "0950b_exec_status"
down_revision: Union[str, Sequence[str], None] = "baseline_v35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_CONSTRAINT = "ck_agent_execution_status"
OLD_VALUES = "status IN ('waiting', 'working', 'blocked', 'complete', 'silent', 'decommissioned')"
NEW_VALUES = "status IN ('waiting', 'working', 'blocked', 'complete', 'silent', 'decommissioned', 'idle', 'sleeping')"


def upgrade() -> None:
    conn = op.get_bind()
    # Check if old constraint exists before dropping
    result = conn.execute(
        sa_text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = :name AND table_name = 'agent_executions'"
        ),
        {"name": OLD_CONSTRAINT},
    )
    if result.fetchone():
        op.drop_constraint(OLD_CONSTRAINT, "agent_executions", type_="check")

    op.create_check_constraint(
        OLD_CONSTRAINT,
        "agent_executions",
        NEW_VALUES,
    )


def downgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa_text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = :name AND table_name = 'agent_executions'"
        ),
        {"name": OLD_CONSTRAINT},
    )
    if result.fetchone():
        op.drop_constraint(OLD_CONSTRAINT, "agent_executions", type_="check")

    op.create_check_constraint(
        OLD_CONSTRAINT,
        "agent_executions",
        OLD_VALUES,
    )
