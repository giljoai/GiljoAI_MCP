# Handover 0351: Agent Name as Single Source of Truth

**Date:** 2025-12-15
**From Agent:** Planning Orchestrator
**To Agent:** Implementation Agent
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation

---

## Task Summary

Change the semantic meaning of `agent_name` and `agent_type` fields so that `agent_name` becomes the single source of truth for template matching, while `agent_type` becomes a display category.

**Why it's important:** Claude Code's `Task(subagent_type=X)` looks for a file named `X.md` in `.claude/agents/`. Currently, `agent_type` is used for this matching, but custom templates like "implementer-frontend" need `agent_name` to be the match field so users can have multiple variants of the same role.

**Expected outcome:**
- Orchestrator spawns agents with `agent_name` matching template filenames exactly
- `agent_type` becomes a display/category field (e.g., "implementer")
- UI shows agent name prominently with type as subtitle
- Validation checks `agent_name` against active templates

---

## Problem Statement

### Current Issues

1. **Template matching uses wrong field**: `agent_type` is validated against template names, but `agent_name` should be the match field
2. **Custom templates ignored**: User creates "implementer-frontend" template but spawned agents don't use this name correctly
3. **UI only shows type**: Agent cards display `agent_type` but not `agent_name`
4. **Staging prompt misleading**: Tells orchestrator to use `agent_type` for Task tool, but should use `agent_name`

### Current vs New Semantics

| Field | CURRENT Meaning | NEW Meaning |
|-------|-----------------|-------------|
| `agent_name` | Display label ("Backend API Implementer") | **Template filename** ("implementer-frontend") |
| `agent_type` | Template match ("implementer") | **Display category** ("implementer") |

### Default Behavior
If user creates template with no suffix, role becomes the name:
- Template "implementer" (no suffix) → `agent_name="implementer"`, `agent_type="implementer"`
- Template "implementer-frontend" → `agent_name="implementer-frontend"`, `agent_type="implementer"`

---

## Solution Overview

### Core Changes

1. **Validation**: Check `agent_name` against template names (not `agent_type`)
2. **CLI Constraints**: Return `allowed_agent_names` (not `allowed_agent_types`)
3. **Staging Prompts**: Tell orchestrator `agent_name` is single source of truth
4. **Template Selector**: Query by `agent_name` parameter
5. **Frontend**: Display `agent_name` prominently, `agent_type` as subtitle

### Data Flow (After Change)

```
Orchestrator reads staging prompt
    ↓
Calls spawn_agent_job(agent_name="implementer-frontend", agent_type="implementer", ...)
    ↓
Backend validates: agent_name in allowed_agent_names? ✓
    ↓
Creates MCPAgentJob record
    ↓
UI displays: "implementer-frontend" (primary), "implementer" (subtitle)
    ↓
Task(subagent_type="implementer-frontend") → finds implementer-frontend.md ✓
```

---

## Implementation Plan

### Phase 1: Backend Validation (orchestration.py)

**File:** `src/giljo_mcp/tools/orchestration.py`

#### Change 1: Validation Logic (Lines ~2310-2344)

```python
# BEFORE:
valid_agent_types = [row[0] for row in template_result.fetchall()]
if agent_type not in valid_agent_types:
    return {
        "success": False,
        "error": f"Invalid agent_type '{agent_type}'. Must be one of: {valid_agent_types}",
    }

# AFTER:
valid_agent_names = [row[0] for row in template_result.fetchall()]
if agent_name not in valid_agent_names:
    return {
        "success": False,
        "error": f"Invalid agent_name '{agent_name}'. Must match a template name: {valid_agent_names}",
        "hint": "agent_name must exactly match a template filename (e.g., 'implementer-frontend')"
    }
```

#### Change 2: CLI Constraints (Lines ~2070-2101)

