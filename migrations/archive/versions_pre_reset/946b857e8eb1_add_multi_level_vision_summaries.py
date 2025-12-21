"""add_multi_level_vision_summaries

Revision ID: 946b857e8eb1
Revises: e2afa1851965
Create Date: 2025-12-12 02:02:47.012736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '946b857e8eb1'
down_revision: Union[str, Sequence[str], None] = 'e2afa1851965'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add multi-level summary columns to vision_documents table.

    Handover 0345e: Sumy Semantic Compression Levels
    - Adds 6 new columns for light/moderate/heavy summaries + token counts
    - All columns nullable for backward compatibility
    - No data migration needed (existing docs can be re-summarized on demand)
    """
    # Add light summary columns
    op.add_column(
        'vision_documents',
        sa.Column(
            'summary_light',
            sa.Text(),
            nullable=True,
            comment='Light summary (~5K tokens, ~250 sentences, 87% compression)'
        )
    )
    op.add_column(
        'vision_documents',
        sa.Column(
            'summary_light_tokens',
            sa.Integer(),
            nullable=True,
            comment='Actual token count in light summary'
        )
    )

    # Add moderate summary columns
    op.add_column(
        'vision_documents',
        sa.Column(
            'summary_moderate',
            sa.Text(),
            nullable=True,
            comment='Moderate summary (~12.5K tokens, ~625 sentences, 69% compression)'
        )
    )
    op.add_column(
        'vision_documents',
        sa.Column(
            'summary_moderate_tokens',
            sa.Integer(),
            nullable=True,
            comment='Actual token count in moderate summary'
        )
    )

    # Add heavy summary columns
    op.add_column(
        'vision_documents',
        sa.Column(
            'summary_heavy',
            sa.Text(),
            nullable=True,
            comment='Heavy summary (~25K tokens, ~1,250 sentences, 37% compression)'
        )
    )
    op.add_column(
        'vision_documents',
        sa.Column(
            'summary_heavy_tokens',
            sa.Integer(),
            nullable=True,
            comment='Actual token count in heavy summary'
        )
    )


def downgrade() -> None:
    """Remove multi-level summary columns."""
    op.drop_column('vision_documents', 'summary_heavy_tokens')
    op.drop_column('vision_documents', 'summary_heavy')
    op.drop_column('vision_documents', 'summary_moderate_tokens')
    op.drop_column('vision_documents', 'summary_moderate')
    op.drop_column('vision_documents', 'summary_light_tokens')
    op.drop_column('vision_documents', 'summary_light')
