# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
DRAFT — SEC-0005 Alembic migration: scope orchestrator prompt per-tenant.

This is a pre-implementation draft for Patrik's review. Before shipping:
1. Move to migrations/versions/ with a real revision id
2. Fill in `revision` and `down_revision` from current head
3. Wire into Alembic by renaming to <rev>_scope_orchestrator_prompt_per_tenant.py
4. Run against a dev DB with both CE (1 tenant) and multi-tenant fixtures to verify branches

Principle: log-before-delete. CE (1 tenant) preserves the admin's work by copying the
NULL row into their tenant. SaaS (2+ tenants) logs the NULL content to server logs
(recoverable by ops) but does NOT copy — that would leak tenant A's text into tenant B's
settings. Fresh install (0 tenants): log + delete NULL row.

Deviation flagged for review: Patrik's direction was "seed each tenant with a fresh
row containing the system default" in multi-tenant mode. This draft does NOT seed,
because seeding creates rows with `is_override=True` semantics even for users who
have never customized — collides with the UI's "Using default system prompt" vs
"Override saved" copy. If Patrik wants explicit seeded rows regardless, replace
the `if tenant_count >= 2` branch with the commented-out seed block.
"""

from __future__ import annotations

import json
import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision: str = "9254a70aef1d"
down_revision: Union[str, Sequence[str], None] = "create_product_agent_assignments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration.sec_0005")

ORCHESTRATOR_KEY = "system.orchestrator_prompt"


def upgrade() -> None:
    bind = op.get_bind()

    # Step 1: read the existing NULL-tenant row, if any.
    null_row = bind.execute(
        sa.text(
            "SELECT id, value, category, description, created_at, updated_at "
            "FROM configurations "
            "WHERE tenant_key IS NULL AND key = :key"
        ),
        {"key": ORCHESTRATOR_KEY},
    ).mappings().first()

    if null_row is None:
        logger.info("SEC-0005: no NULL-tenant orchestrator prompt row found; nothing to migrate.")
        return

    # Step 2: log content before any destructive op (recoverable from logs).
    value = null_row["value"] or {}
    content = value.get("content") if isinstance(value, dict) else None
    updated_by = value.get("updated_by") if isinstance(value, dict) else None
    updated_at_str = (value.get("updated_at") if isinstance(value, dict) else None) or null_row["updated_at"]

    logger.warning(
        "SEC-0005 migration: dropping obsolete NULL-tenant orchestrator prompt override. "
        "length=%d chars, updated_by=%s, updated_at=%s. Content captured below for recovery.\n---BEGIN---\n%s\n---END---",
        len(content) if content else 0,
        updated_by,
        updated_at_str,
        content or "",
    )

    # Step 3: count distinct tenants (CE vs SaaS branch).
    tenant_count = bind.execute(
        sa.text("SELECT COUNT(DISTINCT tenant_key) FROM users WHERE tenant_key IS NOT NULL")
    ).scalar() or 0

    # Step 4: branch.
    if tenant_count == 1 and content:
        # CE: copy the NULL row content to that tenant's row.
        ce_tenant_key = bind.execute(
            sa.text("SELECT DISTINCT tenant_key FROM users WHERE tenant_key IS NOT NULL LIMIT 1")
        ).scalar()

        if not ce_tenant_key:
            logger.error("SEC-0005: tenant_count==1 but could not resolve tenant_key. Aborting copy; will still delete NULL row.")
        else:
            # JSONB-safe insert: serialize with json.dumps, cast with CAST(:value AS JSONB).
            # Idempotent: ON CONFLICT preserves any existing tenant row (don't overwrite).
            payload = json.dumps({
                "content": content,
                "updated_by": updated_by,
                "updated_at": updated_at_str if isinstance(updated_at_str, str) else (
                    updated_at_str.isoformat() if updated_at_str else None
                ),
            })
            bind.execute(
                sa.text(
                    "INSERT INTO configurations "
                    "(id, tenant_key, project_id, key, value, category, description, created_at, updated_at) "
                    "VALUES (gen_random_uuid()::text, :tenant_key, NULL, :key, CAST(:value AS JSONB), 'system', "
                    "'Administrator override for orchestrator prompt (migrated from global row by SEC-0005)', "
                    "NOW(), NOW()) "
                    "ON CONFLICT (tenant_key, key) DO NOTHING"
                ),
                {"tenant_key": ce_tenant_key, "key": ORCHESTRATOR_KEY, "value": payload},
            )
            logger.info("SEC-0005: copied NULL-tenant override to CE tenant %s", ce_tenant_key)

    elif tenant_count >= 2:
        # SaaS/demo: do NOT copy. Service's default-fallback handles un-seeded tenants.
        # (Deviation flagged in module docstring — seed block below is intentionally disabled.)
        #
        # If Patrik approves seeding, uncomment:
        #
        # tenants = bind.execute(
        #     sa.text("SELECT DISTINCT tenant_key FROM users WHERE tenant_key IS NOT NULL")
        # ).scalars().all()
        # default_value = {"content": "<DEFAULT SYSTEM PROMPT>", "updated_by": "system_migration", "updated_at": None}
        # for tk in tenants:
        #     bind.execute(
        #         sa.text("INSERT INTO configurations (...) VALUES (...) ON CONFLICT (tenant_key, key) DO NOTHING"),
        #         {"tenant_key": tk, "key": ORCHESTRATOR_KEY, "value": json.dumps(default_value)},
        #     )
        logger.info("SEC-0005: SaaS mode (%d tenants). NULL row content logged; no seeding per current safer variant.", tenant_count)

    else:
        # tenant_count == 0: fresh install, nothing to preserve.
        logger.info("SEC-0005: tenant_count==0; nothing to preserve, proceeding to delete NULL row.")

    # Step 5: drop the NULL row last (ensures logging happens even if copy fails).
    bind.execute(
        sa.text("DELETE FROM configurations WHERE tenant_key IS NULL AND key = :key"),
        {"key": ORCHESTRATOR_KEY},
    )
    logger.info("SEC-0005: NULL-tenant orchestrator prompt row deleted.")


def downgrade() -> None:
    # Intentional no-op: we logged the content to server logs before deletion.
    # To restore, ops team re-runs the admin UI save with the logged content.
    # Automatic downgrade would re-introduce the cross-tenant leak — not worth the risk.
    logger.warning(
        "SEC-0005 downgrade: no-op. NULL-tenant row was logged to server output before deletion; "
        "restore manually from logs if needed."
    )
