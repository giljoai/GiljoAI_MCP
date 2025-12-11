# Session Memory: Handover 0339 - Agent Naming Enforcement Analysis

**Date**: 2025-12-09
**Session Type**: Investigation & Planning
**Status**: Analysis Complete - Ready for Implementation
**Related Handovers**: 0335 (CLI Mode Validation), 0261 (Implementation Prompt), 0260 (Toggle Persistence)

---

## Executive Summary

Comprehensive investigation into "belt-and-suspenders" strict enforcement of agent naming in Claude Code CLI mode. **Multi-Terminal mode works perfectly and requires NO changes**. Analysis identifies 3 gaps in CLI mode enforcement and provides detailed implementation plan.

**Key Finding**: CLI mode needs stronger two-phase enforcement (STAGING + IMPLEMENTATION) with explicit agent_type strictness and template staleness checking.

---

## User Request

> "Please review last couple of git commits to see how and what we did here. I gave these two examples, here is more context... please use task tool and subagents to investigate and analyze if we have best strict enforcement."

**User clarified the architecture:**
- Belt-and-suspenders = Prompt text + MCP response + Template files (3 layers)
- Multi-Terminal mode ALREADY WORKS PERFECTLY - no changes needed
- Strictness needed ONLY for Claude Code CLI mode in TWO phases
- `agent_type` is SINGLE SOURCE OF TRUTH for Task tool calling

---

## Investigation Methodology

Launched 3 parallel Explore agents to examine:
1. **Staging prompt generation** (`thin_prompt_generator.py`)
2. **MCP orchestrator instructions** (`tool_accessor.py`)
3. **Agent spawn validation** (`orchestration.py`)

---

## Findings Summary

### ✅ What Works (No Changes Needed)

**Multi-Terminal Mode:**
- Orchestrator reads available agents from `get_orchestrator_instructions()`
- Agent selection is lenient but accurate
- Works splendidly today
- **NO CHANGES REQUIRED**

**Validation Layer (Both Modes):**
- `spawn_agent_job()` validates agent_type against active templates
- Rejects invalid types with helpful error messages
- Works in BOTH modes
- Lines 2162-2196 in `orchestration.py`

### ⚠️ Gaps in CLI Mode

**Gap 1: Staleness Check Missing**
- Database has `may_be_stale` flag (from Handover 0335)
- Orchestrator does NOT check during staging
- No warning if templates modified but not exported

**Gap 2: Two-Phase Enforcement Not Explicit**
- Current prompt mentions Task tool but not strongly enough
- Need EXPLICIT rules for BOTH phases:
  - **STAGING**: spawn_agent_job(agent_type="implementer", ...)
  - **IMPLEMENTATION**: Task(subagent_type="implementer", ...)
- SAME value required in both phases

**Gap 3: Function Naming Context Clues**
- User question: Can parameter names provide additional context?
- Examples: `agent_type` vs `template_name` vs `agent_template`
- Trade-off: Clarity vs refactor scope

---

## Architecture Deep Dive

### Belt-and-Suspenders Layers (CLI Mode Only)

1. **Layer 1: Staging Prompt Text** (human-readable)
   - Location: `src/giljo_mcp/thin_prompt_generator.py` (lines 1003-1050)
   - Current: AGENT SPAWNING RULES table (only when `claude_code_mode=True`)
   - Gap: Needs stronger two-phase emphasis

2. **Layer 2: MCP Response** (machine-readable)
   - Location: `src/giljo_mcp/tools/tool_accessor.py` (lines 644-702)
   - Current: Returns `cli_mode_rules`, `agent_spawning_constraint`, `spawning_examples`
   - Gap: Needs staleness warning and two-phase enforcement structure

3. **Layer 3: Template Files** (behavior rules)
   - Location: `/.claude/agents/{agent_type}.md`
   - Exported during SETUP (not during staging/implementation)
   - Cannot be hotloaded in Claude Code

### Agent Naming Hierarchy

**`agent_type`** (SINGLE SOURCE OF TRUTH):
- MUST match exact template filename (e.g., "implementer" → `implementer.md`)
- Used in BOTH phases:
  - **Staging**: `spawn_agent_job(agent_type="implementer", ...)`
  - **Implementation**: `Task(subagent_type="implementer", ...)`
- NEVER use variations, extensions, or creative names

**`agent_name`** (DISPLAY ONLY):
- Unique display label (e.g., "Backend_Implementor", "Frontend_Implementor")
- Used ONLY for:
  - Agent cards visualization
  - MCP communications/audit trails
  - Example: "{agent_type}IMPLEMENTOR, {agent_ID}xxxxx, {agent_name}BACKEND_IMPLEMENTOR sends message"
- **NEVER used for Task tool calling**

