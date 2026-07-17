# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Drop orphan SetupState columns (audit cluster 3 / mission batch 3).

Revision ID: ce_0012_drop_setup_state_orphan_cols
Revises: ce_0011_drop_dead_tables
Create Date: 2026-05-05

The SetupState table was designed to track installer telemetry per tenant,
but most of those fields were never wired. Only `database_initialized`,
`database_initialized_at`, `setup_version`, `python_version`, `first_admin_created`,
`first_admin_created_at`, and `validation_failures` carry product behavior.
The 11 columns dropped here are pure define-only -- defaulted in
state_manager._get_default_state but never persisted by any caller.

Reference: internal design notes sec 3.a /
analyzer matrix row 3.

Drops (in order: indexes first, then constraints, then columns):
- Indexes: idx_setup_mode, idx_setup_features_gin, idx_setup_tools_gin
- Constraints: ck_database_version_format, ck_install_mode_values
- Columns: database_version, node_version, features_configured, tools_enabled,
  config_snapshot, validation_passed, validation_warnings, last_validation_at,
  installer_version, install_mode, install_path

Idempotent. Reversible (downgrade restores columns + GIN indexes + check
constraints; row data is not preserved).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision = "ce_0012_drop_setup_state_orphan_cols"
down_revision = "ce_0011_drop_dead_tables"
branch_labels = None
depends_on = None


TABLE = "setup_state"
COLUMNS = (
    "database_version",
    "node_version",
    "features_configured",
    "tools_enabled",
    "config_snapshot",
    "validation_passed",
    "validation_warnings",
    "last_validation_at",
    "installer_version",
    "install_mode",
    "install_path",
)
INDEXES = ("idx_setup_mode", "idx_setup_features_gin", "idx_setup_tools_gin")
CONSTRAINTS = ("ck_database_version_format", "ck_install_mode_values")


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.first() is not None


def _has_index(conn, index: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :index"),
        {"index": index},
    )
    return result.first() is not None


def _has_constraint(conn, table: str, constraint: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = :table AND constraint_name = :constraint"
        ),
        {"table": table, "constraint": constraint},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()
    for index in INDEXES:
        if _has_index(conn, index):
            op.drop_index(index, table_name=TABLE)
    for constraint in CONSTRAINTS:
        if _has_constraint(conn, TABLE, constraint):
            op.drop_constraint(constraint, TABLE, type_="check")
    for col in COLUMNS:
        if _has_column(conn, TABLE, col):
            op.drop_column(TABLE, col)


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, TABLE, "database_version"):
        op.add_column(TABLE, sa.Column("database_version", sa.String(length=20), nullable=True))
    if not _has_column(conn, TABLE, "node_version"):
        op.add_column(TABLE, sa.Column("node_version", sa.String(length=20), nullable=True))
    if not _has_column(conn, TABLE, "features_configured"):
        op.add_column(
            TABLE,
            sa.Column("features_configured", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        )
    if not _has_column(conn, TABLE, "tools_enabled"):
        op.add_column(
            TABLE,
            sa.Column("tools_enabled", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        )
    if not _has_column(conn, TABLE, "config_snapshot"):
        op.add_column(TABLE, sa.Column("config_snapshot", JSONB(), nullable=True))
    if not _has_column(conn, TABLE, "validation_passed"):
        op.add_column(
            TABLE,
            sa.Column("validation_passed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )
    if not _has_column(conn, TABLE, "validation_warnings"):
        op.add_column(
            TABLE,
            sa.Column("validation_warnings", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        )
    if not _has_column(conn, TABLE, "last_validation_at"):
        op.add_column(TABLE, sa.Column("last_validation_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_column(conn, TABLE, "installer_version"):
        op.add_column(TABLE, sa.Column("installer_version", sa.String(length=20), nullable=True))
    if not _has_column(conn, TABLE, "install_mode"):
        op.add_column(TABLE, sa.Column("install_mode", sa.String(length=20), nullable=True))
    if not _has_column(conn, TABLE, "install_path"):
        op.add_column(TABLE, sa.Column("install_path", sa.Text(), nullable=True))
    if not _has_constraint(conn, TABLE, "ck_database_version_format"):
        op.create_check_constraint(
            "ck_database_version_format",
            TABLE,
            "database_version IS NULL OR database_version ~ '^[0-9]+(\\.([0-9]+|[0-9]+\\.[0-9]+))?$'",
        )
    if not _has_constraint(conn, TABLE, "ck_install_mode_values"):
        op.create_check_constraint(
            "ck_install_mode_values",
            TABLE,
            "install_mode IS NULL OR install_mode IN ('localhost', 'server', 'lan', 'wan')",
        )
    if not _has_index(conn, "idx_setup_mode"):
        op.create_index("idx_setup_mode", TABLE, ["install_mode"])
    if not _has_index(conn, "idx_setup_features_gin"):
        op.create_index("idx_setup_features_gin", TABLE, ["features_configured"], postgresql_using="gin")
    if not _has_index(conn, "idx_setup_tools_gin"):
        op.create_index("idx_setup_tools_gin", TABLE, ["tools_enabled"], postgresql_using="gin")
