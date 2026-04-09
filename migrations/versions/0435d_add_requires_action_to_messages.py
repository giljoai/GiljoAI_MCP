# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Add requires_action column to messages table

Revision ID: 0435d_requires_action
Revises: 0435b_closed_status
Create Date: 2026-04-09

Handover 0435d: Adds a requires_action boolean flag to messages so
informational post-completion messages don't trigger false reactivations.
Default false — existing messages are treated as informational.

Idempotency: uses DO/EXCEPTION block to handle pre-existing column.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op


revision: str = "0435d_requires_action"
down_revision: Union[str, Sequence[str], None] = "0435b_closed_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE messages ADD COLUMN requires_action BOOLEAN NOT NULL DEFAULT false;
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """)


def downgrade() -> None:
    op.drop_column("messages", "requires_action")
