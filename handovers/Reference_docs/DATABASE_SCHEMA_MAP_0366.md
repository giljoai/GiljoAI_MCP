# Database Schema Map for Handover 0366 - Agent Identity Refactor

**Date**: 2025-12-19
**Purpose**: Detailed schema comparison and migration strategy
**Migration ID**: 0366a
**Status**: Reference Document

---

## Executive Summary

This document provides a **complete schema mapping** between the current `mcp_agent_jobs` table and the proposed dual-table architecture (`agent_jobs` + `agent_executions`). It also defines the **data transformation logic** for migrating existing production data.

### Schema Transformation Overview

```
BEFORE (1 table):
mcp_agent_jobs (34 columns, job + execution conflated)

AFTER (2 tables):
agent_jobs (10 columns, work order only)
agent_executions (28 columns, executor instance only)
```

### Data Migration Strategy

**Approach**: 1:1:1 Split
- Each row in `mcp_agent_jobs` becomes:
  - 1 row in `agent_jobs` (work order)
  - 1 row in `agent_executions` (executor instance)
- Foreign key: `agent_executions.job_id` → `agent_jobs.job_id`
- Preservation: All data preserved, no loss

---

## Current Schema: mcp_agent_jobs Table

### Full Column List (34 columns)

| Column | Type | Constraints | Purpose | Destination Table |
|--------|------|-------------|---------|-------------------|
| **id** | Integer | PRIMARY KEY, AUTOINCREMENT | Internal DB ID | agent_executions |
| **job_id** | String(36) | UNIQUE, NOT NULL | Work order UUID | agent_jobs (PK), agent_executions (FK) |
| **tenant_key** | String(36) | NOT NULL, INDEX | Multi-tenant isolation | Both tables |
| **project_id** | String(36) | FK(projects.id), INDEX | Project association | agent_jobs |
| **agent_type** | String(100) | NOT NULL | Agent type (orchestrator, analyzer, etc.) | agent_executions |
| **mission** | Text | NOT NULL | Agent mission/instructions | agent_jobs |
| **status** | String(50) | NOT NULL, DEFAULT 'waiting' | Execution status | agent_executions |
| **failure_reason** | String(50) | NULLABLE | Failure reason (error, timeout, system_error) | agent_executions |
| **spawned_by** | String(36) | NULLABLE | Parent job_id (AMBIGUOUS!) | agent_executions (points to agent_id) |
| **context_chunks** | JSON | DEFAULT [] | Context chunk IDs | agent_executions |
| **messages** | JSONB | DEFAULT [] | Message array for communication | agent_executions |
| **started_at** | DateTime(TZ) | NULLABLE | Execution start time | agent_executions |
| **completed_at** | DateTime(TZ) | NULLABLE | Execution completion time | agent_executions |
| **created_at** | DateTime(TZ) | SERVER DEFAULT NOW() | Record creation time | agent_jobs |
| **progress** | Integer | DEFAULT 0, CHECK 0-100 | Progress percentage | agent_executions |
| **block_reason** | Text | NULLABLE | Blocker explanation | agent_executions |
| **current_task** | Text | NULLABLE | Current task description | agent_executions |
| **estimated_completion** | DateTime(TZ) | NULLABLE | Estimated completion time | agent_executions |
| **tool_type** | String(20) | DEFAULT 'universal' | Coding tool (claude-code, codex, etc.) | agent_executions |
| **agent_name** | String(255) | NULLABLE | Human-readable display name | agent_executions |
| **instance_number** | Integer | DEFAULT 1, NOT NULL | Succession instance number | agent_executions |
| **handover_to** | String(36) | NULLABLE | Successor job_id (AMBIGUOUS!) | agent_executions (rename: succeeded_by) |
| **handover_summary** | JSONB | NULLABLE | Compressed state transfer | agent_executions |
| **handover_context_refs** | JSON | DEFAULT [] | Context chunk refs in handover | agent_executions |
| **succession_reason** | String(100) | NULLABLE | Succession reason | agent_executions |
| **context_used** | Integer | DEFAULT 0, NOT NULL | Context tokens used | agent_executions |
| **context_budget** | Integer | DEFAULT 150000, NOT NULL | Context token budget | agent_executions |
| **job_metadata** | JSONB | DEFAULT {}, NOT NULL | Thin client metadata | agent_jobs |
| **last_health_check** | DateTime(TZ) | NULLABLE | Health check timestamp | agent_executions |
| **health_status** | String(20) | DEFAULT 'unknown' | Health state | agent_executions |
| **health_failure_count** | Integer | DEFAULT 0 | Consecutive health failures | agent_executions |
| **last_progress_at** | DateTime(TZ) | NULLABLE | Last progress update | agent_executions |
| **last_message_check_at** | DateTime(TZ) | NULLABLE | Last message check | agent_executions |
| **decommissioned_at** | DateTime(TZ) | NULLABLE | Decommission timestamp | agent_executions |
| **mission_acknowledged_at** | DateTime(TZ) | NULLABLE | Mission fetch timestamp | agent_executions |
| **template_id** | String(36) | FK(agent_templates.id) | Template reference | agent_jobs |

