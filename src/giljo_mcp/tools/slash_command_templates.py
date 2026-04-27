# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Slash command templates for Claude Code, Codex CLI, and Gemini CLI (Handover 0836b)

This module provides platform-specific command templates:
- Claude Code: Markdown with YAML frontmatter (.md) for ~/.claude/commands/
- Gemini CLI: TOML format (.toml) for ~/.gemini/commands/
- Codex CLI: Markdown skills (.md) for ~/.codex/skills/<name>/SKILL.md

Also provides bootstrap prompt templates for one-time CLI onboarding.
"""

# Semver for the skills/commands package. Bumped when slash command templates change.
# Referenced by health_check so the frontend can compare installed vs available.
SKILLS_VERSION = "1.1.9"

# =============================================================================
# CLAUDE CODE TEMPLATES
# =============================================================================

GIL_GET_AGENTS_MD = """---
name: gil_get_agents
description: Download and install GiljoAI agent templates from the MCP server
allowed-tools: Bash, AskUserQuestion
---

You are the GiljoAI agent template installer for Claude Code. Be fast and efficient.

## Procedure

1. Ask user via AskUserQuestion (2 questions in one call):
   - "Which model should agents use?"
     Options: ["opus (recommended)", "sonnet (balanced)", "haiku (fast)", "Let me pick per agent"]
   - "Install scope?"
     Options: ["Project (.claude/agents/)", "User (~/.claude/agents/)"]
2. If "Let me pick per agent": download ZIP first (steps 3-4) to inspect filenames, then ask
   per-agent model via batched AskUserQuestion calls (up to 4 questions per call, one per agent).
3. Call `mcp__giljo_mcp__generate_download_token(content_type="agent_templates", platform="claude_code")`.
   This returns `{"download_url": "...", "expires_at": "...", "one_time_use": true}`.
   The URL is pre-signed and tied to your authenticated MCP session — no API key needed.
4. Download, extract, patch model, and clean up in a SINGLE Bash call:
   ```bash
   TARGET_DIR="<project_or_user_agents_dir>"
   MODEL="<chosen_model>"
   DOWNLOAD_URL="<download_url from step 3>"
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)

   # Backup existing .md files
   for f in "$TARGET_DIR"/*.md; do
     [ -f "$f" ] && mv "$f" "${f}.bak.${TIMESTAMP}"
   done

   # Download (URL is pre-signed, no auth header needed)
   curl -k -s --fail --show-error "$DOWNLOAD_URL" -o /tmp/giljo_agents.zip
   mkdir -p "$TARGET_DIR"
   unzip -o /tmp/giljo_agents.zip -d "$TARGET_DIR"

   # Patch model frontmatter
   sed -i "s/^model: .*/model: $MODEL/" "$TARGET_DIR"/*.md

   # Remove bundled install scripts (not needed in agents dir)
   rm -f "$TARGET_DIR/install.sh" "$TARGET_DIR/install.ps1"

   # Cleanup
   rm -f /tmp/giljo_agents.zip
   ```
   If user chose "per agent" models, run one sed per agent file instead of the glob sed.
5. Report a table of installed agents and remind user to restart Claude Code.

## Critical Rules

- Always call `generate_download_token` first — it returns a pre-signed URL scoped to your
  tenant. Do NOT hit `/api/download/agent-templates.zip` directly with `X-API-Key` headers;
  that path queries system defaults when unauthenticated and returns 404 for tenant users.
- The download URL expires in 15 minutes and is one-time-use. If the curl fails with an
  expired/used token, generate a fresh token and retry.
- Use Bash for ALL file operations -- one Bash call for step 4 (backup + download + extract + patch + cleanup)
- AskUserQuestion for all user choices -- never open-ended questions
- Do NOT call `list_agent_templates` MCP tool -- use `generate_download_token` + ZIP download instead
- Do NOT modify agent name, description, body content, or protocol sections
- The ONLY user-configurable field is the `model` frontmatter value
- Colors are pre-assigned by the server -- do not change them
- Unix paths work on ALL platforms (Git Bash on Windows)
- Target: complete the entire install in under 60 seconds and under 5 tool calls total
"""


GIL_ADD_MD = """---
description: "Add a task or project to the GiljoAI dashboard. Routes to task (technical debt/TODOs) or project (actionable work items) based on context."
---

# /gil_add — Add task or project to GiljoAI dashboard

