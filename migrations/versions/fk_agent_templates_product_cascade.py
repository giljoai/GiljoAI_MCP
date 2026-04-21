# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Add FK on agent_templates.product_id → products.id with ON DELETE CASCADE.

Product deletion now cascades to its agent templates at the DB level.
Nullable FK: orphan rows (product_id=NULL) are unaffected by the constraint
and are handled by the startup orphan migration.

Revision ID: fk_templates_product
Revises: 2c7b0f717e1d
Create Date: 2026-04-21
"""

import sqlalchemy as sa
from alembic import op

revision: str = "fk_templates_product"
down_revision: str = "2c7b0f717e1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Idempotency: only add FK if it doesn't already exist
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints"
            " WHERE constraint_name = 'fk_agent_templates_product_id'"
            " AND table_name = 'agent_templates'"
        )
    )
    if result.scalar_one_or_none():
        return  # Already exists

    # Clean up any templates pointing to non-existent products
    # (shouldn't happen, but guard before adding FK)
    conn.execute(
        sa.text(
            "DELETE FROM agent_templates"
            " WHERE product_id IS NOT NULL"
            " AND product_id NOT IN (SELECT id::text FROM products)"
        )
    )

    op.create_foreign_key(
        "fk_agent_templates_product_id",
        "agent_templates",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    conn = op.get_bind()

    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints"
            " WHERE constraint_name = 'fk_agent_templates_product_id'"
            " AND table_name = 'agent_templates'"
        )
    )
    if result.scalar_one_or_none():
        op.drop_constraint("fk_agent_templates_product_id", "agent_templates", type_="foreignkey")