**Potential Refactor (User Considering):**
- Rename `agent_type` → `agent_template` or `template_name`
- Rename `agent_name` → `agent_badge_name` or `agent_display_name`
- Need to assess refactor scope (8-12 hours estimated)

---

## Current Implementation Review

### Staging Prompt (lines 1003-1050)

**Current code structure:**
```python
if claude_code_mode:
    mode_block = """
    ## AGENT SPAWNING RULES (CLI MODE - CRITICAL)

    When spawning agents, you MUST use TWO parameters correctly:

    | Parameter    | Purpose                      | Value Must Be               |
    |--------------|------------------------------|----------------------------|
    | `agent_type` | Template name for Task tool  | EXACT match: "implementer" |
    | `agent_name` | Human-readable UI label      | Descriptive: "Folder Impl" |

    ### Why This Matters
    Claude Code's Task tool finds agents by filename:
    - `Task(subagent_type="implementer")` → looks for `implementer.md` ✓
    - `Task(subagent_type="Folder Implementer")` → FILE NOT FOUND ✗
    """
```

**Gap**: Needs two-phase enforcement (staging + implementation)

### MCP Response (lines 644-702)

**Current code structure:**
```python
if execution_mode == 'claude_code_cli':
    response["cli_mode_rules"] = {
        "agent_type_usage": "MUST match template 'name' field exactly...",
        "agent_name_usage": "Descriptive label for UI display only...",
        "task_tool_mapping": "Task(subagent_type=X) where X = agent_type...",
        "validation": "soft",
        "template_locations": [...]
    }

    response["agent_spawning_constraint"] = {
        "mode": "strict_task_tool",
        "allowed_agent_types": [...],
        "instruction": "CRITICAL: You MUST use Claude Code's native Task tool..."
    }
```

**Gaps**:
- No staleness warning
- Validation mode is "soft" (should be "strict")
- No explicit two-phase enforcement structure

### Validation (lines 2162-2196)

**Current code structure:**
```python
# Validate agent_type against active templates (BOTH modes)
if agent_type != "orchestrator":
    template_result = await session.execute(
        select(AgentTemplate.name).where(...)
    )
    valid_agent_types = [row[0] for row in template_result.fetchall()]

    if agent_type not in valid_agent_types:
        return {
            "success": False,
            "error": f"Invalid agent_type '{agent_type}'. Must be one of: {valid_agent_types}",
            "hint": "Use agent_name for descriptive labels, agent_type must match template exactly"
        }
```

**Status**: ✅ Working perfectly - no changes needed

---

## Implementation Plan

### Task 1: Add Staleness Check to Staging (CRITICAL)

**Files to modify:**
- `src/giljo_mcp/thin_prompt_generator.py`
- `src/giljo_mcp/tools/tool_accessor.py`

**A. In `get_orchestrator_instructions()` MCP response:**

```python
# Check for stale templates (CLI mode only)
stale_templates = [
    {"name": t.name, "last_exported_at": t.last_exported_at, "updated_at": t.updated_at}
    for t in templates
    if t.may_be_stale
]

if stale_templates and execution_mode == 'claude_code_cli':
    response["template_staleness_warning"] = {
        "has_stale_templates": True,
        "stale_templates": stale_templates,
        "recommendation": (
            "Some agent templates have been modified since last export. "
            "Re-export templates from GiljoAI Settings → Agent Template Manager before staging."
        )
    }
```

**B. In staging prompt (CLI mode block):**

```markdown
## TEMPLATE STALENESS CHECK (CLI MODE - CRITICAL)

Before spawning agents, verify templates are up-to-date.

The `get_orchestrator_instructions()` response includes `template_staleness_warning` if any templates are stale.

If `has_stale_templates: true`:
- WARN USER: "⚠️ Agent templates have been modified but not exported to Claude Code CLI"
- LIST stale templates with update times
- RECOMMEND: "Export templates from GiljoAI Settings → Agent Template Manager"
- ASK USER: "Proceed anyway? (y/n)"

Template mismatches can cause:
- Agents using outdated behavior rules
- Missing new capabilities
- Unexpected agent behavior
```

**Testing:**
- Unit test: Verify staleness warning appears when `may_be_stale=True`
- Integration test: Mock stale templates and verify prompt includes warning

---

### Task 2: Strengthen Two-Phase Enforcement (CRITICAL)

**Files to modify:**
- `src/giljo_mcp/thin_prompt_generator.py` (lines 1003-1050)
- `src/giljo_mcp/tools/tool_accessor.py` (lines 644-702)

**A. Enhance CLI mode block in staging prompt:**

