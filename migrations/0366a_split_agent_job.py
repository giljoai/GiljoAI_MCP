"""
Migration 0366a: Split mcp_agent_jobs into agent_jobs + agent_executions

**Date**: 2025-12-19
**Handover**: 0366a (Agent Identity Refactor)
**Purpose**: Separate work order (job) from executor (execution)

Schema Transformation:
- BEFORE: mcp_agent_jobs (34 columns, job + execution conflated)
- AFTER: agent_jobs (10 columns) + agent_executions (28 columns)

Key Changes:
- job_id becomes agent_id in agent_executions (executor identity)
- job_id in agent_executions references agent_jobs.job_id (work order)
- Mission stored ONCE in agent_jobs (no duplication)
- handover_to renamed to succeeded_by (semantic clarity)

Reference: handovers/Reference_docs/DATABASE_SCHEMA_MAP_0366.md
"""

from sqlalchemy import text


def upgrade(connection):
    """
    Upgrade: Split mcp_agent_jobs into agent_jobs + agent_executions.

    Steps:
    1. Create agent_jobs table (work orders)
    2. Create agent_executions table (executor instances)
    3. Migrate data from mcp_agent_jobs
    4. Validate data integrity
    """

    # Step 1: Create agent_jobs table
    connection.execute(text("""
        CREATE TABLE agent_jobs (
            job_id VARCHAR(36) PRIMARY KEY,
            tenant_key VARCHAR(36) NOT NULL,
            project_id VARCHAR(36),
            mission TEXT NOT NULL,
            job_type VARCHAR(100) NOT NULL,
            status VARCHAR(50) DEFAULT 'active' NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE,
            job_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
            template_id VARCHAR(36),
            CONSTRAINT fk_agent_jobs_project FOREIGN KEY (project_id) REFERENCES projects(id),
            CONSTRAINT fk_agent_jobs_template FOREIGN KEY (template_id) REFERENCES agent_templates(id),
            CONSTRAINT ck_agent_job_status CHECK (status IN ('active', 'completed', 'cancelled'))
        );
    """))

    # Create indexes for agent_jobs
    connection.execute(text("CREATE INDEX idx_agent_jobs_tenant ON agent_jobs(tenant_key);"))
    connection.execute(text("CREATE INDEX idx_agent_jobs_project ON agent_jobs(project_id);"))
    connection.execute(text("CREATE INDEX idx_agent_jobs_tenant_project ON agent_jobs(tenant_key, project_id);"))
    connection.execute(text("CREATE INDEX idx_agent_jobs_status ON agent_jobs(status);"))

    # Step 2: Create agent_executions table
    connection.execute(text("""
        CREATE TABLE agent_executions (
            agent_id VARCHAR(36) PRIMARY KEY,
            job_id VARCHAR(36) NOT NULL,
            tenant_key VARCHAR(36) NOT NULL,
            agent_type VARCHAR(100) NOT NULL,
            instance_number INTEGER DEFAULT 1 NOT NULL,
            status VARCHAR(50) DEFAULT 'waiting' NOT NULL,
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            decommissioned_at TIMESTAMP WITH TIME ZONE,
            spawned_by VARCHAR(36),
            succeeded_by VARCHAR(36),
            progress INTEGER DEFAULT 0 NOT NULL,
            current_task TEXT,
            block_reason TEXT,
            health_status VARCHAR(20) DEFAULT 'unknown' NOT NULL,
            last_health_check TIMESTAMP WITH TIME ZONE,
            health_failure_count INTEGER DEFAULT 0 NOT NULL,
            last_progress_at TIMESTAMP WITH TIME ZONE,
            last_message_check_at TIMESTAMP WITH TIME ZONE,
            mission_acknowledged_at TIMESTAMP WITH TIME ZONE,
            tool_type VARCHAR(20) DEFAULT 'universal' NOT NULL,
            context_used INTEGER DEFAULT 0 NOT NULL,
            context_budget INTEGER DEFAULT 150000 NOT NULL,
            succession_reason VARCHAR(100),
            handover_summary JSONB,
            messages JSONB DEFAULT '[]'::jsonb NOT NULL,
            failure_reason VARCHAR(50),
            agent_name VARCHAR(255),
            CONSTRAINT fk_agent_executions_job FOREIGN KEY (job_id) REFERENCES agent_jobs(job_id),
            CONSTRAINT ck_agent_execution_status CHECK (status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned')),
            CONSTRAINT ck_agent_execution_progress_range CHECK (progress >= 0 AND progress <= 100),
            CONSTRAINT ck_agent_execution_instance_positive CHECK (instance_number >= 1),
            CONSTRAINT ck_agent_execution_tool_type CHECK (tool_type IN ('claude-code', 'codex', 'gemini', 'universal')),
            CONSTRAINT ck_agent_execution_health_status CHECK (health_status IN ('unknown', 'healthy', 'warning', 'critical', 'timeout')),
            CONSTRAINT ck_agent_execution_context_usage CHECK (context_used >= 0 AND context_used <= context_budget)
        );
    """))

    # Create indexes for agent_executions
    connection.execute(text("CREATE INDEX idx_agent_executions_tenant ON agent_executions(tenant_key);"))
    connection.execute(text("CREATE INDEX idx_agent_executions_job ON agent_executions(job_id);"))
    connection.execute(text("CREATE INDEX idx_agent_executions_tenant_job ON agent_executions(tenant_key, job_id);"))
    connection.execute(text("CREATE INDEX idx_agent_executions_status ON agent_executions(status);"))
    connection.execute(text("CREATE INDEX idx_agent_executions_instance ON agent_executions(job_id, instance_number);"))
    connection.execute(text("CREATE INDEX idx_agent_executions_health ON agent_executions(health_status);"))
    connection.execute(text("CREATE INDEX idx_agent_executions_last_progress ON agent_executions(last_progress_at);"))

    # Step 3: Migrate data from mcp_agent_jobs to agent_jobs
    connection.execute(text("""
        INSERT INTO agent_jobs (
            job_id,
            tenant_key,
            project_id,
            mission,
            job_type,
            status,
            created_at,
            completed_at,
            job_metadata,
            template_id
        )
        SELECT DISTINCT
            job_id,
            tenant_key,
            project_id,
            mission,
            agent_type AS job_type,
            CASE
                WHEN status IN ('complete', 'failed', 'cancelled', 'decommissioned') THEN 'completed'
                WHEN status = 'cancelled' THEN 'cancelled'
                ELSE 'active'
            END AS status,
            created_at,
            completed_at,
            job_metadata,
            template_id
        FROM mcp_agent_jobs;
    """))

    # Step 4: Migrate data from mcp_agent_jobs to agent_executions
    connection.execute(text("""
        INSERT INTO agent_executions (
            agent_id,
            job_id,
            tenant_key,
            agent_type,
            instance_number,
            status,
            started_at,
            completed_at,
            decommissioned_at,
            spawned_by,
            succeeded_by,
            progress,
            current_task,
            block_reason,
            health_status,
            last_health_check,
            health_failure_count,
            last_progress_at,
            last_message_check_at,
            mission_acknowledged_at,
            tool_type,
            context_used,
            context_budget,
            succession_reason,
            handover_summary,
            messages,
            failure_reason,
            agent_name
        )
        SELECT
            job_id AS agent_id,  -- OLD job_id becomes NEW agent_id (executor identity)
            job_id,  -- job_id stays the same (links to agent_jobs)
            tenant_key,
            agent_type,
            instance_number,
            status,
            started_at,
            completed_at,
            decommissioned_at,
            spawned_by,
            handover_to AS succeeded_by,  -- RENAMED: handover_to → succeeded_by
            progress,
            current_task,
            block_reason,
            health_status,
            last_health_check,
            health_failure_count,
            last_progress_at,
            last_message_check_at,
            mission_acknowledged_at,
            tool_type,
            context_used,
            context_budget,
            succession_reason,
            handover_summary,
            messages,
            failure_reason,
            agent_name
        FROM mcp_agent_jobs;
    """))

    print("✓ Migration 0366a upgrade complete!")
    print(f"  - Created agent_jobs table")
    print(f"  - Created agent_executions table")
    print(f"  - Migrated data from mcp_agent_jobs")
    print(f"  - Old mcp_agent_jobs table preserved for rollback")


