"""Add agent_interactions table for sub-agent tracking

Revision ID: a7b8c9d2e3f4
Revises: 45abb2fcc00d
Create Date: 2025-09-14 17:40:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a7b8c9d2e3f4"
down_revision: Union[str, Sequence[str], None] = "45abb2fcc00d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent_interactions table for hybrid orchestration."""
    op.create_table("agent_interactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_key", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("parent_agent_id", sa.String(length=36), nullable=True),
        sa.Column("sub_agent_name", sa.String(length=100), nullable=False),
        sa.Column("interaction_type", sa.String(length=20), nullable=False),
        sa.Column("mission", sa.Text(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["parent_agent_id"], ["agents.id"] ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"] ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("interaction_type IN ('SPAWN', 'COMPLETE', 'ERROR')", name="ck_interaction_type")
    )

    # Create indexes for performance
    op.create_index("idx_interaction_tenant", "agent_interactions", ["tenant_key"], unique=False)
    op.create_index("idx_interaction_project", "agent_interactions", ["project_id"], unique=False)
    op.create_index("idx_interaction_parent", "agent_interactions", ["parent_agent_id"], unique=False)
    op.create_index("idx_interaction_type", "agent_interactions", ["interaction_type"], unique=False)
    op.create_index("idx_interaction_created", "agent_interactions", ["created_at"], unique=False)


def downgrade() -> None:
    """Drop agent_interactions table and its indexes."""
    # Drop indexes first
    op.drop_index("idx_interaction_created", table_name="agent_interactions")
    op.drop_index("idx_interaction_type", table_name="agent_interactions")
    op.drop_index("idx_interaction_parent", table_name="agent_interactions")
    op.drop_index("idx_interaction_project", table_name="agent_interactions")
    op.drop_index("idx_interaction_tenant", table_name="agent_interactions")

    # Drop the table
    op.drop_table("agent_interactions")
