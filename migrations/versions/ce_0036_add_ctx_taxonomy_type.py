# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Seed CTX taxonomy type for every existing tenant (BE-5122).

Revision ID: ce_0036_add_ctx_taxonomy_type
Revises: ce_0035_drop_vision_document_summaries
Create Date: 2026-05-28

BE-5122 registers a new taxonomy abbreviation ``CTX`` (Context Update) used
by the Context Update Feature. The runtime seed list lives in
``taxonomy_ops.DEFAULT_TAXONOMY_TYPES`` and is only applied to brand-new
tenants by ``ensure_default_types_seeded``. Existing tenants whose taxonomy
list was seeded before BE-5122 need this back-fill so the validator in
``TaxonomyService`` accepts ``project_type='CTX'`` immediately after upgrade.

Idempotency: single ``INSERT ... ON CONFLICT (tenant_key, abbreviation)
DO NOTHING`` over ``SELECT DISTINCT tenant_key FROM taxonomy_types``. Re-running
the migration is a no-op. CE installer reruns migrations on every boot.

Downgrade: ``DELETE FROM taxonomy_types WHERE abbreviation = 'CTX'`` guarded
by a NOT EXISTS clause on referencing projects so the downgrade is a no-op
when any CTX project still exists. Without the guard, dropping the row would
orphan ``projects.project_type_id`` on every live CTX project.

Edition Scope: CE -- ``taxonomy_types`` is a CE model used by both editions
via the CE migration chain.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0036_add_ctx_taxonomy_type"
down_revision = "ce_0035_drop_vision_document_summaries"
branch_labels = None
depends_on = None


CTX_ABBREVIATION = "CTX"
CTX_LABEL = "Context Update"
CTX_COLOR = "#9E9E9E"
CTX_SORT_ORDER = 8


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO taxonomy_types (
                id, tenant_key, abbreviation, label, color, sort_order,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid()::text,
                t.tenant_key,
                :abbr,
                :label,
                :color,
                :sort_order,
                NOW(),
                NOW()
            FROM (SELECT DISTINCT tenant_key FROM taxonomy_types) AS t
            ON CONFLICT (tenant_key, abbreviation) DO NOTHING
            """
        ).bindparams(
            abbr=CTX_ABBREVIATION,
            label=CTX_LABEL,
            color=CTX_COLOR,
            sort_order=CTX_SORT_ORDER,
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM taxonomy_types
            WHERE abbreviation = :abbr
              AND NOT EXISTS (
                  SELECT 1 FROM projects
                  WHERE projects.project_type_id = taxonomy_types.id
              )
            """
        ).bindparams(abbr=CTX_ABBREVIATION)
    )
