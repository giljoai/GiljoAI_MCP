"""Add orchestrator auto check-in columns to projects table (Handover 0904)

Revision ID: 0904_auto_checkin
Revises: baseline_v35
Create Date: 2026-04-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0904_auto_checkin"
down_revision = "baseline_v35"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("projects")]

    if "auto_checkin_enabled" not in columns:
        op.add_column(
            "projects",
            sa.Column("auto_checkin_enabled", sa.Boolean(), nullable=False, server_default="false"),
        )
    if "auto_checkin_interval" not in columns:
        op.add_column(
            "projects",
            sa.Column("auto_checkin_interval", sa.Integer(), nullable=False, server_default="60"),
        )


def downgrade():
    op.drop_column("projects", "auto_checkin_interval")
    op.drop_column("projects", "auto_checkin_enabled")