## Routing
- **Task**: technical debt, TODOs, bugs, small fixes, scope creep punts -> `mcp__giljo_mcp__create_task`
- **Project**: actionable work items, features, multi-step dev work -> `mcp__giljo_mcp__create_project`
- **Update project**: if the user wants to update/modify/change an existing project, first call `mcp__giljo_mcp__list_projects` to find it, then call `mcp__giljo_mcp__update_project` with the new values

## Task parameters
- `title` (required), `description` (optional), `priority` (low|medium|high|critical, default: medium), `category` (frontend|backend|database|infra|docs|general, default: general)

## Project parameters
- `name` (required), `description` (optional — generate from context if missing), `project_type` (optional — must match a pre-configured type), `series_number` (optional int 1-9999 — auto-assigned if omitted), `suffix` (optional single letter a-z for sub-series)
- **Before creating a project**, call `list_projects()` which returns available `project_types` in the response. Only use types returned — unknown types are rejected with a list of valid types.
- **Suffix parsing**: If user says "FE-5004b", use `series_number=5004, suffix='b'`. If user says "FE-5004", use `series_number=5004` with no suffix.

## Modes

### Direct flags in `$ARGUMENTS`
- `--task "Name"` or `--name "Name"` (+ optional `--priority`, `--category`, `--description`) -> create task immediately
- `--project "Name"` (+ optional `--description`, `--type`, `--series`, `--suffix`) -> create project immediately
- `--help` -> show usage summary and stop

### Interactive (no flags or bare text)
1. Analyze conversation context to suggest task vs project with generated title/description
2. Ask user to confirm or adjust type, title, description
3. For tasks: ask category and priority
4. For projects: ask optional type label
5. Call appropriate MCP tool and confirm

### Read mode (read project / fetch context)
**Triggers** — route here when the user says any of these, or pastes one or more UUIDs with little surrounding text:
- "read project", "read projects"
- "show project", "show projects"
- "look up project", "look up projects"
- "fetch context for ..."
- A bare list of project UUIDs

**GOTCHA — read this BEFORE filtering:** the project identifier field is **`project_id`**, NOT `id`. Filtering on `.id` returns nothing because that key does not exist on project objects. Past Claude sessions burned 10+ minutes on this exact mistake. Always use `.project_id` in jq filters.

**Tool sequence:**
1. Call `mcp__giljo_mcp__list_projects(summary_only=false, depth=2)` — returns all projects with full fields. If the response is large the harness auto-saves it to a tool-result file on disk.
2. Filter the saved tool-result file with `jq`, keyed on `project_id` (NOT `id`):
   ```bash
   jq '.projects[] | select(.project_id == "UUID-HERE") | {project_id, name, taxonomy_alias, status, description, mission}' /path/to/saved-tool-result.json
   ```
3. For deep single-project context (memory, tasks, agents), call `mcp__giljo_mcp__fetch_context(product_id=..., project_id=..., categories=["project"])` instead of jq-filtering.

**Response shape** — each project object exposes: `project_id`, `name`, `taxonomy_alias` (e.g. "IMP-0015"), `status`, `project_type`, `series_number`, `description`, `mission`, `agent_summary`, `created_at`, `completed_at`.

**Worked example:**
> User pastes 5 UUIDs. Skill runs `mcp__giljo_mcp__list_projects(summary_only=false, depth=2)`, then jq-filters the saved tool-result file with `select(.project_id == "<uuid>")` for each UUID, and returns a compact summary table — one row per project: `taxonomy_alias`, `name`, `status`, one-line description.

## Rules
- Never pass `tenant_key` (auto-injected by security layer)
- Active product required (server-side enforced) — if error mentions "No active product", tell user to activate one in dashboard
- Projects are created as inactive — user activates via dashboard
- On success: show type, title/name, ID, and tell the user it should now be visible in their GiljoAI dashboard (do NOT fabricate a URL — the dashboard updates live via WebSocket)
- On error: show what went wrong and how to fix
"""

# =============================================================================
# GEMINI CLI TEMPLATES
# =============================================================================

GIL_GET_AGENTS_GEMINI_TOML = """description = "Download and install GiljoAI agent templates from the MCP server"

