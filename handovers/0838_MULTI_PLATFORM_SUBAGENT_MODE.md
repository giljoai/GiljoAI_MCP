# Handover 0838: Multi-Platform Subagent Mode (Codex + Gemini)

**Date:** 2026-03-25
**From Agent:** Research/planning session
**To Agent:** Implementation agent
**Priority:** High
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Extend the job staging page to support Codex CLI and Gemini CLI as subagent execution platforms alongside the existing Claude Code CLI mode. The staging UI radio buttons expand from 2 options to 4. The prompt injection pipeline gains platform-aware spawning syntax at two layers: orchestrator protocol (CH3) and implementation prompt.

---

## Context and Background

### Current State

The staging page (`ProjectTabs.vue` lines 48-62) offers two radio buttons:
- **Multi-Terminal** — each agent runs in a separate terminal, user copies prompts manually
- **Claude Code CLI** — single terminal, orchestrator spawns subagents via Claude's `Task()` tool

The prompt pipeline has two mode-divergence points:
1. **CH3 spawning rules** (`protocol_builder.py` lines 938-1019) — tells orchestrator how to spawn agents
2. **Implementation prompt** (`thin_prompt_generator.py` lines 1296-1600) — provides per-agent `Task()` templates

Both are hardcoded to Claude Code's `Task(subagent_type=..., instructions=...)` syntax.

### What Needs to Change

Codex CLI and Gemini CLI have different subagent invocation patterns:
- **Codex CLI:** Uses `spawn_agent` with `gil-` prefixed agent names (built-in roles shadow unprefixed names)
- **Gemini CLI:** Uses subagents by name (no prefix needed, similar to Claude Code)

The backend already validates `tool` as `^(claude-code|codex|gemini)$` (prompts.py line 324) and `AgentExecution.tool_type` stores the platform — but neither is wired into prompt generation.

---

## Technical Details

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/projects/ProjectTabs.vue` | Replace 2 radio buttons with 4-option layout. Change hardcoded `tool: 'claude-code'` (line 615) to dynamic value based on selection. |
| `src/giljo_mcp/services/protocol_builder.py` | `_build_ch3_spawning_rules()` (lines 938-1019): Add Codex and Gemini CLI mode blocks with platform-specific spawning syntax. |
| `src/giljo_mcp/thin_prompt_generator.py` | Add `_build_codex_execution_prompt()` and `_build_gemini_execution_prompt()` parallel to `_build_claude_code_execution_prompt()` (lines 1296-1600). Update `generate_implementation_prompt()` (lines 1239-1263) to route by platform. |
| `api/endpoints/prompts.py` | `get_implementation_prompt()` (lines 456-627): Route `prompt_type` based on `tool` column, not just `execution_mode`. |
| `src/giljo_mcp/services/orchestration_service.py` | `_build_execution_mode_fields()` (lines 2798-2853): Expand `cli_mode_rules` to include platform-specific agent naming and spawning syntax. |

### Files to Read (no changes expected)

| File | Why |
|------|-----|
| `src/giljo_mcp/services/orchestration_service.py` lines 928-1275 | `get_agent_mission()` — verify agent lifecycle protocol is platform-agnostic (it should be). |
| `src/giljo_mcp/services/orchestration_service.py` lines 367-576 | `spawn_agent_job()` — verify thin agent prompt is platform-agnostic. |
| `api/endpoints/mcp_http.py` | MCP tool definitions — verify no platform-specific assumptions. |

---

## Implementation Plan

### Phase 1: Frontend Radio Buttons

Update `ProjectTabs.vue` radio button group from:
```
Multi-Terminal | Claude Code CLI
```
To:
```
Multi-Terminal | Subagent: Claude | Subagent: Codex | Subagent: Gemini
```

Design constraints:
- Short labels, no long descriptions
- All subagent options should visually group together
- The `executionMode` value should store: `multi_terminal`, `claude_code_cli`, `codex_cli`, `gemini_cli`
- The `tool` parameter sent to staging endpoint maps: `claude_code_cli` → `claude-code`, `codex_cli` → `codex`, `gemini_cli` → `gemini`

### Phase 2: Protocol Builder CH3

`_build_ch3_spawning_rules()` currently returns Claude-specific `Task()` syntax when `cli_mode=True`. Refactor to accept a `tool` parameter and return platform-specific blocks:

**Claude Code:**
```
Task(subagent_type='{agent_name}', instructions='...')
CRITICAL: Task() uses agent_name, NOT agent_display_name
```

**Codex CLI:**
```
spawn_agent(agent='gil-{agent_name}', instructions='...')
CRITICAL: ALL GiljoAI agents use the gil- prefix.
The server returns agent_name without prefix. You MUST prepend 'gil-' when spawning.
Built-in Codex roles shadow unprefixed names — verified on Codex CLI v0.116.0.
```

**Gemini CLI:**
```
Use subagents by name: @{agent_name}
Spawn with: /agent {agent_name} followed by instructions
```

Note: Exact Gemini/Codex subagent syntax should be verified against current CLI versions during implementation. The above is directional.

### Phase 3: Implementation Prompt Builders

Create parallel functions in `thin_prompt_generator.py`:
- `_build_codex_execution_prompt()` — mirrors Claude's structure but uses `spawn_agent` with `gil-` prefix and Codex-specific syntax
- `_build_gemini_execution_prompt()` — mirrors Claude's structure but uses Gemini's subagent invocation pattern

Update `generate_implementation_prompt()` routing:
```python
if project.execution_mode == "multi_terminal":
    prompt_type = "multi_terminal_orchestrator"
