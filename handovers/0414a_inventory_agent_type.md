# Phase 0414a: Complete Inventory of agent_type Occurrences

**Status**: COMPLETED
**Generated**: 2026-01-11
**Next Phase**: 0414b (Write TDD tests)

---

## Tenant Key & User Relationships

### How agent_type Flows Through Multi-Tenant Architecture

**Database Layer**:
- `agent_executions.tenant_key` - tenant isolation
- `agent_executions.agent_type` - display name for the agent
- Both fields required for multi-tenant queries

**API Layer**:
- All queries filter by `tenant_key` AND may filter by `agent_type`
- Example: `get_active_jobs(session, tenant_key, agent_type)`
- Example: `get_job_statistics(session, tenant_key, agent_type)`

**WebSocket Events**:
- All broadcasts include `tenant_key` for tenant-scoped delivery
- `agent_type` included in event payloads for UI display
- Events: `agent:spawn`, `agent:complete`, `agent:update`, `agent:status_changed`

**MCP Tools**:
- `spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key)`
- `get_pending_jobs(agent_type, tenant_key)`
- Both parameters required for tenant-isolated operations

### Key Files for Tenant + agent_type Integration

| File | Pattern | Lines |
|------|---------|-------|
| `src/giljo_mcp/agent_job_manager.py` | `tenant_key, agent_type=` | 151 |
| `src/giljo_mcp/repositories/agent_job_repository.py` | `.where(Job.tenant_key == tenant_key)` + agent_type filter | 127, 262, 290 |
| `src/giljo_mcp/services/orchestration_service.py` | `get_pending_jobs(agent_type, tenant_key)` | 978 |
| `src/giljo_mcp/tools/agent_coordination.py` | `get_pending_jobs(agent_type, tenant_key)` | 539, 595 |
| `src/giljo_mcp/tools/orchestration.py` | `spawn_agent_job(..., tenant_key)` | 2564, 2575 |
| `api/endpoints/agent_management.py` | `get_active_jobs(db, tenant_key, agent_type)` | 113 |
| `api/endpoints/mcp_http.py` | `"required": ["agent_type", "tenant_key"]` | 297, 389 |

### WebSocket Event Payloads with agent_type

```python
# agent:status_changed event (api/events/schemas.py:231)
{
    "event_type": "agent:status_changed",
    "tenant_key": "tenant_abc",
    "data": {
        "agent_id": "uuid",
        "agent_type": "orchestrator",  # <-- TO BE RENAMED
        "status": "working",
        ...
    }
}
```

---

## Executive Summary

This inventory documents **ALL** occurrences of `agent_type` across the GiljoAI MCP codebase as Phase 0414a of Handover 0414 (agent_type to agent_display_name migration).

### Key Finding: Dual-Model Architecture

The codebase has a **dual-model architecture** (Handover 0366a):
- **AgentJob** (work order): Uses `job_type` column (NOT `agent_type`) - **DO NOT RENAME**
- **AgentExecution** (executor): Uses `agent_type` column - **RENAME to `agent_display_name`**

### Database Verification (2026-01-11)

```
agent_executions table:
  agent_type              | character varying(100)   | not null
  agent_name              | character varying(255)   |          <-- Template lookup key (NORTH STAR)

agent_jobs table:
  job_type                | character varying(100)   | not null  <-- DIFFERENT FIELD, DO NOT RENAME
```

### Scope Summary (VERIFIED COUNTS)

| Category | File Count | Occurrence Count |
|----------|------------|------------------|
| DATABASE | 2 | 6 |
| API_SCHEMA | 8 | 14 |
| WEBSOCKET_EVENTS | 3 | 20+ |
| SERVICE_LAYER | 8 | 100+ |
| MCP_TOOLS | 8 | 80+ |
| FRONTEND | 20+ | 151 |
| API_ENDPOINTS | 12 | 60+ |
| COMPOUND_VARIABLES | 8 | 15 |
| FUNCTION_NAMES | 6 | 12 |
| BACKEND_TOTAL | ~80 | ~420 |
| TEST_FIXTURES | 50+ | ~961 |
| **GRAND TOTAL** | **~150** | **~1,532** |

### Additional Patterns Found (Thorough Search)

