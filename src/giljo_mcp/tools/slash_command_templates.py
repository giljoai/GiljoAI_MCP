"""
Slash command templates for Claude Code, Codex CLI, and Gemini CLI (Handover 0836b)

This module provides platform-specific command templates:
- Claude Code: Markdown with YAML frontmatter (.md) for ~/.claude/commands/
- Gemini CLI: TOML format (.toml) for ~/.gemini/commands/
- Codex CLI: Markdown skills (.md) for ~/.codex/skills/<name>/SKILL.md

Also provides bootstrap prompt templates for one-time CLI onboarding.
"""

# =============================================================================
# CLAUDE CODE TEMPLATES
# =============================================================================

GIL_GET_AGENTS_MD = """---
name: gil_get_agents
description: Download and install GiljoAI agent templates from the MCP server
allowed-tools: mcp__giljo-mcp__*, Bash, Read, Write, AskUserQuestion
---

You are the GiljoAI agent template installer for Claude Code.

## Your Job

1. Call `mcp__giljo-mcp__get_agent_templates_for_export` with `platform="claude_code"`
2. Show a summary table of all agents (role, name, description)
3. Use AskUserQuestion to ask for model preference with selectable options:
   Question: "Which model should agents use?"
   Options: ["sonnet (balanced — recommended)", "haiku (fast, cost-effective)", "opus (maximum capability)", "Let me pick per agent"]
   If user picks "Let me pick per agent", ask for each agent individually using AskUserQuestion with the same model options (minus the per-agent option).
4. Use AskUserQuestion to ask install location:
   Question: "Where should agents be installed?"
   Options: ["User agents (~/.claude/agents/) — available everywhere (recommended)", "Project agents (.claude/agents/) — this project only"]
5. If the target directory has existing `.md` files, back them up:
   rename `*.md` to `*.md.bak.YYYYMMDD_HHMMSS`
6. Write each agent file with the user's model selection applied to the `model` frontmatter field
7. Report what was installed and instruct the user to restart Claude Code

## Rules

- ALWAYS use AskUserQuestion with options for user choices — never ask open-ended questions
- Do NOT modify the agent name, description, or body content
- Do NOT modify protocol sections
- The ONLY user-configurable field is model selection
- Colors are pre-assigned by the server — do not change them
- Use the Bash tool for file operations (cross-platform via Git Bash)
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

# =============================================================================
# GEMINI CLI TEMPLATES
# =============================================================================

GIL_GET_AGENTS_GEMINI_TOML = """description = "Download and install GiljoAI agent templates from the MCP server"

prompt = \"\"\"
You are the GiljoAI agent template installer for Gemini CLI.

## Your Job

1. Call the GiljoAI MCP tool `get_agent_templates_for_export` with `platform="gemini_cli"`
2. Show a summary table of all agents (role, name, description)
3. Ask the user which model they prefer per agent (default: gemini-2.5-pro)
   The user can set one model for all or pick per-agent.
4. Ask: Install as project agents (`.gemini/agents/`) or user agents (`~/.gemini/agents/`)?
5. If the target directory has existing agent `.md` files, back them up:
   rename `*.md` to `*.md.bak.YYYYMMDD_HHMMSS`
6. Write each agent file with the user's model selection applied
7. Note: parallel subagent execution is experimental in Gemini CLI.
   Agents will work but may execute sequentially.
8. Instruct the user to restart Gemini CLI

## Rules

- Do NOT modify agent names, descriptions, or body content
- Do NOT modify GiljoAI protocol sections
- User-configurable fields: model selection, max_turns (default 50)
- Colors are NOT supported in Gemini agent frontmatter — omit them
- Use shell tool for file operations (cross-platform)
- Unix paths work on ALL platforms
\"\"\"
"""

GIL_ADD_GEMINI_TOML = """description = "Add a task or project to the GiljoAI dashboard"

prompt = \"\"\"
You are executing the gil_add command to create either a task or a project in the GiljoAI MCP server's dashboard.

Tasks are technical debt, TODOs, small fixes, "do this later" items, and scope creep punts.
Projects are actionable work items requiring orchestrator coordination, feature implementations, multi-step development work, or continuation of completed work.

## Three Modes of Operation

### Direct Task Mode (--task or --name flags)
When arguments contain --task or --name, create a task immediately.

