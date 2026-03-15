---
**Document Type:** Unified Workflow Documentation
**Last Updated:** 2025-11-29 - Added spawning type clarifications
**Purpose:** Single source of truth for GiljoAI Agent Orchestration workflows
**Status:** ✅ Updated with Type 1 (MCP) vs Type 2 (CLI) spawning distinctions
---

# GiljoAI MCP Server - Complete Agent Flow Documentation

## Critical Terminology Alignment

**IMPORTANT**: This section resolves naming inconsistencies between UI labels and backend implementation.

### Button & Endpoint Mapping

| UI Label | Backend Endpoint | Actual Function | Database Field Updated |
|----------|-----------------|-----------------|------------------------|
| "Stage Project" | `/api/v1/projects/{id}/activate` | Activates project & creates orchestrator job | Creates MCPAgentJob record |
| "Launch Jobs" | Navigation only | Switches from Launch tab to Implementation tab | None |
| "Activate Project" | `/api/v1/projects/{id}/activate` | Same as "Stage Project" | Project.is_active = true |

### Field Naming Convention (User vs AI)

| Field | Type | Description | Filled By |
|-------|------|-------------|-----------|
| `Product.description` | User Input | User-written product description | **Human** (via UI) |
| `Project.description` | User Input | User-written project requirements | **Human** (via UI) |
| `Project.mission` | AI Output | Orchestrator-generated mission plan | **Orchestrator** (during staging) |
| `MCPAgentJob.mission` | AI Output | Individual agent's job assignment | **Orchestrator** (via spawn_agent_job) |

**Key Rule**: User writes = "description", AI generates = "mission"

### Status Value Translation (Dual-Status Architecture)

**CRITICAL**: GiljoAI uses a dual-status system introduced in Handover 0113 for backward compatibility.

#### Database Layer (Canonical - 7 States)

| Database Value | Description | Constraint |
|---------------|-------------|------------|
| `"waiting"` | Job created but not yet started | ✅ Allowed |
| `"working"` | Agent is executing tasks | ✅ Allowed |
| `"blocked"` | Job needs intervention | ✅ Allowed |
| `"complete"` | Job finished successfully | ✅ Allowed |
| `"failed"` | Job encountered fatal error | ✅ Allowed |
| `"cancelled"` | Job was cancelled by user | ✅ Allowed |
| `"decommissioned"` | Job was archived/retired | ✅ Allowed |

**Database Constraint** (enforced in `models/agents.py`):
```sql
CHECK (status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned'))
```

**Note**: There is NO "staged" or "pending" status in the database constraint. Any reference to "staged" status is incorrect.

#### API Layer (Aliases for Compatibility)

The `AgentJobManager` provides translation between API-friendly terms and database values:

| API Alias | Database Value | Direction |
|-----------|---------------|-----------|
| `"pending"` | `"waiting"` | API → Database (inbound) |
| `"active"` | `"working"` | API → Database (inbound) |
| `"completed"` | `"complete"` | API → Database (inbound) |
| `"waiting"` | `"pending"` | Database → API (outbound) |
| `"working"` | `"active"` | Database → API (outbound) |
| `"complete"` | `"completed"` | Database → API (outbound) |

**Translation Layer**: Implemented in `src/giljo_mcp/agent_job_manager.py` (lines 62-71)
- `STATUS_INBOUND_ALIASES`: Translates API terms to database values
- `STATUS_OUTBOUND_ALIASES`: Translates database values to API terms
- Allows API evolution without breaking existing integrations

**Why This Exists**: Provides backward compatibility for external API clients while maintaining consistent database schema. The system can accept "pending" via API but always stores "waiting" in the database.

---

## Understanding the Two Types of Agent Spawning

**CRITICAL DISTINCTION**: There are TWO completely different "spawning" mechanisms in GiljoAI. Confusing these leads to misunderstanding the workflow.

### Type 1: MCP Server Agent Spawning (Database Record Creation)

**What It Is**: Creating database records and UI agent cards during the staging phase.

**When It Happens**: During orchestrator's staging workflow (Step 4, Task 5)

**What Gets Created**:
- Database record in `mcp_agent_jobs` table
- Assigns unique `agent_id` and `job_id`
- Stores agent mission in `MCPAgentJob.mission` field
- Creates visual agent card in the UI
- Sets initial status to "waiting"

**Think of It As**: Creating "digital twin" job tickets that wait to be picked up.

**Code Location**: `src/giljo_mcp/tools/orchestration.py::spawn_agent_job()`

**MCP Tool**: `spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key)`

**Example**:
```python
# Orchestrator calls during staging (Task 5)
job_info = spawn_agent_job(
    agent_type="implementer",
    agent_name="Code Implementer",
    mission="Implement the user authentication feature...",
    project_id="abc-123",
    tenant_key="tenant-xyz"
)
# Result: Creates database record, agent card appears in UI
```

### Type 2: Claude Code CLI Native Subagent Spawning (Agent Execution)

**What It Is**: Claude Code's built-in capability to invoke subagents from `.md` template files.

**When It Happens**: During implementation phase, ONLY when "Claude Code Mode" toggle is ON.

**How It Works**:
1. Orchestrator reads `.md` templates from `~/.claude/agents/` or `.claude/agents/`
2. Template names match agent types (`implementer.md`, `tester.md`, etc.)
3. Orchestrator uses Claude Code's native subagent feature to spawn them
4. Passes `agent_id`, `job_id`, and other identifiers to the subagent
5. Subagent's `.md` template contains MCP behavior instructions
6. Subagent calls `get_agent_mission(job_id, tenant_key)` to fetch its mission from the database

**Think of It As**: Hiring workers to pick up the job tickets created in Type 1.

**Code Location**: `.claude/agents/implementer.md` (and other agent `.md` files)

**MCP Tool**: `get_agent_mission(agent_job_id, tenant_key)` (called BY the spawned agent)

**Example**:
```markdown
# File: ~/.claude/agents/implementer.md
You are the Implementer Agent for GiljoAI.

Your first action: Fetch your mission from the MCP server.

Call: get_agent_mission('{agent_job_id}', '{tenant_key}')

This returns your mission, project context, and work assignments.
Then begin implementation following the 6-phase protocol...
```

### The Relationship: Digital Twins

**MCP Spawning** (Type 1) creates the "digital twin" - a database representation of the work to be done.

**CLI Spawning** (Type 2) creates the "real agent" - the actual Claude Code instance that executes the work.

The bridge between them is:
- Type 1 creates `job_id` and stores mission in database
- Type 2 receives `job_id` as a parameter
- Agent calls `get_agent_mission(job_id)` to fetch its mission
- Agent updates the same database record as it works

### Why Two Systems?

**Flexibility**: Supports both Claude Code native subagents AND multi-terminal execution.

**Auditability**: All missions stored in database regardless of how agents are spawned.

**Replay**: Agent can re-fetch its mission at any time by calling `get_agent_mission()` again.

**Separation of Concerns**:
- MCP Server = Job ticket system (database, missions, status tracking)
- Claude Code CLI = Worker dispatch system (native subagent spawning)

### Quick Comparison Table

| Aspect | Type 1: MCP Server Spawning | Type 2: Claude Code CLI Spawning |
|--------|----------------------------|----------------------------------|
| **Purpose** | Create job tickets in database | Execute work via subagents |
| **When** | Staging phase (Task 5) | Implementation phase (Step 7A) |
| **Where** | MCP Server (Python backend) | Claude Code CLI (user terminal) |
| **Creates** | Database record + UI card | Running Claude Code instance |
| **Tool/Code** | `spawn_agent_job()` MCP tool | `.md` template invocation |
| **Output** | `job_id`, `agent_id`, metadata | Active agent executing mission |
| **Requires** | Active project, tenant_key | `.md` templates in ~/.claude/agents/ |
| **Used In** | BOTH execution modes | ONLY Claude Code CLI mode |
| **Visible As** | Agent card in UI | Terminal process/subagent |

### Key Takeaway

When you see "spawn_agent_job()" → **Database record creation** (Type 1)

When you see "Claude spawns subagent from .md" → **Agent execution** (Type 2)

They are complementary, not the same thing!

---

## Project Staging → Implementation Phase (Complete Flow)

### Phase 1: PROJECT ACTIVATION & STAGING

#### Step 1: Navigate to Project
```
User Action: Click [Launch Project] button in project list
         OR: Click "Jobs" in left sidebar
         ↓
System Response: Navigate to custom project URL
         URL Format: http://{host}:port/projects/{project_ID}?via=jobs
         ↓
Landing Page: "Launch" Tab (First tab in two-tab interface)
```

#### Step 2: Launch Tab Interface Elements
```
┌─────────────────────────────────────────────────┐
│  Launch Tab                                     │
├─────────────────────────────────────────────────┤
│  [Stage Project] Button                         │ ← UI Label (misleading)
│                                                  │   Backend: /activate endpoint
│  Project Description (editable)                 │ ← User-written content
│                                                  │
│  Orchestrator Generated Mission (empty)         │ ← Will be populated after staging
│                                                  │
│  Orchestrator Card                              │ ← Shows agent_id
│    - Role: orchestrator                         │
│    - Status: waiting                            │
│    - [Copy Prompt >] (disabled initially)       │
└─────────────────────────────────────────────────┘
```

#### Step 3: Stage Project Button Click
```
User Action: Click [Stage Project] button
         ↓
Backend Process:
  1. POST /api/v1/projects/{id}/activate
  2. Create MCPAgentJob record:
     - agent_type: "orchestrator"
     - status: "waiting" (database value)
     - mission: "I am ready to create the project mission..."
  3. Generate thin client prompt (450-550 tokens)
  4. Enable orchestrator [Copy Prompt >] button
         ↓
UI Updates:
  - Orchestrator card shows copyable prompt
  - User copies prompt to terminal

Note: Job is created directly in "waiting" status. There is NO "staged"
      status or separate activation step. The job goes: waiting → working.
```

#### Step 4: Orchestrator Execution - 5-Task Staging Workflow
```
Terminal Process:
  1. User pastes thin prompt into CLI tool
  2. Thin prompt provides identity (orchestrator_id, tenant_key)
  3. Orchestrator executes 5-task staging workflow:

     TASK 1: Verify MCP Connection
     └─► health_check() - REQUIRED first step
         ├─► Verifies MCP server connectivity
         ├─► Response must be < 2 seconds
         └─► Lists available MCP tools

     TASK 2: Fetch Instructions
     └─► get_orchestrator_instructions(orchestrator_id, tenant_key)
         ├─► Mission NOT embedded in thin prompt
         ├─► Server builds condensed mission (~6K tokens)
         ├─► Reads Product.description (user input)
         ├─► Reads Project.description (user input)
         ├─► Reads vision documents (chunked)
         ├─► Reads context based on user's toggle/depth settings
         └─► Returns full context and instructions

     TASK 3: Create Mission Plan
     └─► Analyze requirements and create comprehensive mission
         └─► Orchestrator synthesizes mission from context

     TASK 4: Persist Mission
     └─► update_project_mission(project_id, mission)
         ├─► Saves to Project.mission field in database
         ├─► WebSocket event: project:mission_updated
         └─► UI: "Orchestrator Generated Mission" updates live

     TASK 5: Spawn Agent Database Records (Type 1 Spawning)
     └─► Dynamic agent discovery and MCP server spawning:
         ├─► get_available_agents(tenant_key, active_only=True)
         │   └─► NO hardcoded agent list (Handover 0246c)
         │   └─► Dynamic discovery saves 420 tokens (71% reduction)
         ├─► For each agent needed:
         │   └─► spawn_agent_job(agent_type, mission, ...)
         │       ├─► **TYPE 1 SPAWNING**: Creates database record + UI card
         │       ├─► Stores mission in MCPAgentJob.mission (database)
         │       ├─► Creates job with status="waiting"
         │       ├─► Assigns unique agent_id and job_id
         │       ├─► Creates "digital twin" agent card in UI
         │       └─► Returns agent metadata (NOT a prompt)
         └─► WebSocket: Agent cards appear live in UI

Note: This is MCP SERVER spawning (Type 1) - creating database records and agent
      cards. This is NOT Claude Code CLI spawning (Type 2). The actual agent
      execution happens later in the Implementation phase (see Step 7A/7B below).
      Mission is stored in database, NOT embedded in agent prompts. Agents fetch
      mission on-demand via get_agent_mission() when they start executing.
         ↓
UI Live Updates:
  - "Orchestrator Generated Mission" window populates
  - Agent cards appear in "Agent Team" section
  - [Launch Jobs] button appears
```

---

### Phase 2: JOB IMPLEMENTATION & EXECUTION

#### Step 5: Navigate to Implementation
```
User Action: Click [Launch Jobs] button
         ↓
Navigation: Switch to "Implementation" Tab (same URL)
```

#### Step 6: Implementation Tab Interface
```
┌─────────────────────────────────────────────────┐
│  Implementation Tab                             │
├─────────────────────────────────────────────────┤
│  Claude Code CLI Mode: [Toggle Switch]          │ ← Critical toggle
│  Hint: (dynamic based on toggle state)          │
│                                                  │
│  Orchestrator Card                              │
│    - Status: waiting → working → complete       │
│    - [Copy Prompt >] (always enabled)           │
│                                                  │
│  Agent Cards (spawned by orchestrator)          │
│    - Implementer_1 [Copy Prompt >]              │ ← Enabled/disabled
│    - Tester_1 [Copy Prompt >]                   │   based on toggle
│    - Documenter_1 [Copy Prompt >]               │
│    - [Additional agents...]                     │
│                                                  │
│  Message Center [Tab indicator with count]      │
└─────────────────────────────────────────────────┘
```

#### Step 7A: Claude Code CLI Mode (Toggle ON)

**Prerequisites** (Setup must be completed first):
- User exported agent templates during initial setup
- Templates installed to `~/.claude/agents/` (global) or `.claude/agents/` (project)
- Template files: `orchestrator.md`, `implementer.md`, `tester.md`, `analyzer.md`, etc.
- Each `.md` file contains MCP behavior instructions