**Property Access Patterns (`.agent_type`):**
- Backend: 50+ occurrences across services, tools, repositories
- Frontend: 80+ occurrences across Vue components

**Compound Variable Names:**
- `by_agent_type` - dictionary key in repository
- `sender_agent_type` - variable in message_service.py
- `agent_type_query` - variable in filters.py
- `agent_type_result` - variable in filters.py
- `agent_type_usage` - documentation key in tool_accessor.py
- `max_agent_types` - config key in orchestration.py

**Function Names (to consider renaming):**
- `getAgentType()` - MessageStream.vue
- `getAgentTypeColor()` - AgentDetailsModal.vue, AgentTableView.vue, useAgentData.js
- `agentTypeLabel` - computed property in AgentCard.vue
- `formatAgentName(agentType)` - MessageStream.vue param (keep param name)

---

## Category 1: DATABASE (Priority 1)

### SQLAlchemy Models

| File | Line | Type | Context | Migration Action |
|------|------|------|---------|------------------|
| `src/giljo_mcp/models/agent_identity.py` | 170-174 | Column | `agent_type = Column(String(100), nullable=False, comment="Agent type: orchestrator, analyzer, implementer, tester, etc.")` | **RENAME to agent_display_name** |
| `src/giljo_mcp/models/agent_identity.py` | 341 | __repr__ | `f"agent_type={self.agent_type}"` | RENAME |

### Migrations

| File | Line | Type | Context | Migration Action |
|------|------|------|---------|------------------|
| `migrations/versions/caeddfdbb2a0_unified_baseline_all_tables.py` | 630 | Column | `sa.Column('agent_type', sa.String(length=100), nullable=False)` in agent_executions | RENAME |
| `migrations/versions/caeddfdbb2a0_unified_baseline_all_tables.py` | 677 | Index | `idx_agent_jobs_instance` on `['project_id', 'agent_type', 'instance_number']` | UPDATE index |
| `migrations/versions/caeddfdbb2a0_unified_baseline_all_tables.py` | 686 | Index | `idx_mcp_agent_jobs_tenant_type` on `['tenant_key', 'agent_type']` | UPDATE index |

**Note**: Index names reference `agent_type` - these need updating in migration.

---

## Category 2: API_SCHEMA (Priority 1)

### Pydantic Request/Response Models

| File | Line | Type | Context | Migration Action |
|------|------|------|---------|------------------|
| `api/endpoints/agent_management.py` | 58 | Field | `agent_type: str = Field(..., description="Agent type")` | RENAME |
| `api/endpoints/agent_management.py` | 66 | Field | `agent_type: str` | RENAME |
| `api/schemas/agent_job.py` | 25 | Field | `agent_type: str = Field(...)` | RENAME |
| `api/schemas/agent_job.py` | 58 | Field | `agent_type: str = Field(..., description="Agent type")` | RENAME |
| `api/schemas/agent_job.py` | 131 | Field | `agent_type: str = Field(..., min_length=1, max_length=100, description="Agent type for child job")` | RENAME |
| `api/schemas/prompt.py` | 55 | Field | `agent_type: str = Field(..., description="Agent type")` | RENAME |
| `api/endpoints/context.py` | 69 | Field | `agent_type: str = Field(..., description="Type of agent")` | RENAME |
| `api/endpoints/context.py` | 76 | Field | `agent_type: str` | RENAME |
| `api/endpoints/agent_jobs/models.py` | 21 | Field | `agent_type: str = Field(..., description="Agent type")` | RENAME |
| `api/endpoints/agent_jobs/models.py` | 94 | Field | `agent_type: str` | RENAME |
| `api/endpoints/agent_jobs/orchestration.py` | 67 | Field | `agent_type: str` | RENAME |
| `api/endpoints/agent_jobs/table_view.py` | 42 | Field | `agent_type: str` | RENAME |
| `api/endpoints/projects/models.py` | 51 | Field | `agent_type: str` | RENAME |
| `api/endpoints/projects/models.py` | 202 | Field | `agent_type: str` | RENAME |

---

## Category 3: WEBSOCKET_EVENTS (Priority 1)

### Event Schemas

