# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""merge SEC-0005b and user_managed_export

Revision ID: 50520bba0d1d
Revises: 9254a70aef1d, add_user_managed_export
Create Date: 2026-04-23 13:59:52.278594

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50520bba0d1d'
down_revision: Union[str, Sequence[str], None] = ('9254a70aef1d', 'add_user_managed_export')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
