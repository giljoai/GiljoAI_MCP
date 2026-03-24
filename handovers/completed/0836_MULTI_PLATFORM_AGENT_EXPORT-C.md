# Handover 0836: Multi-Platform Agent Template Export (Parent)

**Date:** 2026-03-22
**Priority:** Critical (CE launch blocker)
**Status:** Not Started
**Edition Scope:** CE
**Branch:** `feature/0836-multi-platform-export` (off master)

## Overview

Evolve the agent template export system from Claude Code-only to multi-platform (Claude Code, Codex CLI, Gemini CLI). One template in the database, server-side assembly into the correct format per CLI tool at export time. Consolidate the dashboard Integrations page into a clean per-platform flow with a single bootstrap prompt per tool.

## Sub-Handovers

| ID | Title | Scope | Can Parallel? |
|----|-------|-------|---------------|
| **0836a** | Backend Assembler + MCP Endpoint | Server-side formatters, MCP tool, ZIP generation | Yes — no dependencies |
| **0836b** | Slash Commands, Skills, Bootstrap Prompts | CLI-side installation instructions for all 3 platforms | Yes — uses API contract from 0836a |
| **0836c** | Frontend UI + Integration Tests | Dashboard changes, test suite | After 0836a endpoint exists |

## Shared Context (Read Before Any Sub-Handover)

### Design Doc Corrections (Validated Against Code)

1. **Protocol injection at export time — WRONG in design docs.** The docs describe injecting a fat protocol block during export. Reality: templates have a slim bootstrap in `system_instructions` (injected at creation, read-only). Full protocol is delivered dynamically via `get_agent_mission()` at runtime. **Keep the current approach. Do NOT change protocol delivery.**
2. **`render_generic_agent()` exists** in `template_renderer.py` — extend, don't replace.
3. **`claude_export.py` endpoint exists** (`POST /export/claude-code`) — not mentioned in design docs. Assess usage; deprecate if redundant with assembler path.
4. **`select_templates_for_packaging()` already enforces 8-role limit** — no new enforcement needed.
5. **`color` field already exists** as `background_color` on the template model — no schema change needed.
6. **Color support:** Claude Code only. Codex uses status colors (cyan/green/red), Gemini has no agent color support. Assembler includes `color` for Claude, omits for others.

### API Contract (Shared Between 0836a and 0836b)

**MCP Tool:** `get_agent_templates_for_export`

Parameters:
- `tenant_key` (required) — standard tenant isolation
- `platform` (required) — `claude_code` | `codex_cli` | `gemini_cli`

**Response for `claude_code` / `gemini_cli` (pre-assembled):**
```json
{
  "platform": "claude_code",
  "agents": [
    {
      "filename": "implementer-frontend.md",
      "content": "---\nname: implementer-frontend\n...",
      "role": "implementer",
      "color": "#3B82F6"
    }
  ],
  "install_paths": {
    "project": ".claude/agents/",
    "user": "~/.claude/agents/"
  },
  "template_count": 6,
  "format_version": "1.0"
}
```

**Response for `codex_cli` (structured data):**
```json
{
  "platform": "codex_cli",
  "agents": [
    {
      "agent_name": "implementer-frontend",
      "description": "Implements frontend features...",
      "role": "implementer",
      "developer_instructions": "[system_instructions + user_instructions + rules]",
      "suggested_model": "gpt-5.2-codex",
      "suggested_reasoning_effort": "medium"
    }
  ],
  "install_paths": {
    "agent_files": "~/.codex/agents/",
    "config_file": "~/.codex/config.toml"
  },
  "toml_format_reference": "...",
  "template_count": 6,
  "format_version": "1.0"
}
```

### Cross-Platform Requirements

- All file paths use universal `~/` notation (works on Windows Git Bash, Linux, macOS)
- Slash command/skill instructions use the Bash tool (Git Bash on Windows, native elsewhere)
- ZIP extraction via `unzip` (available on all platforms)
- No OS-specific commands in MCP tools — platform specificity lives in slash commands/skills only

### Codex config.toml Safety Protocol

Hard-prompted in the Codex skill — not optional:
1. Check if `~/.codex/config.toml` exists
2. If YES: back up to `~/.codex/config.toml.bak.YYYYMMDD_HHMMSS`
3. Read current config to identify existing `[agents.*]` sections
4. Prepare merge: add/update only GiljoAI agent entries, preserve everything else
5. Show unified diff to user before writing
6. Only write after explicit user confirmation
7. If config.toml does NOT exist: create it with only the GiljoAI agent entries

### Key Existing Files

| File | What It Does | Audit Notes |
|------|-------------|-------------|
| `src/giljo_mcp/models/templates.py` | `AgentTemplate` DB model | Has `tool`, `cli_tool`, `background_color`, `model`, `description` fields |
| `src/giljo_mcp/template_renderer.py` | `render_claude_agent()`, `render_generic_agent()` | Claude renderer works; generic is plaintext only |
| `src/giljo_mcp/tools/tool_accessor.py` | MCP tool registration | Has `generate_download_token` tool |
| `src/giljo_mcp/tools/slash_command_templates.py` | `GIL_GET_CLAUDE_AGENTS_MD`, `GIL_ADD_MD` | Claude-only slash commands |
| `api/endpoints/downloads.py` | ZIP generation, token flow, install scripts | 668 lines, Claude-only assembly |
| `api/endpoints/claude_export.py` | Direct file write export | May be redundant with assembler |
| `frontend/src/components/TemplateManager.vue` | Template CRUD UI | Tool selector gates `description` and `model` |
| `frontend/src/components/ClaudeCodeExport.vue` | Integrations export buttons | 3 buttons: Manual, Personal, Product |
| `src/giljo_mcp/template_seeder.py` | Seeds 6 default templates | `_get_mcp_bootstrap_section()` injects slim bootstrap |

### Installation Impact

- No schema migration required
- `cli_tool` field stays in DB but assembler ignores it (formats by export target)
- New slash command templates served from backend — no install.py changes
- Bootstrap prompt generation is frontend logic — no backend config changes

### Rollback Plan

All changes are additive. Existing Claude Code export flow is preserved in the assembler. If multi-platform breaks, users fall back to current Claude-only flow. Feature branch isolates risk.

## References

- `MULTI_PLATFORM_AGENT_TEMPLATE_DESIGN.md` — design proposal (corrections noted above)
- `AGENT_EXPORT_EVOLUTION.md` — `/gil_get_agents` command spec
- `compass_artifact_wf-c84f1a96...` — CLI color support comparison
- Handover 0813 — Agent Template Context Separation
- Handover 0825 — Agent Identity Separation from Mission Response
- Handover 0102 — Agent Template Export System (token-based download)
