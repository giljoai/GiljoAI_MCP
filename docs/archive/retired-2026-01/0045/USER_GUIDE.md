# Multi-Tool Agent Orchestration - User Guide

**Version**: 3.1.0
**Last Updated**: 2025-10-25
**Audience**: GiljoAI MCP End Users, Project Managers, Team Leads

---

## Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Tool Selection Guide](#tool-selection-guide)
4. [Template Configuration](#template-configuration)
5. [Spawning Agents](#spawning-agents)
6. [Job Queue Dashboard](#job-queue-dashboard)
7. [MCP Coordination Protocol](#mcp-coordination-protocol)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)
10. [FAQ](#faq)

---

## Introduction

### What is Multi-Tool Orchestration?

GiljoAI MCP v3.1 introduces revolutionary multi-tool agent orchestration - the ability to orchestrate AI agents across different AI coding tools within a single project. This is the first system in the industry to enable seamless coordination between Claude Code, Codex, and Gemini CLI agents working on the same codebase.

**Traditional Approach**:
```
One Project → One AI Tool → Limited by that tool's constraints
```

**GiljoAI Multi-Tool Approach**:
```
One Project → Multiple AI Tools → Best tool for each task
```

### Benefits

**1. Cost Optimization (40-60% Savings)**
- Mix free and paid tiers strategically
- Route simple tasks to free tools (Gemini)
- Reserve premium tools (Claude Opus) for complex tasks
- Real-world savings: $500/month → $200/month for typical teams

**2. Rate Limit Resilience**
- Hit Claude's rate limit? Switch to Codex instantly
- Distribute load across multiple API keys
- Never block on rate limits again
- Continue work 24/7 without interruption

**3. Capability-Based Task Routing**
- Frontend tasks → Gemini (optimized for Google frameworks)
- Backend logic → Claude Code (best reasoning)
- Data processing → Codex (fast iteration)
- Match task to tool strength

**4. Vendor Independence**
- No lock-in to single AI provider
- Migrate between tools seamlessly
- Hedge against API changes or price increases
- Future-proof your workflow

### Supported Tools

GiljoAI MCP v3.1 supports three AI coding tools:

| Tool | Best For | Pricing | Speed | Quality |
|------|----------|---------|-------|---------|
| **Claude Code** | Complex reasoning, architecture design, hybrid mode with automatic subagent spawning | Paid ($20/mo Pro) | Medium | Excellent |
| **Codex (OpenAI)** | Cost-conscious teams, rapid iteration, OpenAI ecosystem | Free/Paid (ChatGPT Plus) | Fast | Good |
| **Gemini CLI** | Google ecosystem, frontend development, free tier | Free/Paid | Very Fast | Good |

**Hybrid Mode** (Claude Code only):
- Agents run inside Claude Code
- Automatic subagent spawning
- No manual prompt copying
- Real-time coordination via MCP

**Legacy CLI Mode** (Codex/Gemini):
- Copy-paste prompt into CLI tool
- Manual checkpointing via MCP
- Full coordination without IDE integration

---

## Quick Start

Get started with multi-tool orchestration in 5 minutes:

### Prerequisites

**Required**:
- GiljoAI MCP v3.1+ installed
- PostgreSQL 18 running
- Access to at least one AI coding tool

**AI Tool Setup** (choose at least one):
- **Claude Code**: Install Claude Code CLI, configure MCP server
- **Codex**: Install OpenAI Codex CLI, sign in with API key
- **Gemini**: Install Gemini CLI, authenticate with Google account

**For detailed AI tool setup**, see [Admin Settings → Integrations Tab](../../manuals/ADMIN_SETTINGS.md#integrations-tab).

### Step 1: Configure Template Tool Assignment

1. **Open GiljoAI Dashboard**:
   ```
   http://localhost:7274
   ```

2. **Navigate to Templates**:
   - Click "Templates" in left sidebar
   - You'll see 6 agent templates (Orchestrator, Analyzer, Implementer, Tester, Reviewer, Documenter)

3. **Select Tool for Each Agent**:
   - Click "Edit" on the Implementer template
   - Scroll to "Preferred Tool" dropdown
   - Select your tool: `claude` (default), `codex`, or `gemini`
   - Click "Save"

4. **Repeat for Other Templates**:
   - Configure tool for each agent role
   - Mix and match tools based on task type
   - Example strategy:
     - Orchestrator: `claude` (complex coordination)
     - Analyzer: `claude` (deep reasoning)
     - Implementer: `codex` (fast iteration)
     - Tester: `gemini` (parallel test generation)
     - Reviewer: `claude` (quality assurance)
     - Documenter: `gemini` (documentation generation)

### Step 2: Spawn Your First Multi-Tool Project

1. **Create New Project**:
   - Dashboard → "Projects" tab
   - Click "+ New Project"
   - Fill in project details (name, description, vision)
   - Click "Create"

2. **Spawn Agents**:
   - Open project details
   - Click "Spawn Agents"
   - System automatically spawns agents based on template configuration
   - Each agent uses its configured tool

3. **Monitor Agent Status**:
   - Dashboard shows agent cards
   - **Claude Code agents**: Status badge shows "Running in Claude Code"
   - **Codex/Gemini agents**: Status badge shows "Waiting for CLI" with "Copy Prompt" button

### Step 3: Work with Agents

**For Claude Code Agents** (Hybrid Mode):
- No action needed - agents run automatically
- View progress in Claude Code interface
- Agents checkpoint progress via MCP

**For Codex/Gemini Agents** (Legacy CLI Mode):
1. Click "Copy Prompt" button on agent card
2. Open your CLI tool (Codex or Gemini)
3. Paste prompt and press Enter
4. Agent starts working, checkpoints progress via MCP
5. Return to dashboard to see status updates

### Step 4: View Results

- Navigate to "Job Queue" tab
- View all agent jobs in real-time
- Filter by status, tool, or agent
- Click job to see detailed progress
- Review completed work in your codebase

**Congratulations!** You've successfully orchestrated agents across multiple AI tools.

---

## Tool Selection Guide

Choosing the right tool for each agent role maximizes quality, speed, and cost-efficiency.

### When to Use Claude Code

**Best For**:
- Complex architectural decisions
- System design and planning
- Code reviews requiring deep analysis
- Tasks needing strong reasoning
- Multi-step workflows
- Automatic subagent spawning (hybrid mode)

**Strengths**:
- Excellent reasoning and planning
- Best-in-class code understanding
- Automatic coordination via MCP
- No manual prompt copying (hybrid mode)
- Strong security and privacy

**Weaknesses**:
- Paid only ($20/month Pro)
- Slower than Codex/Gemini
- Rate limits on free tier (if available)

**Recommended Roles**:
- **Orchestrator**: Ideal - complex coordination
- **Analyzer**: Ideal - deep architecture analysis
- **Reviewer**: Ideal - thorough code review

**Example**:
```
Template: Orchestrator
Preferred Tool: claude
Rationale: Orchestrator needs to make complex decisions about
           agent coordination and task delegation. Claude's
           reasoning capability is essential.
```

### When to Use Codex (OpenAI)

**Best For**:
- Rapid code iteration
- Implementation tasks
- Data processing scripts
- Testing and validation
- Teams already using OpenAI ecosystem
- Cost-conscious teams (ChatGPT Plus $20/mo = unlimited)

**Strengths**:
- Very fast response times
- Familiar to ChatGPT users
- Good code generation quality
- Strong ecosystem integration
- Unlimited with ChatGPT Plus

**Weaknesses**:
- Manual CLI workflow (copy-paste prompts)
- Requires manual checkpointing
- Less sophisticated reasoning than Claude
- OpenAI API rate limits (if using API directly)

**Recommended Roles**:
- **Implementer**: Ideal - fast code generation
- **Tester**: Good - parallel test writing
- **Documenter**: Good - documentation generation

**Example**:
```
Template: Implementer
Preferred Tool: codex
Rationale: Implementer needs to write code quickly. Codex's
           speed and unlimited tier (ChatGPT Plus) make it
           cost-effective for high-volume implementation.
```

### When to Use Gemini CLI

**Best For**:
- Google Cloud projects
- Frontend development (Angular, React)
- Free tier usage (cost = $0)
- High-volume parallel tasks
- Teams in Google ecosystem
- Experimentation and prototyping

**Strengths**:
- Free tier available (generous limits)
- Very fast response times
- Good for Google Cloud integration
- Strong frontend capabilities
- Excellent for parallel task execution

**Weaknesses**:
- Manual CLI workflow (copy-paste prompts)
- Requires manual checkpointing
- Less sophisticated reasoning
- Newer tool with evolving capabilities

**Recommended Roles**:
- **Tester**: Ideal - parallel test generation, free tier
- **Documenter**: Ideal - documentation at scale, free tier
- **Implementer**: Good - frontend implementation

**Example**:
```
Template: Tester
Preferred Tool: gemini
Rationale: Tester needs to generate many tests in parallel.
           Gemini's free tier and speed make it perfect for
           high-volume test generation without cost.
```

### Mixed Mode Strategies

Maximize value by mixing tools within a single project:

**Strategy 1: Quality-Speed Tradeoff**
```
Critical Path (Claude):
  - Orchestrator: claude (coordination)
  - Analyzer: claude (architecture)
  - Reviewer: claude (quality gates)

Fast Path (Codex/Gemini):
  - Implementer: codex (speed)
  - Tester: gemini (volume, free)
  - Documenter: gemini (volume, free)

Result: 60% cost reduction, minimal quality impact
```

**Strategy 2: Cost Optimization**
```
Premium Tasks (Claude Code - 20% of work):
  - Complex architecture decisions
  - Security-critical code reviews
  - Complex refactoring

Standard Tasks (Codex - 60% of work):
  - Feature implementation
  - Bug fixes
  - Testing

Bulk Tasks (Gemini - 20% of work):
  - Documentation generation
  - Test case expansion
  - Code formatting

Result: 40% cost reduction, strategic quality allocation
```

**Strategy 3: Rate Limit Resilience**
```
Primary Tool: Claude Code (best quality)
Backup Tool: Codex (rate limit overflow)
Emergency Tool: Gemini (both tools rate-limited)

Result: 100% uptime, never blocked on rate limits
```

### Tool Comparison Matrix

| Feature | Claude Code | Codex | Gemini |
|---------|-------------|-------|--------|
| **Reasoning Quality** | Excellent | Good | Good |
| **Code Generation Speed** | Medium | Fast | Very Fast |
| **Cost (per month)** | $20 | $20 (Plus) or Free | Free or Paid |
| **Rate Limits** | Moderate | High (Plus) | Very High |
| **Hybrid Mode Support** | Yes | No | No |
| **Manual Checkpointing** | Not needed | Required | Required |
| **Ecosystem Integration** | Anthropic | OpenAI | Google |
| **Security & Privacy** | Excellent | Good | Good |
| **Best For** | Architecture, Review | Implementation | Testing, Docs |

---

## Template Configuration

Configure which AI tool each agent role uses via the Template Manager.

### Accessing Template Manager

1. **Navigate**: Dashboard → Templates tab
2. **View**: List of 6 agent templates
3. **Search**: Filter templates by name or role

### Configuring Tool Assignment

**Step-by-Step**:

1. **Select Template**:
   - Click "Edit" on template (e.g., "Implementer")
   - Template editor opens

2. **Find Preferred Tool Setting**:
   - Scroll to metadata section (top of editor)
   - Locate "Preferred Tool" dropdown
   - Current value shown (default: `claude`)

3. **Change Tool**:
   - Click dropdown
   - Select new tool:
     - `claude` - Claude Code (hybrid mode)
     - `codex` - OpenAI Codex (legacy CLI mode)
     - `gemini` - Gemini CLI (legacy CLI mode)

4. **Save Changes**:
   - Click "Save" button
   - Template version increments
   - All future agents of this role use new tool
   - Existing agents unchanged (tool locked at spawn time)

5. **Verify**:
   - Template list shows updated "Preferred Tool" column
   - Spawn new agent to test configuration

### Tool-Specific Template Customization

Customize template behavior based on tool capabilities:

**Example: Implementer Template for Codex**
```markdown
# Behavioral Rules
1. Write production-quality code quickly (Codex strength: speed)
2. Use MCP checkpointing after each major change
3. Report progress every 15 minutes via report_progress
4. If blocked, use send_message to ask Orchestrator for help
5. Complete job with complete_job when done

# Success Criteria
1. Code compiles/runs without errors
2. All checkpoints reported to MCP
3. Implementation matches specification
4. Job marked as complete in MCP system

# MCP Integration (Critical for Legacy CLI Mode)
You are working in **Legacy CLI Mode** with MCP coordination.

**Required Workflow**:
1. Start: Call acknowledge_job to confirm you received the task
2. Progress: Call report_progress every 15 minutes with status update
3. Checkpoints: Call report_progress after each major milestone
4. Questions: Call send_message to communicate with Orchestrator
5. Completion: Call complete_job with final summary
6. Errors: Call report_error if you encounter blockers

Without MCP checkpoints, your work will not be tracked!
```

**Example: Implementer Template for Claude Code**
```markdown
# Behavioral Rules
1. Write production-quality code with strong reasoning
2. Automatic subagent spawning enabled (use when needed)
3. Coordinate with other agents via MCP messaging
4. Use symbolic operations (Serena MCP) for precision
5. Report progress automatically via MCP integration

# Success Criteria
1. Code meets architectural requirements
2. Strong reasoning documented in comments
3. Automatic coordination with other agents
4. Job tracked via MCP (automatic in hybrid mode)

# MCP Integration (Automatic in Hybrid Mode)
You are working in **Hybrid Mode** with automatic MCP coordination.

**Automatic Features**:
- Job acknowledgment: Automatic on agent spawn
- Progress reporting: Automatic every 10 minutes
- Checkpointing: Automatic after each tool use
- Messaging: Available via send_message MCP tool
- Completion: Automatic when you signal task done

You still CAN use MCP tools manually for explicit coordination:
- send_message: Communicate with other agents
- get_next_instruction: Request updated instructions from Orchestrator
- report_error: Escalate blockers
```

### Exporting Templates for Claude Code

Generate Claude Code-compatible template files for external use:

1. **Navigate**: Dashboard → Templates tab
2. **Export**: Click "Export for Claude Code" button
3. **Download**: ZIP file containing all templates
4. **Extract**: Unzip to `~/.config/claude-code/templates/`
5. **Verify**: Claude Code now uses your custom templates

**What's Exported**:
- All active templates (6 default roles)
- Product-specific templates (if any)
- MCP integration instructions
- Tool-specific configurations
- Behavioral rules and success criteria

**File Structure**:
```
templates/
├── orchestrator.md
├── analyzer.md
├── implementer.md
├── tester.md
├── reviewer.md
└── documenter.md
```

---

## Spawning Agents

Launch agents configured with different AI tools.

### Claude Code Agent Spawning (Hybrid Mode)

**Fully Automatic** - no manual steps required.

**Workflow**:
1. Click "Spawn Agent" → Select role (e.g., "Implementer")
2. System creates agent record with `mode = "claude"`
3. System generates mission prompt with MCP integration
4. Agent runs inside Claude Code automatically
5. Agent checkpoints progress via MCP (automatic)
6. Dashboard shows agent status in real-time

**Dashboard View**:
```
Agent: Implementer-001
Tool: Claude Code
Status: Running
Mode: Hybrid (automatic coordination)
Progress: 45% (last checkpoint: 2 minutes ago)
Actions: [View Details] [View Messages]
```

**Advantages**:
- Zero manual intervention
- Automatic progress tracking
- Real-time status updates
- Subagent spawning capability
- Best user experience

### Codex/Gemini Agent Spawning (Legacy CLI Mode)

**Semi-Manual** - requires copy-paste to CLI tool.

**Workflow**:

1. **System Spawns Agent**:
   - Click "Spawn Agent" → Select role (e.g., "Tester")
   - Template has `preferred_tool = "codex"` or `"gemini"`
   - System creates agent record with `mode = "codex"` or `"gemini"`
   - System creates MCP job record with status `"waiting_acknowledgment"`
   - System generates CLI prompt with MCP instructions

2. **User Copies Prompt**:
   - Dashboard shows agent card with **"Copy Prompt" button**
   - User clicks "Copy Prompt"
   - Full prompt copied to clipboard (includes mission + MCP integration)

3. **User Pastes to CLI**:
   - Open Codex CLI or Gemini CLI
   - Paste prompt and press Enter
   - Agent starts working in CLI environment

4. **Agent Acknowledges Job** (Manual MCP Call):
   - Agent's first action: Call `acknowledge_job` MCP tool
   - MCP server updates job status: `"waiting_acknowledgment"` → `"in_progress"`
   - Dashboard updates status badge: "Waiting for CLI" → "In Progress"

5. **Agent Works with Checkpointing**:
   - Agent performs task (writes code, generates tests, etc.)
   - Agent calls `report_progress` MCP tool every 15 minutes
   - Dashboard shows real-time progress updates
   - Agent uses `send_message` to communicate with Orchestrator

6. **Agent Completes Job**:
   - Agent calls `complete_job` MCP tool with summary
   - Job status: `"in_progress"` → `"completed"`
   - Dashboard shows completion badge
   - Agent decommissioned (status: `"active"` → `"decommissioned"`)

**Dashboard View**:
```
Agent: Tester-001
Tool: Gemini CLI
Status: In Progress
Mode: Legacy CLI (manual coordination)
Progress: 70% (last checkpoint: 5 minutes ago)
Actions: [View Details] [View Messages] [Copy Prompt]
```

**Important Notes**:
- **Must** call `acknowledge_job` first (or job stays in "waiting" state)
- **Should** call `report_progress` regularly (or dashboard shows stale status)
- **Must** call `complete_job` when done (or job never closes)
- Prompt includes all MCP instructions automatically

### Monitoring Agent Status

**Status Badges**:

| Status | Meaning | Next Action |
|--------|---------|-------------|
| **Waiting for CLI** | Prompt ready, agent not started | Copy prompt to CLI tool |
| **Waiting Acknowledgment** | Agent started, awaiting MCP acknowledgment | Agent should call acknowledge_job |
| **In Progress** | Agent working, checkpointing via MCP | Monitor progress, view messages |
| **Blocked** | Agent encountered error, needs help | Review error, send instructions |
| **Completed** | Agent finished successfully | Review work, mark job done |
| **Failed** | Agent encountered unrecoverable error | Review failure, respawn agent |
| **Running in Claude Code** | Hybrid mode agent active | No action needed (automatic) |

**Agent Cards**:
- **Tool Logo**: Visual indicator (Claude, OpenAI, Google)
- **Mode Badge**: "Hybrid" or "Legacy CLI"
- **Progress Bar**: % completion (based on checkpoints)
- **Last Checkpoint**: Time since last MCP update
- **Actions**: [View Details] [View Messages] [Copy Prompt (CLI only)]

**Real-Time Updates**:
- WebSocket-powered status updates
- No page refresh needed
- Automatic badge transitions
- Live progress bars

---

## Job Queue Dashboard

Monitor all agent jobs across all tools in a unified interface.

### Accessing Job Queue

1. **Navigate**: Dashboard → "Job Queue" tab
2. **View**: Real-time table of all jobs
3. **Filter**: By status, tool, agent, or date

### Dashboard Features

**Job Table Columns**:

| Column | Description | Example |
|--------|-------------|---------|
| **Job ID** | Unique job identifier | `job_abc123` |
| **Agent Name** | Agent assigned to job | `Implementer-001` |
| **Tool** | AI tool used | Claude / Codex / Gemini |
| **Mode** | Coordination mode | Hybrid / Legacy CLI |
| **Status** | Current job status | In Progress |
| **Progress** | Completion percentage | 65% |
| **Created** | Job creation timestamp | 2025-10-25 10:30 AM |
| **Updated** | Last checkpoint time | 5 minutes ago |
| **Actions** | Quick actions | [View] [Messages] |

**Statistics Panel**:
```
Total Jobs: 42
Active: 8
Completed: 30
Failed: 4

By Tool:
  Claude Code: 15 (35%)
  Codex: 18 (43%)
  Gemini: 9 (21%)

Avg Completion Time:
  Claude: 45 min
  Codex: 30 min
  Gemini: 25 min
```

### Filtering and Searching

**Status Filter**:
- All
- Waiting Acknowledgment
- In Progress
- Blocked
- Completed
- Failed

**Tool Filter**:
- All Tools
- Claude Code only
- Codex only
- Gemini only

**Date Range Filter**:
- Today
- Last 7 days
- Last 30 days
- Custom range

**Search**:
- Search by job ID
- Search by agent name
- Search by mission keywords

### Job Details View

Click any job to see detailed information:

**Job Overview**:
```
Job ID: job_abc123
Agent: Implementer-001
Tool: Codex
Mode: Legacy CLI
Status: In Progress
Created: 2025-10-25 10:30:15
Last Update: 2025-10-25 11:45:22 (2 minutes ago)

Mission:
"Implement user authentication with JWT tokens.
 Requirements: bcrypt hashing, token expiration,
 refresh token support."
```

**Progress Timeline**:
```
10:30 AM - Job created (status: waiting_acknowledgment)
10:32 AM - Agent acknowledged job (status: in_progress)
10:45 AM - Progress: "Implemented bcrypt password hashing" (20%)
11:15 AM - Progress: "Created JWT token generation logic" (50%)
11:45 AM - Progress: "Added refresh token endpoint" (80%)
12:00 PM - Job completed successfully
```

**Messages** (Agent-to-Orchestrator Communication):
```
11:20 AM - Implementer-001 → Orchestrator:
  "Question: Should token expiration be configurable or
   hard-coded to 24 hours?"

11:25 AM - Orchestrator → Implementer-001:
  "Make it configurable via environment variable.
   Default to 24 hours."

11:30 AM - Implementer-001 → Orchestrator:
  "Acknowledged. Implementing configurable expiration."
```

**Actions**:
- **View Full Mission**: See complete mission prompt
- **View Messages**: See all agent communication
- **Download Report**: Export job details to PDF
- **Retry Job**: Respawn agent for same task (if failed)

### Real-Time Monitoring

**WebSocket Updates**:
- Job status changes appear instantly
- Progress bar updates live
- Message notifications (toast popup)
- No manual refresh needed

**Event Types**:
```
job:status_changed - Job status updated
job:progress_updated - Progress percentage changed
job:message_received - New message from agent
job:completed - Job finished successfully
job:failed - Job encountered error
```

**Notifications**:
```
🟢 Job "Implement Auth" completed successfully
🔴 Job "Fix Bug #42" failed: "Database connection timeout"
💬 New message from Implementer-001
```

---

## MCP Coordination Protocol

Understand how agents coordinate via MCP (Model Context Protocol) tools.

### What is MCP Coordination?

MCP (Model Context Protocol) is the universal coordination layer that allows agents using different AI tools to communicate, report progress, and receive instructions.

**Key Concepts**:

1. **Job Record**: Database entry linking Agent → Task → Status
2. **Checkpoints**: Progress reports sent to MCP server
3. **Messages**: Inter-agent communication via MCP
4. **Instructions**: Dynamic task updates from Orchestrator
5. **Status Sync**: Event-driven synchronization (Agent ↔ Job)

**Architecture**:
```
Agent (any tool) → MCP Tools → GiljoAI Server → Database → Dashboard
     ↓                                                        ↑
     └────────────── WebSocket Events ──────────────────────┘
```

### MCP Tools Available to Agents

All agents (Claude Code, Codex, Gemini) have access to 7 MCP coordination tools:

#### 1. get_pending_jobs

**Purpose**: Retrieve jobs assigned to this agent that are waiting to be started.

**When to Use**:
- Agent starts up (first action)
- Agent finishes one job and looks for next task

**Parameters**:
```json
{
  "agent_id": "agent_abc123",
  "tenant_key": "tenant_xyz"
}
```

**Response**:
```json
{
  "jobs": [
    {
      "job_id": "job_001",
      "mission": "Implement user authentication",
      "priority": "high",
      "created_at": "2025-10-25T10:30:00Z"
    }
  ]
}
```

**Usage in Agent**:
```
At startup:
1. Call get_pending_jobs to see if there are any tasks assigned
2. If jobs found, pick highest priority job
3. Call acknowledge_job to start working
```

#### 2. acknowledge_job

**Purpose**: Confirm that agent has received the job and is starting work.

**When to Use**:
- **FIRST action** after receiving job (critical!)
- Changes job status: `waiting_acknowledgment` → `in_progress`

**Parameters**:
```json
{
  "job_id": "job_001",
  "agent_id": "agent_abc123",
  "tenant_key": "tenant_xyz"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Job acknowledged, status updated to in_progress"
}
```

**Dashboard Impact**:
- Status badge: "Waiting for CLI" → "In Progress"
- Progress bar appears (0%)
- "Last checkpoint" timer starts

**Critical**: Without acknowledgment, job stays in "waiting" state indefinitely!

#### 3. report_progress

**Purpose**: Report progress checkpoint to MCP server.

**When to Use**:
- Every 15 minutes (recommended for Legacy CLI mode)
- After each major milestone (e.g., "Database schema created")
- When % completion changes significantly (e.g., 25% → 50%)

**Parameters**:
```json
{
  "job_id": "job_001",
  "progress_data": {
    "percentage": 50,
    "message": "JWT token generation implemented",
    "details": "Created token signing and verification logic"
  }
}
```

**Response**:
```json
{
  "success": true,
  "message": "Progress reported successfully"
}
```

**Dashboard Impact**:
- Progress bar updates to 50%
- "Last checkpoint" resets to "just now"
- Timeline entry added: "11:45 AM - Progress: JWT token generation implemented (50%)"

**Best Practice**: Report progress frequently to provide visibility.

#### 4. get_next_instruction

**Purpose**: Request updated instructions from Orchestrator (dynamic task updates).

**When to Use**:
- Task requirements change mid-execution
- Agent needs clarification on ambiguous requirements
- Orchestrator sends message to agent

**Parameters**:
```json
{
  "job_id": "job_001",
  "tenant_key": "tenant_xyz"
}
```

**Response**:
```json
{
  "instruction": "Updated requirement: Token expiration should be configurable via environment variable. Default to 24 hours.",
  "from_agent": "Orchestrator-001",
  "timestamp": "2025-10-25T11:25:00Z"
}
```

**Usage in Agent**:
```
If Orchestrator sends a message:
1. Call get_next_instruction to retrieve the message
2. Read updated requirements
3. Adjust implementation accordingly
4. Report progress with acknowledgment
```

#### 5. complete_job

**Purpose**: Mark job as successfully completed.

**When to Use**:
- **LAST action** after finishing all work
- All success criteria met
- Code tested and validated

**Parameters**:
```json
{
  "job_id": "job_001",
  "summary": "User authentication implemented successfully. Features: bcrypt password hashing, JWT token generation, refresh token support, configurable expiration. All tests passing.",
  "tenant_key": "tenant_xyz"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Job marked as completed"
}
```

**Dashboard Impact**:
- Status badge: "In Progress" → "Completed"
- Progress bar: 100%
- Agent status: `active` → `decommissioned`
- Job appears in "Completed" filter
- Completion notification sent

**Critical**: Without calling complete_job, job stays "in progress" forever!

#### 6. report_error

**Purpose**: Report critical error that blocks job completion.

**When to Use**:
- Encountered unrecoverable error
- Missing dependencies or resources
- Task requirements impossible to meet
- Need Orchestrator intervention

**Parameters**:
```json
{
  "job_id": "job_001",
  "error_details": {
    "error_type": "dependency_missing",
    "message": "Cannot implement JWT auth - 'jsonwebtoken' package not found in dependencies",
    "stack_trace": "...",
    "recovery_suggestion": "Add 'jsonwebtoken' to package.json or use alternative library"
  },
  "tenant_key": "tenant_xyz"
}
```

**Response**:
```json
{
  "success": true,
  "message": "Error reported, job marked as failed"
}
```

**Dashboard Impact**:
- Status badge: "In Progress" → "Failed"
- Error notification sent (red toast)
- Error details visible in job details
- Orchestrator notified for intervention

**Recovery**:
- Orchestrator reviews error
- Orchestrator fixes issue (e.g., adds dependency)
- Orchestrator respawns agent for retry

#### 7. send_message

**Purpose**: Send message to another agent (typically Orchestrator).

**When to Use**:
- Ask question about requirements
- Request clarification on ambiguous task
- Report blocker that needs Orchestrator decision
- Coordinate with other agents

**Parameters**:
```json
{
  "from_agent_id": "agent_abc123",
  "to_agent_id": "orchestrator_001",
  "message": "Question: Should token expiration be configurable or hard-coded to 24 hours?",
  "priority": "normal",
  "tenant_key": "tenant_xyz"
}
```

**Response**:
```json
{
  "success": true,
  "message_id": "msg_001",
  "message": "Message sent successfully"
}
```

**Dashboard Impact**:
- Message appears in Job Details → Messages tab
- Notification sent to recipient agent
- Recipient can view message via get_next_instruction

**Workflow**:
```
1. Implementer sends message: "Question about token expiration"
2. Orchestrator receives notification
3. Orchestrator reviews message
4. Orchestrator sends reply via send_message
5. Implementer calls get_next_instruction to receive reply
6. Implementer continues work with clarification
```

### MCP Workflow Examples

**Example 1: Successful Job Completion (Codex Agent)**

```
Time    | Action                              | MCP Tool Called      | Status
--------|-------------------------------------|----------------------|------------------
10:30   | User spawns Implementer agent       | -                    | waiting_ack
10:32   | User copies prompt to Codex CLI     | -                    | waiting_ack
10:33   | Agent starts, acknowledges job      | acknowledge_job      | in_progress
10:45   | Agent reports initial progress      | report_progress(20%) | in_progress
11:00   | Agent reports milestone             | report_progress(50%) | in_progress
11:15   | Agent reports near completion       | report_progress(80%) | in_progress
11:30   | Agent completes work                | complete_job         | completed
```

**Example 2: Job with Orchestrator Question (Gemini Agent)**

```
Time    | Action                              | MCP Tool Called           | Status
--------|-------------------------------------|---------------------------|------------------
10:00   | Orchestrator spawns Tester agent    | -                         | waiting_ack
10:02   | User copies prompt to Gemini CLI    | -                         | waiting_ack
10:03   | Agent acknowledges job              | acknowledge_job           | in_progress
10:15   | Agent has question about coverage   | send_message              | in_progress
10:18   | Orchestrator sends reply            | send_message              | in_progress
10:19   | Agent retrieves reply               | get_next_instruction      | in_progress
10:25   | Agent continues with clarification  | report_progress(50%)      | in_progress
10:40   | Agent completes tests               | complete_job              | completed
```

**Example 3: Job Failure (Codex Agent)**

```
Time    | Action                              | MCP Tool Called      | Status
--------|-------------------------------------|----------------------|------------------
09:00   | User spawns Implementer agent       | -                    | waiting_ack
09:02   | Agent acknowledges job              | acknowledge_job      | in_progress
09:15   | Agent encounters missing dependency | -                    | in_progress
09:16   | Agent reports error                 | report_error         | failed
09:20   | Orchestrator reviews error          | -                    | failed
09:25   | Orchestrator fixes dependency       | -                    | failed
09:30   | Orchestrator respawns new agent     | -                    | waiting_ack
```

### Error Handling Flow

When agent encounters an error:

1. **Minor Error** (recoverable):
   - Agent retries operation
   - If successful, continue normally
   - If still failing, escalate to major error

2. **Major Error** (needs help):
   - Agent calls `send_message` to ask Orchestrator for help
   - Orchestrator reviews message
   - Orchestrator sends clarification or fix
   - Agent retrieves instruction via `get_next_instruction`
   - Agent continues work

3. **Critical Error** (unrecoverable):
   - Agent calls `report_error` with full details
   - Job status → `failed`
   - Orchestrator notified immediately
   - Orchestrator decides: Fix and retry, or abandon task

### Orchestrator Feedback Loop

Orchestrator uses MCP to guide agents dynamically:

**Scenario**: Requirements change mid-execution

```
1. Orchestrator receives new requirement from user
2. Orchestrator calls send_message to Implementer:
   "New requirement: Add 2FA support to authentication"
3. Implementer calls get_next_instruction (periodically or on trigger)
4. Implementer receives new requirement
5. Implementer adjusts implementation plan
6. Implementer calls report_progress with updated status:
   "Adding 2FA support as requested (60%)"
7. Orchestrator sees progress update in dashboard
8. Orchestrator monitors to completion
```

---

## Troubleshooting

Common issues and solutions for multi-tool orchestration.

### Agent Stuck in "Waiting Acknowledgment"

**Symptoms**:
- Agent spawned 10+ minutes ago
- Status badge still shows "Waiting for CLI"
- No progress updates

**Causes**:
1. User never copied prompt to CLI tool
2. Agent started but forgot to call `acknowledge_job`
3. MCP server unreachable from CLI tool

**Solutions**:

**Solution 1**: Copy Prompt to CLI
```
1. Go to dashboard → Find agent card
2. Click "Copy Prompt" button
3. Open CLI tool (Codex or Gemini)
4. Paste prompt and press Enter
5. Wait 10-30 seconds for acknowledgment
6. Verify status badge changes to "In Progress"
```

**Solution 2**: Verify Agent Called acknowledge_job
```
1. Check CLI output - agent should show:
   "Calling acknowledge_job MCP tool..."
2. If not, agent may have skipped this step
3. Manually instruct agent:
   "Please call the acknowledge_job MCP tool to confirm you've started"
4. Agent should acknowledge immediately
```

**Solution 3**: Check MCP Connectivity
```
1. Test MCP server: curl http://localhost:7272/mcp/health
2. Expected: {"status": "ok"}
3. If error: Restart GiljoAI MCP server
4. If timeout: Check firewall rules (port 7272 open?)
```

### MCP Tool Call Failures

**Symptoms**:
- Agent says "Failed to call acknowledge_job"
- MCP tools return errors
- Dashboard doesn't update despite agent working

**Causes**:
1. MCP server down or unreachable
2. Authentication token invalid/expired
3. Tenant key mismatch
4. Network firewall blocking MCP port

**Solutions**:

**Solution 1**: Verify MCP Server Running
```bash
# Check if API server is running
curl http://localhost:7272/health

# Expected response:
{"status": "healthy", "version": "3.1.0"}

# If not running:
python startup.py
```

**Solution 2**: Check Authentication
```bash
# MCP tools require authentication
# Verify token in agent prompt (auto-included)

# If token missing, regenerate prompt:
1. Dashboard → Agent card → "Regenerate Prompt"
2. Copy new prompt with fresh token
3. Restart agent in CLI with new prompt
```

**Solution 3**: Verify Tenant Key
```
Error: "Job not found" or "Permission denied"

Cause: Tenant key mismatch

Fix:
1. Dashboard → Settings → View Tenant Key
2. Note: tenant_xyz
3. Verify agent prompt includes: "tenant_key": "tenant_xyz"
4. If mismatch, regenerate prompt
```

**Solution 4**: Check Firewall
```
If GiljoAI on network (not localhost):

1. Verify port 7272 open in firewall
2. Test: curl http://<server-ip>:7272/health
3. If timeout: Open port 7272 in firewall
4. If connection refused: Check server binding (should be 0.0.0.0)
```

### Template Export Errors

**Symptoms**:
- "Export for Claude Code" button does nothing
- Export fails with error message
- Downloaded templates incomplete

**Causes**:
1. Template content invalid or corrupted
2. Template size exceeds limit
3. Missing required fields
4. Server-side export error

**Solutions**:

**Solution 1**: Validate Template Content
```
1. Templates tab → Edit template
2. Click "Preview" tab
3. Enter sample values for all variables
4. Click "Render"
5. Check for errors (red text)
6. Fix any validation errors
7. Save and retry export
```

**Solution 2**: Check Template Size
```
Error: "Template too large"

Fix:
1. Edit template → Check character count
2. If > 100KB: Reduce content
   - Remove redundant examples
   - Shorten behavioral rules
   - Link to external docs instead of embedding
3. Save and retry export
```

**Solution 3**: Verify Required Fields
```
Each template must have:
- name: "Implementer"
- role: "implementer"
- category: "role"
- preferred_tool: "claude" | "codex" | "gemini"
- content: (template body)

If any missing:
1. Edit template → Add missing field
2. Save → Retry export
```

**Solution 4**: Check Server Logs
```bash
# If export button does nothing:
# Check API server logs for errors

# Linux/Mac:
tail -f logs/api.log | grep "export"

# Windows:
Get-Content logs\api.log -Wait | Select-String "export"

# Look for error messages, fix accordingly
```

### Job Queue Issues

**Symptoms**:
- Jobs not appearing in dashboard
- Job status not updating
- Missing jobs or duplicate jobs

**Causes**:
1. WebSocket connection lost
2. Database query filter too restrictive
3. Tenant isolation blocking access
4. Cache inconsistency

**Solutions**:

**Solution 1**: Refresh WebSocket Connection
```
1. Open browser DevTools (F12)
2. Network tab → Filter by "WS"
3. Look for WebSocket connection status
4. If disconnected: Refresh page (F5)
5. WebSocket reconnects automatically
6. Jobs should load
```

**Solution 2**: Clear Filters
```
If no jobs visible:

1. Job Queue tab → Check active filters
2. Clear all filters:
   - Status: "All"
   - Tool: "All Tools"
   - Date: "All Time"
3. Click "Refresh"
4. Jobs should appear
```

**Solution 3**: Verify Tenant Access
```
Error: "No jobs found" (but you know jobs exist)

Cause: Logged in with wrong tenant

Fix:
1. Dashboard → Avatar dropdown → Check tenant
2. If wrong tenant: Logout → Login with correct account
3. Correct tenant: Jobs should appear
```

**Solution 4**: Invalidate Cache
```
If jobs stuck with stale data:

1. Restart browser (clear cache)
2. OR: Ctrl+Shift+R (hard refresh)
3. OR: Restart GiljoAI server (clears server cache)
```

### Cross-Tenant Access Errors

**Symptoms**:
- 403 Forbidden when accessing job/agent
- "Permission denied" errors
- Jobs visible but can't view details

**Causes**:
- Attempting to access resources from another tenant
- Multi-tenant isolation enforced correctly (working as designed)
- Tenant key mismatch in request

**Solutions**:

**Solution 1**: Verify Tenant Ownership
```
Error: 403 Forbidden on job details

Fix:
1. Job Queue → Note job ID (job_abc123)
2. Dashboard → Settings → View Tenant Key (tenant_xyz)
3. Check job details → If job belongs to different tenant:
   - This is expected (security feature)
   - Login with correct tenant account
   - OR: Contact admin if job should be accessible
```

**Solution 2**: Check User Permissions
```
If you're admin and should have access:

1. Admin Settings → Users Management
2. Find your user account
3. Verify assigned tenant (should match job's tenant)
4. If mismatch: Admin can reassign user to correct tenant
```

**Note**: Cross-tenant isolation is a security feature. If you genuinely need access across tenants, contact administrator to create a multi-tenant user (advanced feature).

---

## Best Practices

Maximize value from multi-tool orchestration with proven strategies.

### 1. Load Balancing Across Tools

**Strategy**: Distribute work evenly to avoid rate limits and maximize throughput.

**Implementation**:
```
Project with 10 agents:

Claude Code (3 agents - 30%):
  - Orchestrator: 1
  - Analyzer: 1
  - Reviewer: 1

Codex (4 agents - 40%):
  - Implementer: 3
  - Documenter: 1

Gemini (3 agents - 30%):
  - Tester: 3

Result: Balanced load, no single tool overwhelmed
```

**Benefits**:
- No rate limit bottlenecks
- Parallel execution across tools
- Resilience if one tool has issues
- Cost distribution

### 2. Rate Limit Avoidance Strategies

**Strategy 1: Tool Rotation**
```
Primary: Claude Code (best quality)
Fallback 1: Codex (if Claude rate-limited)
Fallback 2: Gemini (if both rate-limited)

When Claude hits rate limit:
1. Pause Claude agents (wait for rate limit reset)
2. Spawn Codex agents for same tasks
3. Continue work without delay
4. Resume Claude when rate limit resets
```

**Strategy 2: Time-Based Scheduling**
```
Peak Hours (9 AM - 5 PM):
  - Use free-tier tools (Gemini) for bulk tasks
  - Reserve premium tools (Claude) for critical work

Off-Peak Hours (5 PM - 9 AM):
  - Use premium tools for all tasks (lower contention)
  - Batch large jobs overnight
```

**Strategy 3: Parallel Execution**
```
Instead of:
  1 Claude agent doing 10 tasks sequentially (slow, rate-limited)

Do:
  10 Gemini agents doing 10 tasks in parallel (fast, free tier)

Result: 10x faster, zero cost, no rate limits
```

### 3. Cost Optimization Tips

**Tip 1: Free Tier Maximization**
```
Use Gemini free tier for:
- Documentation generation (high volume, low complexity)
- Test case expansion (parallel execution)
- Code formatting and linting
- Non-critical implementation

Savings: $0 vs $20-50/month for equivalent premium tier usage
```

**Tip 2: Premium Tier Strategic Use**
```
Use Claude Code for:
- Critical path tasks (architecture, security)
- Tasks requiring strong reasoning
- Complex refactoring
- High-stakes code reviews

Limit to 20-30% of total workload
Result: High quality where it matters, cost-effective overall
```

**Tip 3: Tool Selection by Task Complexity**
```
Simple Tasks (Gemini - Free):
  - Add logging statements
  - Fix typos
  - Format code
  - Generate boilerplate

Medium Tasks (Codex - $20/mo ChatGPT Plus):
  - Feature implementation
  - Bug fixes
  - Unit tests
  - Documentation

Complex Tasks (Claude - $20/mo Pro):
  - Architecture design
  - Security review
  - Complex refactoring
  - System integration

Result: 40-60% cost reduction vs all-premium approach
```

**Tip 4: Batch Processing**
```
Instead of:
  Spawning 100 agents one-by-one (expensive API calls)

Do:
  Batch spawn 10 Gemini agents, each handling 10 tasks (free tier)

Result: Same work done, fraction of the cost
```

### 4. Security Considerations

**Practice 1: Credential Management**
```
Never include credentials in prompts:
❌ "Connect to database at postgres://user:pass@host"

Instead, use environment variables:
✅ "Connect to database using DATABASE_URL env variable"

Benefits:
- Credentials not exposed to AI provider
- Prompts can be shared safely
- Compliance with security policies
```

**Practice 2: Sensitive Data Handling**
```
For tasks involving sensitive data:

1. Use Claude Code (hybrid mode)
   - Data stays local (not sent to cloud)
   - Anthropic's strong privacy policies

2. Avoid Codex/Gemini for:
   - PII (personally identifiable information)
   - Financial data
   - Health records (HIPAA-regulated)
   - Proprietary algorithms

3. If must use Codex/Gemini:
   - Anonymize data before processing
   - Use synthetic/test data
   - Review privacy policies
```

**Practice 3: Tenant Isolation Verification**
```
Regularly verify multi-tenant isolation:

1. Create test tenant
2. Spawn agents in both tenants
3. Attempt cross-tenant access (should fail with 403)
4. Verify job queue shows only own tenant's jobs
5. Confirm no data leakage in logs
```

**Practice 4: Audit Trail**
```
Enable comprehensive logging:

1. All MCP tool calls logged (who, what, when)
2. Job status changes tracked with timestamps
3. Inter-agent messages archived
4. Failed access attempts logged

Review logs periodically:
- Monthly security audit
- Look for suspicious patterns
- Verify compliance requirements met
```

### 5. Performance Optimization

**Optimization 1: Parallel Agent Spawning**
```python
# Instead of sequential spawning (slow):
for role in roles:
    spawn_agent(role)  # 5 seconds each = 30 seconds total

# Use parallel spawning (fast):
await asyncio.gather(*[
    spawn_agent(role) for role in roles
])  # 5 seconds total (parallel execution)
```

**Optimization 2: Checkpoint Frequency Tuning**
```
Too Frequent (every 1 minute):
  - Dashboard updates constantly (good UX)
  - High MCP API overhead (bad performance)
  - Rate limits possible

Too Infrequent (every 60 minutes):
  - Low MCP API overhead (good performance)
  - Stale dashboard status (bad UX)
  - Difficult to debug

Optimal (every 10-15 minutes):
  - Balanced performance
  - Good visibility
  - Low overhead

Adjust based on task duration:
- Short tasks (< 30 min): 5-minute checkpoints
- Medium tasks (30-60 min): 10-minute checkpoints
- Long tasks (> 60 min): 15-minute checkpoints
```

**Optimization 3: Caching Template Resolution**
```
GiljoAI automatically caches templates:

Memory Cache (< 1ms): Hot templates
Redis Cache (< 2ms): Warm templates
Database (< 10ms): Cold templates

Best Practice:
- Use consistent template names (cache-friendly)
- Avoid frequent template changes (invalidates cache)
- Monitor cache hit rate (aim for > 95%)
```

**Optimization 4: Efficient Message Queuing**
```
Instead of:
  Polling for messages every 10 seconds (wasteful)

Use:
  WebSocket events for instant message delivery (efficient)

Result:
- Zero polling overhead
- Instant message notifications
- Reduced API load
```

### 6. Monitoring and Alerting

**Setup 1: Job Completion Rate Monitoring**
```
Track metrics:
- Jobs completed per hour
- Average completion time per tool
- Failure rate per tool

Alerts:
- Failure rate > 10%: Investigate tool issues
- Avg completion time doubled: Check rate limits
- Zero completions for 1 hour: Critical alert
```

**Setup 2: Rate Limit Warnings**
```
Monitor API usage:
- Claude: Track requests per hour vs limit
- Codex: Track token usage vs limit
- Gemini: Track requests per day vs limit

Proactive alerts:
- 80% of limit: Warning (switch tools soon)
- 90% of limit: Alert (switch tools now)
- 100% of limit: Critical (tool unavailable)
```

**Setup 3: Cost Tracking**
```
Track costs per tool:
- Claude: $X per 1M tokens
- Codex: $Y per 1M tokens
- Gemini: Free tier, then $Z per 1M tokens

Monthly budget alerts:
- 50% of budget: Info (on track)
- 80% of budget: Warning (optimize usage)
- 100% of budget: Alert (review strategy)
```

---

## FAQ

### Q1: Can I use multiple AI tools simultaneously in one project?

**A**: Yes! This is the core feature of multi-tool orchestration.

**Example**:
```
Project: E-commerce Backend

Agents:
- Orchestrator: Claude Code (best reasoning)
- Implementer: Codex (fast implementation)
- Tester: Gemini (free tier, parallel tests)
- Reviewer: Claude Code (quality assurance)

All agents coordinate via MCP within the same project.
```

### Q2: Do I need licenses for all three AI tools?

**A**: No, you only need licenses for the tools you plan to use.

**Minimum** (get started for free):
- Gemini CLI (free tier) - sufficient for testing and documentation

**Recommended** (balanced):
- Claude Code Pro ($20/mo) - critical path tasks
- Gemini CLI (free tier) - bulk tasks

**Optimal** (maximum flexibility):
- Claude Code Pro ($20/mo)
- ChatGPT Plus ($20/mo) for Codex
- Gemini CLI (free tier)

**Total cost**: $0 (free tier only) to $40/month (all premium tiers)

### Q3: What happens if an agent's AI tool becomes unavailable mid-job?

**A**: The job enters "blocked" state until tool becomes available again.

**Scenario**:
```
1. Implementer agent (Codex) working on task
2. OpenAI API goes down (service outage)
3. Agent cannot complete MCP checkpoints
4. Dashboard shows "Last checkpoint: 30 minutes ago" (stale)
5. After 60 minutes of no checkpoints, job marked "blocked"
```

**Recovery Options**:

**Option 1: Wait for Service Recovery**
```
1. Wait for OpenAI API to return
2. Agent resumes work automatically
3. Agent reports progress via MCP
4. Job status: blocked → in_progress
```

**Option 2: Switch to Different Tool**
```
1. Mark current job as failed (agent cannot continue)
2. Spawn new agent with different tool (e.g., Gemini)
3. New agent picks up from last checkpoint
4. Work continues without further delay
```

**Option 3: Manual Completion**
```
1. Review agent's work up to last checkpoint
2. Manually complete remaining work
3. Mark job as completed in dashboard
4. Update codebase accordingly
```

### Q4: How do I debug MCP coordination issues?

**A**: Use the Job Queue Dashboard and server logs.

**Step-by-Step**:

1. **Check Job Status**:
   ```
   Job Queue → Find job → View details
   Look for last checkpoint time and status
   ```

2. **Review MCP Call History**:
   ```
   Job Details → Timeline tab
   See all MCP tool calls (acknowledge_job, report_progress, etc.)
   ```

3. **Check Agent Messages**:
   ```
   Job Details → Messages tab
   Look for error messages or questions from agent
   ```

4. **Review Server Logs**:
   ```bash
   # View MCP endpoint logs
   tail -f logs/api.log | grep "/mcp/"

   # Look for errors:
   # - 400 Bad Request: Invalid parameters
   # - 403 Forbidden: Tenant isolation violation
   # - 404 Not Found: Job/agent doesn't exist
   # - 500 Server Error: Server-side issue
   ```

5. **Test MCP Manually**:
   ```bash
   # Test acknowledge_job endpoint
   curl -X POST http://localhost:7272/mcp/acknowledge_job \
     -H "Content-Type: application/json" \
     -d '{"job_id": "job_abc123", "agent_id": "agent_xyz", "tenant_key": "tenant_123"}'

   # Expected: {"success": true, ...}
   ```

### Q5: Can I change an agent's tool after it's been spawned?

**A**: No, the tool is locked at spawn time. You can only change it for future agents.

**Why**:
- Agent mission includes tool-specific instructions (e.g., MCP integration)
- Agent may already be running in external CLI tool
- Changing mid-execution would cause confusion

**Workaround**:
```
1. Complete current agent's work (or mark as failed)
2. Update template: Change "Preferred Tool" to new tool
3. Spawn new agent with updated template
4. New agent uses new tool
```

**Example**:
```
Current: Implementer-001 using Codex (running)
Desired: Switch to Gemini

Steps:
1. Let Implementer-001 complete current task
2. Templates → Edit Implementer → Tool: gemini
3. Spawn Implementer-002 (uses Gemini automatically)
4. Future Implementer agents use Gemini
```

### Q6: How does billing work when using multiple AI tools?

**A**: Billing is separate per AI provider. GiljoAI doesn't charge for multi-tool orchestration.

**GiljoAI MCP**:
- Free and open-source
- No usage-based fees
- No charge for multi-tool coordination

**AI Tool Providers**:
- **Claude Code**: Anthropic billing ($20/mo Pro, or per-token API usage)
- **Codex**: OpenAI billing ($20/mo ChatGPT Plus, or per-token API usage)
- **Gemini**: Google billing (free tier, or per-token for paid tier)

**Example Monthly Cost**:
```
GiljoAI MCP: $0 (free)
Claude Code Pro: $20 (fixed subscription)
ChatGPT Plus (Codex): $20 (fixed subscription)
Gemini: $0 (using free tier)

Total: $40/month for unlimited multi-tool orchestration
```

**Cost Optimization**:
- Use free tiers (Gemini) for bulk work: $0
- One premium subscription: $20/month
- Two premium subscriptions: $40/month

**Recommendation**: Start with one premium tool + free tier Gemini ($20-0/month), expand as needed.

### Q7: What's the difference between Hybrid Mode and Legacy CLI Mode?

**A**: Hybrid Mode is automatic (Claude Code only), Legacy CLI Mode is manual (Codex/Gemini).

**Hybrid Mode** (Claude Code):
```
User Experience:
  - Agent spawns automatically in Claude Code
  - No prompt copying needed
  - Real-time coordination via MCP
  - Subagents spawn automatically

Technical:
  - MCP server integrated into Claude Code
  - Automatic checkpointing
  - Bidirectional communication
  - Agent runs in Claude Code process

Advantages:
  - Zero manual intervention
  - Best user experience
  - Real-time status updates

Disadvantages:
  - Requires Claude Code IDE
  - Claude-only (not available for other tools)
```

**Legacy CLI Mode** (Codex/Gemini):
```
User Experience:
  - User copies prompt from dashboard
  - User pastes into CLI tool
  - Agent checkpoints manually via MCP
  - User monitors dashboard for status

Technical:
  - MCP coordination via HTTP API
  - Manual checkpointing (agent must call MCP tools)
  - Unidirectional communication (agent → server)
  - Agent runs in separate CLI process

Advantages:
  - Works with any AI tool (Codex, Gemini, future tools)
  - No IDE dependency
  - Flexible deployment

Disadvantages:
  - Manual prompt copying (one-time per agent)
  - Requires agent discipline (must call MCP tools)
  - Less seamless than hybrid mode
```

**When to Use Each**:
- **Hybrid Mode**: If you have Claude Code and want best UX
- **Legacy CLI Mode**: If you want cost savings, tool diversity, or don't have Claude Code

### Q8: How do I handle agents that don't call MCP tools correctly?

**A**: Provide explicit MCP instructions in templates and monitor compliance.

**Problem**:
Agent forgets to call `acknowledge_job` or `report_progress`, causing dashboard to show stale status.

**Solution 1: Template Enforcement**
```markdown
# Template: Implementer (Codex)

## CRITICAL MCP WORKFLOW (MUST FOLLOW)

**STEP 1 - Acknowledge Job** (FIRST ACTION):
Call acknowledge_job MCP tool immediately:
```json
{
  "job_id": "{job_id}",
  "agent_id": "{agent_id}",
  "tenant_key": "{tenant_key}"
}
```

**STEP 2 - Report Progress** (Every 15 minutes):
Call report_progress MCP tool with current status:
```json
{
  "job_id": "{job_id}",
  "progress_data": {
    "percentage": 50,
    "message": "Current milestone description"
  }
}
```

**STEP 3 - Complete Job** (LAST ACTION):
Call complete_job MCP tool when done:
```json
{
  "job_id": "{job_id}",
  "summary": "Work completed successfully. Summary of changes."
}
```

⚠️ WITHOUT THESE MCP CALLS, YOUR WORK WILL NOT BE TRACKED!
```

**Solution 2: Monitoring and Reminders**
```
Set up dashboard alerts:

1. Job in "waiting_acknowledgment" for > 5 minutes:
   Alert: "Agent may have forgotten to acknowledge job"
   Action: Send message to agent: "Please call acknowledge_job"

2. No progress updates for > 20 minutes:
   Alert: "Agent may have stopped checkpointing"
   Action: Send message: "Please call report_progress with current status"

3. Job "in_progress" for > 2 hours:
   Alert: "Long-running job, verify agent is still working"
   Action: Check CLI tool, verify agent active
```

**Solution 3: Agent Training**
```
For human-in-the-loop CLI mode:

1. Create MCP checklist:
   - [ ] acknowledge_job called?
   - [ ] report_progress called every 15 min?
   - [ ] complete_job called when done?

2. Train users to verify MCP compliance:
   - After pasting prompt, watch for MCP calls in CLI output
   - If agent doesn't call MCP tools, manually instruct it
   - Review dashboard to confirm updates appear

3. Template includes MCP reminders:
   - Bold text: **MUST CALL acknowledge_job FIRST**
   - Repeated instructions at top and bottom of prompt
   - Examples showing exact MCP tool syntax
```

### Q9: Can I export my multi-tool configuration to share with my team?

**A**: Yes, export templates to share consistent multi-tool setup.

**Steps**:

1. **Export Templates**:
   ```
   Dashboard → Templates → "Export for Claude Code"
   Downloads: giljo_templates.zip
   ```

2. **Share with Team**:
   ```
   # Via file sharing
   Send giljo_templates.zip to team members

   # Or via git repository
   Extract templates/ folder
   Commit to team repository
   Team members clone and import
   ```

3. **Team Members Import**:
   ```
   Dashboard → Templates → "Import Templates"
   Select giljo_templates.zip
   Templates imported with same tool configuration
   ```

**What's Shared**:
- Agent templates with tool assignments
- Behavioral rules and success criteria
- MCP integration instructions
- Product-specific customizations

**What's NOT Shared**:
- API keys or credentials (security)
- Job history or agent data (tenant-specific)
- Database configuration (deployment-specific)

**Use Case**:
```
Team Lead configures optimal tool assignment:
  - Orchestrator: claude
  - Implementer: codex
  - Tester: gemini
  - Reviewer: claude

Team Lead exports templates
Team members import templates
Entire team uses same optimized configuration
Consistent multi-tool orchestration across team
```

### Q10: What metrics should I track to optimize multi-tool usage?

**A**: Track cost per tool, completion rate, and average time.

**Key Metrics**:

**1. Cost Per Tool** (monthly):
```
Claude Code:
  - API usage: $X
  - Subscription: $20
  - Total: $X + $20

Codex:
  - API usage: $Y
  - Subscription: $20 (ChatGPT Plus)
  - Total: $Y + $20

Gemini:
  - API usage: $0 (free tier)
  - Total: $0

Grand Total: $X + $Y + $40
Target: < $100/month
```

**2. Completion Rate** (success %):
```
Claude Code:
  - Jobs completed: 45
  - Jobs failed: 5
  - Completion rate: 90%

Codex:
  - Jobs completed: 80
  - Jobs failed: 20
  - Completion rate: 80%

Gemini:
  - Jobs completed: 30
  - Jobs failed: 5
  - Completion rate: 85%

Analysis: Claude has highest quality, worth premium price
```

**3. Average Completion Time**:
```
Claude Code: 45 minutes/job (slower, higher quality)
Codex: 30 minutes/job (fast, good quality)
Gemini: 25 minutes/job (fastest, acceptable quality)

Analysis: Use Gemini for time-sensitive, low-complexity tasks
```

**4. Cost Per Completed Job**:
```
Claude Code: $2.50/job (high quality, high cost)
Codex: $1.00/job (balanced)
Gemini: $0.00/job (free tier)

ROI: Gemini offers best cost efficiency for bulk tasks
```

**Dashboard to Create**:
```
Multi-Tool Orchestration Dashboard:

┌─────────────────────────────────────────┐
│ Monthly Summary                         │
├─────────────────────────────────────────┤
│ Total Jobs: 155                         │
│ Total Cost: $67                         │
│ Avg Cost/Job: $0.43                     │
│ Avg Time/Job: 32 minutes                │
└─────────────────────────────────────────┘

┌────────────────┬────────┬──────┬────────┬──────────┐
│ Tool           │ Jobs   │ Cost │ Avg    │ Success  │
│                │        │      │ Time   │ Rate     │
├────────────────┼────────┼──────┼────────┼──────────┤
│ Claude Code    │ 45     │ $45  │ 45min  │ 90%      │
│ Codex          │ 80     │ $22  │ 30min  │ 80%      │
│ Gemini         │ 30     │ $0   │ 25min  │ 85%      │
└────────────────┴────────┴──────┴────────┴──────────┘

Recommendations:
✅ Increase Gemini usage (free, good quality)
⚠️ Reduce Codex usage (similar cost to Claude, lower quality)
✅ Reserve Claude for critical tasks (highest quality)
```

**Optimization Actions**:
```
Based on metrics:

1. Cost too high? Shift bulk tasks to Gemini (free tier)
2. Quality too low? Shift critical tasks to Claude
3. Time too slow? Use Gemini for parallel execution
4. Failure rate high? Review template instructions
5. One tool unused? Evaluate if needed, consider dropping subscription
```

---

## Conclusion

Congratulations! You now understand multi-tool agent orchestration in GiljoAI MCP v3.1.

### What You've Learned

- ✅ What multi-tool orchestration is and its benefits
- ✅ How to configure templates for different AI tools
- ✅ When to use Claude Code, Codex, or Gemini
- ✅ How to spawn and monitor agents across tools
- ✅ MCP coordination protocol and tools
- ✅ Troubleshooting common issues
- ✅ Best practices for cost and performance optimization

### Next Steps

1. **Try Multi-Tool Orchestration**:
   - Configure one template with a different tool
   - Spawn an agent and observe the workflow
   - Monitor progress in Job Queue Dashboard

2. **Experiment with Mixed Mode**:
   - Set Orchestrator to Claude (best reasoning)
   - Set Implementer to Codex (fast iteration)
   - Set Tester to Gemini (free tier)
   - Compare results and costs

3. **Optimize Your Workflow**:
   - Track metrics (cost, completion rate, time)
   - Adjust tool assignments based on results
   - Iterate to find optimal configuration

4. **Share with Your Team**:
   - Export templates with tool configuration
   - Train team on MCP coordination protocol
   - Establish best practices for your organization

### Additional Resources

- **[Developer Guide](./DEVELOPER_GUIDE.md)** - Technical architecture and API details
- **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - Production deployment and operations
- **[API Reference](./API_REFERENCE.md)** - Complete API endpoint documentation
- **[Architecture Decision Records](./ADR.md)** - Design decisions and rationale
- **[Main README](../../../README.md)** - GiljoAI MCP overview

### Support

Need help?

- **Documentation**: [docs/README_FIRST.md](../../README_FIRST.md)
- **Issues**: https://github.com/patrik-giljoai/GiljoAI-MCP/issues
- **Community**: GiljoAI Discord server

---

**Document Version**: 1.0
**Last Updated**: 2025-10-25
**Feedback**: Please report errors or suggest improvements via GitHub issues
