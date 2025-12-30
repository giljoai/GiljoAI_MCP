"""
Add 'blocked' status to MCPAgentJob status constraint.

Handover 0066: Agent Self-Navigation for Kanban Board
- Support 4-column Kanban workflow: pending, active, completed, blocked
- 'blocked' replaces 'failed' for user-facing terminology
- Agents use 'blocked' to indicate they need help or encountered an issue

Date: 2025-10-28
"""

from alembic import op


def upgrade():
    """Add 'blocked' to the MCPAgentJob status check constraint."""

    # Drop existing check constraint
    op.drop_constraint("ck_mcp_agent_job_status", "mcp_agent_jobs", type_="check")

    # Create new check constraint with 'blocked' status
    op.create_check_constraint(
        "ck_mcp_agent_job_status", "mcp_agent_jobs", "status IN ('pending', 'active', 'completed', 'failed', 'blocked')"
    )


def downgrade():
    """Remove 'blocked' from the MCPAgentJob status check constraint."""

    # Drop modified check constraint
    op.drop_constraint("ck_mcp_agent_job_status", "mcp_agent_jobs", type_="check")

    # Restore original check constraint without 'blocked'
    op.create_check_constraint(
        "ck_mcp_agent_job_status", "mcp_agent_jobs", "status IN ('pending', 'active', 'completed', 'failed')"
    )