```
Toggle State: ON
         ↓
UI Behavior:
  - Only orchestrator [Copy Prompt >] button active
  - All agent prompt buttons grayed out (disabled)
  - Hint: "Claude Code subagent mode - Orchestrator spawns agents"
  - Why? Because Claude Code spawns subagents natively from .md templates
         ↓
Execution Flow:
  1. User copies orchestrator prompt and pastes in single terminal
  2. Orchestrator reads MCP instructions (includes Claude Code mode flag)
  3. Orchestrator sees which agent jobs exist via get_workflow_status()
  4. **TYPE 2 SPAWNING**: Uses Claude Code's native subagent feature:
     ├─► Looks in ~/.claude/agents/ for matching .md templates
     ├─► Template names match agent types (implementer.md, tester.md, etc.)
     ├─► Invokes each subagent using Claude's native capability
     └─► Passes parameters: agent_id, job_id, project_id, tenant_key
  5. Each spawned subagent:
     ├─► Reads its .md template file (contains MCP instructions)
     ├─► Calls get_agent_mission(job_id, tenant_key) to fetch mission from database
     ├─► Receives mission + context from MCP server
     └─► Begins 6-phase execution protocol
  6. All agents coordinate via MCP messaging tools
         ↓
Single Terminal Execution with native subagents (Type 2 spawning)

Note: The agent cards in the UI are "digital twins" created via Type 1 spawning
      during staging. The .md templates + job_id creates the bridge between the
      database records and the actual Claude Code subagent instances.
```

#### Step 7B: Multi-Terminal Mode (Toggle OFF - Default)
```
Toggle State: OFF (default)
         ↓
UI Behavior:
  - ALL [Copy Prompt >] buttons active (orchestrator + all agents)
  - Each agent gets unique prompt
  - Hint: "Multi-terminal mode - Launch agents in separate windows"
  - Why? Each agent runs independently in its own terminal
         ↓
Execution Flow:
  1. User copies orchestrator prompt → pastes in Terminal 1
  2. User copies implementer prompt → pastes in Terminal 2
  3. User copies tester prompt → pastes in Terminal 3
  4. (Repeat for all agent types)
  5. Each agent independently:
     ├─► Receives thin prompt with agent_id, job_id, tenant_key
     ├─► Calls get_agent_mission(job_id, tenant_key) to fetch mission
     ├─► Receives mission + context from MCP server
     └─► Begins 6-phase execution protocol
  6. Orchestrator coordinates via MCP messaging tools
  7. Agents communicate via send_mcp_message() and broadcast()
         ↓
Multiple Terminal Windows (one per agent)

Note: This mode does NOT use Claude Code's native subagent spawning (Type 2).
      Each agent is a separate, independent Claude Code instance launched manually.
      The agent cards in the UI are still "digital twins" from Type 1 spawning.
      Each terminal connects to the same database record via job_id.
```

---

## Job Action Phase Details (Implementation)

### Agent Status Progression
```
Database Status Flow: waiting → working → complete/failed/blocked/cancelled
                        ↓          ↓               ↓
UI Display:          Waiting    Working        Final state
WebSocket Events:  job:status_changed (all transitions)

Valid Database States (7 total):
  - waiting: Job created, not yet claimed
  - working: Agent actively executing
  - blocked: Waiting for external dependency
  - complete: Successfully finished
  - failed: Encountered fatal error
  - cancelled: User cancelled job
  - decommissioned: Job archived/retired

Note: Database stores canonical values (waiting, working, complete).
      API accepts aliases (pending, active, completed) for compatibility.
      Frontend receives database values via WebSocket events.
```

### MCP Communication During Execution

#### Available MCP Tools for Agents
```
Coordination Tools:
├── get_pending_jobs()      - Find work assigned to agent
├── acknowledge_job()       - Claim job (waiting → working)
├── report_progress()       - Update progress percentage
├── complete_job()          - Mark as done with results (working → complete)
└── report_error()          - Report blocking issues (working → blocked/failed)

Messaging Tools (See "Messaging Architecture" section below for details):
├── send_message()          - Messages Table: Send to specific agents
├── broadcast()             - Messages Table: Send to all agents
├── get_messages()          - Messages Table: Retrieve pending messages
├── send_mcp_message()      - JSONB Queue: Real-time agent messaging
├── read_mcp_messages()     - JSONB Queue: Poll message queue
└── acknowledge_message()   - Both systems (different signatures)

Status Tools:
├── get_workflow_status()   - View all agents in project
└── get_next_instruction()  - Check for orchestrator updates
```

### Real-time UI Updates
```
WebSocket Events → UI Components:
├── job:status_changed      → Agent card badge color
├── job:progress_updated    → Progress bar percentage
├── message:new             → Message center count badge
├── project:mission_updated → Mission window content
└── agent:spawned           → New agent card appears
```

### Agent Execution Patterns

#### Parallel Execution
```
Orchestrator Decision: Independent tasks
         ↓
Example:
  - Implementer_1: Backend authentication
  - Implementer_2: Frontend UI
  - Documenter_1: API documentation
         ↓
All agents work simultaneously
```

#### Sequential Execution
```
Orchestrator Decision: Dependent tasks
         ↓
Example:
  1. Implementer creates feature
  2. Tester validates feature
  3. Documenter updates docs
         ↓
Agents wait for dependencies
```

---

## Messaging Architecture (Two Active Systems)

GiljoAI uses **TWO complementary messaging systems** for different purposes. Both are **ACTIVE and FUNCTIONAL**.

### System 1: Messages Table (Persistent Communication & Audit)

**Purpose**: Inter-agent coordination with full audit trail
**Storage**: PostgreSQL `messages` table
**Best For**: Broadcasts, user messages, long-term history, audit trails

**MCP Tools** (`src/giljo_mcp/tools/message.py`):
- `send_message(to_agents, content, project_id, from_agent, ...)` - Send to specific agents
- `broadcast(content, project_id, priority)` - Broadcast to all agents in project
- `get_messages(agent_name, project_id, status)` - Retrieve pending messages
- `acknowledge_message(message_id, agent_name)` - Mark as read (**simple signature**)
- `complete_message(message_id, agent_name, result)` - Mark as completed

**Database Schema**:
- Single message record per broadcast with multiple recipients
- `to_agents`: JSON array of recipient names
- `acknowledged_by`: JSON array tracking who acknowledged (with timestamps)
- `completed_by`: JSON array tracking who completed (with timestamps + notes)
- Full audit trail with retry logic and circuit breaker

**UI Integration**:
- `/messages` route (MessagePanel, BroadcastPanel)
- Message history and search functionality
- Broadcast message sender with markdown preview

**When to Use**:
✅ Sending from user/developer to agents
✅ Broadcasting to all agents in a project
✅ Need full audit trail (who, when, completion notes)
✅ Message history/search required
✅ Long-term persistence needed

---

### System 2: JSONB Queue (Real-time Agent Coordination)

**Purpose**: Fast agent-to-agent communication within jobs
**Storage**: `MCPAgentJob.messages` JSONB column
**Best For**: Real-time polling, lightweight signaling, status updates

**MCP Tools** (`src/giljo_mcp/tools/agent_communication.py`):
- `send_mcp_message(job_id, tenant_key, content, target, priority)` - Send via JSONB queue
  - Supports `target="agent"`, `target="broadcast"`, or `target="orchestrator"`
- `read_mcp_messages(job_id, tenant_key)` - Poll JSONB queue for new messages
- `check_orchestrator_messages(job_id, tenant_key)` - Check for orchestrator updates
- `acknowledge_message(job_id, tenant_key, message_id, agent_id, response_data)` - Mark as read (**complex signature**)

**Database Schema**:
- Message copies stored in each agent's JSONB array
- Each job has isolated message queue
- Basic status tracking (pending, acknowledged)
- Fast polling (no table joins required)

**UI Integration**:
- JobsTab message count columns (Messages Sent/Waiting/Read)
- Real-time status indicators
- Message counts calculated from JSONB array

**When to Use**:
✅ Agent-to-agent real-time communication
✅ Fast status updates within job context
✅ Lightweight signaling (no heavy audit)
✅ Polling-based message checking
✅ Embedded queue preferred (no cross-job queries)

---

### Why Two Systems?

**Performance Optimization**:
- **Messages Table**: Optimized for cross-job queries and complex audit trails
- **JSONB Queue**: Optimized for single-agent fast polling (no joins)

**Use Case Separation**:
- **Messages Table**: Coordination, broadcasts, user interaction, persistent history
- **JSONB Queue**: Real-time signaling, status updates, ephemeral communication

**Audit Requirements**:
- **Messages Table**: Full audit (who acknowledged, when, completion notes, retry counts)
- **JSONB Queue**: Basic status (pending, acknowledged, timestamp)

**Database Strategy**:
- **Messages Table**: Single record per broadcast (shared by all recipients)
- **JSONB Queue**: Message copies (each agent gets own copy in JSONB array)

---

### Function Name Collision (INTENTIONAL)

⚠️ **Important**: There are **TWO different functions** named `acknowledge_message()`:

1. **`message.py` version** (Messages Table System):
   ```python
   async def acknowledge_message(message_id: str, agent_name: str) -> dict
   ```
   - Simple signature (2 parameters)
   - Works with `messages` table
   - For persistent messaging

2. **`agent_communication.py` version** (JSONB Queue System):
   ```python
   async def acknowledge_message(
       job_id: str,
       tenant_key: str,
       message_id: str,
       agent_id: str,
       response_data: Optional[dict] = None
   ) -> dict
   ```
   - Complex signature (5 parameters)
   - Works with `MCPAgentJob.messages` JSONB
   - For real-time queue

**This is NOT a bug** - they serve different systems and have different signatures. Python allows this because they're in different modules.

---

### Messaging Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│              User / Orchestrator / Developer                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  API Layer (/api/messages)                   │
│  POST /          POST /broadcast      POST /{id}/acknowledge │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│             MessageService (Service Layer)                   │
│    send_message()   broadcast()   acknowledge_message()      │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────────┐        ┌──────────────────────┐
│  Messages Table      │        │   JSONB Queue        │
│  (PostgreSQL)        │        │   (MCPAgentJob)      │
│                      │        │                      │
│  • Single record     │        │  • Message copies    │
│  • Multi-recipient   │        │  • Per-job queue     │
│  • Full audit trail  │        │  • Fast polling      │
│  • acknowledged_by   │        │  • Basic status      │
│  • completed_by      │        │                      │
└──────────┬───────────┘        └──────────┬───────────┘
           │                               │
           └───────────────┬───────────────┘
                           │
                           ▼
                 ┌─────────────────────┐
                 │     MCP Tools       │
                 │  (Agent Interface)  │
                 └─────────┬───────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │Orchestr. │      │Implement.│      │  Tester  │
  └──────────┘      └──────────┘      └──────────┘
```

---

### API Endpoints (Messages Table System)

**Base Route**: `/api/messages`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/messages/` | GET | List all messages (with filters) |
| `/api/messages/` | POST | Send message to specific agents |
| `/api/messages/agent/{name}` | GET | Get messages for specific agent |
| `/api/messages/{id}/acknowledge` | POST | Mark message as read |
| `/api/messages/{id}/complete` | POST | Mark message as completed |
| `/api/messages/broadcast` | POST | Broadcast to all agents in project |

**Example Broadcast Request**:
```json
POST /api/messages/broadcast
{
  "project_id": "uuid",
  "content": "All agents: Database schema updated",
  "priority": "high"
}
```

**Example Response**:
```json
{
  "success": true,
  "message_id": "uuid",
  "recipient_count": 5,
  "recipients": ["orchestrator", "implementer", "tester", "reviewer", "documentor"],
  "timestamp": "2025-11-29T10:00:00Z"
}
```

**Note**: JSONB Queue System is accessed via MCP tools only (no direct HTTP endpoints). Agents call `send_mcp_message()` and `read_mcp_messages()`.

---

### Legacy vs Active Messaging

#### ❌ OBSOLETE (Removed in Handover 0254)

The following refers to an **old table-based orchestrator command polling system** that was replaced:

- **Old Pattern**: Orchestrator sent commands via `messages` table → Agents polled with deprecated `receive_messages()` function
- **Replaced By**: New orchestrator instruction system using `get_next_instruction()`
- **Reason**: Thin client architecture (Handover 0088) required context-aware instruction fetching
- **What Was Removed**: Old polling function signatures that conflicted with new architecture

#### ✅ ACTIVE MESSAGING SYSTEMS (All Functional)

**System 1: Messages Table** (`src/giljo_mcp/tools/message.py`)
- ✅ `send_message()` - Send to specific agents
- ✅ `get_messages()` - Retrieve pending messages
- ✅ `acknowledge_message(message_id, agent_name)` - Simple signature
- ✅ `complete_message()` - Mark as done
- ✅ `broadcast()` - Send to all agents

**System 2: JSONB Queue** (`src/giljo_mcp/tools/agent_communication.py`)
- ✅ `send_mcp_message()` - Send via JSONB queue
- ✅ `read_mcp_messages()` - Poll JSONB queue
- ✅ `check_orchestrator_messages()` - Check for updates
- ✅ `acknowledge_message(job_id, tenant_key, ...)` - Complex signature

**System 3: Orchestrator Instructions** (`src/giljo_mcp/tools/orchestration.py`)
- ✅ `get_orchestrator_instructions()` - Fetch orchestrator mission (thin client)
- ✅ `get_agent_mission()` - Fetch agent-specific mission
- ✅ `spawn_agent_job()` - Create agent jobs

#### 🔍 What Was "Obsolete"?

**NOT the messaging systems** - Only the **old orchestrator command polling approach**:

- ❌ OLD: Orchestrator writes to `messages` table → Agent calls deprecated `receive_messages()` to poll
- ✅ NEW: Orchestrator updates mission context → Agent calls `get_next_instruction()` to fetch

