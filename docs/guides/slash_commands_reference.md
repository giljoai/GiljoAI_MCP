# GiljoAI MCP Slash Commands

**Version**: 1.0
**Created**: October 6, 2025
**Status**: Production Ready
**Location**: `.claude/commands/*.md`

---

## Overview

GiljoAI MCP provides custom slash commands for Claude Code CLI that enable intelligent task management, agent messaging, and project orchestration directly from the command line. These commands bridge the gap between conversational AI interaction and structured MCP operations.

---

## Design Philosophy

### Problem Statement

During active development sessions with Claude Code, users often need to:
1. **Capture technical debt** without breaking flow (scope creep prevention)
2. **Create contextual tasks** from discussions (preserve conversation context)
3. **Communicate with agents** using natural language (fuzzy matching)
4. **Start orchestration** without copy/paste from web UI (streamlined workflow)

### Solution: Prefix-Based Command System

**Why `/gil-` prefix?**
- ✅ **Unambiguous**: Clearly distinguishes system commands from natural conversation
- ✅ **Namespaced**: Prevents conflicts with other slash commands or conversational phrases
- ✅ **Memorable**: Short, associated with product name (GiljoAI)
- ✅ **Extensible**: Easy to add new commands in the future

**Example of ambiguity without prefix**:
```
User: "I think we should create a quick task for refactoring"
→ Without prefix: Claude might think this is a command
→ With /gil-quick-task: Clear intent to create a task
```

---

## Architecture

### How Slash Commands Work

Claude Code's slash command system works by loading markdown files from `~/.claude/commands/`:

1. **Command Definition**: Markdown file with instructions (e.g., `gil-quick-task.md`)
2. **User Invocation**: User types `/gil-quick-task fix the login bug`
3. **Prompt Expansion**: Claude Code reads the markdown file and appends user input
4. **Agent Execution**: Claude processes the expanded prompt and executes MCP tools
5. **Result**: Task created, agent messaged, or orchestration started

### Command Flow Diagram

```
User types /gil-smart-task → Claude Code reads gil-smart-task.md
                           ↓
              Markdown contains instructions for Claude
                           ↓
              Claude analyzes conversation history
                           ↓
              Claude calls mcp__giljo-mcp__create_task
                           ↓
              Task created with rich context
                           ↓
              User receives confirmation
```

---

## Implementation

### File Structure

```
.claude/
└── commands/
    ├── README.md                  # User-facing documentation
    ├── gil-quick-task.md          # Simple task creation
    ├── gil-smart-task.md          # Context-aware task creation
    ├── gil-message.md             # Agent messaging with fuzzy matching
    ├── gil-run.md                 # Project orchestration launcher
    ├── gil-status.md              # Project status display
    ├── gil-agents.md              # Agent list display
    └── gil-tasks.md               # Task list display
```

### Command Implementation Pattern

Each command follows this structure:

```markdown
# Command Title

Brief description of what this command does.

## Input Format
{{prompt}}  ← User's input after the slash command

## Instructions
Step-by-step instructions for Claude to execute:
1. Parse user input
2. Call appropriate MCP tools
3. Present results to user
4. Provide confirmation

## Examples
Show example usage
```

---

## Available Commands

### 1. `/gil-quick-task` - Simple Task Creation

## Setup (0093)

Before using commands, ensure your environment is configured:

- Confirm GiljoAI server URL and authentication (Settings → API & Integrations)
- Install slash commands via Integrations UI (download ZIP) or run the install script
- Optionally, install via MCP tool: `/gil_import_personalagents` and `/gil_import_productagents`
- Verify commands appear in your CLI help list

**Purpose**: Fast task capture without context analysis.

**Usage**:
```
/gil-quick-task Fix the dashboard layout on mobile
```

**What It Does**:
- Creates task with exact description provided
- Sets default priority: "medium"
- No conversation analysis
- Assigns to: unassigned

