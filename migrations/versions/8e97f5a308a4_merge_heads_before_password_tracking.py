"""merge_heads_before_password_tracking

Revision ID: 8e97f5a308a4
Revises: 003_system_user, 2ff9170e5524
Create Date: 2025-10-11 03:59:47.208152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e97f5a308a4'
down_revision: Union[str, Sequence[str], None] = ('003_system_user', '2ff9170e5524')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
