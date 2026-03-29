"""Add coding_conventions to product_architectures and brand_guidelines to products

Revision ID: 0844a_conventions
Revises: 0842a_vds
Create Date: 2026-03-29

New columns:
- product_architectures.coding_conventions TEXT (coding standards for agents)
- products.brand_guidelines TEXT (brand & design guidelines for frontend agents)
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision = "0844a_conventions"
down_revision = "0842a_vds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Idempotency guard: coding_conventions on product_architectures
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'product_architectures' AND column_name = 'coding_conventions'"
        )
    )
    if result.fetchone() is None:
        op.add_column(
            "product_architectures",
            sa.Column("coding_conventions", sa.Text(), nullable=True),
        )

    # Idempotency guard: brand_guidelines on products
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'products' AND column_name = 'brand_guidelines'"
        )
    )
    if result.fetchone() is None:
        op.add_column(
            "products",
            sa.Column(
                "brand_guidelines",
                sa.Text(),
                nullable=True,
                comment="Brand & design guidelines for frontend-facing agents",
            ),
        )


def downgrade() -> None:
    op.drop_column("products", "brand_guidelines")
    op.drop_column("product_architectures", "coding_conventions")
