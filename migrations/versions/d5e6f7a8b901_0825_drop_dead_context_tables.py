"""Drop dead context tables (context_index, large_document_index, mcp_context_summary)

Revision ID: d5e6f7a8b901
Revises: c4d5e6f70812
Create Date: 2026-03-18

Drop three tables that are no longer used by any code path:
- context_index: Was for ContextIndex model, never written to
- large_document_index: Was for LargeDocumentIndex model, never written to
- mcp_context_summary: Was for MCPContextSummary model, only used by dead ContextSummarizer

NOTE: mcp_context_index is KEPT - it is actively used by VisionDocumentChunker.

All operations are IDEMPOTENT - safe on fresh installs where baseline may already omit these.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b901'
down_revision: Union[str, Sequence[str], None] = 'c4d5e6f70812'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEAD_TABLES = [
    "mcp_context_summary",
    "context_index",
    "large_document_index",
]


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = :table"
    ), {"table": table_name})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    for table_name in DEAD_TABLES:
        if _table_exists(conn, table_name):
            op.drop_table(table_name)


def downgrade() -> None:
    # Recreate context_index
    op.create_table(
        "context_index",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_key", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("index_type", sa.String(50), nullable=False),
        sa.Column("document_name", sa.String(255), nullable=False),
        sa.Column("section_name", sa.String(255), nullable=True),
        sa.Column("chunk_numbers", sa.JSON(), default=list),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("keywords", sa.JSON(), default=list),
        sa.Column("full_path", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(32), nullable=True),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("project_id", "document_name", "section_name", name="uq_context_index"),
    )
    op.create_index("idx_context_tenant", "context_index", ["tenant_key"])
    op.create_index("idx_context_type", "context_index", ["index_type"])
    op.create_index("idx_context_doc", "context_index", ["document_name"])

    # Recreate large_document_index
    op.create_table(
        "large_document_index",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_key", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("document_path", sa.Text(), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=True),
        sa.Column("total_size", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("meta_data", sa.JSON(), default=dict),
        sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "document_path", name="uq_large_doc_path"),
    )
    op.create_index("idx_large_doc_tenant", "large_document_index", ["tenant_key"])

    # Recreate mcp_context_summary
    op.create_table(
        "mcp_context_summary",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_key", sa.String(36), nullable=False, index=True),
        sa.Column("context_id", sa.String(36), unique=True, nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=True),
        sa.Column("full_content", sa.Text(), nullable=False),
        sa.Column("condensed_mission", sa.Text(), nullable=False),
        sa.Column("full_token_count", sa.Integer(), nullable=True),
        sa.Column("condensed_token_count", sa.Integer(), nullable=True),
        sa.Column("reduction_percent", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_mcp_summary_tenant_product", "mcp_context_summary", ["tenant_key", "product_id"])
    op.create_index("idx_mcp_summary_context_id", "mcp_context_summary", ["context_id"])
