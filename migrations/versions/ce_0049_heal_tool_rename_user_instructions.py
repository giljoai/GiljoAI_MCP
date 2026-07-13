# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6052c: heal frozen old tool names in default-template user_instructions rows.

Revision ID: ce_0049_heal_tool_rename_user_instructions
Revises: ce_0048_roadmap_item_blocked
Create Date: 2026-06-14

Eight MCP tool names were renamed as part of the INF-6052 contract harmonisation
chain (steps a/b). The ``refresh_tenant_template_instructions`` path is
operator-triggered only (``scripts/refresh_templates.py``) and does NOT run on
startup, so it cannot be relied on to heal existing rows — hence this migration
does its own raw-SQL heal (the CE installer reruns ``alembic upgrade head`` on
every boot, which is the path that actually reaches existing tenants).

This migration rewrites the 8 old→new pairs in-place for rows whose ``name``
matches one of the default template names (orchestrator, implementer, tester,
analyzer, reviewer, documenter).  Tenant-CUSTOMISED rows — those whose
``user_instructions`` differ from the default seeded text — are NOT identified
at migration time (we can't snapshot them cheaply); instead this is a
substring-replace pass, meaning any user text that happened to include an old
tool name will also be updated.  The boot-notice banner surfaces the rename to
admins so they can inspect their custom instructions.

Idempotent: each REPLACE is a no-op when the old substring is absent (the row
was already healed or was seeded fresh).  The CE installer reruns
``alembic upgrade head`` on every boot; a second run produces zero changed rows
and no error.

Edition Scope: CE — ``agent_templates`` is a CE table (``migrations/versions/``).
SaaS inherits the migration unchanged.  NEVER placed in startup.py (SaaS prod
runs uvicorn directly and never executes startup.py; migrations run on both).
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0049_heal_tool_rename_user_instructions"
down_revision = "ce_0048_roadmap_item_blocked"
branch_labels = None
depends_on = None

_DEFAULT_TEMPLATE_NAMES = (
    "orchestrator",
    "implementer",
    "tester",
    "analyzer",
    "reviewer",
    "documenter",
)

_RENAMES: list[tuple[str, str]] = [
    ("get_agent_mission", "get_job_mission"),
    ("update_agent_mission", "update_job_mission"),
    ("fetch_context", "get_context"),
    ("write_360_memory", "write_memory_entry"),
    ("close_project_and_update_memory", "write_project_closeout"),
    ("inspect_messages", "get_messages"),
    ("update_product_fields", "update_product_context"),
    ("submit_tuning_review", "propose_product_context_update"),
]

_NAMES_TUPLE = ", ".join(f"'{n}'" for n in _DEFAULT_TEMPLATE_NAMES)


def upgrade() -> None:
    conn = op.get_bind()
    for old_name, new_name in _RENAMES:
        # Replace bare name occurrences (e.g. `get_agent_mission(`) and also the
        # namespaced mcp__ form and the underscore form used by Gemini frontmatter.
        # All three forms use the same old substring, so a single pass per pair is
        # sufficient — REPLACE is idempotent when the old substring is absent.
        conn.execute(
            sa.text(
                f"UPDATE agent_templates "  # noqa: S608
                f"SET user_instructions = REPLACE(user_instructions, :old, :new) "
                f"WHERE name IN ({_NAMES_TUPLE}) "
                f"AND user_instructions LIKE :pattern"
            ),
            {"old": old_name, "new": new_name, "pattern": f"%{old_name}%"},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for old_name, new_name in _RENAMES:
        conn.execute(
            sa.text(
                f"UPDATE agent_templates "  # noqa: S608
                f"SET user_instructions = REPLACE(user_instructions, :new, :old) "
                f"WHERE name IN ({_NAMES_TUPLE}) "
                f"AND user_instructions LIKE :pattern"
            ),
            {"old": old_name, "new": new_name, "pattern": f"%{new_name}%"},
        )
