"""simplify_job_signaling - remove acknowledged and mission_read_at columns

Revision ID: d5a6385e1ff2
Revises: c972fded3b0e
Create Date: 2025-12-06 12:00:00.000000

CONTEXT:
These columns were removed from the MCPAgentJob model as part of
job signaling simplification. The job lifecycle no longer requires
explicit acknowledgment tracking or mission read timestamps.

Removed columns:
- mcp_agent_jobs.acknowledged (Boolean, nullable)
- mcp_agent_jobs.mission_read_at (DateTime with timezone, nullable)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5a6385e1ff2'
down_revision: Union[str, Sequence[str], None] = 'c972fded3b0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove deprecated job signaling columns from mcp_agent_jobs table.

    These columns are no longer used in the simplified job lifecycle.

    Note: Uses raw SQL with IF EXISTS for idempotency - handles cases where
    columns may not exist (e.g., fresh install from baseline that already
    reflects the final schema state).
    """
    # Use raw SQL with IF EXISTS for idempotency
    # This handles fresh installs where baseline already omits these columns
    conn = op.get_bind()

    # Drop acknowledged column if it exists
    conn.execute(sa.text(
        "ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS acknowledged"
    ))

    # Drop mission_read_at column if it exists
    conn.execute(sa.text(
        "ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS mission_read_at"
    ))


def downgrade() -> None:
    """
    Rollback: Re-add the removed columns.

    Note: Restored columns will be empty (NULL) for existing records.
    """
    # Re-add acknowledged column with default False
    op.add_column('mcp_agent_jobs',
                  sa.Column('acknowledged', sa.Boolean(), nullable=True, server_default='false'))

    # Re-add mission_read_at column
    op.add_column('mcp_agent_jobs',
                  sa.Column('mission_read_at', sa.DateTime(timezone=True), nullable=True))
