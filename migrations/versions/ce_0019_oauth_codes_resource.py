# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add resource column to oauth_authorization_codes (API-0021d Phase 2).

Revision ID: ce_0019_oauth_codes_resource
Revises: ce_0018_user_approvals
Create Date: 2026-05-09

API-0021d Phase 2 introduces RFC 8707 resource indicator binding for OAuth
2.1 token issuance. The resource value is asserted by the client at the
/authorize endpoint, persisted onto the auth-code record, validated at the
/token endpoint, and baked into the JWT ``aud`` claim. Nullable for
backwards compatibility with codes minted before API-0021d (legacy aud-less
flow stays valid for one release window).

Edition Scope: CE -- the OAuth auth-code model lives in CE
(``src/giljo_mcp/models/oauth.py``); per CLAUDE.md, columns on CE models
must go in the CE migration chain so ``startup.py``'s ``alembic upgrade head``
on the CE chain creates them on every deployment.

Idempotent: column add guarded by information_schema lookup; down-migration
drops the column cleanly.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0019_oauth_codes_resource"
down_revision = "ce_0018_user_approvals"
branch_labels = None
depends_on = None


TABLE = "oauth_authorization_codes"
COLUMN = "resource"


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, TABLE, COLUMN):
        op.add_column(
            TABLE,
            sa.Column(COLUMN, sa.String(length=2048), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_column(conn, TABLE, COLUMN):
        op.drop_column(TABLE, COLUMN)