```markdown
## CLAUDE CODE CLI MODE - AGENT TEMPLATE STRICTNESS

**CRITICAL:** You CANNOT hotload agents in Claude Code CLI.
Templates must be exported to `/.claude/agents/` folder BEFORE staging.

### PHASE 1: STAGING (spawn_agent_job)
When spawning agents during staging, `agent_type` parameter MUST:
- Match EXACT template name exported to `/.claude/agents/{agent_type}.md`
- Example: agent_type="implementer" → file must be `implementer.md`

**spawn_agent_job() RULES:**
```python
spawn_agent_job(
    agent_type="implementer",      # ✅ MUST match exported template filename
    agent_name="Backend Implementor"  # ✅ Display label (flexible)
)
```

**VERIFICATION REQUIRED:**
Before spawning, check `get_orchestrator_instructions()` response for:
- `template_staleness_warning` - warns if templates modified but not exported
- `allowed_agent_types` - lists ONLY available template names

### PHASE 2: IMPLEMENTATION (Task tool)
When implementing, Task tool spawning MUST use SAME agent_type:

```python
# From Phase 1 spawning
spawn_agent_job(agent_type="implementer", agent_name="Backend Implementor", ...)

# In Phase 2 Task tool - use EXACT SAME agent_type
Task(subagent_type="implementer", ...)  # ✅ CORRECT - matches spawning

# FORBIDDEN:
Task(subagent_type="Backend Implementor", ...)  # ❌ WRONG - uses agent_name
Task(subagent_type="backend-implementor", ...)  # ❌ WRONG - variation
```

**SINGLE SOURCE OF TRUTH:** The `agent_type` value from spawning is THE ONLY value for Task tool.

### Why This Strictness?
- Claude Code searches for `.claude/agents/{subagent_type}.md`
- Templates cannot be hotloaded during execution
- Mismatches cause "template not found" errors
- No recovery possible once implementation starts
```

**B. Add two-phase enforcement to MCP response:**

```python
if execution_mode == 'claude_code_cli':
    # Enhanced cli_mode_rules
    response["cli_mode_rules"] = {
        "agent_type_usage": (
            "MUST match EXACT template filename in /.claude/agents/ folder. "
            "Used in BOTH spawn_agent_job() during staging AND Task tool during implementation. "
            "This is the SINGLE SOURCE OF TRUTH for agent template identification."
        ),
        "agent_name_usage": (
            "Display label ONLY. NEVER use for Task tool calling. "
            "Can be any descriptive name for UI, messages, audit trails."
        ),
        "task_tool_mapping": (
            "Task(subagent_type=X) where X = agent_type from spawn_agent_job. "
            "CRITICAL: Use the EXACT SAME value - no variations, no substitutions."
        ),
        "validation": "strict",  # Changed from "soft"
        "no_hotloading": "Templates cannot be loaded during execution - must be exported before staging",
        "phase_consistency": "agent_type value must be IDENTICAL in staging and implementation phases"
    }

    # New: Explicit two-phase enforcement
    response["two_phase_enforcement"] = {
        "staging_phase": {
            "tool": "spawn_agent_job",
            "parameter": "agent_type",
            "constraint": "MUST match exported template name",
            "example": 'spawn_agent_job(agent_type="implementer", ...)'
        },
        "implementation_phase": {
            "tool": "Task",
            "parameter": "subagent_type",
            "constraint": "MUST match agent_type from staging phase",
            "example": 'Task(subagent_type="implementer", ...)'
        },
        "critical_rule": "The agent_type value must be IDENTICAL in both phases"
    }
```

**Testing:**
- Unit test: Verify two-phase enforcement structure in MCP response
- Unit test: Verify "strict" validation mode
- Integration test: Staging prompt includes phase consistency rules

---

### Task 3: Strengthen Task Tool Language (OPTIONAL)

**File:** `src/giljo_mcp/thin_prompt_generator.py` (CLI mode block)

**Add explicit forbidden examples:**

```markdown
## ⚠️ TASK TOOL CALLING - ABSOLUTE RULES ⚠️

**SINGLE SOURCE OF TRUTH:** `agent_type` is the ONLY value used for Task tool.

**DURING IMPLEMENTATION PHASE:**
When you spawn agents via Task tool, you MUST use:
- Task(subagent_type=<agent_type>, ...)

**FORBIDDEN VARIATIONS (WILL FAIL):**
- ❌ Task(subagent_type=<agent_name>, ...)
- ❌ Task(subagent_type="{agent_name}", ...)
- ❌ Task(subagent_type="Backend Implementor", ...)
- ❌ Task(subagent_type="Frontend-Implementor", ...)
- ❌ Any creative variation or extension

**WHY:**
Claude Code's Task tool searches for `.claude/agents/{subagent_type}.md`
- If subagent_type="implementer" → looks for `implementer.md` ✅
- If subagent_type="Backend Implementor" → looks for `Backend Implementor.md` ❌ NOT FOUND

**VERIFICATION:**
Before calling Task tool, verify:
1. The agent was spawned with agent_type="X"
2. Use THAT EXACT VALUE: Task(subagent_type="X", ...)
3. Never substitute agent_name
```

