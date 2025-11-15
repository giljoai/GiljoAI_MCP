"""merge_0106_heads

Revision ID: 8cd632d27c5e
Revises: 20251105_0106, 20251105_0106b
Create Date: 2025-11-05 23:58:22.985784

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8cd632d27c5e'
down_revision: Union[str, Sequence[str], None] = ('20251105_0106', '20251105_0106b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