| File | Line | Type | Context | Migration Action |
|------|------|------|---------|------------------|
| `api/events/schemas.py` | 176 | Validation | `required_fields = ["id", "agent_type", "status"]` | RENAME |
| `api/events/schemas.py` | 207 | Example | `"agent_type": "orchestrator"` | RENAME |
| `api/events/schemas.py` | 231 | Field | `agent_type: str = Field(..., min_length=1, description="Type of agent")` | RENAME |
| `api/events/schemas.py` | 281 | Example | `"agent_type": "orchestrator"` | RENAME |
| `api/events/schemas.py` | 509 | Docstring | `agent: Complete agent job data (must include: id, agent_type, status)` | RENAME |
| `api/events/schemas.py` | 523 | Example | `"agent_type": "orchestrator"` | RENAME |
| `api/events/schemas.py` | 549 | Parameter | `agent_type: str,` | RENAME |
| `api/events/schemas.py` | 561 | Docstring | `agent_type: Type of agent` | RENAME |
| `api/events/schemas.py` | 577 | Example | `agent_type="orchestrator"` | RENAME |
| `api/events/schemas.py` | 594 | Usage | `agent_type=agent_type` | RENAME |

### WebSocket Handlers

| File | Line | Type | Context | Migration Action |
|------|------|------|---------|------------------|
| `api/websocket.py` | 847, 865, 886, 896, 902, 914, 1169, 1176, 1203, 1210 | Param/Dict | WebSocket broadcast payloads | RENAME all |
| `api/websocket_event_listener.py` | 169, 191 | Dict key | `"agent_type": data.get("agent_type", "unknown")` | RENAME |

---

## Category 4: SERVICE_LAYER (Priority 1)

### Core Services

| File | Lines | Migration Action |
|------|-------|------------------|
| `src/giljo_mcp/agent_job_manager.py` | 99, 110, 125-126, 133, 151, 167, 188-189, 196, 635, 643, 655-656, 676, 684, 696-697 | RENAME |
| `src/giljo_mcp/services/agent_job_manager.py` | 94, 114, 129, 143, 153, 170, 177, 618, 631, 647, 676 | RENAME |
| `src/giljo_mcp/services/orchestration_service.py` | 74-106, 136-139, 549, 565, 578, 632, 641, 652, 660, 677, 705, 716, 871, 899, 955, 963-964, 978, 988, 996, 1002-1003, 1015, 1029, 1104, 1130, 1146, 1320, 1457, 1539, 1559, 1598-1599, 1619, 1653, 1846 | RENAME |
| `src/giljo_mcp/services/message_service.py` | 160, 181, 194, 204, 210, 298, 301, 305, 406, 413, 461, 1194, 1262 | RENAME |
| `src/giljo_mcp/services/project_service.py` | 232, 1711, 1741 | RENAME |

### Repositories

| File | Lines | Migration Action |
|------|-------|------------------|
| `src/giljo_mcp/repositories/agent_job_repository.py` | 41, 52, 63, 127, 134, 141-142, 262, 269, 276-277, 283-284, 290, 297 | RENAME |

### Other Modules

| File | Lines | Migration Action |
|------|-------|------------------|
| `src/giljo_mcp/job_coordinator.py` | 66, 92-93, 102, 243, 290 | RENAME |
| `src/giljo_mcp/orchestrator_succession.py` | 208, 443 | RENAME |
| `src/giljo_mcp/staging_rollback.py` | 138, 263, 344, 392 | RENAME |
| `src/giljo_mcp/job_monitoring.py` | 136 | RENAME |
| `src/giljo_mcp/monitoring/agent_health_monitor.py` | 189, 260, 310, 319, 348, 380, 388 | RENAME |
| `src/giljo_mcp/orchestrator.py` | 1298, 1299, 1655, 1666 | RENAME |
| `src/giljo_mcp/thin_prompt_generator.py` | 194, 252, 1233 | RENAME |
| `src/giljo_mcp/slash_commands/handover.py` | 137 | RENAME |
| `src/giljo_mcp/prompt_generation/mcp_tool_catalog.py` | 158 | RENAME (agent_types extraction)

---

## Category 5: MCP_TOOLS (Priority 1)

### Primary Tool Files

