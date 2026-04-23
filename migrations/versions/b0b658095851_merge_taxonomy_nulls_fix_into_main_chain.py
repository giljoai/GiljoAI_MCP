# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""merge taxonomy nulls fix into main chain

Revision ID: b0b658095851
Revises: 50520bba0d1d, fix_taxonomy_nulls_not_distinct
Create Date: 2026-04-23 15:23:58.375629

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0b658095851'
down_revision: Union[str, Sequence[str], None] = ('50520bba0d1d', 'fix_taxonomy_nulls_not_distinct')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