**Implementation** (`gil-quick-task.md`):
```markdown
# Quick Task Creation

Create a simple task with the provided description using the GiljoAI MCP system.

## Task Description
{{prompt}}

## Instructions
Use the `mcp__giljo-mcp__create_task` tool to create a task with:
- **title**: Extract a concise title from the description (max 10 words)
- **description**: The full description provided above
- **priority**: "medium" (default)
- **assigned_to**: "" (unassigned)

After creating the task, confirm to the user with the task ID.
```

**Example Code Flow**:
```javascript
// User types: /gil-quick-task Refactor authentication logic

// Claude receives expanded prompt:
"Create a simple task with the provided description...
Task Description: Refactor authentication logic
...instructions..."

// Claude executes:
mcp__giljo-mcp__create_task({
  title: "Refactor authentication logic",
  description: "Refactor authentication logic",
  priority: "medium",
  assigned_to: ""
})

// User sees:
"✓ Task created: #TASK-123 - Refactor authentication logic"
```

---

### 2. `/gil-smart-task` - Context-Aware Task Creation

**Purpose**: Create detailed tasks by analyzing recent conversation history.

**Usage**:
```
/gil-smart-task the connection pooling refactor we discussed
/gil-smart-task bullets 3, 5, and 8 from earlier
```

**What It Does**:
- Analyzes last 20-30 messages of conversation
- Extracts technical details, file paths, code snippets
- Identifies WHY the task is needed (technical debt, feature, bug)
- Creates comprehensive task description with context
- Infers priority from conversation urgency

**Implementation** (`gil-smart-task.md`):
```markdown
# Smart Task Creation with Context

Create a detailed, context-aware task by analyzing the recent conversation.

## Task Reference
{{prompt}}

## Instructions

1. **Analyze the conversation**: Review the last 20-30 messages
2. **Extract context**: Identify what, why, when, and specific details
3. **Create detailed task**: Use `mcp__giljo-mcp__create_task` with:
   - **title**: Clear, action-oriented (max 80 chars)
   - **description**: Comprehensive with:
     - Summary of what needs to be done
     - Context from conversation
     - Why it's needed
     - Relevant file paths/technical details
     - Reference: "Discussed on [date] during [context]"
   - **priority**: Infer from context (high/medium/low)
   - **assigned_to**: "" (unassigned)

Be thorough but concise.
```

**Example Code Flow**:
```javascript
// Conversation history:
// [10 messages ago] User: "The database connection pool is inefficient"
// [8 messages ago] Claude: "We could use PgBouncer or implement custom pooling"
// [5 messages ago] User: "Let's implement custom pooling in db_manager.py"
// [3 messages ago] Claude: "That would require refactoring the connection logic"

// User types: /gil-smart-task the connection pooling refactor

// Claude analyzes conversation and creates:
mcp__giljo-mcp__create_task({
  title: "Refactor database connection pooling in db_manager.py",
  description: `Implement custom connection pooling to improve database performance.

**Context**: During performance optimization discussion on Oct 6, 2025, identified
that current connection pooling is inefficient and causing delays.

**Technical Details**:
- File: src/giljo_mcp/database/db_manager.py
- Replace basic connection logic with connection pool
- Target: <50ms query performance
- Consider: Thread safety, connection limits, timeout handling

**Why Needed**: Technical debt - current implementation creates new connections
for each query, causing 200-300ms overhead.

**Reference**: Discussed during database optimization session, Oct 6 2025`,
  priority: "medium",
  assigned_to: ""
})

// User sees detailed task with full context
```

**Reasoning Behind Smart Task**:

The "smart task" capability solves a critical problem in software development: **context loss**.

During active coding sessions:
- ✅ Ideas emerge mid-conversation
- ✅ Technical debt is identified
- ✅ Important details are discussed but not documented
- ❌ Writing detailed task descriptions breaks flow
- ❌ Context is lost if not captured immediately

**Smart task captures**:
1. **What**: Extracts the specific work item from conversation
2. **Why**: Preserves the reasoning and motivation
3. **When**: Timestamps the discussion for future reference
4. **How**: Includes technical details, file paths, code patterns discussed

This creates **actionable, self-contained tasks** that someone (including future you) can pick up without re-reading entire conversation history.

---

