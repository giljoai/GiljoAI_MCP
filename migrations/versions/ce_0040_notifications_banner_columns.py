# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add banner-consolidation columns to notifications.

Revision ID: ce_0040_notifications_banner_columns
Revises: ce_0039_create_notifications
Create Date: 2026-06-03

IMP-5037b Phase 1: consolidate the legacy standalone dashboard banners onto the
notifications table so a single row is the authority for both the bell and the
page-banner surface.

Adds columns to ``notifications``:
- ``surface``     Text NOT NULL DEFAULT 'bell' + CHECK IN ('bell','banner','both')
- ``role_filter`` Text NULL  — server-enforced role gate (e.g. 'admin')
- ``cta_label``   Text NULL  — call-to-action label
- ``cta_route``   Text NULL  — NAMED Vue route string (NOT a URL)
- ``dismissible`` Boolean NOT NULL DEFAULT true

Idempotent: every ADD COLUMN / ADD CONSTRAINT is guarded by an
information_schema existence check. The CE installer reruns ``alembic upgrade
head`` on every boot. Existing rows are backfilled to ``surface='bell'`` /
``dismissible=true`` by the column server defaults; an explicit UPDATE also
normalizes any NULL ``surface`` left by a partial prior run.

Edition Scope: CE -- ``notifications`` is a CE model.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0040_notifications_banner_columns"
down_revision = "ce_0039_create_notifications"
branch_labels = None
depends_on = None


NOTIFICATIONS_TABLE = "notifications"
SURFACE_CHECK = "ck_notifications_surface"


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.first() is not None


def _has_constraint(conn, table: str, constraint: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = :table AND constraint_name = :constraint"
        ),
        {"table": table, "constraint": constraint},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, NOTIFICATIONS_TABLE, "surface"):
        op.add_column(
            NOTIFICATIONS_TABLE,
            sa.Column("surface", sa.Text(), nullable=False, server_default=sa.text("'bell'")),
        )

    if not _has_column(conn, NOTIFICATIONS_TABLE, "role_filter"):
        op.add_column(NOTIFICATIONS_TABLE, sa.Column("role_filter", sa.Text(), nullable=True))

    if not _has_column(conn, NOTIFICATIONS_TABLE, "cta_label"):
        op.add_column(NOTIFICATIONS_TABLE, sa.Column("cta_label", sa.Text(), nullable=True))

    if not _has_column(conn, NOTIFICATIONS_TABLE, "cta_route"):
        op.add_column(NOTIFICATIONS_TABLE, sa.Column("cta_route", sa.Text(), nullable=True))

    if not _has_column(conn, NOTIFICATIONS_TABLE, "dismissible"):
        op.add_column(
            NOTIFICATIONS_TABLE,
            sa.Column("dismissible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )

    # Backfill any row that a partial prior run may have left without a surface.
    op.execute("UPDATE notifications SET surface = 'bell' WHERE surface IS NULL")

    if not _has_constraint(conn, NOTIFICATIONS_TABLE, SURFACE_CHECK):
        op.create_check_constraint(
            SURFACE_CHECK,
            NOTIFICATIONS_TABLE,
            "surface IN ('bell', 'banner', 'both')",
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_constraint(conn, NOTIFICATIONS_TABLE, SURFACE_CHECK):
        op.drop_constraint(SURFACE_CHECK, NOTIFICATIONS_TABLE, type_="check")

    for column in ("dismissible", "cta_route", "cta_label", "role_filter", "surface"):
        if _has_column(conn, NOTIFICATIONS_TABLE, column):
            op.drop_column(NOTIFICATIONS_TABLE, column)
