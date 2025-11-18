"""Create 14 missing base tables for fresh installations

This migration creates 14 tables that exist in SQLAlchemy models but were never created
by Alembic migrations. The old install.py used create_all() to create missing tables,
but the new v3.1.0 install.py uses ONLY Alembic, exposing this gap.

Tables created (in dependency order):

Phase 1 - Independent Tables (no foreign keys):
1. settings - JSONB tenant-scoped system settings
2. download_tokens - Secure file download token management
3. git_configs - Git repository configuration per product
4. optimization_rules - Serena MCP optimization rules
5. optimization_metrics - Serena MCP context efficiency metrics tracking

Phase 2 - Product-Dependent:
6. vision_documents - Multi-vision document storage (FK: products)

Phase 3 - Project-Dependent:
7. mcp_agent_jobs - Agent coordination and lifecycle (FK: projects)
8. context_index - Fast navigation for chunked documents (FK: projects)
9. large_document_index - Document metadata for large files (FK: projects)
10. discovery_config - Dynamic path overrides per project (FK: projects)
11. git_commits - Git commit audit trail (FK: projects)
12. sessions - HTTP MCP session tracking (FK: projects)

Phase 4 - Cross-Dependent:
13. mcp_context_index - Chunked vision documents for RAG (FK: vision_documents, products)
14. mcp_context_summary - Condensed missions for context prioritization (FK: products)

Safety features:
- IF NOT EXISTS clauses (safe on fresh AND existing databases)
- Transaction-wrapped operations with rollback on error
- Progress logging for installation visibility
- Complete downgrade() support with CASCADE drops
- Multi-tenant indexes on all tenant_key columns
- GIN indexes for JSONB columns
- CHECK constraints for data integrity

Revision ID: 20251114_create_missing
Revises: 00450fa7780c
Create Date: 2025-11-14
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "20251114_create_missing"
down_revision: Union[str, Sequence[str], None] = "00450fa7780c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create 14 missing base tables in dependency order."""
    conn = op.get_bind()

    try:
        print("\n=== Creating 14 missing base tables ===\n")

        # ============================================================================
        # PHASE 1: Independent Tables (no foreign keys)
        # ============================================================================

        print("Phase 1/4: Creating independent tables...")

        # 1. settings
        print("  [1/14] Creating settings table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS settings (
                id VARCHAR(36) PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                category VARCHAR(50) NOT NULL,
                settings_data JSONB NOT NULL DEFAULT '{}',
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT uq_settings_tenant_category UNIQUE (tenant_key, category)
            );

            COMMENT ON TABLE settings IS 'JSONB storage for tenant-scoped system settings';
            COMMENT ON COLUMN settings.category IS 'Setting category: general, network, database';
            COMMENT ON COLUMN settings.settings_data IS 'Flexible JSONB for easy schema evolution';

            CREATE INDEX IF NOT EXISTS idx_settings_tenant ON settings(tenant_key);
            CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);
            CREATE INDEX IF NOT EXISTS idx_settings_data_gin ON settings USING gin(settings_data);
        """))

        # 2. download_tokens
        print("  [2/14] Creating download_tokens table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS download_tokens (
                id SERIAL PRIMARY KEY,
                token VARCHAR(36) UNIQUE NOT NULL,
                tenant_key VARCHAR(36) NOT NULL,
                download_type VARCHAR(50) NOT NULL,
                meta_data JSONB NOT NULL DEFAULT '{}',
                is_used BOOLEAN NOT NULL DEFAULT FALSE,
                downloaded_at TIMESTAMP WITH TIME ZONE,
                staging_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                staging_error TEXT,
                download_count INTEGER NOT NULL DEFAULT 0,
                last_downloaded_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

                CONSTRAINT ck_download_token_type CHECK (download_type IN ('slash_commands', 'agent_templates')),
                CONSTRAINT ck_download_token_staging_status CHECK (staging_status IN ('pending', 'ready', 'failed'))
            );

            COMMENT ON TABLE download_tokens IS 'Secure file download token management with lifecycle tracking';
            COMMENT ON COLUMN download_tokens.token IS 'UUID v4 token used in download URL';
            COMMENT ON COLUMN download_tokens.tenant_key IS 'Tenant key for multi-tenant isolation';
            COMMENT ON COLUMN download_tokens.staging_status IS 'Staging lifecycle status: pending|ready|failed';
            COMMENT ON COLUMN download_tokens.download_count IS 'Number of successful downloads for this token';

            CREATE INDEX IF NOT EXISTS idx_download_token_token ON download_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_download_token_tenant ON download_tokens(tenant_key);
            CREATE INDEX IF NOT EXISTS idx_download_token_expires ON download_tokens(expires_at);
            CREATE INDEX IF NOT EXISTS idx_download_token_tenant_type ON download_tokens(tenant_key, download_type);
            CREATE INDEX IF NOT EXISTS idx_download_token_meta_gin ON download_tokens USING gin(meta_data);
        """))

        # 3. git_configs
        print("  [3/14] Creating git_configs table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS git_configs (
                id VARCHAR(36) PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                product_id VARCHAR(36) NOT NULL,
                repo_url VARCHAR(500) NOT NULL,
                branch VARCHAR(100) DEFAULT 'main',
                remote_name VARCHAR(50) DEFAULT 'origin',
                auth_method VARCHAR(20) NOT NULL,
                username VARCHAR(100),
                password_encrypted TEXT,
                ssh_key_path VARCHAR(500),
                ssh_key_encrypted TEXT,
                auto_commit BOOLEAN DEFAULT TRUE,
                auto_push BOOLEAN DEFAULT FALSE,
                commit_message_template TEXT,
                webhook_url VARCHAR(500),
                webhook_secret VARCHAR(255),
                webhook_events JSON DEFAULT '[]',
                ignore_patterns JSON DEFAULT '[]',
                git_config_options JSON DEFAULT '{}',
                is_active BOOLEAN DEFAULT TRUE,
                last_commit_hash VARCHAR(40),
                last_push_at TIMESTAMP WITH TIME ZONE,
                last_error TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE,
                verified_at TIMESTAMP WITH TIME ZONE,
                meta_data JSON DEFAULT '{}',

                CONSTRAINT uq_git_config_product UNIQUE (product_id),
                CONSTRAINT ck_git_config_auth_method CHECK (auth_method IN ('https', 'ssh', 'token'))
            );

            COMMENT ON TABLE git_configs IS 'Git repository configuration per product for version control integration';

            CREATE INDEX IF NOT EXISTS idx_git_config_tenant ON git_configs(tenant_key);
            CREATE INDEX IF NOT EXISTS idx_git_config_product ON git_configs(product_id);
            CREATE INDEX IF NOT EXISTS idx_git_config_active ON git_configs(is_active);
            CREATE INDEX IF NOT EXISTS idx_git_config_auth ON git_configs(auth_method);
        """))

        # 4. optimization_rules
        print("  [4/14] Creating optimization_rules table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS optimization_rules (
                id VARCHAR(36) PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                operation_type VARCHAR(50) NOT NULL,
                max_answer_chars INTEGER NOT NULL,
                prefer_symbolic BOOLEAN NOT NULL DEFAULT TRUE,
                guidance TEXT NOT NULL,
                context_filter VARCHAR(100),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                priority INTEGER DEFAULT 100,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE,

                CONSTRAINT ck_optimization_rule_operation_type CHECK (
                    operation_type IN ('file_read', 'symbol_search', 'symbol_replace', 'pattern_search', 'directory_list')
                ),
                CONSTRAINT ck_optimization_rule_max_chars CHECK (max_answer_chars > 0),
                CONSTRAINT ck_optimization_rule_priority CHECK (priority >= 0)
            );

            COMMENT ON TABLE optimization_rules IS 'Custom optimization rules per tenant for Serena MCP operations';

            CREATE INDEX IF NOT EXISTS idx_optimization_rule_tenant ON optimization_rules(tenant_key);
            CREATE INDEX IF NOT EXISTS idx_optimization_rule_type ON optimization_rules(operation_type);
            CREATE INDEX IF NOT EXISTS idx_optimization_rule_active ON optimization_rules(is_active);
        """))

        # 5. optimization_metrics
        print("  [5/14] Creating optimization_metrics table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS optimization_metrics (
                id VARCHAR(36) PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                operation_type VARCHAR(50) NOT NULL,
                params_size INTEGER NOT NULL DEFAULT 0,
                result_size INTEGER NOT NULL,
                optimized BOOLEAN NOT NULL DEFAULT TRUE,
                tokens_saved INTEGER NOT NULL DEFAULT 0,
                meta_data JSON DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT ck_optimization_metric_operation_type CHECK (
                    operation_type IN ('file_read', 'symbol_search', 'symbol_replace', 'pattern_search', 'directory_list')
                ),
                CONSTRAINT ck_optimization_metric_params_size CHECK (params_size >= 0),
                CONSTRAINT ck_optimization_metric_result_size CHECK (result_size >= 0),
                CONSTRAINT ck_optimization_metric_tokens_saved CHECK (tokens_saved >= 0)
            );

            COMMENT ON TABLE optimization_metrics IS 'Tracks context efficiency metrics from Serena MCP optimizations for analytics';

            CREATE INDEX IF NOT EXISTS idx_optimization_metric_tenant ON optimization_metrics(tenant_key);
            CREATE INDEX IF NOT EXISTS idx_optimization_metric_type ON optimization_metrics(operation_type);
            CREATE INDEX IF NOT EXISTS idx_optimization_metric_date ON optimization_metrics(created_at);
            CREATE INDEX IF NOT EXISTS idx_optimization_metric_optimized ON optimization_metrics(optimized);
        """))

        print("Phase 1 complete: 5/14 tables created\n")

        # ============================================================================
        # PHASE 2: Product-Dependent Tables
        # ============================================================================

        print("Phase 2/4: Creating product-dependent tables...")

        # 6. vision_documents
        print("  [6/14] Creating vision_documents table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vision_documents (
                id VARCHAR(36) PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                product_id VARCHAR(36) NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                document_name VARCHAR(255) NOT NULL,
                document_type VARCHAR(50) NOT NULL DEFAULT 'vision',
                vision_path VARCHAR(500),
                vision_document TEXT,
                storage_type VARCHAR(20) NOT NULL DEFAULT 'file',
                chunked BOOLEAN NOT NULL DEFAULT FALSE,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER,
                file_size BIGINT,
                version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
                content_hash VARCHAR(64),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                display_order INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE,
                meta_data JSON DEFAULT '{}',

                CONSTRAINT uq_vision_doc_product_name UNIQUE (product_id, document_name),
                CONSTRAINT ck_vision_doc_storage_type CHECK (storage_type IN ('file', 'inline', 'hybrid')),
                CONSTRAINT ck_vision_doc_document_type CHECK (
                    document_type IN ('vision', 'architecture', 'features', 'setup', 'api', 'testing', 'deployment', 'custom')
                ),
                CONSTRAINT ck_vision_doc_storage_consistency CHECK (
                    (storage_type = 'file' AND vision_path IS NOT NULL) OR
                    (storage_type = 'inline' AND vision_document IS NOT NULL) OR
                    (storage_type = 'hybrid' AND vision_path IS NOT NULL AND vision_document IS NOT NULL)
                ),
                CONSTRAINT ck_vision_doc_chunk_count CHECK (chunk_count >= 0),
                CONSTRAINT ck_vision_doc_chunked_consistency CHECK (
                    (chunked = false AND chunk_count = 0) OR (chunked = true AND chunk_count > 0)
                )
            );

            COMMENT ON TABLE vision_documents IS 'Multi-vision document storage with chunking, versioning, and flexible storage';
            COMMENT ON COLUMN vision_documents.document_name IS 'User-friendly document name';
            COMMENT ON COLUMN vision_documents.document_type IS 'Document category: vision, architecture, features, etc.';
            COMMENT ON COLUMN vision_documents.storage_type IS 'Storage mode: file, inline, or hybrid';
            COMMENT ON COLUMN vision_documents.chunked IS 'Has document been chunked into mcp_context_index for RAG';

            CREATE INDEX IF NOT EXISTS idx_vision_doc_tenant ON vision_documents(tenant_key);
            CREATE INDEX IF NOT EXISTS idx_vision_doc_product ON vision_documents(product_id);
            CREATE INDEX IF NOT EXISTS idx_vision_doc_type ON vision_documents(document_type);
            CREATE INDEX IF NOT EXISTS idx_vision_doc_active ON vision_documents(is_active);
            CREATE INDEX IF NOT EXISTS idx_vision_doc_chunked ON vision_documents(chunked);
            CREATE INDEX IF NOT EXISTS idx_vision_doc_tenant_product ON vision_documents(tenant_key, product_id);
            CREATE INDEX IF NOT EXISTS idx_vision_doc_product_type ON vision_documents(product_id, document_type);
            CREATE INDEX IF NOT EXISTS idx_vision_doc_product_active ON vision_documents(product_id, is_active, display_order);
        """))

        print("Phase 2 complete: 6/14 tables created\n")

        # ============================================================================
        # PHASE 3: Project-Dependent Tables
        # ============================================================================

        print("Phase 3/4: Creating project-dependent tables...")

        # 7. mcp_agent_jobs
        print("  [7/14] Creating mcp_agent_jobs table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mcp_agent_jobs (
                id SERIAL PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                project_id VARCHAR(36) REFERENCES projects(id),
                job_id VARCHAR(36) UNIQUE NOT NULL,
                agent_type VARCHAR(100) NOT NULL,
                mission TEXT NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'waiting',
                failure_reason VARCHAR(50),
                spawned_by VARCHAR(36),
                context_chunks JSON DEFAULT '[]',
                messages JSONB DEFAULT '[]',
                acknowledged BOOLEAN DEFAULT FALSE,
                started_at TIMESTAMP WITH TIME ZONE,
                completed_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                progress INTEGER NOT NULL DEFAULT 0,
                block_reason TEXT,
                current_task TEXT,
                estimated_completion TIMESTAMP WITH TIME ZONE,
                tool_type VARCHAR(20) NOT NULL DEFAULT 'universal',
                agent_name VARCHAR(255),
                instance_number INTEGER NOT NULL DEFAULT 1,
                handover_to VARCHAR(36),
                handover_summary JSONB,
                handover_context_refs JSON DEFAULT '[]',
                succession_reason VARCHAR(100),
                context_used INTEGER NOT NULL DEFAULT 0,
                context_budget INTEGER NOT NULL DEFAULT 150000,
                job_metadata JSONB NOT NULL DEFAULT '{}',
                last_health_check TIMESTAMP WITH TIME ZONE,
                health_status VARCHAR(20) NOT NULL DEFAULT 'unknown',
                health_failure_count INTEGER NOT NULL DEFAULT 0,
                last_progress_at TIMESTAMP WITH TIME ZONE,
                last_message_check_at TIMESTAMP WITH TIME ZONE,
                decommissioned_at TIMESTAMP WITH TIME ZONE,

                CONSTRAINT ck_mcp_agent_job_status CHECK (
                    status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned')
                ),
                CONSTRAINT ck_mcp_agent_job_progress_range CHECK (progress >= 0 AND progress <= 100),
                CONSTRAINT ck_mcp_agent_job_failure_reason CHECK (
                    failure_reason IS NULL OR failure_reason IN ('error', 'timeout', 'system_error')
                ),
                CONSTRAINT ck_mcp_agent_job_tool_type CHECK (tool_type IN ('claude-code', 'codex', 'gemini', 'universal')),
                CONSTRAINT ck_mcp_agent_job_instance_positive CHECK (instance_number >= 1),
                CONSTRAINT ck_mcp_agent_job_succession_reason CHECK (
                    succession_reason IS NULL OR succession_reason IN ('context_limit', 'manual', 'phase_transition')
                ),
                CONSTRAINT ck_mcp_agent_job_context_usage CHECK (context_used >= 0 AND context_used <= context_budget),
                CONSTRAINT ck_mcp_agent_job_health_status CHECK (
                    health_status IN ('unknown', 'healthy', 'warning', 'critical', 'timeout')
                ),
                CONSTRAINT ck_mcp_agent_job_health_failure_count CHECK (health_failure_count >= 0)
            );

            COMMENT ON TABLE mcp_agent_jobs IS 'Agent coordination and lifecycle tracking with orchestrator succession support';
            COMMENT ON COLUMN mcp_agent_jobs.agent_type IS 'Agent type: orchestrator, analyzer, implementer, tester, etc.';
            COMMENT ON COLUMN mcp_agent_jobs.mission IS 'Agent mission/instructions';
            COMMENT ON COLUMN mcp_agent_jobs.instance_number IS 'Sequential instance number for orchestrator succession';

            CREATE INDEX IF NOT EXISTS idx_mcp_agent_jobs_tenant_status ON mcp_agent_jobs(tenant_key, status);
            CREATE INDEX IF NOT EXISTS idx_mcp_agent_jobs_tenant_type ON mcp_agent_jobs(tenant_key, agent_type);
            CREATE INDEX IF NOT EXISTS idx_mcp_agent_jobs_job_id ON mcp_agent_jobs(job_id);
            CREATE INDEX IF NOT EXISTS idx_mcp_agent_jobs_project ON mcp_agent_jobs(project_id);
            CREATE INDEX IF NOT EXISTS idx_mcp_agent_jobs_tenant_project ON mcp_agent_jobs(tenant_key, project_id);
            CREATE INDEX IF NOT EXISTS idx_mcp_agent_jobs_tenant_tool ON mcp_agent_jobs(tenant_key, tool_type);
            CREATE INDEX IF NOT EXISTS idx_agent_jobs_instance ON mcp_agent_jobs(project_id, agent_type, instance_number);
            CREATE INDEX IF NOT EXISTS idx_agent_jobs_handover ON mcp_agent_jobs(handover_to);
            CREATE INDEX IF NOT EXISTS idx_mcp_agent_jobs_messages_gin ON mcp_agent_jobs USING gin(messages);
            CREATE INDEX IF NOT EXISTS idx_mcp_agent_jobs_metadata_gin ON mcp_agent_jobs USING gin(job_metadata);
        """))

        # 8. context_index
        print("  [8/14] Creating context_index table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS context_index (
                id VARCHAR(36) PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
                index_type VARCHAR(50) NOT NULL,
                document_name VARCHAR(255) NOT NULL,
                section_name VARCHAR(255),
                chunk_numbers JSON DEFAULT '[]',
                summary TEXT,
                token_count INTEGER,
                keywords JSON DEFAULT '[]',
                full_path TEXT,
                content_hash VARCHAR(32),
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE,

                CONSTRAINT uq_context_index UNIQUE (project_id, document_name, section_name)
            );

            COMMENT ON TABLE context_index IS 'Fast navigation for chunked documents with O(1) retrieval';

            CREATE INDEX IF NOT EXISTS idx_context_tenant ON context_index(tenant_key);
            CREATE INDEX IF NOT EXISTS idx_context_type ON context_index(index_type);
            CREATE INDEX IF NOT EXISTS idx_context_doc ON context_index(document_name);
        """))

        # 9. large_document_index
        print("  [9/14] Creating large_document_index table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS large_document_index (
                id VARCHAR(36) PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
                document_path TEXT NOT NULL,
                document_type VARCHAR(50),
                total_size INTEGER,
                total_tokens INTEGER,
                chunk_count INTEGER,
                meta_data JSON DEFAULT '{}',
                indexed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT uq_large_doc_path UNIQUE (project_id, document_path)
            );

            COMMENT ON TABLE large_document_index IS 'Document metadata for files requiring chunking (over 50K tokens)';

            CREATE INDEX IF NOT EXISTS idx_large_doc_tenant ON large_document_index(tenant_key);
        """))

        # 10. discovery_config
        print("  [10/14] Creating discovery_config table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS discovery_config (
                id VARCHAR(36) PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
                path_key VARCHAR(50) NOT NULL,
                path_value TEXT NOT NULL,
                priority INTEGER DEFAULT 0,
                enabled BOOLEAN DEFAULT TRUE,
                settings JSON DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE,

                CONSTRAINT uq_discovery_path UNIQUE (project_id, path_key)
            );

            COMMENT ON TABLE discovery_config IS 'Dynamic path overrides and discovery settings per project';

            CREATE INDEX IF NOT EXISTS idx_discovery_tenant ON discovery_config(tenant_key);
            CREATE INDEX IF NOT EXISTS idx_discovery_project ON discovery_config(project_id);
        """))

        # 11. git_commits
        print("  [11/14] Creating git_commits table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS git_commits (
                id VARCHAR(36) PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                product_id VARCHAR(36) NOT NULL,
                project_id VARCHAR(36) REFERENCES projects(id),
                commit_hash VARCHAR(40) UNIQUE NOT NULL,
                commit_message TEXT NOT NULL,
                author_name VARCHAR(100) NOT NULL,
                author_email VARCHAR(255) NOT NULL,
                branch_name VARCHAR(100) NOT NULL,
                files_changed JSON DEFAULT '[]',
                insertions INTEGER DEFAULT 0,
                deletions INTEGER DEFAULT 0,
                triggered_by VARCHAR(50),
                commit_type VARCHAR(50),
                push_status VARCHAR(20) DEFAULT 'pending',
                push_error TEXT,
                webhook_triggered BOOLEAN DEFAULT FALSE,
                webhook_response JSON,
                committed_at TIMESTAMP WITH TIME ZONE NOT NULL,
                pushed_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                meta_data JSON DEFAULT '{}',

                CONSTRAINT ck_git_commit_push_status CHECK (push_status IN ('pending', 'pushed', 'failed'))
            );

            COMMENT ON TABLE git_commits IS 'Git commit audit trail for orchestrator-managed commits';

            CREATE INDEX IF NOT EXISTS idx_git_commit_tenant ON git_commits(tenant_key);
            CREATE INDEX IF NOT EXISTS idx_git_commit_product ON git_commits(product_id);
            CREATE INDEX IF NOT EXISTS idx_git_commit_project ON git_commits(project_id);
            CREATE INDEX IF NOT EXISTS idx_git_commit_hash ON git_commits(commit_hash);
            CREATE INDEX IF NOT EXISTS idx_git_commit_date ON git_commits(committed_at);
            CREATE INDEX IF NOT EXISTS idx_git_commit_trigger ON git_commits(triggered_by);
        """))

        # 12. sessions (MCP sessions, not project sessions)
        print("  [12/14] Creating sessions table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sessions (
                id VARCHAR(36) PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
                session_number INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                objectives TEXT,
                outcomes TEXT,
                decisions JSON DEFAULT '[]',
                blockers JSON DEFAULT '[]',
                next_steps JSON DEFAULT '[]',
                started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP WITH TIME ZONE,
                duration_minutes INTEGER,
                meta_data JSON DEFAULT '{}',

                CONSTRAINT uq_session_project_number UNIQUE (project_id, session_number)
            );

            COMMENT ON TABLE sessions IS 'Development session tracking with objectives, outcomes, and decisions';

            CREATE INDEX IF NOT EXISTS idx_session_tenant ON sessions(tenant_key);
            CREATE INDEX IF NOT EXISTS idx_session_project ON sessions(project_id);
        """))

        print("Phase 3 complete: 12/14 tables created\n")

        # ============================================================================
        # PHASE 4: Cross-Dependent Tables
        # ============================================================================

        print("Phase 4/4: Creating cross-dependent tables...")

        # 13. mcp_context_index
        print("  [13/14] Creating mcp_context_index table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mcp_context_index (
                id SERIAL PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                chunk_id VARCHAR(36) UNIQUE NOT NULL,
                product_id VARCHAR(36) REFERENCES products(id) ON DELETE CASCADE,
                vision_document_id VARCHAR(36) REFERENCES vision_documents(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                summary TEXT,
                keywords JSON DEFAULT '[]',
                token_count INTEGER,
                chunk_order INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                searchable_vector TSVECTOR,

                CONSTRAINT ck_mcp_context_index_chunk_order CHECK (chunk_order >= 0 OR chunk_order IS NULL)
            );

            COMMENT ON TABLE mcp_context_index IS 'Chunked vision documents for agentic RAG with full-text search';
            COMMENT ON COLUMN mcp_context_index.vision_document_id IS 'Link to specific vision document (NULL for legacy chunks)';
            COMMENT ON COLUMN mcp_context_index.summary IS 'Optional LLM-generated summary';
            COMMENT ON COLUMN mcp_context_index.searchable_vector IS 'Full-text search vector for fast keyword lookup';

            CREATE INDEX IF NOT EXISTS idx_mcp_context_tenant_product ON mcp_context_index(tenant_key, product_id);
            CREATE INDEX IF NOT EXISTS idx_mcp_context_searchable ON mcp_context_index USING gin(searchable_vector);
            CREATE INDEX IF NOT EXISTS idx_mcp_context_chunk_id ON mcp_context_index(chunk_id);
            CREATE INDEX IF NOT EXISTS idx_mcp_context_vision_doc ON mcp_context_index(vision_document_id);
            CREATE INDEX IF NOT EXISTS idx_mcp_context_product_vision_doc ON mcp_context_index(product_id, vision_document_id);
        """))

        # 14. mcp_context_summary
        print("  [14/14] Creating mcp_context_summary table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mcp_context_summary (
                id SERIAL PRIMARY KEY,
                tenant_key VARCHAR(36) NOT NULL,
                context_id VARCHAR(36) UNIQUE NOT NULL,
                product_id VARCHAR(36) REFERENCES products(id) ON DELETE CASCADE,
                full_content TEXT NOT NULL,
                condensed_mission TEXT NOT NULL,
                full_token_count INTEGER,
                condensed_token_count INTEGER,
                reduction_percent FLOAT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT ck_mcp_context_summary_tokens CHECK (
                    (full_token_count IS NULL AND condensed_token_count IS NULL) OR
                    (full_token_count >= condensed_token_count)
                ),
                CONSTRAINT ck_mcp_context_summary_reduction CHECK (
                    reduction_percent IS NULL OR (reduction_percent >= 0 AND reduction_percent <= 100)
                )
            );

            COMMENT ON TABLE mcp_context_summary IS 'Orchestrator-created condensed missions for context prioritization and orchestration';
            COMMENT ON COLUMN mcp_context_summary.full_content IS 'Original full context before condensation';
            COMMENT ON COLUMN mcp_context_summary.condensed_mission IS 'Orchestrator-generated condensed mission';

            CREATE INDEX IF NOT EXISTS idx_mcp_summary_tenant_product ON mcp_context_summary(tenant_key, product_id);
            CREATE INDEX IF NOT EXISTS idx_mcp_summary_context_id ON mcp_context_summary(context_id);
        """))

        print("Phase 4 complete: 14/14 tables created\n")

        # ============================================================================
        # Verification
        # ============================================================================

        print("=== Verifying table creation ===")
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN (
                'settings', 'download_tokens', 'git_configs', 'optimization_rules', 'optimization_metrics',
                'vision_documents', 'mcp_agent_jobs', 'context_index', 'large_document_index',
                'discovery_config', 'git_commits', 'sessions', 'mcp_context_index', 'mcp_context_summary'
            )
            ORDER BY table_name;
        """))

        created_tables = [row[0] for row in result]
        print(f"\nSuccessfully created {len(created_tables)} tables:")
        for table in created_tables:
            print(f"  ✓ {table}")

        if len(created_tables) == 14:
            print("\n✓ All 14 missing base tables created successfully!")
        else:
            missing = 14 - len(created_tables)
            print(f"\n⚠ Warning: Only {len(created_tables)}/14 tables created ({missing} missing)")

        print("\n=== Migration complete ===\n")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise


def downgrade() -> None:
    """Drop all 14 tables in reverse dependency order."""
    conn = op.get_bind()

    try:
        print("\n=== Dropping 14 base tables (reverse order) ===\n")

        # Phase 4: Cross-dependent tables (drop first due to FKs)
        print("Phase 1/4: Dropping cross-dependent tables...")
        conn.execute(text("DROP TABLE IF EXISTS mcp_context_summary CASCADE;"))
        print("  ✓ Dropped mcp_context_summary")

        conn.execute(text("DROP TABLE IF EXISTS mcp_context_index CASCADE;"))
        print("  ✓ Dropped mcp_context_index")

        # Phase 3: Project-dependent tables
        print("\nPhase 2/4: Dropping project-dependent tables...")
        conn.execute(text("DROP TABLE IF EXISTS sessions CASCADE;"))
        print("  ✓ Dropped sessions")

        conn.execute(text("DROP TABLE IF EXISTS git_commits CASCADE;"))
        print("  ✓ Dropped git_commits")

        conn.execute(text("DROP TABLE IF EXISTS discovery_config CASCADE;"))
        print("  ✓ Dropped discovery_config")

        conn.execute(text("DROP TABLE IF EXISTS large_document_index CASCADE;"))
        print("  ✓ Dropped large_document_index")

        conn.execute(text("DROP TABLE IF EXISTS context_index CASCADE;"))
        print("  ✓ Dropped context_index")

        conn.execute(text("DROP TABLE IF EXISTS mcp_agent_jobs CASCADE;"))
        print("  ✓ Dropped mcp_agent_jobs")

        # Phase 2: Product-dependent tables
        print("\nPhase 3/4: Dropping product-dependent tables...")
        conn.execute(text("DROP TABLE IF EXISTS vision_documents CASCADE;"))
        print("  ✓ Dropped vision_documents")

        # Phase 1: Independent tables
        print("\nPhase 4/4: Dropping independent tables...")
        conn.execute(text("DROP TABLE IF EXISTS optimization_metrics CASCADE;"))
        print("  ✓ Dropped optimization_metrics")

        conn.execute(text("DROP TABLE IF EXISTS optimization_rules CASCADE;"))
        print("  ✓ Dropped optimization_rules")

        conn.execute(text("DROP TABLE IF EXISTS git_configs CASCADE;"))
        print("  ✓ Dropped git_configs")

        conn.execute(text("DROP TABLE IF EXISTS download_tokens CASCADE;"))
        print("  ✓ Dropped download_tokens")

        conn.execute(text("DROP TABLE IF EXISTS settings CASCADE;"))
        print("  ✓ Dropped settings")

        print("\n✓ All 14 tables dropped successfully!")
        print("\n=== Downgrade complete ===\n")

    except Exception as e:
        print(f"\n❌ Downgrade failed: {e}")
        raise
