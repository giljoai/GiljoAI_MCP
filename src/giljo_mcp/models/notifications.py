# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Notification model — DB-backed user/tenant notifications.

IMP-5037a Phase 1: the persistent backing store for the dashboard notification
bell. Replaces the prior client-only/ephemeral notification surfaces with a
tenant-scoped, per-user (or tenant-broadcast) row that survives reloads and
supports read/dismiss/resolve lifecycle and emit-time de-duplication.

Lifecycle timestamps:
- ``read_at``      — user has seen it (clears the unread badge for that row)
- ``dismissed_at`` — user has hidden it from the list
- ``resolved_at``  — the underlying condition no longer applies (auto-clear);
  also the partition key for the de-dupe partial unique index, so a resolved
  notification frees its ``dedupe_key`` for a future re-emit.

De-dupe: a UNIQUE partial index on ``(tenant_key, dedupe_key) WHERE
resolved_at IS NULL`` guarantees at most one *open* notification per natural
key. NotificationService.create relies on this at the write boundary.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


VALID_NOTIFICATION_SEVERITIES = frozenset(
    {
        "info",
        "success",
        "warning",
        "error",
        "critical",
    }
)


# Where a notification renders: the bell dropdown, a page banner, or both.
# IMP-5037b consolidates the legacy standalone banners onto this column so a
# single notification row is the authority for both surfaces.
VALID_NOTIFICATION_SURFACES = frozenset(
    {
        "bell",
        "banner",
        "both",
    }
)


class Notification(Base):
    """Tenant-scoped, optionally user-scoped notification record.

    Multi-tenant isolation: every query MUST filter by ``tenant_key``.
    ``user_id`` NULL means the notification is tenant-scoped (visible to all
    users in the tenant); a non-NULL ``user_id`` scopes it to one user.
    """

    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False)

    # NULL = tenant-scoped (all users in tenant); non-NULL = single-user-scoped.
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)

    # Routing/discriminator: e.g. "api_key.expiring_soon". Keys the payload validator.
    type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)

    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)

    # Structured render/route data, validated by jsonb_validators registry keyed by ``type``.
    payload = Column(JSONB, nullable=False, default=dict)

    # Natural key for emit-time de-dupe (see partial unique index below).
    dedupe_key = Column(String(255), nullable=False)

    # IMP-5037b banner consolidation
    # Render surface: 'bell' | 'banner' | 'both' (CHECK-constrained in DB).
    surface = Column(Text, nullable=False, server_default=text("'bell'"))
    # When non-NULL, only users holding this role see the row. Server-enforced
    # in NotificationService.list_for_user (NOT a frontend-only filter).
    role_filter = Column(Text, nullable=True)
    # Optional call-to-action: a label + a NAMED Vue route string (not a URL).
    cta_label = Column(Text, nullable=True)
    cta_route = Column(Text, nullable=True)
    # Whether the user may dismiss the row (e.g. lapsed-subscription banners
    # are non-dismissible until the underlying condition resolves).
    dismissible = Column(Boolean, nullable=False, server_default=text("true"))

    # Lifecycle timestamps
    read_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "surface IN ('bell', 'banner', 'both')",
            name="ck_notifications_surface",
        ),
        # BE-8000c: idx_notifications_tenant_key dropped — leftmost-covered by
        # idx_notifications_tenant_user_created (tenant_key, user_id, created_at DESC).
        Index("idx_notifications_dedupe_key", "dedupe_key"),
        # Emit-time de-dupe: at most one OPEN notification per (tenant, dedupe_key).
        Index(
            "uq_notifications_tenant_dedupe_open",
            "tenant_key",
            "dedupe_key",
            unique=True,
            postgresql_where=text("resolved_at IS NULL"),
        ),
        # List endpoint: newest-first per (tenant, user).
        Index(
            "idx_notifications_tenant_user_created",
            "tenant_key",
            "user_id",
            text("created_at DESC"),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, type={self.type}, severity={self.severity}, "
            f"user_id={self.user_id}, resolved={self.resolved_at is not None})>"
        )
