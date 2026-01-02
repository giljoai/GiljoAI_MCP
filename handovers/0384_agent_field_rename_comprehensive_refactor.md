# Handover 0384: Agent Field Rename - Comprehensive Refactor

**Status**: Research Complete - Ready for Implementation Planning
**Date**: 2026-01-01
**Priority**: HIGH (v4.0 target)
**Estimated Hours**: 38-50 hours (1-2 weeks)
**Prerequisite**: Implement 0383 first (interim fix)

---

## Problem Statement

Alpha testing revealed orchestrator confusion between `agent_name` (template filename) and `agent_type` (UI category) when writing execution plans. The semantic similarity of these field names creates a footgun for AI agents.

### Proposed Rename

| Current | Proposed | Purpose |
|---------|----------|---------|
| `agent_name` | `template_name` | Template filename for Task tool (SINGLE SOURCE OF TRUTH) |
| `agent_type` | `agent_category` | Display category for UI grouping |

---

## Research Summary

Four parallel research agents analyzed the complete impact:

| Domain | Files Affected | Occurrences | Risk Level |
|--------|---------------|-------------|------------|
| **Frontend** | 78 files | 665 | HIGH |
| **Database** | 3 tables | 3 columns | MEDIUM-HIGH |
| **Backend** | 36 files | 282 | HIGH |
| **Prompts/Workflows** | 30+ files | Critical path | HIGH |
| **TOTAL** | ~150 files | ~1000+ references | **HIGH** |

---

## Impact Topology

```
                    ┌─────────────────────────────────────────┐
                    │         DATABASE LAYER                  │
                    │  AgentExecution: agent_type, agent_name │
                    │  AgentJob: job_type (related)           │
                    └──────────────────┬──────────────────────┘
                                       │
           ┌───────────────────────────┼───────────────────────────┐
           │                           │                           │
           ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  SERVICE LAYER   │       │   MCP TOOLS      │       │   API SCHEMAS    │
│ AgentJobManager  │       │ spawn_agent_job  │       │ SpawnRequest     │
│ OrchestrationSvc │       │ get_agent_mission│       │ JobResponse      │
│ MessageService   │       │ cli_mode_rules   │       │ ChildJobSpec     │
└────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           │                        │                        │
           ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ PROMPT TEMPLATES │    │  API ENDPOINTS   │    │ WEBSOCKET EVENTS │
│ thin_prompt_gen  │    │ /agent-jobs/*    │    │ agent:created    │
│ cli_mode_rules   │    │ /prompts/*       │    │ job:updated      │
│ staging prompt   │    │ /messages/*      │    │ agent:spawn      │
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────────────────┐
                    │            FRONTEND                     │
                    │  Vue Components (78 files)              │
                    │  Pinia Stores, Composables, Utils       │
                    │  WebSocket Event Handlers               │
                    └─────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────────────────────┐
                    │         CLAUDE CODE / CLI               │
                    │  Task(subagent_type=template_name)      │
                    │  .claude/agents/{template_name}.md      │
                    └─────────────────────────────────────────┘
```

---

## Detailed File Inventory

### Database Models (3 columns)

| File | Model | Column | New Name |
|------|-------|--------|----------|
| `src/giljo_mcp/models/agent_identity.py:164` | AgentExecution | `agent_type` | `agent_category` |
| `src/giljo_mcp/models/agent_identity.py:290` | AgentExecution | `agent_name` | `template_name` |
| `src/giljo_mcp/models/agents.py:38` | AgentInteraction | `sub_agent_name` | `sub_template_name` |

### Backend Services (5 files, ~50 occurrences)

| File | Key Methods |
|------|-------------|
| `src/giljo_mcp/services/agent_job_manager.py` | `create_job()`, `spawn_agent()` |
| `src/giljo_mcp/services/orchestration_service.py` | `spawn_agent()`, `get_pending_jobs()` |
| `src/giljo_mcp/services/message_service.py` | `get_messages()`, agent resolution |
| `src/giljo_mcp/services/task_service.py` | `assign_task()` |
| `src/giljo_mcp/services/project_service.py` | Project launch |

### MCP Tools (8 files, ~95 occurrences)

