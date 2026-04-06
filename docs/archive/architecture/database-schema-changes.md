# Database Schema Changes - Unified Agent State Architecture

## Overview

This document details all database schema modifications required for ADR-0108.

## 1. AgentJob Table Modifications (mcp_agent_jobs)

### Add Optimistic Locking Field

```sql
-- Add version field for optimistic locking
ALTER TABLE mcp_agent_jobs 
ADD COLUMN version INTEGER DEFAULT 1 NOT NULL;

-- Create index for version-based queries
CREATE INDEX idx_mcp_agent_jobs_version 
ON mcp_agent_jobs(job_id, version);
```

### Update Status Constraint

```sql
-- Drop old constraint
ALTER TABLE mcp_agent_jobs 
DROP CONSTRAINT IF EXISTS ck_mcp_agent_job_status;

-- Add new constraint with updated status values
ALTER TABLE mcp_agent_jobs 
ADD CONSTRAINT ck_mcp_agent_job_status
CHECK (status IN (
    'waiting', 'preparing', 'working', 'review',
    'blocked', 'complete', 'failed', 'cancelled', 'decommissioned'
));
```

### Add Cancellation Fields

```sql
ALTER TABLE mcp_agent_jobs 
ADD COLUMN cancelled_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

ALTER TABLE mcp_agent_jobs 
ADD COLUMN cancellation_reason TEXT DEFAULT NULL;
```

### Performance Indexes

```sql
-- Active jobs only (partial index)
CREATE INDEX idx_mcp_agent_jobs_active_status_tenant
ON mcp_agent_jobs(status, tenant_key, project_id)
WHERE status NOT IN ('complete', 'failed', 'cancelled', 'decommissioned');

-- Health monitoring (partial index)
CREATE INDEX idx_mcp_agent_jobs_health_check
ON mcp_agent_jobs(last_health_check, health_status, status)
WHERE health_status IN ('warning', 'critical', 'timeout')
  AND status NOT IN ('complete', 'failed', 'cancelled', 'decommissioned');
```

## Rollback Procedures

```sql
-- Remove new fields
ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS version;
ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS cancelled_at;
ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS cancellation_reason;

-- Restore old constraint
ALTER TABLE mcp_agent_jobs DROP CONSTRAINT IF EXISTS ck_mcp_agent_job_status;
ALTER TABLE mcp_agent_jobs ADD CONSTRAINT ck_mcp_agent_job_status
CHECK (status IN (
    'waiting', 'preparing', 'active', 'working', 
    'review', 'complete', 'failed', 'blocked', 'cancelling'
));
```
