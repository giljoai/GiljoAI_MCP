# Handover 0411a: Recommended Execution Order (Phase Labels)

**Status**: Ready for Implementation
**Priority**: MEDIUM (UX enhancement for multi-terminal mode)
**Estimated Effort**: 3-4 hours
**Created**: 2026-02-24
**Parent**: 0411 (Windows Terminal Agent Spawning - superseded, kept as Agent Lab reference)

---

## Executive Summary

Add a `phase` integer field to AgentJob so the staging orchestrator can recommend an execution order for multi-terminal mode. The Jobs tab displays agents grouped by phase, giving users a visual pipeline showing which agents to launch first, which can run in parallel, and which should wait.

**This is advisory only** - no auto-spawning, no job scheduling. The user remains the scheduler, but now has the orchestrator's recommended order displayed visually.

---

## Decision History (Why This, Not Auto-Spawn)

### Original 0411: Auto-Terminal Spawning
Handover 0411 proposed the orchestrator automatically spawning agents in Windows Terminal tabs via `wt.exe`. This was shelved because:
1. **Tool ambiguity**: Each agent template targets a different CLI tool (claude/codex/gemini). Auto-spawning requires knowing which tool to use, which is now stored as `cli_tool` on AgentTemplate but wasn't exposed to orchestrators.
2. **Scheduling complexity**: Parallel vs sequential execution requires a job scheduler with completion detection, failure handling, and conditional spawning. The "last agent to finish triggers next phase" pattern via MCP messaging is architecturally sound but unreliable across CLI tools (Codex/Gemini may not follow spawn instructions).
3. **User control**: The manual play-button model works well. Users are the scheduler - they see agent cards, decide order, and click play. This is flexible and zero-risk.

### 0411a Decision: Phase Labels (This Handover)
Instead of automating execution, we capture the orchestrator's **reasoning about execution order** as structured data:
- Orchestrator already thinks about dependencies during staging (CH2 Step 7 tells it to "document execution order")
- Today that reasoning is lost as free-text prose in `update_agent_mission()`
- With a `phase` integer on AgentJob, the reasoning becomes structured and renderable
- The Jobs tab groups agents by phase, giving users a visual execution plan
- **Only active in multi-terminal mode** - in single-terminal (CLI) mode, the orchestrator manages order internally

### Complexity Assessment
| Concern | Auto-spawn (0411) | Phase labels (0411a) |
|---------|-------------------|----------------------|
| Determining order | Orchestrator decides | Orchestrator decides (same) |
| Storing order | Would need DB field | `phase` integer on AgentJob |
| Executing order | System watches, detects completion, spawns next | **User clicks play buttons in phase order** |
| Failure handling | Retry logic, timeouts, rollback | **User decides** |
| Parallel detection | System must monitor N processes | **User opens N terminals** |

---

## What Exists Today

### AgentTemplate.cli_tool (Already Implemented)
- Column: `cli_tool = Column(String(20), nullable=False, default="claude")`
- Values: `claude`, `codex`, `gemini`, `generic`
- UI: Radio group in TemplateManager.vue
- **NOT exposed to orchestrator** during staging (only `name`, `role`, `description` sent)

### Hardcoded Dependency Rules (orchestration_service.py `_generate_team_context_header`)
```python
dependency_rules = {
    "analyzer": {"upstream": [], "downstream": ["implementer", "documenter", "tester"]},
    "implementer": {"upstream": ["analyzer"], "downstream": ["tester", "reviewer", "documenter"]},
    "tester": {"upstream": ["implementer"], "downstream": ["reviewer"]},
    "reviewer": {"upstream": ["implementer", "tester"], "downstream": ["documenter"]},
    "documenter": {"upstream": ["analyzer", "implementer", "reviewer"], "downstream": []},
}
```
These are prepended to agent missions as informational headers. They do NOT enforce ordering and are not connected to any structured field.

### WorkflowStage/WorkflowEngine (Disconnected)
- `orchestration_types.py` has `WorkflowStage` dataclass with `depends_on` field
- `workflow_engine.py` has `WorkflowEngine` with waterfall/parallel execution
- **Completely disconnected** from staging/spawning flow - not wired to anything

### CH2 Step 7 (Free Text)
The orchestrator protocol instructs: "Document in YOUR_EXECUTION_STRATEGY: Agent execution order (sequential/parallel/hybrid), Dependencies between agents, Coordination checkpoints"
This is stored as prose in `update_agent_mission()`, not structured data.

