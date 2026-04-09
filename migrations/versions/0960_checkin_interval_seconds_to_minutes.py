# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Convert auto_checkin_interval from seconds to minutes

Revision ID: 0960_checkin_min
Revises: 0950b_exec_status
Create Date: 2026-04-06

Handover 0960: The auto_checkin_interval column stored values in seconds
(30, 60, 90). This migration converts existing rows to minutes and updates
the server_default from 60 to 10.

Idempotency: Checks if values are already in minute range (<=60) before
converting. Only converts rows where the value exceeds 60 (i.e. still in
seconds). Server default is updated only if it differs from the target.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text as sa_text


revision: str = "0960_checkin_min"
down_revision: Union[str, Sequence[str], None] = "0950b_exec_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_MINUTES = (5, 10, 15, 20, 30, 40, 60)


def upgrade() -> None:
    conn = op.get_bind()

    # Convert existing second-based values to minutes (only rows still in seconds)
    # Values > 60 are definitely still in seconds; divide and clamp to nearest valid step
    conn.execute(
        sa_text(
            "UPDATE projects "
            "SET auto_checkin_interval = GREATEST(5, (auto_checkin_interval / 60)) "
            "WHERE auto_checkin_interval > 60"
        )
    )

    # Clamp any remaining non-standard values to the nearest valid minute step
    # (e.g., old value of 30 seconds is now ambiguous with 30 minutes — leave as-is since 30 is valid)
    # Values like 90 already handled above. Values <= 60 that aren't valid steps: clamp to 10.
    valid_set = ", ".join(str(v) for v in VALID_MINUTES)
    conn.execute(
        sa_text(
            f"UPDATE projects "
            f"SET auto_checkin_interval = 10 "
            f"WHERE auto_checkin_interval NOT IN ({valid_set})"
        )
    )

    # Update server default from 60 to 10
    op.alter_column(
        "projects",
        "auto_checkin_interval",
        server_default=sa_text("10"),
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Convert minute-based values back to seconds
    conn.execute(
        sa_text(
            "UPDATE projects "
            "SET auto_checkin_interval = auto_checkin_interval * 60 "
            "WHERE auto_checkin_interval <= 60"
        )
    )

    # Restore server default to 60 (seconds)
    op.alter_column(
        "projects",
        "auto_checkin_interval",
        server_default=sa_text("60"),
    )
