"""Add setup wizard state columns to users table (Handover 0855a)

Revision ID: 0855a_setup_state
Revises: baseline_v34
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0855a_setup_state"
down_revision = "baseline_v34"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("users")]

    if "setup_complete" not in columns:
        op.add_column("users", sa.Column("setup_complete", sa.Boolean(), nullable=False, server_default="false"))
    if "setup_selected_tools" not in columns:
        op.add_column("users", sa.Column("setup_selected_tools", JSONB(), nullable=True))
    if "setup_step_completed" not in columns:
        op.add_column("users", sa.Column("setup_step_completed", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("users", "setup_step_completed")
    op.drop_column("users", "setup_selected_tools")
    op.drop_column("users", "setup_complete")
