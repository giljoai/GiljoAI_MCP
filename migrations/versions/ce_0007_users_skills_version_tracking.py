# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available.

"""Users: track installed skills bundle version + last update reminder timestamp.

Revision ID: ce_0007_users_skills_version_tracking
Revises: ce_0006_configurations_unique_tenant_key
Create Date: 2026-04-28

Adds two nullable columns to ``users`` to support skills bundle drift
detection and the 30-day login reminder cadence:

- ``last_installed_skills_version VARCHAR(32) NULL`` — the SKILLS_VERSION
  string stamped at the time the user most recently downloaded the
  combined setup bundle (``/giljo_setup`` flow or
  ``/api/download/agent-templates.zip``).
- ``last_update_reminder_at TIMESTAMPTZ NULL`` — the last time the
  post-login background check pushed a ``system:update_available`` WS
  event to this user. Used to throttle reminders to one per 30 days.

Both columns are nullable; the post-login cadence treats NULL as
"never reminded / never installed" and behaves accordingly.

Idempotency: each ADD COLUMN is wrapped in an ``information_schema.columns``
check so the migration is safe to re-apply.

Reversible: downgrade drops both columns (ditto idempotency guards).
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0007_users_skills_version_tracking"
down_revision = "ce_0006_configurations_unique_tenant_key"
branch_labels = None
depends_on = None


TABLE_NAME = "users"
COL_VERSION = "last_installed_skills_version"
COL_REMINDER = "last_update_reminder_at"


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, TABLE_NAME, COL_VERSION):
        op.add_column(
            TABLE_NAME,
            sa.Column(COL_VERSION, sa.String(length=32), nullable=True),
        )

    if not _has_column(conn, TABLE_NAME, COL_REMINDER):
        op.add_column(
            TABLE_NAME,
            sa.Column(COL_REMINDER, sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_column(conn, TABLE_NAME, COL_REMINDER):
        op.drop_column(TABLE_NAME, COL_REMINDER)

    if _has_column(conn, TABLE_NAME, COL_VERSION):
        op.drop_column(TABLE_NAME, COL_VERSION)
