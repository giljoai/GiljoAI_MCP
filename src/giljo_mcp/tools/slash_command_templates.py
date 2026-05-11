# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Slash command templates for Claude Code, Codex CLI, and Gemini CLI (Handover 0836b)

This module provides platform-specific command templates:
- Claude Code: Markdown with YAML frontmatter (.md) for ~/.claude/commands/
- Gemini CLI: TOML format (.toml) for ~/.gemini/commands/
- Codex CLI: Markdown skills (.md) for ~/.codex/skills/<name>/SKILL.md

INF-5026: `/gil_add` (writes-only) + `/gil_get` (reads-only) fork. The
canonical Claude Code `gil_get` body below is a verbatim copy of the
documenter-authored skill (`~/.claude/commands/gil_get.md`, INF-5026
documenter handoff). Keep these in sync — divergence between the
authored file and the server-shipped template is a bug.

Also provides bootstrap prompt templates for one-time CLI onboarding.
"""

from pathlib import Path


# Semver for the skills/commands package. Bumped when slash command templates change.
# Referenced by health_check so the frontend can compare installed vs available.
SKILLS_VERSION = "1.1.12"

_DATA_DIR = Path(__file__).resolve().parent / "_slash_data"

GIL_GET_MD = (_DATA_DIR / "gil_get.claude.md").read_text(encoding="utf-8")
GIL_GET_REFERENCE_MD = (_DATA_DIR / "gil_get_reference.md").read_text(encoding="utf-8")
GIL_GET_GEMINI_TOML = (_DATA_DIR / "gil_get.gemini.toml").read_text(encoding="utf-8")
GIL_GET_CODEX_SKILL_MD = (_DATA_DIR / "gil_get.codex.SKILL.md").read_text(encoding="utf-8")
GIL_GET_AGENTS_CODEX_SKILL_MD = (_DATA_DIR / "gil_get_agents.codex.SKILL.md").read_text(encoding="utf-8")

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
description: "Add, update, or read tasks and projects in the GiljoAI dashboard. Routes by intent (create / update / read existing project info)."
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
- **Project type discovery**: pass any candidate `project_type`; unknown values are rejected by `create_project` with a list of valid types in the error message. (The dashboard's project-types page is the canonical source.)
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

**GOTCHA:** the project identifier field is **`project_id`**, NOT `id`. Filtering on `.id` returns nothing. Always use `.project_id` in jq filters.

**IDs you already have:** `tenant_key` is auto-injected from auth. `product_id` is in your session context the moment any tool response surfaces it (most tool responses include it). You only need `project_id` — get it from step 1 below or from the user's paste.

**Tool sequence (cheap-first — pick the smallest path that answers the question):**
1. **Find the project_id by name/alias** → `mcp__giljo_mcp__list_projects(summary_only=true)`. Returns ~150 lines of metadata (project_id, name, taxonomy_alias, status, timestamps). Lightweight. Match by `name` or `taxonomy_alias` to grab the project_id.
2. **Read one project deeply** → `mcp__giljo_mcp__fetch_context(product_id=..., project_id=..., categories=["project"])`. Returns ~300 tokens for one project: project_name, project_alias, project_description, orchestrator_mission, status, staging_status. This is the right tool when the user wants description/mission for ONE project.
3. **Bulk read many projects (only if the user pastes multiple UUIDs and needs full fields for all)** → `mcp__giljo_mcp__list_projects(mode="planning")` for description+mission, or `mode="audit"` if memory headlines are also needed. The harness auto-saves the tool result to a file when large. Filter with jq:
   ```bash
   jq '.projects[] | select(.project_id == "UUID-HERE") | {project_id, name, taxonomy_alias, status, description, mission}' /path/to/saved-tool-result.json
   ```

**Modes (preferred over numeric depth):** `triage` (id+name+status+dates), `planning` (+ description, mission, agent counts), `audit` (+ memory headlines + agent summaries), `forensic` (+ full memory bodies, agent results). `mode="forensic"` is the heavy archaeology call — only use it when you actually need full memory bodies.

**Response shapes:**
- `fetch_context(["project"])`: `project_name`, `project_alias`, `project_description`, `orchestrator_mission`, `status`, `staging_status`
- `list_projects` row (`mode="planning"`): `project_id`, `name`, `taxonomy_alias`, `status`, `project_type`, `series_number`, `description`, `mission`, `agent_summary`, `created_at`, `completed_at`

**Worked example:**
> User asks "what's IMP-0019 about?" → call `list_projects(mode="triage")` → match `taxonomy_alias=="IMP-0019"` → grab `project_id` → call `fetch_context(product_id, project_id, ["project"])` → return description + mission. No multi-MB pull.

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

GIL_ADD_GEMINI_TOML = """description = "Add, update, or read tasks and projects in the GiljoAI dashboard. Routes by intent (create / update / read existing project info)."

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

GOTCHA: the project identifier field is project_id, NOT id. Filtering on .id returns nothing. Always use .project_id in jq filters.

IDs you already have: tenant_key is auto-injected from auth. product_id appears in tool responses (cache it once you see it). You only need project_id — get it from step 1 or the user's paste.

Tool sequence (cheap-first — pick the smallest path that answers the question):
1. Find the project_id by name/alias: call list_projects with mode="triage". Returns ~150 lines of metadata only (project_id, name, taxonomy_alias, status, timestamps). Match by name or taxonomy_alias to grab the project_id.
2. Read one project deeply: call fetch_context with product_id, project_id, and categories=["project"]. Returns ~300 tokens for that single project (project_name, project_alias, project_description, orchestrator_mission, status, staging_status). This is the right tool for "what's project X about?" / "show me the mission for X".
3. Bulk read many projects (only if user pastes multiple UUIDs and needs full fields for all): call list_projects with mode="planning" for description+mission, or mode="audit" if memory headlines are also needed. Harness auto-saves large results to a tool-result file. Filter with jq via run_shell_command:
   jq '.projects[] | select(.project_id == "UUID-HERE") | {project_id, name, taxonomy_alias, status, description, mission}' /path/to/saved-tool-result.json

