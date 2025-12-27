"""remove_deprecated_vision_summary_fields

Handover 0374 Phase 1: Remove deprecated vision summary columns from vision_documents table.
Removes columns that are no longer used in the 3-tier summary system (light/medium/full).

Revision ID: 0670e17a56ff
Revises: caeddfdbb2a0
Create Date: 2025-12-22 16:24:44.232372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0670e17a56ff"
down_revision: Union[str, Sequence[str], None] = "caeddfdbb2a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove deprecated summary columns from vision_documents table."""
    # Drop deprecated summary text columns
    op.drop_column("vision_documents", "summary_text")
    op.drop_column("vision_documents", "summary_moderate")
    op.drop_column("vision_documents", "summary_heavy")

    # Drop deprecated token count columns
    op.drop_column("vision_documents", "summary_moderate_tokens")
    op.drop_column("vision_documents", "summary_heavy_tokens")

    # Drop deprecated compression_ratio column
    op.drop_column("vision_documents", "compression_ratio")


def downgrade() -> None:
    """Re-add deprecated summary columns for rollback (nullable for safety)."""
    # Re-add deprecated summary text columns
    op.add_column("vision_documents",
                  sa.Column("summary_text", sa.Text(), nullable=True))
    op.add_column("vision_documents",
                  sa.Column("summary_moderate", sa.Text(), nullable=True))
    op.add_column("vision_documents",
                  sa.Column("summary_heavy", sa.Text(), nullable=True))

    # Re-add deprecated token count columns
    op.add_column("vision_documents",
                  sa.Column("summary_moderate_tokens", sa.Integer(), nullable=True))
    op.add_column("vision_documents",
                  sa.Column("summary_heavy_tokens", sa.Integer(), nullable=True))

    # Re-add deprecated compression_ratio column
    op.add_column("vision_documents",
                  sa.Column("compression_ratio", sa.Float(), nullable=True))