### Agent Lab (AgentTipsDialog.vue)
- Manual reference panel with copy-paste spawn commands
- Shows `wt.exe` syntax for Claude/Codex/Gemini
- Color scheme for agent types
- **Manual integration only** - nothing auto-applied

---

## Implementation Plan

### 1. Database: Add `phase` Column to AgentJob

**File**: `src/giljo_mcp/models/agent_identity.py`

Add to the `AgentJob` model:
```python
phase = Column(Integer, nullable=True, default=None)
```

- `None` = no phase assigned (single-terminal mode, or legacy jobs)
- `1`, `2`, `3`... = execution phase (lower runs first, same number = parallel)

**Migration**: Create Alembic migration adding the column.

### 2. Backend: Accept `phase` in `spawn_agent_job()`

**File**: `src/giljo_mcp/services/orchestration_service.py`

Add `phase: Optional[int] = None` parameter to `spawn_agent_job()`. Pass it through to the `AgentJob` constructor.

The `spawn_agent_job` function signature (currently at ~line 1230) accepts:
```python
agent_display_name: str,
agent_name: str,
mission: str,
project_id: str,
tenant_key: str,
parent_job_id: Optional[str],
context_chunks: Optional[list[str]],
```

Add `phase: Optional[int] = None` to this list.

### 3. MCP Tool: Accept `phase` in the spawn tool

The MCP tool that wraps `spawn_agent_job()` needs the `phase` parameter exposed. Find the tool definition (likely in `src/giljo_mcp/tools/`) and add the parameter.

**Research needed**: Find the exact MCP tool definition that wraps `spawn_agent_job`. Search for `spawn_agent_job` references in `tools/` directory.

### 4. Orchestrator Prompt: Instruct Phase Assignment

**File**: `src/giljo_mcp/services/orchestration_service.py` in `get_orchestrator_instructions()`

**Only when `execution_mode != 'claude_code_cli'`** (multi-terminal mode), add to the orchestrator protocol:

```
## Execution Phase Assignment (Multi-Terminal Mode)

When creating agent jobs with spawn_agent_job, assign a `phase` number to each agent:
- Phase 1: Agents that should run first (no dependencies). Usually: analyzer, researcher.
- Phase 2: Agents that depend on Phase 1 completion. Usually: implementer, designer, db_builder.
- Phase 3: Agents that depend on Phase 2 completion. Usually: tester, reviewer.
- Phase 4+: Final agents. Usually: documenter.

Agents in the SAME phase can run in parallel (user opens multiple terminals).
Higher phases should wait until lower phases complete.

Example: For a full-stack project:
  Phase 1: analyzer (understand codebase first)
  Phase 2: frontend-implementer + backend-implementer (parallel, independent work)
  Phase 3: tester (needs implementation complete)

Use your judgment based on the actual agent team and project requirements.
```

### 5. API: Expose `phase` in Agent Job Responses

**File**: Find the API endpoint that returns agent jobs for the Jobs tab.

The `phase` field needs to be included in the response payload. Check which endpoint `useAgentJobs` composable calls.

**Research needed**: Trace `useAgentJobs` composable to find the API endpoint and response schema.

### 6. Frontend: Phase Grouping Visualization on Jobs Tab

**File**: `frontend/src/components/projects/JobsTab.vue`
**Location**: Above the existing agent table, visible at:
`http://localhost:7274/projects/3f3cb8ad-842a-4ef7-82d9-d59f256f42a5?via=jobs&tab=jobs`

#### Option A: Phase Headers in Existing Table (Simpler)
Insert phase group header rows into the existing table:
```
┌─────────────────────────────────────────────────────┐
│ Phase 1                                              │
├─────────────────────────────────────────────────────┤
│ [AN] Analyzer    │ agent-1234 │ waiting │ ▶ ...     │
├─────────────────────────────────────────────────────┤
│ Phase 2 (after Phase 1 completes)                    │
├─────────────────────────────────────────────────────┤
│ [FI] FE-Impl     │ agent-5678 │ waiting │ ▶ ...     │
│ [BI] BE-Impl     │ agent-9012 │ waiting │ ▶ ...     │
├─────────────────────────────────────────────────────┤
│ Phase 3 (after Phase 2 completes)                    │
├─────────────────────────────────────────────────────┤
│ [TE] Tester      │ agent-3456 │ waiting │ ▶ ...     │
└─────────────────────────────────────────────────────┘
```

