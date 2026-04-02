# Handover 0841: Slash Command Optimization (/gil_add, /gil_add, @gil_task)

**Date:** 2026-03-30 (updated)
**From Agent:** Orchestrator
**To Agent:** Next Session
**Priority:** Low
**Estimated Complexity:** 2-3 hours
**Status:** In Progress
**Edition Scope:** CE

---

## Task Summary

Slim down the `gil_add` / `gil_task` command templates across all three platforms (Claude, Gemini, Codex) and fix the agent closeout signoff to use platform-correct command syntax.

### Three Change Points

1. **Claude template bloat** — Rewrite `GIL_ADD_MD` from 343 lines (~3,500 tokens) to match the density of Gemini/Codex (~80 lines, ~800 tokens). Gemini and Codex templates are already slim and prove the format works.

2. **Gemini + Codex templates** — Already lean. Apply minor harmonization so all three share identical structure and wording where possible (only format/syntax wrappers differ).

3. **Agent closeout signoff** — `protocol_builder.py` line 429-434 hardcodes `/gil_add` regardless of platform. Must say `/gil_add` (Claude/Gemini) or `$gil-add` (Codex) based on execution mode.

## Source File

All templates live in one file: `src/giljo_mcp/tools/slash_command_templates.py`

| Platform | Constant | Current Lines | Target |
|----------|----------|---------------|--------|
| Claude | `GIL_ADD_MD` (lines 53-395) | 343 | ~80 |
| Gemini | `GIL_ADD_GEMINI_TOML` (lines 528-606) | 78 | ~78 (minor tweaks) |
| Codex | `GIL_ADD_CODEX_SKILL_MD` (lines 828-907) | 80 | ~80 (minor tweaks) |

## Closeout Signoff Fix

**File:** `src/giljo_mcp/services/protocol_builder.py` (lines 427-434)

**Current (hardcoded):**
```
"tell me and I'll use /gil_add to save it to your dashboard."
```

**Fix:** Accept `tool` param (derived from `execution_mode` via existing `execution_mode_to_tool` mapping), then:
- `claude-code` / `gemini` / default: `/gil_add`
- `codex`: `$gil-add`

Thread `tool` from `mission_service.py` line 680 using the same `execution_mode_to_tool` pattern already used for orchestrator protocols (line 978-983).

## Implementation Plan

1. Rewrite `GIL_ADD_MD` to slim format (~80 lines)
2. Review/harmonize `GIL_ADD_GEMINI_TOML` and `GIL_ADD_CODEX_SKILL_MD`
3. Add `tool` param to `_generate_agent_protocol()`, thread from `mission_service.py`
4. Make `gil_add_block` signoff platform-aware
5. Test all three exports via `/api/download/slash-commands.zip?platform=`

## Success Criteria

- [ ] Claude `GIL_ADD_MD` reduced from ~3,500 to ~800 tokens
- [ ] All three platform templates share identical structure/wording
- [ ] Agent closeout says `/gil_add` (Claude/Gemini) or `$gil-add` (Codex)
- [ ] `/api/download/slash-commands.zip` ships slim versions for all platforms
- [ ] No regression in MCP tool calls (create_task, create_project)