elif tool == "codex":
    prompt_type = "codex_execution"
elif tool == "gemini":
    prompt_type = "gemini_execution"
else:
    prompt_type = "claude_code_execution"
```

### Phase 4: GOI Mode Fields

Expand `_build_execution_mode_fields()` in `orchestration_service.py`:
- Currently returns `cli_mode_rules` with Claude-specific `agent_name_usage` and `task_tool_mapping`
- Add platform-specific variants for Codex (with `gil-` prefix rules) and Gemini

### Phase 5: Validation & Testing

- Verify `get_agent_mission()` and `spawn_agent_job()` are platform-agnostic (no changes expected)
- Test each platform's staging → GOI → implementation → agent mission flow end-to-end
- Verify the `tool` value propagates correctly from frontend through to prompt generation

---

## Platform-Specific Spawning Reference

| Platform | Subagent Invocation | Agent Name Format | Key Constraint |
|----------|-------------------|-------------------|----------------|
| Claude Code | `Task(subagent_type='{name}', instructions='...')` | `{agent_name}` as-is | Uses `agent_name` not `agent_display_name` |
| Codex CLI | `spawn_agent(agent='gil-{name}', instructions='...')` | `gil-{agent_name}` (prefixed) | Built-in roles shadow unprefixed names |
| Gemini CLI | Subagent by name, similar to Claude | `{agent_name}` as-is | Verify exact syntax at implementation time |

---

## Database Impact

The `Project.execution_mode` column currently stores `multi_terminal` or `claude_code_cli`. New values needed:
- `codex_cli`
- `gemini_cli`

Check if this column has a CHECK constraint or enum validation. If so, add migration. If it's a plain VARCHAR, no migration needed — just update backend validation.

The `AgentExecution.tool_type` column already stores `claude-code`, `codex`, or `gemini` — no change needed.

---

## Testing Requirements

**Unit Tests:**
- CH3 spawning rules return correct syntax for each of 3 platforms
- Implementation prompt builder routes to correct platform builder
- Codex prompt includes `gil-` prefix instructions
- Gemini prompt uses correct subagent syntax

**Integration Tests:**
- Staging endpoint accepts `tool=codex` and `tool=gemini`
- GOI returns platform-specific `cli_mode_rules` per tool
- Implementation prompt contains platform-appropriate spawning templates

**Manual Tests:**
- Stage a project with Codex subagent mode → paste into Codex CLI → orchestrator spawns `gil-` prefixed agents
- Stage a project with Gemini subagent mode → paste into Gemini CLI → orchestrator spawns agents
- Verify Multi-Terminal and Claude Code CLI modes are unaffected

---

## Success Criteria

- [ ] Frontend shows 4 execution mode options (Multi-Terminal, Subagent: Claude, Subagent: Codex, Subagent: Gemini)
- [ ] `tool` parameter flows from frontend through staging to prompt generation
- [ ] CH3 spawning rules are platform-specific
- [ ] Implementation prompts are platform-specific
- [ ] Codex prompts enforce `gil-` prefix on all agent names
- [ ] Gemini prompts use correct subagent invocation
- [ ] Existing Multi-Terminal and Claude Code CLI modes are unaffected
- [ ] All tests pass

---

## Key File Reference

| Component | File | Lines |
|-----------|------|-------|
| Frontend radio buttons | `frontend/src/components/projects/ProjectTabs.vue` | 48-62, 568-594, 600-648 |
| Staging endpoint | `api/endpoints/prompts.py` | 321-453 |
| Implementation endpoint | `api/endpoints/prompts.py` | 456-627 |
| Staging prompt builder | `src/giljo_mcp/thin_prompt_generator.py` | 1157-1237 |
| Implementation prompt builder | `src/giljo_mcp/thin_prompt_generator.py` | 1239-1600 |
| CH3 spawning rules | `src/giljo_mcp/services/protocol_builder.py` | 938-1019 |
| GOI mode fields | `src/giljo_mcp/services/orchestration_service.py` | 2798-2853 |
| GOI full function | `src/giljo_mcp/services/orchestration_service.py` | 2855-3128 |
| Agent mission delivery | `src/giljo_mcp/services/orchestration_service.py` | 928-1275 |
| Agent spawning | `src/giljo_mcp/services/orchestration_service.py` | 367-576 |
