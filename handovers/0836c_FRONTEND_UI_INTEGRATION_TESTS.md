# Handover 0836c: Frontend UI Changes + Integration Tests

**Date:** 2026-03-22
**Parent:** 0836 (Multi-Platform Agent Template Export)
**Priority:** Critical
**Status:** Not Started
**Edition Scope:** CE
**Branch:** `feature/0836-multi-platform-export`
**Dependencies:** 0836a MCP endpoint must exist (or be mockable)

## Pre-Read

Read `handovers/0836_MULTI_PLATFORM_AGENT_EXPORT.md` first — it contains the shared API contract, design doc corrections, and cross-platform requirements.

## Task Summary

Two responsibilities:
1. Update the dashboard UI — remove the CLI tool selector from template creation, ungate fields, redesign the Integrations page for multi-platform export
2. Write integration tests covering the full export pipeline for all 3 platforms

## What to Build

### 1. TemplateManager.vue — Remove Tool Selector, Ungate Fields

**File:** `frontend/src/components/TemplateManager.vue`

**Remove:**
- The CLI tool selector radio group (lines 268-283): `cliToolOptions` array with Claude/Codex/Gemini/Generic
- The `v-model` binding to `cli_tool` on the radio group
- The "Generic" option entirely (multi-terminal mode uses `get_generic_agent_template` at runtime, not exported files)

**Ungate:**
- `showDescription` computed (lines 664-666): currently `return cli_tool === 'claude'`. Change to always return `true`. All platforms need descriptions.
- `modelOptions` computed (lines 668-673): Remove from template creation entirely. Model is an export-time choice (asked by `/gil_get_agents`), not a creation-time choice. Remove the model dropdown from the create/edit dialog.

**Add (collapsed, optional):**
- A "Platform Export Preferences" expansion panel at the bottom of the create/edit dialog
- Contains 3 sub-sections (Claude Code, Codex CLI, Gemini CLI) each with optional model preference
- All fields optional. If unset, the slash command/skill asks at install time
- This section is collapsed by default — most users skip it
- Store in the template's `meta_data` JSON field as `platform_overrides` key

**Keep:**
- The `cli_tool` field in the form data — just stop displaying the selector. Default to `null` or omit when saving. The assembler ignores this field.
- Role selector, custom suffix, description, Role and Expertise editor — all unchanged

### 2. ClaudeCodeExport.vue → AgentExport.vue — Multi-Platform Integrations

**Rename:** `frontend/src/components/ClaudeCodeExport.vue` → `frontend/src/components/AgentExport.vue`

Update the import in `frontend/src/views/UserSettings.vue` to match.

**Current state (3 Claude-only buttons):**
1. Manual Agent installation (direct ZIP download)
2. MCP Installation for Personal Agents (copy prompt)
3. MCP Installation for Product Agents (copy prompt)

**New design (per-platform sections):**

```
┌─────────────────────────────────────────────────┐
│ 1. MCP Connection                               │
│    [Claude Code]  [Codex CLI]  [Gemini CLI]     │
│    (tab or button group — each shows its config)│
│                                                  │
│ 2. One-Time Setup                               │
│    [Setup GiljoAI for Claude Code]              │
│    [Setup GiljoAI for Codex CLI]                │
│    [Setup GiljoAI for Gemini CLI]               │
│    (each generates combined bootstrap prompt)    │
│                                                  │
│ 3. Manual Downloads (collapsed)                 │
│    Agent Templates: [Claude] [Gemini] [Codex]   │
│    Slash Commands: [Claude] [Gemini] [Codex]    │
│                                                  │
│ 4. After Setup (info text)                      │
│    "Use /gil_get_agents to update templates"    │
│    "Use /gil_add to create tasks and projects"  │
└─────────────────────────────────────────────────┘
```

**Section 1 — MCP Connection:**
- Reuse existing `AiToolConfigWizard.vue` component (it already handles all 3 platforms)
- No changes needed here — just ensure it's prominently placed

