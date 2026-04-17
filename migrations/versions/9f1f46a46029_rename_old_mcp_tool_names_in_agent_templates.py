# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""rename_old_mcp_tool_names_in_agent_templates

Revision ID: 9f1f46a46029
Revises: bbdc55534128
Create Date: 2026-04-16 23:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f1f46a46029"
down_revision: str | None = "bbdc55534128"
branch_labels: str | None = None
depends_on: str | None = None

# IMP-1 tool rename mappings (v1.1.6)
_TOOL_RENAMES = {
    "spawn_agent_job": "spawn_job",
    "gil_get_vision_doc": "get_vision_doc",
    "gil_write_product": "update_product_fields",
    "list_messages": "inspect_messages",
    "get_agent_templates_for_export": "list_agent_templates",
}

# Text columns in agent_templates that may contain old tool names
_TEXT_COLUMNS = ["system_instructions", "user_instructions", "description"]


def upgrade() -> None:
    """Replace old MCP tool names in agent_templates text columns (idempotent)."""
    conn = op.get_bind()

    # Verify table exists before proceeding
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'agent_templates'"
        )
    )
    if not result.fetchone():
        return

    for col_name in _TEXT_COLUMNS:
        # Verify column exists
        col_check = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'agent_templates' "
                "AND column_name = :col_name"
            ),
            {"col_name": col_name},
        )
        if not col_check.fetchone():
            continue

        for old_name, new_name in _TOOL_RENAMES.items():
            # Idempotent: only updates rows that still contain the old name
            # col_name is from _TEXT_COLUMNS constant, not user input
            conn.execute(
                sa.text(
                    f"UPDATE agent_templates "
                    f"SET {col_name} = REPLACE({col_name}, :old_name, :new_name) "
                    f"WHERE {col_name} LIKE :pattern"
                ),
                {
                    "old_name": old_name,
                    "new_name": new_name,
                    "pattern": f"%{old_name}%",
                },
            )

    # Also handle the special case: remove 'discovery' references
    # Replace 'discovery(' with 'list_projects(' and 'discovery tool' with
    # 'list_projects tool' as the discovery tool was folded into list_projects
    for col_name in _TEXT_COLUMNS:
        col_check = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'agent_templates' "
                "AND column_name = :col_name"
            ),
            {"col_name": col_name},
        )
        if not col_check.fetchone():
            continue

        # col_name is from _TEXT_COLUMNS constant, not user input
        conn.execute(
            sa.text(
                f"UPDATE agent_templates "
                f"SET {col_name} = REPLACE({col_name}, 'discovery(', 'list_projects(') "
                f"WHERE {col_name} LIKE '%discovery(%'"
            ),
        )
        conn.execute(
            sa.text(
                f"UPDATE agent_templates "
                f"SET {col_name} = REPLACE({col_name}, 'discovery tool', 'list_projects tool') "
                f"WHERE {col_name} LIKE '%discovery tool%'"
            ),
        )


def downgrade() -> None:
    """Reverse tool name replacements in agent_templates (best-effort)."""
    conn = op.get_bind()

    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'agent_templates'"
        )
    )
    if not result.fetchone():
        return

    for col_name in _TEXT_COLUMNS:
        col_check = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'agent_templates' "
                "AND column_name = :col_name"
            ),
            {"col_name": col_name},
        )
        if not col_check.fetchone():
            continue

        for old_name, new_name in _TOOL_RENAMES.items():
            # col_name is from _TEXT_COLUMNS constant, not user input
            conn.execute(
                sa.text(
                    f"UPDATE agent_templates "
                    f"SET {col_name} = REPLACE({col_name}, :new_name, :old_name) "
                    f"WHERE {col_name} LIKE :pattern"
                ),
                {
                    "new_name": new_name,
                    "old_name": old_name,
                    "pattern": f"%{new_name}%",
                },
            )
