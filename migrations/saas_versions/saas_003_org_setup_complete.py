# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Add org_setup_complete column to organizations table (SAAS-007)

Revision ID: saas_003_org_setup_complete
Revises: saas_002_password_reset_tokens
Create Date: 2026-04-16

Tracks whether the org admin has completed the first-login setup wizard.
Defaults to False for all existing and new organizations.
"""

from alembic import op
import sqlalchemy as sa

revision = "saas_003_org_setup_complete"
down_revision = "saas_002_password_reset_tokens"
branch_labels = None
depends_on = "saas_002_password_reset_tokens"


def upgrade() -> None:
    # Idempotency guard: skip if column already exists
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.columns"
            "  WHERE table_name = 'organizations'"
            "  AND column_name = 'org_setup_complete'"
            ")"
        )
    )
    if result.scalar():
        return

    op.add_column(
        "organizations",
        sa.Column(
            "org_setup_complete",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("organizations", "org_setup_complete")