| File | Lines | Migration Action |
|------|-------|------------------|
| `src/giljo_mcp/tools/orchestration.py` | 326, 566, 637, 645, 653-654, 755, 801, 835, 844, 896, 914, 926, 980, 988, 1001, 1004-1008, 2037, 2343, 2431-2432, 2529, 2543, 2564, 2575, 2581, 2605, 2608, 2626, 2638, 2645, 2654, 2706, 2719, 2792, 2812, 2815-2819 | RENAME |
| `src/giljo_mcp/tools/agent_coordination.py` | 76, 94, 124, 127, 178, 182, 236, 240, 294, 359, 397, 444, 472, 539, 547, 556, 578, 581, 595, 603, 613, 648, 699, 868, 906, 914 | RENAME |
| `src/giljo_mcp/tools/agent_coordination_external.py` | 283, 292, 310, 314-315, 321, 327, 404, 565, 572, 592-593, 596 | RENAME |
| `src/giljo_mcp/tools/agent_job_status.py` | 250, 342 | RENAME |
| `src/giljo_mcp/tools/context.py` | 1417, 1481, 1915, 1983 | RENAME |
| `src/giljo_mcp/tools/project.py` | 460 | RENAME |
| `src/giljo_mcp/tools/tool_accessor.py` | 819-820, 855, 864, 886, 888, 932, 1013, 1217 | RENAME |
| `src/giljo_mcp/tools/agent.py` | 224, 275 | RENAME |

### MCP HTTP Endpoints

| File | Lines | Migration Action |
|------|-------|------------------|
| `api/endpoints/mcp_http.py` | 294, 297, 383, 389 | RENAME |
| `api/endpoints/mcp_tools.py` | 345, 355, 365, 431, 438, 445 | RENAME |

---

## Category 6: FRONTEND (Priority 2)

### Vue Components

| File | Lines | Migration Action |
|------|-------|------------------|
| `frontend/src/components/AgentCard.vue` | 5, 406, 447 | RENAME |
| `frontend/src/components/projects/JobsTab.vue` | 23, 26-27, 30-35, 211, 281, 311-316, 749, 806, 835, 845, 1080, 1104 | RENAME |
| `frontend/src/components/projects/LaunchTab.vue` | 120, 122-123, 125-126, 240, 251, 345, 348, 426, 448 | RENAME |
| `frontend/src/components/orchestration/AgentTableView.vue` | 12-25, 197, 324 | RENAME |
| `frontend/src/components/orchestration/AgentCardGrid.vue` | 173, 193 | RENAME |
| `frontend/src/components/projects/AgentDetailsModal.vue` | 22-23, 313, 353, 355, 448 | RENAME |
| `frontend/src/components/projects/MessageInput.vue` | 108, 136 | RENAME |
| `frontend/src/components/projects/MessageStream.vue` | 49, 156, 223 | RENAME |
| `frontend/src/components/projects/ProjectTabs.vue` | 275 | RENAME |
| `frontend/src/components/projects/AgentMissionEditModal.vue` | 7 | RENAME |
| `frontend/src/components/projects/MessageAuditModal.vue` | 245 | RENAME |
| `frontend/src/components/projects/SuccessionTimeline.vue` | 33 | RENAME |
| `frontend/src/components/messages/MessageModal.vue` | 74 | RENAME |
| `frontend/src/components/StatusBoard/ActionIcons.vue` | 161 | RENAME |

### Stores & Composables

| File | Lines | Migration Action |
|------|-------|------------------|
| `frontend/src/stores/agentJobs.js` | 30, 55, 57, 155 | RENAME |
| `frontend/src/stores/agentJobsStore.js` | 107-108, 111, 245, 247 | RENAME |
| `frontend/src/composables/useStalenessMonitor.js` | 43, 46 | RENAME |
| `frontend/src/composables/useAgentData.js` | 46-47 | RENAME |
| `frontend/src/stores/websocketEventRouter.js` | 122, 127, 138, 142 | RENAME |

### Utils

| File | Lines | Migration Action |
|------|-------|------------------|
| `frontend/src/utils/actionConfig.js` | 68, 108, 114, 139, 188, 205 | RENAME |

---

## Category 7: API_ENDPOINTS (Priority 2)

