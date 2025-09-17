"""Add template management tables

Revision ID: add_template_mgmt
Revises: add_agent_interactions_table
Create Date: 2025-01-14 23:00:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "add_template_mgmt"
down_revision = "a7b8c9d2e3f4"
branch_labels = None
depends_on = None


def upgrade():
    """Add template management tables"""

    # Create agent_templates table
    op.create_table(
        "agent_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_key", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("project_type", sa.String(50), nullable=True),
        sa.Column("template_content", sa.Text(), nullable=False),
        sa.Column("variables", sa.JSON(), nullable=True),
        sa.Column("behavioral_rules", sa.JSON(), nullable=True),
        sa.Column("success_criteria", sa.JSON(), nullable=True),
        sa.Column("usage_count", sa.Integer(), default=0),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("avg_generation_ms", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(20), default="1.0.0"),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("is_default", sa.Boolean(), default=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column("created_by", sa.String(100), nullable=True),
    )

    # Create indexes for agent_templates
    op.create_index("idx_template_tenant", "agent_templates", ["tenant_key"])
    op.create_index("idx_template_product", "agent_templates", ["product_id"])
    op.create_index("idx_template_category", "agent_templates", ["category"])
    op.create_index("idx_template_role", "agent_templates", ["role"])
    op.create_index("idx_template_active", "agent_templates", ["is_active"])

    # Create unique constraint
    op.create_unique_constraint(
        "uq_template_product_name_version",
        "agent_templates",
        ["product_id", "name", "version"]
    )

    # Create template_archives table
    op.create_table(
        "template_archives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_key", sa.String(36), nullable=False),
        sa.Column("template_id", sa.String(36), sa.ForeignKey("agent_templates.id"), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("template_content", sa.Text(), nullable=False),
        sa.Column("variables", sa.JSON(), nullable=True),
        sa.Column("behavioral_rules", sa.JSON(), nullable=True),
        sa.Column("success_criteria", sa.JSON(), nullable=True),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("archive_reason", sa.String(255), nullable=True),
        sa.Column("archive_type", sa.String(20), default="manual"),
        sa.Column("archived_by", sa.String(100), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("usage_count_at_archive", sa.Integer(), nullable=True),
        sa.Column("avg_generation_ms_at_archive", sa.Float(), nullable=True),
        sa.Column("is_restorable", sa.Boolean(), default=True),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_by", sa.String(100), nullable=True),
        sa.Column("meta_data", sa.JSON(), nullable=True),
    )

    # Create indexes for template_archives
    op.create_index("idx_archive_tenant", "template_archives", ["tenant_key"])
    op.create_index("idx_archive_template", "template_archives", ["template_id"])
    op.create_index("idx_archive_product", "template_archives", ["product_id"])
    op.create_index("idx_archive_version", "template_archives", ["version"])
    op.create_index("idx_archive_date", "template_archives", ["archived_at"])

    # Create template_augmentations table
    op.create_table(
        "template_augmentations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_key", sa.String(36), nullable=False),
        sa.Column("template_id", sa.String(36), sa.ForeignKey("agent_templates.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("augmentation_type", sa.String(50), nullable=False),
        sa.Column("target_section", sa.String(100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("priority", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("usage_count", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Create indexes for template_augmentations
    op.create_index("idx_augment_tenant", "template_augmentations", ["tenant_key"])
    op.create_index("idx_augment_template", "template_augmentations", ["template_id"])
    op.create_index("idx_augment_active", "template_augmentations", ["is_active"])

    # Create template_usage_stats table
    op.create_table(
        "template_usage_stats",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_key", sa.String(36), nullable=False),
        sa.Column("template_id", sa.String(36), sa.ForeignKey("agent_templates.id"), nullable=False),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("generation_ms", sa.Integer(), nullable=True),
        sa.Column("variables_used", sa.JSON(), nullable=True),
        sa.Column("augmentations_applied", sa.JSON(), nullable=True),
        sa.Column("agent_completed", sa.Boolean(), nullable=True),
        sa.Column("agent_success_rate", sa.Float(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
    )

    # Create indexes for template_usage_stats
    op.create_index("idx_usage_tenant", "template_usage_stats", ["tenant_key"])
    op.create_index("idx_usage_template", "template_usage_stats", ["template_id"])
    op.create_index("idx_usage_project", "template_usage_stats", ["project_id"])
    op.create_index("idx_usage_date", "template_usage_stats", ["used_at"])


def downgrade():
    """Drop template management tables"""

    # Drop tables in reverse order (due to foreign keys)
    op.drop_table("template_usage_stats")
    op.drop_table("template_augmentations")
    op.drop_table("template_archives")
    op.drop_table("agent_templates")