**Section 2 — One-Time Setup (the key new feature):**
- Three buttons, one per platform
- When clicked:
  1. Call `POST /api/download/generate-token` with `content_type="slash_commands"` and the platform
  2. Call `POST /api/download/generate-token` with `content_type="agent_templates"` and the platform
  3. For Codex: only generate the skills token (agents are installed via the skill)
  4. Assemble the bootstrap prompt from the template (substitute `{SLASH_COMMANDS_URL}` and `{AGENT_TEMPLATES_URL}`)
  5. Copy to clipboard, show "Copied!" feedback

**Section 3 — Manual Downloads:**
- Collapsed by default (v-expansion-panel)
- Per-platform direct ZIP download links
- Uses `GET /api/download/agent-templates.zip?platform=claude_code` etc.

**Section 4 — After Setup:**
- Static info text, no interactivity
- Reminds users that `/gil_get_agents` and `/gil_add` are now installed

### 3. Backend Support for Bootstrap Prompt

**File:** `api/endpoints/downloads.py`

The `generate-token` endpoint needs to accept a `platform` parameter so it can stage platform-appropriate files:
- `slash_commands` + `claude_code` → stages Claude `.md` command files
- `slash_commands` + `gemini_cli` → stages Gemini `.toml` command files
- `slash_commands` + `codex_cli` → stages Codex `SKILL.md` skill directories
- `agent_templates` + any platform → stages pre-assembled templates for that platform

This may already be partially handled by 0836a's ZIP generation changes. Coordinate.

### 4. Integration Tests

**New test files in `tests/integration/`:**

**A. `test_agent_template_assembler.py`**
- Test Claude formatter output matches `render_claude_agent()` output exactly
- Test Gemini formatter produces valid YAML frontmatter with `kind: agent`, `tools` as YAML list, no `color`
- Test Codex formatter returns structured dict with all required fields
- Test assembler rejects invalid platform string
- Test 8-template cap is respected
- Test empty template list returns valid response
- Test `background_color` maps to `color` in Claude output, omitted in Gemini/Codex

**B. `test_multi_platform_export.py`**
- Test `get_agent_templates_for_export` MCP tool for each platform
- Test platform-aware ZIP download contains correctly formatted files
- Test backward compatibility: `GET /api/download/agent-templates.zip` (no platform param) returns Claude format
- Test `generate-token` with platform param stages correct files
- Test `/gil_get_claude_agents` deprecated alias template includes migration notice

**C. `test_slash_command_templates.py`**
- Test `get_all_templates(platform="claude_code")` returns `.md` files
- Test `get_all_templates(platform="gemini_cli")` returns `.toml` files
- Test `get_all_templates(platform="codex_cli")` returns `SKILL.md` files
- Test default (no platform) returns Claude format for backward compatibility
- Test all `/gil_add` variants have the same three modes (task, project, interactive)

## Key Files

| File | Action |
|------|--------|
| `frontend/src/components/TemplateManager.vue` | Remove tool selector, ungate fields, add Platform Export Preferences |
| `frontend/src/components/ClaudeCodeExport.vue` | Rename to `AgentExport.vue`, redesign for multi-platform |
| `frontend/src/views/UserSettings.vue` | Update import, integrations tab layout |
| `api/endpoints/downloads.py` | Platform param on generate-token |
| `tests/integration/test_agent_template_assembler.py` | NEW |
| `tests/integration/test_multi_platform_export.py` | NEW |
| `tests/integration/test_slash_command_templates.py` | NEW |

## Success Criteria

- Template creation UI has no tool selector — description always visible, no model dropdown
- Platform Export Preferences section exists (collapsed, optional)
- Integrations page shows per-platform Setup buttons
- Bootstrap prompt copies to clipboard with valid URLs per platform
- Manual download works per platform
- All integration tests pass
- Existing Claude Code users see no regression
- `ruff check` and `npm run lint` pass clean
- Frontend builds without errors
