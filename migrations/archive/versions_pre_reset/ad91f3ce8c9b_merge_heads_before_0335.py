"""merge_heads_before_0335

Revision ID: ad91f3ce8c9b
Revises: 0260_execution_mode, d5a6385e1ff2
Create Date: 2025-12-08 19:55:00.774586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad91f3ce8c9b'
down_revision: Union[str, Sequence[str], None] = ('0260_execution_mode', 'd5a6385e1ff2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