---

## Proposed Schema: agent_jobs Table

### Column List (10 columns)

| Column | Type | Constraints | Purpose | Migrated From |
|--------|------|-------------|---------|---------------|
| **job_id** | String(36) | PRIMARY KEY | Work order UUID | mcp_agent_jobs.job_id |
| **tenant_key** | String(36) | NOT NULL, INDEX | Multi-tenant isolation | mcp_agent_jobs.tenant_key |
| **project_id** | String(36) | FK(projects.id), INDEX | Project association | mcp_agent_jobs.project_id |
| **mission** | Text | NOT NULL | Agent mission (stored ONCE) | mcp_agent_jobs.mission |
| **job_type** | String(100) | NOT NULL | Job type (orchestrator, analyzer, etc.) | mcp_agent_jobs.agent_type |
| **status** | String(50) | DEFAULT 'active', NOT NULL | Job status (active, completed, cancelled) | **DERIVED** (see below) |
| **created_at** | DateTime(TZ) | SERVER DEFAULT NOW() | Job creation time | mcp_agent_jobs.created_at |
| **completed_at** | DateTime(TZ) | NULLABLE | Job completion time | mcp_agent_jobs.completed_at |
| **job_metadata** | JSONB | DEFAULT {}, NOT NULL | Job-level metadata | mcp_agent_jobs.job_metadata |
| **template_id** | String(36) | FK(agent_templates.id), NULLABLE | Template reference | mcp_agent_jobs.template_id |

### Status Derivation Logic

Job status is **derived** from execution status during migration:

```sql
CASE
    WHEN status IN ('complete', 'failed', 'cancelled', 'decommissioned') THEN 'completed'
    WHEN status = 'cancelled' THEN 'cancelled'
    ELSE 'active'
END AS status
```

### Indexes

```sql
CREATE INDEX idx_agent_jobs_tenant ON agent_jobs(tenant_key);
CREATE INDEX idx_agent_jobs_project ON agent_jobs(project_id);
CREATE INDEX idx_agent_jobs_tenant_project ON agent_jobs(tenant_key, project_id);
CREATE INDEX idx_agent_jobs_status ON agent_jobs(status);
```

### Constraints

```sql
ALTER TABLE agent_jobs ADD CONSTRAINT ck_agent_job_status
    CHECK (status IN ('active', 'completed', 'cancelled'));
```

---

## Proposed Schema: agent_executions Table

### Column List (28 columns)

| Column | Type | Constraints | Purpose | Migrated From |
|--------|------|-------------|---------|---------------|
| **agent_id** | String(36) | PRIMARY KEY | Executor UUID | **NEW** (generated from job_id) |
| **job_id** | String(36) | FK(agent_jobs.job_id), NOT NULL, INDEX | Work order reference | mcp_agent_jobs.job_id |
| **tenant_key** | String(36) | NOT NULL, INDEX | Multi-tenant isolation | mcp_agent_jobs.tenant_key |
| **agent_type** | String(100) | NOT NULL | Agent type | mcp_agent_jobs.agent_type |
| **instance_number** | Integer | DEFAULT 1, NOT NULL | Succession instance | mcp_agent_jobs.instance_number |
| **status** | String(50) | DEFAULT 'waiting', NOT NULL | Execution status | mcp_agent_jobs.status |
| **started_at** | DateTime(TZ) | NULLABLE | Execution start | mcp_agent_jobs.started_at |
| **completed_at** | DateTime(TZ) | NULLABLE | Execution completion | mcp_agent_jobs.completed_at |
| **decommissioned_at** | DateTime(TZ) | NULLABLE | Decommission time | mcp_agent_jobs.decommissioned_at |
| **spawned_by** | String(36) | NULLABLE | Parent agent_id | mcp_agent_jobs.spawned_by |
| **succeeded_by** | String(36) | NULLABLE | Successor agent_id | mcp_agent_jobs.handover_to (RENAMED) |
| **progress** | Integer | DEFAULT 0, NOT NULL, CHECK 0-100 | Progress percentage | mcp_agent_jobs.progress |
| **current_task** | Text | NULLABLE | Current task | mcp_agent_jobs.current_task |
| **block_reason** | Text | NULLABLE | Blocker explanation | mcp_agent_jobs.block_reason |
| **health_status** | String(20) | DEFAULT 'unknown', NOT NULL | Health state | mcp_agent_jobs.health_status |
| **last_health_check** | DateTime(TZ) | NULLABLE | Health check time | mcp_agent_jobs.last_health_check |
| **health_failure_count** | Integer | DEFAULT 0, NOT NULL | Health failures | mcp_agent_jobs.health_failure_count |
| **last_progress_at** | DateTime(TZ) | NULLABLE | Progress update time | mcp_agent_jobs.last_progress_at |
| **last_message_check_at** | DateTime(TZ) | NULLABLE | Message check time | mcp_agent_jobs.last_message_check_at |
| **mission_acknowledged_at** | DateTime(TZ) | NULLABLE | Mission fetch time | mcp_agent_jobs.mission_acknowledged_at |
| **tool_type** | String(20) | DEFAULT 'universal', NOT NULL | Coding tool | mcp_agent_jobs.tool_type |
| **context_used** | Integer | DEFAULT 0, NOT NULL | Context tokens used | mcp_agent_jobs.context_used |
| **context_budget** | Integer | DEFAULT 150000, NOT NULL | Context token budget | mcp_agent_jobs.context_budget |
| **succession_reason** | String(100) | NULLABLE | Succession reason | mcp_agent_jobs.succession_reason |
| **handover_summary** | JSONB | NULLABLE | Handover state | mcp_agent_jobs.handover_summary |
| **messages** | JSONB | DEFAULT [] | Message array | mcp_agent_jobs.messages |
| **failure_reason** | String(50) | NULLABLE | Failure reason | mcp_agent_jobs.failure_reason |
| **agent_name** | String(255) | NULLABLE | Display name | mcp_agent_jobs.agent_name |

