# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add oauth_revoked_tokens table (API-0022 RFC 7009 revocation).

Revision ID: ce_0022_oauth_revoked_tokens
Revises: ce_0021_oauth_codes_scope_default
Create Date: 2026-05-12

API-0022 introduces RFC 7009 OAuth Token Revocation. The /oauth/revoke
endpoint persists a row here keyed by JWT ``jti`` (added to all access
tokens by API-0022). The /mcp Bearer middleware looks up the presented
token's jti against this table on every request (with a short-lived
in-process TTL cache in front) and rejects revoked tokens with 401.

Edition Scope: CE -- the OAuth surface lives in CE (api/endpoints/oauth.py);
per CLAUDE.md migration-chain rule the table must go in the CE chain so
``startup.py``'s ``alembic upgrade head`` creates it on every install.

Idempotent: create_table + index guarded by information_schema lookup.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0022_oauth_revoked_tokens"
down_revision = "ce_0021_oauth_codes_scope_default"
branch_labels = None
depends_on = None


TABLE = "oauth_revoked_tokens"
INDEX = "ix_oauth_revoked_tokens_tenant_key"


def _has_table(conn, table: str) -> bool:
    return (
        conn.execute(
            sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
            {"t": table},
        ).first()
        is not None
    )


def _has_index(conn, index: str) -> bool:
    return (
        conn.execute(
            sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :i"),
            {"i": index},
        ).first()
        is not None
    )


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, TABLE):
        op.create_table(
            TABLE,
            sa.Column("jti", sa.String(length=64), nullable=False),
            sa.Column("token_type", sa.String(length=32), nullable=False),
            sa.Column("tenant_key", sa.String(length=64), nullable=False),
            sa.Column(
                "revoked_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("jti"),
        )

    if not _has_index(conn, INDEX):
        op.create_index(INDEX, TABLE, ["tenant_key"])


def downgrade() -> None:
    conn = op.get_bind()

    if _has_index(conn, INDEX):
        op.drop_index(INDEX, table_name=TABLE)

    if _has_table(conn, TABLE):
        op.drop_table(TABLE)
