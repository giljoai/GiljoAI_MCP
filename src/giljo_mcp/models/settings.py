"""
Settings model for GiljoAI MCP system settings.

Stores general, network, and database settings per tenant in JSONB format.
Handover 0506: Settings endpoints implementation.
"""

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class Settings(Base):
    """
    Settings model - JSONB storage for tenant-scoped system settings.

    Each tenant can have multiple setting categories (general, network, database).
    Settings are stored as flexible JSONB for easy schema evolution.

    Categories:
    - general: UI preferences, theme, locale
    - network: CORS, cookie domains, security settings
    - database: Connection settings, backup config
    """

    __tablename__ = "settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # 'general', 'network', 'database'
    settings_data = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tenant_key", "category", name="uq_settings_tenant_category"),
        Index("idx_settings_tenant", "tenant_key"),
        Index("idx_settings_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<Settings(id={self.id}, tenant_key={self.tenant_key}, category={self.category})>"