| File | Tools Affected |
|------|----------------|
| `src/giljo_mcp/tools/orchestration.py` | `spawn_agent_job()`, validation logic |
| `src/giljo_mcp/tools/tool_accessor.py` | `cli_mode_rules`, `allowed_agent_names` |
| `src/giljo_mcp/tools/agent_coordination.py` | `register_agent_executor()`, `get_pending_jobs()` |
| `src/giljo_mcp/tools/agent_coordination_external.py` | `create_agent_job()` |
| `src/giljo_mcp/tools/agent.py` | Multiple agent lifecycle tools |
| `src/giljo_mcp/tools/agent_job_status.py` | Status responses |
| `src/giljo_mcp/tools/project.py` | Project launch |
| `src/giljo_mcp/tools/context.py` | Tool schema docs |

### API Endpoints (15 files, ~85 occurrences)

| File | Endpoints |
|------|-----------|
| `api/endpoints/agent_jobs/lifecycle.py` | `POST /spawn` |
| `api/endpoints/agent_jobs/models.py` | Pydantic models |
| `api/endpoints/agent_jobs/status.py` | `GET /status` |
| `api/endpoints/agent_jobs/table_view.py` | `GET /table` |
| `api/endpoints/agent_jobs/filters.py` | `GET /filters` |
| `api/endpoints/agent_management.py` | `GET /jobs`, `GET /statistics` |
| `api/endpoints/messages.py` | `GET /agent/{agent_name}` |
| `api/endpoints/mcp_http.py` | MCP JSON-RPC schema |
| `api/endpoints/mcp_tools.py` | Tool documentation |
| `api/endpoints/prompts.py` | Prompt generation |
| `api/schemas/agent_job.py` | Request/response schemas |
| `api/schemas/prompt.py` | Prompt schemas |

### Prompt Templates (Critical Path)

| File | Section | Impact |
|------|---------|--------|
| `src/giljo_mcp/tools/tool_accessor.py:792-804` | `cli_mode_rules` | CRITICAL - instructs AI agents |
| `src/giljo_mcp/thin_prompt_generator.py:984-989` | Staging prompt | Task tool instructions |
| `src/giljo_mcp/templates/generic_agent_template.py` | Agent protocol | Identity references |

### WebSocket Events (4 files, ~35 occurrences)

| Event | Fields |
|-------|--------|
| `agent:created` | `agent_type`, `agent_name` |
| `agent:spawn` | `agent_name` |
| `agent_job:created` | `agent_type`, `agent_name` |
| `sub_agent:spawn` | `parent_agent_name`, `sub_agent_name` |

### Frontend (78 files, 665 occurrences)

**High-Impact Components:**
| File | Occurrences |
|------|-------------|
| `frontend/src/components/projects/JobsTab.vue` | 15 |
| `frontend/src/components/projects/LaunchTab.vue` | 12 |
| `frontend/src/components/orchestration/AgentTableView.vue` | 10 |
| `frontend/src/stores/agentJobsStore.js` | 8 |
| `frontend/src/stores/agents.js` | 8 |
| `frontend/src/composables/useAgentData.js` | 7 |

**Test Files:** ~400+ occurrences across 50+ test files

### Documentation (30+ files)

| Area | Files |
|------|-------|
| API Reference | `docs/AGENT_JOBS_API_REFERENCE.md` |
| Orchestrator | `docs/ORCHESTRATOR.md` |
| CLAUDE.md | Quick reference section |
| Handovers | Historical references (leave as-is) |

---

## Critical Path: Task Tool Mapping

```
spawn_agent_job(template_name="implementer-frontend", agent_category="implementer")
                    │
                    ▼
            AgentExecution record created
                    │
                    ▼
    Orchestrator writes execution plan:
    Task(subagent_type="implementer-frontend", ...)  ← MUST use template_name
                    │
                    ▼
    Claude Code resolves:
    .claude/agents/implementer-frontend.md  ← Filename matching
```

**CRITICAL**: The `subagent_type` parameter MUST equal `template_name` (not `agent_category`).

---

## Migration Strategy

### Recommended: Blue-Green Migration (Safest)

#### Phase 1: Add New Columns (Week 1)
```sql
-- Add new columns alongside old
ALTER TABLE agent_executions ADD COLUMN agent_category VARCHAR(100);
ALTER TABLE agent_executions ADD COLUMN template_name VARCHAR(255);
ALTER TABLE agent_interactions ADD COLUMN sub_template_name VARCHAR(100);

-- Backfill from old columns
UPDATE agent_executions SET agent_category = agent_type, template_name = agent_name;
UPDATE agent_interactions SET sub_template_name = sub_agent_name;
```

#### Phase 2: Dual-Write Code (Week 1-2)
- Update all Python code to write to BOTH old and new columns
- Update API schemas to accept both field names
- Update cli_mode_rules to document both (deprecation warning for old)