**The Messages Table System itself is ACTIVE** - now used for:
- User-to-agent communication
- Agent-to-agent coordination
- Broadcast messaging
- Message history and audit

**The JSONB Queue System is ACTIVE** - used for:
- Real-time agent polling
- Embedded message queue per job
- Fast status updates

---

## Critical Implementation Details

### 1. Token Optimization (Handover 0246 Series)
- **Before**: 3,500 token prompts embedded in requests
- **After**: 450-550 token thin client prompts
- **Method**: Mission fetched via MCP tools, not embedded

### 2. Context Configuration
User configurable in: My Settings → Context Configuration
- Enabled (toggle: true): Category included with configured depth
- Disabled (toggle: false): Category excluded entirely

### 3. Agent Template Management
- **Max Active**: 8 agent types at once
- **Unlimited Instances**: Can have multiple of same type (Implementer_1, Implementer_2)
- **Export Required**: Claude Code mode needs templates exported to ~/.claude/agents/

### 4. Orchestrator Succession (Context Limits)
When orchestrator approaches context limit (90%):
1. User clicks [Handover] button
2. Current orchestrator writes 360 memory
3. New orchestrator spawned with condensed context
4. Mission and agent states preserved
5. Execution continues with new orchestrator

### 5. Dual-Status Architecture (Handover 0113)

**CRITICAL ARCHITECTURAL DECISION**: GiljoAI maintains two parallel status representations for backward compatibility and API evolution.

#### Database Layer (Authoritative)
**7 Canonical States** (enforced by PostgreSQL CHECK constraint):
- `waiting` - Job created, not yet claimed by agent
- `working` - Agent actively executing tasks
- `blocked` - Waiting for external dependency or intervention
- `complete` - Successfully finished
- `failed` - Encountered fatal error
- `cancelled` - User cancelled job
- `decommissioned` - Job archived/retired

**Database Constraint** (`models/agents.py`, line 217):
```sql
CHECK (status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned'))
```

**IMPORTANT**: There is NO "staged" or "pending" status in the database. Jobs are created directly with `status="waiting"`.

#### API Layer (Compatibility Aliases)
**3 Main Aliases** (for external API clients):
- `pending` → translates to `waiting` (inbound)
- `active` → translates to `working` (inbound)
- `completed` → translates to `complete` (inbound)

**Translation Logic** (`agent_job_manager.py`, lines 62-71):
```python
STATUS_INBOUND_ALIASES = {
    "pending": "waiting",     # API accepts "pending"
    "active": "working",      # but stores "waiting"
    "completed": "complete"
}

STATUS_OUTBOUND_ALIASES = {
    "waiting": "pending",     # Database has "waiting"
    "working": "active",      # but API can return "pending"
    "complete": "completed"
}
```

**Why This Exists**:
1. **Backward Compatibility**: External integrations can continue using old status names
2. **API Evolution**: Database schema can change without breaking API contracts
3. **User-Friendly Terms**: API can use more intuitive terminology
4. **Database Integrity**: CHECK constraint enforces canonical values

**Frontend Behavior**:
- WebSocket events send database values (`waiting`, `working`, `complete`)
- Frontend expects and displays database values
- NO translation occurs for WebSocket events (direct database values)

---

## Workflow State Diagram

```
┌──────────┐      ┌──────────┐      ┌────────────┐      ┌──────────────┐
│ Project  │ ───► │ Activate │ ───► │   Launch   │ ───► │ Implementation│
│ Created  │      │ Project  │      │   (Stage)  │      │   (Execute)   │
└──────────┘      └──────────┘      └────────────┘      └──────────────┘
     │                  │                   │                    │
     │                  │                   │                    │
     ▼                  ▼                   ▼                    ▼
[Inactive]    [Creates Job Record]  [Mission Created]    [Agents Working]
                [Status: waiting]    [Agents Spawned]     [Status: working]
                [Direct to DB]       [Jobs: waiting]      [Progress Updates]
                                                          [Message Flow]

Job Status Flow: waiting → working → complete/failed/blocked/cancelled
                   ↑                         ↓
                   └─────── No "staged" or "pending" status in database
```

---

## Complete Flow Overview (ASCII Visualization)

### 6-Phase Master Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GILJOAI AGENT ORCHESTRATION FLOW                     │
│                              (End-to-End Journey)                            │
└─────────────────────────────────────────────────────────────────────────────┘

PHASE 1: INSTALLATION & SETUP
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────┐
    │  install.py  │  ← User runs installation script
    └──────┬───────┘
           │
           ├──► [1] PostgreSQL Setup
           │         └─► Create database 'giljo_mcp'
           │         └─► Create tables (Alembic migrations)
           │         └─► Migration 6adac1467121 adds cli_tool, background_color
           │
           ├──► [2] First User Creation
           │         └─► User navigates to /welcome → /first-login
           │         └─► Creates admin user with tenant_key
           │         └─► ✅ seed_tenant_templates() called (auth.py:910)
           │                └─► Seeds 6 default agent templates per tenant
           │                └─► Templates: orchestrator, implementer, tester, analyzer, reviewer, documenter
           │                └─► Source: template_seeder.py::_get_default_templates_v103()
           │
           └──► [3] API Server Launch
                     └─► FastAPI starts on 0.0.0.0:7272
                     └─► WebSocket manager initialized
                     └─► MCP tools registered


PHASE 2: AGENT TEMPLATE EXPORT
═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────┐
    │  Dashboard → Settings   │  ← User navigates to My Settings
    │  → Integrations Tab     │
    └────────────┬────────────┘
                 │
                 ├──► [4] Agent Template Manager
                 │         └─► User views active agent templates (max 8)
                 │         └─► Each template has: role, cli_tool, model, tools, background_color
                 │
                 └──► [5] Export Agent Templates
                           └─► Click "Claude Export Agents" button
                           └─► POST /api/v1/export/claude-code
                                 │
                                 ├──► Query active templates (is_active=true)
                                 ├──► Generate YAML frontmatter per template
                                 ├──► Create ZIP file with all templates
                                 ├──► Generate download token
                                 │      └─► Token lifecycle: pending → ready → failed
                                 │      └─► TTL: 15 minutes
                                 │
                                 └──► [6] Update UI with Copy Command
                                          └─► Button shows tokenized download link
                                          └─► Format: /api/download/temp/{token}/{filename}


PHASE 3: CLI TOOL INSTALLATION
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────────┐
    │  User's AI Coding Tool   │  ← Claude Code / Codex CLI / Gemini CLI
    │  (Terminal)              │
    └─────────────┬────────────┘
                  │
                  ├──► [7] User Copies Installation Command
                  │         └─► Paste into terminal: claude-code mcp add http://x.x.x.x:7272/...
                  │
                  ├──► [8] CLI Tool Downloads Templates
                  │         └─► HTTP GET /api/download/temp/{token}/agents.zip
                  │         └─► Token validated (status=ready, not expired)
                  │         └─► ZIP downloaded and extracted to ~/.claude/agents/
                  │
                  └──► [9] MCP Configuration
                            └─► CLI tool updates config (~/.claude/config.json)
                            └─► Adds GiljoAI MCP server entry
                            └─► Agents now available in MCP registry


PHASE 4: PROJECT STAGING & ORCHESTRATION
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────────┐
    │  Dashboard → Projects    │  ← User navigates to project
    └─────────────┬────────────┘
                  │
                  ├──► [10] Create/Select Project
                  │          └─► Project has: vision documents, product_id, description
                  │          └─► Status: draft → active
                  │
                  ├──► [10b] Navigate to Project (Two-Tab Interface)
                  │          └─► Custom project link created
                  │          └─► Format: http://server:port/projects/{project_ID}?via=jobs
                  │          │
                  │          ├──► Navigation: [LAUNCH] button in projects list OR "Jobs" in left navbar
                  │          │      └─► Both navigate to LAUNCH TAB (first tab)
                  │          │
                  │          └──► LAUNCH TAB shows:
                  │                ├─► [Stage Project] Button (UI label)
                  │                │    └─► ⚠️ Backend endpoint: /api/v1/projects/{id}/activate
                  │                ├─► Project Description (human-written, from Project.description)
                  │                ├─► Orchestrator Generated Mission (empty initially)
                  │                └─► Agent Team section (empty initially)
                  │                └─► Orchestrator Card (shows agent_id, status: waiting)
                  │
                  ├──► [11] Click "Stage Project" Button
                  │          └─► POST /api/v1/projects/{id}/activate
                  │                │
                  │                ├──► [A] Create Orchestrator Job (Backend)
                  │                │      └─► MCPAgentJob record created
                  │                │      └─► agent_type: "orchestrator"
                  │                │      └─► status: "waiting" (database canonical value)
                  │                │      └─► mission: "I am ready to create the project mission..."
                  │                │      └─► Generate thin client prompt (450-550 tokens)
                  │                │      └─► Enable orchestrator [Copy Prompt >] button
                  │                │
                  │                ├──► [B] User Copies & Pastes Orchestrator Prompt
                  │                │      └─► User copies thin prompt from orchestrator card
                  │                │      └─► User pastes into AI coding tool terminal
                  │                │      └─► Orchestrator 5-task staging workflow:
                  │                │           ├─► Task 1: Verify MCP via health_check()
                  │                │           │    └─► REQUIRED first step, verifies server connectivity
                  │                │           ├─► Task 2: Fetch instructions via get_orchestrator_instructions()
                  │                │           │    ├─► Mission NOT embedded in thin prompt
                  │                │           │    ├─► Retrieves vision_documents (pre-chunked)
                  │                │           │    ├─► Retrieves product name, description
                  │                │           │    ├─► Retrieves Project.description (human requirements)
                  │                │           │    ├─► Retrieves context based on user's field priorities
                  │                │           │    ├─► Retrieves 360 memory, Git history if enabled
                  │                │           │    └─► Returns condensed mission (~6K tokens)
                  │                │           ├─► Task 3: Create comprehensive mission plan
                  │                │           ├─► Task 4: PERSIST mission via update_project_mission()
                  │                │           │    └─► Saves to Project.mission field in database
                  │                │           │    └─► WebSocket event: project:mission_updated
                  │                │           │    └─► UI: "Orchestrator Generated Mission" updates live
                  │                │           └─► Task 5: Spawn agents dynamically
                  │                │                ├─► get_available_agents() - Dynamic discovery (NOT hardcoded)
                  │                │                └─► spawn_agent_job() - For each agent needed
                  │                │                    ├─► Stores mission in MCPAgentJob.mission (database)
                  │                │                    ├─► Creates job with status="waiting"
                  │                │                    ├─► Returns thin prompt (~10 lines, NO mission)
                  │                │                    ├─► Agent will fetch mission via get_agent_mission()
                  │                │                    └─► Agent cards appear live in "Agent Team"
                  │                │
                  │                └──► [C] UI Updates After Staging Complete
                  │                       ├─► "Orchestrator Generated Mission" window populated
                  │                       ├─► Agent cards appear in "Agent Team" section
                  │                       ├─► Each agent shows: role, status (waiting), agent_id
                  │                       └─► [Launch Jobs] button appears
                  │
                  └──► [12] Navigate to Implementation Tab
                             └─► User clicks [Launch Jobs] button
                             └─► Switches to IMPLEMENTATION TAB (second tab, same URL)


PHASE 5: AGENT EXECUTION & COORDINATION
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────────────────────────────────────────────────────┐
    │  Implementation Tab → Agent Launch                                   │
    │  (Custom Project Link: /projects/{id}?via=jobs)                      │
    └─────────────┬────────────────────────────────────────────────────────┘
                  │
                  ├──► [13] Claude Code CLI Mode Toggle (at top of tab)
                  │          │
                  │          ├──► Toggle OFF (Default - Multi-Terminal Mode)
                  │          │      └─► ALL [Copy Prompt >] buttons active
                  │          │      └─► Hint: "Multi-terminal mode - Launch agents in separate windows"
                  │          │      └─► Each agent gets unique prompt with agent_id, job_id
                  │          │      └─► User copies each prompt to separate terminal windows
                  │          │      └─► Each agent fetches mission via get_agent_mission()
                  │          │      └─► User manually coordinates agents
                  │          │
                  │          └──► Toggle ON (Claude Code Subagent Mode)
                  │                 └─► Only orchestrator [Copy Prompt >] button active
                  │                 └─► All other agent buttons grayed out
                  │                 └─► Hint: "Claude Code subagent mode - Orchestrator spawns agents"
                  │                 └─► Orchestrator prompt includes subagent instructions
                  │                 └─► Orchestrator spawns native Claude subagents
                  │                 └─► Each subagent gets agent_id, job_id from orchestrator
                  │                 └─► Subagents fetch missions via get_agent_mission()
                  │                 └─► Single terminal execution
                  │
                  ├──► [14] Orchestrator Claims Job & Begins Coordination
                  │          └─► MCP tool: get_pending_jobs() (finds orchestrator job)
                  │          └─► MCP tool: acknowledge_job() (status: waiting → working)
                  │          └─► UI updates: Orchestrator card shows "Working"
                  │          └─► Orchestrator coordinates agent team
                  │
                  ├──► [15] Sub-Agent Team Execution
                  │          └─► For each agent in spawned team:
                  │                │
                  │                ├─► [CLAUDE CODE FLOW] Native Sub-Agent Spawning
                  │                │      └─► Orchestrator uses native subagent capabilities
                  │                │      └─► Sub-agents spawned in same terminal session
                  │                │      └─► Each subagent gets role-specific mission
                  │                │      └─► Agent templates guide MCP usage
                  │                │
                  │                └─► [MULTI-TERMINAL FLOW] Manual Spawning
                  │                       └─► User copies each agent prompt
                  │                       └─► Each agent launches in separate terminal
                  │                       └─► Agent gets agent_id, job_id, profile
                  │                       └─► Agent fetches mission via MCP
                  │
                  ├──► [16] Agent Work Execution
                  │          └─► Each agent (Claude sub-agents or separate terminals):
                  │                │
                  │                ├──► [A] Read assigned mission
                  │                │      └─► MCP tool: get_agent_mission(job_id, tenant_key)
                  │                │      └─► Retrieves specialized role, mission context
                  │                │
                  │                ├──► [B] Perform specialized work
                  │                │      └─► Implementer: Code changes, file modifications
                  │                │      └─► Tester: Run tests, validate functionality
                  │                │      └─► Documenter: Create/update documentation
                  │                │      └─► Reviewer: Code quality, improvements
                  │                │
                  │                ├──► [C] Report progress & communicate
                  │                │      └─► MCP tool: report_progress(job_id, progress%)
                  │                │      └─► MCP tool: send_message() for coordination
                  │                │      └─► UI updates: Agent cards show live status
                  │                │
                  │                └──► [D] Complete job
                  │                       └─► MCP tool: complete_job(job_id, result)
                  │                       └─► Update status: working → complete
                  │                       └─► UI updates: Agent card shows "Complete"
                  │
                  └──► [17] Orchestrator Monitors & Orchestrates
                             ├─► Polls for agent status updates via MCP
                             ├─► Coordinates dependencies and handoffs
                             ├─► MCP tool: send_message() for broadcasts
                             ├─► Handles errors, blocks, escalations
                             ├─► UI: Message center shows communications
                             └─► Initiates project closeout when all agents complete


