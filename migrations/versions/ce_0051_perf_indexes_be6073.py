# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6073 (F10 + m9): perf indexes for agent-stats, health-monitor, and the deletion reaper.

Revision ID: ce_0051_perf_indexes_be6073
Revises: ce_0050_roadmap_sort_order
Create Date: 2026-06-14

Five composite/tenant-leading indexes that turn today's tenant-filtered heap
scans into single index range reads. All tables are single-digit rows today, so
the cost is hidden; at 10k+ rows/tenant each of these becomes a per-tick or
per-request scan. Mirrors the ce_0045 / ce_0046 idempotent-index precedent.

F10 (a) messages (tenant_key, from_agent_id, created_at)
    GET /api/v1/stats/agents (job_statistics_repository.py) runs two correlated
    subqueries over messages keyed on from_agent_id (count + max(created_at)) per
    tenant. The existing idx_message_tenant leads on tenant_key only, so each
    subquery tenant-scans + filters from_agent_id in memory.

F10 (b) agent_executions (tenant_key, job_id, started_at DESC)
    Serves both shapes that dominate this table:
    - max(started_at) GROUP BY job_id WHERE tenant_key=? — the 3 health-monitor
      latest-instance subqueries (agent_health_monitor.py) that run per tenant
      every scan cycle.
    - ORDER BY started_at DESC LIMIT 1 WHERE job_id=? AND tenant_key=? — the
      ubiquitous latest-execution lookup (progress_repository, message_repository,
      user_approval_service). The DESC ordering matches the index so the LIMIT 1
      is a single index seek, no sort.
    idx_agent_executions_tenant_job covers (tenant_key, job_id) but stops short of
    started_at, so the aggregate/sort still touches every matching row.

m9 message_recipients / message_acknowledgments / message_completions (tenant_key)
    The SaaS deletion reaper issues DELETE FROM <table> WHERE tenant_key = ?. The
    only tenant index on these tables is idx_message_*_agent (agent_id, tenant_key)
    — agent_id leads, so the tenant-key purge is a full seq scan. A plain
    tenant_key index makes the per-tenant cascade delete an index range read.

Idempotent: every statement is CREATE INDEX IF NOT EXISTS (plain, NOT CONCURRENTLY
so it runs inside Alembic's transaction). The CE installer reruns
``alembic upgrade head`` on every boot; a second run is a clean no-op. Reversible:
downgrade drops each by name with IF EXISTS.

Edition Scope: Both. messages / agent_executions / message_* are CE core tables;
this migration lives in migrations/versions/ (NOT saas_versions/). The reaper that
benefits from the m9 indexes is SaaS, but the tables and indexes are CE.
"""

from alembic import op


revision = "ce_0051_perf_indexes_be6073"
down_revision = "ce_0050_roadmap_sort_order"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # F10 (a) — messages: agent-stats correlated subqueries (from_agent_id).
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_tenant_from_agent_created "
        "ON messages (tenant_key, from_agent_id, created_at)"
    )
    # F10 (b) — agent_executions: health-monitor max(started_at) aggregates +
    # latest-execution ORDER BY started_at DESC LIMIT 1.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_executions_tenant_job_started "
        "ON agent_executions (tenant_key, job_id, started_at DESC)"
    )
    # m9 — message junction tables: deletion reaper DELETE WHERE tenant_key = ?.
    op.execute("CREATE INDEX IF NOT EXISTS idx_message_recipients_tenant ON message_recipients (tenant_key)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_message_acks_tenant ON message_acknowledgments (tenant_key)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_message_completions_tenant ON message_completions (tenant_key)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_message_completions_tenant")
    op.execute("DROP INDEX IF EXISTS idx_message_acks_tenant")
    op.execute("DROP INDEX IF EXISTS idx_message_recipients_tenant")
    op.execute("DROP INDEX IF EXISTS idx_agent_executions_tenant_job_started")
    op.execute("DROP INDEX IF EXISTS idx_messages_tenant_from_agent_created")