```python
# BEFORE:
response["agent_spawning_constraint"] = {
    "mode": "strict_task_tool",
    "allowed_agent_types": allowed_agent_types,
    "instruction": "agent_type parameter must be EXACTLY one of the allowed template names."
}

# AFTER:
response["agent_spawning_constraint"] = {
    "mode": "strict_task_tool",
    "allowed_agent_names": allowed_agent_names,
    "instruction": "agent_name parameter must be EXACTLY one of the allowed template names."
}
```

### Phase 2: Template Selector (agent_selector.py)

**File:** `src/giljo_mcp/agent_selector.py`

#### Change 1: Method Parameter Rename

```python
# BEFORE (line ~141):
async def _get_template(
    self,
    agent_type: str,
    tenant_key: str,
    product_id: Optional[str] = None,
) -> Optional[AgentTemplate]:

# AFTER:
async def _get_template(
    self,
    agent_name: str,  # Renamed parameter
    tenant_key: str,
    product_id: Optional[str] = None,
) -> Optional[AgentTemplate]:
```

#### Change 2: Query Parameter (Line ~237)

```python
# BEFORE:
AgentTemplate.name == agent_type

# AFTER:
AgentTemplate.name == agent_name
```

#### Change 3: Update _query_template Similarly

Rename `agent_type` parameter to `agent_name` in `_query_template()` method.

#### Change 4: Update Callers in select_agents()

```python
# BEFORE (line ~107-111):
template = await self._get_template(
    agent_type=agent_type,
    tenant_key=tenant_key,
    product_id=product_id,
)

# AFTER:
template = await self._get_template(
    agent_name=agent_type,  # Note: still using agent_type from work_types dict
    tenant_key=tenant_key,
    product_id=product_id,
)
```

### Phase 3: Staging Prompts (thin_prompt_generator.py)

**File:** `src/giljo_mcp/thin_prompt_generator.py`

#### Change 1: CLI Mode Instructions (Lines ~957-963)

```python
# BEFORE:
mode_block = """CLI MODE CRITICAL:
This project uses Claude Code CLI for implementation. When spawning agents:
- agent_type: SINGLE SOURCE OF TRUTH - must EXACTLY match template name (e.g., "implementer")
- agent_name: Descriptive display label only (e.g., "Backend API Implementer")

In implementation phase, Task(subagent_type=X) uses agent_type value, NOT agent_name."""

# AFTER:
mode_block = """CLI MODE CRITICAL:
This project uses Claude Code CLI for implementation. When spawning agents:
- agent_name: SINGLE SOURCE OF TRUTH - must EXACTLY match template name (e.g., "implementer-frontend")
- agent_type: Display category label (e.g., "implementer")

In implementation phase, Task(subagent_type=X) uses agent_name value, NOT agent_type.
Full cli_mode_rules, allowed_agent_names, and examples are in get_orchestrator_instructions() response."""
```

#### Change 2: Task Tool Pattern (Line ~1127)

```python
# BEFORE:
'subagent_type="{agent_type}",  # CRITICAL: Use agent_type, NOT agent_name'

# AFTER:
'subagent_type="{agent_name}",  # CRITICAL: Use agent_name (template filename)'
```

#### Change 3: Agent Spawn Docs (Lines ~1100-1106)

```python
# BEFORE:
f"   - Agent Type: `{agent.agent_type}` (matches .claude/agents/{agent.agent_type}.md)"

# AFTER:
f"   - Agent Name: `{agent.agent_name}` (matches .claude/agents/{agent.agent_name}.md)"
f"   - Agent Type: `{agent.agent_type}` (display category)"
```

#### Change 4: CLI Mode Constraints Section (Lines ~1215-1231)

Update all references from `agent_type` to `agent_name` for template matching.

#### Change 5: Step 5 in Staging Prompt

```python
# BEFORE:
"5. SPAWN AGENTS: spawn_agent_job() for each specialist
   CRITICAL: agent_type MUST exactly match template name from Step 2"

# AFTER:
"5. SPAWN AGENTS: spawn_agent_job() for each specialist
   CRITICAL: agent_name MUST exactly match template name from Step 2
   THIS IS CRITICAL FOR TASK TOOL AGENT SUBSPAWNING."
```

