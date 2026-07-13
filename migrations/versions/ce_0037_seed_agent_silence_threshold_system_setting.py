# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Seed global agent silence threshold system setting (BE-6009).

Revision ID: ce_0037_seed_agent_silence_threshold_system_setting
Revises: ce_0036_add_ctx_taxonomy_type
Create Date: 2026-05-29

BE-6009 moves ``agent_silence_threshold_minutes`` out of tenant-scoped
``settings.general`` and into the deployment-wide ``system_settings`` table.

Idempotency: upgrade inserts the default only when the key is absent.
Downgrade deletes only this key.

Edition Scope: Both -- ``system_settings`` is a CE model shared by SaaS via the
CE migration chain, while the runtime write endpoint is CE-only.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0037_seed_agent_silence_threshold_system_setting"
down_revision = "ce_0036_add_ctx_taxonomy_type"
branch_labels = None
depends_on = None


SETTING_KEY = "agent_silence_threshold_minutes"
DEFAULT_VALUE = "10"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO system_settings (key, value, updated_at)
            SELECT :key, :value, NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM system_settings WHERE key = :key
            )
            """
        ).bindparams(key=SETTING_KEY, value=DEFAULT_VALUE)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM system_settings WHERE key = :key").bindparams(
            key=SETTING_KEY,
        )
    )
