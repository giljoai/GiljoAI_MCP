# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""drop orphan tables: discovery_config, git_configs, optimization_rules, optimization_metrics

Sprint 002d: Remove 4 orphan DB tables whose model classes have been deleted.
These tables were created in baseline_v36_unified but never used by any service,
repository, or endpoint.

Revision ID: a3c7e1f9d024
Revises: 9f1f46a46029
Create Date: 2026-04-17 19:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3c7e1f9d024"
down_revision: str | None = "9f1f46a46029"
branch_labels: str | None = None
depends_on: str | None = None

_TABLES = [
    "discovery_config",
    "git_configs",
    "optimization_rules",
    "optimization_metrics",
]


def upgrade() -> None:
    for table in _TABLES:
        # Idempotency guard: only drop if the table exists
        op.execute(
            f"DROP TABLE IF EXISTS {table} CASCADE"
        )


def downgrade() -> None:
    # Tables were orphaned and unused; no downgrade needed.
    # If needed, restore from baseline_v36_unified.py manually.
    pass
