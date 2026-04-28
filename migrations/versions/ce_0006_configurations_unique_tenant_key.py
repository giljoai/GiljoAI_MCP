# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available.

"""Configurations: drop NULL-tenant orchestrator prompt orphans, add UNIQUE(tenant_key, key).

Revision ID: ce_0006_configurations_unique_tenant_key
Revises: ce_0005_drop_users_execution_mode
Create Date: 2026-04-28

HO1027 (three-layer orchestrator identity refactor) — DB hardening:

1. Delete orphan rows where ``tenant_key IS NULL`` for the
   ``system.orchestrator_prompt`` key. Pre-HO1027, the upsert helper used a
   select-then-insert pattern that, under a race or with a tenantless caller,
   could persist a NULL-tenant override row. The runtime fetch always filters
   by ``tenant_key = :tenant``, so these rows are unreachable orphans that
   would later violate the unique constraint we are about to add.

2. Add ``UNIQUE(tenant_key, key)`` on ``configurations``. The ORM model
   already declares this constraint (``uq_config_tenant_key``); some legacy
   databases were created before it landed and are missing the index. This
   migration brings the schema into agreement with the model and converts
   the upsert path to ``INSERT ... ON CONFLICT (tenant_key, key) DO UPDATE``
   in the same change set (see ``system_prompts/service.py``).

Idempotent:
- Step 1 deletes by predicate (no-op if no orphans).
- Step 2 inspects ``information_schema.table_constraints`` before creating.

Reversible: downgrade drops the constraint only. The orphan deletion is
intentionally NOT reversed (the rows were unreachable garbage).
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0006_configurations_unique_tenant_key"
down_revision = "ce_0005_drop_users_execution_mode"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = "uq_config_tenant_key"
TABLE_NAME = "configurations"
ORCHESTRATOR_PROMPT_KEY = "system.orchestrator_prompt"


def _has_constraint(conn, table: str, constraint: str) -> bool:
    """Idempotency guard -- check named constraint via information_schema."""
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = :table AND constraint_name = :constraint"
        ),
        {"table": table, "constraint": constraint},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # Step 1: drop orphan NULL-tenant orchestrator prompt rows (pre-constraint cleanup).
    conn.execute(
        sa.text("DELETE FROM configurations WHERE tenant_key IS NULL AND key = :key"),
        {"key": ORCHESTRATOR_PROMPT_KEY},
    )

    # Step 2: add UNIQUE(tenant_key, key) if not already present.
    if not _has_constraint(conn, TABLE_NAME, CONSTRAINT_NAME):
        op.create_unique_constraint(
            CONSTRAINT_NAME,
            TABLE_NAME,
            ["tenant_key", "key"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_constraint(conn, TABLE_NAME, CONSTRAINT_NAME):
        op.drop_constraint(CONSTRAINT_NAME, TABLE_NAME, type_="unique")
