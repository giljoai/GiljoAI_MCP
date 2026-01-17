---
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

   Note: Store category in the description or title since the MCP tool may not have a direct category parameter.

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

   **Question 1 - Scope:**
   ```
   Where should this task live?
   1. Active product: [Product Name if available]
   2. All Tasks (unscoped - no product association)

   Which would you prefer? (1 or 2)
   ```

   **Question 2 - Category:**
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

   **Question 3 - Priority:**
   ```
   What's the priority level?
   1. low - Nice to have
   2. medium - Should do eventually (default)
   3. high - Important, do soon
   4. critical - Blocking, do ASAP

   Select a number (1-4, default is 2):
   ```

4. **Collect User Responses:**
   Wait for the user to answer each question before proceeding.

5. **Call MCP Tool:**
   After collecting all responses, use `mcp__giljo-mcp__create_task`:
   ```
   title: <generated title>
   description: <generated description>
   priority: <user selected priority>
   ```

   Note: Include category information in the description or title.

6. **Confirm Success:**
   ```
   Task punted successfully!

   Title: <task title>
   Category: <category>
   Priority: <priority>
   Scope: <product name or "All Tasks (unscoped)">
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
If `mcp__giljo-mcp__create_task` returns `{"success": false, "error": "..."}`:
```
Failed to create task: <error message>

Please check your connection to the GiljoAI MCP server and try again.
```

---

## Examples

### Example 1: Direct Mode
```
User: /gil_task --name "Refactor auth service" --priority high --category backend

Claude:
[Parses flags: name="Refactor auth service", priority="high", category="backend"]
[Calls mcp__giljo-mcp__create_task with title="Refactor auth service", description="Refactor auth service", priority="high"]
[Receives response: {"success": true, "task_id": "task-abc123"}]

Task created successfully!

Title: Refactor auth service
Priority: high
Category: backend
Task ID: task-abc123

You can view this task in the GiljoAI Tasks dashboard.
```

### Example 2: Interactive Mode
```
User: /gil_task

Claude:
Based on our conversation, I'll punt this task to your Tasks dashboard:

Title: Implement JWT authentication for API endpoints
Description: Add JWT token-based authentication to replace the current session-based auth, improving security and enabling stateless API access

Where should this task live?
1. Active product: GiljoAI MCP Server
2. All Tasks (unscoped - no product association)

Which would you prefer? (1 or 2)

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

User: 2

Claude:
What's the priority level?
1. low - Nice to have
2. medium - Should do eventually (default)
3. high - Important, do soon
4. critical - Blocking, do ASAP

Select a number (1-4, default is 2):

User: 3

Claude:
[Calls mcp__giljo-mcp__create_task with collected information]
[Receives response: {"success": true, "task_id": "task-def456"}]

Task punted successfully!

Title: Implement JWT authentication for API endpoints
Category: backend
Priority: high
Scope: GiljoAI MCP Server
Task ID: task-def456

This task is now in your Tasks dashboard and can be converted to a project when ready.
```

---

## Important Notes

1. **MCP Tool Parameters:** The `create_task` tool accepts `title`, `description`, `priority`, and optionally `assigned_to`. Store category in the description text since the Task model supports it via the `category` field.

2. **Product Scope:** If the user selects a product scope in interactive mode, you may need to fetch the active product ID using another MCP tool if available, or note it in the task description.

3. **Conversation Context:** For interactive mode, analyze recent conversation history to generate meaningful titles and descriptions. Don't just punt generic "Task X" - be specific based on what was discussed.

4. **$ARGUMENTS Variable:** This contains everything the user typed after `/gil_task`. Parse it for flags or treat it as free text for interactive mode.

---

## Task Arguments

The `$ARGUMENTS` variable will contain the user's input after `/gil_task`.

Execute the appropriate mode based on the presence of flags in `$ARGUMENTS`.