-- Migration Script v3: Restore data from pre-0424 backup to new database structure
-- Created: 2026-02-04
-- Source: giljo_mcp_backup_before_0424.dump
-- Target: giljo_mcp (new database with org_id support)
-- NOTE: Agent templates are SKIPPED due to incompatible schema changes

-- Key mappings:
-- Old tenant_key: tk_uYhgYTmdb2AJ2KRVojtjOMFsiBhRv16y
-- New tenant_key: tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO
-- New org_id: 8c57dedc-13b1-4038-9222-95d5ddac29b5

BEGIN;

-- =============================================================================
-- 1. PRODUCTS (with new org_id column)
-- =============================================================================
INSERT INTO products (
    id, tenant_key, org_id, name, description, project_path, quality_standards,
    created_at, updated_at, deleted_at, meta_data, is_active, config_data,
    product_memory, target_platforms
)
SELECT
    p.id,
    'tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO' as tenant_key,
    '8c57dedc-13b1-4038-9222-95d5ddac29b5' as org_id,
    p.name,
    p.description,
    p.project_path,
    p.quality_standards,
    p.created_at,
    p.updated_at,
    p.deleted_at,
    p.meta_data,
    p.is_active,
    p.config_data,
    p.product_memory,
    p.target_platforms
FROM dblink(
    'dbname=giljo_mcp_backup_temp user=postgres password=$DB_PASSWORD',
    'SELECT id, tenant_key, name, description, project_path, quality_standards,
            created_at, updated_at, deleted_at, meta_data, is_active, config_data,
            product_memory, target_platforms FROM products'
) AS p(
    id varchar(36), tenant_key varchar(36), name varchar(255), description text,
    project_path varchar(500), quality_standards text, created_at timestamptz,
    updated_at timestamptz, deleted_at timestamptz, meta_data json, is_active boolean,
    config_data jsonb, product_memory jsonb, target_platforms varchar[]
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- 2. VISION DOCUMENTS
-- =============================================================================
INSERT INTO vision_documents (
    id, tenant_key, product_id, document_name, document_type, vision_path,
    vision_document, storage_type, chunked, chunk_count, total_tokens, file_size,
    is_summarized, original_token_count, summary_light, summary_medium,
    summary_light_tokens, summary_medium_tokens, version, content_hash,
    is_active, display_order, created_at, updated_at, meta_data
)
SELECT
    v.id,
    'tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO' as tenant_key,
    v.product_id,
    v.document_name,
    v.document_type,
    v.vision_path,
    v.vision_document,
    v.storage_type,
    v.chunked,
    v.chunk_count,
    v.total_tokens,
    v.file_size,
    v.is_summarized,
    v.original_token_count,
    v.summary_light,
    v.summary_medium,
    v.summary_light_tokens,
    v.summary_medium_tokens,
    v.version,
    v.content_hash,
    v.is_active,
    v.display_order,
    v.created_at,
    v.updated_at,
    v.meta_data
FROM dblink(
    'dbname=giljo_mcp_backup_temp user=postgres password=$DB_PASSWORD',
    'SELECT id, tenant_key, product_id, document_name, document_type, vision_path,
            vision_document, storage_type, chunked, chunk_count, total_tokens, file_size,
            is_summarized, original_token_count, summary_light, summary_medium,
            summary_light_tokens, summary_medium_tokens, version, content_hash,
            is_active, display_order, created_at, updated_at, meta_data FROM vision_documents'
) AS v(
    id varchar(36), tenant_key varchar(36), product_id varchar(36), document_name varchar(255),
    document_type varchar(50), vision_path varchar(500), vision_document text, storage_type varchar(20),
    chunked boolean, chunk_count integer, total_tokens integer, file_size bigint,
    is_summarized boolean, original_token_count integer, summary_light text, summary_medium text,
    summary_light_tokens integer, summary_medium_tokens integer, version varchar(50),
    content_hash varchar(64), is_active boolean, display_order integer, created_at timestamptz,
    updated_at timestamptz, meta_data json
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- 3. PROJECTS (full schema match)
-- =============================================================================
INSERT INTO projects (
    id, tenant_key, product_id, name, alias, description, mission, status,
    staging_status, context_budget, context_used, created_at, updated_at,
    completed_at, activated_at, paused_at, deleted_at, meta_data,
    orchestrator_summary, closeout_prompt, closeout_executed_at, closeout_checklist,
    execution_mode
)
SELECT
    p.id,
    'tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO' as tenant_key,
    p.product_id,
    p.name,
    p.alias,
    p.description,
    p.mission,
    p.status,
    p.staging_status,
    p.context_budget,
    p.context_used,
    p.created_at,
    p.updated_at,
    p.completed_at,
    p.activated_at,
    p.paused_at,
    p.deleted_at,
    p.meta_data,
    p.orchestrator_summary,
    p.closeout_prompt,
    p.closeout_executed_at,
    p.closeout_checklist,
    p.execution_mode
FROM dblink(
    'dbname=giljo_mcp_backup_temp user=postgres password=$DB_PASSWORD',
    'SELECT id, tenant_key, product_id, name, alias, description, mission, status,
            staging_status, context_budget, context_used, created_at, updated_at,
            completed_at, activated_at, paused_at, deleted_at, meta_data,
            orchestrator_summary, closeout_prompt, closeout_executed_at, closeout_checklist,
            execution_mode FROM projects'
) AS p(
    id varchar(36), tenant_key varchar(36), product_id varchar(36), name varchar(255),
    alias varchar(6), description text, mission text, status varchar(50),
    staging_status varchar(50), context_budget integer, context_used integer,
    created_at timestamptz, updated_at timestamptz, completed_at timestamptz,
    activated_at timestamptz, paused_at timestamptz, deleted_at timestamptz,
    meta_data json, orchestrator_summary text, closeout_prompt text,
    closeout_executed_at timestamptz, closeout_checklist jsonb, execution_mode varchar(20)
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- 4. TASKS (with new org_id column, skip test_tenant)
-- =============================================================================
INSERT INTO tasks (
    id, tenant_key, org_id, product_id, project_id, parent_task_id,
    created_by_user_id, converted_to_project_id, job_id, title, description,
    category, status, priority, estimated_effort, actual_effort, created_at,
    started_at, completed_at, due_date, meta_data
)
SELECT
    t.id,
    'tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO' as tenant_key,
    '8c57dedc-13b1-4038-9222-95d5ddac29b5' as org_id,
    t.product_id,
    t.project_id,
    t.parent_task_id,
    NULL as created_by_user_id,  -- Old user IDs won't match new user
    t.converted_to_project_id,
    NULL as job_id,  -- Old job IDs won't exist in new database
    t.title,
    t.description,
    t.category,
    t.status,
    t.priority,
    t.estimated_effort,
    t.actual_effort,
    t.created_at,
    t.started_at,
    t.completed_at,
    t.due_date,
    t.meta_data
FROM dblink(
    'dbname=giljo_mcp_backup_temp user=postgres password=$DB_PASSWORD',
    'SELECT id, tenant_key, product_id, project_id, parent_task_id,
            created_by_user_id, converted_to_project_id, job_id, title, description,
            category, status, priority, estimated_effort, actual_effort, created_at,
            started_at, completed_at, due_date, meta_data
     FROM tasks WHERE tenant_key != ''test_tenant'''
) AS t(
    id varchar(36), tenant_key varchar(36), product_id varchar(36), project_id varchar(36),
    parent_task_id varchar(36), created_by_user_id varchar(36), converted_to_project_id varchar(36),
    job_id varchar(36), title varchar(255), description text, category varchar(100),
    status varchar(50), priority varchar(20), estimated_effort float8, actual_effort float8,
    created_at timestamptz, started_at timestamptz, completed_at timestamptz,
    due_date timestamptz, meta_data jsonb
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- 5. PRODUCT MEMORY ENTRIES (with UUID cast and full column list)
-- =============================================================================
INSERT INTO product_memory_entries (
    id, tenant_key, product_id, project_id, sequence, entry_type, source,
    timestamp, project_name, summary, key_outcomes, decisions_made, git_commits,
    deliverables, metrics, priority, significance_score, token_estimate, tags,
    author_job_id, author_name, author_type, deleted_by_user, user_deleted_at,
    created_at, updated_at
)
SELECT
    m.id::uuid,
    'tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO' as tenant_key,
    m.product_id,
    m.project_id,
    m.sequence,
    m.entry_type,
    m.source,
    m.timestamp,
    m.project_name,
    m.summary,
    m.key_outcomes,
    m.decisions_made,
    m.git_commits,
    m.deliverables,
    m.metrics,
    m.priority,
    m.significance_score,
    m.token_estimate,
    m.tags,
    m.author_job_id,
    m.author_name,
    m.author_type,
    m.deleted_by_user,
    m.user_deleted_at,
    m.created_at,
    m.updated_at
FROM dblink(
    'dbname=giljo_mcp_backup_temp user=postgres password=$DB_PASSWORD',
    'SELECT id, tenant_key, product_id, project_id, sequence, entry_type, source,
            timestamp, project_name, summary, key_outcomes, decisions_made, git_commits,
            deliverables, metrics, priority, significance_score, token_estimate, tags,
            author_job_id, author_name, author_type, deleted_by_user, user_deleted_at,
            created_at, updated_at FROM product_memory_entries'
) AS m(
    id uuid, tenant_key varchar(36), product_id varchar(36), project_id varchar(36),
    sequence integer, entry_type varchar(50), source varchar(50), timestamp timestamptz,
    project_name varchar(255), summary text, key_outcomes jsonb, decisions_made jsonb,
    git_commits jsonb, deliverables jsonb, metrics jsonb, priority integer,
    significance_score float8, token_estimate integer, tags jsonb, author_job_id varchar(36),
    author_name varchar(255), author_type varchar(50), deleted_by_user boolean,
    user_deleted_at timestamptz, created_at timestamptz, updated_at timestamptz
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- 6. AGENT TEMPLATES - SKIPPED
-- Schema changed significantly between versions. Please recreate templates manually.
-- =============================================================================

COMMIT;

-- =============================================================================
-- VERIFICATION QUERIES (run after migration)
-- =============================================================================
-- SELECT 'Products' as entity, COUNT(*) as count FROM products WHERE tenant_key = 'tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO'
-- UNION ALL
-- SELECT 'Vision Documents', COUNT(*) FROM vision_documents WHERE tenant_key = 'tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO'
-- UNION ALL
-- SELECT 'Projects', COUNT(*) FROM projects WHERE tenant_key = 'tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO'
-- UNION ALL
-- SELECT 'Tasks', COUNT(*) FROM tasks WHERE tenant_key = 'tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO'
-- UNION ALL
-- SELECT 'Product Memory', COUNT(*) FROM product_memory_entries WHERE tenant_key = 'tk_rbY4dGFnwJa4TBSQfmlxWvzToZsl6wbO';
