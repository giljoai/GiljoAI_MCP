# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""add_org_setup_complete_to_organizations

Revision ID: bbdc55534128
Revises: add_hidden_to_projects
Create Date: 2026-04-16 01:32:54.142948

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbdc55534128'
down_revision: Union[str, Sequence[str], None] = 'add_hidden_to_projects'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add org_setup_complete column to organizations (idempotent)."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'organizations' AND column_name = 'org_setup_complete'"
        )
    )
    if not result.fetchone():
        op.add_column(
            "organizations",
            sa.Column("org_setup_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )


def downgrade() -> None:
    """Remove org_setup_complete column from organizations."""
    op.drop_column("organizations", "org_setup_complete")
