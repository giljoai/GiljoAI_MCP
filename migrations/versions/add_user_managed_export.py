# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Add user_managed_export column to agent_templates.

Allows users to dismiss the "May be outdated" staleness warning manually.
When set, the template shows "User Managed" instead of a stale warning.
Cleared automatically when the template is edited (updated_at changes).

Revision ID: add_user_managed_export
Revises: revert_product_templates
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op

revision: str = "add_user_managed_export"
down_revision: str = "revert_product_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name='agent_templates' AND column_name='user_managed_export'"
        )
    )
    if not result.fetchone():
        op.add_column(
            "agent_templates",
            sa.Column("user_managed_export", sa.Boolean(), server_default="false", nullable=False),
        )


def downgrade() -> None:
    op.drop_column("agent_templates", "user_managed_export")
