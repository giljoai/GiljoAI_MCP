# Handover 0847: Tool-Aware Orchestrator Protocol

**Date:** 2026-03-29
**Edition Scope:** CE
**Priority:** High
**Estimated Complexity:** 2-3 hours
**Status:** Not Started

## Task Summary

Make the orchestrator protocol (CH1-CH4 + orchestrator_identity) fully tool-aware so each platform receives only its own native language. Currently only CH3 branches on `tool`; the rest is Claude-centric. Codex alpha test confirmed this causes Codex to misinterpret spawning semantics — it saw Claude Code references first and treated Codex instructions as a footnote.

Also rebrand multi-terminal mode from "Claude Code Web" to "Any MCP-Connected Agent" — the generic mode where agent templates are fetched from the server and any tool can consume them.

## Context and Background

**What broke:** Codex CLI spawned generic workers instead of using installed `gil-*` agent templates. The prompt told Codex *what syntax to use* but never explained *what `agent=` mechanically does* (loads a `.toml` with baked-in behavior). Codex over-instructed in `instructions=` and effectively overwrote the template.

**Root causes from alpha review:**
1. CH1 says "do NOT call Task() tool" — that's Claude-only language. Codex has `spawn_agent()`, Gemini has `@agent`.
2. CH3 leads with `.claude/agents/{name}.md` file mapping and Claude Code CLI Note before showing the platform-specific block
3. `orchestrator_identity` hardcodes "Two Execution Modes: Claude Code CLI / Multi-terminal"
4. No explanation anywhere that `agent='gil-X'` loads an installed template with its own developer_instructions
5. No "DO NOT spawn generic workers" guardrail for Codex
6. Multi-terminal references "Claude Code Web" — should be generic "any MCP tool"

## Technical Details

### Files to Modify

**1. `src/giljo_mcp/services/protocol_builder.py`**
- `_build_ch1_mission()` → accept `tool` param, replace `Task()` with platform-native "do not" example
- `_build_ch2_startup()` → no changes needed (already platform-agnostic)
- `_build_ch3_spawning_rules(tool)` → restructure: platform block comes FIRST, remove Claude-specific file mapping from shared section, add Codex mechanical explanation
- `_build_ch4_error_handling()` → no changes needed (already platform-agnostic)
- `_build_ch5_reference()` → accept `tool` param, use platform-native spawning syntax in coordination patterns
- `_build_orchestrator_protocol()` → pass `tool` to ch1 and ch5

**2. `src/giljo_mcp/template_seeder.py`**
- `get_orchestrator_identity_content()` → accept `tool` param (or make identity platform-neutral)
- Orchestrator template `user_instructions` at line 238 → replace "Two Execution Modes" with dynamic or neutral language

**3. `src/giljo_mcp/services/orchestration_service.py`**
- `get_orchestrator_instructions()` around line 3142 → pass `tool` to `get_orchestrator_identity_content()`
- `_build_execution_mode_fields()` → update multi-terminal label/description to "Any MCP-Connected Agent"

**4. `src/giljo_mcp/thin_prompt_generator.py`**
- `_build_codex_execution_prompt()` → add "DO NOT spawn generic workers" block, add "keep instructions= minimal" guidance

**5. Frontend (label only)**
- `frontend/src/components/projects/ProjectTabs.vue` → rename "Multi-Terminal" radio label to "Any Coding Agent" or similar

### No Database Changes
All protocol content is built dynamically at request time — no migration needed.

## Implementation Plan

### Phase 1: Protocol Builder — Tool-Aware CH1 + CH3 + CH5

**CH1 changes (small):**
```python
def _build_ch1_mission(tool: str = "claude-code") -> str:
```
Replace line 649:
```
- You do NOT call Task() tool (that's for implementation phase)
```
With platform-specific:
- `claude-code`: "You do NOT call Task() tool"
- `codex`: "You do NOT call spawn_agent() tool"
- `gemini`: "You do NOT invoke @agent commands"
- `multi_terminal` / default: "You do NOT execute implementation work directly"

**CH3 restructure (main work):**
1. Move the `Claude Code CLI Mode Note` block (lines 1055-1058) INTO the `elif cli_mode:` branch — it currently lives in the shared PARAMETER REQUIREMENTS section where all platforms see it
2. Remove the `.claude/agents/{agent_name}.md` file mapping from shared section — replace with platform-specific mapping:
   - Claude: `.claude/agents/{agent_name}.md`
   - Codex: `~/.codex/agents/gil-{agent_name}.toml`
   - Gemini: `~/.gemini/agents/{agent_name}.md`
   - Generic: "Agent templates are fetched from the MCP server via get_orchestrator_instructions()"
