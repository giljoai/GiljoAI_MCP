# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""System-scoped settings (NOT tenant-scoped).

The system_settings table holds singleton key/value rows that describe
the deployment as a whole. The first such row is skills_version_announced,
which records the SKILLS_VERSION the server considers current for the
purpose of the slash-command bundle drift banner.

Tenant isolation does NOT apply here: there is exactly one row per key
across the entire database.
"""

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.sql import func

from .base import Base


class SystemSetting(Base):
    """System-wide singleton key/value setting (no tenant_key)."""

    __tablename__ = "system_settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<SystemSetting(key={self.key!r})>"
