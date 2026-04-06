# Handover 0910c: Write INSTALLATION_GUIDE.md and MCP_TOOLS_REFERENCE.md

**Edition Scope:** CE
**Date:** 2026-04-06
**From Agent:** Orchestrator (0910 kickoff)
**To Agent:** documentation-manager
**Priority:** High
**Estimated Effort:** 3-4 hours
**Status:** Not Started
**Series:** 0910 Documentation Overhaul (subagent 3 of 4, runs after 0910a in parallel with 0910b)

---

## Task Summary

Write the two technical reference documents: INSTALLATION_GUIDE.md and MCP_TOOLS_REFERENCE.md. Content must come from reading actual source files. The MCP tools reference must list every tool registered in mcp_sdk_server.py, matched exactly to the code.

---

## Critical Rules (read before touching anything)

1. No em dashes anywhere. Use colons, semicolons, and periods. Not "this -- that". Use "this: that".
2. No emoji in any document body.
3. Every MCP tool name must match what is registered in mcp_sdk_server.py exactly. Do not invent names or paraphrase.
4. Do not reference handover numbers in output documents. Users do not know what handovers are.
5. Active voice. Direct sentences. No filler.
6. Prefer tables for MCP tool parameters. Prefer numbered lists for step sequences.
7. No document exceeds 1000 lines.
8. Activate venv before any code inspection: `source /media/patrik/Work/GiljoAI_MCP/venv/bin/activate && export PYTHONPATH=.`
9. Use absolute paths for all bash commands. The working directory resets between bash calls.

---

## Context

0910a has already archived all stale docs and created scaffold files. This subagent fills in INSTALLATION_GUIDE.md and MCP_TOOLS_REFERENCE.md. It runs in parallel with 0910b (which writes PRODUCT_OVERVIEW.md and USER_GUIDE.md). There is no file conflict.

There are 29 registered MCP tools in mcp_sdk_server.py. Read the file to get exact names, descriptions, and parameter signatures.

---

## Dependencies

**Requires:** 0910a complete (scaffold files exist at /docs/INSTALLATION_GUIDE.md and /docs/MCP_TOOLS_REFERENCE.md).

**Runs in parallel with:** 0910b (different output files).

---

## Source Files to Read

Read these files before writing anything.

| File | What to Extract |
|------|-----------------|
| `/media/patrik/Work/GiljoAI_MCP/install.py` | Installation steps, prompts, network mode options, config generation, what each step does |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/components/setup/SetupWizardOverlay.vue` | Setup wizard steps (STEPS constant), what each step shows |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/components/setup/SetupStep2Connect.vue` | Connection config UI |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/components/setup/SetupStep3Commands.vue` | Commands shown to user for Claude/Codex/Gemini |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/components/setup/SetupStep4Complete.vue` | Completion step content |
| `/media/patrik/Work/GiljoAI_MCP/api/endpoints/mcp_sdk_server.py` | Every @mcp.tool registration: name, description, parameters, return type |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/views/McpIntegration.vue` | MCP integration page content (platform-specific connection instructions) |

---

## Implementation Plan

### Phase 1: Read install.py and setup wizard components

```bash
grep -n "def \|step\|Step\|network\|postgresql\|python\|venv\|npm\|Node\|Prerequisites\|print\|Welcome" \
  /media/patrik/Work/GiljoAI_MCP/install.py | head -80
```

Read the `run()` method fully to understand each numbered step.

Read the STEPS constant in SetupWizardOverlay.vue:

```bash
grep -n "STEPS\|steps\|id.*tools\|id.*connect\|id.*install\|id.*launch\|label" \
  /media/patrik/Work/GiljoAI_MCP/frontend/src/components/setup/SetupWizardOverlay.vue | head -30
```

Read the three setup step components to extract:
- Step 2: what connection details the user enters (host, port, API key)
- Step 3: the exact commands shown for Claude Code, Codex CLI, Gemini CLI
- Step 4: what the completion screen tells the user

```bash
grep -n "claude\|codex\|gemini\|mcp\|config\|command\|snippet\|add.*tool\|API_KEY" \
  /media/patrik/Work/GiljoAI_MCP/frontend/src/components/setup/SetupStep3Commands.vue | head -60
```

Read McpIntegration.vue for the platform-specific connection JSON or command formats:

```bash
grep -n "claude\|codex\|gemini\|mcp\|server\|url\|API_KEY\|config\|snippet" \
  /media/patrik/Work/GiljoAI_MCP/frontend/src/views/McpIntegration.vue | head -60
```

Read the giljo_setup tool in mcp_sdk_server.py to understand what it installs:

```bash
grep -n -A 40 "async def giljo_setup" \
  /media/patrik/Work/GiljoAI_MCP/api/endpoints/mcp_sdk_server.py
