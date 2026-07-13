# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add server_runtime_metrics table (per-worker runtime gauges) — BE-6108.

Revision ID: ce_0056_server_runtime_metrics
Revises: ce_0055_users_registration_ip
Create Date: 2026-06-16

Creates ``server_runtime_metrics`` — a small server-level (NOT tenant-scoped)
table holding one int gauge per (worker_id, metric). The first gauge is the
active WebSocket connection count, written per-worker by a background task and
read (SUM across workers, within a freshness window) by the SaaS Ops Panel so it
shows the real count instead of "unknown". Int-only, no PII, no tenant_key
(mirrors ``system_settings`` / ``reaper_runs``).

Idempotent (existence-checked) because the CE installer reruns migrations on
every boot; reversible (downgrade drops the table). New table, so no backfill.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0056_server_runtime_metrics"
down_revision = "ce_0055_users_registration_ip"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotency guard: skip if the table already exists (CE reruns on boot).
    conn = op.get_bind()
    exists = conn.execute(
        sa.text("SELECT EXISTS (  SELECT FROM information_schema.tables  WHERE table_name = 'server_runtime_metrics')")
    ).scalar()
    if exists:
        return

    op.create_table(
        "server_runtime_metrics",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("worker_id", sa.String(length=128), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("worker_id", "metric", name="uq_server_runtime_metric_worker_metric"),
    )


def downgrade() -> None:
    op.drop_table("server_runtime_metrics")
