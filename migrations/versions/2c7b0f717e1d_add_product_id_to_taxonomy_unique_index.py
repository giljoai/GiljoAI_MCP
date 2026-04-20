# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Add product_id to uq_project_taxonomy_active unique index.

Scopes taxonomy series numbering per product instead of per tenant,
allowing two products under the same tenant to both have BE-0001.

Revision ID: 2c7b0f717e1d
Revises: a3c7e1f9d024
Create Date: 2026-04-18
"""

import sqlalchemy as sa
from alembic import op


revision: str = "2c7b0f717e1d"
down_revision: str = "a3c7e1f9d024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Idempotency: drop old index only if it exists
    result = conn.execute(sa.text("SELECT 1 FROM pg_indexes WHERE indexname = 'uq_project_taxonomy_active'"))
    if result.scalar_one_or_none():
        op.drop_index("uq_project_taxonomy_active", table_name="projects")

    # Recreate with product_id included
    op.create_index(
        "uq_project_taxonomy_active",
        "projects",
        ["tenant_key", "product_id", "project_type_id", "series_number", "subseries"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Idempotency: drop new index only if it exists
    result = conn.execute(sa.text("SELECT 1 FROM pg_indexes WHERE indexname = 'uq_project_taxonomy_active'"))
    if result.scalar_one_or_none():
        op.drop_index("uq_project_taxonomy_active", table_name="projects")

    # Recreate without product_id (original form)
    op.create_index(
        "uq_project_taxonomy_active",
        "projects",
        ["tenant_key", "project_type_id", "series_number", "subseries"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
