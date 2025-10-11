-- GiljoAI MCP Complete Schema Creation Script
-- Generated for PostgreSQL 14-18
-- This script creates ALL tables for the GiljoAI MCP system
--
-- USAGE:
--   psql -h localhost -p 5432 -U giljo_owner -d giljo_mcp -f create_schema.sql
--
-- IMPORTANT: Run this AFTER creating the database and roles

-- ============================================================================
-- CORE PROJECT TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    mission TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    context_budget INTEGER DEFAULT 150000,
    context_used INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    meta_data JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_project_tenant ON projects(tenant_key);
CREATE INDEX IF NOT EXISTS idx_project_status ON projects(status);

-- ============================================================================
-- AGENT TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS agents (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    mission TEXT,
    context_used INTEGER DEFAULT 0,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    decommissioned_at TIMESTAMP WITH TIME ZONE,
    meta_data JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_agent_project_name UNIQUE (project_id, name)
);

CREATE INDEX IF NOT EXISTS idx_agent_tenant ON agents(tenant_key);
CREATE INDEX IF NOT EXISTS idx_agent_project ON agents(project_id);
CREATE INDEX IF NOT EXISTS idx_agent_status ON agents(status);

-- ============================================================================
-- MESSAGING TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS messages (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    from_agent_id VARCHAR(36) REFERENCES agents(id),
    to_agents JSONB DEFAULT '[]'::jsonb,
    message_type VARCHAR(50) DEFAULT 'direct',
    subject VARCHAR(255),
    content TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    status VARCHAR(50) DEFAULT 'pending',
    acknowledged_by JSONB DEFAULT '[]'::jsonb,
    completed_by JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    meta_data JSONB DEFAULT '{}'::jsonb,
    processing_started_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    backoff_seconds INTEGER DEFAULT 60,
    circuit_breaker_status VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_message_tenant ON messages(tenant_key);
CREATE INDEX IF NOT EXISTS idx_message_project ON messages(project_id);
CREATE INDEX IF NOT EXISTS idx_message_status ON messages(status);
CREATE INDEX IF NOT EXISTS idx_message_priority ON messages(priority);
CREATE INDEX IF NOT EXISTS idx_message_created ON messages(created_at);

-- ============================================================================
-- TASK MANAGEMENT TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    product_id VARCHAR(36),
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    assigned_agent_id VARCHAR(36) REFERENCES agents(id),
    parent_task_id VARCHAR(36) REFERENCES tasks(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'medium',
    estimated_effort FLOAT,
    actual_effort FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    due_date TIMESTAMP WITH TIME ZONE,
    meta_data JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_task_tenant ON tasks(tenant_key);
CREATE INDEX IF NOT EXISTS idx_task_product ON tasks(product_id);
CREATE INDEX IF NOT EXISTS idx_task_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_task_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_task_assigned ON tasks(assigned_agent_id);

-- ============================================================================
-- SESSION TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    session_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    objectives TEXT,
    outcomes TEXT,
    decisions JSONB DEFAULT '[]'::jsonb,
    blockers JSONB DEFAULT '[]'::jsonb,
    next_steps JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    meta_data JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_session_project_number UNIQUE (project_id, session_number)
);

CREATE INDEX IF NOT EXISTS idx_session_tenant ON sessions(tenant_key);
CREATE INDEX IF NOT EXISTS idx_session_project ON sessions(project_id);

-- ============================================================================
-- VISION AND DOCUMENT TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS visions (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    document_name VARCHAR(255) NOT NULL,
    chunk_number INTEGER DEFAULT 1,
    total_chunks INTEGER DEFAULT 1,
    content TEXT NOT NULL,
    tokens INTEGER,
    version VARCHAR(50) DEFAULT '1.0.0',
    char_start INTEGER,
    char_end INTEGER,
    boundary_type VARCHAR(20),
    keywords JSONB DEFAULT '[]'::jsonb,
    headers JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    meta_data JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_vision_chunk UNIQUE (project_id, document_name, chunk_number)
);

CREATE INDEX IF NOT EXISTS idx_vision_tenant ON visions(tenant_key);
CREATE INDEX IF NOT EXISTS idx_vision_project ON visions(project_id);
CREATE INDEX IF NOT EXISTS idx_vision_document ON visions(document_name);

-- ============================================================================
-- CONFIGURATION TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS configurations (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36),
    project_id VARCHAR(36) REFERENCES projects(id),
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    description TEXT,
    is_secret BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_config_tenant_key UNIQUE (tenant_key, key)
);

CREATE INDEX IF NOT EXISTS idx_config_tenant ON configurations(tenant_key);
CREATE INDEX IF NOT EXISTS idx_config_category ON configurations(category);

CREATE TABLE IF NOT EXISTS discovery_config (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    path_key VARCHAR(50) NOT NULL,
    path_value TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_discovery_path UNIQUE (project_id, path_key)
);

CREATE INDEX IF NOT EXISTS idx_discovery_tenant ON discovery_config(tenant_key);
CREATE INDEX IF NOT EXISTS idx_discovery_project ON discovery_config(project_id);