### Direct Project Mode (--project flag)
When arguments contain --project, create a project immediately.

### Interactive Mode (No recognized flags)
When arguments are empty or contain no recognized flags, use conversation context to suggest the appropriate type and guide the user through creation.

## Execution Instructions

### Step 1: Parse Arguments

Task flags:
- --task (triggers direct task mode)
- --name "Task Name" (triggers direct task mode, required name for task)
- --priority [low|medium|high|critical] (optional, default: medium)
- --category [frontend|backend|database|infra|docs|general] (optional, default: general)
- --description "Detailed description" (optional)

Project flags:
- --project "Project Name" (triggers direct project mode)
- --description "Detailed description" (optional)

### Step 2: Route to Mode
- If arguments contain --name or --task -> Direct Task Mode
- If arguments contain --project -> Direct Project Mode
- Otherwise -> Interactive Mode

## Direct Task Mode
1. Parse and validate flags (name required, validate priority/category values)
2. Call GiljoAI MCP tool create_task with: title, description, priority, category
3. Confirm success with task ID

## Direct Project Mode
1. Parse and validate flags (project name required)
2. If --description missing, generate from conversation context
3. Call GiljoAI MCP tool create_project with: name, description
4. Confirm success with project ID. Note: project created as inactive.

## Interactive Mode
1. Review conversation context to suggest task vs project
2. Present suggestion with generated title/description
3. Ask user to confirm type (task or project)
4. For tasks: ask category (frontend/backend/database/infra/docs/general) and priority (low/medium/high/critical)
5. For projects: confirm name and description
6. Call appropriate MCP tool and confirm success

## Important Notes
- Never pass tenant_key to MCP tools (auto-injected)
- Both tasks and projects require an active product (server-side enforced)
- Projects are created as inactive — user activates via dashboard
\"\"\"
"""

# =============================================================================
# CODEX CLI TEMPLATES (Skills)
# =============================================================================

GIL_GET_AGENTS_CODEX_SKILL_MD = """---
name: gil-get-agents
description: "Download and install GiljoAI agent templates into Codex CLI"
---

You are the GiljoAI agent template installer for Codex CLI.

## Your Job

1. Call the GiljoAI MCP tool `get_agent_templates_for_export` with `platform="codex_cli"`
2. Show a summary table of all agents (role, name, description)
3. Ask the user which model to use per agent (default: gpt-5.2-codex)
   and reasoning effort per agent (low/medium/high, default: medium).
   The user can set one for all or pick per-agent.
4. **config.toml Safety Protocol** (MANDATORY):
   a. Check if `~/.codex/config.toml` exists
   b. If YES: back up to `~/.codex/config.toml.bak.YYYYMMDD_HHMMSS`
   c. Read current config to identify existing `[agents.*]` sections
   d. Prepare merge: add/update only GiljoAI agent entries, preserve everything else
   e. Show unified diff of config.toml changes to user before writing
   f. ONLY write after explicit user confirmation
   g. If config.toml does NOT exist: create it with only GiljoAI agent entries
5. Write `.toml` agent files to `~/.codex/agents/` using the `toml_format_reference`
   from the API response
6. Instruct the user to restart Codex CLI

## Rules

- Do NOT modify agent names, descriptions, or developer_instructions content
- Do NOT modify GiljoAI protocol sections within developer_instructions
- User-configurable fields: model, model_reasoning_effort, nickname_candidates
- ALWAYS show config.toml diff before writing — this file affects the user's entire Codex setup
- ALWAYS back up existing config.toml before modifying
- If user declines the diff, abort without writing
- If config.toml has existing [agents.*] entries, preserve them
- Use shell commands for file operations (cross-platform)
"""

GIL_ADD_CODEX_SKILL_MD = """---
name: gil-add
description: "Add a task or project to the GiljoAI dashboard"
---

You are executing the gil-add skill to create either a **task** or a **project** in the GiljoAI MCP server's dashboard.

**Tasks** are technical debt, TODOs, small fixes, "do this later" items, and scope creep punts.
**Projects** are actionable work items requiring orchestrator coordination, feature implementations, multi-step development work, or continuation of completed work.

## Three Modes of Operation

### Direct Task Mode (--task or --name flags)
When arguments contain `--task` or `--name`, create a task immediately.

