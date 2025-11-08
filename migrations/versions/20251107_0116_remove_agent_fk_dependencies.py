"""Remove agent FK dependencies (Handover 0116)

Revision ID: 20251107_0116_remove_agent_fk
Revises: 20251107_0113b_add_decommissioned_at_field
Create Date: 2025-11-07 20:53:13

This migration removes all foreign key constraints from agents.id across 6 tables,
preparing for the elimination of the legacy Agent model.

Strategy: Set all agent_id references to NULL and drop FK constraints.
This preserves historical data while breaking dependencies.

Tables modified:
1. messages.from_agent_id (nullable) - SET NULL
2. jobs.agent_id (NOT NULL → nullable) - MAKE NULLABLE, then SET NULL
3. agent_interactions.parent_agent_id (nullable) - SET NULL
4. template_usage_stats.agent_id (nullable) - SET NULL
5. git_commits.agent_id (nullable) - SET NULL
6. optimization_metrics.agent_id (NOT NULL → nullable) - MAKE NULLABLE, then SET NULL

IMPORTANT: This migration is IRREVERSIBLE. Downgrade will recreate FK constraints
but cannot restore the original agent_id values.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251107_0116_remove_agent_fk'
down_revision = '20251107_0113b_add_decommissioned_at_field'
branch_labels = None
depends_on = None


def upgrade():
    """
    Remove all FK constraints to agents.id and set agent_id columns to NULL.

    This allows the agents table to be dropped in a subsequent migration.
    """

    # Bind to current connection for logging
    bind = op.get_bind()

    print("=" * 80)
    print("HANDOVER 0116: Removing Agent FK Dependencies")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # 1. messages.from_agent_id (NULLABLE)
    # -------------------------------------------------------------------------
    print("\n[1/6] Processing messages.from_agent_id...")

    # Count affected records
    result = bind.execute(sa.text(
        "SELECT COUNT(*) FROM messages WHERE from_agent_id IS NOT NULL"
    ))
    count = result.scalar()
    print(f"  → Found {count} messages with agent references")

    # Drop FK constraint
    # Note: SQLAlchemy auto-generates constraint names, we need to find it
    result = bind.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'messages'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%from_agent%'
    """))
    constraint_name = result.scalar()

    if constraint_name:
        print(f"  → Dropping FK constraint: {constraint_name}")
        op.drop_constraint(constraint_name, 'messages', type_='foreignkey')
    else:
        print("  → No FK constraint found (may have been dropped manually)")

    # Set to NULL
    bind.execute(sa.text("UPDATE messages SET from_agent_id = NULL WHERE from_agent_id IS NOT NULL"))
    print(f"  → Set {count} records to NULL")
    print("  ✓ messages.from_agent_id complete")

    # -------------------------------------------------------------------------
    # 2. jobs.agent_id (NOT NULL → NULLABLE)
    # -------------------------------------------------------------------------
    print("\n[2/6] Processing jobs.agent_id...")

    # Count affected records
    result = bind.execute(sa.text("SELECT COUNT(*) FROM jobs"))
    count = result.scalar()
    print(f"  → Found {count} job records")

    # Drop FK constraint
    result = bind.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'jobs'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%agent%'
    """))
    constraint_name = result.scalar()

    if constraint_name:
        print(f"  → Dropping FK constraint: {constraint_name}")
        op.drop_constraint(constraint_name, 'jobs', type_='foreignkey')
    else:
        print("  → No FK constraint found (may have been dropped manually)")

    # Make column nullable
    print("  → Making agent_id nullable")
    op.alter_column('jobs', 'agent_id', nullable=True, existing_type=sa.String(36))

    # Set to NULL
    bind.execute(sa.text("UPDATE jobs SET agent_id = NULL"))
    print(f"  → Set {count} records to NULL")
    print("  ✓ jobs.agent_id complete")

    # -------------------------------------------------------------------------
    # 3. agent_interactions.parent_agent_id (NULLABLE)
    # -------------------------------------------------------------------------
    print("\n[3/6] Processing agent_interactions.parent_agent_id...")

    # Count affected records
    result = bind.execute(sa.text(
        "SELECT COUNT(*) FROM agent_interactions WHERE parent_agent_id IS NOT NULL"
    ))
    count = result.scalar()
    print(f"  → Found {count} agent interactions with parent references")

    # Drop FK constraint
    result = bind.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'agent_interactions'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%parent_agent%'
    """))
    constraint_name = result.scalar()

    if constraint_name:
        print(f"  → Dropping FK constraint: {constraint_name}")
        op.drop_constraint(constraint_name, 'agent_interactions', type_='foreignkey')
    else:
        print("  → No FK constraint found (may have been dropped manually)")

    # Set to NULL
    bind.execute(sa.text(
        "UPDATE agent_interactions SET parent_agent_id = NULL WHERE parent_agent_id IS NOT NULL"
    ))
    print(f"  → Set {count} records to NULL")
    print("  ✓ agent_interactions.parent_agent_id complete")

    # -------------------------------------------------------------------------
    # 4. template_usage_stats.agent_id (NULLABLE)
    # -------------------------------------------------------------------------
    print("\n[4/6] Processing template_usage_stats.agent_id...")

    # Count affected records
    result = bind.execute(sa.text(
        "SELECT COUNT(*) FROM template_usage_stats WHERE agent_id IS NOT NULL"
    ))
    count = result.scalar()
    print(f"  → Found {count} template usage records with agent references")

    # Drop FK constraint
    result = bind.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'template_usage_stats'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%agent%'
    """))
    constraint_name = result.scalar()

    if constraint_name:
        print(f"  → Dropping FK constraint: {constraint_name}")
        op.drop_constraint(constraint_name, 'template_usage_stats', type_='foreignkey')
    else:
        print("  → No FK constraint found (may have been dropped manually)")

    # Set to NULL
    bind.execute(sa.text(
        "UPDATE template_usage_stats SET agent_id = NULL WHERE agent_id IS NOT NULL"
    ))
    print(f"  → Set {count} records to NULL")
    print("  ✓ template_usage_stats.agent_id complete")

    # -------------------------------------------------------------------------
    # 5. git_commits.agent_id (NULLABLE)
    # -------------------------------------------------------------------------
    print("\n[5/6] Processing git_commits.agent_id...")

    # Count affected records
    result = bind.execute(sa.text(
        "SELECT COUNT(*) FROM git_commits WHERE agent_id IS NOT NULL"
    ))
    count = result.scalar()
    print(f"  → Found {count} git commits with agent references")

    # Drop FK constraint
    result = bind.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'git_commits'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%agent%'
    """))
    constraint_name = result.scalar()

    if constraint_name:
        print(f"  → Dropping FK constraint: {constraint_name}")
        op.drop_constraint(constraint_name, 'git_commits', type_='foreignkey')
    else:
        print("  → No FK constraint found (may have been dropped manually)")

    # Set to NULL
    bind.execute(sa.text(
        "UPDATE git_commits SET agent_id = NULL WHERE agent_id IS NOT NULL"
    ))
    print(f"  → Set {count} records to NULL")
    print("  ✓ git_commits.agent_id complete")

    # -------------------------------------------------------------------------
    # 6. optimization_metrics.agent_id (NOT NULL → NULLABLE)
    # -------------------------------------------------------------------------
    print("\n[6/6] Processing optimization_metrics.agent_id...")

    # Count affected records
    result = bind.execute(sa.text("SELECT COUNT(*) FROM optimization_metrics"))
    count = result.scalar()
    print(f"  → Found {count} optimization metric records")

    # Drop FK constraint
    result = bind.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'optimization_metrics'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%agent%'
    """))
    constraint_name = result.scalar()

    if constraint_name:
        print(f"  → Dropping FK constraint: {constraint_name}")
        op.drop_constraint(constraint_name, 'optimization_metrics', type_='foreignkey')
    else:
        print("  → No FK constraint found (may have been dropped manually)")

    # Make column nullable
    print("  → Making agent_id nullable")
    op.alter_column('optimization_metrics', 'agent_id', nullable=True, existing_type=sa.String(36))

    # Set to NULL
    bind.execute(sa.text("UPDATE optimization_metrics SET agent_id = NULL"))
    print(f"  → Set {count} records to NULL")
    print("  ✓ optimization_metrics.agent_id complete")

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print("All 6 FK constraints to agents.id have been removed.")
    print("All agent_id columns have been set to NULL.")
    print("The agents table can now be safely dropped in the next migration.")
    print("=" * 80 + "\n")


def downgrade():
    """
    IMPORTANT: This downgrade is PARTIAL and cannot restore original data.

    It recreates the FK constraints but all agent_id values will be NULL.
    Only use this if you need to rollback the schema structure.

    CANNOT RESTORE: Original agent_id values (set to NULL in upgrade)
    """

    print("=" * 80)
    print("HANDOVER 0116: Downgrade (PARTIAL - Data Loss Warning)")
    print("=" * 80)
    print("WARNING: This downgrade recreates FK constraints but cannot restore")
    print("         the original agent_id values. All will remain NULL.")
    print("=" * 80 + "\n")

    # Recreate FK constraints (but data will remain NULL)
    # Note: We set ondelete='SET NULL' to prevent cascade issues

    print("[1/6] Recreating messages.from_agent_id FK...")
    op.create_foreign_key(
        'fk_messages_from_agent_id',
        'messages', 'agents',
        ['from_agent_id'], ['id'],
        ondelete='SET NULL'
    )

    print("[2/6] Recreating jobs.agent_id FK (making NOT NULL)...")
    # Cannot make NOT NULL if values are NULL - this will FAIL if run
    # User must manually populate data before running this downgrade
    op.alter_column('jobs', 'agent_id', nullable=False, existing_type=sa.String(36))
    op.create_foreign_key(
        'fk_jobs_agent_id',
        'jobs', 'agents',
        ['agent_id'], ['id'],
        ondelete='CASCADE'
    )

    print("[3/6] Recreating agent_interactions.parent_agent_id FK...")
    op.create_foreign_key(
        'fk_agent_interactions_parent_agent_id',
        'agent_interactions', 'agents',
        ['parent_agent_id'], ['id'],
        ondelete='SET NULL'
    )

    print("[4/6] Recreating template_usage_stats.agent_id FK...")
    op.create_foreign_key(
        'fk_template_usage_stats_agent_id',
        'template_usage_stats', 'agents',
        ['agent_id'], ['id'],
        ondelete='SET NULL'
    )

    print("[5/6] Recreating git_commits.agent_id FK...")
    op.create_foreign_key(
        'fk_git_commits_agent_id',
        'git_commits', 'agents',
        ['agent_id'], ['id'],
        ondelete='SET NULL'
    )

    print("[6/6] Recreating optimization_metrics.agent_id FK (making NOT NULL)...")
    # Cannot make NOT NULL if values are NULL - this will FAIL if run
    # User must manually populate data before running this downgrade
    op.alter_column('optimization_metrics', 'agent_id', nullable=False, existing_type=sa.String(36))
    op.create_foreign_key(
        'fk_optimization_metrics_agent_id',
        'optimization_metrics', 'agents',
        ['agent_id'], ['id'],
        ondelete='CASCADE'
    )

    print("\n" + "=" * 80)
    print("DOWNGRADE COMPLETE (with data loss)")
    print("=" * 80)
    print("FK constraints have been recreated but agent_id values are NULL.")
    print("Manual data restoration required if needed.")
    print("=" * 80 + "\n")
