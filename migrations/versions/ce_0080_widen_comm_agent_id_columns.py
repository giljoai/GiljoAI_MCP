# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Widen the message-hub fan-out agent-id columns from varchar(36) to varchar(64).

Revision ID: ce_0080_widen_comm_agent_id_columns
Revises: ce_0079_users_tutorial_reentry_state
Create Date: 2026-07-17

BE-9214 -- live-blocker fix. The Agent Message Hub validates ``agent_id`` /
``from_agent`` up to 64 chars at the ``@mcp.tool`` boundary, but the legacy
message-persistence tables the hub reuses for thread fan-out
(``CommThreadRepository.persist_thread_message``) carried UUID-sized varchar(36)
agent-id columns. Once ANY participant with a >36-char id joined a thread, EVERY
broadcast to that thread 500'd on the recipient fan-out INSERT
(``StringDataRightTruncationError: value too long for type character varying(36)``);
the poster's own id length was irrelevant because the fan-out inserts a row per
participant. Observed 2026-07-17 on a live operation with a 45-char reviewer id.

Sweep of the schema for the same class -- every free-form agent-id column
narrower than the validated 64:

- ``messages.from_agent_id``            (poster; a 64-char poster 500s the messages INSERT)
- ``message_recipients.agent_id``       (the reported incident -- recipient fan-out)
- ``message_acknowledgments.agent_id``  (same family -- ack fan-out)
- ``message_completions.agent_id``      (same family -- completion fan-out)
- ``sequence_runs.conductor_agent_id``  (chain conductor identity; a >36-char conductor
                                         id 500s at chain-start self-registration -- the
                                         same class at the chain-runtime boundary. Folded
                                         in per the orchestrator ruling on this project.)

Already wide enough (varchar 255), left untouched: ``comm_threads.next_action_owner``
(the baton) and ``comm_participants.participant_id``. Out of scope and NOT changed
here: ``agent_executions.agent_id`` (a generated UUID, never a free-form id) and
``sequence_runs.conductor_project_id`` (a project UUID, not an agent id).

Chain routing
-------------
All four are columns on CE models (``src/giljo_mcp/models/tasks.py``), so this
lives in ``migrations/versions/`` (the CE chain), NEVER ``saas_versions/``. Paired
with the matching width edit in ``baseline_v38_unified.py`` so a fresh install
builds the columns at 64 directly and this migration's width guards no-op
(the INF-5060 parity invariant).

Idempotency
-----------
Each widen is guarded by an ``inspect()`` current-width check -- the ALTER runs
only when the column is still narrower than 64, so the CE installer's every-boot
re-run is a no-op. Widening is data-preserving: no row is touched, no default, no
backfill (tolerant by construction -- existing short ids remain valid).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "ce_0080_widen_comm_agent_id_columns"
down_revision = "ce_0079_users_tutorial_reentry_state"
branch_labels = None
depends_on = None


# (table, column, nullable) -- the agent-id columns widened to 64.
_WIDEN: tuple[tuple[str, str, bool], ...] = (
    ("messages", "from_agent_id", True),
    ("message_recipients", "agent_id", False),
    ("message_acknowledgments", "agent_id", False),
    ("message_completions", "agent_id", False),
    ("sequence_runs", "conductor_agent_id", True),
)


def _current_length(inspector, table: str, column: str) -> int | None:
    """Return the varchar length of ``table.column``, or None if absent/untyped."""
    for col in inspector.get_columns(table):
        if col["name"] == column:
            return getattr(col["type"], "length", None)
    return None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table, column, nullable in _WIDEN:
        if table not in existing_tables:
            continue
        if _current_length(inspector, table, column) == 64:
            continue  # already widened (fresh install via baseline, or a re-run)
        op.alter_column(
            table,
            column,
            type_=sa.String(length=64),
            existing_type=sa.String(length=36),
            existing_nullable=nullable,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table, column, _nullable in _WIDEN:
        if table not in existing_tables:
            continue
        if _current_length(inspector, table, column) == 36:
            continue
        # Truncate-safe narrow: any id longer than 36 is clipped so the type change
        # cannot fail on the rollback path (rollback reverts the feature).
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR(36) USING substring({column} for 36)")
