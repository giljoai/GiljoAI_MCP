# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""SaaS migration chain baseline

Revision ID: saas_baseline_v1
Revises:
Create Date: 2026-04-13

Empty baseline that establishes the SaaS migration chain head.
SaaS-only table migrations will depend on this revision.
"""

revision = "saas_baseline_v1"
down_revision = None
branch_labels = ("saas",)
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
