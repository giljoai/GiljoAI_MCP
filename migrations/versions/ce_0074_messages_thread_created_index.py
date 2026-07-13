# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9061: composite (thread_id, created_at) index on messages for the hot
thread-timeline read; drop the now-redundant single-column idx_message_thread.

Revision ID: ce_0074_messages_thread_created_index
Revises: ce_0073_users_password_nudge_dismissed
Create Date: 2026-07-06

The hottest Hub read is get_thread_messages: WHERE tenant_key = ? AND
thread_id = ? ORDER BY created_at (loop_directive polling re-reads a thread each
tick). The only supporting index was idx_message_thread (thread_id) — it seeks
the thread's rows but leaves created_at unordered, so a long thread pays a sort
every poll. This adds idx_messages_thread_created (thread_id, created_at), which
serves the filter AND the ordering, and fully leftmost-covers idx_message_thread
(thread_id) — so that narrow index is dropped in the same change to avoid a
redundant duplicate (the pattern established by ce_0069's index dedup).

Idempotent: CREATE INDEX IF NOT EXISTS + DROP INDEX IF EXISTS, so the CE
installer's every-boot `alembic upgrade head` re-run is a clean no-op. Reversible:
downgrade recreates idx_message_thread and drops the composite.

Baseline: baseline_v37_unified.py never created idx_message_thread (it came from
the BE-6054a incremental), so both a fresh install (baseline -> BE-6054a ->
here) and an existing DB converge to the identical shape via this migration —
no baseline edit is needed.

Edition Scope: Both. messages is a CE-model table; this migration lives in
migrations/versions/ (never saas_versions/).
"""

from alembic import op


revision = "ce_0074_messages_thread_created_index"
down_revision = "ce_0073_users_password_nudge_dismissed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_thread_created ON messages (thread_id, created_at)")
    # Superseded by the composite above (leftmost-covered) — drop the duplicate.
    op.execute("DROP INDEX IF EXISTS idx_message_thread")


def downgrade() -> None:
    op.execute("CREATE INDEX IF NOT EXISTS idx_message_thread ON messages (thread_id)")
    op.execute("DROP INDEX IF EXISTS idx_messages_thread_created")
