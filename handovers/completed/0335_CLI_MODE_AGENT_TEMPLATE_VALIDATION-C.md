# Handover 0335: CLI Mode Agent Template Validation

## Status: COMPLETE
## Priority: HIGH
## Completed: 2025-12-09

---

## Completion Summary

**All 4 tasks completed:**
- Task 1: `cli_mode_rules` in `get_orchestrator_instructions` response ✅
- Task 2: Staging prompt validation section (CLI mode) ✅
- Task 3: `last_exported_at` column + `may_be_stale` property ✅
- Task 4: UI staleness indicator in TemplateManager ✅

**Additional bug fixes during implementation:**
- WebSocket `ws_manager` import fix (use `app.state`)
- Vue lazy-loading WebSocket fix (provide/inject pattern)
- API response missing export fields fix
- Execution mode prop staleness fix (event emission)

**Key commits:** `1b488be8`, `858a0e10`, `1f35ea5b`, `66c76019`, `2db3b3bb`, `617b5298`

**See also:** `handover_0335_session_complete.md` for detailed session memory
## Type: Prompt Enhancement + Soft Validation
## Depends On: 0260 (CLI Toggle), 0334 (full_protocol in get_agent_mission)

---

## Executive Summary

Enhance the Claude Code CLI mode staging workflow with **belt-and-suspenders agent naming enforcement** and **soft validation** to warn users when agent templates may be outdated or missing from their Claude Code environment.

**Two Goals:**
1. **Reinforce naming rules** - Ensure orchestrator uses exact template names for `agent_type` (not creative names)
2. **Soft validation** - Warn if templates haven't been exported or may be outdated

**Scope:** Staging prompt + `get_orchestrator_instructions` response (CLI mode only). Multi-terminal mode unchanged.

---

## Problem Statement

### Issue 1: Agent Naming Confusion Risk

The orchestrator correctly uses `agent_type` (template name) vs `agent_name` (display label):

```
spawn_agent_job(
    agent_type="implementer",                    # Correct - matches template
    agent_name="Folder Structure Implementer"    # Correct - human label
)
```

But in CLI mode, the **Task tool** must use the exact template name:
```
Task(subagent_type="implementer")           # Works
Task(subagent_type="Folder Structure...")   # FAILS - no such template
```

**Risk:** If orchestrator or implementation prompt confuses these, agents won't spawn correctly.

### Issue 2: Template Synchronization

User edits templates in GiljoAI → Exports to `.claude/agents/` → Uses CLI mode

**Problem:** If user:
- Edits a template but forgets to re-export
- Never exported certain templates
- Has stale templates from weeks ago

The orchestrator has no way to warn them. Spawning will fail silently or use wrong agent definitions.

---

## Solution Design

### Part 1: Belt-and-Suspenders Naming Enforcement

**In `get_orchestrator_instructions` response** (machine-readable):
```python
{
    "agent_templates": [...],
    "cli_mode_rules": {
        "agent_type_usage": "MUST match template 'name' field exactly",
        "agent_name_usage": "Descriptive label for UI display only",
        "task_tool_mapping": "Task(subagent_type=agent_type) - NOT agent_name"
    }
}
```

**In staging prompt** (human-readable, CLI mode section):
```markdown
## AGENT SPAWNING RULES (CLI MODE - CRITICAL)

When spawning agents, you MUST use TWO parameters correctly:

| Parameter    | Purpose                      | Value Must Be               |
|--------------|------------------------------|----------------------------|
| `agent_type` | Template name for Task tool  | EXACT match: "implementer" |
| `agent_name` | Human-readable UI label      | Descriptive: "Folder Structure Implementer" |

### Why This Matters
Claude Code's Task tool finds agents by filename:
- `Task(subagent_type="implementer")` → looks for `implementer.md`
- `Task(subagent_type="Folder Structure Implementer")` → FILE NOT FOUND

### Available Templates (use these EXACT names for agent_type)
{agent_list}

### Example - Spawning 2 implementers:
```python
spawn_agent_job(agent_type="implementer", agent_name="Folder Scaffolder", ...)
spawn_agent_job(agent_type="implementer", agent_name="README Writer", ...)
```
Both use `agent_type="implementer"` but have different display names.
```

### Part 2: Soft Validation (Template Freshness Warning)