### Indexes

```sql
CREATE INDEX idx_agent_executions_tenant ON agent_executions(tenant_key);
CREATE INDEX idx_agent_executions_job ON agent_executions(job_id);
CREATE INDEX idx_agent_executions_tenant_job ON agent_executions(tenant_key, job_id);
CREATE INDEX idx_agent_executions_status ON agent_executions(status);
CREATE INDEX idx_agent_executions_instance ON agent_executions(job_id, instance_number);
CREATE INDEX idx_agent_executions_health ON agent_executions(health_status);
CREATE INDEX idx_agent_executions_last_progress ON agent_executions(last_progress_at);
```

### Constraints

```sql
ALTER TABLE agent_executions ADD CONSTRAINT ck_agent_execution_status
    CHECK (status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned'));

ALTER TABLE agent_executions ADD CONSTRAINT ck_agent_execution_progress_range
    CHECK (progress >= 0 AND progress <= 100);

ALTER TABLE agent_executions ADD CONSTRAINT ck_agent_execution_instance_positive
    CHECK (instance_number >= 1);

ALTER TABLE agent_executions ADD CONSTRAINT ck_agent_execution_tool_type
    CHECK (tool_type IN ('claude-code', 'codex', 'gemini', 'universal'));

ALTER TABLE agent_executions ADD CONSTRAINT ck_agent_execution_health_status
    CHECK (health_status IN ('unknown', 'healthy', 'warning', 'critical', 'timeout'));

ALTER TABLE agent_executions ADD CONSTRAINT ck_agent_execution_context_usage
    CHECK (context_used >= 0 AND context_used <= context_budget);
```

---

## Data Migration Logic (Detailed)

### Step 1: Create agent_jobs table (work orders)

```sql
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
```

**Deduplication**: `DISTINCT` ensures only one job record per unique `job_id` (handles edge cases where job_id might be duplicated due to data anomalies).

### Step 2: Create agent_executions table (executor instances)

```sql
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
    job_id AS agent_id,  -- OLD job_id becomes NEW agent_id
    job_id,  -- job_id stays the same (links to agent_jobs)
    tenant_key,
    agent_type,
    instance_number,
    status,
    started_at,
    completed_at,
    decommissioned_at,
    spawned_by,
    handover_to AS succeeded_by,  -- RENAMED column
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
```

**Key Transformation**: `job_id AS agent_id` - Old job_id becomes the executor's agent_id in the new schema.

### Step 3: Update Foreign Key References

#### spawned_by and succeeded_by
In the current schema, these fields point to `job_id` (ambiguous - work or worker?).
In the new schema, they point to `agent_id` (clear - specific executor).

**Migration**: No change needed for initial migration (old job_id becomes new agent_id).
**Post-Migration**: New spawns/successions will use agent_id semantics correctly.

#### Messages Table
The `messages` table has `to_agents` JSONB array containing job_id references.

**Migration Strategy**:
```sql
-- Update messages.to_agents to use agent_id (same UUID, different semantic meaning)
-- No data transformation needed (UUIDs are identical after migration)
-- Only documentation/semantic understanding changes
```

