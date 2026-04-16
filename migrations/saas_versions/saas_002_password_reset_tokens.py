# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Create password_reset_tokens table (SAAS-006)

Revision ID: saas_002_password_reset_tokens
Revises: saas_baseline_v1
Create Date: 2026-04-16

Stores SHA-256 hashed tokens for email-based password recovery.
Each token is tenant-isolated, single-use, and expires after 1 hour.
"""

import sqlalchemy as sa
from alembic import op

revision = "saas_002_password_reset_tokens"
down_revision = "saas_baseline_v1"
branch_labels = None
depends_on = "saas_baseline_v1"


def upgrade() -> None:
    # Idempotency guard: skip if table already exists
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.tables"
            "  WHERE table_name = 'password_reset_tokens'"
            ")"
        )
    )
    if result.scalar():
        return

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_key", sa.String(36), nullable=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("idx_prt_tenant", "password_reset_tokens", ["tenant_key"])
    op.create_index(
        "idx_prt_token_hash",
        "password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index("idx_prt_user_id", "password_reset_tokens", ["user_id"])
    op.create_index(
        "idx_prt_email_created",
        "password_reset_tokens",
        ["email", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_prt_email_created", table_name="password_reset_tokens")
    op.drop_index("idx_prt_user_id", table_name="password_reset_tokens")
    op.drop_index("idx_prt_token_hash", table_name="password_reset_tokens")
    op.drop_index("idx_prt_tenant", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