### 3. `/gil-message` - Agent Communication

**Purpose**: Send messages to agents using fuzzy name matching.

**Usage**:
```
/gil-message database don't forget to add indexes for user table
/gil-message doc agent update the API endpoints documentation
```

**What It Does**:
- Fuzzy matches agent name (e.g., "db" → "database-expert")
- Sends message to matched agent
- Confirms delivery

**Implementation** (`gil-message.md`):
```markdown
# Send Message to Agent

Send a message to a specific agent using fuzzy name matching.

## Command Format
{{prompt}}

## Instructions

1. **Parse input**: Extract agent name (first word/phrase) and message content
2. **Find agent**: Use `mcp__giljo-mcp__list_agents` and fuzzy match
   - "db" matches "database-expert"
   - "doc" matches "documentation-agent"
3. **Send message**: Use `mcp__giljo-mcp__send_message`:
   - **from_agent**: "user"
   - **to_agent**: Matched agent ID
   - **content**: Parsed message content
   - **message_type**: "instruction"
4. **Confirm**: Tell user which agent received the message
```

**Example Code Flow**:
```javascript
// User types: /gil-message database add indexes to user table

// Claude parses:
const agentName = "database"
const messageContent = "add indexes to user table"

// Claude calls:
const agents = mcp__giljo-mcp__list_agents({ status: "" })

// Fuzzy match: "database" → finds "database-expert-agent"
const matched = agents.find(a =>
  a.name.toLowerCase().includes("database") ||
  a.role.toLowerCase().includes("database")
)

// Send message:
mcp__giljo-mcp__send_message({
  from_agent: "user",
  to_agent: matched.id,
  content: "add indexes to user table",
  message_type: "instruction"
})

// User sees:
"✓ Message sent to: database-expert-agent
   Content: 'add indexes to user table'"
```

**Fuzzy Matching Logic**:
```javascript
function fuzzyMatchAgent(input, agents) {
  const normalized = input.toLowerCase()

  // Priority 1: Exact name match
  let match = agents.find(a => a.name.toLowerCase() === normalized)
  if (match) return match

  // Priority 2: Exact role match
  match = agents.find(a => a.role.toLowerCase() === normalized)
  if (match) return match

  // Priority 3: Name contains input
  match = agents.find(a => a.name.toLowerCase().includes(normalized))
  if (match) return match

  // Priority 4: Role contains input
  match = agents.find(a => a.role.toLowerCase().includes(normalized))
  if (match) return match

  // Priority 5: Input contains name/role (partial match)
  match = agents.find(a =>
    normalized.includes(a.name.toLowerCase()) ||
    normalized.includes(a.role.toLowerCase())
  )

  return match || null
}
```

---

### 4. `/gil-run` - Project Orchestration

**Purpose**: Activate project and start multi-agent orchestration.

**Usage**:
```
/gil-run Authentication System
/gil-run proj_abc123
```

**What It Does**:
- Finds project by name or ID
- Switches to project context
- Lists all agents
- Puts Claude in orchestrator mode
- Ready to coordinate work

**Implementation** (`gil-run.md`):
```markdown
# Run GiljoAI Project with Full Orchestration

Activate a project and start multi-agent orchestration directly in CLI.

## Project Identifier
{{prompt}}

## Instructions

1. **Find project**: Use `mcp__giljo-mcp__list_projects`, fuzzy match name/ID
2. **Activate project**: ⚠️ Project activation is done via web UI (Handover 0388 removed CLI activation)
3. **Get agents**: Use `mcp__giljo-mcp__list_agents`
4. **Start orchestration**: Present summary and enter orchestrator mode

Present:
```
🚀 Starting GiljoAI Project: [Name]
Mission: [Mission]
Active Agents: [Count]
- [Agent 1] (Role) - [mission]
...
Ready to coordinate work.
```
```

