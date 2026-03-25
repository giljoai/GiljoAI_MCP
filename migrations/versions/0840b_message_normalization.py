"""Normalize messages table: extract JSONB arrays into junction tables

Revision ID: 0840b_msg_norm
Revises: 0840a_dead_cols
Create Date: 2026-03-25

Extracts denormalized JSONB data from the messages table into proper
relational structures:

New columns on messages:
- from_agent_id   (was meta_data->>'_from_agent')
- from_display_name (was meta_data->>'_from_display_name')
- auto_generated  (was meta_data->>'auto_generated')

New junction tables (replacing JSONB arrays):
- message_recipients     (was to_agents JSONB)
- message_acknowledgments (was acknowledged_by JSONB)
- message_completions    (was completed_by JSONB)

Old columns dropped after backfill:
- to_agents, acknowledged_by, completed_by, meta_data
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "0840b_msg_norm"
down_revision: str | None = "0840a_dead_cols"
branch_labels: str | None = None
depends_on: str | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in the given table (idempotency guard)."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns "
            "  WHERE table_name = :table AND column_name = :col"
            ")"
        ),
        {"table": table_name, "col": column_name},
    )
    return result.scalar()


def _table_exists(table_name: str) -> bool:
    """Check if a table exists (idempotency guard)."""
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables "
            "  WHERE table_name = :table"
            ")"
        ),
        {"table": table_name},
    )
    return result.scalar()


# ---------------------------------------------------------------------------
# UPGRADE
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Add new scalar columns to messages
    # ------------------------------------------------------------------
    if not _column_exists("messages", "from_agent_id"):
        op.add_column(
            "messages",
            sa.Column("from_agent_id", sa.String(36), nullable=True),
        )

    if not _column_exists("messages", "from_display_name"):
        op.add_column(
            "messages",
            sa.Column("from_display_name", sa.String(255), nullable=True),
        )

    if not _column_exists("messages", "auto_generated"):
        op.add_column(
            "messages",
            sa.Column(
                "auto_generated",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            ),
        )

    # ------------------------------------------------------------------
    # 2. Create junction tables
    # ------------------------------------------------------------------
    if not _table_exists("message_recipients"):
        op.create_table(
            "message_recipients",
            sa.Column(
                "id",
                sa.String(36),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()::text"),
            ),
            sa.Column(
                "message_id",
                sa.String(36),
                sa.ForeignKey("messages.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("agent_id", sa.String(36), nullable=False),
            sa.Column("tenant_key", sa.String(255), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint("message_id", "agent_id", name="uq_msg_recipient"),
        )
        op.create_index(
            "idx_message_recipients_agent",
            "message_recipients",
            ["agent_id", "tenant_key"],
        )
        op.create_index(
            "idx_message_recipients_message",
            "message_recipients",
            ["message_id"],
        )

    if not _table_exists("message_acknowledgments"):
        op.create_table(
            "message_acknowledgments",
            sa.Column(
                "id",
                sa.String(36),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()::text"),
            ),
            sa.Column(
                "message_id",
                sa.String(36),
                sa.ForeignKey("messages.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("agent_id", sa.String(36), nullable=False),
            sa.Column("tenant_key", sa.String(255), nullable=False),
            sa.Column(
                "acknowledged_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint("message_id", "agent_id", name="uq_msg_ack"),
        )
        op.create_index(
            "idx_message_acks_agent",
            "message_acknowledgments",
            ["agent_id", "tenant_key"],
        )
        op.create_index(
            "idx_message_acks_message",
            "message_acknowledgments",
            ["message_id"],
        )

    if not _table_exists("message_completions"):
        op.create_table(
            "message_completions",
            sa.Column(
                "id",
                sa.String(36),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()::text"),
            ),
            sa.Column(
                "message_id",
                sa.String(36),
                sa.ForeignKey("messages.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("agent_id", sa.String(36), nullable=False),
            sa.Column("tenant_key", sa.String(255), nullable=False),
            sa.Column(
                "completed_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint("message_id", "agent_id", name="uq_msg_completion"),
        )
        op.create_index(
            "idx_message_completions_agent",
            "message_completions",
            ["agent_id", "tenant_key"],
        )
        op.create_index(
            "idx_message_completions_message",
            "message_completions",
            ["message_id"],
        )

    # ------------------------------------------------------------------
    # 3. Backfill scalar columns from meta_data
    # ------------------------------------------------------------------
    if _column_exists("messages", "meta_data"):
        op.execute(
            sa.text(
                "UPDATE messages "
                "SET from_agent_id = meta_data->>'_from_agent' "
                "WHERE meta_data->>'_from_agent' IS NOT NULL "
                "  AND from_agent_id IS NULL"
            )
        )
        op.execute(
            sa.text(
                "UPDATE messages "
                "SET from_display_name = meta_data->>'_from_display_name' "
                "WHERE meta_data->>'_from_display_name' IS NOT NULL "
                "  AND from_display_name IS NULL"
            )
        )
        op.execute(
            sa.text(
                "UPDATE messages "
                "SET auto_generated = (meta_data->>'auto_generated')::boolean "
                "WHERE meta_data->>'auto_generated' IS NOT NULL "
                "  AND auto_generated = false"
            )
        )

    # ------------------------------------------------------------------
    # 4. Backfill junction tables from JSONB arrays
    # ------------------------------------------------------------------
    if _column_exists("messages", "to_agents"):
        op.execute(
            sa.text(
                "INSERT INTO message_recipients (id, message_id, agent_id, tenant_key) "
                "SELECT gen_random_uuid()::text, m.id, elem.value, m.tenant_key "
                "FROM messages m, "
                "     jsonb_array_elements_text(m.to_agents) AS elem(value) "
                "WHERE m.to_agents IS NOT NULL "
                "  AND jsonb_array_length(m.to_agents) > 0 "
                "ON CONFLICT ON CONSTRAINT uq_msg_recipient DO NOTHING"
            )
        )

    if _column_exists("messages", "acknowledged_by"):
        op.execute(
            sa.text(
                "INSERT INTO message_acknowledgments "
                "  (id, message_id, agent_id, tenant_key) "
                "SELECT gen_random_uuid()::text, m.id, elem.value, m.tenant_key "
                "FROM messages m, "
                "     jsonb_array_elements_text(m.acknowledged_by) AS elem(value) "
                "WHERE m.acknowledged_by IS NOT NULL "
                "  AND jsonb_array_length(m.acknowledged_by) > 0 "
                "ON CONFLICT ON CONSTRAINT uq_msg_ack DO NOTHING"
            )
        )

    if _column_exists("messages", "completed_by"):
        op.execute(
            sa.text(
                "INSERT INTO message_completions "
                "  (id, message_id, agent_id, tenant_key) "
                "SELECT gen_random_uuid()::text, m.id, elem.value, m.tenant_key "
                "FROM messages m, "
                "     jsonb_array_elements_text(m.completed_by) AS elem(value) "
                "WHERE m.completed_by IS NOT NULL "
                "  AND jsonb_array_length(m.completed_by) > 0 "
                "ON CONFLICT ON CONSTRAINT uq_msg_completion DO NOTHING"
            )
        )

    # ------------------------------------------------------------------
    # 5. Drop old JSONB columns
    # ------------------------------------------------------------------
    for col in ("to_agents", "acknowledged_by", "completed_by", "meta_data"):
        if _column_exists("messages", col):
            op.drop_column("messages", col)


# ---------------------------------------------------------------------------
# DOWNGRADE
# ---------------------------------------------------------------------------


def downgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Re-add old JSONB columns
    # ------------------------------------------------------------------
    if not _column_exists("messages", "to_agents"):
        op.add_column(
            "messages",
            sa.Column("to_agents", JSONB(), nullable=True),
        )

    if not _column_exists("messages", "acknowledged_by"):
        op.add_column(
            "messages",
            sa.Column("acknowledged_by", JSONB(), nullable=True),
        )

    if not _column_exists("messages", "completed_by"):
        op.add_column(
            "messages",
            sa.Column("completed_by", JSONB(), nullable=True),
        )

    if not _column_exists("messages", "meta_data"):
        op.add_column(
            "messages",
            sa.Column("meta_data", JSONB(), nullable=True),
        )

    # ------------------------------------------------------------------
    # 2. Reverse-backfill: junction tables -> JSONB arrays
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            "UPDATE messages m "
            "SET to_agents = COALESCE(("
            "  SELECT jsonb_agg(mr.agent_id) "
            "  FROM message_recipients mr "
            "  WHERE mr.message_id = m.id"
            "), '[]'::jsonb)"
        )
    )

    op.execute(
        sa.text(
            "UPDATE messages m "
            "SET acknowledged_by = COALESCE(("
            "  SELECT jsonb_agg(ma.agent_id) "
            "  FROM message_acknowledgments ma "
            "  WHERE ma.message_id = m.id"
            "), '[]'::jsonb)"
        )
    )

    op.execute(
        sa.text(
            "UPDATE messages m "
            "SET completed_by = COALESCE(("
            "  SELECT jsonb_agg(mc.agent_id) "
            "  FROM message_completions mc "
            "  WHERE mc.message_id = m.id"
            "), '[]'::jsonb)"
        )
    )

    # ------------------------------------------------------------------
    # 3. Reverse-backfill: scalar columns -> meta_data JSONB
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            "UPDATE messages "
            "SET meta_data = COALESCE(meta_data, '{}'::jsonb) || "
            "  jsonb_build_object("
            "    '_from_agent', from_agent_id, "
            "    '_from_display_name', from_display_name, "
            "    'auto_generated', auto_generated"
            "  ) "
            "WHERE from_agent_id IS NOT NULL "
            "   OR from_display_name IS NOT NULL "
            "   OR auto_generated = true"
        )
    )

    # ------------------------------------------------------------------
    # 4. Drop new columns and tables
    # ------------------------------------------------------------------
    if _column_exists("messages", "from_agent_id"):
        op.drop_column("messages", "from_agent_id")

    if _column_exists("messages", "from_display_name"):
        op.drop_column("messages", "from_display_name")

    if _column_exists("messages", "auto_generated"):
        op.drop_column("messages", "auto_generated")

    if _table_exists("message_completions"):
        op.drop_table("message_completions")

    if _table_exists("message_acknowledgments"):
        op.drop_table("message_acknowledgments")

    if _table_exists("message_recipients"):
        op.drop_table("message_recipients")
