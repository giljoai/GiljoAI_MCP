"""Add setup_state table with multi-tenant support

This migration creates the setup_state table to replace file-based setup state tracking.
The table stores installation status, version info, configured features, and validation results
on a per-tenant basis.

Key features:
- Multi-tenant isolation with UNIQUE constraint on tenant_key
- JSONB columns for features_configured and tools_enabled (efficient querying)
- GIN indexes on JSONB columns for fast nested queries
- Partial index on incomplete setups for performance
- CHECK constraints for version format validation and data integrity
- Automatic migration from legacy setup_state.json if present

Revision ID: e2639692ae52
Revises: be602279af75
Create Date: 2025-10-07 10:37:04.876016
"""
import json
import logging
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e2639692ae52'
down_revision: Union[str, Sequence[str], None] = 'be602279af75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def migrate_legacy_setup_state() -> None:
    """
    Migrate data from legacy setup_state.json file to database.

    Looks for setup state in:
    1. ~/.giljo-mcp/setup_state.json
    2. Current directory config.yaml (for setup info)

    If found, creates a SetupState row with migrated data.
    """
    legacy_file = Path.home() / ".giljo-mcp" / "setup_state.json"

    if not legacy_file.exists():
        logger.info("No legacy setup_state.json found - skipping data migration")
        return

    try:
        with open(legacy_file, 'r') as f:
            legacy_data = json.load(f)

        logger.info(f"Found legacy setup state: {legacy_data}")

        # Use a default tenant_key for single-tenant legacy installations
        tenant_key = legacy_data.get("tenant_key", "default")

        # Prepare data for insert
        setup_state_data = {
            "tenant_key": tenant_key,
            "completed": legacy_data.get("completed", False),
            "completed_at": legacy_data.get("completed_at"),
            "setup_version": legacy_data.get("setup_version"),
            "database_version": legacy_data.get("database_version"),
            "python_version": legacy_data.get("python_version"),
            "node_version": legacy_data.get("node_version"),
            "features_configured": json.dumps(legacy_data.get("features_configured", {})),
            "tools_enabled": json.dumps(legacy_data.get("tools_enabled", [])),
            "config_snapshot": json.dumps(legacy_data.get("config_snapshot")) if legacy_data.get("config_snapshot") else None,
            "validation_passed": legacy_data.get("validation_passed", True),
            "validation_failures": json.dumps(legacy_data.get("validation_failures", [])),
            "validation_warnings": json.dumps(legacy_data.get("validation_warnings", [])),
            "installer_version": legacy_data.get("installer_version"),
            "install_mode": legacy_data.get("install_mode"),
            "install_path": legacy_data.get("install_path"),
            "meta_data": json.dumps(legacy_data.get("meta_data", {})),
        }

        # Insert into database
        conn = op.get_bind()
        conn.execute(
            sa.text("""
                INSERT INTO setup_state (
                    tenant_key, completed, completed_at, setup_version, database_version,
                    python_version, node_version, features_configured, tools_enabled,
                    config_snapshot, validation_passed, validation_failures, validation_warnings,
                    installer_version, install_mode, install_path, meta_data
                )
                VALUES (
                    :tenant_key, :completed, :completed_at, :setup_version, :database_version,
                    :python_version, :node_version, :features_configured::jsonb, :tools_enabled::jsonb,
                    :config_snapshot::jsonb, :validation_passed, :validation_failures::jsonb,
                    :validation_warnings::jsonb, :installer_version, :install_mode, :install_path,
                    :meta_data::jsonb
                )
                ON CONFLICT (tenant_key) DO NOTHING
            """),
            setup_state_data
        )

        logger.info(f"Successfully migrated legacy setup state for tenant: {tenant_key}")

        # Optionally backup and remove legacy file
        backup_file = legacy_file.with_suffix(".json.backup")
        legacy_file.rename(backup_file)
        logger.info(f"Backed up legacy file to: {backup_file}")

    except Exception as e:
        logger.warning(f"Failed to migrate legacy setup state: {e}")
        # Don't fail the migration if legacy data can't be migrated