prompt = '''
You are the GiljoAI agent template installer for Gemini CLI.

## Your Job

1. Ask the user how they want to assign models using `ask_user` with numbered options:

   ```
   How would you like to assign models to agents?
   1. Use the default model (gemini-3-pro-preview) for all agents
   2. Use gemini-2.5-flash for all agents
   3. Inherit model from parent session
   4. Choose a model for each agent individually
   ```

   **If the user picks 1, 2, or 3:** Proceed with that model for every agent.

   **If the user picks 4 (per-agent selection):**
   Download the ZIP first (step 3) to inspect filenames, then ask per-agent model
   using `ask_user` with numbered options showing agent name and model list.
   Fall back to these common models if discovery fails: gemini-3-pro-preview,
   gemini-2.5-flash, gemini-2.0-flash.

2. Tell the user: "Agents will be installed to .gemini/agents/ (project-level)."
   Remind: "Ensure `security.folderTrust.enabled` is set if using Gemini folder trust gates."

3. Call `mcp__giljo_mcp__generate_download_token(content_type="agent_templates", platform="gemini_cli")`.
   This returns `{"download_url": "...", "expires_at": "...", "one_time_use": true}`.
   The URL is pre-signed and tied to your authenticated MCP session — no API key needed.
4. Download, extract, patch, and clean up using `run_shell_command`:
   ```bash
   TARGET_DIR=".gemini/agents"
   MODEL="<chosen_model>"
   DOWNLOAD_URL="<download_url from step 3>"
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)

   # Backup existing .md files
   for f in "$TARGET_DIR"/*.md; do
     [ -f "$f" ] && mv "$f" "${f}.bak.${TIMESTAMP}"
   done

   # Download (URL is pre-signed, no auth header needed)
   curl -k -s --fail --show-error "$DOWNLOAD_URL" -o /tmp/giljo_agents.zip
   mkdir -p "$TARGET_DIR"
   unzip -o /tmp/giljo_agents.zip -d "$TARGET_DIR"

   # Patch model frontmatter
   sed -i "s/^model: .*/model: $MODEL/" "$TARGET_DIR"/*.md

   # Remove bundled install scripts
   rm -f "$TARGET_DIR/install.sh" "$TARGET_DIR/install.ps1"

   # Cleanup
   rm -f /tmp/giljo_agents.zip
   ```
   If user chose per-agent models, run one sed per agent file instead of the glob sed.
   Token expires in 15 minutes and is one-time-use; if curl fails with expired/used token,
   generate a fresh token and retry.

5. **Enable experimental agents flag** (MANDATORY):
   Read the user's `.gemini/settings.json` (project-level or `~/.gemini/settings.json` for user-level).
   If `experimental.enableAgents` is not already set to `true`, merge it in:
   ```bash
   python3 -c "
   import json, pathlib
   p = pathlib.Path.home() / '.gemini' / 'settings.json'
   d = json.loads(p.read_text()) if p.exists() else {}
   d.setdefault('experimental', {})['enableAgents'] = True
   p.write_text(json.dumps(d, indent=2))
   "
   ```
   Merge with existing settings -- do NOT overwrite MCP server configs or other settings.
   IMPORTANT -- Windows BOM trap: Use the python3 one-liner above (BOM-safe) or your built-in
   write_file tool. If you must use PowerShell, use this exact command (the $false prevents BOM):
   ```powershell
   $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
   [System.IO.File]::WriteAllText($path, $json, $utf8NoBom)
   ```
   Do NOT use Set-Content, Out-File, or [System.Text.Encoding]::UTF8 (all add BOM).
   Show the diff before writing. This flag is required for custom agents to load.

6. Show a summary table of installed agents and instruct the user to restart Gemini CLI.

## IMPORTANT: Use `ask_user` for All User Choices

Gemini CLI supports the `ask_user` tool which presents structured options the user can select
by clicking or typing a number. You MUST use `ask_user` for every user choice (model assignment,
install location, confirmations). Never ask open-ended questions -- always present numbered menus.

## Troubleshooting

If agents don't appear after restart:
1. Check folder trust: run `/permissions trust` in Gemini CLI
2. Verify `experimental.enableAgents` is `true` in settings.json
3. Check YAML frontmatter: `kind` must be `local`, tools must use correct names
4. Run `/agents list` to see registered agents

## Rules

- Do NOT call `list_agent_templates` MCP tool -- use `generate_download_token` + ZIP download instead
- Do NOT modify agent names, descriptions, or body content from the server
- Do NOT modify GiljoAI protocol sections
- User-configurable fields: model selection, max_turns (default 50)
- ALWAYS install to `.gemini/agents/` (project root) -- agents are project-scoped
- ALWAYS ensure experimental.enableAgents is set in settings.json
- Use run_shell_command tool for file operations (cross-platform)
- Unix paths work on ALL platforms
'''
"""

GIL_ADD_GEMINI_TOML = """description = "Add a task or project to the GiljoAI dashboard"

