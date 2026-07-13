# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6082: full-text-search GIN index on product_memory_entries (360-Memory browser).

Revision ID: ce_0052_pme_fts_be6082
Revises: ce_0051_perf_indexes_be6073
Create Date: 2026-06-15

A single EXPRESSION GIN index that backs server-side full-text search over a
product's 360-memory entries (the deferred backend half of the FE-5042 memory
browser; client-side JS filtering does not scale past a few thousand entries).

DESIGN — expression index, NO new column. The index is built over

    to_tsvector('english',
        coalesce(summary, '') || ' ' ||
        coalesce(project_name, '') || ' ' ||
        coalesce(key_outcomes::text, '') || ' ' ||
        coalesce(decisions_made::text, '') || ' ' ||
        coalesce(tags::text, ''))

and the repository's search query filters on the IDENTICAL expression
(``@@ plainto_tsquery('english', :q)``) so the planner uses this index. Adding
no column means NO model change and therefore NO schema-drift gate risk
(BE-3002a): a stored generated tsvector column would have to be mirrored on the
ProductMemoryEntry ORM model or the migrated DB would carry a column the model
lacks. The expression-index approach sidesteps that entirely.

The fields mirror the existing client-side ``_matchesSearch`` haystack in
``memoryStore.js`` (summary, project_name, key_outcomes, decisions_made, tags)
so server-side and client-side search return parity results.

JSONB note: ``key_outcomes`` / ``decisions_made`` / ``tags`` are JSONB columns
(NOT PostgreSQL ``text[]``), so the ``array_to_string`` sketch does not apply —
they are cast with ``::text``. ``jsonb`` output (``jsonb_out``) is IMMUTABLE and
the 2-arg ``to_tsvector(regconfig, text)`` form is IMMUTABLE, so the whole
expression is immutable and valid as an index expression.

Idempotent: ``CREATE INDEX IF NOT EXISTS`` (plain, NOT CONCURRENTLY so it runs
inside Alembic's transaction). The CE installer reruns ``alembic upgrade head``
on every boot; a second run is a clean no-op. Reversible: downgrade drops the
index by name with ``IF EXISTS``. Mirrors the ce_0045 / ce_0046 / ce_0051
idempotent-index precedent.

Edition Scope: Both. product_memory_entries is a CE core table; this migration
lives in migrations/versions/ (NOT saas_versions/).
"""

from alembic import op


revision = "ce_0052_pme_fts_be6082"
down_revision = "ce_0051_perf_indexes_be6073"
branch_labels = None
depends_on = None


# The tsvector document expression. MUST stay byte-identical to
# ``_FTS_DOCUMENT_SQL`` in
# ``src/giljo_mcp/repositories/product_memory_repository.py`` so the runtime
# search query's expression matches this index and the planner uses it.
_FTS_DOCUMENT = (
    "to_tsvector('english', "
    "coalesce(summary, '') || ' ' || "
    "coalesce(project_name, '') || ' ' || "
    "coalesce(key_outcomes::text, '') || ' ' || "
    "coalesce(decisions_made::text, '') || ' ' || "
    "coalesce(tags::text, ''))"
)


def upgrade() -> None:
    op.execute(f"CREATE INDEX IF NOT EXISTS idx_pme_fts ON product_memory_entries USING gin ({_FTS_DOCUMENT})")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_pme_fts")
