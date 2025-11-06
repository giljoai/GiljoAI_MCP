"""Add alias column to projects table

Revision ID: add_alias_to_projects
Revises: f7f0422fda1e
Create Date: 2025-10-20 00:00:00.000000

This migration adds a 6-character alphanumeric alias column to the projects table.
The alias serves as a short, human-friendly identifier for projects.

Migration Steps:
1. Add alias column (nullable initially)
2. Generate unique aliases for existing projects
3. Create unique index on alias column
4. Make alias NOT NULL after backfilling
"""

import random
import string
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "add_alias_to_projects"
down_revision: Union[str, Sequence[str], None] = "f7f0422fda1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def generate_unique_alias(existing_aliases: set) -> str:
    """
    Generate a unique 6-character alphanumeric alias.

    Format: A-Z0-9, 6 characters (e.g., "A1B2C3")

    Args:
        existing_aliases: Set of already-used aliases to avoid duplicates

    Returns:
        str: Unique 6-character alias
    """
    chars = string.ascii_uppercase + string.digits
    max_attempts = 100  # Prevent infinite loop

    for _ in range(max_attempts):
        alias = "".join(random.choices(chars, k=6))
        if alias not in existing_aliases:
            existing_aliases.add(alias)
            return alias

    raise ValueError("Failed to generate unique alias after 100 attempts")


def upgrade() -> None:
    """Upgrade schema - Add alias column to projects table."""
    # Get database connection
    connection = op.get_bind()

    # Step 1: Add alias column as nullable String(6)
    op.add_column(
        "projects",
        sa.Column(
            "alias",
            sa.String(length=6),
            nullable=True,
            comment="6-character alphanumeric project identifier (e.g., A1B2C3)",
        ),
    )

    # Step 2: Backfill aliases for existing projects
    # Query all existing projects with tenant_key for isolation
    result = connection.execute(text("SELECT id, tenant_key FROM projects ORDER BY created_at"))
    projects = result.fetchall()

    if projects:
        existing_aliases = set()

        # Generate unique aliases for each project
        # Use batch updates within a transaction for performance
        for project_id, tenant_key in projects:
            alias = generate_unique_alias(existing_aliases)

            # Update project with generated alias
            # CRITICAL: Filter by BOTH id AND tenant_key for data isolation
            connection.execute(
                text("UPDATE projects SET alias = :alias WHERE id = :project_id AND tenant_key = :tenant_key"),
                {"alias": alias, "project_id": project_id, "tenant_key": tenant_key},
            )

    # Step 3: Create unique index on alias column
    # This ensures alias uniqueness at the database level
    op.create_index("idx_project_alias_unique", "projects", ["alias"], unique=True)

    # Step 4: Make alias NOT NULL after backfilling
    # All existing projects now have aliases, so we can enforce NOT NULL
    op.alter_column(
        "projects",
        "alias",
        existing_type=sa.String(length=6),
        nullable=False,
        existing_comment="6-character alphanumeric project identifier (e.g., A1B2C3)",
    )


def downgrade() -> None:
    """Downgrade schema - Remove alias column from projects table."""
    # Drop the unique index first
    op.drop_index("idx_project_alias_unique", table_name="projects")

    # Drop the alias column
    op.drop_column("projects", "alias")
