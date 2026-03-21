"""0831_product_context_tuning

Add tuning_state JSONB column to products table and
notification_preferences JSONB column to users table for
the Product Context Tuning feature.

Revision ID: i9j0k1l2m345
Revises: h8i9j0k1l234
Create Date: 2026-03-21 16:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "i9j0k1l2m345"
down_revision: Union[str, Sequence[str], None] = "h8i9j0k1l234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tuning_state to products and notification_preferences to users."""
    op.add_column(
        "products",
        sa.Column(
            "tuning_state",
            JSONB,
            nullable=True,
            comment="Context tuning state: last_tuned_at, last_tuned_at_sequence, pending_proposals",
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "notification_preferences",
            JSONB,
            nullable=True,
            comment="User notification preferences: tuning reminders, thresholds",
        ),
    )


def downgrade() -> None:
    """Remove tuning columns."""
    op.drop_column("users", "notification_preferences")
    op.drop_column("products", "tuning_state")
