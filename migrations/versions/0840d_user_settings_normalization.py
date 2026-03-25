"""Normalize User settings: extract JSONB into relational table + depth columns

Revision ID: 0840d_user_norm
Revises: 0840c_config_norm
Create Date: 2026-03-25

Extracts denormalized JSONB settings from users table:

New table:
- user_field_priorities  (was field_priority_config JSONB -> priorities -> {category} -> toggle)

New columns on users (was depth_config JSONB):
- depth_vision_documents   VARCHAR(20) DEFAULT 'medium'
- depth_memory_last_n      INTEGER DEFAULT 3
- depth_git_commits        INTEGER DEFAULT 25
- depth_agent_templates    VARCHAR(20) DEFAULT 'type_only'
- depth_tech_stack_sections VARCHAR(20) DEFAULT 'all'
- depth_architecture       VARCHAR(20) DEFAULT 'overview'
- execution_mode           VARCHAR(20) DEFAULT 'claude_code'

Old columns dropped after backfill:
- field_priority_config JSONB
- depth_config JSONB
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision = "0840d_user_norm"
down_revision = "0840c_config_norm"
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
    result = conn.execute(sa.text(_COL_EXISTS_SQL), {"tbl": table, "col": column})
    return result.fetchone() is not None


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(sa.text(_TBL_EXISTS_SQL), {"tbl": table})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Create user_field_priorities table ──
    if not _table_exists(conn, "user_field_priorities"):
        op.create_table(
            "user_field_priorities",
            sa.Column("id", sa.String(36), primary_key=True,
                      server_default=sa.text("gen_random_uuid()::text")),
            sa.Column("user_id", sa.String(36),
                      sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("tenant_key", sa.String(255), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "category", name="uq_user_field_priorities_user_category"),
        )
        op.create_index(
            "idx_user_field_priorities_user",
            "user_field_priorities",
            ["user_id", "tenant_key"],
        )

    # ── 2. Add depth columns to users ──
    depth_columns = [
        ("depth_vision_documents", sa.String(20), sa.text("'medium'")),
        ("depth_memory_last_n", sa.Integer(), sa.text("3")),
        ("depth_git_commits", sa.Integer(), sa.text("25")),
        ("depth_agent_templates", sa.String(20), sa.text("'type_only'")),
        ("depth_tech_stack_sections", sa.String(20), sa.text("'all'")),
        ("depth_architecture", sa.String(20), sa.text("'overview'")),
        ("execution_mode", sa.String(20), sa.text("'claude_code'")),
    ]
    for col_name, col_type, default in depth_columns:
        if not _column_exists(conn, "users", col_name):
            op.add_column(
                "users",
                sa.Column(col_name, col_type, server_default=default, nullable=True),
            )

    # ── 3. Backfill user_field_priorities from field_priority_config JSONB ──
    if _column_exists(conn, "users", "field_priority_config"):
        conn.execute(
            sa.text("""
                INSERT INTO user_field_priorities (id, user_id, tenant_key, category, enabled)
                SELECT gen_random_uuid()::text, u.id, u.tenant_key, cat.category,
                    COALESCE(
                        (u.field_priority_config->'priorities'->cat.category->>'toggle')::boolean,
                        TRUE
                    )
                FROM users u
                CROSS JOIN (VALUES
                    ('tech_stack'), ('architecture'), ('testing'),
                    ('vision_documents'), ('memory_360'), ('git_history'),
                    ('agent_templates')
                ) AS cat(category)
                WHERE u.field_priority_config IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM user_field_priorities ufp
                        WHERE ufp.user_id = u.id AND ufp.category = cat.category
                    )
            """)
        )

    # ── 4. Backfill depth columns from depth_config JSONB ──
    if _column_exists(conn, "users", "depth_config"):
        conn.execute(
            sa.text("""
                UPDATE users SET
                    depth_vision_documents = COALESCE(depth_config->>'vision_documents', 'medium'),
                    depth_memory_last_n = COALESCE((depth_config->>'memory_last_n_projects')::integer, 3),
                    depth_git_commits = COALESCE((depth_config->>'git_commits')::integer, 25),
                    depth_agent_templates = COALESCE(depth_config->>'agent_templates', 'type_only'),
                    depth_tech_stack_sections = COALESCE(depth_config->>'tech_stack_sections', 'all'),
                    depth_architecture = COALESCE(depth_config->>'architecture_depth', 'overview'),
                    execution_mode = COALESCE(depth_config->>'execution_mode', 'claude_code')
                WHERE depth_config IS NOT NULL
            """)
        )

    # ── 5. Drop old JSONB columns ──
    if _column_exists(conn, "users", "field_priority_config"):
        op.drop_column("users", "field_priority_config")

    if _column_exists(conn, "users", "depth_config"):
        op.drop_column("users", "depth_config")


def downgrade() -> None:
    conn = op.get_bind()

    # ── 1. Re-add JSONB columns ──
    if not _column_exists(conn, "users", "field_priority_config"):
        op.add_column("users", sa.Column("field_priority_config", JSONB, nullable=True))

    if not _column_exists(conn, "users", "depth_config"):
        op.add_column("users", sa.Column("depth_config", JSONB, nullable=True))

    # ── 2. Reverse backfill: rebuild field_priority_config from user_field_priorities ──
    if _table_exists(conn, "user_field_priorities"):
        conn.execute(
            sa.text("""
                UPDATE users u SET field_priority_config = jsonb_build_object(
                    'priorities', COALESCE((
                        SELECT jsonb_object_agg(
                            ufp.category,
                            jsonb_build_object('toggle', ufp.enabled)
                        )
                        FROM user_field_priorities ufp
                        WHERE ufp.user_id = u.id
                    ), '{}'::jsonb)
                )
            """)
        )

    # ── 3. Reverse backfill: rebuild depth_config from depth columns ──
    conn.execute(
        sa.text("""
            UPDATE users SET depth_config = jsonb_build_object(
                'vision_documents', COALESCE(depth_vision_documents, 'medium'),
                'memory_last_n_projects', COALESCE(depth_memory_last_n, 3),
                'git_commits', COALESCE(depth_git_commits, 25),
                'agent_templates', COALESCE(depth_agent_templates, 'type_only'),
                'tech_stack_sections', COALESCE(depth_tech_stack_sections, 'all'),
                'architecture_depth', COALESCE(depth_architecture, 'overview'),
                'execution_mode', COALESCE(execution_mode, 'claude_code')
            )
        """)
    )

    # ── 4. Drop user_field_priorities table ──
    if _table_exists(conn, "user_field_priorities"):
        op.drop_table("user_field_priorities")

    # ── 5. Drop depth columns from users ──
    depth_col_names = [
        "depth_vision_documents",
        "depth_memory_last_n",
        "depth_git_commits",
        "depth_agent_templates",
        "depth_tech_stack_sections",
        "depth_architecture",
        "execution_mode",
    ]
    for col_name in depth_col_names:
        if _column_exists(conn, "users", col_name):
            op.drop_column("users", col_name)
