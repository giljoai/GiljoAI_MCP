# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Rename agent_templates depth 'type_only' to 'basic'

Revision ID: rename_type_only
Revises: baseline_v36
Create Date: 2026-04-12

Idempotent: safe to run on fresh installs (no rows match) and upgrades.
"""

from alembic import op


revision = "rename_type_only"
down_revision = "baseline_v36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE users SET depth_agent_templates = 'basic' "
        "WHERE depth_agent_templates = 'type_only'"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN depth_agent_templates SET DEFAULT 'basic'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE users SET depth_agent_templates = 'type_only' "
        "WHERE depth_agent_templates = 'basic'"
    )
    op.execute(
        "ALTER TABLE users ALTER COLUMN depth_agent_templates SET DEFAULT 'type_only'"
    )
