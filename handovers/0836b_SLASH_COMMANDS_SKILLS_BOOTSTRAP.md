# Handover 0836b: Slash Commands, Skills, and Bootstrap Prompts

**Date:** 2026-03-22
**Parent:** 0836 (Multi-Platform Agent Template Export)
**Priority:** Critical
**Status:** Not Started
**Edition Scope:** CE
**Branch:** `feature/0836-multi-platform-export`
**Dependencies:** Uses API contract from 0836a (can work in parallel — contract is defined in parent doc)

## Pre-Read

Read `handovers/0836_MULTI_PLATFORM_AGENT_EXPORT.md` first — it contains the shared API contract, Codex config.toml safety protocol, and cross-platform requirements.

## Task Summary

Create the slash commands (Claude Code), custom commands (Gemini CLI), and skills (Codex CLI) that let users install and update agent templates from their CLI tool. Also create the platform-specific `/gil_add` equivalents and the combined bootstrap prompt templates.

## What to Build

### 1. Rename and Enhance Claude Code Slash Command

**File:** `src/giljo_mcp/tools/slash_command_templates.py`

**A. `GIL_GET_AGENTS_MD` (new, replaces `GIL_GET_CLAUDE_AGENTS_MD`)**

```yaml
---
name: gil_get_agents
description: Download and install GiljoAI agent templates from the MCP server
allowed-tools: mcp__giljo-mcp__*, Bash, Read, Write
---
```

Instructions for the LLM:
1. Call `mcp__giljo-mcp__get_agent_templates_for_export` with `platform="claude_code"`
2. Show summary table of all agents (role, name, description)
3. Ask model preference per agent: haiku (fast) / sonnet (balanced, default) / opus (maximum). User can set one for all or pick per-agent.
4. Ask: project agents (`.claude/agents/`) or user agents (`~/.claude/agents/`)?
5. If target directory has existing `.md` files, back up to `*.md.bak.YYYYMMDD_HHMMSS`
6. Write each agent file with the user's model selection applied to the `model` frontmatter field
7. Report what was installed, instruct user to restart Claude Code

Rules:
- Do NOT modify agent name, description, or body content
- Do NOT modify protocol sections
- ONLY user-configurable field is model selection
- Colors are pre-assigned — do not change them
- Use Bash tool for file operations (cross-platform via Git Bash)

**B. `GIL_GET_CLAUDE_AGENTS_MD` (deprecated alias)**

Keep the existing template but prepend a notice:
```
NOTE: This command has been renamed to /gil_get_agents.
Run the "Setup GiljoAI" prompt from the dashboard to update your slash commands.
Continuing with agent installation...
```
Then execute the same logic as `GIL_GET_AGENTS_MD`.

### 2. Create Gemini CLI Custom Command

**Add to `slash_command_templates.py`:**

**A. `GIL_GET_AGENTS_GEMINI_TOML`**

Gemini custom commands use TOML format:
```toml
description = "Download and install GiljoAI agent templates from the MCP server"

prompt = """
You are the GiljoAI agent template installer for Gemini CLI.

1. Call the GiljoAI MCP tool `get_agent_templates_for_export` with platform="gemini_cli"
2. Show summary table of all agents
3. Ask model preference (default: gemini-2.5-pro)
4. Ask: project agents (.gemini/agents/) or user agents (~/.gemini/agents/)?
5. Back up existing agent files before overwriting
6. Write each agent file
7. Note: parallel subagent execution is experimental — agents may run sequentially
8. Instruct user to restart Gemini CLI

Rules:
- Do NOT modify agent names, descriptions, or body content
- User-configurable: model, max_turns (default 50)
- Colors NOT supported in Gemini — omit them
- Use shell tool for file operations
"""
```

**B. `GIL_ADD_GEMINI_TOML`**

Same dual function as Claude Code's `/gil_add` (tasks + projects via MCP tools), but in TOML format:
```toml
description = "Add a task or project to the GiljoAI dashboard"

prompt = """
[Same logic as GIL_ADD_MD but referencing Gemini's MCP tool naming convention]
"""
```

Review the existing `GIL_ADD_MD` template carefully. The Gemini version must have identical behavior: direct task mode (`--task`/`--name`), direct project mode (`--project`), and interactive mode. The only differences are:
- MCP tool references use Gemini's naming convention (verify at implementation time)
- File format is TOML, not markdown with YAML frontmatter

### 3. Create Codex CLI Skills

**Add to `slash_command_templates.py`:**

**A. `GIL_GET_AGENTS_CODEX_SKILL_MD`**

Codex skills are markdown files in `~/.codex/skills/skill-name/SKILL.md`:

```yaml
---
name: gil-get-agents
description: "Download and install GiljoAI agent templates into Codex CLI"
---
```

Instructions (heavier than Claude/Gemini because of config.toml merge):
1. Call `get_agent_templates_for_export` with `platform="codex_cli"`
2. Show summary table of all agents
3. Ask model per agent (default: gpt-5.2-codex) and reasoning effort (low/medium/high, default: medium)
4. **config.toml safety protocol** (MANDATORY — see parent handover):
   - Check if `~/.codex/config.toml` exists
   - If YES: back up to `config.toml.bak.YYYYMMDD_HHMMSS`
   - Read current config, identify existing `[agents.*]` sections
   - Prepare merge: add/update only GiljoAI entries, preserve everything else
   - Show diff before writing — MUST get user confirmation
   - If does NOT exist: create with only GiljoAI entries
5. Write `.toml` agent files to `~/.codex/agents/` using the `toml_format_reference` from the API response
6. Instruct user to restart Codex CLI