**Example Code Flow**:
```javascript
// User types: /gil-run Authentication System

// Claude searches projects:
const projects = mcp__giljo-mcp__list_projects({ status: "active" })
const project = projects.find(p =>
  p.name.toLowerCase().includes("authentication")
)

// NOTE: Project activation is done via web UI (Handover 0388)
// Projects must be activated in the dashboard before CLI orchestration

// Get agents:
const agents = mcp__giljo-mcp__list_agents({ status: "active" })

// Display orchestration summary:
console.log(`
🚀 Starting GiljoAI Project: Authentication System

Mission: Build JWT-based authentication with user management

Active Agents: 3
- database-agent (database) - Design auth schema with users and tokens tables
- backend-agent (backend) - Implement JWT auth endpoints
- tester-agent (testing) - Create integration tests for auth flow

Ready to coordinate work. What would you like to accomplish?
`)
```

---

### 5. `/gil-status` - Project Status Display

**Purpose**: Show current project, agents, and tasks at a glance.

**Usage**:
```
/gil-status
```

**What It Does**:
- Shows active project and mission
- Lists all agents with status
- Shows task counts (pending, in progress, completed)
- Highlights recent activity

**Implementation** (`gil-status.md`):
```markdown
# Show GiljoAI Project Status

Display current project status, agents, and tasks.

## Instructions

1. **Get project**: `mcp__giljo-mcp__list_projects` (active)
2. **Get agents**: `mcp__giljo-mcp__list_agents` (all statuses)
3. **Get tasks**:
   - `mcp__giljo-mcp__list_tasks` (status="pending")
   - `mcp__giljo-mcp__list_tasks` (status="in_progress")
   - Count completed tasks if available
4. **Present summary** with project, agents, tasks, recent activity
```

---

### 6. `/gil-agents` - Agent List Display

**Purpose**: List all agents in current project with details.

**Usage**:
```
/gil-agents
```

**What It Does**:
- Lists all agents (active, idle, retired)
- Shows role, status, mission, ID
- Highlights agents with pending messages

---

### 7. `/gil-tasks` - Task List Display

**Purpose**: List all tasks organized by status.

**Usage**:
```
/gil-tasks
```

**What It Does**:
- Shows tasks grouped by status
- Sorted by priority within each group
- Shows assignee, description preview, task IDs

---

## Installation

### Manual Installation (Current)

1. **Create commands directory**:
   ```bash
   mkdir -p ~/.claude/commands
   ```

2. **Copy command files**:
   ```bash
   cp C:/Projects/GiljoAI_MCP/.claude/commands/*.md ~/.claude/commands/
   ```

3. **Verify installation**:
   ```bash
   ls ~/.claude/commands/
   # Should see: gil-*.md files
   ```

4. **Test in Claude Code**:
   ```bash
   claude code
   # Type: /gil-quick-task Test task
   ```

### Automated Installation (Future)

**Option A: CLI Installer**
```python
# installer/core/installer.py

def install_claude_commands(self):
    """Copy slash commands to user's Claude Code directory."""
    source = Path("C:/Projects/GiljoAI_MCP/.claude/commands")
    target = Path.home() / ".claude" / "commands"

    target.mkdir(parents=True, exist_ok=True)

    for cmd_file in source.glob("gil-*.md"):
        shutil.copy(cmd_file, target / cmd_file.name)

    print(f"✓ Installed {len(list(source.glob('gil-*.md')))} slash commands")
```

**Option B: Frontend Setup Wizard** (Phase 0.5)
```vue
<!-- Step 3: AI Coding Agent Integration -->
<template>
  <v-card>
    <v-card-title>Configure Claude Code Commands</v-card-title>
    <v-card-text>
      <v-btn @click="installSlashCommands" :loading="installing">
        Install GiljoAI Slash Commands
      </v-btn>
      <v-alert v-if="installed" type="success">
        ✓ 7 slash commands installed to ~/.claude/commands/
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script>
async installSlashCommands() {
  const response = await fetch('/api/setup/install-claude-commands', {
    method: 'POST'
  })
  this.installed = response.ok
}
</script>
```

---

## Usage Examples

### Example 1: Technical Debt Capture

**Scenario**: During code review, you realize the error handling needs improvement.

