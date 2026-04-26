# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available.

"""Widen alembic_version.version_num to VARCHAR(64).

Revision ID: ce_0003_widen_alembic_version
Revises: ce_0002_add_org_deleted_at
Create Date: 2026-04-25

Alembic's default ``alembic_version.version_num`` is VARCHAR(32). Long
human-readable revision IDs (e.g. ``ce_0003_widen_alembic_version_num``) can
exceed 32 chars and produce a ``StringDataRightTruncation`` on stamp/upgrade.
Widen to VARCHAR(64). Idempotent: skips ALTER if column is already >= 64.
PostgreSQL only (project is Postgres-only -- no SQLite branching).
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0003_widen_alembic_version"
down_revision = "ce_0002_add_org_deleted_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    current_len = conn.execute(
        sa.text(
            "SELECT character_maximum_length "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND table_name = 'alembic_version' "
            "AND column_name = 'version_num'"
        )
    ).scalar()
    if current_len is None or current_len >= 64:
        return
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")


def downgrade() -> None:
    # No-op: shrinking version_num back to VARCHAR(32) would truncate any stamped
    # revision IDs longer than 32 chars (data loss risk on the alembic state row).
    pass
