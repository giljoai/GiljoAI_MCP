# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Users: add ``learning_beat`` + ``router_choice`` tutorial re-entry state.

Revision ID: ce_0079_users_tutorial_reentry_state
Revises: ce_0078_projects_superseded_status_and_successor
Create Date: 2026-07-16

BE-9201 -- onboarding-tutorial re-entry persistence (companion FE project
FE-9200). ``learning_beat`` (nullable int, 1-6 validated at the PATCH
boundary) lets a reopened tutorial resume at the beat the user left;
``router_choice`` (nullable short string, 'A'|'B'|'C'|'D' validated at the
PATCH boundary) makes the bootstrap-card spotlight survive reload.

Operations
----------
1. Add nullable ``learning_beat`` (Integer) to ``users`` (existence-guarded).
2. Add nullable ``router_choice`` (String(8)) to ``users`` (existence-guarded).

Chain routing
-------------
Both are columns on the CE ``User`` model (src/giljo_mcp/models/auth.py), so
this lives in ``migrations/versions/`` (the CE chain), NEVER ``saas_versions/``.
Paired with a parity edit to ``baseline_v38_unified.py`` adding the same two
columns at the END of the users create_table -- this migration appends them,
so declaring them last in the baseline keeps the fresh-install and chain-replay
schemas byte-identical (the INF-5060 parity invariant covers column ORDER).

Idempotency
-----------
Both column adds are guarded by ``inspect()`` column-existence checks. The CE
installer reruns the chain on every boot, so every step must be re-runnable.

Data-facing DoD
---------------
Additive only: two nullable columns, no defaults, no backfill. Every existing
row is untouched and remains valid -- tolerant by construction.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "ce_0079_users_tutorial_reentry_state"
down_revision = "ce_0078_projects_superseded_status_and_successor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("users")]

    if "learning_beat" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "learning_beat",
                sa.Integer(),
                nullable=True,
                comment="BE-9201: last onboarding-tutorial beat reached (1-6); NULL until the tutorial persists it",
            ),
        )

    if "router_choice" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "router_choice",
                sa.String(length=8),
                nullable=True,
                comment="BE-9201: tutorial router door picked (A|B|C|D); drives the bootstrap-card spotlight",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("users")]

    if "router_choice" in columns:
        op.drop_column("users", "router_choice")
    if "learning_beat" in columns:
        op.drop_column("users", "learning_beat")