| File | Lines | Migration Action |
|------|-------|------------------|
| `api/endpoints/agent_management.py` | 100, 113, 118, 151, 163, 175, 232, 277, 461, 474 | RENAME |
| `api/endpoints/agent_jobs/filters.py` | 34, 82-83, 87, 90-91, 136 | RENAME (including `agent_types` list) |
| `api/endpoints/agent_jobs/lifecycle.py` | 63, 75-76, 100 | RENAME |
| `api/endpoints/agent_jobs/status.py` | 47, 69, 86, 103, 111, 228 | RENAME |
| `api/endpoints/agent_jobs/succession.py` | 274, 388, 433 | RENAME |
| `api/endpoints/agent_jobs/table_view.py` | 9, 42, 98-99, 114, 149-151, 176-177, 249, 267 | RENAME |
| `api/endpoints/agent_jobs/operations.py` | 393 | RENAME |
| `api/endpoints/context.py` | 363, 379 | RENAME |
| `api/endpoints/prompts.py` | 287, 301, 307, 323, 336, 647, 679, 823, 869, 899-900 | RENAME |
| `api/endpoints/projects/status.py` | 178, 212 | RENAME |
| `api/endpoints/statistics.py` | 404 | RENAME |
| `api/endpoints/websocket_bridge.py` | 76 | RENAME |

---

## Category 8: TEST_FIXTURES (Priority 3)

### Backend Tests

| File | Approx. Occurrences | Migration Action |
|------|---------------------|------------------|
| `tests/conftest.py` | 1 | RENAME |
| `tests/api/test_jobs_endpoint_mission_acknowledged.py` | 17 | RENAME |
| `tests/api/test_implementation_prompt_api.py` | 9 | RENAME |
| `tests/api/test_filter_options.py` | 12 | RENAME |
| `tests/api/test_jobs_endpoint_message_counters.py` | 9 | RENAME |
| `tests/api/test_agent_jobs_mission.py` | 13 | RENAME |
| `tests/api/test_messages_api.py` | 3 | RENAME |
| `tests/api/test_mcp_messaging_tools.py` | 2 | RENAME |
| `tests/api/test_agent_jobs_api.py` | 12 | RENAME |
| `tests/api/test_0367b_mcpagentjob_removal.py` | 13 | RENAME |
| `tests/api/test_table_view_endpoint.py` | 20 | RENAME |
| `tests/helpers/test_factories.py` | 6 | RENAME |
| `tests/fixtures/base_fixtures.py` | 8 | RENAME |
| `tests/test_agent_job_manager.py` | 60+ | RENAME |
| `tests/test_agent_coordination_tools.py` | 40+ | RENAME |
| `tests/integration/test_agent_workflow.py` | 20+ | RENAME |
| `tests/models/test_agent_execution.py` | 30+ | RENAME |

### Frontend Tests (Specific Files Found)

| File | Approx. Occurrences | Migration Action |
|------|---------------------|------------------|
| `frontend/src/components/projects/JobsTab.integration.spec.js` | 10+ | RENAME |
| `frontend/src/components/projects/JobsTab.spec.js` | 15+ | RENAME |
| `frontend/src/components/projects/LaunchTab.test.js` | 5+ | RENAME (agentTypes variable) |
| `frontend/src/components/projects/__tests__/MessageStream.spec.js` | 5+ | RENAME (getAgentType tests) |
| `frontend/src/__tests__/components/*.spec.js` | Multiple | RENAME |
| `frontend/src/stores/*.spec.js` | Multiple | RENAME |
| `frontend/tests/e2e/*.spec.js` | Multiple | RENAME (selectors)

---

## Category 9: CASE VARIATIONS & COMPOUND NAMES

### agentType (camelCase local variables)

| File | Line | Context | Migration Action |
|------|------|---------|------------------|
| `frontend/src/components/projects/LaunchTab.vue` | 345 | `const agentType = agent.agent_type?.toLowerCase()` | RENAME source property |
| `frontend/src/components/projects/AgentDetailsModal.vue` | 355 | `const agentType = props.agent?.agent_type` | RENAME source property |
| `frontend/src/components/projects/ChatHeadBadge.vue` | 39, 83 | `agentType` prop definition | RENAME prop |

### agent-type (kebab-case in HTML/CSS)