**In staging prompt** (CLI mode only):
```markdown
## AGENT TEMPLATE VALIDATION (CLI MODE)

Before spawning agents, verify templates exist in Claude Code:

### Step 1: Check Your Agent Folders
```bash
ls -la .claude/agents/ 2>/dev/null || echo "No project agents folder"
ls -la ~/.claude/agents/ 2>/dev/null || echo "No user agents folder"
```

### Step 2: Resolution Priority
Claude Code checks templates in this order:
1. **Project agents**: `{project}/.claude/agents/{agent_type}.md` (HIGHEST PRIORITY)
2. **User agents**: `~/.claude/agents/{agent_type}.md`
3. **Built-in**: Claude Code defaults (FALLBACK)

### Step 3: Compare Against Required Agents
The server expects these agents:
{agent_list_from_get_orchestrator_instructions}

### Step 4: Handle Mismatches
If any required agent is MISSING from both folders:
- WARN the user: "Template '{agent_type}' not found in .claude/agents/"
- SUGGEST: "Export templates from GiljoAI Settings → Agent Template Manager"
- PROCEED with available agents (soft fail - don't block entirely)

### Step 5: Check Freshness (Optional)
If templates exist but filenames show old dates, warn user:
- "Template 'implementer.md' may be outdated"
- "Consider re-exporting from GiljoAI if you've made recent changes"
```

---

## Implementation Tasks

### Task 1: Enhance `get_orchestrator_instructions` Response

**File:** `src/giljo_mcp/services/orchestration_service.py`

**Method:** `get_orchestrator_instructions()`

**Add to response when `execution_mode == 'claude_code_cli'`:**

```python
if execution_mode == "claude_code_cli":
    result["cli_mode_rules"] = {
        "agent_type_usage": "MUST match template 'name' field exactly for Task tool",
        "agent_name_usage": "Descriptive label for UI display only - NOT for Task tool",
        "task_tool_mapping": "Task(subagent_type=X) where X = agent_type value",
        "validation": "soft",  # warn but don't block
        "template_locations": [
            "{project}/.claude/agents/ (priority 1 - project agents)",
            "~/.claude/agents/ (priority 2 - user agents)"
        ]
    }
    result["spawning_examples"] = [
        {
            "scenario": "Two implementers with different tasks",
            "calls": [
                'spawn_agent_job(agent_type="implementer", agent_name="Folder Scaffolder", ...)',
                'spawn_agent_job(agent_type="implementer", agent_name="README Writer", ...)'
            ],
            "note": "Both use agent_type='implementer' - the template name"
        }
    ]
```

**Acceptance Criteria:**
- Response includes `cli_mode_rules` only when `execution_mode == 'claude_code_cli'`
- Multi-terminal mode response unchanged
- Unit test verifies structure

---

### Task 2: Update Staging Prompt (CLI Mode Section)

**File:** `src/giljo_mcp/thin_prompt_generator.py`

**Method:** `_build_staging_prompt()` or equivalent

**Add CLI mode section with:**
1. Agent spawning rules table (agent_type vs agent_name)
2. Task tool mapping explanation
3. Template validation steps (ls commands)
4. Resolution priority (project → user → built-in)
5. Soft warning guidance (warn but proceed)

**Acceptance Criteria:**
- Staging prompt includes new section only when `claude_code_mode=True`
- Section appears after agent discovery, before spawning instructions
- Includes actual agent list from `get_available_agents`
- Unit test verifies prompt content

---

### Task 3: Add `last_exported_at` Tracking (Backend)

**File:** `src/giljo_mcp/models/agents.py` (or templates model)

**Add column:**
```python
last_exported_at = Column(DateTime(timezone=True), nullable=True)
```

**Update export endpoint** to set this timestamp when user exports templates.

**Use in response:**
```python
{
    "agent_templates": [
        {
            "name": "implementer",
            "last_exported_at": "2025-12-07T10:30:00Z",  # or null if never
            "last_modified_at": "2025-12-08T15:00:00Z",
            "may_be_stale": True  # last_modified > last_exported
        }
    ]
}
```

**Acceptance Criteria:**
- Timestamp set on successful export
- `may_be_stale` flag computed when `last_modified_at > last_exported_at`
- UI can show warning badge on stale templates (future enhancement)

---

### Task 4: Update Agent Template Export Flow

**Files:**
- `api/endpoints/templates.py` (export endpoint)
- `frontend/src/components/settings/AgentTemplateManager.vue`

