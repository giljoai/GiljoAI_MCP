"""
Slash command markdown templates for Claude Code/Codex/Gemini (Handover 0093)

This module provides markdown templates with YAML frontmatter for slash commands
that can be installed to ~/.claude/commands/ directory.

Note: gil_activate, gil_launch, gil_handover slash commands removed - users
use the web UI for these actions. Only gil_get_claude_agents is needed for CLI.
"""

GIL_GET_CLAUDE_AGENTS_MD = """---
name: gil_get_claude_agents
description: Download and install GiljoAI agent templates to Claude Code
allowed-tools: []
---

Install GiljoAI agent templates to your Claude Code environment.

## STEP 1: Get Download URL

Call the HTTP endpoint to stage templates and get download URL.

First, get the server URL and API key from the MCP config:
- Server URL is typically `http://localhost:7272` or the URL you used to connect to GiljoAI
- API key is in your MCP connection config (X-API-Key header value)

Then make a POST request:

```bash
curl -X POST "http://localhost:7272/api/download/generate-token?content_type=agent_templates" \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json"
```

Returns JSON with: `download_url` (valid 15 minutes, one-time use), `expires_at`, and `content_type`

## STEP 2: Download Templates

Use the Bash tool (NOT PowerShell) to download. The URL contains auth token - no headers needed:

```bash
curl -o /tmp/agents.zip "{download_url}"
```

## STEP 3: Ask User Install Location

Ask: "Where should I install the {template_count} agent templates?"

Options:
- **Project agents** (`.claude/agents/`) - Available only in this project
- **User agents** (`~/.claude/agents/`) - Available across all your projects

## STEP 4: Extract to Chosen Location

Use Bash to extract based on user choice:

**For Project agents:**
```bash
mkdir -p .claude/agents && unzip -o /tmp/agents.zip -d .claude/agents/ && rm /tmp/agents.zip
```

**For User agents:**
```bash
mkdir -p ~/.claude/agents && unzip -o /tmp/agents.zip -d ~/.claude/agents/ && rm /tmp/agents.zip
```

## STEP 5: Confirm and Restart Notice

Tell the user:
1. How many templates were installed (from `template_count`)
2. Where they were installed
3. **They must restart Claude Code** (Ctrl+C and relaunch) for agents to become available
4. After restart, use agents via `@agent-name` in Claude Code

Example: "Installed 6 agent templates to ~/.claude/agents/. **Please restart Claude Code** for the agents to become available."

## IMPORTANT

- Use the Bash tool for curl/unzip commands (works on Windows via Git Bash, Linux, macOS)
- Unix paths (/tmp, ~/.claude/) work on ALL platforms
- Do NOT use PowerShell or Windows-style paths
"""