Rules:
- Do NOT modify agent names, descriptions, or developer_instructions content
- ALWAYS show config.toml diff before writing
- ALWAYS back up existing config.toml before modifying
- If user declines the diff, abort without writing

**B. `GIL_ADD_CODEX_SKILL_MD`**

Same dual function as Claude Code's `/gil_add`, in Codex skill format:
```yaml
---
name: gil-add
description: "Add a task or project to the GiljoAI dashboard"
---
```

Same three modes (direct task, direct project, interactive). Only difference is MCP tool naming convention for Codex.

### 4. Bootstrap Prompt Templates

**Add to `slash_command_templates.py`:**

Three bootstrap prompt templates — one per platform. These are NOT slash commands. They are natural language instructions that the frontend copies to clipboard when the user clicks "Setup GiljoAI."

**A. `BOOTSTRAP_CLAUDE_CODE`**

```
Install the GiljoAI CLI integration. This is a one-time setup.

Step 1 — Install slash commands:
Download: {SLASH_COMMANDS_URL}
Extract to: ~/.claude/commands/ (create if needed, overwrite existing)
Delete the downloaded zip.

Step 2 — Install agent templates:
Download: {AGENT_TEMPLATES_URL}
Extract to: ~/.claude/agents/ (create if needed)
If existing agents are present, back them up to ~/.claude/agents/backup_YYYYMMDD_HHMMSS/ first.
Delete the downloaded zip.

Adapt all commands for the OS you are running on.
After both installs complete, instruct the user to restart Claude Code.
Note: Download links expire in 15 minutes.
```

**B. `BOOTSTRAP_GEMINI_CLI`**

Same pattern, different paths:
- Slash commands → `~/.gemini/commands/`
- Agent templates → `~/.gemini/agents/`
- Restart instruction: restart Gemini CLI

**C. `BOOTSTRAP_CODEX_CLI`**

Two-step because Codex needs interactive config.toml merge:
```
Install the GiljoAI CLI integration. This is a one-time setup.

Step 1 — Install skills:
Download: {SKILLS_URL}
Extract to: ~/.codex/skills/ (create if needed, overwrite existing)
Delete the downloaded zip.

Step 2 — Install agent templates:
Skills are now installed. Run the $gil-get-agents skill to install agent templates
with proper config.toml integration. This step is interactive — the skill will
guide you through model selection and config file merge.

Adapt all commands for the OS you are running on.
After skill installation, instruct the user to restart Codex CLI, then run $gil-get-agents.
Note: Download link expires in 15 minutes.
```

### 5. Update get_all_templates()

The existing `get_all_templates()` function returns a dict of filename → content. Extend it to accept a `platform` parameter:

- `platform="claude_code"` (default): returns `gil_get_agents.md`, `gil_get_claude_agents.md` (deprecated alias), `gil_add.md`
- `platform="gemini_cli"`: returns `gil_get_agents.toml`, `gil_add.toml`
- `platform="codex_cli"`: returns `gil-get-agents/SKILL.md`, `gil-add/SKILL.md`

The ZIP generation in `downloads.py` already calls `get_all_templates()` — it needs to forward the platform parameter.

## Testing Requirements

- Verify each slash command template has correct frontmatter format for its platform
- Verify `/gil_add` Gemini and Codex versions have identical behavior to Claude Code version (all three modes)
- Verify deprecated `/gil_get_claude_agents` alias includes migration notice
- Verify bootstrap prompt templates have correct placeholder variables
- Verify `get_all_templates(platform=...)` returns correct files per platform

## Key Files

| File | Action |
|------|--------|
| `src/giljo_mcp/tools/slash_command_templates.py` | Major update — all new templates |
| `api/endpoints/downloads.py` | Forward platform param to `get_all_templates()` |

## Success Criteria

- 3 versions of `/gil_get_agents` exist (Claude `.md`, Gemini `.toml`, Codex `SKILL.md`)
- 3 versions of `/gil_add` exist (Claude `.md`, Gemini `.toml`, Codex `SKILL.md`)
- 3 bootstrap prompt templates exist with correct paths per platform
- Deprecated alias works with migration notice
- `get_all_templates()` returns platform-appropriate files
- All templates use Bash/shell for file operations (cross-platform)
- Codex skill hard-prompts the config.toml backup+diff+confirm sequence

## Implementation Summary (2026-03-22)

**Status:** Complete

### What Was Built
- **10 template constants** in `slash_command_templates.py`:
  - `GIL_GET_AGENTS_MD` — new Claude Code slash command with MCP tool + model selection
  - `GIL_GET_CLAUDE_AGENTS_MD` — deprecated alias with migration notice
  - `GIL_ADD_MD` — preserved (unchanged behavior)
  - `GIL_GET_AGENTS_GEMINI_TOML` + `GIL_ADD_GEMINI_TOML` — TOML-format Gemini custom commands
  - `GIL_GET_AGENTS_CODEX_SKILL_MD` + `GIL_ADD_CODEX_SKILL_MD` — Codex CLI skills with config.toml safety protocol
  - `BOOTSTRAP_CLAUDE_CODE`, `BOOTSTRAP_GEMINI_CLI`, `BOOTSTRAP_CODEX_CLI` — one-time onboarding prompts
- **`get_all_templates(platform=...)`** — updated to accept platform parameter, returns correct filenames per platform, raises `ValueError` on invalid platform
- **`downloads.py`** — `/slash-commands.zip` endpoint now accepts `?platform=` query parameter

### Key Files Modified
- `src/giljo_mcp/tools/slash_command_templates.py` (complete rewrite)
- `api/endpoints/downloads.py` (platform query param on slash-commands.zip endpoint)
- `tests/test_slash_command_templates.py` (new — 13 tests, all passing)

### All Success Criteria Met
- All 13 tests passing, zero lint issues
