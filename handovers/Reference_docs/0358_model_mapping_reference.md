# Reference: MCPAgentJob to AgentJob + AgentExecution Mapping

**Purpose**: Complete field mapping and query translation guide for 0358 series handovers  
**Last Updated**: 2025-12-20  
**Migration**: From legacy MCPAgentJob to AgentJob + AgentExecution identity model

---

## Executive Summary

This document provides the authoritative mapping of ALL 44 fields from MCPAgentJob to the new two-table identity model. Use this as your primary reference when migrating services, endpoints, MCP tools, and frontend components during the 0358 series.

**Key Changes**:
- 44 fields split into 41 fields across 2 tables (3 removed)
- job_id semantic shift: executor ID to work order ID (CRITICAL)
- agent_id introduced as new executor identity
- Mission storage: duplicated per instance to stored once
- Status values: 7 states to 3 job states + 7 execution states

## Model Architecture Comparison

### Legacy: Single Monolithic Table

MCPAgentJob (44 fields)
- Work Order Fields: mission, agent_type  
- Executor Fields: status, progress, current_task  
- Succession Fields: instance_number, handover_to  
- Problem: Mixed concerns, data duplication

### New: Separated Concerns

AgentJob (11 fields - WHAT)
- job_id (PK) - work order identity
- mission (stored once)
- job_type (what work)
- status (3 values: active, completed, cancelled)

AgentExecution (30 fields - WHO)
- agent_id (PK) - executor identity  
- job_id (FK to AgentJob)
- agent_type (who executes)
- status (7 values: waiting, working, etc.)
- progress, current_task, instance_number
- spawned_by, succeeded_by (both agent_id)

## CRITICAL: job_id Semantic Shift

**Legacy MCPAgentJob**:
- job_id = executor identity
- Changes with each succession (orch-001, orch-002, etc.)
- Each instance gets new job_id

**New Agent Identity Model**:
- job_id = work order identity (persistent)
- agent_id = executor identity (changes on succession)
- Succession: new agent_id, SAME job_id

**Example**:
Legacy: job_id changes (orch-001 -> orch-002 -> orch-003)
New:    job_id stays (build-auth), agent_id changes (orch-001 -> orch-002 -> orch-003)

**Impact**: ALL spawn tracking, succession, and handover code must use agent_id instead of job_id

## Complete Field Mapping Table

| MCPAgentJob | AgentJob | AgentExecution | Notes |
|-------------|----------|----------------|-------|
| id | - | - | REMOVED (UUIDs only) |
| job_id | job_id (PK) | job_id (FK) | SEMANTIC: executor -> work order |
| tenant_key | tenant_key | tenant_key | Both tables (multi-tenant) |
| project_id | project_id | - | Job-level only |
| agent_type | job_type | agent_type | SPLIT: WHAT vs WHO |
| mission | mission | - | Stored ONCE in job |
| status | status | status | Different sets (3 vs 7) |
| failure_reason | - | failure_reason | Execution-level |
| spawned_by | - | spawned_by | NOW agent_id (was job_id) |
| context_chunks | - | - | REMOVED |
| messages | - | messages | Execution-level |
| started_at | - | started_at | Execution-level |
| completed_at | completed_at | completed_at | Both tables |
| created_at | created_at | - | Job-level |
| progress | - | progress | Execution-level |
| block_reason | - | block_reason | Execution-level |
| current_task | - | current_task | Execution-level |
| estimated_completion | - | - | REMOVED |
| tool_type | - | tool_type | Execution-level |
| agent_name | - | agent_name | Execution-level |
| instance_number | - | instance_number | Execution-level |
| handover_to | - | succeeded_by | RENAMED + agent_id |
| handover_summary | - | handover_summary | Execution-level |
| handover_context_refs | - | - | REMOVED |
| succession_reason | - | succession_reason | Execution-level |
| context_used | - | context_used | Execution-level |
| context_budget | - | context_budget | Execution-level |
| job_metadata | job_metadata | - | Job-level |
| last_health_check | - | last_health_check | Execution-level |
| health_status | - | health_status | Execution-level |
| health_failure_count | - | health_failure_count | Execution-level |
| last_progress_at | - | last_progress_at | Execution-level |
| last_message_check_at | - | last_message_check_at | Execution-level |
| decommissioned_at | - | decommissioned_at | Execution-level |
| mission_acknowledged_at | - | mission_acknowledged_at | Execution-level |
| template_id | template_id | - | Job-level |
| (NEW) | - | succeeded_by | Forward succession link |

**Removed Fields**: id, context_chunks, handover_context_refs, estimated_completion

## Status Value Mapping

**MCPAgentJob Status** (7 execution states):
waiting | working | blocked | complete | failed | cancelled | decommissioned

**AgentJob Status** (3 job states):
active | completed | cancelled

**AgentExecution Status** (7 execution states):
waiting | working | blocked | complete | failed | cancelled | decommissioned

**Mapping Strategy**:
- MCPAgentJob.status -> AgentExecution.status (direct 1:1)
- AgentJob.status derived from executions:
  - active: ANY execution in [waiting, working, blocked]
  - completed: ALL executions in [complete, decommissioned]
  - cancelled: ALL executions in [failed, cancelled]

## Critical Gotchas

1. **job_id Semantic Shift**: executor ID -> work order ID
2. **spawned_by Change**: job_id -> agent_id  
3. **handover_to Renamed**: -> succeeded_by (agent_id)
4. **Mission Location**: job.mission (execution.mission does not exist)
5. **Two-Step Creation**: MUST create job + execution
6. **Status Values**: 3 job vs 7 execution states
7. **Queries Need Joins**: For executor data
8. **Tenant Filtering**: BOTH tables in joins (security!)

## Migration Checklist

- [ ] Find all MCPAgentJob imports/references
- [ ] Determine job vs execution data needs
- [ ] Replace single-table queries with joins
- [ ] Update job_id semantics (work order not executor)
- [ ] Split agent_type -> job_type/agent_type
- [ ] Update creation (two-step: job + execution)
- [ ] Update succession (new execution, same job)
- [ ] Change handover_to -> succeeded_by (agent_id)
- [ ] Change spawned_by to agent_id
- [ ] Verify tenant_key on BOTH tables
- [ ] Update status value sets
- [ ] Test succession (job_id persistence)
- [ ] Verify no mission duplication

## Resources

- **Handover 0366a**: Schema and models definition
- **Handover 0358**: Migration roadmap
- **Handover 0366b**: Service layer updates
- **DATABASE_SCHEMA_MAP_0366.md**: Complete schema reference
- **UUID_INDEX_0366.md**: UUID standardization

---

**Status**: Complete  
**Maintained By**: System Architect Agent  
**Series**: 0358 Migration

