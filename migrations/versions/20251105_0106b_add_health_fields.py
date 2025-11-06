"""
Add health monitoring fields to mcp_agent_jobs table.

Handover 0106: Agent Health Monitoring System
- Adds last_health_check (timestamp)
- Adds health_status (unknown, healthy, warning, critical, timeout)
- Adds health_failure_count (consecutive failures)

Revision ID: 20251105_0106b
Revises: 20251104_0102
Create Date: 2025-11-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251105_0106b'
down_revision = '20251104_0102'  # Update this to match your latest migration
branch_labels = None
depends_on = None


def upgrade():
    """Add health monitoring fields to mcp_agent_jobs table."""

    # Add health monitoring columns
    op.add_column(
        'mcp_agent_jobs',
        sa.Column(
            'last_health_check',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp of last health check scan'
        )
    )

    op.add_column(
        'mcp_agent_jobs',
        sa.Column(
            'health_status',
            sa.String(length=20),
            nullable=False,
            server_default='unknown',
            comment='Health state: unknown, healthy, warning, critical, timeout'
        )
    )

    op.add_column(
        'mcp_agent_jobs',
        sa.Column(
            'health_failure_count',
            sa.Integer(),
            nullable=False,
            server_default='0',
            comment='Consecutive health check failures'
        )
    )

    # Add check constraints
    op.create_check_constraint(
        'ck_mcp_agent_job_health_status',
        'mcp_agent_jobs',
        "health_status IN ('unknown', 'healthy', 'warning', 'critical', 'timeout')"
    )

    op.create_check_constraint(
        'ck_mcp_agent_job_health_failure_count',
        'mcp_agent_jobs',
        'health_failure_count >= 0'
    )

    # Add index for health status queries
    op.create_index(
        'idx_mcp_agent_jobs_health_status',
        'mcp_agent_jobs',
        ['tenant_key', 'health_status'],
        unique=False
    )


def downgrade():
    """Remove health monitoring fields from mcp_agent_jobs table."""

    # Drop index
    op.drop_index('idx_mcp_agent_jobs_health_status', table_name='mcp_agent_jobs')

    # Drop check constraints
    op.drop_constraint('ck_mcp_agent_job_health_failure_count', 'mcp_agent_jobs', type_='check')
    op.drop_constraint('ck_mcp_agent_job_health_status', 'mcp_agent_jobs', type_='check')

    # Drop columns
    op.drop_column('mcp_agent_jobs', 'health_failure_count')
    op.drop_column('mcp_agent_jobs', 'health_status')
    op.drop_column('mcp_agent_jobs', 'last_health_check')
