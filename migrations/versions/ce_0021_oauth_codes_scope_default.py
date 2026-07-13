# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Update oauth_authorization_codes.scope server default to canonical form.

Revision ID: ce_0021_oauth_codes_scope_default
Revises: ce_0020_oauth_refresh_tokens
Create Date: 2026-05-12

API-0021b switched the canonical OAuth scope string from the pre-split
``'mcp'`` literal to the RFC 6749 space-separated form
``'mcp:read mcp:write'``. The ORM column default was bumped at the model
layer (commit b895fabf7), but the underlying Postgres column default on
``oauth_authorization_codes.scope`` still resolves to ``'mcp'`` for rows
inserted without an explicit value. This bridges the schema-level default
to match the application contract surfaced by /authorize and /token.

Edition Scope: CE -- ``oauth_authorization_codes`` is a CE table defined
in ``src/giljo_mcp/models/oauth.py``; per CLAUDE.md the migration belongs
in the CE chain so ``startup.py``'s ``alembic upgrade head`` picks it up
on every install.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0021_oauth_codes_scope_default"
down_revision = "ce_0020_oauth_refresh_tokens"
branch_labels = None
depends_on = None


TABLE = "oauth_authorization_codes"
COLUMN = "scope"
NEW_DEFAULT = "mcp:read mcp:write"
OLD_DEFAULT = "mcp"


def upgrade() -> None:
    op.alter_column(
        TABLE,
        COLUMN,
        existing_type=sa.String(length=512),
        server_default=sa.text(f"'{NEW_DEFAULT}'"),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        TABLE,
        COLUMN,
        existing_type=sa.String(length=512),
        server_default=sa.text(f"'{OLD_DEFAULT}'"),
        existing_nullable=True,
    )