-- ============================================================================
-- CONTEXT INDEX TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS context_index (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    index_type VARCHAR(50) NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    section_name VARCHAR(255),
    chunk_numbers JSONB DEFAULT '[]'::jsonb,
    summary TEXT,
    token_count INTEGER,
    keywords JSONB DEFAULT '[]'::jsonb,
    full_path TEXT,
    content_hash VARCHAR(32),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_context_index UNIQUE (project_id, document_name, section_name)
);

CREATE INDEX IF NOT EXISTS idx_context_tenant ON context_index(tenant_key);
CREATE INDEX IF NOT EXISTS idx_context_type ON context_index(index_type);
CREATE INDEX IF NOT EXISTS idx_context_doc ON context_index(document_name);

CREATE TABLE IF NOT EXISTS large_document_index (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    document_path TEXT NOT NULL,
    document_type VARCHAR(50),
    total_size INTEGER,
    total_tokens INTEGER,
    chunk_count INTEGER,
    meta_data JSONB DEFAULT '{}'::jsonb,
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_large_doc_path UNIQUE (project_id, document_path)
);

CREATE INDEX IF NOT EXISTS idx_large_doc_tenant ON large_document_index(tenant_key);

-- ============================================================================
-- JOB TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    agent_id VARCHAR(36) NOT NULL REFERENCES agents(id),
    job_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    tasks JSONB DEFAULT '[]'::jsonb,
    scope_boundary TEXT,
    vision_alignment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    meta_data JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_job_tenant ON jobs(tenant_key);
CREATE INDEX IF NOT EXISTS idx_job_agent ON jobs(agent_id);
CREATE INDEX IF NOT EXISTS idx_job_status ON jobs(status);

-- ============================================================================
-- AGENT INTERACTION TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_interactions (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id),
    parent_agent_id VARCHAR(36) REFERENCES agents(id),
    sub_agent_name VARCHAR(100) NOT NULL,
    interaction_type VARCHAR(20) NOT NULL CHECK (interaction_type IN ('SPAWN', 'COMPLETE', 'ERROR')),
    mission TEXT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    tokens_used INTEGER,
    result TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    meta_data JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_interaction_tenant ON agent_interactions(tenant_key);
CREATE INDEX IF NOT EXISTS idx_interaction_project ON agent_interactions(project_id);
CREATE INDEX IF NOT EXISTS idx_interaction_parent ON agent_interactions(parent_agent_id);
CREATE INDEX IF NOT EXISTS idx_interaction_type ON agent_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_interaction_created ON agent_interactions(created_at);

-- ============================================================================
-- AGENT TEMPLATE TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_templates (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    product_id VARCHAR(36),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    role VARCHAR(50),
    project_type VARCHAR(50),
    template_content TEXT NOT NULL,
    variables JSONB DEFAULT '[]'::jsonb,
    behavioral_rules JSONB DEFAULT '[]'::jsonb,
    success_criteria JSONB DEFAULT '[]'::jsonb,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    avg_generation_ms FLOAT,
    description TEXT,
    version VARCHAR(20) DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    tags JSONB DEFAULT '[]'::jsonb,
    meta_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(100),
    CONSTRAINT uq_template_product_name_version UNIQUE (product_id, name, version)
);

CREATE INDEX IF NOT EXISTS idx_template_tenant ON agent_templates(tenant_key);
CREATE INDEX IF NOT EXISTS idx_template_product ON agent_templates(product_id);
CREATE INDEX IF NOT EXISTS idx_template_category ON agent_templates(category);
CREATE INDEX IF NOT EXISTS idx_template_role ON agent_templates(role);
CREATE INDEX IF NOT EXISTS idx_template_active ON agent_templates(is_active);

