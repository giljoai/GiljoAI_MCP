# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Add last_activity_at column to agent_executions for heartbeat tracking

Revision ID: add_last_activity_at
Revises: rename_type_only
Create Date: 2026-04-14

Idempotent: uses ADD COLUMN IF NOT EXISTS (PostgreSQL 9.6+).
"""

from alembic import op


revision = "add_last_activity_at"
down_revision = "rename_type_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE agent_executions "
        "ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE agent_executions "
        "DROP COLUMN IF EXISTS last_activity_at"
    )
