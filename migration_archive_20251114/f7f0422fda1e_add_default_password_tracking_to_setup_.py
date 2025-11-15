"""add_default_password_tracking_to_setup_state

Revision ID: f7f0422fda1e
Revises: 8e97f5a308a4
Create Date: 2025-10-11 03:59:52.821455

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f7f0422fda1e"
down_revision: Union[str, Sequence[str], None] = "8e97f5a308a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add default_password_active and password_changed_at columns to setup_state table."""
    # Add default_password_active column
    op.add_column(
        "setup_state",
        sa.Column(
            "default_password_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="True if default admin/admin password is still active",
        ),
    )

    # Add password_changed_at column
    op.add_column(
        "setup_state",
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when default password was changed",
        ),
    )


def downgrade() -> None:
    """Remove default_password_active and password_changed_at columns from setup_state table."""
    op.drop_column("setup_state", "password_changed_at")
    op.drop_column("setup_state", "default_password_active")