```
[Conversation about authentication]
User: "The error handling in login() is inconsistent"
Claude: "Yes, some paths return HTTP 500, others 401..."

User: /gil-smart-task fix error handling inconsistencies
Claude: ✓ Created task #TASK-456
       Title: "Standardize error handling in authentication login()"
       Description: "During code review on Oct 6, identified that login()
                     in auth.py returns inconsistent HTTP status codes..."
       Priority: medium
```

**Why this works**:
- ✅ Doesn't break conversation flow
- ✅ Captures context automatically
- ✅ Creates actionable task for later
- ✅ Prevents scope creep in current session

---

### Example 2: Agent Coordination

**Scenario**: Database schema is ready, backend needs to implement endpoints.

```
User: /gil-status
Claude:
📊 GiljoAI Project Status
Current Project: E-Commerce API
Agents:
- database-agent (completed) - Schema deployed
- backend-agent (idle) - Waiting for work
- frontend-agent (idle) - Waiting for API

User: /gil-message backend implement the checkout endpoints, schema is ready
Claude: ✓ Message sent to backend-agent
        Content: "implement the checkout endpoints, schema is ready"

[Backend agent receives message and begins work]
```

---

### Example 3: Quick Capture During Meeting

**Scenario**: Product owner mentions a feature request during standup.

```
[During meeting discussion]
Product Owner: "Users are asking for export to CSV"

User: /gil-quick-task Add CSV export for transaction history
Claude: ✓ Task created #TASK-789 - Add CSV export for transaction history

[Continue meeting without interruption]
```

---

## Design Decisions

### Why Separate Quick vs Smart Task?

**Quick Task** (`/gil-quick-task`):
- **Use case**: Rapid capture during meetings, simple todos
- **Speed**: Instant, no analysis
- **Context**: None, just the text provided
- **Example**: "Fix typo in README"

**Smart Task** (`/gil-smart-task`):
- **Use case**: Technical debt, discussed improvements
- **Speed**: 2-5 seconds (conversation analysis)
- **Context**: Rich, with history and reasoning
- **Example**: "That refactoring we discussed 10 minutes ago"

**Trade-off**: Two commands vs. one smart command
- ❌ More commands to remember
- ✅ User control over speed vs. detail
- ✅ Quick capture doesn't force waiting
- ✅ Smart capture available when needed

### Why Fuzzy Matching for Agents?

**Problem**: Agent names can be verbose
- `database-expert-agent-for-authentication`
- `backend-implementation-specialist`

**Solution**: Fuzzy matching
```
/gil-message db ...     → database-expert-agent
/gil-message backend ...  → backend-implementation-specialist
/gil-message doc ...     → documentation-agent
```

**Implementation Strategy**:
1. Try exact match first (fast path)
2. Try substring match (most common)
3. Try partial match (flexible)
4. Ask user if multiple matches

### Why `/gil-run` Instead of Copy/Paste Prompt?

**Old Workflow**:
1. Open dashboard
2. Click "Activate Project"
3. Copy prompt to clipboard
4. Switch to terminal
5. Paste into Claude Code

**New Workflow**:
```
/gil-run Authentication System
```

**Benefits**:
- ✅ Single command
- ✅ No context switching
- ✅ No clipboard management
- ✅ Faster by 4 steps

---

## Testing

### Manual Testing Checklist

```
□ /gil-quick-task creates task successfully
□ /gil-smart-task analyzes conversation correctly
□ /gil-message finds agent with fuzzy match
□ /gil-run activates project and lists agents
□ /gil-status shows current project state
□ /gil-agents lists all agents
□ /gil-tasks shows tasks by status
□ All commands handle errors gracefully
□ All commands provide user feedback
```

### Automated Testing

**Unit Tests** (`tests/unit/test_slash_commands.py`):
```python
def test_fuzzy_agent_matching():
    """Test fuzzy matching for agent names."""
    agents = [
        Agent(name="database-expert-agent", role="database"),
        Agent(name="backend-developer-agent", role="backend"),
    ]

    assert fuzzy_match("db", agents) == agents[0]
    assert fuzzy_match("database", agents) == agents[0]
    assert fuzzy_match("backend", agents) == agents[1]
    assert fuzzy_match("back", agents) == agents[1]
```