| File | Context | Migration Action |
|------|---------|------------------|
| `frontend/src/components/projects/JobsTab.vue` | `:data-agent-type="agent.agent_type"` | RENAME to `data-agent-display-name` |
| `frontend/src/components/projects/JobsTab.vue` | `.agent-type-cell`, `.agent-type-secondary` CSS classes | RENAME |
| `frontend/src/components/projects/LaunchTab.vue` | `data-testid="agent-type"`, `.agent-type` class | RENAME |
| `frontend/src/components/projects/MessageStream.vue` | `:agent-type="getAgentType(message)"` | RENAME |
| E2E tests | `[data-agent-type="orchestrator"]` selectors | RENAME |

### AGENT_TYPE (constant case)

| File | Context | Migration Action |
|------|---------|------------------|
| `api/endpoints/prompts.py:307` | `export AGENT_TYPE={agent.agent_type}` (shell var) | RENAME |

### Compound Variable Names (Backend)

| File | Variable | Migration Action |
|------|----------|------------------|
| `src/giljo_mcp/repositories/agent_job_repository.py:297` | `by_agent_type` dict key | RENAME to `by_agent_display_name` |
| `src/giljo_mcp/services/message_service.py:298,301,305` | `sender_agent_type` variable | RENAME to `sender_agent_display_name` |
| `api/endpoints/agent_jobs/filters.py:82,90` | `agent_type_query`, `agent_type_result` | RENAME to `agent_display_name_*` |
| `src/giljo_mcp/tools/tool_accessor.py:819` | `agent_type_usage` doc key | RENAME |
| `src/giljo_mcp/tools/orchestration.py:2037` | `max_agent_types` config | RENAME to `max_agent_display_names` |

### Function/Method Names (Frontend)

| File | Function | Migration Action |
|------|----------|------------------|
| `frontend/src/components/projects/MessageStream.vue:222` | `getAgentType()` | RENAME to `getAgentDisplayName()` |
| `frontend/src/components/projects/MessageStream.vue:236` | `formatAgentName(agentType)` | RENAME param to `agentDisplayName` |
| `frontend/src/components/projects/AgentDetailsModal.vue:324` | `getAgentTypeColor(agentType)` | RENAME to `getAgentDisplayNameColor()` |
| `frontend/src/components/orchestration/AgentTableView.vue:180` | `getAgentTypeColor` import | RENAME |
| `frontend/src/composables/useAgentData.js:97,167` | `getAgentTypeColor()` | RENAME to `getAgentDisplayNameColor()` |
| `frontend/src/components/AgentCard.vue:449` | `agentTypeLabel` computed | RENAME to `agentDisplayNameLabel` |
| `frontend/src/components/projects/JobsTab.vue:571,588` | `getAgentColor(agentType)`, `getAgentAbbr(agentType)` | RENAME params |
| `frontend/src/components/projects/LaunchTab.vue:285,302` | `getAgentColor(agentType)`, `getAgentInitials(agentType)` | RENAME params |

---

## Category 10: ZOMBIE_CODE (0414c Candidates)

### CONFIRMED ZOMBIE CODE (Safe to Remove)

#### 1. WebSocket Manager - Unused Agent Broadcast Functions (~80 lines)

| File | Function | Lines | Reason | Action |
|------|----------|-------|--------|--------|
| `api/websocket.py` | `broadcast_agent_spawn()` | 640-679 | **ZERO production callers** - only called in tests | DELETE |
| `api/websocket.py` | `broadcast_agent_complete()` | 681-721 | **ZERO production callers** - only called in tests | DELETE |

**Evidence**: `grep -rn "broadcast_agent_spawn\|broadcast_agent_complete"` returns ONLY test files as callers.

#### 2. WebSocketService - Unused Helper Methods (~70 lines)

| File | Function | Lines | Reason | Action |
|------|----------|-------|--------|--------|
| `api/websocket_service.py` | `notify_agent_status()` | 16-42 | **ZERO callers** - WebSocketService not imported anywhere | DELETE |
| `api/websocket_service.py` | `notify_sub_agent_spawned()` | 191-216 | **ZERO callers** | DELETE |
| `api/websocket_service.py` | `notify_sub_agent_completed()` | 218-247 | **ZERO callers** | DELETE |

**Evidence**:
- `grep -rn "WebSocketService\."` returns ONLY self-references within websocket_service.py
- `WebSocketService` is never imported in production code (only 2 test files)

