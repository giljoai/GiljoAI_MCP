# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Create product_agent_assignments junction table.

Lightweight per-product agent toggle: templates belong to the tenant,
products reference which ones are active via this junction table.

Chains after the Phase B revert migration that restored tenant-scoped templates.

Revision ID: create_product_agent_assignments
Revises: revert_product_templates
Create Date: 2026-04-21
"""

import sqlalchemy as sa
from alembic import op

revision: str = "create_product_agent_assignments"
down_revision: str = "revert_product_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Idempotency: check if table already exists
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = 'product_agent_assignments'")
    )
    if result.scalar_one_or_none():
        return  # Table already exists, skip

    op.create_table(
        "product_agent_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "product_id",
            sa.String(36),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "template_id",
            sa.String(36),
            sa.ForeignKey("agent_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("tenant_key", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Unique constraint: one assignment per product+template pair
    op.create_unique_constraint(
        "uq_product_template_assignment",
        "product_agent_assignments",
        ["product_id", "template_id"],
    )

    # Indexes for query performance
    op.create_index("idx_assignment_tenant", "product_agent_assignments", ["tenant_key"])
    op.create_index("idx_assignment_product", "product_agent_assignments", ["product_id"])
    op.create_index("idx_assignment_template", "product_agent_assignments", ["template_id"])
    op.create_index("idx_assignment_active", "product_agent_assignments", ["is_active"])


def downgrade() -> None:
    conn = op.get_bind()

    # Idempotency: check if table exists before dropping
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = 'product_agent_assignments'")
    )
    if result.scalar_one_or_none():
        op.drop_table("product_agent_assignments")
