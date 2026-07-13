# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Server-level runtime gauges (NOT tenant-scoped) — BE-6108.

One row per (worker, metric) holding a small integer gauge that describes the
running process, not any tenant's data. The first such gauge is the active
WebSocket connection count: each worker upserts its own live count on a short
cadence (a sibling of ``sync_api_metrics_to_db``), and the SaaS Ops Panel reads
``SUM(value)`` across workers within a freshness window to show the real number
instead of "unknown".

Tenant isolation does NOT apply here (mirrors ``SystemSetting`` / ``reaper_runs``):
WebSocket connections span tenants, the value is int-only, and there is no PII.
The table carries no ``tenant_key`` column, so the tenant-isolation guard does
not gate it.
"""

from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from .base import Base


class ServerRuntimeMetric(Base):
    """A per-worker integer runtime gauge (no tenant_key, no PII)."""

    __tablename__ = "server_runtime_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # Stable per-process identity ("<hostname>:<pid>") so each worker upserts its
    # own single row; rows from exited workers go stale and are excluded by the
    # reader's freshness window (and pruned by the writer).
    worker_id = Column(String(128), nullable=False)
    metric = Column(String(64), nullable=False)
    value = Column(Integer, nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("worker_id", "metric", name="uq_server_runtime_metric_worker_metric"),)

    def __repr__(self) -> str:
        return f"<ServerRuntimeMetric(worker_id={self.worker_id!r}, metric={self.metric!r}, value={self.value})>"
