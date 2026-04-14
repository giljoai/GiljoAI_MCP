# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.

"""Add hidden column to projects table (CE-OPT-4).

Revision ID: add_hidden_to_projects
Revises: rename_type_only_to_basic
Create Date: 2026-04-14
"""

import sqlalchemy as sa
from alembic import op

revision = "add_hidden_to_projects"
down_revision = "add_last_activity_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotency guard
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'projects' AND column_name = 'hidden'"
        )
    )
    if result.fetchone() is None:
        op.add_column(
            "projects",
            sa.Column(
                "hidden",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="Whether project is hidden from default list view",
            ),
        )


def downgrade() -> None:
    op.drop_column("projects", "hidden")
