# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Per-tenant skills-bundle acknowledgement (CE, tenant-scoped).

Records the SKILLS_VERSION a tenant last acknowledged by running
``/giljo_setup``. The skills-drift banner compares the server's bundled
``SKILLS_VERSION`` against THIS tenant's ``acknowledged_version``: a mismatch
(or a missing row) is per-tenant drift, so one tenant re-running setup clears
only its own banner.

This is deliberately a separate table from the global ``system_settings``
singleton: ``system_settings`` holds deployment-wide rows with NO tenant_key
(e.g. ``agent_silence_threshold_minutes``) and must not gain per-tenant state.
``tenant_skills_ack`` is keyed by ``tenant_key`` (CE column) and is therefore
fully removable with the rest of CE under the Deletion Test.
"""

from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.sql import func

from .base import Base


class TenantSkillsAck(Base):
    """The skills bundle version a tenant has acknowledged via /giljo_setup."""

    __tablename__ = "tenant_skills_ack"

    tenant_key = Column(String(255), primary_key=True)
    acknowledged_version = Column(String(128), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        # TSK-9076: backup watermark sweep — MAX(updated_at) per tenant. Indexed
        # uniformly with every other sweep source; the primary key on tenant_key
        # already answers this query for the current single-row-per-tenant shape,
        # so the composite simply keeps coverage uniform across the discovered set.
        Index("idx_tenant_skills_ack_tenant_updated", "tenant_key", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<TenantSkillsAck(tenant_key={self.tenant_key!r}, acknowledged_version={self.acknowledged_version!r})>"
