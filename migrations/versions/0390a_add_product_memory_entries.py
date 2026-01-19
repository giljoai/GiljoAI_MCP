"""Add product_memory_entries table (Handover 0390a)

Revision ID: 0390a_memory_entries
Revises: 0387i_deprecate
Create Date: 2026-01-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0390a_memory_entries'
down_revision = '0387i_deprecate'
branch_labels = None
depends_on = None


def upgrade():
    # Create table
    op.create_table(
        'product_memory_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_key', sa.String(36), nullable=False),
        sa.Column('product_id', sa.String(36), sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),

        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('entry_type', sa.String(50), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),

        sa.Column('project_name', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_outcomes', postgresql.JSONB(), server_default='[]'),
        sa.Column('decisions_made', postgresql.JSONB(), server_default='[]'),
        sa.Column('git_commits', postgresql.JSONB(), server_default='[]'),

        sa.Column('deliverables', postgresql.JSONB(), server_default='[]'),
        sa.Column('metrics', postgresql.JSONB(), server_default='{}'),
        sa.Column('priority', sa.Integer(), server_default='3'),
        sa.Column('significance_score', sa.Float(), server_default='0.5'),
        sa.Column('token_estimate', sa.Integer(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), server_default='[]'),

        sa.Column('author_job_id', sa.String(36), nullable=True),
        sa.Column('author_name', sa.String(255), nullable=True),
        sa.Column('author_type', sa.String(50), nullable=True),

        sa.Column('deleted_by_user', sa.Boolean(), server_default='false'),
        sa.Column('user_deleted_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),

        sa.UniqueConstraint('product_id', 'sequence', name='uq_product_sequence'),
    )

    # Create indexes
    op.create_index('idx_pme_tenant_product', 'product_memory_entries', ['tenant_key', 'product_id'])
    op.create_index('idx_pme_project', 'product_memory_entries', ['project_id'], postgresql_where=sa.text('project_id IS NOT NULL'))
    op.create_index('idx_pme_sequence', 'product_memory_entries', ['product_id', 'sequence'])
    op.create_index('idx_pme_type', 'product_memory_entries', ['entry_type'])
    op.create_index('idx_pme_deleted', 'product_memory_entries', ['deleted_by_user'], postgresql_where=sa.text('deleted_by_user = true'))

    # Backfill from JSONB
    op.execute("""
        INSERT INTO product_memory_entries (
            tenant_key, product_id, project_id, sequence, entry_type, source, timestamp,
            project_name, summary, key_outcomes, decisions_made, git_commits,
            deliverables, metrics, priority, significance_score, token_estimate, tags,
            author_job_id, author_name, author_type,
            deleted_by_user, user_deleted_at, created_at, updated_at
        )
        SELECT
            p.tenant_key,
            p.id AS product_id,
            CASE
                WHEN entry->>'project_id' IS NOT NULL
                    AND entry->>'project_id' != 'null'
                    AND EXISTS (SELECT 1 FROM projects WHERE id = entry->>'project_id')
                THEN entry->>'project_id'
                ELSE NULL
            END AS project_id,
            (entry->>'sequence')::integer AS sequence,
            COALESCE(entry->>'type', 'project_completion') AS entry_type,
            COALESCE(entry->>'source', 'migration_backfill') AS source,
            COALESCE(
                (entry->>'timestamp')::timestamp with time zone,
                NOW()
            ) AS timestamp,
            entry->>'project_name' AS project_name,
            entry->>'summary' AS summary,
            COALESCE(entry->'key_outcomes', '[]'::jsonb) AS key_outcomes,
            COALESCE(entry->'decisions_made', '[]'::jsonb) AS decisions_made,
            COALESCE(entry->'git_commits', '[]'::jsonb) AS git_commits,
            COALESCE(entry->'deliverables', '[]'::jsonb) AS deliverables,
            COALESCE(entry->'metrics', '{}'::jsonb) AS metrics,
            COALESCE((entry->>'priority')::integer, 3) AS priority,
            COALESCE((entry->>'significance_score')::float, 0.5) AS significance_score,
            (entry->>'token_estimate')::integer AS token_estimate,
            COALESCE(entry->'tags', '[]'::jsonb) AS tags,
            CASE
                WHEN entry->>'author_job_id' IS NOT NULL AND entry->>'author_job_id' != 'null'
                THEN entry->>'author_job_id'
                ELSE NULL
            END AS author_job_id,
            entry->>'author_name' AS author_name,
            entry->>'author_type' AS author_type,
            COALESCE((entry->>'deleted_by_user')::boolean, false) AS deleted_by_user,
            (entry->>'user_deleted_at')::timestamp with time zone AS user_deleted_at,
            NOW() AS created_at,
            NOW() AS updated_at
        FROM products p,
        LATERAL jsonb_array_elements(
            COALESCE(p.product_memory->'sequential_history', '[]'::jsonb)
        ) AS entry
        WHERE p.product_memory IS NOT NULL
          AND jsonb_array_length(COALESCE(p.product_memory->'sequential_history', '[]'::jsonb)) > 0
    """)


def downgrade():
    op.drop_table('product_memory_entries')
