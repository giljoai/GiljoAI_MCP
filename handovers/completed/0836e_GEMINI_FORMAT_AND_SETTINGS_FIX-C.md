# Handover 0836e: Gemini CLI Agent Format & Settings Fix

**Date:** 2026-03-23
**From Agent:** Session coordinator (continuation agent)
**To Agent:** N/A (retroactive — work complete)
**Priority:** Critical
**Status:** Complete
**Edition Scope:** CE

---

## Task Summary

Fix Gemini CLI agent template format and installation flow so custom agents actually load and work. Three bugs were discovered during live testing on Gemini CLI v0.34.0.

---

## What Was Fixed

### Bug 1: Wrong `kind` field (`e580ebc5`)
- **Problem:** `render_gemini_agent()` used `kind: agent`. Gemini built-in agents use `kind: local`.
- **Fix:** Changed to `kind: local` in `template_renderer.py`.

### Bug 2: Wrong tool name (`e580ebc5`)
- **Problem:** `tools` list had `shell`. Gemini CLI requires `run_shell_command`.
- **Fix:** Changed to `run_shell_command`, added `glob`, `grep_search`, `list_directory`, `read_many_files` (matching built-in `codebase_investigator`).

### Bug 3: Custom agents silently not loading (`9ba820de`)
- **Problem:** `experimental.enableAgents` must be `true` in `.gemini/settings.json`. Defaults to true in v0.34.0 but not always present. Also, project-level agents require folder trust.
- **Fix:** `/gil_get_agents` Gemini command now merges `experimental.enableAgents: true` into settings.json and warns about folder trust for project-level installs.

### Alignment with proven format (`d1487cec`)
- **Problem:** Model defaulted to `gemini-2.5-pro`, MCP wildcard was `mcp_*`.
- **Fix:** Model changed to `inherit` (parent session model; `/gil_get_agents` rewrites at install time). MCP wildcard changed to `mcp_giljo-mcp_*` (server-specific, proven working).

---

## Key Findings from Live Testing

1. Gemini subagents are labeled "experimental" but ship enabled by default (`enableAgents` defaults to `true`)
2. Built-in agents (codebase_investigator, cli_help, generalist) bypass the experimental flag entirely
3. Custom agents CAN execute in parallel (contradicts earlier assumption)
4. Folder trust (`/permissions trust`) is required for project-level agents — untrusted folders silently ignore `.gemini/agents/`
5. GiljoAI protocols (STARTUP, health_check, get_agent_mission) confirmed working in spawned Gemini subagents

## Files Modified

| File | Change |
|------|--------|
| `src/giljo_mcp/template_renderer.py` | `kind: local`, `run_shell_command`, `mcp_giljo-mcp_*`, `model: inherit` |
| `src/giljo_mcp/tools/slash_command_templates.py` | Updated format reference, added settings.json enablement, folder trust, troubleshooting |
| `tests/unit/test_template_assembler_0836a.py` | Updated assertions for new format |
| `tests/integration/test_agent_template_assembler.py` | Updated `kind` assertion |

## Commits

- `e580ebc5` — kind:local, run_shell_command, expanded tools
- `9ba820de` — experimental.enableAgents + folder trust guidance
- `d1487cec` — model:inherit, mcp_giljo-mcp_* alignment with proven format

## Status

Complete. All 99 tests passing. Verified working in Gemini CLI v0.34.0.
