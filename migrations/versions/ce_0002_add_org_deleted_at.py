# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available.

"""Add deleted_at column to organizations (SAAS-022 account deletion grace period).

Revision ID: ce_0002_add_org_deleted_at
Revises: ce_0001_add_org_status
Create Date: 2026-04-25

Adds a nullable ``deleted_at`` TIMESTAMPTZ column to ``organizations`` so the
deletion reaper can determine when the 30-day grace period ends. The column is
unused by CE code paths; SaaS deletion service and reaper are the only readers.
Added to the CE chain per the edition-isolation rule that new columns on existing
CE tables belong in the CE migration chain even when only SaaS code reads/writes
them.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0002_add_org_deleted_at"
down_revision = "ce_0001_add_org_status"
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
            "  AND column_name = 'deleted_at'"
            ")"
        )
    ).scalar()
    if exists:
        return

    op.add_column(
        "organizations",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "deleted_at")
