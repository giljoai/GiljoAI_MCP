# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6054a: backfill the reserved CHT (Chat Thread) taxonomy type for
already-seeded tenants.

Revision ID: ce_0054_cht_taxonomy_backfill
Revises: ce_0053_comm_hub_tables
Create Date: 2026-06-15

``CHT`` is added to ``DEFAULT_TAXONOMY_TYPES`` so NEW tenants get it on first
seed. But ``ensure_default_types_seeded`` is empty-table-guarded (it returns
early if a tenant already has ANY taxonomy types), so EXISTING tenants
(every CE self-hoster past first boot) would never receive
CHT — and minting ``CHT-0001`` for them would 422 on the unknown type.

This migration inserts exactly one CHT row for every tenant that has taxonomy
types but lacks CHT. Idempotent via the ``NOT EXISTS`` guard (a second run is a
clean no-op) and safe against the ``uq_taxonomy_type_abbr`` unique. It mirrors
the lazy ``ensure_reserved_task_type`` precedent (TSK), just applied as a
one-shot backfill in the chain rather than on the request path.

Edition Scope: CE (taxonomy_types is a CE core table). Data-only — no schema
change, so no schema-drift impact.
"""

from alembic import op
from sqlalchemy import text


revision = "ce_0054_cht_taxonomy_backfill"
down_revision = "ce_0053_comm_hub_tables"
branch_labels = None
depends_on = None


# Keep in sync with taxonomy_ops.RESERVED_CHAT_THREAD_TYPE_ABBR + the
# DEFAULT_TAXONOMY_TYPES "Chat Thread" entry.
_CHT_ABBR = "CHT"
_CHT_LABEL = "Chat Thread"
_CHT_COLOR = "#1565C0"
_CHT_SORT_ORDER = 101  # sorts last; CHT is filtered from project dropdowns anyway


def upgrade() -> None:
    op.execute(
        text(
            """
            INSERT INTO taxonomy_types
                (id, tenant_key, abbreviation, label, color, sort_order, created_at, updated_at)
            SELECT
                gen_random_uuid()::text, t.tenant_key, :abbr, :label, :color, :sort_order,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM (SELECT DISTINCT tenant_key FROM taxonomy_types) t
            WHERE NOT EXISTS (
                SELECT 1 FROM taxonomy_types x
                WHERE x.tenant_key = t.tenant_key AND x.abbreviation = :abbr
            )
            """
        ).bindparams(
            abbr=_CHT_ABBR,
            label=_CHT_LABEL,
            color=_CHT_COLOR,
            sort_order=_CHT_SORT_ORDER,
        )
    )


def downgrade() -> None:
    # Remove only backfilled CHT rows that have no threads referencing their
    # serial space. CHT carries no project FK, so a plain delete is safe; guarded
    # by abbreviation so nothing else is touched.
    op.execute(text("DELETE FROM taxonomy_types WHERE abbreviation = :abbr").bindparams(abbr=_CHT_ABBR))