prompt = '''
# /gil_add — Add task or project to GiljoAI dashboard

## Routing
- Task: technical debt, TODOs, bugs, small fixes, scope creep punts -> create_task MCP tool
- Project: actionable work items, features, multi-step dev work -> create_project MCP tool
- Update project: if the user wants to update/modify/change an existing project, first call list_projects to find it, then call update_project with the new values

## Task parameters
- title (required), description (optional), priority (low|medium|high|critical, default: medium), category (frontend|backend|database|infra|docs|general, default: general)

## Project parameters
- name (required), description (optional — generate from context if missing), project_type (optional — label e.g. "Frontend" OR abbreviation e.g. "FE", "TST"), series_number (optional int 1-9999 — auto-assigned if omitted), suffix (optional single letter a-z for sub-series)
- Suffix parsing: If user says "FE-5004b", use series_number=5004, suffix='b'. If user says "FE-5004", use series_number=5004 with no suffix.

## Modes

### Direct flags in arguments
- --task "Name" or --name "Name" (+ optional --priority, --category, --description) -> create task immediately
- --project "Name" (+ optional --description, --type, --series, --suffix) -> create project immediately
- --help -> show usage summary and stop

### Interactive (no flags or bare text)
1. Analyze conversation context to suggest task vs project with generated title/description
2. Ask user to confirm or adjust type, title, description
3. For tasks: ask category and priority
4. For projects: ask optional type label
5. Call appropriate MCP tool and confirm

### Read mode (read project / fetch context)
Triggers — route here when the user says any of these, or pastes one or more UUIDs with little surrounding text:
- "read project", "read projects"
- "show project", "show projects"
- "look up project", "look up projects"
- "fetch context for ..."
- A bare list of project UUIDs

GOTCHA — read this BEFORE filtering: the project identifier field is project_id, NOT id. Filtering on .id returns nothing because that key does not exist on project objects. Past Claude sessions burned 10+ minutes on this exact mistake. Always use .project_id in jq filters.

Tool sequence:
1. Call list_projects with summary_only=false and depth=2 — returns all projects with full fields. If the response is large the harness auto-saves it to a tool-result file on disk.
2. Filter the saved tool-result file with jq, keyed on project_id (NOT id). Example invocation via run_shell_command:
   jq '.projects[] | select(.project_id == "UUID-HERE") | {project_id, name, taxonomy_alias, status, description, mission}' /path/to/saved-tool-result.json
3. For deep single-project context (memory, tasks, agents), call fetch_context with product_id, project_id, and categories=["project"] instead of jq-filtering.

Response shape — each project object exposes: project_id, name, taxonomy_alias (e.g. "IMP-0015"), status, project_type, series_number, description, mission, agent_summary, created_at, completed_at.

Worked example:
User pastes 5 UUIDs. Skill calls list_projects(summary_only=false, depth=2), then jq-filters the saved tool-result file with select(.project_id == "<uuid>") for each UUID, and returns a compact summary table — one row per project: taxonomy_alias, name, status, one-line description.

## Rules
- Never pass tenant_key (auto-injected by security layer)
- Active product required (server-side enforced) — if error mentions "No active product", tell user to activate one in dashboard
- Projects are created as inactive — user activates via dashboard
- On success: show type, title/name, ID, and tell the user it should now be visible in their GiljoAI dashboard (do NOT fabricate a URL — the dashboard updates live via WebSocket)
- On error: show what went wrong and how to fix
'''
"""

# =============================================================================
# CODEX CLI TEMPLATES (Skills)
# =============================================================================

GIL_GET_AGENTS_CODEX_SKILL_MD = """---
name: gil-get-agents
description: "Download and install GiljoAI agent templates from the MCP server into Codex CLI. Use when the user says 'install giljo agents', 'get agents', 'gil_get_agents', or wants to set up GiljoAI subagents."
---

You are the GiljoAI agent template installer for Codex CLI.

## Important: Workspace Trust

Codex requires workspace trust. Run this from a trusted directory or agents will be silently skipped.

## Your Job

