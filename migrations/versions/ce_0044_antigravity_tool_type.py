# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6041b: widen agent_executions.tool_type CHECK to include 'antigravity'.

Revision ID: ce_0044_antigravity_tool_type
Revises: ce_0043_projects_execution_mode_nullable
Create Date: 2026-06-09

Antigravity CLI (`agy`) replaces the free/Pro/individual Gemini CLI tier on
2026-06-18. A switching user's agy executions record under
``tool_type = 'antigravity'`` (the platform string is ``antigravity_cli``; the
tool_type drops the ``_cli`` suffix, mirroring ``gemini_cli`` -> ``gemini``).

This ADDITIVELY widens the ``ck_agent_execution_tool_type`` CHECK constraint to
accept ``'antigravity'`` alongside the existing values. The ``'gemini'`` value is
KEPT -- Enterprise / Gemini Code Assist Standard+Enterprise / paid-API-key users
retain Gemini CLI (no announced end date). This is a widening, not a rename.

Idempotent: the CHECK constraint is dropped (existence-guarded) and recreated
with the wider value set. The CE installer reruns ``alembic upgrade head`` on
every boot, so a second run is a clean no-op.

Edition Scope: CE -- ``agent_executions`` is a CE table; this migration lives in
``migrations/versions/`` (NOT ``saas_versions/``). SaaS inherits the change
unchanged. The unified baseline (``baseline_v37_unified.py``) is intentionally
NOT edited: fresh installs converge to the wider constraint via this incremental,
matching the ce_0043 precedent for incremental-driven schema convergence.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0044_antigravity_tool_type"
down_revision = "ce_0043_projects_execution_mode_nullable"
branch_labels = None
depends_on = None


_TOOL_TYPE_CONSTRAINT = "ck_agent_execution_tool_type"

_TOOL_TYPE_CHECK_OLD = "tool_type IN ('claude-code', 'codex', 'gemini', 'universal')"
_TOOL_TYPE_CHECK_NEW = "tool_type IN ('claude-code', 'codex', 'gemini', 'antigravity', 'universal')"


def _has_check_constraint(conn, name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = :name AND constraint_type = 'CHECK'"
        ),
        {"name": name},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if _has_check_constraint(conn, _TOOL_TYPE_CONSTRAINT):
        op.drop_constraint(_TOOL_TYPE_CONSTRAINT, "agent_executions", type_="check")
    op.create_check_constraint(
        _TOOL_TYPE_CONSTRAINT,
        "agent_executions",
        _TOOL_TYPE_CHECK_NEW,
    )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_check_constraint(conn, _TOOL_TYPE_CONSTRAINT):
        op.drop_constraint(_TOOL_TYPE_CONSTRAINT, "agent_executions", type_="check")
    op.create_check_constraint(
        _TOOL_TYPE_CONSTRAINT,
        "agent_executions",
        _TOOL_TYPE_CHECK_OLD,
    )
