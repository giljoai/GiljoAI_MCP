"""add web to target_platforms check constraint

Revision ID: a47a279202a2
Revises: baseline_v35
Create Date: 2026-04-03 23:10:13.008297

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a47a279202a2'
down_revision: Union[str, Sequence[str], None] = 'baseline_v35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_CONSTRAINT = "target_platforms <@ ARRAY['windows', 'linux', 'macos', 'android', 'ios', 'all']::VARCHAR[]"
NEW_CONSTRAINT = "target_platforms <@ ARRAY['windows', 'linux', 'macos', 'android', 'ios', 'web', 'all']::VARCHAR[]"


def upgrade() -> None:
    """Add 'web' to target_platforms check constraint."""
    # Idempotency: drop old constraint only if it exists
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE products DROP CONSTRAINT IF EXISTS ck_product_target_platforms_valid;
        END $$;
    """)
    op.create_check_constraint(
        "ck_product_target_platforms_valid",
        "products",
        NEW_CONSTRAINT,
    )


def downgrade() -> None:
    """Remove 'web' from target_platforms check constraint."""
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE products DROP CONSTRAINT IF EXISTS ck_product_target_platforms_valid;
        END $$;
    """)
    op.create_check_constraint(
        "ck_product_target_platforms_valid",
        "products",
        OLD_CONSTRAINT,
    )