GIL_TASK_MD = """---
description: "Punt technical debt and scope creep items to the GiljoAI Tasks dashboard. Supports direct mode with flags or interactive mode with summarization."
---

# /gil_task - Punt Tasks to Dashboard

You are executing the `/gil_task` slash command to create a task in the GiljoAI MCP server's Tasks dashboard.

## Two Modes of Operation

### Direct Mode (With Flags)
When `$ARGUMENTS` contains flags like `--name`, create the task immediately.

### Interactive Mode (No Flags)
When `$ARGUMENTS` is empty or contains only a description, engage in interactive mode:
1. Summarize the last concept discussed in the conversation
2. Ask the user clarifying questions
3. Create the task with collected information

---

## Execution Instructions

### Step 1: Parse Arguments

Check if `$ARGUMENTS` contains any of these flags:
- `--name "Task Name"` (required for direct mode)
- `--priority [low|medium|high|critical]` (optional, default: medium)
- `--category [frontend|backend|database|infra|docs|general]` (optional, default: general)
- `--description "Detailed description"` (optional, uses name if not provided)

**Valid Categories:** `frontend`, `backend`, `database`, `infra`, `docs`, `general`
**Valid Priorities:** `low`, `medium`, `high`, `critical`

### Step 2: Execute Mode

#### If Flags Detected (Direct Mode):

1. **Validate Flags:**
   - Ensure `--name` is provided (REQUIRED)
   - Validate `--priority` is one of: low, medium, high, critical
   - Validate `--category` is one of: frontend, backend, database, infra, docs, general
   - If validation fails, show error message and stop

2. **Parse Flag Values:**
   ```
   Extract values from $ARGUMENTS:
   - name: value of --name flag (required)
   - priority: value of --priority flag (default: "medium")
   - category: value of --category flag (default: "general")
   - description: value of --description flag (default: same as name)
   ```

3. **Call MCP Tool:**
   Use the `mcp__giljo-mcp__create_task` tool with these parameters:
   ```
   title: <name value>
   description: <description value or name if not provided>
   priority: <priority value>
   ```

4. **Confirm Success:**
   ```
   Task created successfully!

   Title: <task title>
   Priority: <priority>
   Category: <category>
   Task ID: <task_id from MCP response>

   You can view this task in the GiljoAI Tasks dashboard.
   ```

#### If No Flags (Interactive Mode):

1. **Summarize Conversation:**
   - Review the last 3-5 messages in the conversation
   - Identify the most recent concept, feature, or issue discussed
   - Generate a concise title and detailed description

2. **Show Summary to User:**
   ```
   Based on our conversation, I'll punt this task to your Tasks dashboard:

   Title: <generated title>
   Description: <generated description>
   ```

3. **Ask Clarifying Questions:**

   **Question 1 - Category:**
   ```
   What category best describes this task?
   1. frontend - UI/UX work
   2. backend - Server/API work
   3. database - Schema/query work
   4. infra - DevOps/deployment work
   5. docs - Documentation work
   6. general - Other/miscellaneous

   Select a number (1-6):
   ```

   **Question 2 - Priority:**
   ```
   What's the priority level?
   1. low - Nice to have
   2. medium - Should do eventually (default)
   3. high - Important, do soon
   4. critical - Blocking, do ASAP

   Select a number (1-4, default is 2):
   ```

4. **Call MCP Tool:**
   After collecting all responses, use `mcp__giljo-mcp__create_task`:
   ```
   title: <generated title>
   description: <generated description>
   priority: <user selected priority>
   ```

5. **Confirm Success:**
   ```
   Task punted successfully!

   Title: <task title>
   Category: <category>
   Priority: <priority>
   Task ID: <task_id from MCP response>

   This task is now in your Tasks dashboard and can be converted to a project when ready.
   ```

---

## Error Handling

### Validation Errors (Direct Mode):
- Missing `--name`: "Error: --name flag is required for direct mode. Use /gil_task without flags for interactive mode."
- Invalid priority: "Error: Invalid priority '<value>'. Must be one of: low, medium, high, critical"
- Invalid category: "Error: Invalid category '<value>'. Must be one of: frontend, backend, database, infra, docs, general"

### MCP Tool Errors:
If `mcp__giljo-mcp__create_task` returns an error:
```
Failed to create task: <error message>

Please check your connection to the GiljoAI MCP server and try again.
```

---

## Examples

### Direct Mode
```
/gil_task --name "Refactor auth service" --priority high --category backend
```

### Interactive Mode
```
/gil_task
```
(Claude summarizes conversation, asks category/priority, creates task)

---

## Important Notes

1. **$ARGUMENTS Variable:** Contains everything typed after `/gil_task`. Parse for flags or use interactive mode.

2. **Conversation Context:** For interactive mode, analyze recent conversation to generate meaningful titles.

3. **Task Dashboard:** Created tasks appear in the GiljoAI web UI under Tasks tab and can be converted to projects.
"""


def get_all_templates() -> dict[str, str]:
    """
    Return all slash command templates

    Returns:
        dict[str, str]: Mapping of filename to markdown content
    """
    return {
        "gil_get_claude_agents.md": GIL_GET_CLAUDE_AGENTS_MD,
        "gil_task.md": GIL_TASK_MD,
    }