**Changes:**
1. Set `last_exported_at` when templates exported
2. Show "may be stale" indicator in UI if template modified since last export
3. Include export timestamp in downloaded `.md` files (optional - in header comment)

**Acceptance Criteria:**
- Export sets timestamp in DB
- UI shows visual indicator for stale templates
- User can see when they last exported

---

## Testing Requirements

### Unit Tests

```python
# test_orchestration_service_cli_rules.py

def test_get_orchestrator_instructions_includes_cli_rules_when_cli_mode():
    """CLI mode response includes cli_mode_rules and spawning_examples."""

def test_get_orchestrator_instructions_excludes_cli_rules_when_multi_terminal():
    """Multi-terminal mode response does NOT include cli_mode_rules."""

def test_cli_mode_rules_structure():
    """Verify cli_mode_rules contains required fields."""

# test_thin_prompt_generator_cli_validation.py

def test_staging_prompt_includes_validation_section_cli_mode():
    """CLI mode staging prompt includes agent validation section."""

def test_staging_prompt_excludes_validation_section_multi_terminal():
    """Multi-terminal staging prompt does NOT include validation section."""

def test_staging_prompt_lists_available_agents():
    """Staging prompt includes actual agent template names."""
```

### Integration Tests

```python
def test_full_staging_flow_cli_mode():
    """
    1. Create project with execution_mode='claude_code_cli'
    2. Call get_orchestrator_instructions
    3. Verify cli_mode_rules present
    4. Generate staging prompt
    5. Verify validation section present
    """

def test_template_staleness_detection():
    """
    1. Export templates (sets last_exported_at)
    2. Modify template (updates last_modified_at)
    3. Verify may_be_stale=True in response
    """
```

---

## Files Summary

| File | Action | Description |
|------|--------|-------------|
| `src/giljo_mcp/services/orchestration_service.py` | Modify | Add `cli_mode_rules` to response |
| `src/giljo_mcp/thin_prompt_generator.py` | Modify | Add validation section to staging prompt |
| `src/giljo_mcp/models/agents.py` | Modify | Add `last_exported_at` column |
| `api/endpoints/templates.py` | Modify | Set timestamp on export |
| `frontend/.../AgentTemplateManager.vue` | Modify | Show staleness indicator |
| `tests/services/test_orchestration_service_cli_rules.py` | Create | Unit tests |
| `tests/unit/test_thin_prompt_generator_cli_validation.py` | Create | Prompt tests |

---

## Multi-Terminal Mode (No Changes)

In multi-terminal mode:
- User copies individual agent prompts from Jobs tab
- Each prompt is self-contained (fetched from server)
- No template validation needed - server provides everything
- `cli_mode_rules` NOT included in response
- Validation section NOT included in staging prompt

---

## Success Criteria

1. **CLI mode staging prompt** includes:
   - Agent spawning rules table (agent_type vs agent_name)
   - Task tool mapping explanation
   - Template validation steps with `ls` commands
   - Soft warning guidance

2. **`get_orchestrator_instructions` response** (CLI mode only) includes:
   - `cli_mode_rules` object with usage instructions
   - `spawning_examples` with correct patterns

3. **Template staleness tracking**:
   - `last_exported_at` timestamp in DB
   - `may_be_stale` flag in response when applicable
   - UI indicator for stale templates

4. **Multi-terminal mode unchanged**

5. **All tests passing**

---

## Estimated Effort

| Task | Effort |
|------|--------|
| Task 1: Enhance get_orchestrator_instructions | 1-2 hours |
| Task 2: Update staging prompt | 2 hours |
| Task 3: Add last_exported_at tracking | 1-2 hours |
| Task 4: Update export flow + UI | 1-2 hours |
| Testing | 2 hours |
| **Total** | **7-10 hours** |

---

## Related Handovers

- **0260**: Claude Code CLI Mode (toggle persistence) - COMPLETE
- **0261**: CLI Implementation Prompt - SUPERSEDED by this + future 0336
- **0332**: Agent Staging & Execution Overview - Reference
- **0333**: Staging Prompt Architecture Correction - COMPLETE
- **0334**: HTTP-Only MCP Consolidation - COMPLETE

---

## Future Work (Not in Scope)

- **0336**: CLI Mode Implementation Prompt (Jobs tab orchestrator copy button)
- Automatic template sync (push from server to Claude Code)
- Template version diffing (show what changed)

---

**End of Handover 0335**
