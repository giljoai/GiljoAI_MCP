# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9085b: durable ``projects.ever_launched_at`` set-once signal that
survives restage, replacing the shipped BE-9085 detector's
accept-and-note restage false-positive with an actual fix.

Revision ID: ce_0075_projects_ever_launched_at
Revises: ce_0074_messages_thread_created_index
Create Date: 2026-07-08

``implementation_launched_at`` is cleared to NULL by ``restage`` as a
clean-slate reset for the next implementation cycle (see
``project_staging_service.py``). That made the BE-9085 pre-launch-
workproduct closeout detector unable to tell "never launched" apart from
"launched, then restaged" -- both look like NULL at closeout time. This
adds ``ever_launched_at``: stamped once at launch, left untouched by
restage, and cleared only by ``reset_to_prestage`` (the discard-everything
rewind). The detector now fires on ``ever_launched_at IS NULL`` instead.

Backfill: marks currently-launched projects (``implementation_launched_at``
already set) as having ever been launched. Limitation (accepted): a
project that was launched, then restaged, BEFORE this migration ran
already has ``implementation_launched_at`` NULL at backfill time, so it is
NOT backfilled and could false-positive ONCE on its next closeout. Going
forward (post-migration launches) the signal is durable and correct.

Idempotent: existence-guarded ADD COLUMN + a backfill UPDATE that is
naturally idempotent (WHERE ... AND ever_launched_at IS NULL), so the CE
installer's every-boot `alembic upgrade head` re-run is a clean no-op.

Baseline: paired with a parity edit to baseline_v37_unified.py so fresh
installs get the column directly (this incremental's guard makes it a
no-op there).

Edition Scope: Both. projects is a CE-model table; this migration lives in
migrations/versions/ (never saas_versions/).
"""

from alembic import op
from sqlalchemy import inspect


revision = "ce_0075_projects_ever_launched_at"
down_revision = "ce_0074_messages_thread_created_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns("projects")]
    if "ever_launched_at" not in columns:
        op.execute("ALTER TABLE projects ADD COLUMN ever_launched_at TIMESTAMPTZ NULL")
    op.execute(
        "UPDATE projects SET ever_launched_at = implementation_launched_at "
        "WHERE implementation_launched_at IS NOT NULL AND ever_launched_at IS NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE projects DROP COLUMN IF EXISTS ever_launched_at")