### Direct Project Mode (--project flag)
When arguments contain `--project`, create a project immediately.

### Interactive Mode (No recognized flags)
When arguments are empty or contain no recognized flags, use conversation context to suggest the appropriate type and guide the user through creation.

## Execution Instructions

### Step 1: Parse Arguments

**Task flags:**
- `--task` (triggers direct task mode)
- `--name "Task Name"` (triggers direct task mode, required name for task)
- `--priority [low|medium|high|critical]` (optional, default: medium)
- `--category [frontend|backend|database|infra|docs|general]` (optional, default: general)
- `--description "Detailed description"` (optional)

**Project flags:**
- `--project "Project Name"` (triggers direct project mode)
- `--description "Detailed description"` (optional)

### Step 2: Route to Mode
- If arguments contain `--name` or `--task` -> Direct Task Mode
- If arguments contain `--project` -> Direct Project Mode
- Otherwise -> Interactive Mode

## Direct Task Mode
1. Parse and validate flags (name required, validate priority/category values)
2. Call GiljoAI MCP tool `create_task` with: title, description, priority, category
3. Confirm success with task ID

## Direct Project Mode
1. Parse and validate flags (project name required)
2. If `--description` missing, generate from conversation context
3. Call GiljoAI MCP tool `create_project` with: name, description
4. Confirm success with project ID. Note: project created as inactive.

## Interactive Mode
1. Review conversation context to suggest task vs project
2. Present suggestion with generated title/description
3. Ask user to confirm type (task or project)
4. For tasks: ask category (frontend/backend/database/infra/docs/general) and priority (low/medium/high/critical)
5. For projects: confirm name and description
6. Call appropriate MCP tool and confirm success

## Important Notes
- Never pass `tenant_key` to MCP tools (auto-injected by security layer)
- Both tasks and projects require an active product (server-side enforced)
- Projects are created as inactive — user activates via dashboard
"""

# =============================================================================
# BOOTSTRAP PROMPT TEMPLATES
# =============================================================================

BOOTSTRAP_CLAUDE_CODE = """Install the GiljoAI CLI integration. This is a one-time setup.

Step 1 — Install slash commands:
Download: {SLASH_COMMANDS_URL}
Extract to: ~/.claude/commands/ (create if needed, overwrite existing)
Delete the downloaded zip.

Step 2 — Install agent templates:
Before downloading, use AskUserQuestion to ask the user where to install agents with these options:
- "User agents (~/.claude/agents/) — available everywhere (recommended)"
- "Project agents (.claude/agents/) — this project only"

Download: {AGENT_TEMPLATES_URL}
Extract to the chosen directory (create if needed).
If existing agents are present, back them up to a backup_YYYYMMDD_HHMMSS/ subfolder first.
Delete the downloaded zip.

Adapt all commands for the OS you are running on.
After both installs complete, instruct the user to restart Claude Code.
Note: Download links expire in 15 minutes.
"""

BOOTSTRAP_GEMINI_CLI = """Install the GiljoAI CLI integration. This is a one-time setup.

Step 1 — Install custom commands:
Download: {SLASH_COMMANDS_URL}
Extract to: ~/.gemini/commands/ (create if needed, overwrite existing)
Delete the downloaded zip.

Step 2 — Install agent templates:
First, ask the user where to install agents:
  1. Project agents (.gemini/agents/) — available only in the current project
  2. User agents (~/.gemini/agents/) — available across all projects (recommended)

Download: {AGENT_TEMPLATES_URL}
Extract to the chosen directory (create if needed).
If existing agents are present, back them up to a backup_YYYYMMDD_HHMMSS/ subfolder first.
Delete the downloaded zip.

Adapt all commands for the OS you are running on.
After both installs complete, instruct the user to restart Gemini CLI.
Note: Download links expire in 15 minutes.
"""

BOOTSTRAP_CODEX_CLI = """Install the GiljoAI CLI integration. This is a one-time setup.

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
"""

# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

_VALID_PLATFORMS = ("claude_code", "gemini_cli", "codex_cli")


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

    # codex_cli
    return {
        "gil-get-agents/SKILL.md": GIL_GET_AGENTS_CODEX_SKILL_MD,
        "gil-add/SKILL.md": GIL_ADD_CODEX_SKILL_MD,
    }
