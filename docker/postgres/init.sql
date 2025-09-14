-- PostgreSQL Initialization Script for GiljoAI MCP
-- This script runs automatically when the PostgreSQL container is first created
-- Best practices implemented:
-- 1. Explicit schema creation
-- 2. Proper permissions and ownership
-- 3. Extension setup for advanced features
-- 4. Performance tuning defaults
-- 5. Security hardening

-- Create database if not exists (handled by POSTGRES_DB env var)
-- Note: Database creation is handled by Docker environment variables

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- For query performance monitoring
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- For encryption functions

-- Create application schema
CREATE SCHEMA IF NOT EXISTS giljo_mcp;

-- Set search path
ALTER DATABASE giljo_mcp_db SET search_path TO giljo_mcp, public;

-- Create enum types for better data integrity
CREATE TYPE giljo_mcp.project_status AS ENUM ('active', 'paused', 'completed', 'archived');
CREATE TYPE giljo_mcp.agent_status AS ENUM ('idle', 'working', 'handoff', 'completed', 'error');
CREATE TYPE giljo_mcp.message_status AS ENUM ('pending', 'acknowledged', 'processing', 'completed', 'failed');
CREATE TYPE giljo_mcp.message_priority AS ENUM ('low', 'normal', 'high', 'critical');
CREATE TYPE giljo_mcp.task_status AS ENUM ('pending', 'in_progress', 'completed', 'failed', 'cancelled');

-- Create tables with best practices
-- Projects table with tenant isolation
CREATE TABLE IF NOT EXISTS giljo_mcp.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_key VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    mission TEXT,
    status giljo_mcp.project_status DEFAULT 'active',
    context_budget INTEGER DEFAULT 150000,
    context_used INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',

    -- Indexes for performance
    CONSTRAINT check_context_used CHECK (context_used >= 0),
    CONSTRAINT check_context_budget CHECK (context_budget > 0)
);

-- Agents table
CREATE TABLE IF NOT EXISTS giljo_mcp.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES giljo_mcp.projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100),
    status giljo_mcp.agent_status DEFAULT 'idle',
    context_used INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',

    -- Composite unique constraint
    UNIQUE(project_id, name),

    -- Performance constraint
    CONSTRAINT check_agent_context CHECK (context_used >= 0)
);

-- Messages table with acknowledgment tracking
CREATE TABLE IF NOT EXISTS giljo_mcp.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES giljo_mcp.projects(id) ON DELETE CASCADE,
    from_agent VARCHAR(255),
    to_agents TEXT[], -- Array of recipient agent names
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'direct',
    priority giljo_mcp.message_priority DEFAULT 'normal',
    status giljo_mcp.message_status DEFAULT 'pending',
    acknowledged_by TEXT[], -- Array of agents who acknowledged
    completed_by TEXT[],    -- Array of agents who completed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

-- Tasks table
CREATE TABLE IF NOT EXISTS giljo_mcp.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES giljo_mcp.projects(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES giljo_mcp.agents(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status giljo_mcp.task_status DEFAULT 'pending',
    priority giljo_mcp.message_priority DEFAULT 'normal',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

-- Sessions table for tracking work sessions
CREATE TABLE IF NOT EXISTS giljo_mcp.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES giljo_mcp.projects(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES giljo_mcp.agents(id) ON DELETE SET NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    context_snapshot JSONB,
    metadata JSONB DEFAULT '{}'
);

-- Vision documents table for chunked storage
CREATE TABLE IF NOT EXISTS giljo_mcp.vision_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES giljo_mcp.projects(id) ON DELETE CASCADE,
    document_name VARCHAR(255) NOT NULL,
    chunk_index INTEGER NOT NULL,
    total_chunks INTEGER NOT NULL,
    content TEXT NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}',

    -- Ensure unique chunks per document
    UNIQUE(project_id, document_name, chunk_index)
);

-- Configuration table for system settings
CREATE TABLE IF NOT EXISTS giljo_mcp.configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    category VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_tenant_key ON giljo_mcp.projects(tenant_key);
CREATE INDEX IF NOT EXISTS idx_projects_status ON giljo_mcp.projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON giljo_mcp.projects(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agents_project_id ON giljo_mcp.agents(project_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON giljo_mcp.agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_last_active ON giljo_mcp.agents(last_active DESC);

CREATE INDEX IF NOT EXISTS idx_messages_project_id ON giljo_mcp.messages(project_id);
CREATE INDEX IF NOT EXISTS idx_messages_status ON giljo_mcp.messages(status);
CREATE INDEX IF NOT EXISTS idx_messages_priority ON giljo_mcp.messages(priority);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON giljo_mcp.messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_to_agents ON giljo_mcp.messages USING GIN(to_agents);

CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON giljo_mcp.tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_id ON giljo_mcp.tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON giljo_mcp.tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON giljo_mcp.tasks(priority);

CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON giljo_mcp.sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_sessions_agent_id ON giljo_mcp.sessions(agent_id);

CREATE INDEX IF NOT EXISTS idx_vision_project_doc ON giljo_mcp.vision_documents(project_id, document_name);

-- Create update trigger for updated_at columns
CREATE OR REPLACE FUNCTION giljo_mcp.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to relevant tables
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON giljo_mcp.projects
    FOR EACH ROW EXECUTE FUNCTION giljo_mcp.update_updated_at_column();

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON giljo_mcp.agents
    FOR EACH ROW EXECUTE FUNCTION giljo_mcp.update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON giljo_mcp.tasks
    FOR EACH ROW EXECUTE FUNCTION giljo_mcp.update_updated_at_column();

CREATE TRIGGER update_configurations_updated_at BEFORE UPDATE ON giljo_mcp.configurations
    FOR EACH ROW EXECUTE FUNCTION giljo_mcp.update_updated_at_column();

-- Insert default configuration
INSERT INTO giljo_mcp.configurations (key, value, category, description)
VALUES
    ('system.version', '"1.0.0"', 'system', 'System version'),
    ('agents.max_per_project', '20', 'agents', 'Maximum agents per project'),
    ('agents.context_limit', '150000', 'agents', 'Context token limit per agent'),
    ('messages.batch_size', '10', 'messages', 'Message processing batch size'),
    ('vision.chunk_size', '20000', 'vision', 'Vision document chunk size in tokens')
ON CONFLICT (key) DO NOTHING;

-- Create read-only user for reporting (optional)
-- CREATE USER giljo_readonly WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE giljo_mcp_db TO giljo_readonly;
-- GRANT USAGE ON SCHEMA giljo_mcp TO giljo_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA giljo_mcp TO giljo_readonly;

-- Analyze tables for query planner
ANALYZE giljo_mcp.projects;
ANALYZE giljo_mcp.agents;
ANALYZE giljo_mcp.messages;
ANALYZE giljo_mcp.tasks;
ANALYZE giljo_mcp.sessions;
ANALYZE giljo_mcp.vision_documents;
ANALYZE giljo_mcp.configurations;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'GiljoAI MCP database initialization completed successfully';
END $$;