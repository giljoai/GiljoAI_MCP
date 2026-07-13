# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6063x: add (tenant_key, created_at DESC) indexes to high-cardinality list tables.

Revision ID: ce_0046_list_tables_tenant_created_index
Revises: ce_0045_pme_tenant_timestamp_index
Create Date: 2026-06-10

Paginated "recent items for this tenant" reads run
``WHERE tenant_key = ? ORDER BY created_at DESC LIMIT n`` against projects,
messages, and agent_jobs. Today these tables hold single-digit rows so the cost
is hidden, but at 10k+ rows/tenant the existing single-column tenant indexes
force a tenant-filtered scan + in-memory sort. A (tenant_key, created_at DESC)
composite lets Postgres satisfy filter + ordering from one index range read.

- projects: PARTIAL ``WHERE deleted_at IS NULL`` — every list read filters
  soft-deleted rows out, so the partial index stays small and exactly matches.
- messages / agent_jobs: no soft-delete column; plain composite.
- agent_executions: intentionally NOT indexed here — it has no created_at column;
  its list paths order by the joined agent_jobs.created_at.
- notifications: intentionally skipped — already covered by
  idx_notifications_tenant_user_created (tenant_key leads that 3-col index).
- product_memory_entries: already covered by idx_pme_tenant_timestamp (ce_0045).

Idempotent: each index is CREATE INDEX IF NOT EXISTS (plain, NOT CONCURRENTLY so
it runs inside Alembic's transaction). The CE installer reruns
``alembic upgrade head`` on every boot; a second run is a clean no-op.

Edition Scope: Both. projects/messages/agent_jobs are CE tables; this migration
lives in migrations/versions/ (NOT saas_versions/). The unified baseline
(baseline_v37_unified.py) gains the same three indexes for fresh-install parity;
the IF-NOT-EXISTS guard makes this incremental a no-op on fresh installs, matching
the ce_0045 / idx_pme_tenant_timestamp precedent.
"""

from alembic import op


revision = "ce_0046_list_tables_tenant_created_index"
down_revision = "ce_0045_pme_tenant_timestamp_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_projects_tenant_created "
        "ON projects (tenant_key, created_at DESC) "
        "WHERE deleted_at IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_tenant_created "
        "ON messages (tenant_key, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_jobs_tenant_created "
        "ON agent_jobs (tenant_key, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_agent_jobs_tenant_created")
    op.execute("DROP INDEX IF EXISTS idx_messages_tenant_created")
    op.execute("DROP INDEX IF EXISTS idx_projects_tenant_created")