3. For Codex block, ADD mechanical explanation:
   ```
   WHAT agent= DOES: Loads the installed agent template file at
   ~/.codex/agents/gil-{agent_name}.toml which contains developer_instructions,
   model config, and sandbox settings. The agent ALREADY KNOWS its role from
   the template — you do NOT need to re-explain it in the instructions= parameter.

   DO NOT spawn a generic/default worker and instruct it to "act as" a GiljoAI agent.
   The instructions= parameter should contain ONLY:
     - The job_id
     - The MCP call to fetch its mission: mcp__giljo-mcp__get_agent_mission(job_id="...")
   The template handles everything else.
   ```
4. For Gemini block, ADD equivalent explanation for `@agent` or `/agent` loading

**CH5 changes (small):**
Pass `tool` and use platform-native spawn syntax in coordination pattern examples.

### Phase 2: Orchestrator Identity — Platform-Neutral

Replace the hardcoded "Two Execution Modes" block in template_seeder.py:
```python
# Before:
- **Two Execution Modes**:
  - **Claude Code CLI**: Spawn sub-agents via Task tool (single terminal)
  - **Multi-terminal**: User copies prompts into separate terminals

# After (platform-neutral):
- **Execution**: Spawn and coordinate specialist agents via MCP tools
- **Subagent Mode**: Platform-specific spawning (see CH3 in your protocol)
```

Make `get_orchestrator_identity_content()` either:
- (a) Accept `tool` param and inject platform-specific execution mode description, OR
- (b) Keep it platform-neutral (simpler, preferred) — the protocol chapters handle the specifics

Recommend option (b) — identity should describe *what* the orchestrator does, not *how* it spawns. CH3 owns the "how."

### Phase 3: Multi-Terminal → "Any MCP-Connected Agent"

1. `protocol_builder.py` line 1027: rename `MULTI-TERMINAL MODE (CCW)` to `GENERIC MCP MODE`
2. Update the description to be tool-agnostic:
   ```
   ── GENERIC MCP MODE ────────────────────────────────────────────────────────
   Agent templates are served by the MCP server via get_orchestrator_instructions().
   Any MCP-connected coding agent can consume these templates.
   Each spawned agent gets a thin prompt (~10 lines).
   Agent calls get_agent_mission() to fetch full instructions.
   Coordination happens via MCP messaging tools (send_message, receive_messages).
   MESSAGING: Always use agent_id UUIDs in to_agents.
   Orchestrator has NO active role after STAGING_COMPLETE broadcast.
   ```
3. Frontend `ProjectTabs.vue`: Change radio label from "Multi-Terminal" to "Any Coding Agent"
4. `_build_execution_mode_fields()`: Update phase_assignment_instructions heading from "Multi-Terminal Mode" to "Generic Mode"

### Phase 4: Codex Implementation Prompt Guardrails

In `thin_prompt_generator.py` `_build_codex_execution_prompt()`, add to spawning_section after template:

```
### CRITICAL: Template-First Spawning
The agent='gil-{name}' parameter loads the INSTALLED agent template.
The template contains the agent's full behavioral instructions.

DO NOT:
- Spawn a generic/default worker and tell it to "act as" a GiljoAI agent
- Re-explain the agent's role in instructions= (the template already has this)
- Override template behavior with lengthy instruction text

DO:
- Use agent='gil-{agent_name}' to load the real template
- Keep instructions= minimal: job_id + mission fetch call only
- Trust the template's baked-in behavior
```

### Phase 5: Tests

- Unit tests for `_build_ch1_mission(tool="codex")` — verify no "Task()" reference
- Unit tests for `_build_ch3_spawning_rules(tool="codex")` — verify Codex-first, no `.claude/` path
- Unit tests for `_build_ch3_spawning_rules(tool="gemini")` — verify Gemini-native
- Unit test for generic mode — verify "Any MCP-Connected Agent" language
- Integration test: `get_orchestrator_instructions()` with `execution_mode="codex_cli"` returns no Claude references
- Frontend snapshot test for radio label change

## Testing Requirements

**Unit Tests:**
- Each CH builder with each tool value returns platform-appropriate content
- No cross-platform leakage (Codex output should not contain "Task()", Claude output should not contain "spawn_agent()")

**Manual Testing:**
- Stage a project with each execution mode, inspect the full protocol dump
- Verify Codex implementation prompt includes "DO NOT spawn generic workers" block
- Verify multi-terminal label reads "Any Coding Agent" in UI

## Success Criteria

1. Each platform's orchestrator protocol contains ONLY its own native spawning language
2. Codex protocol includes mechanical explanation of what `agent=` does
3. Codex protocol includes "DO NOT spawn generic workers" guardrail
4. Multi-terminal mode rebranded to "Any Coding Agent" / generic MCP
5. No database migration required
6. All existing tests pass + new platform-specific tests added
7. `orchestrator_identity` is platform-neutral (no Claude-specific execution mode references)

## Rollback Plan

All changes are in protocol builder (pure functions) and template seeder (string content). Revert the commit. No DB state affected.