1. Use `request_user_input` to ask model and reasoning effort:

   ```json
   {
     "questions": [
       {
         "header": "Model Assignment",
         "id": "model_mode",
         "question": "How would you like to assign models to your GiljoAI agents?",
         "options": [
           {
             "label": "Default model for all agents (Recommended)",
             "description": "Use gpt-5.4 for every agent -- fastest setup."
           },
           {
             "label": "Choose a model per agent",
             "description": "Pick from your available models for each agent individually."
           }
         ]
       },
       {
         "header": "Reasoning Effort",
         "id": "reasoning_effort",
         "question": "What reasoning effort level?",
         "options": [
           {"label": "Low", "description": "Fastest responses, less thorough."},
           {"label": "Medium (Recommended)", "description": "Balanced speed and quality."},
           {"label": "High", "description": "Most thorough, slower responses."}
         ]
       }
     ]
   }
   ```

   **If the user picks "Default model for all agents":**
   Proceed using `gpt-5.4` for every agent with the chosen reasoning effort.

   **If the user picks "Choose a model per agent":**
   Download the ZIP first (step 2) to inspect filenames, then discover available models:
   ```powershell
   (Get-Content -Raw "$HOME\\.codex\\models_cache.json" | ConvertFrom-Json).models | Where-Object visibility -eq 'list' | Select-Object -ExpandProperty slug
   ```
   Then for EACH agent, use `request_user_input` with the available models as options.
   You can batch up to 3 questions per call (Codex limit). Build options dynamically from
   models_cache.json output. After model selection, ask reasoning effort per agent.

2. Call `mcp__giljo_mcp__generate_download_token(content_type="agent_templates", platform="codex_cli")`.
   This returns `{"download_url": "...", "expires_at": "...", "one_time_use": true}`.
   The URL is pre-signed and tied to your authenticated MCP session — no API key needed.
3. Download the agent template ZIP and extract to ~/.codex/agents/:
   ```bash
   TARGET_DIR="$HOME/.codex/agents"
   MODEL="<chosen_model>"
   EFFORT="<chosen_effort>"
   DOWNLOAD_URL="<download_url from step 2>"
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)

   # Backup existing .toml agent files
   for f in "$TARGET_DIR"/*.toml; do
     [ -f "$f" ] && mv "$f" "${f}.bak.${TIMESTAMP}"
   done

   # Download (URL is pre-signed, no auth header needed)
   curl -k -s --fail --show-error "$DOWNLOAD_URL" -o /tmp/giljo_agents.zip
   mkdir -p "$TARGET_DIR"
   unzip -o /tmp/giljo_agents.zip -d "$TARGET_DIR"

   # Patch model and reasoning effort in .toml files
   sed -i "s/^model = .*/model = \\"$MODEL\\"/" "$TARGET_DIR"/*.toml
   sed -i "s/^model_reasoning_effort = .*/model_reasoning_effort = \\"$EFFORT\\"/" "$TARGET_DIR"/*.toml

   # Remove bundled install scripts
   rm -f "$TARGET_DIR/install.sh" "$TARGET_DIR/install.ps1"

   # Cleanup
   rm -f /tmp/giljo_agents.zip
   ```
   If user chose per-agent models, run one sed per agent file instead of the glob sed.
   Token expires in 15 minutes and is one-time-use; if curl fails with expired/used token,
   generate a fresh token and retry.

4. Read the user's existing ~/.codex/config.toml to understand current state
5. Merge [agents.*] entries into config.toml -- show a diff before writing
6. Ensure [features] section has multi_agent = true AND default_mode_request_user_input = true
7. Show summary table of installed agents and instruct the user to restart Codex CLI

## IMPORTANT: Use `request_user_input` for All User Choices

This skill requires the `request_user_input` tool for structured menus. The bootstrap
installer enables `default_mode_request_user_input = true` in config.toml before the user
runs this skill. If `request_user_input` is unavailable, tell the user to add
`default_mode_request_user_input = true` under `[features]` in `~/.codex/config.toml`
and restart Codex CLI.

Rules for `request_user_input`:
- Send 1 to 3 questions per call (Codex limit)
- Each question needs: header, id, question, and options (2-3 options)
- The client auto-adds an "Other" free-text option -- do NOT add one yourself
- NEVER ask choices via plain text -- always use `request_user_input`

## CRITICAL: Agent Naming Convention

All GiljoAI agent names MUST use the `gil-` prefix to avoid collisions with Codex CLI built-in roles.

The ZIP contains files already named with the `gil-` prefix. Verify after extraction that
all .toml files in ~/.codex/agents/ use the `gil-` prefix. If any do not, rename them:
- `analyzer.toml` -> `gil-analyzer.toml`
- `implementer.toml` -> `gil-implementer.toml`
- etc.

**Why:** Codex CLI has built-in roles (analyzer, documenter, etc.) that shadow custom roles with the same name. Without the `gil-` prefix, spawn_agent uses the built-in role definition and ignores your custom TOML developer_instructions entirely. This was verified on Codex CLI v0.116.0 on 2026-03-22.

