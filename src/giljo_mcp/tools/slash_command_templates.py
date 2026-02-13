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

## STEP 1: Generate Download URL

Call the MCP tool to generate a download URL:

```
mcp__giljo-mcp__generate_download_token(content_type="agent_templates")
```

This returns:
- `download_url` - Valid for 15 minutes, one-time use
- `expires_at` - Expiration timestamp
- `content_type` - "agent_templates"

## STEP 2: Download Templates

Use the Bash tool (NOT PowerShell) to download. The URL contains auth token - no headers needed:

```bash
curl -o /tmp/agents.zip "{download_url}"
```

## STEP 3: Ask User Install Location

Ask: "Where should I install the {template_count} agent templates?"

Options (present in this order):
1. **Project agents (Recommended)** (`.claude/agents/`) - Available only in this project
2. **User agents** (`~/.claude/agents/`) - Available across all your projects

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


GIL_ADD_MD = """---
description: "Add a task or project to the GiljoAI dashboard. Routes to task (technical debt/TODOs) or project (actionable work items) based on context."
---

# /gil_add - Add Task or Project to Dashboard

You are executing the `/gil_add` slash command to create either a **task** or a **project** in the GiljoAI MCP server's dashboard.

**Tasks** are technical debt, TODOs, small fixes, "do this later" items, and scope creep punts.
**Projects** are actionable work items requiring orchestrator coordination, feature implementations, multi-step development work, or continuation of completed work.

## Three Modes of Operation

### Direct Task Mode (--task or --name flags)
When `$ARGUMENTS` contains `--task` or `--name`, create a task immediately.

### Direct Project Mode (--project flag)
When `$ARGUMENTS` contains `--project`, create a project immediately.

### Interactive Mode (No recognized flags)
When `$ARGUMENTS` is empty or contains no recognized flags, use conversation context to suggest the appropriate type and guide the user through creation.

---

## Execution Instructions

### Step 1: Parse Arguments

Check `$ARGUMENTS` for the following flags:

**Task flags:**
- `--task` (triggers direct task mode, can be combined with other task flags)
- `--name "Task Name"` (triggers direct task mode, required name for task)
- `--priority [low|medium|high|critical]` (optional, default: medium)
- `--category [frontend|backend|database|infra|docs|general]` (optional, default: general)
- `--description "Detailed description"` (optional, uses name/task value if not provided)

**Project flags:**
- `--project "Project Name"` (triggers direct project mode, required name for project)
- `--description "Detailed description"` (optional, Claude generates from context if missing)

**Valid Categories:** `frontend`, `backend`, `database`, `infra`, `docs`, `general`
**Valid Priorities:** `low`, `medium`, `high`, `critical`

### Step 2: Route to Mode

- If `$ARGUMENTS` contains `--name` or `--task` -> Direct Task Mode
- If `$ARGUMENTS` contains `--project` -> Direct Project Mode
- Otherwise -> Interactive Mode

---

## Direct Task Mode

1. **Validate Flags:**
   - If `--name` is present, use its value as the task name
   - If `--task` is present with a quoted value (e.g., `--task "Fix login bug"`), use that as the task name
   - If `--task` is present without a value but `--name` is also present, use `--name`
   - If neither `--name` nor a `--task` value is provided, show error and stop
   - Validate `--priority` is one of: low, medium, high, critical
   - Validate `--category` is one of: frontend, backend, database, infra, docs, general

2. **Parse Flag Values:**
   ```
   Extract values from $ARGUMENTS:
   - title: value of --name or --task flag (required)
   - priority: value of --priority flag (default: "medium")
   - category: value of --category flag (default: "general")
   - description: value of --description flag (default: same as title)
   ```

3. **Call MCP Tool:**
   Use the `mcp__giljo-mcp__create_task` tool with:
   ```
   title: <title value>
   description: <description value or title if not provided>
   priority: <priority value>
   category: <category value>
   ```

4. **Confirm Success:**
   ```
   Task created successfully.

   Title: <task title>
   Priority: <priority>
   Category: <category>
   Task ID: <task_id from MCP response>

   You can view this task in the GiljoAI Tasks dashboard.
   ```

---

## Direct Project Mode

1. **Validate Flags:**
   - `--project` must have a quoted value (the project name)
   - If `--project` has no value, show error and stop

2. **Parse Flag Values:**
   ```
   Extract values from $ARGUMENTS:
   - name: value of --project flag (required)
   - description: value of --description flag (optional)
   ```

3. **Generate Description (if missing):**
   If `--description` is not provided, review the conversation context and generate a concise description of the project's purpose and scope. If there is no meaningful conversation context, use the project name as the description.

4. **Call MCP Tool:**
   Use the `mcp__giljo-mcp__create_project` tool with:
   ```
   name: <project name>
   description: <description value>
   ```

5. **Confirm Success:**
   ```
   Project created successfully.

   Name: <project name>
   Description: <description>
   Project ID: <project_id from MCP response>
   Alias: <alias from MCP response, if available>

   Project created as inactive. Open the GiljoAI dashboard to activate and launch.
   ```

---

## Interactive Mode

### Phase 1: Analyze and Suggest

1. **Review Conversation Context:**
   - Identify the most relevant recent concept, feature, or issue discussed
   - Determine whether the item is better suited as a task or a project

2. **Classification Guidance:**
   - **Suggest Task when:** The item is technical debt, a TODO, a small fix, a "do this later" item, a scope creep punt, a bug to address later, or a minor improvement
   - **Suggest Project when:** The item requires orchestrator coordination, involves multi-step development, is a feature implementation, represents a significant body of work, or is a continuation/follow-up of completed work

3. **Present Suggestion to User:**
   ```
   Based on our conversation, this sounds like a [task/project]:

   [Generated title/name]: <title or name>
   [Generated description]: <description>

   Would you like to add it as:
   1. Task - technical debt / future TODO
   2. Project - actionable work for orchestrator execution
   ```

4. **Wait for User Confirmation:**
   - If user selects Task (or confirms task suggestion), proceed to Task Path
   - If user selects Project (or confirms project suggestion), proceed to Project Path
   - If user provides corrections to the title/description, incorporate them

### Phase 2A: Task Path (Interactive)

1. **Confirm Title and Description:**
   If not already confirmed in Phase 1, present:
   ```
   Title: <generated title>
   Description: <generated description>

   Does this look correct?
   ```
   Allow user to edit or confirm.

2. **Ask for Category:**
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

3. **Ask for Priority:**
   ```
   What is the priority level?
   1. low - Nice to have
   2. medium - Should do eventually (default)
   3. high - Important, do soon
   4. critical - Blocking, do ASAP

   Select a number (1-4, default is 2):
   ```

4. **Call MCP Tool:**
   Use `mcp__giljo-mcp__create_task` with:
   ```
   title: <confirmed title>
   description: <confirmed description>
   priority: <user selected priority>
   category: <user selected category>
   ```

5. **Confirm Success:**
   ```
   Task created successfully.

   Title: <task title>
   Category: <category>
   Priority: <priority>
   Task ID: <task_id from MCP response>

   This task is now in your Tasks dashboard.
   ```

### Phase 2B: Project Path (Interactive)

1. **Confirm Name and Description:**
   If not already confirmed in Phase 1, present:
   ```
   Project Name: <generated name>
   Description: <generated description>

   Does this look correct?
   ```
   Allow user to edit or confirm.

2. **Call MCP Tool:**
   Use `mcp__giljo-mcp__create_project` with:
   ```
   name: <confirmed project name>
   description: <confirmed description>
   ```

3. **Confirm Success:**
   ```
   Project created successfully.

   Name: <project name>
   Description: <description>
   Project ID: <project_id from MCP response>
   Alias: <alias from MCP response, if available>

   Project created as inactive. Open the GiljoAI dashboard to activate and launch.
   ```

---

## Error Handling

### Validation Errors (Direct Task Mode):
- Missing name: "Error: A task name is required. Provide --name \\"Task Name\\" or --task \\"Task Name\\", or use /gil_add without flags for interactive mode."
- Invalid priority: "Error: Invalid priority '<value>'. Must be one of: low, medium, high, critical"
- Invalid category: "Error: Invalid category '<value>'. Must be one of: frontend, backend, database, infra, docs, general"

### Validation Errors (Direct Project Mode):
- Missing name: "Error: A project name is required. Provide --project \\"Project Name\\", or use /gil_add without flags for interactive mode."

### MCP Tool Errors:
If the MCP tool returns an error:
```
Failed to create [task/project]: <error message>

Please check your connection to the GiljoAI MCP server and try again.
```

### Active Product Errors:
If the MCP tool returns an error containing "No active product" or similar:
```
No active product is set. You need to activate a product in the GiljoAI dashboard before creating tasks or projects.

Open the dashboard and select a product to activate, then try again.
```

---

## Examples

### Example 1: Direct Task Mode with --name
```
User: /gil_add --name "Refactor auth service" --priority high --category backend

Claude:
[Parses flags: name="Refactor auth service", priority="high", category="backend"]
[Calls mcp__giljo-mcp__create_task with title="Refactor auth service", description="Refactor auth service", priority="high", category="backend"]

Task created successfully.

Title: Refactor auth service
Priority: high
Category: backend
Task ID: task-abc123

You can view this task in the GiljoAI Tasks dashboard.
```

### Example 2: Direct Task Mode with --task
```
User: /gil_add --task "Fix WebSocket reconnection" --priority medium

Claude:
[Parses flags: task="Fix WebSocket reconnection", priority="medium"]
[Calls mcp__giljo-mcp__create_task with title="Fix WebSocket reconnection", description="Fix WebSocket reconnection", priority="medium", category="general"]

Task created successfully.

Title: Fix WebSocket reconnection
Priority: medium
Category: general
Task ID: task-def456

You can view this task in the GiljoAI Tasks dashboard.
```

### Example 3: Direct Project Mode
```
User: /gil_add --project "Agent Health Monitoring v2" --description "Implement real-time agent health checks with configurable thresholds and alerting"

Claude:
[Parses flags: project="Agent Health Monitoring v2", description="Implement real-time..."]
[Calls mcp__giljo-mcp__create_project with name="Agent Health Monitoring v2", description="Implement real-time agent health checks with configurable thresholds and alerting"]

Project created successfully.

Name: Agent Health Monitoring v2
Description: Implement real-time agent health checks with configurable thresholds and alerting
Project ID: proj-ghi789
Alias: agent-health-monitoring-v2

Project created as inactive. Open the GiljoAI dashboard to activate and launch.
```

### Example 4: Interactive Mode (Routes to Task)
```
User: [has been discussing a CSS alignment bug in the status board]
User: /gil_add

Claude:
Based on our conversation, this sounds like a task:

Title: Fix CSS alignment issue in StatusChip component
Description: The StatusChip badge text is misaligned when health indicator icons are present, causing visual inconsistency in the status board grid layout.

Would you like to add it as:
1. Task - technical debt / future TODO
2. Project - actionable work for orchestrator execution

User: 1

Claude:
What category best describes this task?
1. frontend - UI/UX work
2. backend - Server/API work
3. database - Schema/query work
4. infra - DevOps/deployment work
5. docs - Documentation work
6. general - Other/miscellaneous

Select a number (1-6):

User: 1

Claude:
What is the priority level?
1. low - Nice to have
2. medium - Should do eventually (default)
3. high - Important, do soon
4. critical - Blocking, do ASAP

Select a number (1-4, default is 2):

User: 2

Claude:
[Calls mcp__giljo-mcp__create_task with collected information]

Task created successfully.

Title: Fix CSS alignment issue in StatusChip component
Category: frontend
Priority: medium
Task ID: task-jkl012

This task is now in your Tasks dashboard.
```

### Example 5: Interactive Mode (Routes to Project)
```
User: [has been discussing a new agent template management overhaul]
User: /gil_add

Claude:
Based on our conversation, this sounds like a project:

Project Name: Agent Template Management Overhaul
Description: Redesign the agent template system to support versioned templates, template inheritance, and per-organization template customization. Includes database schema changes, service layer updates, API endpoints, and frontend template editor.

Would you like to add it as:
1. Task - technical debt / future TODO
2. Project - actionable work for orchestrator execution

User: 2

Claude:
Project Name: Agent Template Management Overhaul
Description: Redesign the agent template system to support versioned templates, template inheritance, and per-organization template customization. Includes database schema changes, service layer updates, API endpoints, and frontend template editor.

Does this look correct?

User: yes

Claude:
[Calls mcp__giljo-mcp__create_project with collected information]

Project created successfully.

Name: Agent Template Management Overhaul
Description: Redesign the agent template system to support versioned templates, template inheritance, and per-organization template customization. Includes database schema changes, service layer updates, API endpoints, and frontend template editor.
Project ID: proj-mno345
Alias: agent-template-management-overhaul

Project created as inactive. Open the GiljoAI dashboard to activate and launch.
```

---

## Important Notes

1. **MCP Tool Parameters:** The `create_task` tool accepts `title`, `description`, `priority`, and `category`. The `create_project` tool accepts `name` and `description`. Tasks and projects are always bound to the active product (enforced server-side).

2. **Tenant Key:** Never pass `tenant_key` to MCP tools. It is auto-injected by the MCP security layer.

3. **Active Product Required:** Both tasks and projects require an active product. If the MCP tool returns an error about "No active product set", inform the user they need to activate a product in the GiljoAI dashboard first.

4. **Conversation Context:** For interactive mode, analyze conversation history to generate meaningful titles and descriptions. Be specific based on what was discussed. Use your judgement on how far back to look for relevant context.

5. **Project Lifecycle:** Projects are created as inactive. The user must open the GiljoAI dashboard to activate and launch them with orchestrator coordination.

6. **$ARGUMENTS Variable:** This contains everything the user typed after `/gil_add`. Parse it for flags or treat the absence of flags as the trigger for interactive mode.

---

## Task Arguments

The `$ARGUMENTS` variable will contain the user's input after `/gil_add`.

Execute the appropriate mode based on the presence of flags in `$ARGUMENTS`.
"""


def get_all_templates() -> dict[str, str]:
    """
    Return all slash command templates

    Returns:
        dict[str, str]: Mapping of filename to markdown content
    """
    return {
        "gil_get_claude_agents.md": GIL_GET_CLAUDE_AGENTS_MD,
        "gil_add.md": GIL_ADD_MD,
    }