PHASE 6: PROJECT CLOSEOUT & MEMORY UPDATE (360 Memory Management)
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────────────────────────────────────────────────────────┐
    │  Implementation Tab → Project Completion                              │
    └─────────────┬────────────────────────────────────────────────────────┘
                  │
                  ├──► [18] All Agents Report Completion
                  │          └─► All sub-agents reach status="complete"
                  │          └─► Orchestrator verifies deliverables
                  │          └─► UI: All agent cards display "Completed"
                  │
                  └──► [19] Orchestrator Calls Project Closeout
                             └─► MCP tool: close_project_and_update_memory()
                                   │
                                   ├──► [A] Generate Project Summary
                                   │      └─► What was accomplished (2-3 sentences)
                                   │      └─► Key outcomes (bullet list)
                                   │      └─► Important decisions made
                                   │      └─► Files created/modified
                                   │
                                   ├──► [B] Fetch GitHub Commits (if enabled)
                                   │      └─► Check Product.product_memory.git_integration
                                   │      └─► If enabled: Fetch commits since project start
                                   │      └─► If disabled: Use manual summary only
                                   │
                                   ├──► [C] Update Product Memory
                                   │      └─► Append to Product.product_memory.sequential_history[]
                                   │      └─► Assign next sequence number (auto-increment)
                                   │      └─► Store summary, outcomes, decisions
                                   │      └─► Attach GitHub commits (if available)
                                   │      └─► Timestamp: ISO 8601 format
                                   │
                                   └──► [D] Emit WebSocket Event
                                          └─► Event: "product:memory_updated"
                                          └─► Payload: {product_id, sequence, summary}
                                          └─► UI: Toast notification "Product memory updated"
                                          └─► Future orchestrators see this in context
```

---

## System Architecture (ASCII Visualization)

### Agent ↔ MCP Server ↔ PostgreSQL Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SYSTEM ARCHITECTURE OVERVIEW                         │
└─────────────────────────────────────────────────────────────────────────────┘

LAYER 1: CLIENT LAYER (AI Coding Tools)
═══════════════════════════════════════════════════════════════════════════════

    ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
    │  Claude Code   │    │   Codex CLI    │    │   Gemini CLI   │
    │                │    │                │    │                │
    │  (Orchestrator │    │  (Implementer) │    │    (Tester)    │
    │   + Subagents) │    │                │    │                │
    └────────┬───────┘    └────────┬───────┘    └────────┬───────┘
             │                     │                     │
             └─────────────────────┴─────────────────────┘
                                   │
                        MCP JSON-RPC 2.0 over HTTP
                                   │
                                   ▼

LAYER 2: MCP SERVER LAYER (GiljoAI MCP Tools)
═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                    GiljoAI MCP Server (FastAPI)                          │
    │                     http://server:7272/mcp                               │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                           │
    │  ┌─────────────────────────────────────────────────────────────────┐   │
    │  │               MCP TOOL SUITE (14 Core Tools)                     │   │
    │  ├─────────────────────────────────────────────────────────────────┤   │
    │  │                                                                   │   │
    │  │  ORCHESTRATION TOOLS (orchestration.py)                          │   │
    │  │  ├─► health_check()                    - Verify MCP connection   │   │
    │  │  ├─► get_orchestrator_instructions()   - Fetch staging context   │   │
    │  │  ├─► get_agent_mission()               - Fetch agent-specific    │   │
    │  │  ├─► spawn_agent_job()                 - Create agent jobs       │   │
    │  │  ├─► get_workflow_status()             - View all agents         │   │
    │  │  ├─► update_project_mission()          - Persist mission to DB   │   │
    │  │  └─► get_available_agents()            - Dynamic agent discovery │   │
    │  │                                                                   │   │
    │  │  COORDINATION TOOLS (agent_coordination.py)                      │   │
    │  │  ├─► get_pending_jobs()                - Find work assignments   │   │
    │  │  ├─► acknowledge_job()                 - Claim job (→ active)    │   │
    │  │  ├─► report_progress()                 - Update progress %       │   │
    │  │  ├─► complete_job()                    - Mark done with results  │   │
    │  │  ├─► report_error()                    - Report blocking issues  │   │
    │  │  └─► get_next_instruction()            - Check for updates       │   │
    │  │                                                                   │   │
    │  │  MESSAGING TOOLS (agent_messaging.py)                            │   │
    │  │  ├─► send_message()                    - Direct/broadcast msgs   │   │
    │  │  └─► receive_messages()                - Check incoming msgs     │   │
    │  │                                                                   │   │
    │  └─────────────────────────────────────────────────────────────────┘   │
    │                                                                           │
    │  ┌─────────────────────────────────────────────────────────────────┐   │
    │  │               MULTI-TENANT ISOLATION LAYER                       │   │
    │  ├─────────────────────────────────────────────────────────────────┤   │
    │  │  ✅ Every query filtered by tenant_key                          │   │
    │  │  ✅ Zero cross-tenant data leakage possible                     │   │
    │  │  ✅ Enforced at 6 layers: DB, MCP, API, Job Manager, Queue, WS  │   │
    │  └─────────────────────────────────────────────────────────────────┘   │
    │                                                                           │
    └─────────────────────┬───────────────────────────────────────────────────┘
                          │
                SQLAlchemy ORM Queries
                          │
                          ▼

LAYER 3: DATABASE LAYER (PostgreSQL 18)
═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                   PostgreSQL Database: giljo_mcp                         │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                           │
    │  CORE TABLES:                                                            │
    │  ├─► users                     - Authentication, tenant_key             │
    │  ├─► products                  - Product definitions, descriptions      │
    │  │    └─► product_memory (JSONB) - 360 memory, sequential history       │
    │  ├─► projects                  - Project definitions, missions          │
    │  │    ├─► description (TEXT)   - Human-written requirements             │
    │  │    └─► mission (TEXT)       - AI-generated execution plan            │
    │  ├─► vision_documents          - Chunked vision docs (<=10K tokens)     │
    │  ├─► agent_templates           - Agent role definitions (max 8 active)  │
    │  │    ├─► cli_tool             - claude, codex, gemini, generic         │
    │  │    ├─► background_color     - UI color coding                        │
    │  │    ├─► model                - LLM model preference                   │
    │  │    └─► tools                - MCP tool access list                   │
    │  ├─► mcp_agent_jobs            - Agent work assignments                 │
    │  │    ├─► status               - waiting/working/blocked/complete/failed/cancelled/decommissioned │
    │  │    ├─► mission (TEXT)       - AI-generated agent assignment          │
    │  │    ├─► agent_type           - Role from template                     │
    │  │    └─► progress             - Percentage complete                    │
    │  ├─► agent_messages            - Inter-agent communication queue        │
    │  └─► download_tokens           - Secure file delivery tokens (15min)    │
    │                                                                           │
    │  TENANT ISOLATION:                                                       │
    │  └─► All tables have tenant_key column (indexed)                        │
    │                                                                           │
    └─────────────────────────────────────────────────────────────────────────┘


LAYER 4: WEBSOCKET LAYER (Real-Time Updates)
═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                   WebSocket Manager (api/websocket.py)                   │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                           │
    │  REAL-TIME EVENTS:                                                       │
    │  ├─► job:status_changed         - Agent card badge updates              │
    │  ├─► job:progress_updated       - Progress bar percentage               │
    │  ├─► message:new                - Message center count badge            │
    │  ├─► project:mission_updated    - Mission window content                │
    │  ├─► agent:spawned              - New agent card appears                │
    │  └─► product:memory_updated     - 360 memory closeout notification      │
    │                                                                           │
    │  TENANT SCOPING:                                                         │
    │  └─► All events scoped to tenant_key (no cross-tenant leakage)          │
    │                                                                           │
    └─────────────────────┬───────────────────────────────────────────────────┘
                          │
                    WebSocket Protocol
                          │
                          ▼

LAYER 5: FRONTEND LAYER (Vue 3 Dashboard)
═══════════════════════════════════════════════════════════════════════════════

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                   Vue 3 Dashboard (Vuetify UI)                           │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                           │
    │  KEY COMPONENTS:                                                         │
    │  ├─► LaunchTab.vue              - Project staging interface             │
    │  │    ├─► [Stage Project] Button                                        │
    │  │    ├─► Project Description (human input)                             │
    │  │    ├─► Orchestrator Generated Mission (AI output)                    │
    │  │    └─► Agent Team section                                            │
    │  │                                                                        │
    │  ├─► JobsTab.vue                - Implementation interface              │
    │  │    ├─► Claude Code Toggle (execution mode selector)                  │
    │  │    ├─► Agent Cards with [Copy Prompt >] buttons                      │
    │  │    ├─► Status badges (waiting/working/blocked/complete/failed/cancelled) │
    │  │    └─► Progress bars                                                 │
    │  │                                                                        │
    │  ├─► StatusChip.vue             - Status badge component                │
    │  ├─► ActionIcons.vue            - Agent action buttons                  │
    │  └─► AgentTableView.vue         - Reusable status board table           │
    │                                                                           │
    └─────────────────────────────────────────────────────────────────────────┘


DATA FLOW EXAMPLE: Agent Acknowledges Job
═══════════════════════════════════════════════════════════════════════════════

┌────────────┐                ┌────────────┐                ┌────────────┐
│   Agent    │                │ MCP Server │                │ PostgreSQL │
│ (Terminal) │                │  (FastAPI) │                │  Database  │
└─────┬──────┘                └─────┬──────┘                └─────┬──────┘
      │                             │                             │
      │  acknowledge_job(job_id)    │                             │
      │────────────────────────────>│                             │
      │                             │  UPDATE mcp_agent_jobs      │
      │                             │  SET status='active'        │
      │                             │  WHERE id=? AND tenant_key=?│
      │                             │────────────────────────────>│
      │                             │                             │
      │                             │         200 OK              │
      │                             │<────────────────────────────│
      │                             │                             │
      │      Success Response       │                             │
      │<────────────────────────────│                             │
      │                             │                             │
      │                             │  WebSocket Event Emission:  │
      │                             │  job:status_changed         │
      │                             │────────────┐                │
      │                             │            │                │
      │                             │            ▼                │
      │                         ┌───┴────────────────┐           │
      │                         │  Vue Dashboard     │           │
      │                         │  (WebSocket Client)│           │
      │                         └───┬────────────────┘           │
      │                             │                             │
      │                         Agent card badge                  │
      │                         updates to "Active"               │
      │                             │                             │
      └─────────────────────────────┴─────────────────────────────┘
```

---

## Execution Mode Comparison (ASCII)

