# ADR-0108: Unified Agent State Architecture

**Status:** Superseded by Handover 0366a
**Date:** 2025-01-07
**Superseded:** 2025-12-21 (Handover 0366a - AgentJob + AgentExecution architecture)
**Architect:** System Architect Agent
**Related:** Handover 0107 (Cancellation), Handover 0106 (Health Monitoring)

> **⚠️ SUPERSEDED (Dec 2025 - Handover 0366a)**
>
> This ADR described the MCPAgentJob unified state model, which has been replaced by
> the AgentJob (work order) + AgentExecution (executor instance) architecture.
>
> **New Architecture:**
> - `job_id` = The work to be done (persists across succession)
> - `agent_id` = The executor doing the work (changes on succession)
>
> **Migration:** MCPAgentJob is deprecated as of v3.3.0, will be removed in v4.0.
>
> See Handover 0366 series for the new architecture.

## Decision

Standardize on MCPAgentJob as the authoritative agent state model with 9 well-defined status states.

## Status States

### Active States
- waiting - Job created, awaiting acknowledgment
- preparing - Agent setting up environment
- working - Agent actively executing
- review - Work complete, awaiting human review
- blocked - Agent blocked, needs human input

### Terminal States
- complete - Mission successfully completed
- failed - Mission failed due to errors
- cancelled - User cancelled job
- decommissioned - Agent permanently retired

## State Transitions

Valid transitions:
- waiting -> preparing, failed, cancelled
- preparing -> working, failed, cancelled
- working -> review, complete, failed, blocked, cancelled
- review -> complete, working, failed
- blocked -> working, cancelled, failed
- Terminal states -> NO TRANSITIONS

## Components

### StateTransitionManager
Location: src/giljo_mcp/state_manager.py
- Validate transitions
- Optimistic locking via version field
- Audit trail in job_metadata
- WebSocket broadcasting

### MessageInterceptor
Location: src/giljo_mcp/message_interceptor.py
- Block messages to terminal agents
- Auto-responses for cancelled/decommissioned
- Audit logging

### Health Monitor Integration
Location: src/giljo_mcp/monitoring/agent_health_monitor.py
- waiting timeout -> failed
- preparing timeout -> failed
- working timeout/critical -> blocked

## Database Changes

Add version field for optimistic locking:
ALTER TABLE mcp_agent_jobs ADD COLUMN version INTEGER DEFAULT 1;

Update status constraint:
ALTER TABLE mcp_agent_jobs DROP CONSTRAINT ck_mcp_agent_job_status;
ALTER TABLE mcp_agent_jobs ADD CONSTRAINT ck_mcp_agent_job_status
  CHECK (status IN (waiting, preparing, working, review, blocked,
                    complete, failed, cancelled, decommissioned));

Add cancellation fields:
ALTER TABLE mcp_agent_jobs ADD COLUMN cancelled_at TIMESTAMP;
ALTER TABLE mcp_agent_jobs ADD COLUMN cancellation_reason TEXT;

## API Endpoints

POST /{job_id}/transition - Validated state transitions (NEW)
POST /{job_id}/cancel - Enhanced with cancelled status
POST /{job_id}/decommission - Permanently retire agent (NEW)

## Migration Timeline

Week 1: Database schema changes
Week 2: Deploy core components
Week 3-4: Migrate Agent model to MCPAgentJob

## Risk Assessment

Risk Level: MEDIUM
Recommendation: APPROVE with phased rollout
