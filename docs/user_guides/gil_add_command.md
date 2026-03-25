# /gil_add Slash Command User Guide

The `/gil_add` command allows you to quickly create **tasks** or **projects** directly from your Claude Code conversation. Use it to punt technical debt, capture scope creep, or spin up new projects without leaving your workflow.

## When to Use

Use `/gil_add` when:
- You discover technical debt while working on Feature X
- You realize you need to do Y but don't want to derail the current conversation
- You want to capture ideas, improvements, or future work as tasks for later review
- You need to create a new project directly from a conversation insight
- You want to track items that can eventually be converted to full projects (tasks) or start immediately (projects)

## Three Modes

### Interactive Mode (Guided Create)

Run without flags for a guided experience:

```bash
/gil_add
```

Claude will:
1. Ask whether you want to create a **task** or a **project**
2. Summarize the last concept discussed in your conversation
3. Show you the proposed title and description
4. Guide you through the remaining fields based on your selection

**Example Flow:**
```
You: /gil_add

Claude: What would you like to create?
1. Task - Capture work for later (parking lot)
2. Project - Create a project for agent orchestration

Select (1 or 2):

You: 1

Claude: Based on our conversation, I'll punt this task to your Tasks dashboard:

Title: Implement JWT authentication for API endpoints
Description: Add JWT token-based authentication to replace the current
session-based auth, improving security and enabling stateless API access

Where should this task live?
1. Active product: GiljoAI MCP
2. All Tasks (unscoped - no product association)

Which would you prefer? (1 or 2)

You: 1

Claude: What category best describes this task?
1. frontend - UI/UX work
2. backend - Server/API work
3. database - Schema/query work
4. infra - DevOps/deployment work
5. docs - Documentation work
6. general - Other/miscellaneous

Select a number (1-6):

You: 2

Claude: What's the priority level?
1. low - Nice to have
2. medium - Should do eventually (default)
3. high - Important, do soon
4. critical - Blocking, do ASAP

Select a number (1-4, default is 2):

You: 3

Claude: Task punted successfully!

Title: Implement JWT authentication for API endpoints
Category: backend
Priority: high
Scope: GiljoAI MCP
Task ID: task-def456

This task is now in your Tasks dashboard and can be converted to a
project when ready.
```

### Direct Task Mode (Quick Create)

Create a task immediately with flags:

```bash
/gil_add --task --name "Refactor auth service" --priority high --category backend
```

**Flags:**
- `--task` (required for direct task mode) - Indicates task creation
- `--name` (required) - Task title
- `--priority` (optional) - `low`, `medium` (default), `high`, or `critical`
- `--category` (optional) - `frontend`, `backend`, `database`, `infra`, `docs`, or `general` (default)
- `--description` (optional) - Detailed description (defaults to same as name)

**Examples:**
```bash
# Minimal task
/gil_add --task --name "Fix login bug"

# Task with priority
/gil_add --task --name "Add JWT auth" --priority high

# Task with full details
/gil_add --task --name "Migrate to PostgreSQL 16" --priority medium --category database --description "Upgrade database from PostgreSQL 14 to 16 for better performance"
```

### Direct Project Mode (Quick Create)

Create a project immediately with flags:

```bash
/gil_add --project --name "Authentication Overhaul"
```

**Flags:**
- `--project` (required for direct project mode) - Indicates project creation
- `--name` (required) - Project name
- `--description` (optional) - Project description

**Examples:**
```bash
# Minimal project
/gil_add --project --name "API Rate Limiting"

# Project with description
/gil_add --project --name "Dashboard Redesign" --description "Redesign the admin dashboard with improved navigation and responsive layout"
```

## Viewing Tasks

After creating a task:
1. Open the GiljoAI MCP dashboard in your browser
2. Navigate to the **Tasks** tab
3. Find your task in the list
4. Click to view details, edit, or convert to a project

## Converting Tasks to Projects

Tasks are designed to be a "parking lot" for ideas. When you're ready to work on a task:
1. Open the task in the dashboard
2. Click "Convert to Project"
3. The task becomes a full project with agent orchestration
4. Launch agents to execute the work

## Viewing Projects

After creating a project:
1. Open the GiljoAI MCP dashboard in your browser
2. Navigate to the **Projects** tab
3. Find your project in the list
4. Activate and launch agents to begin orchestration

## Categories Explained (Tasks Only)

| Category | Use For |
|----------|---------|
| `frontend` | UI/UX work, React components, styling |
| `backend` | Server code, API endpoints, business logic |
| `database` | Schema changes, migrations, query optimization |
| `infra` | DevOps, deployment, CI/CD, Docker, cloud |
| `docs` | Documentation, README updates, user guides |
| `general` | Anything that doesn't fit above categories |

## Priority Levels (Tasks Only)

| Priority | When to Use |
|----------|-------------|
| `low` | Nice to have, no rush |
| `medium` | Should do eventually (default) |
| `high` | Important, do soon |
| `critical` | Blocking issue, do ASAP |

## Best Practices

1. **Be Specific**: Use descriptive names like "Refactor auth service to use JWT" instead of "Fix auth"
2. **Task vs Project**: Use tasks for small items and future work; use projects for larger efforts that need agent orchestration
3. **Context in Description**: In interactive mode, Claude generates context from your conversation - review it carefully
4. **Right Priority**: Don't mark everything as critical - reserve that for true blockers
5. **Categorize Properly**: Helps with filtering and organizing tasks in the dashboard
6. **Review Regularly**: Check your Tasks dashboard weekly to convert items to projects

## Troubleshooting

**Error: "Specify --task or --project for direct mode"**
- You used flags but did not indicate the type
- Solution: Add `--task` or `--project` before your other flags, or use interactive mode without flags

**Error: "--name is required for direct mode"**
- You used flags but forgot `--name`
- Solution: Add `--name "Title"` or use interactive mode without flags

**Error: "Invalid priority 'urgent'"**
- Priority must be one of: low, medium, high, critical
- Solution: Use a valid priority value

**Error: "Invalid category 'api'"**
- Category must be one of: frontend, backend, database, infra, docs, general
- Solution: Use `backend` for API work

**Task or project not appearing in dashboard**
- Check your connection to the MCP server
- Refresh the relevant tab in the dashboard
- Verify you are logged into the correct account

## Tips and Tricks

- **Batch Create**: Use direct mode to quickly create multiple related tasks or projects
- **Conversation Context**: Interactive mode is great when Claude understands the context - it writes better descriptions
- **Product Scope**: Link tasks to your active product for better organization
- **Quick Projects**: Use `--project` when you know right away the work needs full orchestration

## Related Commands

- `/gil_activate` - Activate a project for orchestrator staging
- `/gil_launch` - Launch a staged project into execution
- `/gil_handover` - Trigger orchestrator succession for context handover

## Technical Details

For developers:
- Backend MCP tools: `mcp__giljo-mcp__create_task`, `mcp__giljo-mcp__create_project`
- Database models: `src.giljo_mcp.models.tasks.Task`, `src.giljo_mcp.models.projects.Project`
- Service layers: `src.giljo_mcp.services.task_service.TaskService`, `src.giljo_mcp.services.project_service.ProjectService`
- Command file: `.claude/commands/gil_add.md`
