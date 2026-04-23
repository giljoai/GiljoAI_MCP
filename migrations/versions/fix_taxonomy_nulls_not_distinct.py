# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Fix taxonomy unique index to treat NULL subseries as equal.

PostgreSQL treats NULL != NULL in unique indexes by default, allowing
duplicate taxonomies like two DOC-0001 (with NULL subseries) in the
same product. NULLS NOT DISTINCT (PG 15+) fixes this.

Revision ID: fix_taxonomy_nulls_not_distinct
Revises: create_product_agent_assignments
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op


revision: str = "fix_taxonomy_nulls_not_distinct"
down_revision: str = "create_product_agent_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Drop existing index if present
    result = conn.execute(sa.text("SELECT 1 FROM pg_indexes WHERE indexname = 'uq_project_taxonomy_active'"))
    if result.scalar_one_or_none():
        op.drop_index("uq_project_taxonomy_active", table_name="projects")

    # Recreate with NULLS NOT DISTINCT so NULL subseries is treated as equal
    conn.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_project_taxonomy_active "
            "ON projects (tenant_key, product_id, project_type_id, series_number, subseries) "
            "NULLS NOT DISTINCT "
            "WHERE deleted_at IS NULL"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    result = conn.execute(sa.text("SELECT 1 FROM pg_indexes WHERE indexname = 'uq_project_taxonomy_active'"))
    if result.scalar_one_or_none():
        op.drop_index("uq_project_taxonomy_active", table_name="projects")

    # Recreate without NULLS NOT DISTINCT (original PG default)
    op.create_index(
        "uq_project_taxonomy_active",
        "projects",
        ["tenant_key", "product_id", "project_type_id", "series_number", "subseries"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
