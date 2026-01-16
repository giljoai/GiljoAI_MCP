# Handover 0417: Multi-Terminal Mode Template Injection

**Date**: 2026-01-16
**From Agent**: Research/Planning Session
**To Agent**: TDD Implementor
**Priority**: HIGH
**Estimated Complexity**: 4-6 hours
**Status**: Ready for Implementation
**Branch**: `0417-multi-terminal-template-injection`

---

## Objective

Implement backend auto-injection of agent templates for multi-terminal mode, reducing orchestrator token usage and ensuring agents receive their expertise automatically.

## Problem Statement

### Current State (Multi-Terminal Mode)
When orchestrator spawns an agent in multi-terminal mode:
1. Orchestrator must write **full role/expertise** into the `mission` parameter
2. This wastes ~500+ tokens per agent on role description
3. Role information may be inconsistent with template definitions
4. Agent's expertise is embedded in orchestrator's context, not database

### Current State (Claude Code CLI Mode)
When orchestrator spawns via Task tool:
1. Task tool loads `.claude/agents/{agent_name}.md` template automatically
2. Template contains full expertise (~170 lines, ~1400 tokens)
3. Orchestrator only provides thin identity + work assignment
4. Works correctly - no changes needed

### Root Cause
Multi-terminal mode lacks template injection. The toggle between modes should determine whether the backend injects template content.

---

## Solution: Option A - Backend Auto-Injection

When `spawn_agent_job()` is called in multi-terminal mode:

```
spawn_agent_job(agent_name="implementer", mission="Build feature X")
    ↓
Backend: Look up AgentTemplate WHERE name = agent_name
    ↓
Backend: AgentJob.mission = template_content + "\n\n---\n\n" + orchestrator's work
    ↓
Agent: get_agent_mission() → Gets template expertise + specific work
```