### Phase 4: Multi-Terminal Staging Prompt

Update the multi-terminal mode prompt similarly:
- Change Step 5 to reference `agent_name`
- Remove type-centric language

### Phase 5: Frontend Display

#### File 1: `frontend/src/components/projects/JobsTab.vue`

**Current (lines ~23-28):**
```vue
<td class="agent-type-cell">
  <v-avatar :color="getAgentColor(agent.agent_type)" size="32" class="agent-avatar">
    <span class="avatar-text">{{ getAgentAbbr(agent.agent_type) }}</span>
  </v-avatar>
  <span class="agent-name">{{ agent.agent_type?.toUpperCase() || '' }}</span>
</td>
```

**After:**
```vue
<td class="agent-type-cell">
  <v-avatar :color="getAgentColor(agent.agent_type)" size="32" class="agent-avatar">
    <span class="avatar-text">{{ getAgentAbbr(agent.agent_type) }}</span>
  </v-avatar>
  <div class="agent-info">
    <span class="agent-name-primary">{{ agent.agent_name || agent.agent_type }}</span>
    <span class="agent-type-secondary" v-if="agent.agent_name && agent.agent_name !== agent.agent_type">
      {{ agent.agent_type }}
    </span>
  </div>
</td>
```

Add CSS:
```scss
.agent-info {
  display: flex;
  flex-direction: column;
}
.agent-name-primary {
  font-weight: 500;
}
.agent-type-secondary {
  font-size: 0.75rem;
  color: var(--v-theme-on-surface-variant);
  text-transform: capitalize;
}
```

#### File 2: `frontend/src/components/orchestration/AgentTableView.vue`

**Current (lines ~12-20):**
```vue
<span class="text-capitalize">{{ item.agent_type }}</span>
```

**After:**
```vue
<div class="d-flex flex-column">
  <span class="font-weight-medium">{{ item.agent_name || item.agent_type }}</span>
  <span v-if="item.agent_name && item.agent_name !== item.agent_type"
        class="text-caption text-grey text-capitalize">
    {{ item.agent_type }}
  </span>
</div>
```

#### File 3: `frontend/src/components/AgentCard.vue`

Update header section to show `agent_name` prominently with `agent_type` as subtitle.

---

## Testing Requirements

### Unit Tests to Update

| File | Changes Required |
|------|------------------|
| `tests/unit/test_orchestration_agent_validation.py` | Change `allowed_agent_types` → `allowed_agent_names`, update validation assertions |
| `tests/unit/test_agent_selector.py` | Rename `agent_type` param to `agent_name` in all test calls to `_get_template()` |
| `tests/unit/test_dynamic_agent_discovery.py` | Update agent discovery assertions |
| `tests/unit/test_agent_discovery.py` | Update discovery system tests |
| `tests/unit/test_thin_prompt_generator_execution_mode.py` | Update prompt content assertions |
| `tests/unit/test_thin_prompt_cli_validation.py` | Update CLI validation tests |
| `tests/unit/test_agent_job_template_tracking.py` | Review for agent_type references |

### Integration Tests to Update

| File | Changes Required |
|------|------------------|
| `tests/integration/test_spawn_agent_job_validation.py` | Core validation tests - change from agent_type to agent_name |
| `tests/integration/test_agent_spawning_with_context.py` | Update spawning workflow tests |
| `tests/integration/test_agent_workflow.py` | Update workflow tests |
| `tests/integration/test_agent_template_id_tracking.py` | Review template tracking |
| `tests/integration/test_agent_templates_integration.py` | Update template integration |
| `tests/integration/test_orchestration_workflow.py` | Update orchestration tests |
| `tests/integration/test_orchestrator_framing_response.py` | Update framing response tests |
| `tests/integration/test_full_stack_mode_flow.py` | Update mode flow tests |

### Service Tests to Update