**Testing:**
- Manual review of prompt readability
- User acceptance testing

---

## Files Affected Summary

| File | Lines | Changes | Priority |
|------|-------|---------|----------|
| `src/giljo_mcp/thin_prompt_generator.py` | 1003-1050 | Add staleness check, two-phase enforcement | CRITICAL |
| `src/giljo_mcp/tools/tool_accessor.py` | 644-702 | Add staleness warning, two-phase structure | CRITICAL |
| `tests/unit/test_thin_prompt_generator_cli_validation.py` | Various | Update tests for new rules | HIGH |
| `tests/services/test_orchestration_service_cli_rules.py` | Various | Add staleness check tests | HIGH |

---

## Success Criteria

1. ✅ **Staleness check**: Orchestrator warned if CLI templates stale
2. ✅ **Two-phase enforcement**: Explicit rules for STAGING and IMPLEMENTATION
3. ✅ **Task tool strictness**: Crystal clear that agent_type is ONLY value
4. ✅ **CLI mode belt-and-suspenders**: Strictness in prompt + MCP response
5. ✅ **Multi-terminal untouched**: No changes to multi-terminal mode
6. ✅ **No regressions**: Existing functionality unchanged
7. ✅ **Tests passing**: All unit and integration tests green

---

## Open Questions for User

### 1. Function/Parameter Naming Strategy

Should we make parameter names MORE explicit for additional context clues?

**Current naming:**
- `agent_type` (parameter in spawn_agent_job)
- `subagent_type` (parameter in Task tool)

**Potential alternatives:**
- `template_name` or `agent_template_name` (more explicit)
- `exported_template_id` (emphasizes must be exported)
- `strict_template_identifier` (emphasizes strictness)

**Trade-offs:**
- **Pro**: More self-documenting, harder to confuse
- **Con**: Larger refactor (8-12 hours), breaks existing code
- **Con**: May be overly verbose

**User decision needed**: Keep current naming or initiate refactor?

### 2. Validation Mode

Current MCP response has `"validation": "soft"`. Should we change to `"strict"`?
- **Soft**: Warns but allows proceeding
- **Strict**: Blocks invalid operations

**Recommendation**: Change to "strict" for CLI mode only

---

## Related Documentation

- **Handover 0335**: CLI Mode Agent Template Validation (COMPLETE)
- **Handover 0261**: Claude Code CLI Implementation Prompt (PENDING)
- **Handover 0260**: Claude Code CLI Toggle Enhancement (COMPLETE)
- **Handover 0334**: HTTP-Only MCP Consolidation (COMPLETE)
- **Handover 0246a-c**: Orchestrator Workflow Pipeline (COMPLETE)

---

## Implementation Timeline Estimate

**Task 1** (Staleness Check): 2-3 hours
- MCP response modification: 1 hour
- Staging prompt update: 1 hour
- Tests: 1 hour

**Task 2** (Two-Phase Enforcement): 3-4 hours
- MCP response structure: 1.5 hours
- Staging prompt enhancement: 1.5 hours
- Tests: 1 hour

**Task 3** (Task Tool Language): 1 hour
- Prompt text enhancement: 0.5 hours
- Manual review: 0.5 hours

**Total Estimate**: 6-8 hours

---

## Notes for Implementation

### Critical Principles

1. **Multi-Terminal Mode = Untouchable**
   - Already works perfectly
   - Do NOT add rules to multi-terminal prompts or MCP responses
   - Only CLI mode needs changes

2. **agent_type is Sacred**
   - SINGLE SOURCE OF TRUTH for CLI mode
   - Used in BOTH staging and implementation phases
   - No variations, no substitutions, no creativity

3. **agent_name is Display Only**
   - Never used for tool calling
   - Can be any unique descriptive name
   - Purpose: UI visualization and audit trails

4. **Templates Cannot Hotload**
   - Must be exported BEFORE staging begins
   - Staleness check prevents mismatches
   - No recovery possible once implementation starts

---

## Conclusion

This investigation confirms that:
- ✅ Multi-Terminal mode works perfectly (no changes)
- ⚠️ CLI mode needs 3 enhancements:
  1. Staleness checking during staging
  2. Explicit two-phase enforcement (staging + implementation)
  3. Stronger Task tool strictness language

Implementation is straightforward, well-scoped, and low-risk. All changes are additive (no breaking changes to existing functionality).

**Ready for implementation pending user decision on naming strategy question.**

---

**Document Version**: 1.0
**Created**: 2025-12-09
**Author**: Deep Researcher + System Architect Agents
**Next Steps**: User review → Implementation → Testing → Documentation update
