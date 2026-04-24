# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available.

"""Add status column to organizations (INF-0002 Ops Panel soft-delete).

Revision ID: ce_0001_add_org_status
Revises: baseline_v37
Create Date: 2026-04-23

Adds a nullable ``status`` VARCHAR(32) column to ``organizations`` so the
Ops Panel soft-delete action can mark orgs as ``'deleted'`` without hard
deleting rows. The column is unused by CE code paths; the ops panel is the
only writer. Added to the CE chain per the edition-isolation rule that
new columns on existing CE tables belong in the CE migration chain even
when only SaaS code reads/writes them.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0001_add_org_status"
down_revision = "baseline_v37"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotency guard: skip if column already exists
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.columns"
            "  WHERE table_name = 'organizations'"
            "  AND column_name = 'status'"
            ")"
        )
    ).scalar()
    if exists:
        return

    op.add_column(
        "organizations",
        sa.Column("status", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "status")
