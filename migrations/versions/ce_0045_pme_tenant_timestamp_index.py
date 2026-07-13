# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6063a: add (tenant_key, timestamp DESC) index on product_memory_entries.

Revision ID: ce_0045_pme_tenant_timestamp_index
Revises: ce_0044_antigravity_tool_type
Create Date: 2026-06-10

The dashboard "recent memories" widget runs
``WHERE tenant_key = ? ORDER BY timestamp DESC LIMIT N`` on every
``/stats`` poll (``ProductStatisticsRepository.get_recent_memory_entries``).
The existing product_memory_entries indexes cover
``(tenant_key, product_id)`` and ``(product_id, sequence)`` but NONE order
by ``timestamp``, so this query does a tenant-filtered scan + sort. Adding a
``(tenant_key, timestamp DESC)`` composite lets Postgres satisfy both the
filter and the ordering from the index, turning the poll into an index-range
read of the top N rows.

Idempotent: the index is created only if absent (CREATE INDEX IF NOT EXISTS).
The CE installer reruns ``alembic upgrade head`` on every boot, so a second
run is a clean no-op.

Edition Scope: Both. ``product_memory_entries`` is a CE table; this migration
lives in ``migrations/versions/`` (NOT ``saas_versions/``). SaaS inherits the
index unchanged. The unified baseline (``baseline_v37_unified.py``) gains the
same index for fresh-install parity; this incremental's IF-NOT-EXISTS guard
makes it a no-op on fresh installs, matching the existing index-creation
pattern in the baseline.
"""

from alembic import op


revision = "ce_0045_pme_tenant_timestamp_index"
down_revision = "ce_0044_antigravity_tool_type"
branch_labels = None
depends_on = None


_INDEX_NAME = "idx_pme_tenant_timestamp"


def upgrade() -> None:
    op.execute(f"CREATE INDEX IF NOT EXISTS {_INDEX_NAME} ON product_memory_entries (tenant_key, timestamp DESC)")


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_INDEX_NAME}")
