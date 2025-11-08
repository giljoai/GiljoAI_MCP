# Schema Comparison: Before vs. After Agent Table Drop

**Migration:** 0116b_drop_agents
**Date:** 2025-11-07

---

## Table of Contents

1. [Overview](#overview)
2. [Schema Comparison](#schema-comparison)
3. [State Model Comparison](#state-model-comparison)
4. [Data Flow Changes](#data-flow-changes)
5. [Query Examples](#query-examples)

---

## Overview

This document compares the database schema before and after dropping the `agents` table, showing the transition to a unified MCPAgentJob model.

---

## Schema Comparison

### Before Migration (Two Tables)

```sql
-- ============================================================================
-- agents table (LEGACY - 4-state model)
-- ============================================================================
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_key VARCHAR(255) NOT NULL,
    job_id VARCHAR(36) UNIQUE,  -- Links to MCPAgentJob
    agent_name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- idle, active, completed, failed (4 states)
    context_used INTEGER DEFAULT 0,
    last_active TIMESTAMP WITH TIME ZONE,
    meta_data TEXT,  -- JSON stored as text
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_agents_tenant_key ON agents(tenant_key);
CREATE INDEX idx_agents_job_id ON agents(job_id);
CREATE INDEX idx_agents_status ON agents(status);

-- ============================================================================
-- mcp_agent_jobs table (MODERN - 7-state model)
-- ============================================================================
CREATE TABLE mcp_agent_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_key VARCHAR(255) NOT NULL,
    job_id VARCHAR(36) UNIQUE NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- waiting, working, blocked, complete, failed, cancelled, decommissioned (7 states)
    failure_reason TEXT,
    job_metadata JSONB DEFAULT '{}'::jsonb,  -- Structured JSON
    decommissioned_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    product_id UUID REFERENCES products(id),
    project_id UUID REFERENCES projects(id)
);

CREATE INDEX idx_mcp_agent_jobs_tenant_key ON mcp_agent_jobs(tenant_key);
CREATE INDEX idx_mcp_agent_jobs_job_id ON mcp_agent_jobs(job_id);
CREATE INDEX idx_mcp_agent_jobs_status ON mcp_agent_jobs(status);
CREATE INDEX idx_mcp_agent_jobs_product_id ON mcp_agent_jobs(product_id);
CREATE INDEX idx_mcp_agent_jobs_project_id ON mcp_agent_jobs(project_id);
CREATE INDEX idx_mcp_agent_jobs_metadata ON mcp_agent_jobs USING gin(job_metadata);
```

**Issues:**
- Two tables tracking agent state (data disconnect)
- Agent table not visible on dashboard
- Legacy tools query wrong table
- 4-state model too simplistic

---

### After Migration (One Table + Backup)

```sql
-- ============================================================================
-- mcp_agent_jobs table (SINGLE SOURCE OF TRUTH - 7-state model)
-- ============================================================================
CREATE TABLE mcp_agent_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_key VARCHAR(255) NOT NULL,
    job_id VARCHAR(36) UNIQUE NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- waiting, working, blocked, complete, failed, cancelled, decommissioned (7 states)
    failure_reason TEXT,
    job_metadata JSONB DEFAULT '{}'::jsonb,  -- NOW includes legacy_agent_data
    decommissioned_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    product_id UUID REFERENCES products(id),
    project_id UUID REFERENCES projects(id)
);

CREATE INDEX idx_mcp_agent_jobs_tenant_key ON mcp_agent_jobs(tenant_key);
CREATE INDEX idx_mcp_agent_jobs_job_id ON mcp_agent_jobs(job_id);
CREATE INDEX idx_mcp_agent_jobs_status ON mcp_agent_jobs(status);
CREATE INDEX idx_mcp_agent_jobs_product_id ON mcp_agent_jobs(product_id);
CREATE INDEX idx_mcp_agent_jobs_project_id ON mcp_agent_jobs(project_id);
CREATE INDEX idx_mcp_agent_jobs_metadata ON mcp_agent_jobs USING gin(job_metadata);

-- ============================================================================
-- agents_backup_final (BACKUP ONLY - 30-day retention)
-- ============================================================================
-- Identical to old agents table schema
-- Safe to drop after 2025-12-07
-- Not queried by application code
```

**Benefits:**
- Single source of truth (no data disconnect)
- Dashboard-visible
- All tools query same table
- 7-state model supports complex workflows
- Legacy data preserved in job_metadata

---

## State Model Comparison

### Before Migration: Agent Table (4 States)

```
┌─────────────────────────────────────────────────────────┐
│ AGENT 4-STATE MODEL (LEGACY)                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  idle → active → completed                              │
│           ↓                                              │
│         failed                                           │
│                                                          │
│ LIMITATIONS:                                             │
│  - No "waiting" state (before active)                   │
│  - No "blocked" state (temporary pause)                 │
│  - No "cancelled" state (explicit termination)          │
│  - No "decommissioned" state (project closeout)         │
│  - Cannot track reason for failure                      │
│  - No structured metadata (plain text)                  │
└─────────────────────────────────────────────────────────┘
```

### After Migration: MCPAgentJob (7 States)

```
┌─────────────────────────────────────────────────────────┐
│ MCPAGENTJOB 7-STATE MODEL (MODERN)                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  waiting → working → blocked                            │
│              ↓         ↓                                 │
│           complete  working (resume)                     │
│              ↓                                           │
│           decommissioned (project close)                 │
│                                                          │
│  Any state → cancelled (explicit termination)            │
│  Any state → failed (with failure_reason)                │
│                                                          │
│ FEATURES:                                                │
│  ✓ waiting: Job queued, not started                     │
│  ✓ working: Actively executing                          │
│  ✓ blocked: Paused (waiting for dependency)             │
│  ✓ complete: Finished successfully                      │
│  ✓ failed: Error occurred (with reason)                 │
│  ✓ cancelled: Explicitly terminated by user             │
│  ✓ decommissioned: Project closed gracefully            │
│  ✓ failure_reason: Detailed error tracking              │
│  ✓ job_metadata: JSONB structured data                  │
│  ✓ decommissioned_at: Audit trail                       │
└─────────────────────────────────────────────────────────┘
```

---

## Data Flow Changes

### Before Migration

```
┌─────────────────────────────────────────────────────────┐
│ LEGACY DATA FLOW (DISCONNECTED)                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Orchestrator → create_agent_job()                      │
│                      ↓                                   │
│              MCPAgentJob created                         │
│                      ↓                                   │
│              get_agent_status()  ← Legacy MCP tool       │
│                      ↓                                   │
│              Queries agents table ← WRONG TABLE          │
│                      ↓                                   │
│              Returns 4-state status                      │
│                      ↓                                   │
│              Dashboard shows nothing (not synced)        │
│                                                          │
│  PROBLEM: Two tables, data disconnect, invisible to UI   │
└─────────────────────────────────────────────────────────┘
```

### After Migration

```
┌─────────────────────────────────────────────────────────┐
│ MODERN DATA FLOW (UNIFIED)                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Orchestrator → create_agent_job()                      │
│                      ↓                                   │
│              MCPAgentJob created                         │
│                      ↓                                   │
│              get_mcp_agent_job_status() ← Modern tool    │
│                      ↓                                   │
│              Queries mcp_agent_jobs table ← CORRECT      │
│                      ↓                                   │
│              Returns 7-state status                      │
│                      ↓                                   │
│              Dashboard updates (WebSocket)               │
│                      ↓                                   │
│              Real-time visibility                        │
│                                                          │
│  BENEFIT: Single table, unified data, dashboard-visible  │
└─────────────────────────────────────────────────────────┘
```

---

## Query Examples

### Before Migration: Querying Agent Status (WRONG)

```python
# Legacy tool - queries wrong table
def get_agent_status(job_id: str) -> dict:
    """Get agent status from agents table (4-state model)."""
    agent = db.query(Agent).filter(Agent.job_id == job_id).first()

    if not agent:
        return {"status": "not_found"}

    return {
        "status": agent.status,  # idle, active, completed, failed
        "context_used": agent.context_used,
        "last_active": agent.last_active,
        # No failure_reason available
        # No structured metadata
        # Not visible on dashboard
    }
```

**Issues:**
- Queries wrong table (not dashboard-visible)
- 4-state model too simple
- No failure reason
- No structured metadata
- Dashboard shows nothing

---

### After Migration: Querying Agent Status (CORRECT)

```python
# Modern tool - queries correct table
def get_mcp_agent_job_status(job_id: str) -> dict:
    """Get agent job status from mcp_agent_jobs table (7-state model)."""
    job = db.query(MCPAgentJob).filter(MCPAgentJob.job_id == job_id).first()

    if not job:
        return {"status": "not_found"}

    return {
        "status": job.status,  # waiting, working, blocked, complete, failed, cancelled, decommissioned
        "failure_reason": job.failure_reason,  # If failed
        "job_metadata": job.job_metadata,  # JSONB structured data
        "decommissioned_at": job.decommissioned_at,  # If decommissioned
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        # Dashboard-visible (WebSocket updates)
        # Legacy data available in job_metadata['legacy_agent_data']
    }
```

**Benefits:**
- Queries correct table (dashboard-visible)
- 7-state model supports complex workflows
- Failure reason tracked
- Structured JSONB metadata
- Dashboard shows real-time updates
- Legacy data preserved

---

### Legacy Data Access (After Migration)

```python
# Access legacy Agent data from MCPAgentJob.job_metadata
job = db.query(MCPAgentJob).filter(MCPAgentJob.job_id == job_id).first()

if job.job_metadata and 'legacy_agent_data' in job.job_metadata:
    legacy_data = job.job_metadata['legacy_agent_data']

    # Available fields:
    legacy_agent_id = legacy_data.get('agent_id')  # Original Agent.id
    legacy_status = legacy_data.get('legacy_status')  # Original Agent.status
    legacy_context = legacy_data.get('context_used')  # Original Agent.context_used
    legacy_active = legacy_data.get('last_active')  # Original Agent.last_active
    legacy_meta = legacy_data.get('meta_data')  # Original Agent.meta_data
    migrated_at = legacy_data.get('migrated_at')  # Migration timestamp
```

---

## Foreign Key Changes

### Before Migration: FK Dependencies

```sql
-- 6 tables with FK constraints to agents.id
messages.from_agent_id → agents.id
jobs.agent_id → agents.id
agent_interactions.parent_agent_id → agents.id
template_usage_stats.agent_id → agents.id
git_commits.agent_id → agents.id
optimization_metrics.agent_id → agents.id
```

**Status:** All FK constraints removed in migration `0116_remove_fk`

---

### After Migration: No FK Dependencies

```sql
-- All agent_id columns set to NULL
-- No FK constraints to agents table
-- MCPAgentJob FK constraints preserved:

mcp_agent_jobs.product_id → products.id
mcp_agent_jobs.project_id → projects.id
```

**Status:** Clean schema, no orphaned references

---

## Index Changes

### Before Migration

```sql
-- agents table indexes (DROPPED)
idx_agents_tenant_key ON agents(tenant_key)
idx_agents_job_id ON agents(job_id)
idx_agents_status ON agents(status)

-- mcp_agent_jobs table indexes (PRESERVED)
idx_mcp_agent_jobs_tenant_key ON mcp_agent_jobs(tenant_key)
idx_mcp_agent_jobs_job_id ON mcp_agent_jobs(job_id)
idx_mcp_agent_jobs_status ON mcp_agent_jobs(status)
idx_mcp_agent_jobs_product_id ON mcp_agent_jobs(product_id)
idx_mcp_agent_jobs_project_id ON mcp_agent_jobs(project_id)
idx_mcp_agent_jobs_metadata ON mcp_agent_jobs USING gin(job_metadata)
```

### After Migration

```sql
-- mcp_agent_jobs table indexes ONLY
idx_mcp_agent_jobs_tenant_key ON mcp_agent_jobs(tenant_key)
idx_mcp_agent_jobs_job_id ON mcp_agent_jobs(job_id)
idx_mcp_agent_jobs_status ON mcp_agent_jobs(status)
idx_mcp_agent_jobs_product_id ON mcp_agent_jobs(product_id)
idx_mcp_agent_jobs_project_id ON mcp_agent_jobs(project_id)
idx_mcp_agent_jobs_metadata ON mcp_agent_jobs USING gin(job_metadata)
  ↑ GIN index enables efficient JSONB queries (including legacy_agent_data)
```

---

## Backup Table Structure

### agents_backup_final (30-day retention)

```sql
-- Exact copy of agents table at migration time
-- Same schema as original agents table
-- Includes all records (migrated + orphaned)
-- Has table comment: 'Backup of agents table before Handover 0116 drop.
--                     Created 2025-11-07. Safe to drop after 2025-12-07 (30 days).'

-- Query example (read-only):
SELECT * FROM agents_backup_final WHERE job_id = 'some-job-id';

-- DROP after 30 days (2025-12-07):
DROP TABLE agents_backup_final;
```

---

## Summary

| Aspect | Before Migration | After Migration |
|--------|------------------|-----------------|
| **Tables** | agents + mcp_agent_jobs | mcp_agent_jobs only (+ backup) |
| **State Model** | 4 states (idle, active, completed, failed) | 7 states (waiting, working, blocked, complete, failed, cancelled, decommissioned) |
| **Dashboard** | Not visible | Real-time visible |
| **Tools** | Legacy (wrong table) + Modern | Modern only (correct table) |
| **Metadata** | Text (unstructured) | JSONB (structured) |
| **Failure Tracking** | No | Yes (failure_reason field) |
| **Decommission** | No | Yes (decommissioned_at field) |
| **FK Constraints** | 6 tables depend on agents.id | None (all removed) |
| **Indexes** | 3 on agents + 6 on mcp_agent_jobs | 6 on mcp_agent_jobs only |
| **Data Disconnect** | Yes (two sources of truth) | No (single source of truth) |

---

**Document Version:** 1.0
**Created:** 2025-11-07
**Migration ID:** 0116b_drop_agents