def upgrade() -> None:
    """
    Upgrade schema - create setup_state table and migrate legacy data.

    Creates:
    - setup_state table with JSONB columns and constraints
    - Regular B-tree indexes for tenant_key, completed, install_mode
    - GIN indexes for JSONB columns (features_configured, tools_enabled)
    - Partial index for incomplete setups
    - CHECK constraints for version format and data integrity

    Then attempts to migrate data from legacy setup_state.json if present.
    """
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('setup_state',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('tenant_key', sa.String(length=36), nullable=False),
    sa.Column('completed', sa.Boolean(), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('setup_version', sa.String(length=20), nullable=True),
    sa.Column('database_version', sa.String(length=20), nullable=True),
    sa.Column('python_version', sa.String(length=20), nullable=True),
    sa.Column('node_version', sa.String(length=20), nullable=True),
    sa.Column('features_configured', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Nested dict of configured features: {database: true, api: {enabled: true, port: 7272}}'),
    sa.Column('tools_enabled', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Array of enabled MCP tool names'),
    sa.Column('config_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Snapshot of config.yaml at setup completion'),
    sa.Column('validation_passed', sa.Boolean(), nullable=False),
    sa.Column('validation_failures', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Array of validation failure messages'),
    sa.Column('validation_warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Array of validation warning messages'),
    sa.Column('last_validation_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('installer_version', sa.String(length=20), nullable=True),
    sa.Column('install_mode', sa.String(length=20), nullable=True, comment='Installation mode: localhost, server, lan, wan'),
    sa.Column('install_path', sa.Text(), nullable=True, comment='Installation directory path'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.CheckConstraint("database_version IS NULL OR database_version ~ '^[0-9]+(\\.([0-9]+|[0-9]+\\.[0-9]+))?$'", name='ck_database_version_format'),
    sa.CheckConstraint("install_mode IS NULL OR install_mode IN ('localhost', 'server', 'lan', 'wan')", name='ck_install_mode_values'),
    sa.CheckConstraint("setup_version IS NULL OR setup_version ~ '^[0-9]+\\.[0-9]+\\.[0-9]+(-[a-zA-Z0-9\\.\\-]+)?$'", name='ck_setup_version_format'),
    sa.CheckConstraint('(completed = false) OR (completed = true AND completed_at IS NOT NULL)', name='ck_completed_at_required'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_setup_completed', 'setup_state', ['completed'], unique=False)
    op.create_index('idx_setup_features_gin', 'setup_state', ['features_configured'], unique=False, postgresql_using='gin')
    op.create_index('idx_setup_incomplete', 'setup_state', ['tenant_key', 'completed'], unique=False, postgresql_where='completed = false')
    op.create_index('idx_setup_mode', 'setup_state', ['install_mode'], unique=False)
    op.create_index('idx_setup_tenant', 'setup_state', ['tenant_key'], unique=False)
    op.create_index('idx_setup_tools_gin', 'setup_state', ['tools_enabled'], unique=False, postgresql_using='gin')
    op.create_index(op.f('ix_setup_state_completed'), 'setup_state', ['completed'], unique=False)
    op.create_index(op.f('ix_setup_state_tenant_key'), 'setup_state', ['tenant_key'], unique=True)
    # ### end Alembic commands ###

    # Migrate legacy data if present
    logger.info("Checking for legacy setup state data to migrate...")
    migrate_legacy_setup_state()


def downgrade() -> None:
    """
    Downgrade schema - drop setup_state table.

    WARNING: This will permanently delete all setup state data.
    The legacy setup_state.json file (if backed up) will NOT be restored automatically.
    You may need to manually restore from the .backup file if needed.
    """
    logger.warning("Dropping setup_state table - all setup state data will be lost!")
    logger.warning("Legacy setup_state.json.backup file (if exists) must be manually restored.")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_setup_state_tenant_key'), table_name='setup_state')
    op.drop_index(op.f('ix_setup_state_completed'), table_name='setup_state')
    op.drop_index('idx_setup_tools_gin', table_name='setup_state', postgresql_using='gin')
    op.drop_index('idx_setup_tenant', table_name='setup_state')
    op.drop_index('idx_setup_mode', table_name='setup_state')
    op.drop_index('idx_setup_incomplete', table_name='setup_state', postgresql_where='completed = false')
    op.drop_index('idx_setup_features_gin', table_name='setup_state', postgresql_using='gin')
    op.drop_index('idx_setup_completed', table_name='setup_state')
    op.drop_table('setup_state')
    # ### end Alembic commands ###
