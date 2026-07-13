# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Collapse vision_documents.storage_type to 'inline' only (BE-5115).

Revision ID: ce_0032_vision_docs_inline_only
Revises: ce_0031_user_split_name
Create Date: 2026-05-27

Eliminates the file-based vision-document storage path that broke every
Railway redeploy (ephemeral disk wipe between releases). The DB column
``vision_document`` has been populated unconditionally since Handover 0246b
(see ``vision_document_repository.py:107``); the on-disk file has been
pure redundancy. This migration is dead-code cleanup, not a data move.

Schema changes:
- Backfill any existing 'file' / 'hybrid' rows to 'inline'. ``vision_path``
  is cleared. Any row with NULL ``vision_document`` (expected zero rows
  given the unconditional populate at repo:107) is set to '' so the new
  CHECK does not reject the row.
- Drop the legacy ``ck_vision_doc_storage_consistency`` constraint
  (which allowed 'file', 'inline', or 'hybrid' shapes).
- Add ``ck_vision_doc_inline_only`` enforcing the single inline shape:
  storage_type='inline' AND vision_document IS NOT NULL AND vision_path IS NULL.
- Replace the storage_type enum CHECK so only 'inline' is accepted going
  forward.

Idempotency: every DDL operation existence-checks before mutating.
The CE installer reruns migrations on every boot.

Downgrade: NOT A FULL ROLLBACK -- schema only; any disk files lost during
inline adoption are permanent. Restores the legacy CHECK constraints but
does not (and cannot) repopulate ``vision_path`` from a vanished disk.

Edition Scope: Both -- the ``vision_documents`` table is a CE model
shared by SaaS via the CE chain.
"""

import logging

import sqlalchemy as sa
from alembic import op


logger = logging.getLogger(__name__)


revision = "ce_0032_vision_docs_inline_only"
down_revision = "ce_0031_user_split_name"
branch_labels = None
depends_on = None


TABLE = "vision_documents"
OLD_STORAGE_CHECK = "ck_vision_doc_storage_type"
OLD_CONSISTENCY_CHECK = "ck_vision_doc_storage_consistency"
NEW_INLINE_CHECK = "ck_vision_doc_inline_only"


def _has_check_constraint(conn, table: str, constraint: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = :table AND constraint_name = :name "
            "AND constraint_type = 'CHECK'"
        ),
        {"table": table, "name": constraint},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # Defensive backfill: any row where storage_type required vision_document
    # but it is NULL would be rejected by the new CHECK. Repo:107 has populated
    # vision_document on every insert since Handover 0246b, so this should
    # match zero rows -- we emit a WARNING per row caught.
    orphan_rows = conn.execute(
        sa.text("SELECT id FROM vision_documents WHERE storage_type IN ('file', 'hybrid') AND vision_document IS NULL")
    ).all()
    if orphan_rows:
        logger.warning(
            "BE-5115 backfill: %d vision_documents rows had NULL vision_document under "
            "storage_type IN ('file','hybrid'); resetting to '' so the inline CHECK accepts them. "
            "Affected ids: %s",
            len(orphan_rows),
            [r[0] for r in orphan_rows],
        )
        conn.execute(
            sa.text(
                "UPDATE vision_documents SET vision_document = '' "
                "WHERE storage_type IN ('file', 'hybrid') AND vision_document IS NULL"
            )
        )

    # Collapse all rows to the inline shape.
    conn.execute(
        sa.text(
            "UPDATE vision_documents "
            "SET storage_type = 'inline', vision_path = NULL "
            "WHERE storage_type IN ('file', 'hybrid')"
        )
    )

    # Drop the legacy storage consistency CHECK (allowed file / hybrid).
    if _has_check_constraint(conn, TABLE, OLD_CONSISTENCY_CHECK):
        op.drop_constraint(OLD_CONSISTENCY_CHECK, TABLE, type_="check")

    # Drop the legacy 3-value enum CHECK; we will re-add it scoped to 'inline'.
    if _has_check_constraint(conn, TABLE, OLD_STORAGE_CHECK):
        op.drop_constraint(OLD_STORAGE_CHECK, TABLE, type_="check")

    # Re-add the storage_type CHECK with the single-value enum.
    op.create_check_constraint(
        OLD_STORAGE_CHECK,
        TABLE,
        "storage_type = 'inline'",
    )

    # Add the new inline-only consistency CHECK.
    if not _has_check_constraint(conn, TABLE, NEW_INLINE_CHECK):
        op.create_check_constraint(
            NEW_INLINE_CHECK,
            TABLE,
            "storage_type = 'inline' AND vision_document IS NOT NULL AND vision_path IS NULL",
        )


def downgrade() -> None:
    """Restore the legacy storage CHECK constraints.

    NOT A FULL ROLLBACK -- schema only; any disk files lost during inline
    adoption are permanent. Existing rows remain inline because there is no
    surviving disk path to point them back at.
    """
    conn = op.get_bind()

    if _has_check_constraint(conn, TABLE, NEW_INLINE_CHECK):
        op.drop_constraint(NEW_INLINE_CHECK, TABLE, type_="check")

    if _has_check_constraint(conn, TABLE, OLD_STORAGE_CHECK):
        op.drop_constraint(OLD_STORAGE_CHECK, TABLE, type_="check")

    op.create_check_constraint(
        OLD_STORAGE_CHECK,
        TABLE,
        "storage_type IN ('file', 'inline', 'hybrid')",
    )

    if not _has_check_constraint(conn, TABLE, OLD_CONSISTENCY_CHECK):
        op.create_check_constraint(
            OLD_CONSISTENCY_CHECK,
            TABLE,
            "(storage_type = 'file' AND vision_path IS NOT NULL) OR "
            "(storage_type = 'inline' AND vision_document IS NOT NULL) OR "
            "(storage_type = 'hybrid' AND vision_path IS NOT NULL AND vision_document IS NOT NULL)",
        )