CREATE TABLE IF NOT EXISTS template_archives (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    template_id VARCHAR(36) NOT NULL REFERENCES agent_templates(id),
    product_id VARCHAR(36),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    role VARCHAR(50),
    template_content TEXT NOT NULL,
    variables JSONB DEFAULT '[]'::jsonb,
    behavioral_rules JSONB DEFAULT '[]'::jsonb,
    success_criteria JSONB DEFAULT '[]'::jsonb,
    version VARCHAR(20) NOT NULL,
    archive_reason VARCHAR(255),
    archive_type VARCHAR(20) DEFAULT 'manual',
    archived_by VARCHAR(100),
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    usage_count_at_archive INTEGER,
    avg_generation_ms_at_archive FLOAT,
    is_restorable BOOLEAN DEFAULT TRUE,
    restored_at TIMESTAMP WITH TIME ZONE,
    restored_by VARCHAR(100),
    meta_data JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_archive_tenant ON template_archives(tenant_key);
CREATE INDEX IF NOT EXISTS idx_archive_template ON template_archives(template_id);
CREATE INDEX IF NOT EXISTS idx_archive_product ON template_archives(product_id);
CREATE INDEX IF NOT EXISTS idx_archive_version ON template_archives(version);
CREATE INDEX IF NOT EXISTS idx_archive_date ON template_archives(archived_at);

CREATE TABLE IF NOT EXISTS template_augmentations (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    template_id VARCHAR(36) NOT NULL REFERENCES agent_templates(id),
    name VARCHAR(100) NOT NULL,
    augmentation_type VARCHAR(50) NOT NULL,
    target_section VARCHAR(100),
    content TEXT NOT NULL,
    conditions JSONB DEFAULT '{}'::jsonb,
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_augment_tenant ON template_augmentations(tenant_key);
CREATE INDEX IF NOT EXISTS idx_augment_template ON template_augmentations(template_id);
CREATE INDEX IF NOT EXISTS idx_augment_active ON template_augmentations(is_active);

CREATE TABLE IF NOT EXISTS template_usage_stats (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    template_id VARCHAR(36) NOT NULL REFERENCES agent_templates(id),
    agent_id VARCHAR(36) REFERENCES agents(id),
    project_id VARCHAR(36) REFERENCES projects(id),
    used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    generation_ms INTEGER,
    variables_used JSONB DEFAULT '{}'::jsonb,
    augmentations_applied JSONB DEFAULT '[]'::jsonb,
    agent_completed BOOLEAN,
    agent_success_rate FLOAT,
    tokens_used INTEGER
);

CREATE INDEX IF NOT EXISTS idx_usage_tenant ON template_usage_stats(tenant_key);
CREATE INDEX IF NOT EXISTS idx_usage_template ON template_usage_stats(template_id);
CREATE INDEX IF NOT EXISTS idx_usage_project ON template_usage_stats(project_id);
CREATE INDEX IF NOT EXISTS idx_usage_date ON template_usage_stats(used_at);

-- ============================================================================
-- GIT INTEGRATION TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS git_configs (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    repo_url VARCHAR(500) NOT NULL,
    branch VARCHAR(100) DEFAULT 'main',
    remote_name VARCHAR(50) DEFAULT 'origin',
    auth_method VARCHAR(20) NOT NULL CHECK (auth_method IN ('https', 'ssh', 'token')),
    username VARCHAR(100),
    password_encrypted TEXT,
    ssh_key_path VARCHAR(500),
    ssh_key_encrypted TEXT,
    auto_commit BOOLEAN DEFAULT TRUE,
    auto_push BOOLEAN DEFAULT FALSE,
    commit_message_template TEXT,
    webhook_url VARCHAR(500),
    webhook_secret VARCHAR(255),
    webhook_events JSONB DEFAULT '[]'::jsonb,
    ignore_patterns JSONB DEFAULT '[]'::jsonb,
    git_config_options JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    last_commit_hash VARCHAR(40),
    last_push_at TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    verified_at TIMESTAMP WITH TIME ZONE,
    meta_data JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_git_config_product UNIQUE (product_id)
);

CREATE INDEX IF NOT EXISTS idx_git_config_tenant ON git_configs(tenant_key);
CREATE INDEX IF NOT EXISTS idx_git_config_product ON git_configs(product_id);
CREATE INDEX IF NOT EXISTS idx_git_config_active ON git_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_git_config_auth ON git_configs(auth_method);

CREATE TABLE IF NOT EXISTS git_commits (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) REFERENCES projects(id),
    commit_hash VARCHAR(40) NOT NULL UNIQUE,
    commit_message TEXT NOT NULL,
    author_name VARCHAR(100) NOT NULL,
    author_email VARCHAR(255) NOT NULL,
    branch_name VARCHAR(100) NOT NULL,
    files_changed JSONB DEFAULT '[]'::jsonb,
    insertions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    triggered_by VARCHAR(50),
    agent_id VARCHAR(36) REFERENCES agents(id),
    commit_type VARCHAR(50),
    push_status VARCHAR(20) DEFAULT 'pending' CHECK (push_status IN ('pending', 'pushed', 'failed')),
    push_error TEXT,
    webhook_triggered BOOLEAN DEFAULT FALSE,
    webhook_response JSONB,
    committed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    pushed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    meta_data JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_git_commit_tenant ON git_commits(tenant_key);
CREATE INDEX IF NOT EXISTS idx_git_commit_product ON git_commits(product_id);
CREATE INDEX IF NOT EXISTS idx_git_commit_project ON git_commits(project_id);
CREATE INDEX IF NOT EXISTS idx_git_commit_hash ON git_commits(commit_hash);
CREATE INDEX IF NOT EXISTS idx_git_commit_date ON git_commits(committed_at);
CREATE INDEX IF NOT EXISTS idx_git_commit_trigger ON git_commits(triggered_by);

-- ============================================================================
-- GRANTS - Set up permissions for giljo_user role
-- ============================================================================

-- Grant select, insert, update, delete on all tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO giljo_user;

-- Grant usage on all sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO giljo_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO giljo_user;

ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO giljo_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Display created tables
SELECT 'Tables created successfully!' AS status;
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Display table counts
SELECT 'Schema Statistics:' AS info;
SELECT COUNT(*) AS total_tables FROM pg_tables WHERE schemaname = 'public';
SELECT COUNT(*) AS total_indexes FROM pg_indexes WHERE schemaname = 'public';
