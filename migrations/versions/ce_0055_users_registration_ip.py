# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add nullable registration_ip column to users (registration audit / abuse signal).

Revision ID: ce_0055_users_registration_ip
Revises: ce_0054_cht_taxonomy_backfill
Create Date: 2026-06-16

Adds a nullable ``registration_ip`` VARCHAR(45) column to ``users`` so the
client IP can be captured at account creation (abuse/fraud signal + audit). The
column belongs in the CE chain because ``users`` is a CE table, even though the
primary reader is the SaaS Ops Panel (mirrors ce_0002's deleted_at rationale).

Nullable, no backfill: existing rows predate the column and tolerate its absence
(data-shape self-heal). Idempotent (existence-checked) because the CE installer
reruns migrations on every boot; reversible (downgrade drops the column).
Length 45 = IPv6 maximum, mirroring ApiKeyIpLog.ip_address.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0055_users_registration_ip"
down_revision = "ce_0054_cht_taxonomy_backfill"
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
            "  AND column_name = 'registration_ip'"
            ")"
        )
    ).scalar()
    if exists:
        return

    op.add_column(
        "users",
        sa.Column("registration_ip", sa.String(length=45), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "registration_ip")
