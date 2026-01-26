# 0383 - MCP Tool Surface Audit + Legacy Download Tool Removal

## Context

User request:
1. Audit the public MCP tool catalog for `giljo-mcp` and classify tools by who uses them (user/operator vs orchestrator/agents).
2. Identify exposed tools that appear unused or user-only (candidates for decommission).
3. Completely remove legacy hidden download-flow MCP tools (no cascading breakage):
   - `gil_fetch`
   - `gil_import_productagents`
   - `gil_import_personalagents`

## Status

**COMPLETE** (legacy tools removed from MCP exposure + implementations + UI/docs references cleaned; targeted tests updated).

Note: `pytest tests/` still fails collection due to unrelated missing legacy modules (pre-existing).

---

## Decommission: Legacy Download Tools (Removed)

Removed from:
- MCP HTTP tool catalog (`tools/list`) and call routing
- ToolAccessor methods / implementations
- Legacy REST wrappers (`/api/download/mcp/gil_import_*`)
- Slash command template set and server-side registries
- Frontend UI references and user-facing docs

Also removed the dependent alias tool `gil_update_agents` (it was just a legacy alias on top of `gil_fetch`).

---

## Current Public MCP Tool Catalog (30 tools)

**Source of truth:** `api/endpoints/mcp_http.py` (`tool_map` keys).

```
acknowledge_job
check_succession_status
complete_job
create_project
create_successor_orchestrator
create_task
fetch_context
~~file_exists~~ (removed 0501)
get_agent_download_url
get_agent_mission
get_next_instruction
get_orchestrator_instructions
get_pending_jobs
get_template
get_workflow_status
gil_activate
gil_handover
gil_launch
health_check
list_messages
orchestrate_project
receive_messages
report_error
report_progress
send_message
setup_slash_commands
spawn_agent_job
switch_project
update_agent_mission
update_project_mission
```

---

## Classification: User/Operator vs Agent Work-Loop

### User/Operator (CLI/UI setup + lifecycle control)

These are primarily for *you* (or the dashboard) rather than for “agents doing work”:
- `setup_slash_commands` (installs Claude Code slash commands into `~/.claude/commands/`)
- `get_agent_download_url` (stages active templates ZIP for `/gil_get_claude_agents`)
- `gil_activate` (activate a project for staging)
- `gil_launch` (launch staged project into execution)
- `gil_handover` (manual orchestrator succession trigger)
- Likely UI/admin utilities: `create_project`, `switch_project`, `create_task` (confirm in UI before decommission)

### Orchestrator tools (staging + spawning + coordination)

Used directly by orchestrator prompts / orchestration workflows:
- `health_check`
- `get_orchestrator_instructions`
- `update_project_mission`
- `spawn_agent_job`
- `update_agent_mission`
- `get_workflow_status`
- `send_message`
- `orchestrate_project` (auto-orchestration entrypoint)

### Worker agent tools (job loop)

Used by spawned agents to fetch mission, coordinate, and close out work:
- `get_agent_mission`
- `acknowledge_job`
- `receive_messages`
- `get_next_instruction`
- `report_progress`
- `complete_job`
- `report_error`

### Messaging + audit

Used for agent-to-agent communication and UI visibility:
- `send_message`
- `receive_messages`
- `list_messages`

### Context + templates (context reading / template retrieval)

Used for context loading and template resolution:
- `fetch_context`
- ~~`file_exists`~~ (removed in Handover 0501 - flawed assumption: MCP server cannot access user local files)
- `get_template`

### Succession helpers

Used for orchestrator succession lifecycle:
- `create_successor_orchestrator`
- `check_succession_status`

---

## Potential Decommission Candidates (Needs Confirmation)

These tools have no obvious presence in the thin prompts / generic agent protocol text and may be UI-only or rarely used:
- `create_project`
- `switch_project`
- `create_task`
- `orchestrate_project`
- `get_pending_jobs`
- `list_messages`
- `check_succession_status` / `create_successor_orchestrator` (if `gil_handover` fully covers the user flow)

Recommendation before removal:
1. Confirm usage via server-side audit/logging of tool calls (or DB event history if present).
2. Confirm frontend/dashboard does not rely on them.
3. Remove in one PR: schema + routing + ToolAccessor + tests + docs.

---

## New Supported Download/Install Flow (Jan 2026+)

- Slash commands installation:
  - MCP tool: `setup_slash_commands`
  - Public ZIP endpoint: `/api/download/slash-commands.zip`
- Agent templates installation:
  - Slash command: `/gil_get_claude_agents`
  - MCP tool: `get_agent_download_url` (returns one-time token URL)
  - Token download endpoint: `/api/download/temp/{token}/agent_templates.zip`

---

## Files Changed (Key)

- `api/endpoints/mcp_http.py`
- `src/giljo_mcp/tools/tool_accessor.py`
- `src/giljo_mcp/tools/slash_command_templates.py`
- `api/endpoints/downloads.py`
- `src/giljo_mcp/slash_commands/__init__.py`
- `frontend/src/components/SlashCommandSetup.vue`
- `frontend/src/services/api.js`

Docs refreshed to remove legacy command references:
- `installer/templates/README.md`
- `docs/guides/MCP_SLASH_COMMANDS_QUICK_REFERENCE.md`
- `docs/guides/MCP_SLASH_COMMANDS_USER_GUIDE.md`
- `docs/guides/token_efficient_mcp_downloads_user_guide.md`
- `docs/guides/token_efficient_downloads_technical_guide.md`

---

## Tests Run (Targeted)

```
pytest --no-cov tests/test_slash_command_setup.py
pytest --no-cov tests/test_downloads.py
pytest --no-cov tests/integration/test_downloads_integration.py
pytest --no-cov tests/integration/test_mcp_http_tool_catalog.py
pytest --no-cov tests/unit/test_tools_tool_accessor.py
```