Modes (preferred over numeric depth): triage (id+name+status+dates), planning (+ description, mission, agent counts), audit (+ memory headlines + agent summaries), forensic (+ full memory bodies, agent results). Use forensic only when full memory bodies are genuinely needed.

Response shapes:
- fetch_context(["project"]): project_name, project_alias, project_description, orchestrator_mission, status, staging_status
- list_projects row (mode="planning"): project_id, name, taxonomy_alias, status, project_type, series_number, description, mission, agent_summary, created_at, completed_at

Worked example:
User asks "what's IMP-0019 about?" → call list_projects(mode="triage") → match taxonomy_alias=="IMP-0019" → grab project_id → call fetch_context(product_id, project_id, ["project"]) → return description + mission. No multi-MB pull.

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


GIL_ADD_CODEX_SKILL_MD = """---
name: gil-add
description: "Add, update, or read tasks and projects in the GiljoAI dashboard. Routes by intent (create / update / read existing project info)."
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
- **Project type discovery**: pass any candidate `project_type`; unknown values are rejected by `create_project` with a list of valid types in the error message. (The dashboard's project-types page is the canonical source.)
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

**GOTCHA:** the project identifier field is **`project_id`**, NOT `id`. Filtering on `.id` returns nothing. Always use `.project_id` in jq filters.

**IDs you already have:** `tenant_key` is auto-injected from auth. `product_id` is in your session context the moment any tool response surfaces it. You only need `project_id` — get it from step 1 or the user's paste.

**Tool sequence (cheap-first — pick the smallest path that answers the question):**
1. **Find the project_id by name/alias** → call `list_projects` with `mode="triage"`. Returns ~150 lines of metadata only (project_id, name, taxonomy_alias, status, timestamps). Match by `name` or `taxonomy_alias` to grab the project_id.
2. **Read one project deeply** → call `fetch_context` with `product_id`, `project_id`, and `categories=["project"]`. Returns ~300 tokens for one project (project_name, project_alias, project_description, orchestrator_mission, status, staging_status). Right tool for "what's project X about?" / "show mission for X".
3. **Bulk read many projects (only if user pastes multiple UUIDs and needs full fields for all)** → call `list_projects` with `mode="planning"` for description+mission, or `mode="audit"` if memory headlines are also needed. Codex auto-saves large results to a tool-result file. Filter with `jq`:
   ```
   jq '.projects[] | select(.project_id == "UUID-HERE") | {project_id, name, taxonomy_alias, status, description, mission}' /path/to/saved-tool-result.json
   ```

**Modes (preferred over numeric depth):** `triage` (id+name+status+dates), `planning` (+ description, mission, agent counts), `audit` (+ memory headlines + agent summaries), `forensic` (+ full memory bodies, agent results). Use `forensic` only when full memory bodies are genuinely needed.

**Response shapes:**
- `fetch_context(["project"])`: `project_name`, `project_alias`, `project_description`, `orchestrator_mission`, `status`, `staging_status`
- `list_projects` row (`mode="planning"`): `project_id`, `name`, `taxonomy_alias`, `status`, `project_type`, `series_number`, `description`, `mission`, `agent_summary`, `created_at`, `completed_at`

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
> User pastes 5 UUIDs. Skill runs `list_projects(mode="planning")`, jq-filters the saved tool-result file with `select(.project_id == "<uuid>")` for each UUID, and returns a compact summary table — one row per project: `taxonomy_alias`, `name`, `status`, one-line description.

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
Three commands are now available:
- /gil_get_agents — pull agent templates from the server
- /gil_add — create tasks and projects from the CLI (try /gil_add --help)
- /gil_get — read existing tasks and projects

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
Three commands are now available:
- /gil_get_agents — pull agent templates from the server
- /gil_add — create tasks and projects from the CLI (try /gil_add --help)
- /gil_get — read existing tasks and projects

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
Three skills are now available:
- $gil-get-agents — pull agent templates from the server
- $gil-add — create tasks and projects from the CLI (try $gil-add --help)
- $gil-get — read existing tasks and projects

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
            "gil_get.md": GIL_GET_MD,
            "gil_get_reference.md": GIL_GET_REFERENCE_MD,
        }

    if platform == "gemini_cli":
        return {
            "gil_get_agents.toml": GIL_GET_AGENTS_GEMINI_TOML,
            "gil_add.toml": GIL_ADD_GEMINI_TOML,
            "gil_get.toml": GIL_GET_GEMINI_TOML,
            "gil_get_reference.md": GIL_GET_REFERENCE_MD,
        }

    if platform == "generic":
        return {
            "gil_get_agents_reference.md": _strip_yaml_frontmatter(GIL_GET_AGENTS_MD),
            "gil_add_reference.md": _strip_yaml_frontmatter(GIL_ADD_MD),
            "gil_get_reference.md": GIL_GET_REFERENCE_MD,
        }

    # codex_cli
    return {
        "gil-get-agents/SKILL.md": GIL_GET_AGENTS_CODEX_SKILL_MD,
        "gil-add/SKILL.md": GIL_ADD_CODEX_SKILL_MD,
        "gil-get/SKILL.md": GIL_GET_CODEX_SKILL_MD,
        "gil-get/reference.md": GIL_GET_REFERENCE_MD,
    }
