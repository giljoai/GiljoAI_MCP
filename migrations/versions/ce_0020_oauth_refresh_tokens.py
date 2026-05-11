# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add oauth_refresh_tokens table (API-0021e Phase 2).

Revision ID: ce_0020_oauth_refresh_tokens
Revises: ce_0019_oauth_codes_resource
Create Date: 2026-05-10

API-0021e Phase 2 introduces the OAuth 2.1 refresh-token grant with rotation
+ family-level reuse detection. The model lives in CE
(``src/giljo_mcp/models/oauth.py``) so per CLAUDE.md migration-chain rule the
table is created in the CE chain — ``startup.py`` only runs ``alembic upgrade
head`` on the CE chain, and confidential SaaS clients hold the only
refresh-token-issuing path today (claude.ai DCR). Keeping the table in CE
also means the OAuth code paths stay self-consistent for tenants that never
register a confidential client (they simply have no rows).

Schema mirrors the security-critical contract documented in the model:
  - ``token_hash`` (sha256 hex, 64 chars) is the unique lookup key; raw
    refresh tokens are never persisted.
  - ``family_id`` groups every refresh token derived from the same initial
    authorization-code grant. Reuse of a revoked/already-rotated token
    revokes the entire family (RFC 6749 §10.4 + §6 best practice).
  - ``tenant_key`` is NOT NULL + indexed (CLAUDE.md tenant-isolation).

Idempotent: table create + every index guarded by information_schema lookup;
down-migration drops the table cleanly.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "ce_0020_oauth_refresh_tokens"
down_revision = "ce_0019_oauth_codes_resource"
branch_labels = None
depends_on = None


TABLE = "oauth_refresh_tokens"


def _table_exists(conn, name: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"),
            {"name": name},
        ).scalar()
    )


def _index_exists(conn, name: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT EXISTS (SELECT FROM pg_indexes WHERE indexname = :name)"),
            {"name": name},
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, TABLE):
        op.create_table(
            TABLE,
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
            sa.Column("family_id", postgresql.UUID(as_uuid=False), nullable=False),
            # client_id width matches oauth_clients.client_id (UUID stringified
            # at the application layer) and oauth_authorization_codes.client_id
            # (String(64)); keep VARCHAR(64) so the FK-less wide column accepts
            # both shapes during the API-0021e transition window.
            sa.Column("client_id", sa.String(length=64), nullable=False),
            sa.Column("tenant_key", sa.String(length=64), nullable=False),
            # users.id is String(36) (UUID stringified, see models.auth.User).
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("scope", sa.Text(), nullable=True),
            sa.Column("aud", sa.Text(), nullable=False),
            sa.Column(
                "issued_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "revoked",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    if not _index_exists(conn, "ix_oauth_refresh_tokens_family_id"):
        op.create_index("ix_oauth_refresh_tokens_family_id", TABLE, ["family_id"])

    if not _index_exists(conn, "ix_oauth_refresh_tokens_tenant_key"):
        op.create_index("ix_oauth_refresh_tokens_tenant_key", TABLE, ["tenant_key"])


def downgrade() -> None:
    conn = op.get_bind()

    if _index_exists(conn, "ix_oauth_refresh_tokens_tenant_key"):
        op.drop_index("ix_oauth_refresh_tokens_tenant_key", table_name=TABLE)

    if _index_exists(conn, "ix_oauth_refresh_tokens_family_id"):
        op.drop_index("ix_oauth_refresh_tokens_family_id", table_name=TABLE)

    if _table_exists(conn, TABLE):
        op.drop_table(TABLE)
