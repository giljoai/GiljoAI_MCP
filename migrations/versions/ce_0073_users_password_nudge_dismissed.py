# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add nullable password_nudge_dismissed_at column to users (BE-1004).

Revision ID: ce_0073_users_password_nudge_dismissed
Revises: ce_0072_bus_retirement_fold_and_fk
Create Date: 2026-07-04

Backs the BE-1004 "set a password" nudge: a one-time, skippable interstitial
shown to first-time social-only users (password_hash IS NULL). The column
belongs in the CE chain because ``users`` is a CE table, even though the only
writer today is the SaaS social-login flow (mirrors ce_0055's
registration_ip rationale -- a SaaS-relevant signal on a CE-owned table).

Nullable, no backfill: NULL means "not dismissed yet" (also the correct
default for every pre-existing row, since the nudge concept didn't exist
before this column). Idempotent (existence-checked) because the CE installer
reruns migrations on every boot; reversible (downgrade drops the column).
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0073_users_password_nudge_dismissed"
down_revision = "ce_0072_bus_retirement_fold_and_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.columns"
            "  WHERE table_name = 'users'"
            "  AND column_name = 'password_nudge_dismissed_at'"
            ")"
        )
    ).scalar()
    if exists:
        return

    op.add_column(
        "users",
        sa.Column("password_nudge_dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_nudge_dismissed_at")
