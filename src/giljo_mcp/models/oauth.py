"""
OAuth 2.1 authorization models.

This module contains models for OAuth 2.1 Authorization Code flow with PKCE:
- OAuthAuthorizationCode: Short-lived authorization codes exchanged for tokens
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class OAuthAuthorizationCode(Base):
    """
    OAuth 2.1 Authorization Code with PKCE support.

    Stores short-lived authorization codes issued during the OAuth authorization
    flow. Codes are single-use, expire after 10 minutes, and require PKCE S256
    challenge verification at the token exchange step.

    Multi-tenant isolation: Every query MUST filter by tenant_key.
    """

    __tablename__ = "oauth_authorization_codes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(128), unique=True, nullable=False, index=True)
    client_id = Column(String(64), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_key = Column(String(64), nullable=False, index=True)
    redirect_uri = Column(String(2048), nullable=False)
    code_challenge = Column(String(128), nullable=False)
    code_challenge_method = Column(String(10), default="S256")
    scope = Column(String(512), default="mcp")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_oauth_code_tenant", "tenant_key"),
        Index("idx_oauth_code_user", "user_id"),
        Index("idx_oauth_code_expires", "expires_at"),
        Index("idx_oauth_code_lookup", "code", "tenant_key"),
    )

    def __repr__(self) -> str:
        return f"<OAuthAuthorizationCode(id={self.id}, client_id={self.client_id}, tenant_key={self.tenant_key})>"