#### Option B: Pipeline Visualization Above Table (Richer)
Add a compact horizontal pipeline strip above the table:
```
[Phase 1: Analyzer] ──→ [Phase 2: FE-Impl + BE-Impl] ──→ [Phase 3: Tester]
```
With color-coded chips per agent, using the agent's `background_color` from their template.

**Recommendation**: Start with Option A (phase header rows in table). It's minimal UI change, consistent with existing table layout, and can be enhanced to Option B later.

#### Implementation Details (Option A):
1. Group `sortedAgents` by `phase` in a computed property
2. Sort groups by phase number (null/undefined phases go last as "Unphased")
3. Render `<tr>` header rows between phase groups with phase label and description
4. Phase descriptions: "Phase 1", "Phase 2 (after Phase 1)", etc.
5. Only show phase grouping when ANY agent has a non-null `phase` value
6. When no phases exist (single-terminal mode or legacy), render flat table as today

#### Sorting Logic:
```javascript
const groupedAgents = computed(() => {
  const hasPhases = sortedAgents.value.some(a => a.phase != null)
  if (!hasPhases) return null  // render flat table

  const groups = {}
  for (const agent of sortedAgents.value) {
    const phase = agent.phase ?? 999  // unphased goes last
    if (!groups[phase]) groups[phase] = []
    groups[phase].push(agent)
  }
  return Object.entries(groups)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([phase, agents]) => ({
      phase: Number(phase),
      label: Number(phase) === 999 ? 'Unphased' : `Phase ${phase}`,
      agents
    }))
})
```

### 7. Also Populate `template_id` on AgentJob (Quick Win)

**File**: `src/giljo_mcp/services/orchestration_service.py` in `spawn_agent_job()`

The `template_id` FK on AgentJob exists in the schema but is **never populated** during spawn. When the template lookup succeeds (around the section that injects `system_instructions + user_instructions`), also set `template_id` on the AgentJob record. This enables future features like showing the agent's `cli_tool` and `background_color` on the Jobs tab without extra lookups.

---

## Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/models/agent_identity.py` | Add `phase` column to AgentJob |
| `src/giljo_mcp/services/orchestration_service.py` | Add `phase` param to `spawn_agent_job()`, populate `template_id`, add phase instructions to `get_orchestrator_instructions()` |
| MCP tool wrapping `spawn_agent_job` | Add `phase` parameter |
| API response for agent jobs | Include `phase` in response |
| `frontend/src/components/projects/JobsTab.vue` | Phase grouping visualization |
| Alembic migration | New migration for `phase` column |

---

## Testing Checklist

- [ ] Alembic migration runs cleanly (upgrade + downgrade)
- [ ] `spawn_agent_job()` accepts and stores `phase` parameter
- [ ] `spawn_agent_job()` populates `template_id` when template found
- [ ] API returns `phase` in agent job response
- [ ] `get_orchestrator_instructions()` includes phase assignment instructions ONLY in multi-terminal mode
- [ ] Jobs tab renders flat table when no phases assigned (backward compatible)
- [ ] Jobs tab renders phase-grouped table when phases exist
- [ ] Phase header rows display correctly with phase labels
- [ ] Existing agent table functionality unaffected (play buttons, modals, messages, duration, etc.)
- [ ] Orchestrator staging prompt includes phase instructions in multi-terminal mode
- [ ] Orchestrator staging prompt does NOT include phase instructions in CLI mode

---

## Out of Scope (Deferred)

- **Auto-terminal spawning** - User remains the scheduler (see Decision History)
- **Exposing `cli_tool` to orchestrator** - Not needed for phase labels; could be added later for richer Agent Lab integration
- **Pipeline visualization (Option B)** - Start with table headers, enhance later
- **Dependency enforcement** - Phases are advisory, not enforced by system
- **WorkflowEngine integration** - The disconnected WorkflowStage/WorkflowEngine system is not addressed here; it may be useful for future auto-spawn work

---

## Related

- 0411: Windows Terminal Agent Spawning (parent, superseded by Agent Lab + this)
- Agent Lab (AgentTipsDialog.vue): Manual spawn command reference
- `_generate_team_context_header()`: Existing hardcoded dependency rules (informational)
- WorkflowStage/WorkflowEngine: Disconnected dependency system (future use)