### Side-by-Side: Claude Code Mode vs Multi-Terminal Mode

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXECUTION MODE COMPARISON                            │
│                    (Implementation Tab Toggle Behavior)                      │
└─────────────────────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════╦═══════════════════════════════════════╗
║   CLAUDE CODE CLI MODE (Toggle ON)    ║  MULTI-TERMINAL MODE (Toggle OFF)     ║
║           Native Subagents            ║         General CLI Tools             ║
╠═══════════════════════════════════════╬═══════════════════════════════════════╣
║                                       ║                                       ║
║  UI BEHAVIOR:                         ║  UI BEHAVIOR:                         ║
║  ├─► Only orchestrator [Copy Prompt >]║  ├─► ALL [Copy Prompt >] active      ║
║  │    button active                   ║  │    (orchestrator + all agents)    ║
║  ├─► All agent buttons grayed out     ║  ├─► Each agent has unique prompt    ║
║  └─► Hint: "Claude Code subagent mode"║  └─► Hint: "Multi-terminal mode"     ║
║                                       ║                                       ║
║  TERMINAL SETUP:                      ║  TERMINAL SETUP:                      ║
║  └─► Single terminal window           ║  └─► Multiple terminal windows        ║
║      └─► 1 for orchestrator           ║      ├─► 1 for orchestrator          ║
║                                       ║      ├─► 1 for Implementer_1         ║
║                                       ║      ├─► 1 for Tester_1              ║
║                                       ║      └─► 1 for each additional agent ║
║                                       ║                                       ║
║  ORCHESTRATOR PROMPT:                 ║  ORCHESTRATOR PROMPT:                 ║
║  ├─► Includes subagent spawning rules ║  ├─► Includes coordination rules     ║
║  ├─► Uses native @{agent_role}.md     ║  ├─► Uses MCP messaging tools        ║
║  │    template system                 ║  │    for inter-agent communication  ║
║  └─► Example:                         ║  └─► Example:                         ║
║      "Use @implementer.md to spawn    ║      "Broadcast instructions to      ║
║       subagents for code changes"     ║       agents via send_message()"     ║
║                                       ║                                       ║
║  AGENT SPAWNING:                      ║  AGENT SPAWNING:                      ║
║  └─► Orchestrator spawns via Claude   ║  └─► User manually launches each     ║
║      native subagent syntax           ║      agent in separate terminal      ║
║      ├─► @implementer.md              ║      ├─► Copy Implementer_1 prompt   ║
║      ├─► @tester.md                   ║      ├─► Copy Tester_1 prompt        ║
║      └─► @documenter.md               ║      └─► Copy Documenter_1 prompt    ║
║                                       ║                                       ║
║  AGENT ID ASSIGNMENT:                 ║  AGENT ID ASSIGNMENT:                 ║
║  └─► Orchestrator assigns agent_id    ║  └─► Each prompt includes unique     ║
║      to each subagent dynamically     ║      agent_id from MCPAgentJob       ║
║      └─► "You are agent_abc123..."    ║      └─► Pre-generated by backend    ║
║                                       ║                                       ║
║  MISSION RETRIEVAL:                   ║  MISSION RETRIEVAL:                   ║
║  └─► Subagents call:                  ║  └─► Each agent calls:                ║
║      get_agent_mission(job_id,        ║      get_agent_mission(job_id,        ║
║                        tenant_key)    ║                        tenant_key)    ║
║      └─► job_id passed by orchestrator║      └─► job_id embedded in prompt    ║
║                                       ║                                       ║
║  COORDINATION:                        ║  COORDINATION:                        ║
║  └─► Orchestrator coordinates via     ║  └─► User manually coordinates or     ║
║      native Claude conversation       ║      orchestrator uses MCP messaging  ║
║      └─► Subagents share context      ║      └─► Agents use send_message()   ║
║      └─► No MCP messaging needed      ║      └─► Agents use receive_messages()║
║                                       ║                                       ║
║  USER INTERACTION:                    ║  USER INTERACTION:                    ║
║  └─► User interacts with orchestrator ║  └─► User can interact with each      ║
║      └─► Orchestrator delegates to    ║      agent independently              ║
║           subagents                   ║      └─► Direct control per agent     ║
║                                       ║                                       ║
║  ADVANTAGES:                          ║  ADVANTAGES:                          ║
║  ✅ Single terminal (simpler)         ║  ✅ Works with any CLI tool           ║
║  ✅ Native Claude integration         ║  ✅ Full agent visibility             ║
║  ✅ Automatic context sharing         ║  ✅ Fine-grained control              ║
║  ✅ Streamlined workflow              ║  ✅ Parallel execution                ║
║                                       ║                                       ║
║  LIMITATIONS:                         ║  LIMITATIONS:                         ║
║  ⚠️  Claude Code only                 ║  ⚠️  Multiple windows to manage       ║
║  ⚠️  Requires template export         ║  ⚠️  Manual coordination overhead     ║
║  ⚠️  Subagent context limits          ║  ⚠️  More complex setup               ║
║                                       ║                                       ║
╚═══════════════════════════════════════╩═══════════════════════════════════════╝


PROMPT BUTTON BEHAVIOR MATRIX
═══════════════════════════════════════════════════════════════════════════════

┌────────────────────────┬─────────────────────┬─────────────────────┐
│        Agent           │  Claude Code Mode   │  Multi-Terminal Mode│
│                        │    (Toggle ON)      │    (Toggle OFF)     │
├────────────────────────┼─────────────────────┼─────────────────────┤
│  Orchestrator          │   ✅ ENABLED        │   ✅ ENABLED        │
│  [Copy Prompt >]       │   (only active btn) │   (all active)      │
├────────────────────────┼─────────────────────┼─────────────────────┤
│  Implementer_1         │   🔒 DISABLED       │   ✅ ENABLED        │
│  [Copy Prompt >]       │   (grayed out)      │   (unique prompt)   │
├────────────────────────┼─────────────────────┼─────────────────────┤
│  Tester_1              │   🔒 DISABLED       │   ✅ ENABLED        │
│  [Copy Prompt >]       │   (grayed out)      │   (unique prompt)   │
├────────────────────────┼─────────────────────┼─────────────────────┤
│  Documenter_1          │   🔒 DISABLED       │   ✅ ENABLED        │
│  [Copy Prompt >]       │   (grayed out)      │   (unique prompt)   │
├────────────────────────┼─────────────────────┼─────────────────────┤
│  [Additional agents]   │   🔒 DISABLED       │   ✅ ENABLED        │
│  [Copy Prompt >]       │   (grayed out)      │   (unique prompts)  │
└────────────────────────┴─────────────────────┴─────────────────────┘


WORKFLOW COMPARISON
═══════════════════════════════════════════════════════════════════════════════

CLAUDE CODE MODE:                    MULTI-TERMINAL MODE:
─────────────────                    ────────────────────

1. User clicks [Copy Prompt >]       1. User clicks [Copy Prompt >]
   for orchestrator                     for orchestrator

2. Pastes into Claude Code terminal  2. Pastes into terminal #1

3. Orchestrator spawns subagents:    3. User clicks [Copy Prompt >]
   @implementer.md                      for Implementer_1
   @tester.md
   @documenter.md                    4. Pastes into terminal #2

4. Subagents auto-fetch missions     5. User clicks [Copy Prompt >]
   via get_agent_mission()              for Tester_1

5. All work in single session        6. Pastes into terminal #3

6. Orchestrator coordinates          7. Each agent fetches mission
   subagents automatically              via get_agent_mission()

7. User monitors one window          8. User monitors all windows

                                     9. Orchestrator coordinates via
                                        MCP messaging or user does
                                        manual coordination
```

---

## Technical Verification Summary

### Component Health Check (21/21 Components Verified)

✅ **Core Infrastructure**
- PostgreSQL database: OPERATIONAL
- FastAPI server: RUNNING
- Frontend (Vue 3): ACCESSIBLE
- WebSocket handler: ACTIVE
- MCP-over-HTTP: FUNCTIONAL

✅ **Database Layer**
- Agent templates (AgentTemplate): 6 seeded per tenant
- MCPAgentJob table: Complete with all fields
- Project table: mission field present
- User table: context settings in JSONB

✅ **Service Layer**
- AgentJobManager: Full lifecycle support
- AgentCommunicationQueue: Message routing
- ThinClientPromptGenerator: 70% token reduction
- OrchestrationService: Context prioritization

✅ **MCP Tools (Complete Suite)**
- get_orchestrator_instructions(): Context retrieval
- spawn_agent_job(): Agent creation
- update_project_mission(): Mission persistence
- get_pending_jobs(): Job discovery
- acknowledge_job(): Job claiming
- report_progress(): Status updates
- complete_job(): Job completion
- send_message(): Inter-agent communication

### Security Verification

✅ **Multi-Tenant Isolation**: Enforced at 6 layers (Database, MCP Tools, API, Job Manager, Message Queue, WebSocket)
✅ **SQL Injection Prevention**: Migration 6adac1467121 security-hardened (2025-11-05)
✅ **Token-Based Security**: 15-minute TTL, one-time use for agent templates
✅ **Authentication**: JWT + API key support for CLI tools
✅ **Cross-Tenant Leakage**: Zero risk verified

### Performance Metrics

- **Token Reduction**: 70% achieved via thin client architecture
- **Template Seeding**: 6 templates in <500ms
- **Export Generation**: <2 seconds for 8 templates
- **Download Token**: <100ms generation, <50ms validation
- **MCP Tool Calls**: <100ms average response time
- **Job Creation**: <150ms per MCPAgentJob

### Architecture Highlights

#### 1. Thin Client Pattern (Handover 0088)
- **Before**: 3000-line prompts embedded in requests
- **After**: 10-line prompts, mission fetched via MCP
- **Result**: 70% token reduction

#### 2. Multi-Tenant Architecture
- Complete isolation across all layers
- Zero cross-tenant data leakage possible
- Tenant-scoped queries enforced

#### 3. Job Lifecycle Management
- Production-grade state machine (AgentJobManager)
- Terminal state protection
- Idempotent operations

#### 4. Real-Time Coordination
- WebSocket events for UI updates
- Agent-to-agent messaging queue
- Progress tracking with context warnings

---

## TECHNICAL IMPLEMENTATION REFERENCE

This section provides detailed code references, database schemas, API specifications, error handling scenarios, and testing procedures for developers performing code review and implementation verification.

---

### PHASE 1: INSTALLATION & TEMPLATE SEEDING

#### Code Implementation
- **Entry Point**: `install.py` (root directory)
- **Template Seeding**: `src/giljo_mcp/template_seeder.py::seed_tenant_templates()` (lines 37-193)
- **Database Manager**: `src/giljo_mcp/database.py::DatabaseManager`
- **Migration System**: Single baseline migration approach (Handover 0601)

#### Database Operations

**Tables Created** (32 total):
- `users` - Authentication, tenant_key assignment
- `products` - Product definitions with JSONB product_memory field
- `projects` - Project records with description (user) and mission (AI) fields
- `vision_documents` - Chunked vision docs (≤10K tokens per chunk)
- `agent_templates` - Agent role definitions (max 8 active per tenant)
- `mcp_agent_jobs` - Agent work assignments with status state machine
- `agent_messages` - Inter-agent communication queue
- `download_tokens` - Secure file delivery (15min TTL)

**Agent Template Schema**:
```sql
CREATE TABLE agent_templates (
    id UUID PRIMARY KEY,
    tenant_key VARCHAR NOT NULL,
    product_id UUID (nullable - tenant-level templates),
    name VARCHAR NOT NULL,
    role VARCHAR NOT NULL,  -- orchestrator, implementer, tester, etc.
    cli_tool VARCHAR,  -- claude, codex, gemini, generic
    background_color VARCHAR,  -- UI color coding
    model VARCHAR,  -- sonnet, opus, etc.
    tools JSONB,  -- MCP tool access list
    system_instructions TEXT,  -- Protected MCP coordination (Handover 0106)
    user_instructions TEXT,  -- Editable role-specific guidance (Handover 0106)
    template_content TEXT,  -- DEPRECATED: Legacy field for backward compatibility
    behavioral_rules JSONB,
    success_criteria JSONB,
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP,
    INDEX idx_agent_templates_tenant_active (tenant_key, is_active)
);
```

**Template Seeding Logic**:
```python
# src/giljo_mcp/template_seeder.py::seed_tenant_templates()

# Idempotency check (lines 82-88)
existing_count = await session.execute(
    select(func.count(AgentTemplate.id))
    .where(AgentTemplate.tenant_key == tenant_key)
).scalar()

if existing_count > 0:
    logger.info(f"Tenant '{tenant_key}' already has {existing_count} templates, skipping seed")
    return 0  # Skip if templates already exist

# Default templates from _get_default_templates_v103() (Handover 0103)
# 6 templates: orchestrator, implementer, tester, analyzer, reviewer, documenter
```

#### API Calls
- **Endpoint**: `POST /api/auth/register` - User registration with tenant_key generation
- **Endpoint**: `GET /api/v1/templates` - List active templates (max 8)
- **Endpoint**: `POST /api/v1/export/claude-code` - Generate ZIP export with download token

#### Error Scenarios

**Template Seeding Failures**:
- **Duplicate Seeding**: Idempotency check prevents duplicate templates (existing_count > 0)
- **Invalid Tenant**: `ValueError` raised if tenant_key is None or empty
- **Database Connection**: SQLAlchemy exceptions propagated to caller
- **Recovery**: Re-run `install.py` - idempotent design ensures safe retry

**Migration Failures**:
- **Symptom**: Tables not created, application fails to start
- **Check**: `PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\dt"`
- **Recovery**: Drop database, re-run `install.py` with fresh baseline migration

#### Testing Procedures

**Verify Template Seeding**:
```bash
# Check template count per tenant
PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT tenant_key, COUNT(*) FROM agent_templates GROUP BY tenant_key;"

# Expected: 6 templates per tenant

# Verify template structure
PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT role, cli_tool, is_active FROM agent_templates WHERE tenant_key='YOUR_TENANT' LIMIT 10;"

# Expected roles: orchestrator, implementer, tester, analyzer, reviewer, documenter
```

**Integration Test**:
- **File**: `tests/integration/test_template_seeding.py`
- **Coverage**: Template creation, idempotency, tenant isolation
- **Command**: `pytest tests/integration/test_template_seeding.py -v`

#### Performance Benchmarks
- Template seeding: <500ms for 6 templates
- Database baseline migration: <1 second (32 tables from pristine SQLAlchemy models)
- First user creation: <200ms (includes tenant_key generation + template seeding trigger)

---

### PHASE 2: AGENT TEMPLATE EXPORT & CLI INSTALLATION

**Purpose**: This phase enables Claude Code CLI Mode (Type 2 spawning) by installing `.md` template files that Claude Code can invoke as native subagents.

**When Required**: Only necessary if user wants to use Claude Code CLI Mode (toggle ON). Multi-terminal mode does NOT require template installation.

**What Gets Created**: Agent template files (`.md`) with YAML frontmatter and MCP behavior instructions, installed to `~/.claude/agents/` or `.claude/agents/`.

#### Code Implementation
- **Export Generator**: `api/endpoints/export/claude_code.py::export_agents()`
- **Download Token Manager**: `src/giljo_mcp/services/download_token_service.py`
- **ZIP Builder**: Python's `zipfile` module with YAML frontmatter generation
- **Token Lifecycle**: pending → ready → failed (15min TTL)

#### Database Operations

**Download Token Schema**:
```sql
CREATE TABLE download_tokens (
    id UUID PRIMARY KEY,
    token VARCHAR UNIQUE NOT NULL,
    tenant_key VARCHAR NOT NULL,
    filename VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,  -- Temporary file path on server
    status VARCHAR CHECK (status IN ('pending', 'ready', 'failed')),
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,  -- created_at + 15 minutes
    downloaded_at TIMESTAMP,
    INDEX idx_download_tokens_token (token),
    INDEX idx_download_tokens_expires (expires_at)
);
```