#### 3. Orchestrator - Dead Code Statements (~2 lines)

| File | Lines | Context | Reason | Action |
|------|-------|---------|--------|--------|
| `src/giljo_mcp/orchestrator.py` | 1298-1299 | `AgentRole(from_execution.agent_type)` | Creates enum but doesn't use result - DEAD CODE | DELETE |

**Code snippet**:
```python
# Line 1298-1299 - These statements do nothing!
AgentRole(from_execution.agent_type)  # Created but never used
AgentRole(to_execution.agent_type)    # Created but never used
context.get("summary", "Work completed by previous agent")  # Also unused!
```

### QUESTIONABLE CODE (Needs Analysis in 0414c)

#### 1. AgentRole Enum vs agent_type Field Mismatch

| Issue | Context | Risk |
|-------|---------|------|
| `AgentRole` enum has 6 values | orchestrator, analyzer, implementer, tester, reviewer, documenter |
| `agent_type` field stores custom names | tdd-implementor, backend-tester, deep-researcher, etc. |
| Enum conversion would FAIL | `AgentRole("tdd-implementor")` raises ValueError |

**Files affected**: `src/giljo_mcp/orchestrator.py:1298-1299` (dead code, but reveals misunderstanding)

### Archived Migrations (NO ACTION NEEDED)

| File | Context | Status |
|------|---------|--------|
| `migrations/archive/pre_baseline/0366a_split_agent_job.py` | Old migration | ARCHIVE ONLY |
| `migrations/archive/versions_pre_reset/f504ea46e988_baseline_schema_all_27_tables.py` | Pre-reset | ARCHIVE ONLY |

### Summary: Zombie Code to Remove in 0414c

| Category | Files | Lines | Effort |
|----------|-------|-------|--------|
| WebSocket broadcast functions | 1 | ~80 | LOW |
| WebSocketService methods | 1 | ~70 | LOW |
| Orchestrator dead statements | 1 | ~3 | LOW |
| Test updates for removed code | 3 | ~50 | MEDIUM |
| **TOTAL** | **6** | **~200** | **LOW-MEDIUM** |

---

## DO NOT RENAME (Different Semantic Meaning)

| Field | File | Reason |
|-------|------|--------|
| `AgentJob.job_type` | `src/giljo_mcp/models/agent_identity.py:75` | Different field - work order type, NOT executor type |
| `subagent_type` | `thin_prompt_generator.py`, tests | Different concept - Task tool parameter |
| `agent_types` (plural) | `api/endpoints/agent_jobs/filters.py:34` | Response field listing available types - RENAME to `agent_display_names` |

---

## Migration Dependency Order

Execute in this order to maintain application integrity:

1. **DATABASE** (Foundation)
   - Create Alembic migration to rename column
   - Update SQLAlchemy model column name

2. **API_SCHEMA** (Depends on DB)
   - All Pydantic models
   - WebSocket event schemas

3. **SERVICE_LAYER** (Depends on Schema)
   - orchestration_service.py
   - agent_job_manager.py
   - message_service.py
   - repositories

4. **MCP_TOOLS** (Depends on Service)
   - orchestration.py
   - agent_coordination.py
   - All other tool files

5. **API_ENDPOINTS** (Depends on all above)
   - All endpoint files

6. **FRONTEND** (Depends on API)
   - Stores, components, utils
   - E2E test selectors

7. **TESTS** (Final)
   - All test fixtures and assertions

---

## Approval Checklist

Before proceeding to Phase 0414b:

- [x] Database schema verified (agent_executions.agent_type exists)
- [x] All categories inventoried (10 categories)
- [x] Zombie code candidates identified
- [x] DO NOT RENAME items documented
- [x] Migration order defined
- [ ] **User approval to proceed**

---

## Next Steps

**Phase 0414b**: Write TDD tests (RED phase)
- Create test file: `tests/services/test_agent_display_name_migration.py`
- Tests should FAIL initially (agent_type still exists, agent_display_name doesn't)
- Cover: Model field, API response, WebSocket events, frontend props

**Phase 0414c**: Clean zombie code
**Phase 0414d**: Verify existing tests pass
**Phase 0414e**: Execute migration
**Phase 0414f**: Full E2E testing with Chrome extension
