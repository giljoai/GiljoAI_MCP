# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Add 'closed' to agent_executions status CheckConstraint

Revision ID: 0435b_closed_status
Revises: 0950b_exec_status
Create Date: 2026-04-09

Handover 0435b: Adds 'closed' as a first-class agent lifecycle status.
'closed' = orchestrator accepted deliverables, no further work expected.

Idempotency: drops the old constraint only if it exists, then creates
the new one.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text as sa_text


revision: str = "0435b_closed_status"
down_revision: Union[str, Sequence[str], None] = "0950b_exec_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "ck_agent_execution_status"
OLD_VALUES = "status IN ('waiting', 'working', 'blocked', 'complete', 'silent', 'decommissioned', 'idle', 'sleeping')"
NEW_VALUES = "status IN ('waiting', 'working', 'blocked', 'complete', 'closed', 'silent', 'decommissioned', 'idle', 'sleeping')"


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa_text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = :name AND table_name = 'agent_executions'"
        ),
        {"name": CONSTRAINT_NAME},
    )
    if result.fetchone():
        op.drop_constraint(CONSTRAINT_NAME, "agent_executions", type_="check")

    op.create_check_constraint(
        CONSTRAINT_NAME,
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
        {"name": CONSTRAINT_NAME},
    )
    if result.fetchone():
        op.drop_constraint(CONSTRAINT_NAME, "agent_executions", type_="check")

    op.create_check_constraint(
        CONSTRAINT_NAME,
        "agent_executions",
        OLD_VALUES,
    )
