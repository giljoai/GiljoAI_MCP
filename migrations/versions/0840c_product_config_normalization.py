"""Normalize Product config_data: extract JSONB into relational tables

Revision ID: 0840c_config_norm
Revises: 0840b_msg_norm
Create Date: 2026-03-25

Extracts denormalized config_data JSONB from products table into proper
relational structures:

New column on products:
- core_features TEXT (was config_data->'features'->>'core')

New tables (1:1 with products):
- product_tech_stacks     (was config_data->'tech_stack')
- product_architectures   (was config_data->'architecture')
- product_test_configs    (was config_data->'test_config')

Old column dropped after backfill:
- config_data JSONB
- idx_product_config_data_gin GIN index
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision = "0840c_config_norm"
down_revision = "0840b_msg_norm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Add core_features column to products ──
    # Idempotency: check column exists before adding
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'products' AND column_name = 'core_features'"
        )
    )
    if result.fetchone() is None:
        op.add_column("products", sa.Column("core_features", sa.Text(), nullable=True))

    # ── 2. Create product_tech_stacks table ──
    result = conn.execute(
        sa.text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'product_tech_stacks'"
        )
    )
    if result.fetchone() is None:
        op.create_table(
            "product_tech_stacks",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("tenant_key", sa.String(255), nullable=False),
            sa.Column("programming_languages", sa.Text(), nullable=True),
            sa.Column("frontend_frameworks", sa.Text(), nullable=True),
            sa.Column("backend_frameworks", sa.Text(), nullable=True),
            sa.Column("databases_storage", sa.Text(), nullable=True),
            sa.Column("infrastructure", sa.Text(), nullable=True),
            sa.Column("dev_tools", sa.Text(), nullable=True),
            sa.Column("target_windows", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("target_linux", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("target_macos", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("target_android", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("target_ios", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("target_cross_platform", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_product_tech_stacks_product", "product_tech_stacks", ["product_id"])
        op.create_index("idx_product_tech_stacks_tenant", "product_tech_stacks", ["tenant_key"])

    # ── 3. Create product_architectures table ──
    result = conn.execute(
        sa.text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'product_architectures'"
        )
    )
    if result.fetchone() is None:
        op.create_table(
            "product_architectures",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("tenant_key", sa.String(255), nullable=False),
            sa.Column("primary_pattern", sa.Text(), nullable=True),
            sa.Column("design_patterns", sa.Text(), nullable=True),
            sa.Column("api_style", sa.Text(), nullable=True),
            sa.Column("architecture_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_product_architectures_product", "product_architectures", ["product_id"])
        op.create_index("idx_product_architectures_tenant", "product_architectures", ["tenant_key"])

    # ── 4. Create product_test_configs table ──
    result = conn.execute(
        sa.text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = 'product_test_configs'"
        )
    )
    if result.fetchone() is None:
        op.create_table(
            "product_test_configs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("product_id", sa.String(36), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("tenant_key", sa.String(255), nullable=False),
            sa.Column("quality_standards", sa.Text(), nullable=True),
            sa.Column("test_strategy", sa.String(50), nullable=True),
            sa.Column("coverage_target", sa.Integer(), server_default=sa.text("80")),
            sa.Column("testing_frameworks", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_product_test_configs_product", "product_test_configs", ["product_id"])
        op.create_index("idx_product_test_configs_tenant", "product_test_configs", ["tenant_key"])

    # ── 5. Backfill data from config_data JSONB ──
    # Only run if config_data column still exists (idempotency)
    result = conn.execute(
        sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'products' AND column_name = 'config_data'"
        )
    )
    if result.fetchone() is not None:
        # Backfill core_features
        conn.execute(
            sa.text(
                "UPDATE products SET core_features = config_data->'features'->>'core' "
                "WHERE config_data IS NOT NULL AND core_features IS NULL"
            )
        )

        # Backfill product_tech_stacks (skip if already backfilled)
        conn.execute(
            sa.text("""
                INSERT INTO product_tech_stacks (id, product_id, tenant_key,
                    programming_languages, frontend_frameworks, backend_frameworks,
                    databases_storage, infrastructure, dev_tools)
                SELECT gen_random_uuid()::text, p.id, p.tenant_key,
                    p.config_data->'tech_stack'->>'languages',
                    p.config_data->'tech_stack'->>'frontend',
                    p.config_data->'tech_stack'->>'backend',
                    p.config_data->'tech_stack'->>'database',
                    p.config_data->'tech_stack'->>'infrastructure',
                    p.config_data->'tech_stack'->>'dev_tools'
                FROM products p
                WHERE p.config_data IS NOT NULL
                    AND p.config_data->'tech_stack' IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM product_tech_stacks pts WHERE pts.product_id = p.id
                    )
            """)
        )

        # Backfill product_architectures
        conn.execute(
            sa.text("""
                INSERT INTO product_architectures (id, product_id, tenant_key,
                    primary_pattern, design_patterns, api_style, architecture_notes)
                SELECT gen_random_uuid()::text, p.id, p.tenant_key,
                    p.config_data->'architecture'->>'pattern',
                    p.config_data->'architecture'->>'design_patterns',
                    p.config_data->'architecture'->>'api_style',
                    p.config_data->'architecture'->>'notes'
                FROM products p
                WHERE p.config_data IS NOT NULL
                    AND p.config_data->'architecture' IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM product_architectures pa WHERE pa.product_id = p.id
                    )
            """)
        )

        # Backfill product_test_configs
        conn.execute(
            sa.text("""
                INSERT INTO product_test_configs (id, product_id, tenant_key,
                    quality_standards, test_strategy, coverage_target, testing_frameworks)
                SELECT gen_random_uuid()::text, p.id, p.tenant_key,
                    p.config_data->'test_config'->>'quality_standards',
                    p.config_data->'test_config'->>'strategy',
                    COALESCE((p.config_data->'test_config'->>'coverage_target')::integer, 80),
                    p.config_data->'test_config'->>'frameworks'
                FROM products p
                WHERE p.config_data IS NOT NULL
                    AND p.config_data->'test_config' IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM product_test_configs ptc WHERE ptc.product_id = p.id
                    )
            """)
        )

        # ── 6. Drop config_data column and GIN index ──
        # Drop GIN index first (idempotency)
        result = conn.execute(
            sa.text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'products' AND indexname = 'idx_product_config_data_gin'"
            )
        )
        if result.fetchone() is not None:
            op.drop_index("idx_product_config_data_gin", table_name="products")

        op.drop_column("products", "config_data")


def downgrade() -> None:
    # Re-add config_data column
    op.add_column("products", sa.Column("config_data", JSONB, nullable=True))
    op.create_index(
        "idx_product_config_data_gin", "products", ["config_data"],
        postgresql_using="gin"
    )

    # Reverse backfill: rebuild config_data from related tables
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE products p SET config_data = jsonb_build_object(
                'tech_stack', COALESCE((
                    SELECT jsonb_build_object(
                        'languages', COALESCE(pts.programming_languages, ''),
                        'frontend', COALESCE(pts.frontend_frameworks, ''),
                        'backend', COALESCE(pts.backend_frameworks, ''),
                        'database', COALESCE(pts.databases_storage, ''),
                        'infrastructure', COALESCE(pts.infrastructure, ''),
                        'dev_tools', COALESCE(pts.dev_tools, '')
                    ) FROM product_tech_stacks pts WHERE pts.product_id = p.id
                ), '{}'::jsonb),
                'architecture', COALESCE((
                    SELECT jsonb_build_object(
                        'pattern', COALESCE(pa.primary_pattern, ''),
                        'design_patterns', COALESCE(pa.design_patterns, ''),
                        'api_style', COALESCE(pa.api_style, ''),
                        'notes', COALESCE(pa.architecture_notes, '')
                    ) FROM product_architectures pa WHERE pa.product_id = p.id
                ), '{}'::jsonb),
                'features', jsonb_build_object('core', COALESCE(p.core_features, '')),
                'test_config', COALESCE((
                    SELECT jsonb_build_object(
                        'quality_standards', COALESCE(ptc.quality_standards, ''),
                        'strategy', COALESCE(ptc.test_strategy, ''),
                        'coverage_target', COALESCE(ptc.coverage_target, 80),
                        'frameworks', COALESCE(ptc.testing_frameworks, '')
                    ) FROM product_test_configs ptc WHERE ptc.product_id = p.id
                ), '{}'::jsonb)
            )
        """)
    )

    # Drop new tables
    op.drop_table("product_test_configs")
    op.drop_table("product_architectures")
    op.drop_table("product_tech_stacks")

    # Drop core_features column
    op.drop_column("products", "core_features")
