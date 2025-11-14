"""merge_0106c_with_activated_paused_fields

Revision ID: 00450fa7780c
Revises: 20251113_0106c, 4efd65f41897
Create Date: 2025-11-13 22:22:43.614785

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00450fa7780c'
down_revision: Union[str, Sequence[str], None] = ('20251113_0106c', '4efd65f41897')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
