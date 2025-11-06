"""Merge heads

Revision ID: 08b6b226922d
Revises: add_product_id_to_tasks, add_template_mgmt
Create Date: 2025-10-04 00:52:17.993047

"""

from collections.abc import Sequence
from typing import Union


# revision identifiers, used by Alembic.
revision: str = "08b6b226922d"
down_revision: Union[str, Sequence[str], None] = ("add_product_id_to_tasks", "add_template_mgmt")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
