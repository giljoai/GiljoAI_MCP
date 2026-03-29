"""Drop 7 dead meta_data columns never written to or read in production

Revision ID: 0840a_dead_cols
Revises: baseline_v33
Create Date: 2026-03-25

These JSON/JSONB meta_data columns exist in the schema but are never populated
or queried by any application code. Dropping them reduces schema noise and
eliminates confusion about their purpose.

Columns dropped:
- template_archives.meta_data (JSON)
- products.meta_data (JSON)
- tasks.meta_data (JSONB)
- git_configs.meta_data (JSON)
- git_commits.meta_data (JSON)
- setup_state.meta_data (JSONB)
- optimization_metrics.meta_data (JSON)

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "0840a_dead_cols"
down_revision: str | None = "baseline_v33"
branch_labels: str | None = None
depends_on: str | None = None


# (table_name, column_name, column_type) -- column_type used only by downgrade
_DEAD_COLUMNS: list[tuple[str, str, sa.types.TypeEngine]] = [
    ("template_archives", "meta_data", sa.JSON()),
    ("products", "meta_data", sa.JSON()),
    ("tasks", "meta_data", JSONB()),
    ("git_configs", "meta_data", sa.JSON()),
    ("git_commits", "meta_data", sa.JSON()),
    ("setup_state", "meta_data", JSONB()),
    ("optimization_metrics", "meta_data", sa.JSON()),
]


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


def upgrade() -> None:
    for table_name, column_name, _ in _DEAD_COLUMNS:
        if _column_exists(table_name, column_name):
            op.drop_column(table_name, column_name)


def downgrade() -> None:
    for table_name, column_name, column_type in _DEAD_COLUMNS:
        if not _column_exists(table_name, column_name):
            op.add_column(
                table_name,
                sa.Column(column_name, column_type, nullable=True),
            )