### Benefits
- **85% orchestrator token savings**: Just pass agent_name + work description
- **Single source of truth**: AgentTemplate in DB = exported .claude/agents/*.md
- **Consistency**: Same expertise regardless of how orchestrator phrases it
- **No new tools needed**: Uses existing `get_agent_mission()` flow

---

## Technical Specification

### 1. Modify `spawn_agent_job()` in `orchestration.py`

**Location**: `src/giljo_mcp/tools/orchestration.py:752-1020`

**Logic**:
```python
async def spawn_agent_job(
    agent_display_name: str,
    agent_name: str,
    mission: str,  # Now just the work assignment
    project_id: str,
    tenant_key: str,
    ...
) -> dict:
    # NEW: Check execution mode
    project = await session.execute(select(Project).where(Project.id == project_id))
    execution_mode = project.execution_mode  # "multi_terminal" or "claude_code_cli"

    if execution_mode == "multi_terminal":
        # Look up template by agent_name
        template = await session.execute(
            select(AgentTemplate).where(
                AgentTemplate.name == agent_name,
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active == True
            )
        )

        if template:
            # Inject template content into mission
            template_expertise = template.template_content or template.user_instructions or ""
            full_mission = f"{template_expertise}\n\n---\n\nYOUR ASSIGNED WORK:\n{mission}"
        else:
            # No template found - log warning but proceed with orchestrator's mission
            logger.warning(f"No template found for agent_name={agent_name}")
            full_mission = mission
    else:
        # Claude Code CLI mode - template loaded by Task tool
        full_mission = mission

    # Store full_mission in AgentJob.mission
    agent_job = AgentJob(
        mission=full_mission,
        ...
    )
```

### 2. Template Manager Simplification

**Location**: `src/giljo_mcp/template_manager.py`

**Current Issues**:
- `agent_type` vs `agent_name` confusion
- Tool-specific icons (codex, gemini symbols)
- Complex suffix handling

**Simplifications**:
1. **agent_name = single source of truth**: Matches template filename and DB lookup key
2. **Remove tool-specific icons**: Consolidate to ONE template format
3. **Assume Codex/Gemini = multi-terminal mode**: No special handling needed

**Key Fields**:
- `AgentTemplate.name` = agent_name (e.g., "tdd-implementor")
- `AgentTemplate.category` = display category (e.g., "implementer")
- `AgentTemplate.template_content` = full expertise text

### 3. Template Content Structure

Follow 0415's chapter-based pattern for consistency. Template should include:

```markdown
## CRITICAL: MCP TOOLS ARE NATIVE TOOL CALLS
[~30 lines of MCP usage instructions]

## MCP TOOL SUMMARY
[~60 lines of tool reference]

## CHECK-IN PROTOCOL
[~15 lines]

## INTER-AGENT MESSAGING PROTOCOL
[~20 lines]

---

## Role-Specific Instructions
[~35 lines of agent expertise]

## Behavioral Rules
[~5-10 lines]

## Success Criteria
[~5-10 lines]
```

**Total**: ~175 lines (~1400 tokens)

### 4. Template Export Consistency

Ensure `/gil_get_claude_agents` exports templates that match what backend injects:
- Same content in `.claude/agents/*.md` as in `AgentTemplate.template_content`
- Both are generated from same database source

---

## Execution Mode Toggle

The toggle lives in `Project.execution_mode`:
- `"claude_code_cli"` = Task tool loads templates → NO injection needed
- `"multi_terminal"` = Manual terminal launches → Backend MUST inject

**UI Location**: Project settings, mode selection during staging

---

## Implementation Plan

### Phase 1: Unit Tests (RED)
Create `tests/unit/test_template_injection.py`:
1. `test_spawn_agent_job_injects_template_for_multi_terminal_mode`
2. `test_spawn_agent_job_no_injection_for_cli_mode`
3. `test_template_lookup_uses_agent_name`
4. `test_template_not_found_logs_warning_proceeds`
5. `test_injected_mission_structure`
6. `test_full_mission_contains_template_plus_work`

### Phase 2: Backend Implementation (GREEN)
1. Modify `spawn_agent_job()` in `orchestration.py`
2. Add template lookup by agent_name
3. Compose full_mission with injection
4. Log template injection events

### Phase 3: Template Manager Cleanup (REFACTOR)
1. **Remove tool-specific code**:
   - Delete `codex_icon`, `gemini_icon`, `cli_tool` field handling
   - Remove any tool-detection logic (all non-Claude-CLI = multi-terminal)
2. **Simplify naming**:
   - `agent_name` = template lookup key (single source of truth)
   - `agent_display_name` = UI display category only
   - Remove `agent_type` confusion (was alias for display_name)
3. **Update legacy template loading**:
   - Ensure `_load_legacy_templates()` uses consistent naming
4. **Cache invalidation**: Verify cache works with simplified structure

### Phase 4: Integration Tests
1. E2E test: spawn with injection
2. Verify get_agent_mission() returns full content
3. Test template cache refresh after update

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/giljo_mcp/tools/orchestration.py` | Add template injection logic to spawn_agent_job() |
| `src/giljo_mcp/services/orchestration_service.py` | Add template injection to service layer spawn |
| `src/giljo_mcp/template_manager.py` | Simplify, remove tool-specific complexity |
| `src/giljo_mcp/models/templates.py` | Verify agent_name as lookup key |
| `tests/unit/test_template_injection.py` | New test file |
| `tests/integration/test_multi_terminal_spawn.py` | Integration tests |

---

## Success Criteria

- [ ] Multi-terminal spawn includes template content in AgentJob.mission
- [ ] CLI mode spawn does NOT inject (unchanged behavior)
- [ ] Template lookup uses agent_name (case-sensitive match)
- [ ] Missing template logs warning but proceeds with orchestrator's mission
- [ ] All unit tests pass
- [ ] Integration tests verify end-to-end flow
- [ ] Template manager simplified (no tool-specific code)

---

## Token Impact

| Component | Before | After |
|-----------|--------|-------|
| Orchestrator spawn call | ~500 tokens (full role) | ~50 tokens (work only) |
| AgentJob.mission | ~50 tokens (work only) | ~1450 tokens (template + work) |
| Agent's get_agent_mission | ~1450 tokens (template + protocol) | ~1600 tokens (same + work) |
| **Orchestrator savings** | - | **~450 tokens per agent** |

---

## Dependencies

- Handover 0415: Chapter-based protocol (COMPLETE) - use same framing pattern
- Handover 0351: agent_name as single source of truth (COMPLETE) - foundation
- Handover 0366: Agent identity refactor (COMPLETE) - AgentJob/AgentExecution model

---

## CLI Tool Strategy: Multi-Terminal as Universal Solution

**Decision**: Treat ALL non-Claude-Code-CLI tools as multi-terminal mode.

### Rationale

Per research in `Reference_docs/gemini_vs_claude_agent_templates.md`:

| CLI Tool | Subagent Support | Our Approach |
|----------|------------------|--------------|
| **Claude Code CLI** | Native Task tool (mature) | Task tool loads templates |
| **Claude Code Web** | None | Multi-terminal mode |
| **Gemini CLI** | Experimental/community | Multi-terminal mode |
| **Codex CLI** | None | Multi-terminal mode |

**Why NOT implement Gemini's native extension system:**
1. **Experimental** - Gemini's subagent is community-driven, not production-ready
2. **Different architecture** - Extensions are folders (JSON + MD + TOML), not single files
3. **Our MCP is the coordination layer** - Agents coordinate via MCP tools, not CLI features
4. **Maintenance burden** - Supporting native Gemini extensions adds complexity for minimal gain
5. **Template injection solves it universally** - Works for ALL CLIs without special handling

### Simplifications

1. **Remove tool-specific icons/symbols** - No `codex_icon`, `gemini_icon` in TemplateManager
2. **ONE template format** - MD with YAML frontmatter (Claude Code format is canonical)
3. **Single export endpoint** - `/gil_get_claude_agents` exports to `.claude/agents/*.md`
4. **Universal injection** - Multi-terminal mode + template injection works for ALL CLIs

### Future Consideration

If Gemini's subagent support matures to a native file format, we can add:
```
/gil_get_gemini_agents → extension folders
```
But this is a future enhancement, NOT a blocker for this handover.

---

## Rollback Plan

If issues arise:
1. Revert spawn_agent_job() changes
2. Template manager changes are backward-compatible
3. No database schema changes required

---

## References

- Handover 0415: `handovers/0415_thin_client_chapter_protocol.md` (framing pattern)
- Template Manager: `src/giljo_mcp/template_manager.py`
- Orchestration Tools: `src/giljo_mcp/tools/orchestration.py`
- Agent Identity Models: `src/giljo_mcp/models/agent_identity.py`
- Gemini Research: `handovers/Reference_docs/gemini_vs_claude_agent_templates.md`
- TinyContacts Templates: `F:\TinyContacts\.claude\agents\` (example structure)

---

## Recommended Sub-Agent

**TDD Implementor** - This task requires:
- Unit tests first (TDD approach)
- Backend service modification
- Integration testing
- Template manager refactoring

---

## Questions for User

1. **Template content field**: Use `template_content` or create separate `role_instructions` field?
   - Recommendation: Use `template_content` for simplicity (Option A)

2. **Fallback behavior**: If template not found, should we:
   - (A) Proceed with orchestrator's mission + warning
   - (B) Fail the spawn
   - Recommendation: (A) - graceful degradation

3. **Template export sync**: Should we update `/gil_get_claude_agents` to use same `template_content` source?
   - Recommendation: Yes - ensures consistency