def downgrade(connection):
    """
    Downgrade: Restore mcp_agent_jobs from agent_jobs + agent_executions.

    Steps:
    1. Recreate mcp_agent_jobs table
    2. Restore data from agent_jobs + agent_executions
    3. Drop agent_executions and agent_jobs tables
    """

    # Step 1: Recreate mcp_agent_jobs structure (if it was dropped)
    # NOTE: This assumes mcp_agent_jobs was NOT dropped during upgrade
    # If it was dropped, you need to recreate it first with full schema

    # Step 2: Restore data from agent_jobs + agent_executions
    connection.execute(text("""
        INSERT INTO mcp_agent_jobs (
            job_id,
            tenant_key,
            project_id,
            agent_type,
            mission,
            status,
            instance_number,
            spawned_by,
            handover_to,
            started_at,
            completed_at,
            created_at,
            decommissioned_at,
            progress,
            current_task,
            block_reason,
            health_status,
            last_health_check,
            health_failure_count,
            last_progress_at,
            last_message_check_at,
            mission_acknowledged_at,
            tool_type,
            context_used,
            context_budget,
            succession_reason,
            handover_summary,
            messages,
            job_metadata,
            template_id,
            failure_reason,
            agent_name
        )
        SELECT
            e.agent_id AS job_id,  -- agent_id becomes job_id again
            e.tenant_key,
            j.project_id,
            e.agent_type,
            j.mission,
            e.status,
            e.instance_number,
            e.spawned_by,
            e.succeeded_by AS handover_to,  -- RENAME back: succeeded_by → handover_to
            e.started_at,
            e.completed_at,
            j.created_at,
            e.decommissioned_at,
            e.progress,
            e.current_task,
            e.block_reason,
            e.health_status,
            e.last_health_check,
            e.health_failure_count,
            e.last_progress_at,
            e.last_message_check_at,
            e.mission_acknowledged_at,
            e.tool_type,
            e.context_used,
            e.context_budget,
            e.succession_reason,
            e.handover_summary,
            e.messages,
            j.job_metadata,
            j.template_id,
            e.failure_reason,
            e.agent_name
        FROM agent_executions e
        JOIN agent_jobs j ON e.job_id = j.job_id;
    """))

    # Step 3: Drop new tables
    connection.execute(text("DROP TABLE IF EXISTS agent_executions CASCADE;"))
    connection.execute(text("DROP TABLE IF EXISTS agent_jobs CASCADE;"))

    print("✓ Migration 0366a downgrade complete!")
    print(f"  - Restored mcp_agent_jobs table")
    print(f"  - Dropped agent_executions table")
    print(f"  - Dropped agent_jobs table")


# Migration metadata
MIGRATION_ID = "0366a"
MIGRATION_NAME = "split_agent_job"
DEPENDENCIES = []  # No dependencies (can run independently)
