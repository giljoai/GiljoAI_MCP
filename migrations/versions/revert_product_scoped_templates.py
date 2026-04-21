# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Revert product-scoped agent templates to tenant-scoped.

Drop the FK constraint fk_agent_templates_product_id and the product-scoped
unique constraint. Replace with tenant-scoped unique constraint.
Also drop the idx_template_product index (product_id no longer a scoping key).

This migration is part of the template simplification rollback that reverts
the product-scoping introduced after v1.1.6.

Revision ID: revert_product_templates
Revises: fk_templates_product
Create Date: 2026-04-21
"""

import sqlalchemy as sa
from alembic import op

revision: str = "revert_product_templates"
down_revision: str = "fk_templates_product"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Drop FK constraint if it exists
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints"
            " WHERE constraint_name = 'fk_agent_templates_product_id'"
            " AND table_name = 'agent_templates'"
        )
    )
    if result.scalar_one_or_none():
        op.drop_constraint("fk_agent_templates_product_id", "agent_templates", type_="foreignkey")

    # 2. Drop old product-scoped unique constraint if it exists
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints"
            " WHERE constraint_name = 'uq_template_product_name_version'"
            " AND table_name = 'agent_templates'"
        )
    )
    if result.scalar_one_or_none():
        op.drop_constraint("uq_template_product_name_version", "agent_templates", type_="unique")

    # 3. Drop idx_template_product index if it exists
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = 'idx_template_product' AND tablename = 'agent_templates'")
    )
    if result.scalar_one_or_none():
        op.drop_index("idx_template_product", table_name="agent_templates")

    # 4. Before creating the tenant-scoped unique constraint, handle duplicates.
    # If multiple templates exist with same (tenant_key, name, version) due to
    # product-scoping, keep only the one with the lowest created_at (or id).
    conn.execute(
        sa.text(
            "DELETE FROM agent_templates WHERE id IN ("
            "  SELECT id FROM ("
            "    SELECT id, ROW_NUMBER() OVER ("
            "      PARTITION BY tenant_key, name, version"
            "      ORDER BY created_at ASC NULLS LAST, id ASC"
            "    ) AS rn"
            "    FROM agent_templates"
            "  ) ranked WHERE rn > 1"
            ")"
        )
    )

    # 5. Create tenant-scoped unique constraint
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints"
            " WHERE constraint_name = 'uq_template_tenant_name_version'"
            " AND table_name = 'agent_templates'"
        )
    )
    if not result.scalar_one_or_none():
        op.create_unique_constraint(
            "uq_template_tenant_name_version",
            "agent_templates",
            ["tenant_key", "name", "version"],
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop tenant-scoped unique constraint
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints"
            " WHERE constraint_name = 'uq_template_tenant_name_version'"
            " AND table_name = 'agent_templates'"
        )
    )
    if result.scalar_one_or_none():
        op.drop_constraint("uq_template_tenant_name_version", "agent_templates", type_="unique")

    # Restore product-scoped unique constraint
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints"
            " WHERE constraint_name = 'uq_template_product_name_version'"
            " AND table_name = 'agent_templates'"
        )
    )
    if not result.scalar_one_or_none():
        op.create_unique_constraint(
            "uq_template_product_name_version",
            "agent_templates",
            ["product_id", "name", "version"],
        )

    # Restore idx_template_product index
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = 'idx_template_product' AND tablename = 'agent_templates'")
    )
    if not result.scalar_one_or_none():
        op.create_index("idx_template_product", "agent_templates", ["product_id"])

    # Restore FK constraint
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints"
            " WHERE constraint_name = 'fk_agent_templates_product_id'"
            " AND table_name = 'agent_templates'"
        )
    )
    if not result.scalar_one_or_none():
        op.create_foreign_key(
            "fk_agent_templates_product_id",
            "agent_templates",
            "products",
            ["product_id"],
            ["id"],
            ondelete="CASCADE",
        )
