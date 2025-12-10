# Handover 0340: CLI Mode Two-Phase Architecture Summary

**Date:** 2025-12-09
**From Agent:** Claude Opus 4.5 (Session completing 0260/0339)
**To Agent:** Next Session (Implementation Prompt Work)
**Priority:** High
**Status:** Summary / Ready for Stage 2

---

## Key Architecture Insight

CLI Mode operates in **two distinct phases**, each with its own prompt:

```
Two-Phase CLI Mode Workflow:
┌─────────────────────┐     ┌─────────────────────┐
│ Stage 1: STAGING    │     │ Stage 2: IMPLEMENT  │
│ (Launch Tab)        │ --> │ (Jobs Tab)          │
│                     │     │                     │
│ ✅ COMPLETE (0339)  │     │ ❌ NOT DONE YET     │
│ - agent_type rules  │     │ - Implementation    │
│ - forbidden patterns│     │   prompt endpoint   │
│ - lifecycle flow    │     │ - Task tool launch  │
└─────────────────────┘     └─────────────────────┘
```

---

## Stage 1: Staging (COMPLETE)

**What:** Orchestrator plans the project and spawns agent jobs

**UI Location:** Launch Tab → [Stage Project] button

**Prompt Generator:** `ThinClientPromptGenerator.generate_staging_prompt()`

**What We Implemented (0339):**
- AGENT_TYPE LIFECYCLE section with 4-phase flow table
- FORBIDDEN PATTERNS section with 5 explicit failure examples
- ABSOLUTE RULE callout ("agent_type is SINGLE SOURCE OF TRUTH")
- MCP response: `agent_type_is_truth`, `forbidden_patterns`, `lifecycle_flow` fields
- Belt-and-suspenders enforcement in staging prompt + MCP response

**Commits:**
- `6b6eb173`: feat(0339): Strengthen agent_type enforcement in CLI mode
- `907b4ad4`: docs: Archive completed handover 0260

---

## Stage 2: Implementation (NOT DONE)

**What:** Orchestrator launches spawned agents via Task tool

**UI Location:** Jobs Tab → orchestrator card → [▶ Implement] button

**Problem:** Currently shows toast "Feature not yet implemented" instead of generating prompt

**What's Needed:**

### 1. API Endpoint
```
GET /api/prompts/implementation/{project_id}
```
Returns: Implementation prompt for orchestrator to launch agents via Task tool

### 2. Backend Method
```python
ThinClientPromptGenerator.generate_implementation_prompt(project_id, tenant_key)
```
- Fetch spawned agents from database (status='waiting')
- Generate Task tool launch instructions
- Include agent_type enforcement (same rules as staging)

### 3. Jobs Tab UI Handler
```javascript
// JobsTab.vue - orchestrator card implement button
async handleImplementClick(job) {
    const response = await api.get(`/api/prompts/implementation/${projectId}`)
    // Show copy dialog with implementation prompt
}
```

### 4. get_agent_mission() Enhancement
Return full 6-phase protocol for spawned agents:
1. Identity verification
2. MCP health check
3. Mission fetch
4. Work execution
5. Progress reporting
6. Completion

---

## Related Handovers

| Handover | Relationship | Status |
|----------|--------------|--------|
| **0260** | CLI Mode Toggle (all phases) | ✅ COMPLETE (archived) |
| **0261** | Implementation Prompt Spec | Partially superseded |
| **0337** | Implementation Prompt Fix | Active - needs completion |
| **0335** | CLI Template Validation | ✅ COMPLETE |
| **0339** | Stage 1 Enforcement | ✅ COMPLETE (this work) |

---

## Files to Create/Modify for Stage 2

| File | Change |
|------|--------|
| `api/endpoints/prompts.py` | Add `/implementation/{project_id}` endpoint |
| `src/giljo_mcp/thin_prompt_generator.py` | Add `generate_implementation_prompt()` method |
| `frontend/src/components/projects/JobsTab.vue` | Update implement button handler |
| `src/giljo_mcp/tools/orchestration.py` | Enhance `get_agent_mission()` response |

---

## Implementation Prompt Content (Draft)

The implementation prompt should include:

```markdown
# Implementation Phase - Launch Agents

You have completed staging. Now launch your spawned agents.

## Spawned Agents Ready to Launch
| agent_type | agent_name | job_id | status |
|------------|------------|--------|--------|
| implementer | Backend Impl | uuid-1 | waiting |
| implementer | Frontend Impl | uuid-2 | waiting |
| tester | Integration Tester | uuid-3 | waiting |

## Launch Instructions
For each agent above, use Task tool:

```
Task(
    subagent_type="{agent_type}",  # MUST match exactly
    prompt="You are {agent_name}. Call get_agent_mission('{job_id}', '{tenant_key}') to start."
)
```

## CRITICAL: agent_type Rules (Same as Staging)
- agent_type MUST match template filename exactly
- agent_name is display only - NEVER use for Task tool
- See FORBIDDEN PATTERNS from staging prompt
```

---

## Success Criteria for Stage 2

1. ✅ `/api/prompts/implementation/{project_id}` returns valid prompt
2. ✅ Prompt lists all spawned agents with correct agent_type
3. ✅ Task tool launch instructions use strict agent_type
4. ✅ Jobs Tab implement button copies prompt (not toast)
5. ✅ Agents receive full 6-phase protocol from get_agent_mission()

---

## Questions for User

Before implementing Stage 2, clarify:

1. **Button behavior:** Should implement button open modal with copy, or auto-copy to clipboard?
2. **Agent filtering:** Include only 'waiting' status agents, or all non-completed?
3. **Prompt format:** Single prompt for all agents, or paginated by agent?
4. **Error handling:** What if no agents spawned yet?

---

## Next Steps

1. Review 0337_CLI_MODE_IMPLEMENTATION_PROMPT.md for detailed spec
2. Answer clarifying questions above
3. Implement Stage 2 (estimated: 2-3 hours)
