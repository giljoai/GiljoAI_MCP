# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add token_revocation_epoch column to users (SEC-6011 admin-forced-logout).

Revision ID: ce_0066_users_token_revocation_epoch
Revises: ce_0065_sequence_run_chain_mission
Create Date: 2026-06-30

Adds an integer ``token_revocation_epoch`` column to ``users`` (default 0). The
value at mint time is embedded in each access JWT as the ``rev`` claim;
validation rejects any token whose ``rev`` is below the user's current epoch, so
an admin force-logout (which bumps the epoch) invalidates ALL of that user's
outstanding access tokens at once.

The column belongs in the CE chain because ``users`` is a CE table (Edition
Scope: Both — the mechanism is used by CE and SaaS alike; SaaS adds no table).

NOT NULL with ``server_default '0'`` so existing rows backfill to a valid
baseline in-place and fresh inserts self-heal — numeric comparison then treats
every row as having a concrete epoch. Idempotent (existence-checked) because the
CE installer reruns migrations on every boot; reversible (downgrade drops it).
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0066_users_token_revocation_epoch"
down_revision = "ce_0065_sequence_run_chain_mission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotency guard: skip if the column already exists (CE reruns on boot).
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.columns"
            "  WHERE table_name = 'users'"
            "  AND column_name = 'token_revocation_epoch'"
            ")"
        )
    ).scalar()
    if exists:
        return

    op.add_column(
        "users",
        sa.Column(
            "token_revocation_epoch",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_revocation_epoch")