## Rules
- Do NOT call `list_agent_templates` MCP tool -- use `generate_download_token` + ZIP download instead
- Do NOT modify agent descriptions or developer_instructions content from the server
- Do NOT modify GiljoAI protocol sections within developer_instructions
- ALWAYS apply the `gil-` prefix to all agent names
- User-configurable: model, model_reasoning_effort, nickname_candidates
- ALWAYS show config.toml diff before writing -- this file affects the user's entire Codex setup
- If config.toml has existing [agents.*] entries, preserve non-GiljoAI entries
- Create ~/.codex/agents/ directory if it does not exist

## Codex Agent File Format Reference

### Per-Agent File: ~/.codex/agents/gil-{role}.toml

The ZIP extracts .toml files with the correct format. Each agent file contains:

```toml
# ~/.codex/agents/gil-implementer.toml
name = "gil-implementer"
description = "Implementation specialist for writing production-grade code"
nickname_candidates = ["gil-implementer"]
developer_instructions = \"\"\"
[The developer_instructions content goes here VERBATIM]
\"\"\"
```

Valid fields in agent .toml files (all optional, inherit from parent session if omitted):
- name -- string, MUST match the [agents.{name}] key in config.toml
- description -- string, from server response
- nickname_candidates -- array of strings, use the gil-prefixed name
- developer_instructions -- multi-line string (use triple quotes)
- model -- string, e.g. "gpt-5.4", "o3"
- model_reasoning_effort -- "low", "medium", "high", "xhigh"
- sandbox_mode -- "read-only", "workspace-write", "danger-full-access"
- approval_policy -- "on-request", "unless-allow-listed", "never"

Do NOT add fields not in this list. Codex rejects unknown fields.

### Config.toml Registration: ~/.codex/config.toml

CRITICAL: `config_file` paths are RELATIVE to the directory where config.toml lives (~/.codex/).
Use `"agents/gil-{role}.toml"` -- NOT `"~/.codex/agents/..."` (tilde is treated as a literal directory name and will fail).

Each agent must be registered in config.toml under [agents.gil-{name}]:

```toml
[features]
multi_agent = true

[agents]
max_threads = 6
max_depth = 1

[agents.gil-analyzer]
config_file = "agents/gil-analyzer.toml"
model = "gpt-5.4"
model_reasoning_effort = "medium"
nickname_candidates = ["gil-analyzer"]
```

Required fields per [agents.gil-{name}]:
- config_file -- string, RELATIVE path: "agents/gil-{name}.toml" (NOT absolute, NOT ~/)
- model -- string, user's chosen model
- model_reasoning_effort -- string, user's chosen effort level
- nickname_candidates -- array of strings, display names

### Merge Rules for config.toml

1. If [features] section exists, add multi_agent = true without removing other features
2. If [agents] section exists, preserve max_threads and max_depth if already set
3. If [agents.gil-{name}] already exists for a GiljoAI agent, overwrite it
4. If [agents.{name}] exists for a NON-GiljoAI agent (no gil- prefix), DO NOT touch it
5. Show the complete diff to the user before writing
6. Create a timestamped backup of config.toml before writing
7. Write UTF-8 without BOM. If using PowerShell, use `$utf8NoBom = New-Object System.Text.UTF8Encoding($false); [System.IO.File]::WriteAllText($path, $content, $utf8NoBom)`. Do NOT use Set-Content, Out-File, or [System.Text.Encoding]::UTF8 (all add BOM)

### Verification After Install

After restarting Codex CLI, the user should verify by spawning a test agent:

```
Spawn a gil-documenter subagent. Before doing any work, tell me the two mandatory startup MCP calls your role requires.
```

Expected answer (proves custom template is loaded):
1. mcp__giljo_mcp__health_check()
2. mcp__giljo_mcp__get_agent_mission(job_id="...", tenant_key="...")

If the agent does NOT mention these GiljoAI MCP calls, the custom template is not being loaded -- troubleshoot the config_file path and agent name.
"""

GIL_ADD_CODEX_SKILL_MD = """---
name: gil-add
description: "Add a task or project to the GiljoAI dashboard"
---

# $gil-add — Add task or project to GiljoAI dashboard

## Routing
- **Task**: technical debt, TODOs, bugs, small fixes, scope creep punts -> `create_task` MCP tool
- **Project**: actionable work items, features, multi-step dev work -> `create_project` MCP tool
- **Update project**: if the user wants to update/modify/change an existing project, first call `list_projects` to find it, then call `update_project` with the new values