| File | Changes Required |
|------|------------------|
| `tests/services/test_orchestration_service_cli_rules.py` | Change `allowed_agent_types` → `allowed_agent_names` |
| `tests/services/test_orchestration_service_agent_mission.py` | Review agent mission tests |
| `tests/services/test_agent_template_depth.py` | Review template depth tests |
| `tests/services/test_thin_client_prompt_generator_agent_templates.py` | Update prompt generator tests |

### Tool Tests to Update

| File | Changes Required |
|------|------------------|
| `tests/tools/test_orchestration_response_fields.py` | Update response field assertions |
| `tests/tools/test_thin_client_mcp_tools.py` | Update MCP tool tests |
| `tests/tools/test_deprecated_tools.py` | Review deprecated tool tests |

### API Tests to Update

| File | Changes Required |
|------|------------------|
| `tests/api/test_agent_jobs_api.py` | Review agent jobs API tests |
| `tests/api/test_agent_jobs_mission.py` | Review mission API tests |
| `tests/api/test_prompts_execution_mode.py` | Update execution mode tests |
| `tests/api/test_execution_mode_endpoints.py` | Update endpoint tests |

### Fixture Files to Review

| File | Changes Required |
|------|------------------|
| `tests/fixtures/test_orchestrator_simulator.py` | Update simulator tests |
| `tests/fixtures/orchestrator_simulator.py` | Update simulator helpers |

### Manual Testing

1. **Create custom template**: In Template Manager, create "implementer-frontend"
2. **Stage project**: Click "Stage Project" in Claude Code CLI mode
3. **Verify prompt**: Check that staging prompt says `agent_name` is single source of truth
4. **Spawn agent**: Have orchestrator spawn an agent with `agent_name="implementer-frontend"`
5. **Check UI**: Verify agent card shows "implementer-frontend" with "implementer" subtitle
6. **Test Task tool**: Verify `Task(subagent_type="implementer-frontend")` works

---

## Success Criteria

1. [ ] Validation checks `agent_name` against active templates
2. [ ] CLI constraints return `allowed_agent_names`
3. [ ] Staging prompts reference `agent_name` as single source of truth
4. [ ] Task tool examples use `agent_name` value
5. [ ] Frontend shows `agent_name` prominently with `agent_type` as subtitle
6. [ ] All existing tests pass (after updates)
7. [ ] Custom template "implementer-frontend" appears in exported ZIP
8. [ ] Spawned agents with custom names work with Task tool

---

## Files Summary

### Backend (6 files)

| File | Lines to Change | Description |
|------|-----------------|-------------|
| `src/giljo_mcp/tools/orchestration.py` | ~2070-2101, ~2310-2344 | Validation + CLI constraints |
| `src/giljo_mcp/agent_selector.py` | ~141-211, ~213-256, ~237 | Template lookup methods |
| `src/giljo_mcp/thin_prompt_generator.py` | ~957-963, ~1100-1106, ~1127, ~1215-1231 | Prompt generation |

### Frontend (3 files)

| File | Description |
|------|-------------|
| `frontend/src/components/projects/JobsTab.vue` | Agent table display |
| `frontend/src/components/orchestration/AgentTableView.vue` | Table component |
| `frontend/src/components/AgentCard.vue` | Card component |

### Tests (~30 files)

See Testing Requirements section above for complete list.

---

## Dependencies and Blockers

### Dependencies
- None - this is a self-contained semantic change

### Related Handovers
- Handover 0260: Original agent validation implementation
- Handover 0335: CLI mode rules
- Handover 0336: agent_type_is_truth structure (now being reversed)

### Blockers
- None identified

---

## Additional Notes

### Backward Compatibility
- Existing agents with `agent_type` = `agent_name` will continue to work
- Only affects new agent spawning after this change
- Database schema unchanged (same columns, different content)

### Color/Category Behavior
- `agent_type` continues to determine avatar color in UI
- Category grouping in Template Manager unchanged
- Role-based coloring preserved

### Default Name Logic
- If user creates template with no suffix → role becomes name
- Template "implementer" → agent_name="implementer", agent_type="implementer"
- Both fields same value, UI shows single line (no subtitle)
