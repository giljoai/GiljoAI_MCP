# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available.

"""Enforce NOT NULL on projects.product_id.

Revision ID: ce_0004_projects_product_id_not_null
Revises: ce_0003_widen_alembic_version
Create Date: 2026-04-27

Projects must always belong to a product. Historical NULL rows leaked into
every product's project list via an OR-NULL fallback in the repository
filter. Orphan rows are removed (none expected in a healthy install) and
the column is set NOT NULL so the issue cannot recur at the data layer.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0004_projects_product_id_not_null"
down_revision = "ce_0003_widen_alembic_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Defensive: orphan rows would block ALTER ... SET NOT NULL. Delete any
    # remaining NULL-product_id projects (legacy fallback rows).
    conn.execute(sa.text("DELETE FROM projects WHERE product_id IS NULL"))
    op.alter_column("projects", "product_id", existing_type=sa.String(length=36), nullable=False)


def downgrade() -> None:
    op.alter_column("projects", "product_id", existing_type=sa.String(length=36), nullable=True)
