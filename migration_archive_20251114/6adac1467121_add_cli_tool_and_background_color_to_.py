"""add_cli_tool_and_background_color_to_agent_templates

Revision ID: 6adac1467121
Revises: 20251104_0102
Create Date: 2025-11-05 (SECURITY FIX)

SECURITY FIX: Replaced f-string SQL interpolation with CASE statement
to prevent SQL injection vulnerability. Original migration had dangerous
f"UPDATE ... WHERE role = '{role}'" pattern which could allow SQL injection
if role values were ever controlled by user input.

Changes from original:
- Replaced Python loop with single atomic CASE statement
- Added sqlalchemy.text() wrapper for query safety
- Added server_default for cli_tool (automatic backfill on column add)
- Made migration idempotent (WHERE background_color IS NULL)
- Drop server_default after backfill to allow future custom defaults
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "6adac1467121"
down_revision: Union[str, Sequence[str], None] = "20251104_0102"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - SECURITY HARDENED."""
    # Add cli_tool with server_default for automatic backfill
    # This ensures all existing rows get 'claude' without needing separate UPDATE
    op.add_column(
        "agent_templates",
        sa.Column("cli_tool", sa.String(20), nullable=False, server_default="claude")
    )

    # Add background_color (nullable - optional field)
    op.add_column(
        "agent_templates",
        sa.Column("background_color", sa.String(7), nullable=True)
    )

    # Backfill background_color using CASE statement (SQL injection safe)
    # Single atomic query instead of loop - more efficient and secure
    # WHERE clause makes this idempotent (safe to run multiple times)
    op.execute(text("""
        UPDATE agent_templates
        SET background_color = CASE role
            WHEN 'orchestrator' THEN '#D4A574'
            WHEN 'analyzer' THEN '#E74C3C'
            WHEN 'designer' THEN '#9B59B6'
            WHEN 'frontend' THEN '#3498DB'
            WHEN 'backend' THEN '#2ECC71'
            WHEN 'implementer' THEN '#3498DB'
            WHEN 'tester' THEN '#FFC300'
            WHEN 'reviewer' THEN '#9B59B6'
            WHEN 'documenter' THEN '#27AE60'
            ELSE '#90A4AE'
        END
        WHERE background_color IS NULL
    """))

    # Drop server_default after backfill (allows future custom defaults per tenant)
    op.alter_column("agent_templates", "cli_tool", server_default=None)

    # Add CHECK constraint for cli_tool validation
    op.create_check_constraint(
        "check_cli_tool",
        "agent_templates",
        "cli_tool IN ('claude', 'codex', 'gemini', 'generic')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("check_cli_tool", "agent_templates", type_="check")
    op.drop_column("agent_templates", "background_color")
    op.drop_column("agent_templates", "cli_tool")
