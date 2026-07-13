# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Update vision_documents.is_summarized DB comment to post-Sumy framing (BE-5119 Phase 5).

Revision ID: ce_0034_update_is_summarized_comment
Revises: ce_0033_vision_analysis_complete
Create Date: 2026-05-27

BE-5117 stripped Sumy/LSA from the product. The baseline's `COMMENT ON COLUMN`
on `vision_documents.is_summarized` (baseline_v37_unified.py:726, inside the
vision_documents create_table block) still reads "Has document been summarized
using LSA algorithm", which surfaces as stale schema metadata to anyone
inspecting their DB. This migration overwrites the comment to reflect the
current meaning: the flag indicates that the vision document now has
agent-written summaries in `vision_document_summaries`.

Idempotency: `COMMENT ON COLUMN` is idempotent by nature — it overwrites.

Downgrade: restores the original baseline text for migration-discipline
correctness.

Edition Scope: Both -- the ``vision_documents`` table is a CE model shared by
SaaS via the CE chain.
"""

from alembic import op


revision = "ce_0034_update_is_summarized_comment"
down_revision = "ce_0033_vision_analysis_complete"
branch_labels = None
depends_on = None


NEW_COMMENT = (
    "Legacy: pre-BE-5117 Sumy-based summary flag. Now indicates: vision "
    "document has a summary in vision_document_summaries (AI-tool-generated)."
)
OLD_COMMENT = "Has document been summarized using LSA algorithm"


def upgrade() -> None:
    op.execute(f"COMMENT ON COLUMN vision_documents.is_summarized IS '{NEW_COMMENT}'")


def downgrade() -> None:
    op.execute(f"COMMENT ON COLUMN vision_documents.is_summarized IS '{OLD_COMMENT}'")
