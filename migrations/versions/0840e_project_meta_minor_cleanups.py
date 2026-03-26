"""Normalize project meta_data, download_tokens meta_data, and bulk JSON->JSONB

Revision ID: 0840e_project_meta
Revises: 0840d_user_norm
Create Date: 2026-03-25

Phase 1: Extract denormalized JSONB fields from projects.meta_data:
- cancellation_reason  TEXT
- deactivation_reason  TEXT
- early_termination    BOOLEAN DEFAULT FALSE

Phase 2: Extract denormalized JSONB field from download_tokens.meta_data:
- filename  VARCHAR(255)

Phase 3: Drop meta_data columns from projects and download_tokens

Phase 4: Bulk JSON -> JSONB migration (20 columns across 9 tables)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSON, JSONB


# revision identifiers
revision = "0840e_project_meta"
down_revision = "0840d_user_norm"
branch_labels = None
depends_on = None


# Helper: column-exists check
_COL_EXISTS_SQL = (
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_name = :tbl AND column_name = :col"
)

# Helper: table-exists check
_TBL_EXISTS_SQL = (
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_name = :tbl"
)


def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(text(_COL_EXISTS_SQL), {"tbl": table, "col": column})
    return result.fetchone() is not None


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(text(_TBL_EXISTS_SQL), {"tbl": table})
    return result.fetchone() is not None


def _col_is_jsonb(conn, table: str, column: str) -> bool:
    """Check if a column is already JSONB (vs JSON)."""
    result = conn.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = :tbl AND column_name = :col"
        ),
        {"tbl": table, "col": column},
    )
    row = result.fetchone()
    if row is None:
        return False
    # PostgreSQL reports 'jsonb' for JSONB and 'json' for JSON;
    # USER-DEFINED can appear in edge cases, treat as already done.
    return row[0] != "json"


# ── 20 columns to migrate from JSON to JSONB ──
_JSON_TO_JSONB_COLUMNS = [
    ("agent_templates", "variables"),
    ("agent_templates", "behavioral_rules"),
    ("agent_templates", "success_criteria"),
    ("agent_templates", "tags"),
    ("agent_templates", "meta_data"),
    ("template_archives", "variables"),
    ("template_archives", "behavioral_rules"),
    ("template_archives", "success_criteria"),
    ("template_usage_stats", "variables_used"),
    ("template_usage_stats", "augmentations_applied"),
    ("agent_executions", "result"),
    ("configurations", "value"),
    ("discovery_config", "settings"),
    ("git_configs", "webhook_events"),
    ("git_configs", "ignore_patterns"),
    ("git_configs", "git_config_options"),
    ("git_commits", "files_changed"),
    ("git_commits", "webhook_response"),
    ("vision_documents", "meta_data"),
    ("mcp_context_index", "keywords"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # ── Phase 1: Add new columns to projects ──
    new_project_cols = [
        ("cancellation_reason", sa.Text(), None),
        ("deactivation_reason", sa.Text(), None),
        ("early_termination", sa.Boolean(), sa.text("false")),
    ]
    for col_name, col_type, default in new_project_cols:
        if not _column_exists(conn, "projects", col_name):
            op.add_column(
                "projects",
                sa.Column(col_name, col_type, server_default=default, nullable=True),
            )

    # ── Phase 2: Backfill projects columns from meta_data JSONB ──
    if _column_exists(conn, "projects", "meta_data"):
        conn.execute(
            text("""
                UPDATE projects SET cancellation_reason = meta_data->>'cancellation_reason'
                WHERE meta_data->>'cancellation_reason' IS NOT NULL
                    AND cancellation_reason IS NULL
            """)
        )
        conn.execute(
            text("""
                UPDATE projects SET deactivation_reason = meta_data->>'deactivation_reason'
                WHERE meta_data->>'deactivation_reason' IS NOT NULL
                    AND deactivation_reason IS NULL
            """)
        )
        conn.execute(
            text("""
                UPDATE projects SET early_termination = TRUE
                WHERE (meta_data->>'early_termination')::boolean = TRUE
                    AND (early_termination IS NULL OR early_termination = FALSE)
            """)
        )

    # ── Phase 3: Add filename column to download_tokens ──
    if _table_exists(conn, "download_tokens"):
        if not _column_exists(conn, "download_tokens", "filename"):
            op.add_column(
                "download_tokens",
                sa.Column("filename", sa.String(255), nullable=True),
            )

        # Backfill filename from meta_data
        if _column_exists(conn, "download_tokens", "meta_data"):
            conn.execute(
                text("""
                    UPDATE download_tokens SET filename = meta_data->>'filename'
                    WHERE meta_data->>'filename' IS NOT NULL
                        AND filename IS NULL
                """)
            )

    # ── Phase 4: Drop meta_data columns ──
    if _column_exists(conn, "projects", "meta_data"):
        op.drop_column("projects", "meta_data")

    if _table_exists(conn, "download_tokens"):
        if _column_exists(conn, "download_tokens", "meta_data"):
            op.drop_column("download_tokens", "meta_data")

    # ── Phase 5: JSON -> JSONB bulk migration (20 columns) ──
    for tbl, col in _JSON_TO_JSONB_COLUMNS:
        if not _table_exists(conn, tbl):
            continue
        if not _column_exists(conn, tbl, col):
            continue
        if _col_is_jsonb(conn, tbl, col):
            continue
        conn.execute(
            text(
                f'ALTER TABLE {tbl} ALTER COLUMN "{col}" '
                f'TYPE JSONB USING "{col}"::jsonb'
            )
        )


def downgrade() -> None:
    conn = op.get_bind()

    # ── 1. Convert JSONB columns back to JSON (reverse of Phase 5) ──
    for tbl, col in _JSON_TO_JSONB_COLUMNS:
        if not _table_exists(conn, tbl):
            continue
        if not _column_exists(conn, tbl, col):
            continue
        if _col_is_jsonb(conn, tbl, col):
            conn.execute(
                text(
                    f'ALTER TABLE {tbl} ALTER COLUMN "{col}" '
                    f'TYPE JSON USING "{col}"::json'
                )
            )

    # ── 2. Re-add meta_data columns (reverse of Phase 4) ──
    if not _column_exists(conn, "projects", "meta_data"):
        op.add_column("projects", sa.Column("meta_data", JSONB, nullable=True))

    if _table_exists(conn, "download_tokens"):
        if not _column_exists(conn, "download_tokens", "meta_data"):
            op.add_column("download_tokens", sa.Column("meta_data", JSONB, nullable=True))

    # ── 3. Reverse backfill: rebuild projects.meta_data from new columns ──
    conn.execute(
        text("""
            UPDATE projects SET meta_data = jsonb_build_object(
                'cancellation_reason', cancellation_reason,
                'deactivation_reason', deactivation_reason,
                'early_termination', COALESCE(early_termination, FALSE)
            )
            WHERE cancellation_reason IS NOT NULL
                OR deactivation_reason IS NOT NULL
                OR early_termination = TRUE
        """)
    )

    # ── 4. Reverse backfill: rebuild download_tokens.meta_data from filename ──
    if _table_exists(conn, "download_tokens"):
        conn.execute(
            text("""
                UPDATE download_tokens SET meta_data = jsonb_build_object(
                    'filename', filename
                )
                WHERE filename IS NOT NULL
            """)
        )

    # ── 5. Drop new columns (reverse of Phase 1 + Phase 3) ──
    for col_name in ("cancellation_reason", "deactivation_reason", "early_termination"):
        if _column_exists(conn, "projects", col_name):
            op.drop_column("projects", col_name)

    if _table_exists(conn, "download_tokens"):
        if _column_exists(conn, "download_tokens", "filename"):
            op.drop_column("download_tokens", "filename")