---

## Migration Validation Queries

### Validate Row Counts Match

```sql
-- Count original rows
SELECT COUNT(*) FROM mcp_agent_jobs;

-- Count migrated jobs (should equal unique job_ids)
SELECT COUNT(*) FROM agent_jobs;

-- Count migrated executions (should equal original row count)
SELECT COUNT(*) FROM agent_executions;

-- Verify 1:1 mapping: executions = original rows
SELECT COUNT(*) AS original,
       (SELECT COUNT(*) FROM agent_executions) AS executions,
       CASE
           WHEN COUNT(*) = (SELECT COUNT(*) FROM agent_executions) THEN 'PASS'
           ELSE 'FAIL'
       END AS validation_status
FROM mcp_agent_jobs;
```

### Validate Foreign Key Integrity

```sql
-- Verify all executions link to valid jobs
SELECT COUNT(*) AS orphaned_executions
FROM agent_executions e
LEFT JOIN agent_jobs j ON e.job_id = j.job_id
WHERE j.job_id IS NULL;

-- Expected result: 0 (no orphaned executions)
```

### Validate Succession Chains

```sql
-- Verify succession chain integrity
SELECT
    e1.agent_id AS current_agent,
    e1.succeeded_by AS successor_agent,
    e2.agent_id AS successor_agent_verified,
    CASE
        WHEN e1.succeeded_by = e2.agent_id THEN 'VALID'
        ELSE 'BROKEN'
    END AS chain_status
FROM agent_executions e1
LEFT JOIN agent_executions e2 ON e1.succeeded_by = e2.agent_id
WHERE e1.succeeded_by IS NOT NULL;

-- All rows should show 'VALID' in chain_status
```

### Validate Data Preservation

```sql
-- Verify mission preserved in job (not duplicated in executions)
SELECT
    j.job_id,
    j.mission AS job_mission,
    COUNT(e.agent_id) AS execution_count
FROM agent_jobs j
JOIN agent_executions e ON j.job_id = e.job_id
GROUP BY j.job_id, j.mission;

-- Verify progress values migrated correctly
SELECT
    original.job_id,
    original.progress AS original_progress,
    migrated.progress AS migrated_progress,
    CASE
        WHEN original.progress = migrated.progress THEN 'MATCH'
        ELSE 'MISMATCH'
    END AS validation_status
FROM mcp_agent_jobs original
JOIN agent_executions migrated ON original.job_id = migrated.agent_id;

-- All rows should show 'MATCH'
```

---

## Rollback Strategy

### Rollback SQL (Restore mcp_agent_jobs)

```sql
-- Recreate mcp_agent_jobs from agent_jobs + agent_executions
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
    e.succeeded_by AS handover_to,  -- RENAME back
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

-- Drop new tables
DROP TABLE agent_executions;
DROP TABLE agent_jobs;
```

### Rollback Validation

```sql
-- Verify row count matches pre-migration
SELECT COUNT(*) FROM mcp_agent_jobs;

-- Compare against backup count (from pre-migration snapshot)
-- Expected: Counts match exactly
```

---

## Migration Timeline

| Step | Duration | Risk | Validation |
|------|----------|------|------------|
| 1. Backup database | 5 min | LOW | Verify backup file size |
| 2. Create agent_jobs table | 1 min | LOW | Table exists, indexes created |
| 3. Create agent_executions table | 1 min | LOW | Table exists, indexes created |
| 4. Migrate data to agent_jobs | 2 min | MEDIUM | Row count validation |
| 5. Migrate data to agent_executions | 3 min | MEDIUM | Row count + FK validation |
| 6. Validate succession chains | 2 min | MEDIUM | Chain integrity checks |
| 7. Validate data preservation | 3 min | MEDIUM | Mission, progress, status checks |
| 8. Drop mcp_agent_jobs (OPTIONAL) | 1 min | HIGH | Rollback tested first |
| **Total** | **18 min** | **MEDIUM** | **All validations pass** |

**Recommendation**: Keep `mcp_agent_jobs` table for 1 week after migration for emergency rollback, then drop.

---

## Post-Migration Checklist

- [ ] All validation queries return expected results (0 orphans, all chains valid)
- [ ] Backend services query new tables correctly (agent_jobs + agent_executions)
- [ ] Frontend displays agent_id + job_id correctly
- [ ] Messaging routes to agent_id (executor-specific delivery)
- [ ] Succession creates new execution (NOT new job)
- [ ] Fresh installations use new schema (install.py updated)
- [ ] Documentation updated (architecture diagrams, API docs)
- [ ] Rollback script tested on staging environment

---

**Last Updated**: 2025-12-19
**Database Expert**: Responsible for migration execution
**Status**: Reference Document - Ready for Phase A execution