```

### Phase 2: Write INSTALLATION_GUIDE.md

Write to `/media/patrik/Work/GiljoAI_MCP/docs/INSTALLATION_GUIDE.md`.

**Prerequisites section:**

List the actual requirements from install.py:
- Python version check (read what version install.py requires: `check_python_version()`)
- PostgreSQL version (read `POSTGRESQL_DOWNLOAD_URL` and discovery logic)
- Node.js (read whether it is required or optional for frontend)
- Git (needed to clone the repo)
- Operating system: Windows, Linux, macOS (all supported, read `platform.system()` logic)

Format as a simple table:

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12+ | ... |
| PostgreSQL | 18 | ... |
| Node.js | 18+ | Required for frontend build |
| Git | Any | For cloning |

**Installation Steps section:**

Walk through each step in install.py's `run()` method in plain language. Number them clearly. Do not copy code; describe what happens.

Key steps to document (from install.py):
1. Clone the repository: `git clone <url> && cd GiljoAI_MCP`
2. Run install.py: `python install.py`
3. install.py prompts for network mode (localhost vs LAN/WAN). Describe the two modes and when to use each.
4. install.py checks Python version, discovers PostgreSQL, discovers Node.js.
5. install.py creates a venv and installs Python dependencies from requirements.txt.
6. install.py generates config files (.env, config.yaml).
7. install.py creates the database, runs migrations.
8. install.py installs frontend dependencies (npm install).
9. install.py prompts for HTTPS setup if LAN/WAN mode was selected.
10. install.py launches the browser at `http://localhost:7272` (localhost mode) or the LAN address.

**Setup Wizard section:**

The setup wizard runs in the browser on first launch. Read the STEPS constant in SetupWizardOverlay.vue for the four step labels. Describe each step:

Step 1 (Choose Tools): Select which AI tools to connect (Claude Code, Codex CLI, Gemini CLI). Can select multiple.

Step 2 (Connect): The wizard shows the server URL and generates an API key. The user copies these into their AI tool's MCP config.

Step 3 (Install): Shows the exact commands to add GiljoAI as an MCP server for each selected tool. Read SetupStep3Commands.vue for the actual command format.

Step 4 (Launch): Confirms the connection and shows next steps. Read SetupStep4Complete.vue.

**Connecting AI Tools section:**

For each platform (Claude Code, Codex CLI, Gemini CLI), document the exact config format. Read this from McpIntegration.vue and SetupStep3Commands.vue. Use code blocks with the actual config JSON or command structure.

**giljo_setup Tool section:**

Explain that after connecting, agents can run `giljo_setup` to install the `/gil_add` and `/gil_get_agents` skills (or `$gil-add` / `$gil-get-agents` on Codex CLI). Read the giljo_setup tool in mcp_sdk_server.py for what it installs and where.

**Troubleshooting section:**

Common issues to include:
- PostgreSQL not found: check PATH, run `pg_config` or `psql --version`
- Port 7272 already in use: change the port in config.yaml
- HTTPS cert not trusted: the setup wizard shows a CertTrustModal with instructions (read CertTrustModal.vue briefly)
- Connection refused from AI tool: verify the server is running, check the API key

Document length target: 300-500 lines.

### Phase 3: Read all 29 MCP tools from mcp_sdk_server.py

This is the most important accuracy requirement. Read every `@mcp.tool` registration.

```bash
grep -n "@mcp.tool\|async def \|\"\"\"" \
  /media/patrik/Work/GiljoAI_MCP/api/endpoints/mcp_sdk_server.py | head -100
```

For each of the 29 tools, extract:
- Function name (this is the tool name)
- Description (from the decorator description or the docstring)
- Parameters: name, type, whether required or optional, description (from type annotations and docstring)
- Return type

Read each function individually for parameters. The function signatures are the ground truth.

Tool list by function name (read the file to confirm these and get descriptions):

Discovery: `health_check`, `discovery`

Project Management: `create_project`, `update_project_mission`, `close_project_and_update_memory`

Agent Lifecycle: `spawn_agent_job`, `get_pending_jobs`, `get_agent_mission`, `update_agent_mission`, `set_agent_status`, `report_progress`, `complete_job`, `get_agent_result`, `get_workflow_status`, `reactivate_job`, `dismiss_reactivation`

Messaging: `send_message`, `receive_messages`, `list_messages`

Context and Memory: `fetch_context`, `write_360_memory`

Vision Documents: `get_vision_doc`, `write_product_from_analysis`

Tasks: `create_task`

Setup and Export: `giljo_setup`, `generate_download_token`, `get_agent_templates_for_export`, `submit_tuning_review`

Note: there are 29 tools total. Verify the count when reading the file: `grep -c "@mcp.tool" /media/patrik/Work/GiljoAI_MCP/api/endpoints/mcp_sdk_server.py`