## Task parameters
- `title` (required), `description` (optional), `priority` (low|medium|high|critical, default: medium), `category` (frontend|backend|database|infra|docs|general, default: general)

## Project parameters
- `name` (required), `description` (optional — generate from context if missing), `project_type` (optional — must match a pre-configured type), `series_number` (optional int 1-9999 — auto-assigned if omitted), `suffix` (optional single letter a-z for sub-series)
- **Before creating a project**, call `list_projects()` which returns available `project_types` in the response. Only use types returned — unknown types are rejected with a list of valid types.
- **Suffix parsing**: If user says "FE-5004b", use `series_number=5004, suffix='b'`. If user says "FE-5004", use `series_number=5004` with no suffix.

## Modes

### Direct flags in arguments
- `--task "Name"` or `--name "Name"` (+ optional `--priority`, `--category`, `--description`) -> create task immediately
- `--project "Name"` (+ optional `--description`, `--type`, `--series`, `--suffix`) -> create project immediately
- `--help` -> show usage summary and stop

### Interactive (no flags or bare text)
1. Analyze conversation context to suggest task vs project with generated title/description
2. Ask user to confirm or adjust type, title, description
3. For tasks: ask category and priority
4. For projects: ask optional type label
5. Call appropriate MCP tool and confirm

### Read mode (read project / fetch context)
**Triggers** — route here when the user says any of these, or pastes one or more UUIDs with little surrounding text:
- "read project", "read projects"
- "show project", "show projects"
- "look up project", "look up projects"
- "fetch context for ..."
- A bare list of project UUIDs

**GOTCHA — read this BEFORE filtering:** the project identifier field is **`project_id`**, NOT `id`. Filtering on `.id` returns nothing because that key does not exist on project objects. Past Claude sessions burned 10+ minutes on this exact mistake. Always use `.project_id` in jq filters.

**Tool sequence:**
1. Invoke `$gil-add` Read mode by calling `list_projects` with `summary_only=false` and `depth=2`. Returns all projects with full fields. If the response is large, Codex auto-saves it to a tool-result file on disk.
2. Filter the saved tool-result file with `jq`, keyed on `project_id` (NOT `id`):
   ```
   jq '.projects[] | select(.project_id == "UUID-HERE") | {project_id, name, taxonomy_alias, status, description, mission}' /path/to/saved-tool-result.json
   ```
3. For deep single-project context (memory, tasks, agents), call `fetch_context` with `product_id`, `project_id`, and `categories=["project"]` instead of jq-filtering.

**Response shape** — each project object exposes: `project_id`, `name`, `taxonomy_alias` (e.g. "IMP-0015"), `status`, `project_type`, `series_number`, `description`, `mission`, `agent_summary`, `created_at`, `completed_at`.

**Menu prompts:** When asking which projects to expand, or whether to show summary vs full, use `request_user_input` (1-3 questions per call) with structured options. Never ask via plain text. Example shape:
```json
{
  "questions": [
    {
      "header": "Read mode",
      "id": "read_depth",
      "question": "How much detail should I show?",
      "options": [
        {"label": "Summary table (recommended)", "description": "One row per project."},
        {"label": "Full mission text", "description": "Show description + mission for each."}
      ]
    }
  ]
}
```

**Worked example:**
> User pastes 5 UUIDs. Skill runs `list_projects(summary_only=false, depth=2)`, jq-filters the saved tool-result file with `select(.project_id == "<uuid>")` for each UUID, and returns a compact summary table — one row per project: `taxonomy_alias`, `name`, `status`, one-line description.

## Rules
- Never pass `tenant_key` (auto-injected by security layer)
- Active product required (server-side enforced) — if error mentions "No active product", tell user to activate one in dashboard
- Projects are created as inactive — user activates via dashboard
- On success: show type, title/name, ID, and tell the user it should now be visible in their GiljoAI dashboard (do NOT fabricate a URL — the dashboard updates live via WebSocket)
- On error: show what went wrong and how to fix
"""

# =============================================================================
# BOOTSTRAP PROMPT TEMPLATES
# =============================================================================

BOOTSTRAP_CLAUDE_CODE = """Install the GiljoAI CLI skills. This is a one-time setup.

Step 1 — Install slash commands:
Download: {SLASH_COMMANDS_URL}
Extract to: ~/.claude/commands/ (create if needed, overwrite existing)
Delete the downloaded zip.

