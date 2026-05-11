---
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
   (Get-Content -Raw "$HOME\.codex\models_cache.json" | ConvertFrom-Json).models | Where-Object visibility -eq 'list' | Select-Object -ExpandProperty slug
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
   sed -i "s/^model = .*/model = \"$MODEL\"/" "$TARGET_DIR"/*.toml
   sed -i "s/^model_reasoning_effort = .*/model_reasoning_effort = \"$EFFORT\"/" "$TARGET_DIR"/*.toml

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
developer_instructions = """
[The developer_instructions content goes here VERBATIM]
"""
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
