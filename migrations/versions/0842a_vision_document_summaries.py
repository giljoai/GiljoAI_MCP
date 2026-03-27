"""Create vision_document_summaries table and add extraction_custom_instructions

Revision ID: 0842a_vds
Revises: 0840e_project_meta
Create Date: 2026-03-27

Handover 0842a: Vision Document Analysis feature foundation.

New table: vision_document_summaries
  - Stores per-document summaries with source tracking (sumy vs ai)
  - Enables AI-preferred summary selection in Context Manager

New column on products:
  - extraction_custom_instructions TEXT (custom prompt instructions for AI analysis)
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision = "0842a_vds"
down_revision = "0840e_project_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Create vision_document_summaries table ──
    result = conn.execute(
        sa.text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'vision_document_summaries'"
        )
    )
    if result.fetchone() is None:
        op.create_table(
            "vision_document_summaries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tenant_key", sa.String(255), nullable=False),
            sa.Column(
                "document_id",
                sa.String(36),
                sa.ForeignKey("vision_documents.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "product_id",
                sa.String(36),
                sa.ForeignKey("products.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("source", sa.String(20), nullable=False),
            sa.Column("ratio", sa.Numeric(3, 2), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("tokens_original", sa.Integer(), nullable=False),
            sa.Column("tokens_summary", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "idx_vds_lookup",
            "vision_document_summaries",
            ["tenant_key", "document_id", "source", "ratio"],
        )
        op.create_index(
            "idx_vds_product",
            "vision_document_summaries",
            ["tenant_key", "product_id"],
        )

    # ── 2. Add extraction_custom_instructions column to products ──
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'products' AND column_name = 'extraction_custom_instructions'"
        )
    )
    if result.fetchone() is None:
        op.add_column(
            "products",
            sa.Column(
                "extraction_custom_instructions",
                sa.Text(),
                nullable=True,
                comment="Custom instructions appended to AI vision document extraction prompt",
            ),
        )


def downgrade() -> None:
    op.drop_table("vision_document_summaries")
    op.drop_column("products", "extraction_custom_instructions")