Adapt all commands for the OS you are running on.
After installation, tell the user:
Skills installed to user-level (~/.claude/commands/).
Two commands are now available:
- /gil_get_agents — pull agent templates from the server
- /gil_add — add tasks and projects from the CLI (try /gil_add --help)

Restart Claude Code, then run /gil_get_agents to pull agent templates from the server.
Note: Download link expires in 15 minutes.
"""

BOOTSTRAP_GEMINI_CLI = """Install the GiljoAI CLI skills. This is a one-time setup.

Step 1 — Install custom commands:
Download: {SLASH_COMMANDS_URL}
Extract to: ~/.gemini/commands/ (create if needed, overwrite existing)
Delete the downloaded zip.

Adapt all commands for the OS you are running on.
After installation, tell the user:
Skills installed to user-level (~/.gemini/commands/).
Two commands are now available:
- /gil_get_agents — pull agent templates from the server
- /gil_add — add tasks and projects from the CLI (try /gil_add --help)

Restart Gemini CLI, then run /gil_get_agents to pull agent templates from the server.
Note: Download link expires in 15 minutes.
"""

BOOTSTRAP_CODEX_CLI = """Install the GiljoAI CLI skills. This is a one-time setup.

Step 1 — Install skills:
Download: {SKILLS_URL}
Extract to: ~/.codex/skills/ (create if needed, overwrite existing)
Delete the downloaded zip.

Step 2 — Enable interactive menus:
Read the user's ~/.codex/config.toml. Under the [features] section, ensure this flag is set:

```toml
[features]
default_mode_request_user_input = true
```

If [features] already exists, merge — do NOT remove existing feature flags.
If config.toml does not exist, create it with just the [features] section above.
This flag enables structured menu prompts that GiljoAI skills rely on.
IMPORTANT — Windows BOM trap: If writing config files on Windows via PowerShell, use:
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($path, $content, $utf8NoBom)
Do NOT use Set-Content, Out-File, or [System.Text.Encoding]::UTF8 (all add BOM).
Prefer your built-in write_file tool if available.

Adapt all commands for the OS you are running on.
After installation, tell the user:
Skills installed to user-level (~/.codex/skills/).
Two skills are now available:
- $gil-get-agents — pull agent templates from the server
- $gil-add — add tasks and projects from the CLI (try $gil-add --help)

Restart Codex CLI, then run $gil-get-agents to pull agent templates from the server.
Note: Download link expires in 15 minutes.
"""

BOOTSTRAP_GENERIC = """Your CLI platform was not auto-detected. Visit your GiljoAI server's
Tools -> Connect page to download skill reference files.
Install them according to your tool's documentation, then use the
get-agents command to pull agent templates.
"""

# =============================================================================
# HELPERS
# =============================================================================


def _strip_yaml_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (between --- markers) from Markdown content."""
    stripped = content.strip()
    if stripped.startswith("---"):
        end = stripped.find("---", 3)
        if end != -1:
            return stripped[end + 3 :].strip()
    return stripped


# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

_VALID_PLATFORMS = ("claude_code", "gemini_cli", "codex_cli", "generic")


def get_all_templates(platform: str = "claude_code") -> dict[str, str]:
    """
    Return slash command/skill templates for the given platform.

    Args:
        platform: Target CLI platform. One of 'claude_code', 'gemini_cli', 'codex_cli'.

    Returns:
        dict[str, str]: Mapping of filename to template content.

    Raises:
        ValueError: If platform is not recognized.
    """
    if platform not in _VALID_PLATFORMS:
        raise ValueError(f"Unknown platform '{platform}'. Must be one of: {', '.join(_VALID_PLATFORMS)}")

    if platform == "claude_code":
        return {
            "gil_get_agents.md": GIL_GET_AGENTS_MD,
            "gil_add.md": GIL_ADD_MD,
        }

    if platform == "gemini_cli":
        return {
            "gil_get_agents.toml": GIL_GET_AGENTS_GEMINI_TOML,
            "gil_add.toml": GIL_ADD_GEMINI_TOML,
        }

    if platform == "generic":
        return {
            "gil_get_agents_reference.md": _strip_yaml_frontmatter(GIL_GET_AGENTS_MD),
            "gil_add_reference.md": _strip_yaml_frontmatter(GIL_ADD_MD),
        }

    # codex_cli
    return {
        "gil-get-agents/SKILL.md": GIL_GET_AGENTS_CODEX_SKILL_MD,
        "gil-add/SKILL.md": GIL_ADD_CODEX_SKILL_MD,
    }
