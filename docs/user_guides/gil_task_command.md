# /gil_task Slash Command User Guide

The `/gil_task` command allows you to quickly "punt" technical debt, scope creep, and future work items from your Claude Code conversation directly to the GiljoAI Tasks dashboard.

## When to Use

Use `/gil_task` when:
- You discover technical debt while working on Feature X
- You realize you need to do Y but don't want to derail the current conversation
- You want to capture ideas, improvements, or future work for later review
- You need to track tasks that can eventually be converted to full projects

## Two Modes

### Direct Mode (Quick Create)

Create a task immediately with flags:

```bash
/gil_task --name "Refactor auth service" --priority high --category backend
```

**Flags:**
- `--name` (required) - Task title
- `--priority` (optional) - `low`, `medium` (default), `high`, or `critical`
- `--category` (optional) - `frontend`, `backend`, `database`, `infra`, `docs`, or `general` (default)
- `--description` (optional) - Detailed description (defaults to same as name)

**Examples:**
```bash
# Minimal
/gil_task --name "Fix login bug"

# With priority
/gil_task --name "Add JWT auth" --priority high

# Full details
/gil_task --name "Migrate to PostgreSQL 16" --priority medium --category database --description "Upgrade database from PostgreSQL 14 to 16 for better performance"
```

### Interactive Mode (Guided Create)

Run without flags for a guided experience:

```bash
/gil_task
```

Claude will:
1. Summarize the last concept discussed in your conversation
2. Show you the proposed task title and description
3. Ask you to choose:
   - **Scope**: Active product or unscoped
   - **Category**: frontend, backend, database, infra, docs, general
   - **Priority**: low, medium, high, critical
4. Create the task with your selections

**Example Flow:**
```
You: /gil_task

Claude: Based on our conversation, I'll punt this task to your Tasks dashboard:

Title: Implement JWT authentication for API endpoints
Description: Add JWT token-based authentication to replace the current session-based auth, improving security and enabling stateless API access

Where should this task live?
1. Active product: GiljoAI MCP Server
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
Scope: GiljoAI MCP Server
Task ID: task-def456

This task is now in your Tasks dashboard and can be converted to a project when ready.
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

## Categories Explained

| Category | Use For |
|----------|---------|
| `frontend` | UI/UX work, React components, styling |
| `backend` | Server code, API endpoints, business logic |
| `database` | Schema changes, migrations, query optimization |
| `infra` | DevOps, deployment, CI/CD, Docker, cloud |
| `docs` | Documentation, README updates, user guides |
| `general` | Anything that doesn't fit above categories |

## Priority Levels

| Priority | When to Use |
|----------|-------------|
| `low` | Nice to have, no rush |
| `medium` | Should do eventually (default) |
| `high` | Important, do soon |
| `critical` | Blocking issue, do ASAP |

## Best Practices

1. **Be Specific**: Use descriptive names like "Refactor auth service to use JWT" instead of "Fix auth"
2. **Context in Description**: In interactive mode, Claude generates context from your conversation - review it carefully
3. **Right Priority**: Don't mark everything as critical - reserve that for true blockers
4. **Categorize Properly**: Helps with filtering and organizing tasks in the dashboard
5. **Review Regularly**: Check your Tasks dashboard weekly to convert items to projects

## Troubleshooting

**Error: "--name is required for direct mode"**
- You used flags but forgot `--name`
- Solution: Add `--name "Task Title"` or use interactive mode without flags

**Error: "Invalid priority 'urgent'"**
- Priority must be one of: low, medium, high, critical
- Solution: Use a valid priority value

**Error: "Invalid category 'api'"**
- Category must be one of: frontend, backend, database, infra, docs, general
- Solution: Use `backend` for API work

**Task not appearing in dashboard**
- Check your connection to the MCP server
- Refresh the Tasks tab in the dashboard
- Verify you're logged into the correct account

## Tips and Tricks

- **Batch Create**: Use direct mode in a loop to quickly create multiple related tasks
- **Conversation Context**: Interactive mode is great when Claude understands the context - it writes better descriptions
- **Product Scope**: Link tasks to your active product for better organization
- **Unscoped Tasks**: Use "All Tasks" for general ideas not tied to a specific product

## Related Commands

- `/gil_activate` - Activate a project for orchestrator staging
- `/gil_launch` - Launch a staged project into execution
- `/gil_handover` - Trigger orchestrator succession for context handover

## Technical Details

For developers:
- Backend MCP tool: `mcp__giljo-mcp__create_task`
- Database model: `src.giljo_mcp.models.tasks.Task`
- Service layer: `src.giljo_mcp.services.task_service.TaskService`
- Command file: `.claude/commands/gil_task.md`
