"""
Add project description field and project_id to MCPAgentJob.

Handover 0062: Project Launch Panel & Database Foundation
- Separate human input (description) from AI-generated mission
- Scope agent jobs to projects for proper tracking
- Enable project-level job management for Kanban workflow

Date: 2025-10-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import text


def upgrade():
    """Add description to projects and project_id to mcp_agent_jobs."""

    # Add description column to projects table
    op.add_column("projects", sa.Column("description", sa.Text(), nullable=True))

    # Backfill description from mission for existing projects
    # This preserves existing data during migration
    connection = op.get_bind()
    connection.execute(text("UPDATE projects SET description = mission WHERE description IS NULL"))

    # Make description NOT NULL after backfill
    op.alter_column("projects", "description", nullable=False)

    # Add project_id to mcp_agent_jobs table
    op.add_column("mcp_agent_jobs", sa.Column("project_id", sa.String(36), nullable=True))

    # For dev environment, we can leave orphaned jobs without project_id
    # In production, you'd want to handle this more carefully

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_mcp_agent_jobs_project", "mcp_agent_jobs", "projects", ["project_id"], ["id"], ondelete="CASCADE"
    )

    # Add indexes for performance
    op.create_index("idx_mcp_agent_jobs_project", "mcp_agent_jobs", ["project_id"])
    op.create_index("idx_mcp_agent_jobs_tenant_project", "mcp_agent_jobs", ["tenant_key", "project_id"])

    # For new installations, project_id should be required
    # For existing data, we'll handle orphaned jobs gracefully
    # Not making it NOT NULL to avoid breaking existing dev data


def downgrade():
    """Remove project description and project_id from MCPAgentJob."""

    # Drop indexes
    op.drop_index("idx_mcp_agent_jobs_tenant_project", "mcp_agent_jobs")
    op.drop_index("idx_mcp_agent_jobs_project", "mcp_agent_jobs")

    # Drop foreign key
    op.drop_constraint("fk_mcp_agent_jobs_project", "mcp_agent_jobs", type_="foreignkey")

    # Remove columns
    op.drop_column("mcp_agent_jobs", "project_id")
    op.drop_column("projects", "description")