### Phase 4: Write MCP_TOOLS_REFERENCE.md

Write to `/media/patrik/Work/GiljoAI_MCP/docs/MCP_TOOLS_REFERENCE.md`.

**Overview section:**

Brief paragraph: GiljoAI MCP exposes 29 tools to connected AI coding tools. Tools are organized by category. Every tool call requires a valid `job_id` and `tenant_key` (injected by the orchestrator spawn prompt; individual agents receive these at spawn time).

**Per-tool format:**

Use this format for every tool:

```markdown
### tool_name

**Description:** What the tool does.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| param_name | str | Yes | What it is |

**Returns:** Shape of the response.

**Example:**

\`\`\`
tool_name(param_name="value")
\`\`\`
```

Write every tool in its category section. The example calls must use the real parameter names from the function signature.

**Discovery category** tools deal with system health and capability enumeration.

**Project Management category** tools create and close projects and write project-level context.

**Agent Lifecycle category** tools handle the full agent job lifecycle from spawn to completion.

**Messaging category** tools send and receive messages between agents and from the dashboard user.

**Context and Memory category** tools fetch assembled context and write 360 Memory entries.

**Vision Documents category** tools interact with product vision documents.

**Tasks category** tools create tasks (technical debt, backlog items).

**Setup and Export category** tools handle first-run installation and agent template export.

Document length target: 400-700 lines.

### Phase 5: Verify both documents

```bash
grep -n " -- " /media/patrik/Work/GiljoAI_MCP/docs/INSTALLATION_GUIDE.md
grep -n " -- " /media/patrik/Work/GiljoAI_MCP/docs/MCP_TOOLS_REFERENCE.md
```

Both must return no output.

Verify MCP tool count matches code:

```bash
grep -c "@mcp.tool" /media/patrik/Work/GiljoAI_MCP/api/endpoints/mcp_sdk_server.py
grep -c "^### " /media/patrik/Work/GiljoAI_MCP/docs/MCP_TOOLS_REFERENCE.md
```

The number of `### ` headings in MCP_TOOLS_REFERENCE.md must equal the tool count minus category headings. Do a manual count to verify every tool has a section.

Check line counts:

```bash
wc -l /media/patrik/Work/GiljoAI_MCP/docs/INSTALLATION_GUIDE.md \
       /media/patrik/Work/GiljoAI_MCP/docs/MCP_TOOLS_REFERENCE.md
```

Neither may exceed 1000 lines.

Check for stale references:

```bash
grep -in "handover\|0910\|deprecated\|legacy\|old version" \
  /media/patrik/Work/GiljoAI_MCP/docs/INSTALLATION_GUIDE.md \
  /media/patrik/Work/GiljoAI_MCP/docs/MCP_TOOLS_REFERENCE.md
```

### Phase 6: Commit

```bash
cd /media/patrik/Work/GiljoAI_MCP
git add docs/INSTALLATION_GUIDE.md docs/MCP_TOOLS_REFERENCE.md
git commit -m "docs(0910c): write INSTALLATION_GUIDE and MCP_TOOLS_REFERENCE from source inspection"
```

---

## Testing Requirements

**Accuracy checks:**

1. Every tool name in MCP_TOOLS_REFERENCE.md must match a function name that follows an `@mcp.tool` decorator in mcp_sdk_server.py. No extras, no missing.
2. The installation steps must reflect what install.py actually does (read the `run()` method in full).
3. The MCP connection commands in INSTALLATION_GUIDE.md must come from reading SetupStep3Commands.vue or McpIntegration.vue, not from memory.
4. Prerequisites must list the actual Python version required (read `check_python_version()` in install.py).

**Format checks:**

1. No em dashes.
2. No handover numbers.
3. Line counts within limits.
4. Tool count in docs matches code.

---

## Success Criteria

- [ ] /docs/INSTALLATION_GUIDE.md written with all sections (prerequisites, install steps, setup wizard, per-platform connection, giljo_setup, troubleshooting)
- [ ] /docs/MCP_TOOLS_REFERENCE.md written with all 29 tools documented
- [ ] Every tool name matches the registered function name in mcp_sdk_server.py
- [ ] Zero em dashes in either document
- [ ] Zero handover number references in either document
- [ ] Neither document exceeds 1000 lines
- [ ] Commit created with the specified message

---

## Rollback Plan

The scaffold files from 0910a remain in git. To roll back: revert to the 0910a commit and the scaffold files (empty section headers) are restored.

---

## Chain Log

Update `/media/patrik/Work/GiljoAI_MCP/prompts/0910_chain/chain_log.json` when done:

```json
{
  "0910c": {
    "status": "complete",
    "commit": "<commit hash>",
    "notes": "Wrote INSTALLATION_GUIDE (~N lines) and MCP_TOOLS_REFERENCE (~N lines, 29 tools)."
  }
}
```