**Integration Tests** (`tests/integration/test_slash_commands.py`):
```python
def test_gil_quick_task_e2e():
    """Test quick task creation end-to-end."""
    # Simulate slash command invocation
    result = execute_command("/gil-quick-task Fix login bug")

    assert result.success
    assert "task_id" in result
    assert result.message == "Task created successfully"

    # Verify task in database
    task = get_task(result.task_id)
    assert task.title == "Fix login bug"
    assert task.priority == "medium"
```

---

## Troubleshooting

### Command Not Found

**Problem**: `/gil-quick-task` shows "Command not found"

**Solution**:
```bash
# Check if command files exist
ls ~/.claude/commands/gil-*.md

# If missing, copy them
cp C:/Projects/GiljoAI_MCP/.claude/commands/*.md ~/.claude/commands/
```

### Command Doesn't Execute

**Problem**: Command recognized but nothing happens

**Solution**:
1. Check MCP server is running: `curl http://localhost:7272/health`
2. Verify Claude Code can access MCP tools
3. Check logs: `tail -f ~/.claude/logs/claude-code.log`

### Fuzzy Match Returns Wrong Agent

**Problem**: `/gil-message back` sends to wrong agent

**Solution**:
- Use more specific match: `/gil-message backend`
- Or use full agent name
- Check available agents: `/gil-agents`

---

## Future Enhancements

### Planned Features

1. **`/gil-assign <task_id> <agent>`**: Assign task to agent
   ```
   /gil-assign TASK-123 database-agent
   ```

2. **`/gil-complete <task_id>`**: Mark task as complete
   ```
   /gil-complete TASK-123
   ```

3. **`/gil-archive`**: Archive completed tasks
   ```
   /gil-archive older than 30 days
   ```

4. **`/gil-report`**: Generate status report
   ```
   /gil-report weekly
   ```

### Community Commands

Users can create custom commands by adding markdown files to `~/.claude/commands/`:

**Example**: Custom bug triage command
```markdown
# Bug Triage

Analyze the bug described and create a prioritized task.

## Bug Description
{{prompt}}

## Instructions
1. Assess severity (critical/high/medium/low)
2. Identify affected components
3. Create task with appropriate priority
4. Suggest investigation steps
```

Save as `~/.claude/commands/gil-triage-bug.md`

Usage: `/gil-triage-bug User login fails on mobile Safari`

---

## Contributing

To add new slash commands:

1. **Create markdown file**: `~/.claude/commands/gil-yourcommand.md`
2. **Follow pattern**: Use `{{prompt}}` for user input
3. **Write instructions**: Clear steps for Claude to execute
4. **Test**: Verify command works in Claude Code
5. **Document**: Add to this guide
6. **Submit PR**: Share with community

---

## References

- **Command Files**: `.claude/commands/gil-*.md`
- **Implementation Plan**: `docs/IMPLEMENTATION_PLAN.md`
- **MCP Tools Manual**: `docs/manuals/MCP_TOOLS_MANUAL.md`
- **User Guide**: `docs/guides/USER_GUIDE.md`

---

## Changelog

### Version 1.0 (October 6, 2025)
- ✅ Initial release
- ✅ 7 core commands implemented
- ✅ Quick task and smart task distinction
- ✅ Fuzzy agent matching
- ✅ Project orchestration support
- ✅ Status and list commands

---

**End of Slash Commands Documentation**
### X. `/gil_handover` (alias: `/gil-handover`) — Simple Session Handover

Purpose: Reset orchestrator context via 360 Memory when running out of context (Handover 0461c).

Usage:
```
/gil_handover
/gil_handover <ORCHESTRATOR_JOB_ID>
```

What it does:
- Writes current session context to 360 Memory (session_handover entry)
- Returns a continuation prompt that instructs reading 360 Memory
- Emits WebSocket event for UI updates

Events:
- `orchestrator:context_reset` (context reset complete)

See also:
- `docs/features/360_MEMORY_MANAGEMENT.md`
- `handovers/0461c_backend_simplification.md`