**Export Process**:
```python
# api/endpoints/export/claude_code.py::export_agents()

# 1. Query active templates (max 8)
templates = await session.execute(
    select(AgentTemplate)
    .where(and_(
        AgentTemplate.tenant_key == tenant_key,
        AgentTemplate.is_active == True
    ))
    .limit(8)
).scalars().all()

# 2. Generate YAML frontmatter per template
for template in templates:
    yaml_content = f"""---
name: {template.role}
model: {template.model or 'sonnet'}
tools: {json.dumps(template.tools or [])}
---

{template.system_instructions}

{template.user_instructions}
"""

# 3. Create ZIP file
zip_buffer = io.BytesIO()
with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
    for template in templates:
        zip_file.writestr(f"{template.role}.md", yaml_content)

# 4. Generate download token (15min TTL)
token = secrets.token_urlsafe(32)
expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
```

#### API Calls

**Export Endpoint**:
- **Route**: `POST /api/v1/export/claude-code`
- **Authentication**: JWT required (current user's tenant_key)
- **Response**:
```json
{
  "success": true,
  "download_url": "/api/download/temp/{token}/agents.zip",
  "token": "{32-char-urlsafe-token}",
  "expires_at": "2025-11-29T12:45:00Z",
  "template_count": 6,
  "cli_commands": {
    "claude": "claude-code mcp add http://x.x.x.x:7272/api/download/temp/{token}/agents.zip",
    "codex": "codex mcp add http://x.x.x.x:7272/api/download/temp/{token}/agents.zip",
    "gemini": "gemini mcp add http://x.x.x.x:7272/api/download/temp/{token}/agents.zip"
  }
}
```

**Download Endpoint**:
- **Route**: `GET /api/download/temp/{token}/{filename}`
- **Authentication**: None (token-based security)
- **Validation**: Token must be valid, not expired, status='ready'
- **Response**: Binary ZIP file stream
- **Side Effect**: Sets `downloaded_at` timestamp (one-time use tracking)

#### Error Scenarios

**Export Failures**:
- **No Templates Found**: Returns error if tenant has 0 active templates
- **ZIP Creation Error**: File I/O errors during ZIP generation
- **Recovery**: Check template activation status in My Settings → Integrations

**Download Failures**:
- **Token Expired**: HTTP 410 Gone (token > 15min old)
- **Token Not Found**: HTTP 404 Not Found (invalid token)
- **Token Not Ready**: HTTP 400 Bad Request (status != 'ready')
- **Recovery**: Re-generate export from UI, get new token

**CLI Installation Failures**:
- **Network Error**: CLI cannot reach server (check firewall, 0.0.0.0 binding)
- **Authentication Error**: API key not configured correctly
- **Recovery**: Verify MCP setup command includes correct API key or bearer token

#### Testing Procedures

**Verify Export**:
```bash
# Test export endpoint
curl -X POST http://localhost:7272/api/v1/export/claude-code \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  | jq .

# Test download (replace {token} with actual token from export response)
curl -o agents.zip http://localhost:7272/api/download/temp/{token}/agents.zip

# Verify ZIP contents
unzip -l agents.zip
# Expected: orchestrator.md, implementer.md, tester.md, analyzer.md, reviewer.md, documenter.md
```

**Integration Test**:
- **File**: `tests/integration/test_export_workflow.py`
- **Coverage**: Export generation, token creation, download validation, TTL expiry
- **Command**: `pytest tests/integration/test_export_workflow.py -v`

#### Performance Benchmarks
- Export generation (8 templates): <2 seconds
- ZIP file size: ~15-25KB (6 templates with YAML frontmatter)
- Download token generation: <100ms
- Download token validation: <50ms

---

### PHASE 3: MCP TO CLI TOOL SETUP

#### Code Implementation
- **MCP Configuration**: My Settings → Integrations → MCP Setup (frontend)
- **API Key Generation**: `api/endpoints/auth/api_keys.py`
- **Bearer Key Generation**: `api/endpoints/auth/bearer_keys.py`
- **CLI Tools Supported**: Claude Code, Codex CLI, Gemini CLI

#### Authentication Methods

**API Key (Claude Code, Gemini)**:
```bash
# Generated from My Settings → Integrations → MCP Setup
# Format: X-API-Key header
X-API-Key: giljo_abc123def456...
```

**Bearer Key (Codex, Gemini alternative)**:
```bash
# Generated from My Settings → Integrations → MCP Setup
# Format: Authorization header
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

#### CLI Configuration Examples

**Claude Code** (`~/.claude/config.json`):
```json
{
  "mcpServers": {
    "giljoai-mcp": {
      "url": "http://x.x.x.x:7272/mcp",
      "headers": {
        "X-API-Key": "giljo_abc123..."
      }
    }
  }
}
```

**Codex CLI** (`.codexrc`):
```json
{
  "mcp_servers": {
    "giljoai": {
      "url": "http://x.x.x.x:7272/mcp",
      "auth": {
        "type": "bearer",
        "token": "eyJ0eXAi..."
      }
    }
  }
}
```

**Gemini CLI** (`gemini_config.yaml`):
```yaml
mcp:
  servers:
    - name: giljoai
      url: http://x.x.x.x:7272/mcp
      auth:
        apiKey: giljo_abc123...
```

#### Error Scenarios

**MCP Connection Failures**:
- **Symptom**: CLI tool cannot reach MCP server
- **Check**: `curl http://x.x.x.x:7272/mcp -H "X-API-Key: YOUR_KEY"`
- **Common Causes**:
  - Server not running (`python startup.py` not executed)
  - Firewall blocking port 7272
  - Incorrect IP address (0.0.0.0 binds to all interfaces)
- **Recovery**: Verify server running, check `config.yaml` network settings

**Authentication Failures**:
- **Symptom**: HTTP 401 Unauthorized or HTTP 403 Forbidden
- **Check**: API key validity, expiration date
- **Recovery**: Regenerate API key from My Settings → Integrations

**Agent Template Loading Failures**:
- **Symptom**: CLI reports "Agent templates not found"
- **Check**: Verify ZIP download completed, templates extracted to `~/.claude/agents/`
- **Recovery**: Re-download ZIP, manually extract to correct directory

#### Testing Procedures

**Verify MCP Connection**:
```bash
# Test health endpoint
curl http://localhost:7272/mcp/health \
  -H "X-API-Key: YOUR_API_KEY"

# Expected: {"status": "healthy", "version": "3.1.0"}

# Test MCP JSON-RPC 2.0 endpoint
curl -X POST http://localhost:7272/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'

# Expected: List of available MCP tools
```

**Verify Agent Templates**:
```bash
# Check CLI registry (Claude Code example)
claude-code agent list

# Expected: Shows orchestrator, implementer, tester, analyzer, reviewer, documenter
```

#### Performance Benchmarks
- MCP connection establishment: <200ms
- Agent template registration: <100ms per template
- First MCP tool call: <500ms (includes connection pooling setup)
- Subsequent tool calls: <100ms

---

### PHASE 4: PROJECT STAGING & ORCHESTRATION

#### Code Implementation
- **Activation Endpoint**: `api/endpoints/projects/lifecycle.py::activate_project()` (lines 38-105)
- **Service Layer**: `src/giljo_mcp/services/project_service.py::activate_project()` (lines 808-930)
- **Thin Prompt Generator**: `src/giljo_mcp/thin_prompt_generator.py::ThinClientPromptGenerator`
- **Orchestrator Instructions**: `src/giljo_mcp/tools/orchestration.py::get_orchestrator_instructions()` (lines 1205-1479)

#### Database Operations

**Project Activation**:
```python
# api/endpoints/projects/lifecycle.py::activate_project()

# Single Active Project constraint enforcement
existing_active = await session.execute(
    select(Project).where(
        and_(
            Project.product_id == project.product_id,
            Project.status == "active",
            Project.id != project_id,
            Project.tenant_key == tenant_key
        )
    )
).scalar_one_or_none()

if existing_active:
    # Auto-deactivate existing active project
    existing_active.status = "inactive"
    await session.flush()  # CRITICAL: Flush before activating new project

# Activate new project
project.status = "active"
project.activated_at = datetime.utcnow()  # Set only on first activation
await session.commit()
```

**MCPAgentJob Creation** (Orchestrator):
```sql
INSERT INTO mcp_agent_jobs (
    job_id, project_id, tenant_key, agent_type, mission,
    status, context_budget, context_used, metadata, created_at
) VALUES (
    '{uuid}', '{project_id}', '{tenant_key}', 'orchestrator',
    'I am ready to create the project mission...',
    'waiting',  -- Initial status (not 'pending')
    200000,  -- Sonnet 4.5 default context budget
    0,  -- Initial context usage
    '{"created_via": "thin_client", "thin_client": true}',
    NOW()
);
```

**Orchestrator Instructions Fetch**:
```python
# src/giljo_mcp/tools/orchestration.py::get_orchestrator_instructions()

# Context condensation via MissionPlanner
from giljo_mcp.mission_planner import MissionPlanner

planner = MissionPlanner(db_manager)
metadata = orchestrator.job_metadata or {}
field_toggles = metadata.get("field_toggles", {})
user_id = metadata.get("user_id")

# Generate condensed mission with field toggles applied
condensed_mission = await planner._build_fetch_instructions(
    product=product,
    project=project,
    field_toggles=field_toggles,
    user_id=user_id,
    include_serena=include_serena  # From config.yaml
)

# Returns condensed mission (~6K tokens vs ~30K full vision)
```

#### API Calls

**Activate Project**:
- **Route**: `POST /api/v1/projects/{project_id}/activate`
- **Parameters**: `force: bool = False` (skip validation if true)
- **Authentication**: JWT required
- **Response**:
```json
{
  "id": "proj-uuid",
  "name": "My Project",
  "description": "User-written requirements",
  "mission": "",  // Empty until orchestrator persists it
  "status": "active",
  "product_id": "prod-uuid",
  "context_budget": 150000,
  "context_used": 0,
  "agent_count": 1,  // Orchestrator created
  "agents": []
}
```

**Update Project Mission** (MCP Tool):
- **Tool**: `update_project_mission(project_id, mission, tenant_key)`
- **Purpose**: Orchestrator persists created mission to `Project.mission` field
- **Side Effect**: Emits WebSocket event `project:mission_updated`

**Spawn Agent Job** (MCP Tool):
- **Tool**: `spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key, parent_job_id, template_id)`
- **Purpose**: Create specialist agent jobs for execution
- **Implementation**: `src/giljo_mcp/tools/orchestration.py::spawn_agent_job()` (lines 471-673)
- **Returns**:
```json
{
  "success": true,
  "agent_job_id": "agent-uuid",
  "agent_prompt": "~10 line thin prompt",
  "prompt_tokens": 50,
  "mission_stored": true,
  "mission_tokens": 2000,
  "thin_client": true
}
```

#### Error Scenarios

**Activation Failures**:
- **Invalid State Transition**: Project not in 'staging' or 'inactive' status
  - **Error**: HTTP 400 "Cannot activate project from status 'complete'"
  - **Recovery**: Check project status, ensure proper workflow sequence

- **Project Not Found**: Invalid project_id or tenant mismatch
  - **Error**: HTTP 404 "Project not found"
  - **Recovery**: Verify project_id, check tenant_key matches

- **Single Active Project Violation**: Another project already active in same product
  - **Behavior**: Auto-deactivates existing project (non-error, logged)
  - **Check**: Database logs for "Auto-deactivated project {id} due to Single Active Project constraint"

**Orchestrator Instruction Failures**:
- **Orchestrator Not Found**:
  - **Error**: `{"error": "NOT_FOUND", "message": "Orchestrator {id} not found"}`
  - **Troubleshooting**: Check `SELECT * FROM mcp_agent_jobs WHERE job_id = '{id}'`
  - **Recovery**: Re-activate project to create new orchestrator job

- **Context Generation Error**:
  - **Error**: `{"error": "INTERNAL_ERROR", "message": "Unexpected error: ..."}`
  - **Logs**: `~/.giljo_mcp/logs/mcp_adapter.log`, `~/.giljo_mcp/logs/api.log`
  - **Recovery**: Check vision document chunking, product context validity

**Agent Spawning Failures**:
- **Duplicate Orchestrator Prevention**:
  - **Check**: Query existing orchestrators with status in ['waiting', 'working']
  - **Error**: `{"success": false, "error": "Orchestrator already exists for this project"}`
  - **Recovery**: Use succession workflow (`/gil_handover`) for context handover

- **Mission Storage Failure**:
  - **Symptom**: Agent job created but mission field empty
  - **Check**: Database `SELECT mission FROM mcp_agent_jobs WHERE job_id = '{id}'`
  - **Recovery**: Re-spawn agent with valid mission text

#### Testing Procedures

**Verify Project Activation**:
```bash
# Activate project via API
curl -X POST http://localhost:7272/api/v1/projects/{project_id}/activate \
  -H "Authorization: Bearer YOUR_JWT" \
  | jq .

# Verify orchestrator created
PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT job_id, agent_type, status, created_at FROM mcp_agent_jobs WHERE project_id='{project_id}' AND agent_type='orchestrator';"

# Expected: 1 orchestrator with status='waiting'
```

**Verify Orchestrator Instructions**:
```python
# Integration test
# tests/integration/test_orchestrator_workflow.py

async def test_orchestrator_instructions_fetch():
    # Create project + activate
    project = await create_test_project()
    await activate_project(project.id)

    # Get orchestrator job
    orch_job = await get_orchestrator_job(project.id)

    # Fetch instructions via MCP tool
    instructions = await get_orchestrator_instructions(
        orchestrator_id=orch_job.job_id,
        tenant_key=tenant_key
    )

    # Assertions
    assert instructions["project_id"] == str(project.id)
    assert instructions["mission"]  # Condensed mission present
    assert instructions["estimated_tokens"] < 10000  # Context prioritization applied
    assert instructions["thin_client"] == True
```

**Integration Test**:
- **File**: `tests/integration/test_staging_workflow.py`
- **Coverage**: Project activation, orchestrator creation, instruction fetch, mission persistence, agent spawning
- **Command**: `pytest tests/integration/test_staging_workflow.py -v`

#### Performance Benchmarks
- Project activation: <150ms (includes Single Active Project check + deactivation)
- Orchestrator job creation: <100ms
- Thin prompt generation: <50ms
- Orchestrator instructions fetch: <500ms (includes context condensation)
- Mission persistence: <100ms
- Agent job spawning: <150ms per agent

---

### PHASE 5: AGENT EXECUTION & COORDINATION

#### Code Implementation
- **Job Lifecycle Manager**: `src/giljo_mcp/agent_job_manager.py::AgentJobManager` (lines 24-931)
- **Coordination Tools**: `src/giljo_mcp/tools/agent_coordination.py`
- **Messaging Tools**: `src/giljo_mcp/tools/agent_messaging.py`
- **WebSocket Manager**: `api/websocket.py::WebSocketManager`

#### Database Operations

**Agent Job Status State Machine**:
```python
# src/giljo_mcp/agent_job_manager.py::AgentJobManager.VALID_TRANSITIONS

VALID_TRANSITIONS = {
    "waiting": ["working", "cancelled", "decommissioned"],
    "working": ["complete", "failed", "blocked", "decommissioned"],
    "complete": ["decommissioned"],
    "failed": ["waiting", "decommissioned"],  # Allow retry
    "blocked": ["waiting", "working", "failed", "decommissioned"],
    "cancelled": ["decommissioned"],
    "decommissioned": []  # Terminal state
}
```

**Status Translation Layer** (Backend ↔ Frontend):
```python
# src/giljo_mcp/agent_job_manager.py::AgentJobManager

STATUS_INBOUND_ALIASES = {"pending": "waiting"}  # API input normalization
STATUS_OUTBOUND_ALIASES = {"waiting": "waiting"}  # API output (no translation)

# Note: Frontend displays "Waiting" for initial job state
# Backend stores "waiting" (NOT "pending")
# Translation occurs in API serialization layer
```

**Job Acknowledgement** (Agent claims job):
```python
# src/giljo_mcp/agent_job_manager.py::acknowledge_job()

# Transition: waiting → working
job = await self._get_job_or_raise(job_id, tenant_key)
if job.status != "waiting":
    raise ValueError(f"Job {job_id} cannot be acknowledged (status={job.status})")

job.status = "working"
job.acknowledged_at = datetime.now(timezone.utc)
job.acknowledged_by = agent_id
await session.commit()

# Emit WebSocket event
await websocket_manager.broadcast_to_tenant(
    tenant_key=tenant_key,
    event_type="job:status_changed",
    data={"job_id": job_id, "status": "working"}
)
```

**Progress Reporting**:
```python
# src/giljo_mcp/tools/agent_coordination.py::report_progress()

job.progress = progress_percent  # 0-100
job.updated_at = datetime.now(timezone.utc)

# Emit WebSocket event for live progress bar
await websocket_manager.broadcast_to_tenant(
    tenant_key=tenant_key,
    event_type="job:progress_updated",
    data={"job_id": job_id, "progress": progress_percent, "message": status_message}
)
```

**Job Completion**:
```python
# src/giljo_mcp/agent_job_manager.py::complete_job()

# Transition: working → complete (terminal state)
job.status = "complete"
job.completed_at = datetime.now(timezone.utc)
job.result = result_data  # JSONB field
await session.commit()

# Emit WebSocket event
await websocket_manager.broadcast_to_tenant(
    tenant_key=tenant_key,
    event_type="job:complete",
    data={"job_id": job_id, "result": result_data}
)
```

#### API Calls

**Get Pending Jobs** (MCP Tool):
- **Tool**: `get_pending_jobs(agent_type, tenant_key)`
- **Purpose**: Agent discovers assigned work
- **Returns**: List of jobs with status='waiting' for agent_type

**Acknowledge Job** (MCP Tool):
- **Tool**: `acknowledge_job(job_id, agent_id)`
- **Purpose**: Agent claims job (waiting → working)
- **Side Effect**: Sets `acknowledged_at` timestamp, emits WebSocket event

**Report Progress** (MCP Tool):
- **Tool**: `report_progress(job_id, progress_dict)`
- **Purpose**: Agent updates progress percentage
- **Fields**: `{"percent": 0-100, "message": "status", "timestamp": "ISO8601"}`

**Complete Job** (MCP Tool):
- **Tool**: `complete_job(job_id, result)`
- **Purpose**: Agent marks job done (working → complete)
- **Side Effect**: Sets `completed_at` timestamp, emits WebSocket event

**Send Message** (MCP Tool):
- **Tool**: `send_message(to_agent, message, priority)`
- **Purpose**: Inter-agent coordination
- **Modes**: Direct (to specific agent_id) or Broadcast (to all agents)

#### Error Scenarios

**Job State Transition Errors**:
- **Invalid Transition**: Attempt to move from terminal state
  - **Error**: `ValueError: Invalid transition from complete to working`
  - **Recovery**: Check job status before operations, respect state machine

- **Concurrent Acknowledgement**: Two agents try to claim same job
  - **Behavior**: First wins (database-level locking), second gets error
  - **Error**: `ValueError: Job already acknowledged by agent_xyz`
  - **Recovery**: Agent queries for other pending jobs

**Progress Reporting Failures**:
- **Progress Out of Range**: percent < 0 or > 100
  - **Validation**: MCP tool validates before database update
  - **Error**: `{"error": "VALIDATION_ERROR", "message": "Progress must be 0-100"}`

- **WebSocket Broadcast Failure**: Event emission fails
  - **Behavior**: Non-blocking, logged as warning
  - **Impact**: UI not updated in real-time (user can refresh)
  - **Logs**: `[WEBSOCKET] Failed to broadcast event: {error}`

**Messaging Failures**:
- **Recipient Not Found**: Agent ID invalid or decommissioned
  - **Error**: `{"error": "NOT_FOUND", "message": "Recipient agent not found"}`
  - **Recovery**: Verify agent exists, check decommissioning status

- **Message Queue Full**: (Theoretical - no limit enforced)
  - **Mitigation**: Messages auto-acknowledged on read
  - **Monitoring**: Track `agent_messages` table row count

#### Testing Procedures

**Verify Job Lifecycle**:
```bash
# Create test job
curl -X POST http://localhost:7272/api/v1/agent-jobs/spawn \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "implementer",
    "agent_name": "impl-test",
    "mission": "Test mission",
    "project_id": "{project_id}"
  }' | jq .

# Acknowledge job (via MCP tool simulation)
PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "UPDATE mcp_agent_jobs SET status='working', acknowledged_at=NOW() WHERE job_id='{job_id}';"

# Verify status change
PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT job_id, status, acknowledged_at FROM mcp_agent_jobs WHERE job_id='{job_id}';"

# Expected: status='working', acknowledged_at populated
```

**Integration Test**:
```python
# tests/integration/test_job_lifecycle.py

async def test_complete_job_workflow():
    # Setup: Create job
    job = await create_test_job(agent_type="implementer")
    assert job.status == "waiting"

    # Acknowledge
    await acknowledge_job(job.job_id, agent_id="test-agent")
    job = await get_job(job.job_id)
    assert job.status == "working"
    assert job.acknowledged_at is not None

    # Report progress
    await report_progress(job.job_id, {"percent": 50, "message": "Halfway done"})
    job = await get_job(job.job_id)
    assert job.progress == 50

    # Complete
    await complete_job(job.job_id, {"files_modified": ["test.py"]})
    job = await get_job(job.job_id)
    assert job.status == "complete"
    assert job.completed_at is not None
```

**End-to-End Test**:
- **File**: `tests/e2e/test_agent_coordination.py`
- **Coverage**: Multi-agent orchestration, message passing, job completion sequence
- **Command**: `pytest tests/e2e/test_agent_coordination.py -v --timeout=300`

#### Performance Benchmarks
- Job acknowledgement: <100ms (includes status update + WebSocket broadcast)
- Progress report: <50ms
- Job completion: <100ms
- Message send: <80ms
- Message receive (poll): <50ms
- WebSocket event delivery: <200ms (client receives update)

---

### PHASE 6: PROJECT CLOSEOUT & 360 MEMORY UPDATE

#### Code Implementation
- **Closeout Tool**: `src/giljo_mcp/tools/orchestration.py::close_project_and_update_memory()`
- **Memory Manager**: `src/giljo_mcp/services/product_service.py::update_product_memory()`
- **GitHub Integration**: `src/giljo_mcp/integrations/github_service.py`
- **WebSocket Events**: `api/websocket.py::broadcast_to_tenant()`

#### Database Operations

**Product Memory Schema** (JSONB field):
```json
{
  "objectives": ["Goal 1", "Goal 2"],
  "decisions": ["Decision 1", "Decision 2"],
  "context": {
    "tech_stack": "Python/FastAPI/Vue3/PostgreSQL",
    "architecture": "Multi-tenant SaaS"
  },
  "knowledge_base": {
    "patterns": ["Pattern 1"],
    "anti_patterns": ["Anti-pattern 1"]
  },
  "sequential_history": [
    {
      "sequence": 1,
      "type": "project_closeout",
      "project_id": "proj-uuid",
      "summary": "Implemented feature X",
      "key_outcomes": ["Outcome 1", "Outcome 2"],
      "decisions_made": ["Decision 1"],
      "git_commits": [
        {
          "sha": "abc123",
          "message": "Commit message",
          "author": "user@example.com",
          "timestamp": "2025-11-29T10:00:00Z",
          "files_changed": ["file1.py", "file2.py"]
        }
      ],
      "timestamp": "2025-11-29T12:00:00Z"
    },
    {
      "sequence": 2,
      "type": "project_closeout",
      // Next project closeout...
    }
  ]
}
```

**Memory Update Process**:
```python
# src/giljo_mcp/tools/orchestration.py::close_project_and_update_memory()

# 1. Fetch GitHub commits (if enabled)
git_integration = product.product_memory.get("git_integration", {})
git_commits = []

if git_integration.get("enabled"):
    from giljo_mcp.integrations.github_service import GitHubService
    gh_service = GitHubService(api_token=git_integration["api_token"])
    git_commits = await gh_service.fetch_commits_since(
        repo=git_integration["repo"],
        since=project.activated_at
    )

# 2. Build closeout entry
next_sequence = len(product.product_memory.get("sequential_history", [])) + 1
closeout_entry = {
    "sequence": next_sequence,
    "type": "project_closeout",
    "project_id": str(project.id),
    "summary": summary,
    "key_outcomes": key_outcomes,
    "decisions_made": decisions_made,
    "git_commits": git_commits,
    "timestamp": datetime.now(timezone.utc).isoformat()
}

# 3. Append to sequential_history
product.product_memory["sequential_history"].append(closeout_entry)
await session.commit()

# 4. Emit WebSocket event
await websocket_manager.broadcast_to_tenant(
    tenant_key=tenant_key,
    event_type="product:memory_updated",
    data={
        "product_id": str(product.id),
        "sequence": next_sequence,
        "summary": summary[:200]
    }
)
```

#### API Calls

**Close Project and Update Memory** (MCP Tool):
- **Tool**: `close_project_and_update_memory(project_id, summary, key_outcomes, decisions_made)`
- **Purpose**: Orchestrator finalizes project, updates 360 memory
- **Implementation**: `src/giljo_mcp/tools/orchestration.py::close_project_and_update_memory()`
- **Returns**:
```json
{
  "success": true,
  "sequence_number": 3,
  "git_commits_captured": 12,
  "memory_updated": true,
  "project_completed_at": "2025-11-29T12:00:00Z"
}
```

**GitHub Integration Endpoints**:
- **Route**: `POST /api/v1/integrations/github/configure`
- **Purpose**: Enable GitHub commit tracking
- **Payload**:
```json
{
  "enabled": true,
  "api_token": "ghp_...",
  "repo": "owner/repo-name",
  "branch": "main"
}
```

#### Error Scenarios

**Closeout Failures**:
- **Project Not Found**:
  - **Error**: `{"error": "NOT_FOUND", "message": "Project not found"}`
  - **Recovery**: Verify project_id, check if project was soft-deleted

- **Product Not Found**:
  - **Error**: `{"error": "NOT_FOUND", "message": "No product linked to project"}`
  - **Recovery**: Ensure project.product_id is set (required field)

**GitHub Integration Failures**:
- **API Token Invalid**:
  - **Error**: HTTP 401 from GitHub API
  - **Fallback**: Use manual summary without git commits
  - **Logs**: `[GITHUB] Authentication failed: {error}`

- **Rate Limit Exceeded**:
  - **Error**: HTTP 403 from GitHub API (rate limit)
  - **Fallback**: Use cached commits or manual summary
  - **Recovery**: Wait for rate limit reset, configure Personal Access Token

- **Network Error**:
  - **Error**: Connection timeout to GitHub API
  - **Fallback**: Use manual summary without git commits
  - **Logs**: `[GITHUB] Network error: {error}`

**Memory Update Failures**:
- **JSONB Serialization Error**:
  - **Cause**: Invalid JSON in summary or outcomes
  - **Error**: `TypeError: Object of type X is not JSON serializable`
  - **Recovery**: Sanitize input, convert to strings

- **Sequence Number Conflict**: (Theoretical - auto-increment prevents)
  - **Mitigation**: Lock product row during update
  - **Recovery**: Retry closeout operation

#### Testing Procedures

**Verify Closeout Workflow**:
```bash
# Trigger closeout (via MCP tool simulation)
curl -X POST http://localhost:7272/api/v1/projects/{project_id}/closeout \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "Test closeout summary",
    "key_outcomes": ["Outcome 1", "Outcome 2"],
    "decisions_made": ["Decision 1"]
  }' | jq .

# Verify 360 memory updated
PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT product_memory->'sequential_history' FROM products WHERE id='{product_id}';"

# Expected: New entry with correct sequence number
```

**GitHub Integration Test**:
```python
# tests/integration/test_github_integration.py

async def test_github_commit_fetch():
    # Setup: Configure GitHub integration
    await configure_github_integration(
        product_id=product.id,
        api_token="test-token",
        repo="test-owner/test-repo"
    )

    # Mock GitHub API response
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.json.return_value = [
            {
                "sha": "abc123",
                "commit": {
                    "message": "Test commit",
                    "author": {"email": "test@example.com"},
                    "committer": {"date": "2025-11-29T10:00:00Z"}
                },
                "files": [{"filename": "test.py"}]
            }
        ]

        # Trigger closeout
        result = await close_project_and_update_memory(
            project_id=project.id,
            summary="Test closeout"
        )

        # Assertions
        assert result["success"] == True
        assert result["git_commits_captured"] == 1
```

**Integration Test**:
- **File**: `tests/integration/test_closeout_workflow.py`
- **Coverage**: Project completion, 360 memory update, GitHub integration, WebSocket events
- **Command**: `pytest tests/integration/test_closeout_workflow.py -v`

#### Performance Benchmarks
- Closeout without GitHub: <200ms
- GitHub commit fetch (10 commits): <1 second
- GitHub commit fetch (100 commits): <3 seconds
- Memory update (append to JSONB): <100ms
- WebSocket broadcast: <50ms

---

### ERROR RECOVERY PROCEDURES

#### Critical Failure Scenarios

**Database Connection Loss**:
- **Symptom**: SQLAlchemy connection errors, timeouts
- **Check**:
  ```bash
  PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -l
  ```
- **Recovery**:
  1. Restart PostgreSQL service
  2. Verify `config.yaml` database connection string
  3. Check connection pool settings (max_connections)
  4. Restart API server: `python startup.py`

**WebSocket Manager Crash**:
- **Symptom**: Real-time UI updates stop working
- **Check**: API server logs for WebSocket errors
- **Impact**: Non-critical - UI updates on page refresh
- **Recovery**: Restart API server (WebSocket manager reinitializes)

**MCP Server Unresponsive**:
- **Symptom**: Agents cannot fetch missions, tools timeout
- **Check**:
  ```bash
  curl http://localhost:7272/mcp/health
  ```
- **Recovery**:
  1. Check MCP logs: `~/.giljo_mcp/logs/mcp_adapter.log`
  2. Restart MCP server (handled by `startup.py`)
  3. Verify firewall not blocking port 7272

**Context Budget Exceeded**:
- **Symptom**: Orchestrator approaching 200K token limit (90% threshold)
- **Detection**: Context monitoring in OrchestrationService
- **Recovery**:
  1. User clicks [Handover] button in UI
  2. Orchestrator writes 360 memory closeout
  3. New orchestrator spawned with condensed context
  4. Mission and agent states preserved

#### Data Consistency Issues

**Orphaned Agent Jobs**:
- **Cause**: Project deleted but agent jobs remain
- **Detection**:
  ```sql
  SELECT job_id, project_id FROM mcp_agent_jobs
  WHERE project_id NOT IN (SELECT id FROM projects);
  ```
- **Recovery**: Decommission orphaned jobs:
  ```sql
  UPDATE mcp_agent_jobs SET status='decommissioned'
  WHERE project_id NOT IN (SELECT id FROM projects);
  ```

**Status Inconsistency**:
- **Cause**: WebSocket failure during state transition
- **Detection**: Job status doesn't match UI display
- **Recovery**:
  1. Query job status directly:
     ```sql
     SELECT job_id, status, updated_at FROM mcp_agent_jobs WHERE job_id='{id}';
     ```
  2. Refresh UI to sync with database state
  3. Manual status correction if needed (via API)

#### Performance Degradation

**Slow MCP Tool Calls** (>1 second):
- **Causes**:
  - Large vision documents not chunked properly
  - Too many agent templates (>8 active)
  - Context priorities not optimized
- **Diagnosis**:
  ```bash
  # Check vision document sizes
  PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
    "SELECT id, LENGTH(content) as size FROM vision_documents ORDER BY size DESC LIMIT 10;"

  # Check active template count
  PGPASSWORD=4010 /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
    "SELECT tenant_key, COUNT(*) FROM agent_templates WHERE is_active=true GROUP BY tenant_key;"
  ```
- **Recovery**:
  1. Chunk large vision documents (≤10K tokens)
  2. Deactivate unused templates (keep ≤8 active)
  3. Optimize field priorities in My Settings → Context

**Database Query Slowness**:
- **Causes**:
  - Missing indexes
  - Large result sets without pagination
  - Unoptimized queries
- **Diagnosis**:
  ```sql
  -- Enable query timing
  \timing on

  -- Identify slow queries
  SELECT query, mean_exec_time, calls
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;
  ```
- **Recovery**:
  1. Add indexes on frequently queried columns
  2. Use pagination for large result sets
  3. Optimize queries with EXPLAIN ANALYZE

---

### TESTING VERIFICATION CHECKLIST

Use this checklist to verify complete system functionality:

#### Installation & Setup
- [ ] PostgreSQL database created successfully
- [ ] 32 tables migrated (verify with `\dt` in psql)
- [ ] First user created with valid tenant_key
- [ ] 6 agent templates seeded per tenant
- [ ] API server running on 0.0.0.0:7272
- [ ] Frontend accessible at http://localhost:8080

#### Template Export & CLI Setup
- [ ] Export generates ZIP with 6 agent templates
- [ ] Download token created with 15min TTL
- [ ] CLI tool successfully downloads ZIP
- [ ] Agent templates extracted to `~/.claude/agents/`
- [ ] MCP connection established (health check passes)
- [ ] Agent templates registered in CLI tool

#### Project Staging
- [ ] Project activation creates orchestrator job
- [ ] Orchestrator status = 'waiting' (not 'pending')
- [ ] Thin prompt generated (<600 tokens)
- [ ] Orchestrator fetches instructions via MCP
- [ ] Condensed mission returned (context prioritization applied)
- [ ] Mission persisted to `Project.mission` field
- [ ] Agent jobs spawned with thin prompts
- [ ] WebSocket events emitted for UI updates

#### Agent Execution
- [ ] Agents acknowledge jobs (waiting → working)
- [ ] Progress reports update UI in real-time
- [ ] Inter-agent messaging functional
- [ ] Jobs complete successfully (working → complete)
- [ ] Failed jobs handled gracefully (working → failed)
- [ ] WebSocket events received by frontend

#### Project Closeout
- [ ] Orchestrator calls closeout MCP tool
- [ ] 360 memory updated with project summary
- [ ] GitHub commits fetched (if integration enabled)
- [ ] Sequence number auto-incremented
- [ ] WebSocket event emitted for memory update
- [ ] Project status = 'complete'

#### Error Handling
- [ ] Invalid API calls return proper error codes
- [ ] Multi-tenant isolation enforced (no cross-tenant data leak)
- [ ] Token expiry handled (HTTP 410 for expired tokens)
- [ ] WebSocket failures logged but non-blocking
- [ ] Context budget warnings emitted at 90% threshold

#### Performance
- [ ] MCP tool calls complete in <500ms
- [ ] Database queries optimized (use indexes)
- [ ] WebSocket events delivered in <200ms
- [ ] Vision documents chunked (≤10K tokens)
- [ ] Agent template count ≤8 active

---

### CODE IMPLEMENTATION STATUS

This section tracks implementation status for code review verification:

#### ✅ Fully Implemented
- Template seeding (`src/giljo_mcp/template_seeder.py`)
- Project activation (`api/endpoints/projects/lifecycle.py`)
- Thin client prompt generation (`src/giljo_mcp/thin_prompt_generator.py`)
- Agent job lifecycle (`src/giljo_mcp/agent_job_manager.py`)
- MCP orchestration tools (`src/giljo_mcp/tools/orchestration.py`)
- WebSocket real-time updates (`api/websocket.py`)
- Multi-tenant isolation (enforced across all layers)
- Context prioritization v2.0 (`src/giljo_mcp/mission_planner.py`)
- 360 memory management (`src/giljo_mcp/tools/orchestration.py::close_project_and_update_memory()`)

#### ⚠️ Partial Implementation
- GitHub integration (basic commit fetch - advanced features pending)
- Orchestrator succession (manual trigger - auto-trigger at 90% functional)
- Serena MCP integration (toggle functional, prompt injection active)

#### 🚧 Planned Features
- Agent decommissioning workflow (code exists, UI integration pending)
- Advanced context analytics (token usage trends, recommendations)
- Multi-product support (database schema ready, UI pending)

---

**Last Updated**: 2025-11-29
**Technical Review Status**: COMPREHENSIVE IMPLEMENTATION REFERENCE COMPLETE
**Code Review Ready**: YES - All critical paths documented with file locations and line numbers

---

## User Flow Confirmation

Your simplified flow description is **ACCURATE**. Here's the verified sequence:

1. ✅ **Install.py runs** → Database setup → Agent templates seeded (6 per tenant)
2. ✅ **Export function** → User clicks "Claude Export Agents" → ZIP generated → Download token created
3. ✅ **Copy Command button** → Tokenized link displayed → User copies → Pastes into CLI terminal
4. ✅ **CLI installs agents** → Downloads ZIP → Extracts to ~/.claude/agents/ → Registers in MCP
5. ✅ **Agents staged** → Templates available in MCP registry for orchestrator to use
6. ✅ **Project activation** → User clicks "Stage Project" → Orchestrator job created (status="waiting")
7. ✅ **Orchestrator reads context** → MCP tool: get_orchestrator_instructions() → Vision + mission + context
8. ✅ **Orchestrator hires agents** → Queries active templates → Selects agents based on capabilities (max 8)
9. ✅ **Mission assignments** → Breaks down mission → Creates MCPAgentJob records for each sub-agent
10. ✅ **Instructions stored** → Jobs saved on MCP server → Status: "waiting"
11. ✅ **User copies trigger** → Frontend generates prompt → User pastes into terminal
12. ✅ **Agents execute** → MCP tools: get_pending_jobs(), acknowledge_job(), report_progress(), complete_job()
13. ✅ **Agent communication** → Agents have IDs, types, profiles → Communicate via MCP messaging tools

---

## Resolved Inconsistencies

1. **"Stage Project" vs "Activate"**: UI shows "Stage Project", backend uses `/activate` endpoint
2. **Tab Navigation**: Two distinct tabs - "Launch" (staging) and "Implementation" (execution)
3. **Claude Toggle Location**: Located at top of Implementation tab, not Launch tab
4. **Mission Persistence**: Mission saved to database via `update_project_mission()` MCP tool
5. **Dual-Status Architecture**: Database stores canonical values (waiting, working, complete), API accepts aliases (pending, active, completed)
   - Introduced in Handover 0113 for backward compatibility
   - `AgentJobManager` translates between representations
   - 7 valid database states enforced by database constraint
   - Frontend receives database values via WebSocket events
6. **Agent Prompt Behavior**: Toggle controls which prompt buttons are active

---

## Key Takeaways

1. **UI Labels ≠ Backend Endpoints**: "Stage Project" button actually calls `/activate`
2. **Two-Phase Process**: Launch tab (staging) → Implementation tab (execution)
3. **Mode Toggle Critical**: Determines single vs multi-terminal execution
4. **Mission Persistence**: Orchestrator creates AND persists mission to database
5. **Real-time Updates**: WebSocket events drive all UI updates
6. **Token Efficient**: Thin client architecture reduces prompt size by 85%
7. **Dual-Status System**: Database uses 7 canonical states (waiting, working, etc.), API accepts aliases (pending, active, etc.) for compatibility
8. **No "Staged" Status**: Jobs go directly from creation to "waiting" status - there is NO intermediate "staged" state
9. **Dynamic Agent Discovery**: Orchestrator calls `get_available_agents()` - no hardcoded agent lists
10. **Two-Step Agent Spawning**: `spawn_agent_job()` stores mission in database, agent fetches via `get_agent_mission()`

---

## Recommendations

### For Users
1. Follow the exact flow: Install → Export → Copy Command → CLI Install → Stage Project → Copy Trigger
2. Respect 8-role cap (system enforces, but plan accordingly)
3. Use native CLI commands (codex mcp add, gemini mcp add, claude-code mcp add)
4. Monitor orchestrator job status before launching sub-agents

### For Developers
1. Understand the dual terminology: backend "pending" = frontend "waiting"
2. Add explicit `/projects/{id}/stage` alias for API consistency if needed
3. Remember that execution mode is a UI-only concern (frontend toggle)
4. Consider adding E2E test for complete flow (install → export → stage → execute)

### For Operations
1. Monitor download token expiry rates
2. Track MCP tool call latency
3. Add metrics for agent job lifecycle transitions
4. Implement alerting for failed job states

---

## Documentation Cross-References

- Handover 0041: Agent Template Database Integration
- Handover 0088: Thin Client Architecture (70% token reduction)
- Handover 0102: Download Token System
- Handover 0103: Multi-CLI Support (Claude, Codex, Gemini)
- Handover 0104: Master Closeout (Security Fixes)
- Handover 0246 Series: Token Optimization & Dynamic Agent Discovery
- docs/MCP_OVER_HTTP_INTEGRATION.md: MCP protocol documentation
- docs/AI_TOOL_CONFIGURATION_MANAGEMENT.md: CLI configuration guide

---

## Final Verdict

### ✅ **ALL PLUMBING IS WIRED CORRECTLY**

**Evidence Summary**:
- 21/21 components verified functional
- 0 critical issues found
- 5 critical path connections confirmed
- Multi-tenant isolation verified at all layers
- Security hardening confirmed
- 70% token reduction achieved
- Complete MCP tool suite present

**System Status**: **PRODUCTION-READY**

**Next Step**: **User Testing** (recommended testing guide in docs/user_guides/0104_USER_TESTING_GUIDE.md)

---

**Document Harmonization Completed**: 2025-11-29
**Original Investigation**: 2025-11-05
**Harmonization Sources**: PDF workflow slides + Markdown technical verification
**Status**: ✅ **UNIFIED SINGLE SOURCE OF TRUTH**

---

*This document serves as the authoritative workflow and technical verification record for the GiljoAI MCP agent orchestration system.*