#### Phase 3: Frontend Migration (Week 2)
- Update all Vue components
- Update Pinia stores
- Update composables and utils
- Rebuild frontend

#### Phase 4: Prompt Regeneration (Week 2)
- Update cli_mode_rules to use new names only
- Update staging prompt templates
- Regenerate all active orchestrator prompts

#### Phase 5: Cleanup (Week 3)
- Remove old column writes from Python code
- Remove deprecated field aliases from schemas
- Drop old columns from database
- Update all documentation

---

## Test Strategy

### Unit Tests to Update
- `tests/services/test_orchestration_service_cli_rules.py`
- `tests/tools/test_spawn_agent_job*.py`
- `tests/api/test_agent_jobs_api.py`

### Integration Tests
- Full staging -> implementation flow
- Template validation with new field names
- WebSocket event payload verification

### E2E Tests
- Complete project lifecycle with renamed fields
- Task tool spawn verification

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Active orchestrators have old field names | Complete all projects before Phase 4 |
| External MCP clients break | Version API, deprecation period |
| Frontend/backend desync | Deploy atomically |
| Test coverage gaps | Comprehensive test updates in Phase 2 |

---

## Timeline Estimate

| Phase | Duration | Key Activities |
|-------|----------|----------------|
| Phase 1: Schema | 4 hours | Add columns, backfill data |
| Phase 2: Backend | 16 hours | Services, tools, endpoints |
| Phase 3: Frontend | 16 hours | 78 files, stores, tests |
| Phase 4: Prompts | 4 hours | cli_mode_rules, templates |
| Phase 5: Cleanup | 8 hours | Remove old columns, docs |
| **Total** | **48 hours** | ~2 weeks for 1 developer |

---

## Semantic Clarification Questions

Before implementation, confirm:

1. **Is `template_name` the right choice?**
   - Current `agent_name` stores instance names like "Orchestrator Instance #1"
   - If it's truly template filename, `template_name` is correct
   - If it's display name, consider `display_name` instead

2. **Is `agent_category` the right choice?**
   - Alternatives: `agent_role`, `display_type`, `category`
   - `agent_category` clearly indicates grouping purpose

3. **Should `AgentJob.job_type` also rename?**
   - Currently stores same values as `agent_type`
   - Consider: `job_category` for consistency

---

## Dependencies

- **Prerequisite**: Complete Handover 0383 first (interim fix with task_tool_usage)
- **Related**: 0381 (agent_id/job_id separation - similar pattern)
- **Blocked by**: Active projects using current field names

---

## Success Criteria

1. [ ] All database columns renamed with data preserved
2. [ ] All Python code uses new field names
3. [ ] All API schemas updated (with deprecation warnings)
4. [ ] All frontend components updated
5. [ ] cli_mode_rules uses new names
6. [ ] All tests pass
7. [ ] Documentation updated
8. [ ] E2E staging -> implementation flow works
9. [ ] No orchestrator confusion in alpha testing

---

## Files Index (Sorted by Impact)

### Tier 1: Critical Path (Change First)
1. `src/giljo_mcp/models/agent_identity.py` - Database columns
2. `src/giljo_mcp/tools/tool_accessor.py` - cli_mode_rules
3. `src/giljo_mcp/thin_prompt_generator.py` - Staging prompts

### Tier 2: Service Layer
4. `src/giljo_mcp/services/agent_job_manager.py`
5. `src/giljo_mcp/services/orchestration_service.py`
6. `src/giljo_mcp/services/message_service.py`

### Tier 3: MCP Tools
7. `src/giljo_mcp/tools/orchestration.py`
8. `src/giljo_mcp/tools/agent_coordination.py`
9. `src/giljo_mcp/tools/agent.py`

### Tier 4: API Layer
10. `api/endpoints/agent_jobs/models.py`
11. `api/schemas/agent_job.py`
12. `api/endpoints/mcp_http.py`

### Tier 5: Frontend (Parallel with Tier 3-4)
13. `frontend/src/stores/agentJobsStore.js`
14. `frontend/src/stores/agents.js`
15. `frontend/src/components/projects/JobsTab.vue`
16. `frontend/src/components/projects/LaunchTab.vue`
17. ... (70+ more files)

---

## Notes

- This is a **breaking change** - plan for v4.0 release
- Implement 0383 first as interim fix
- Blue-green migration prevents data loss
- Dual-write period allows gradual cutover
