# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [SaaS] SaaS Edition only -- excluded from Community Edition builds.

"""Password reset token model for SaaS email-based password recovery (SAAS-006).

Tokens are stored as SHA-256 hashes, never plaintext. Each token has a 1-hour
expiry window and is marked as used after successful password reset to prevent
replay attacks.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class PasswordResetToken(Base):
    """Password reset token for SaaS email-based recovery.

    Security model:
        - ``token_hash`` stores SHA-256 of the plaintext token (never stored raw)
        - Token expires after 1 hour (``expires_at``)
        - Token is single-use (``used_at`` set on consumption)
        - Rate limiting: max 3 tokens per email per hour (enforced at endpoint)

    Multi-tenant isolation: ``tenant_key`` is NOT NULL and indexed.
    """

    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email = Column(String(320), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_prt_tenant", "tenant_key"),
        Index("idx_prt_token_hash", "token_hash", unique=True),
        Index("idx_prt_user_id", "user_id"),
        Index("idx_prt_email_created", "email", "created_at"),
    )

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_used(self) -> bool:
        """Check if the token has been consumed."""
        return self.used_at is not None

    def __repr__(self) -> str:
        return f"<PasswordResetToken(id={self.id}, email={self.email}, expired={self.is_expired})>"
