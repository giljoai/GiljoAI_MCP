"""merge_0435d_and_0960_heads

Revision ID: bee938301ffa
Revises: 0435d_requires_action, 0960_checkin_min
Create Date: 2026-04-09 14:45:36.260443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bee938301ffa'
down_revision: Union[str, Sequence[str], None] = ('0435d_requires_action', '0960_checkin_min')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
