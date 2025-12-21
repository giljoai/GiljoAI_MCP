"""add_vision_summarization_columns_handover_0345b

Revision ID: e2afa1851965
Revises: 7983bf9c91c9
Create Date: 2025-12-12 01:14:03.094106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2afa1851965'
down_revision: Union[str, Sequence[str], None] = '7983bf9c91c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add LSA summarization columns to vision_documents."""
    # Handover 0345b: Add summarization metadata columns for LSA integration
    # These columns enable extractive summarization using Latent Semantic Analysis

    # Add summary_text column (stores the generated summary)
    op.add_column('vision_documents',
        sa.Column('summary_text', sa.Text(), nullable=True,
                  comment='Extractive summary using LSA (optional, generated when enabled)'))

    # Add is_summarized flag (tracks whether document has been summarized)
    op.add_column('vision_documents',
        sa.Column('is_summarized', sa.Boolean(), nullable=False, server_default='false',
                  comment='Has document been summarized using LSA algorithm'))

    # Add original_token_count (stores pre-summarization token count)
    op.add_column('vision_documents',
        sa.Column('original_token_count', sa.Integer(), nullable=True,
                  comment='Original document token count before summarization'))

    # Add compression_ratio (tracks summarization efficiency)
    op.add_column('vision_documents',
        sa.Column('compression_ratio', sa.Float(), nullable=True,
                  comment='Compression ratio achieved (0.0-1.0, e.g., 0.75 = 75% compression)'))


def downgrade() -> None:
    """Downgrade schema - Remove LSA summarization columns."""
    # Handover 0345b: Remove summarization columns in reverse order
    op.drop_column('vision_documents', 'compression_ratio')
    op.drop_column('vision_documents', 'original_token_count')
    op.drop_column('vision_documents', 'is_summarized')
    op.drop_column('vision_documents', 'summary_text')
