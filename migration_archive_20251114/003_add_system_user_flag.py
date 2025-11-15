"""Add is_system_user flag to User model for localhost auto-login

Revision ID: 003_system_user
Revises: d189b2321f76
Create Date: 2025-10-09

This migration adds the `is_system_user` boolean flag to the User model
to support Phase 1 auto-login infrastructure for localhost deployment mode.

System users (like "localhost") are auto-created during setup and bypass
password authentication for local development convenience.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "003_system_user"
down_revision: Union[str, Sequence[str], None] = "d189b2321f76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_system_user column, make password_hash nullable, and mark existing localhost user."""
    # 1. Add is_system_user column with default=False
    op.add_column(
        "users",
        sa.Column(
            "is_system_user",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="True for auto-created system users (localhost) that bypass password auth",
        ),
    )

    # 2. Create index for efficient system user queries
    op.create_index("idx_user_system", "users", ["is_system_user"], unique=False)

    # 3. Make password_hash nullable for system users (auto-login only)
    # System users don't require passwords as they use auto-login
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)

    # 4. Mark any existing "localhost" user as a system user
    # This ensures backward compatibility with any pre-existing localhost accounts
    op.execute("""
        UPDATE users
        SET is_system_user = true
        WHERE username = 'localhost'
    """)


def downgrade() -> None:
    """Remove is_system_user column and restore password_hash NOT NULL constraint."""
    # 1. Make password_hash NOT NULL again
    # WARNING: This will fail if any users have NULL password_hash
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)

    # 2. Drop index
    op.drop_index("idx_user_system", table_name="users")

    # 3. Drop column
    op.drop_column("users", "is_system_user")
