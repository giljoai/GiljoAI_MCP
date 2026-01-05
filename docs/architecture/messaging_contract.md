# Messaging Contract & Communication Taxonomy

**Version**: v3.3+ (Handovers 0295, 0360, 0366)
**Last Updated**: 2025-12-21

## Overview

GiljoAI MCP uses a **three-category communication model** to separate concerns and prevent conceptual confusion in agent coordination. This taxonomy ensures:

- **Clean separation**: Messages, signals, and instructions serve distinct purposes
- **Developer clarity**: New contributors understand which tool to use when
- **Maintainability**: Business logic stays in appropriate layers
- **Testability**: Each category can be tested independently

**Why This Matters**: Early versions of GiljoAI conflated messages (communication) with signals (job status) and instructions (missions). This led to:
- Bloated message content (missions embedded in messages)
- Job status confusion (status updates sent as messages)
- Testing difficulties (business logic scattered across layers)
- Poor auditability (unclear separation between human and AI-generated content)

Handover 0295 establishes clear boundaries between these three categories.

---

## The Three Categories

### Category 1: MESSAGES (Auditable Communication)

**Definition**: Structured, auditable communication between agents and user↔agents.

**Purpose**:
- Agent-to-agent coordination ("Ready for testing")
- User-to-agent instructions ("Focus on error handling")
- Orchestrator-to-agent directives ("Pause until blockers resolved")
- System notifications (rare, minimal usage)

**Canonical Store**: PostgreSQL `messages` table (`Message` model)

**Public API Tools** (HTTP MCP):
```python
# Send message (Handover 0366: Uses agent_id for routing)
send_message(
    to_agent_id: str,                # Agent executor UUID (AgentExecution.agent_id)
    content: str,                    # Message body
    project_id: str,                 # UUID
    tenant_key: str,                 # Multi-tenant isolation
    message_type: str = "direct",    # "direct" | "broadcast" | "system"
    priority: str = "normal"         # "low" | "normal" | "high"
)

# Receive pending messages (Handover 0360: Auto-acknowledge & remove from queue)
# NOTE: This is the standard tool for agents to retrieve messages.
# Deprecated tool `get_next_instruction()` has been removed - use receive_messages() instead.
receive_messages(
    agent_id: str,                   # Agent executor UUID (AgentExecution.agent_id)
    tenant_key: str,                 # Multi-tenant isolation
    limit: int = 10                  # Max messages to retrieve
)

# List message history (read-only, no removal)
list_messages(
    project_id: Optional[str] = None,
    status: Optional[str] = None,    # "pending" | "completed"
    agent_id: Optional[str] = None,
    tenant_key: str,                 # Multi-tenant isolation
    limit: int = 50
)

# Discover team members (Handover 0360: Find agents on same job)
get_team_agents(
    job_id: str,                     # Work order UUID (AgentJob.id)
    tenant_key: str                  # Multi-tenant isolation
)
```

**Identity Model (Handover 0366)**:
Messages use **agent_id** (executor UUID) for routing, NOT job_id:
- `job_id` = Work order UUID (AgentJob) - the **WHAT** (task definition)
- `agent_id` = Executor UUID (AgentExecution) - the **WHO** (running agent instance)
- Message routing: `send_message(to_agent_id=...)` → `receive_messages(agent_id=...)`
- Database field: `Message.recipient_agent_id` stores the executor UUID

**Team Discovery (Handover 0360)**:
Use `get_team_agents(job_id, tenant_key)` to discover all agent executors working on the same job:
- Returns list of agent_id values for team members
- Filter by status (e.g., active agents only)
- Use returned agent_id values in `send_message()` calls

**Message Types**:
- `"direct"` - Specific recipient via `to_agent_id` parameter
- `"broadcast"` - Logical broadcast to all agents (future feature)
- `"system"` - System-level notifications (use sparingly)

**Message Status**:
- `"pending"` - Created but not completed
- `"completed"` - Explicitly completed with result

**JSONB Mirror** (`MCPAgentJob.messages`):
- **Purpose**: Counter persistence for UI display (Messages Sent/Waiting/Read)
- **Pattern**: Not a separate messaging system - just a cache/mirror
- **Updates**: Automatically synchronized by `MessageService`

**Counter Logic**:
```python
# Messages Sent: Outbound messages from agent
sent_count = len([m for m in agent.messages if m["from"] == agent.id])

# Messages Waiting: Inbound, unacknowledged messages
waiting_count = len([
    m for m in agent.messages
    if agent.id in m["to_agents"] and agent.id not in m["acknowledged_by"]
])

# Messages Read: Acknowledged messages
read_count = len([
    m for m in agent.messages
    if agent.id in m["acknowledged_by"]
])
```

**Architecture Flow**:
```
Agent → MCP Tool (send_message) → MessageService → Database + JSONB Mirror
                                                  ↓
                                            WebSocket Events
                                              (message:sent, message:received)
```

**Anti-Patterns** (DO NOT):
- ❌ Embed mission content in message body
- ❌ Use messages for job status updates (use signals)
- ❌ Bypass `MessageService` for direct database writes
- ❌ Store large payloads in message content (>10K tokens)

---

### Category 2: SIGNALS (Job State & Progress)

**Definition**: Job lifecycle events, status transitions, and progress updates.

**Purpose**:
- Track agent job status (waiting → working → complete)
- Report incremental progress (25%, 50%, 75%, 100%)
- Signal health and blocking conditions
- Coordinate workflow dependencies

**Canonical Store**: `MCPAgentJob` table via `AgentJobManager`

**Job Statuses**:
```python
# State machine
"waiting"        # Job created, agent not yet claimed
"working"        # Agent actively executing
"blocked"        # Agent paused (dependency or error)
"complete"       # Job finished successfully
"failed"         # Job encountered unrecoverable error
"cancelled"      # User or orchestrator cancelled
"decommissioned" # Job archived (cleanup)
```

**Public API Tools** (MCP):
```python
# Claim job (pending → active)
acknowledge_job(
    job_id: str,
    agent_id: str
)

# Report incremental progress
report_progress(
    job_id: str,
    progress: dict  # {"percent": 50, "message": "Core implementation complete"}
)

# Complete successfully
complete_job(
    job_id: str,
    result: dict  # {"status": "success", "deliverables": [...]}
)

# Report error (job paused)
report_error(
    job_id: str,
    error: str
)

# Check workflow status
get_workflow_status(
    project_id: str,
    tenant_key: str
)
```

**WebSocket Events** (Real-time UI updates):
```javascript
// Job status changes
ws.on("job:status_changed", (data) => {
    // data: { job_id, status, agent_type, timestamp }
});

// Progress updates
ws.on("job:progress_updated", (data) => {
    // data: { job_id, percent_complete, status_message }
});
```

**Critical Rule**: Messages MUST NOT be used for job status signaling. Job state lives in `MCPAgentJob` table, not `messages` table.

**Example Usage**:
```python
# Agent claims job
await acknowledge_job(job_id="abc-123", agent_id="implementer-1")

# Agent reports progress
await report_progress(
    job_id="abc-123",
    progress={"percent": 25, "message": "Initialization complete"}
)

await report_progress(
    job_id="abc-123",
    progress={"percent": 50, "message": "Core implementation complete"}
)

# Agent completes job
await complete_job(
    job_id="abc-123",
    result={
        "status": "success",
        "files_modified": 5,
        "tests_passed": 12,
        "documentation_updated": True
    }
)
```

**Workflow Status Monitoring**:
```python
# Orchestrator checks if all agents completed
status = await get_workflow_status(
    project_id="proj-456",
    tenant_key="user_alice"
)

# Returns:
{
    "active_agents": 2,
    "completed_agents": 8,
    "failed_agents": 0,
    "progress_percent": 80  # (8/10 * 100)
}

# Decision logic
if status["progress_percent"] == 100:
    print("All agents complete - project finished!")
elif status["failed_agents"] > 0:
    print("Investigate failures before proceeding")
```

**Anti-Patterns** (DO NOT):
- ❌ Send job status as a message (`send_message("Status: complete")`)
- ❌ Use message acknowledgment as job acknowledgment
- ❌ Embed progress percentages in message content
- ❌ Query `messages` table for job status (use `MCPAgentJob`)

---

### Category 3: INSTRUCTIONS (Missions & Configuration)

**Definition**: Structured mission content and configuration fetched from server.

**Purpose**:
- Deliver agent-specific missions (not chat)
- Provide orchestrator instructions
- Fetch next steps in a multi-phase workflow
- Retrieve configuration and context

**Public API Tools** (MCP):
```python
# Orchestrator fetches instructions
# NOTE (0366): orchestrator_id is a job_id (work order), not agent_id (executor)
get_orchestrator_instructions(
    orchestrator_id: str,  # Orchestrator job UUID (work order)
    tenant_key: str        # Multi-tenant isolation
)

# Agent fetches mission
# NOTE (0262/0332): In CLI subagent mode, this is the ATOMIC JOB START:
# - First call sets mission_acknowledged_at and transitions waiting → working
# - Subsequent calls are idempotent re-reads
# NOTE (0366): job_id is work order UUID, agent_id is executor UUID
get_agent_mission(
    job_id: str,           # Work order UUID (AgentJob.id)
    tenant_key: str        # Multi-tenant isolation
)

# DEPRECATED: get_next_instruction() has been removed.
# Agents should use receive_messages(agent_id, tenant_key) to check for new instructions.
# Instructions are delivered via the standard messaging system (Category 1: MESSAGES).
```

**Return Format**:
```python
# get_orchestrator_instructions() returns:
{
    "success": True,
    "instructions": "You are Orchestrator #1 for Project XYZ...",
    "context": {
        "project_id": "uuid",
        "product_id": "uuid",
        "context_budget": 200000,
        "priority_config": {...}
    }
}

# get_agent_mission() returns:
{
    "success": True,
    "mission": "Implement user authentication with JWT tokens...",
    "context": {
        "project_id": "uuid",
        "agent_type": "implementer",
        "priority": "high",
        "related_agents": ["tester", "reviewer"]
    },
    "previous_work": [
        {"agent": "analyzer", "summary": "Requirements analyzed"}
    ]
}
```

**Mission Storage** (Database Fields):
- `Project.mission` - AI-generated orchestrator plan
- `MCPAgentJob.mission` - Agent-specific work assignment

**Critical Distinction** (Field Naming):
- `description` - Human-provided input (user requirements)
- `mission` - AI-generated content (orchestrator plan)

See [SERVICES.md - Database Field Naming Conventions](../SERVICES.md#database-field-naming-conventions) for details.

**Anti-Patterns** (DO NOT):
- ❌ Embed missions in message content (`send_message(content=mission)`)
- ❌ Use messages for long-form mission delivery
- ❌ Confuse `description` (user input) with `mission` (AI plan)
- ❌ Store missions in message bodies (use database fields)

---

## Team Messaging & Agent Discovery (Handover 0360)

**Purpose**: Enable agents to discover and communicate with teammates working on the same job.

**Key Tool**: `get_team_agents(job_id, tenant_key)`

**Workflow**:
1. Agent calls `get_team_agents(job_id, tenant_key)` to discover teammates
2. Filter results by role, status, or other criteria
3. Extract `agent_id` values from team members
4. Use `send_message(to_agent_id=...)` to communicate with specific teammates

**Example**:
```python
# Step 1: Discover team
team = await get_team_agents(
    job_id="job-abc",
    tenant_key="user_alice"
)
# Returns: [
#   {"agent_id": "agent-123", "role": "implementer", "status": "working"},
#   {"agent_id": "agent-456", "role": "tester", "status": "working"},
#   {"agent_id": "agent-789", "role": "reviewer", "status": "waiting"}
# ]

# Step 2: Filter active team members
active_team = [a for a in team if a["status"] == "working"]

# Step 3: Send message to all active teammates
for teammate in active_team:
    await send_message(
        to_agent_id=teammate["agent_id"],
        content="Phase 1 complete. Ready for next phase.",
        project_id="proj-456",
        tenant_key="user_alice",
        message_type="direct"
    )
```

**Use Cases**:
- **Status broadcasts**: Notify all team members of milestone completion
- **Handoffs**: Pass work between sequential agents (implementer → tester)
- **Collaboration**: Coordinate parallel work across multiple agents
- **Escalation**: Alert specific roles when blockers occur

**Identity Model**:
- `job_id` identifies the work order (task definition)
- `agent_id` identifies individual executors (running instances)
- Multiple agents can work on the same job (parallel execution)
- Message routing always uses `agent_id` (executor), never `job_id`

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ MESSAGES (Communication) - Handover 0360/0366                   │
│ ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│ │  Agent A        │─1─▶│ send_message()  │─2─▶│  messages    │ │
│ │ (agent-123)     │    │                 │    │  (table)     │ │
│ │                 │    │ to_agent_id=456 │    │ recipient_   │ │
│ │                 │    │ tenant_key="x"  │    │ agent_id=456 │ │
│ └─────────────────┘    └─────────────────┘    └──────┬───────┘ │
│                                                       │         │
│ ┌─────────────────┐    ┌─────────────────┐          │         │
│ │  Agent B        │◀3──│ receive_        │◀─────────┘         │
│ │ (agent-456)     │    │ messages()      │                    │
│ │                 │    │ agent_id=456    │  Auto-acknowledge  │
│ │                 │    │ tenant_key="x"  │  & remove from     │
│ └─────────────────┘    └─────────────────┘  queue (0360)      │
│                                                                 │
│ Team Discovery (get_team_agents):                              │
│ job_id → [agent_id_1, agent_id_2, ...] → send_message()        │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ WebSocket Events: message:sent, message:received            │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ SIGNALS (Job Lifecycle)                                         │
│ ┌─────────────┐      ┌─────────────────┐      ┌──────────────┐ │
│ │   Agent     │──1──▶│ AgentJobManager │──2──▶│ mcp_agent_   │ │
│ │             │      │                 │      │ jobs (table) │ │
│ │             │      │  - acknowledge()│      └──────────────┘ │
│ │             │      │  - progress()   │             │          │
│ │             │      │  - complete()   │             │          │
│ │             │◀─3───│  - fail()       │             ▼          │
│ └─────────────┘      └─────────────────┘      Job Status        │
│                                                (waiting →        │
│ ┌─────────────────────────────────────────────working →         │
│ │ WebSocket Events: job:status_changed,       complete)         │
│ │                  job:progress_updated                         │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ INSTRUCTIONS (Mission Fetch)                                    │
│ ┌─────────────┐      ┌─────────────────┐      ┌──────────────┐ │
│ │ Orchestrator│──1──▶│ MCP Tool        │──2──▶│ mcp_agent_   │ │
│ │ or Agent    │      │                 │      │ jobs.mission │ │
│ │             │      │ get_orchestrator│      │              │ │
│ │             │      │ _instructions() │      │ OR           │ │
│ │             │◀─3───│                 │      │ projects.    │ │
│ │             │      │ get_agent_      │      │ mission      │ │
│ └─────────────┘      │ mission()       │      └──────────────┘ │
│                      └─────────────────┘                        │
│                                                                 │
│ Returns: Mission text + context (NOT stored in messages)       │
└─────────────────────────────────────────────────────────────────┘
```

**Flow Legend**:
1. Agent/Orchestrator calls MCP tool
2. Service layer updates database (canonical store)
3. Response returned to caller
4. WebSocket events broadcast (where applicable)

---

## Code Examples

### Example 1: Agent-to-Agent Communication (MESSAGES)

**Scenario**: Implementer notifies tester that code is ready.

```python
# Step 1: Discover team members (Handover 0360)
team = await get_team_agents(
    job_id="job-abc",
    tenant_key="user_alice"
)
# Returns: [{"agent_id": "agent-123", "role": "tester", "status": "working"}, ...]

# Step 2: Find tester agent_id
tester_agent = next(a for a in team if a["role"] == "tester")
tester_agent_id = tester_agent["agent_id"]  # "agent-123"

# Step 3: Send message using agent_id (Handover 0366)
await send_message(
    to_agent_id=tester_agent_id,  # Agent executor UUID, NOT job_id
    content="Authentication implementation complete. Ready for testing. See: api/endpoints/auth.py",
    project_id="proj-456",
    tenant_key="user_alice",
    message_type="direct",
    priority="high"
)

# Step 4: Tester receives messages (auto-acknowledged, removed from queue)
messages = await receive_messages(
    agent_id=tester_agent_id,  # Own agent_id
    tenant_key="user_alice",
    limit=10
)
# Returns: [{"id": "msg-789", "content": "Authentication implementation...", ...}]
# NOTE: Messages are automatically acknowledged and removed from queue
```

**Result**:
- Message stored in `messages` table with `recipient_agent_id=agent-123`
- Message auto-acknowledged and removed from pending queue
- WebSocket events: `message:sent`, `message:received`

---

### Example 2: Job Progress Reporting (SIGNALS)

**Scenario**: Agent reports incremental progress during execution.

```python
# Agent claims job
await acknowledge_job(job_id="job-abc", agent_id="implementer-1")

# Phase 1: Initialization (25%)
await report_progress(
    job_id="job-abc",
    progress={"percent": 25, "message": "Initialization phase complete"}
)

# Phase 2: Core Implementation (50%)
await report_progress(
    job_id="job-abc",
    progress={"percent": 50, "message": "Core implementation complete"}
)

# Phase 3: Testing (75%)
await report_progress(
    job_id="job-abc",
    progress={"percent": 75, "message": "All tests passing"}
)

# Phase 4: Completion (100%)
await complete_job(
    job_id="job-abc",
    result={
        "status": "success",
        "files_modified": ["api/endpoints/auth.py", "tests/test_auth.py"],
        "tests_passed": 12,
        "documentation_updated": True
    }
)
```

**Result**:
- `MCPAgentJob` status transitions: waiting → working → complete
- Progress percentages stored in `MCPAgentJob.progress`
- WebSocket events: `job:status_changed`, `job:progress_updated` (4 times)

**UI Display**:
```
[Implementer-1]  [████████████████████░░░] 80% - All tests passing
```

---

### Example 3: Mission Fetch (INSTRUCTIONS)

**Scenario**: Agent starts work and fetches mission from server.

```python
# Agent receives thin prompt with job_id and tenant_key
# Thin prompt: "Call get_agent_mission(job_id='job-abc', tenant_key='user_alice')"

# Agent fetches mission (Handover 0262/0332: Atomic job start)
mission_data = await get_agent_mission(
    job_id="job-abc",           # Work order UUID
    tenant_key="user_alice"     # Multi-tenant isolation
)

# Returns:
{
    "success": True,
    "mission": "Implement user authentication with JWT tokens. Requirements:\n- POST /api/auth/register\n- POST /api/auth/login\n- Bcrypt password hashing\n- 1-hour access tokens, 7-day refresh tokens",
    "context": {
        "project_id": "proj-456",
        "agent_type": "implementer",
        "priority": "high",
        "related_agents": ["tester", "reviewer"]
    },
    "previous_work": [
        {
            "agent": "analyzer",
            "summary": "Analyzed authentication requirements and recommended JWT approach"
        }
    ]
}

# Agent executes mission
# ... implementation code ...

# Agent completes (using SIGNALS, not messages)
await complete_job(job_id="job-abc", result={...})
```

**Result**:
- Mission fetched from `MCPAgentJob.mission` (database field)
- No message created (missions are NOT messages)
- Agent has full context to execute work

---

## Anti-Patterns (What NOT to Do)

### Anti-Pattern 1: Embedding Missions in Messages ❌

**WRONG**:
```python
# DO NOT DO THIS
await send_message(
    to_agents=["implementer"],
    content="Your mission: Implement authentication with JWT...\n[3000 lines of mission]",
    message_type="direct"
)
```

**CORRECT**:
```python
# Store mission in database
job = await spawn_agent_job(
    agent_type="implementer",
    mission="Implement authentication with JWT...\n[3000 lines of mission]",
    project_id="proj-456"
)

# Agent fetches mission
mission = await get_agent_mission(job_id=job.id, tenant_key="user_alice")
```

**Why**: Messages are for communication, not bulk data transfer. Missions belong in database fields.

---

### Anti-Pattern 2: Using Messages for Job Status ❌

**WRONG**:
```python
# DO NOT DO THIS
await send_message(
    to_agents=["orchestrator"],
    content="Status update: 50% complete",
    message_type="direct"
)
```

**CORRECT**:
```python
# Use job signals
await report_progress(
    job_id="job-abc",
    progress={"percent": 50, "message": "Core implementation complete"}
)
```

**Why**: Job status is a signal, not a message. Status lives in `MCPAgentJob` table.

---

### Anti-Pattern 3: Bypassing MessageService ❌

**WRONG**:
```python
# DO NOT DO THIS
from src.giljo_mcp.models import Message

message = Message(
    project_id=project_id,
    to_agents=["tester"],
    content="Ready for testing",
    tenant_key=tenant_key
)
session.add(message)
await session.commit()
```

**CORRECT**:
```python
# Use MessageService
from src.giljo_mcp.services.message_service import MessageService

service = MessageService(session, tenant_key)
await service.send_message(
    to_agents=["tester"],
    content="Ready for testing",
    project_id=project_id
)
```

**Why**: `MessageService` handles JSONB mirroring, WebSocket events, and business logic. Direct database writes bypass these.

---

### Anti-Pattern 4: Confusing description vs mission ❌

**WRONG**:
```python
# DO NOT DO THIS (user input in mission field)
await update_project_mission(
    project_id="proj-456",
    mission="Add JWT authentication"  # This is user input!
)
```

**CORRECT**:
```python
# User input goes in description
await update_project(
    project_id="proj-456",
    description="Add JWT authentication"  # User requirement
)

# Orchestrator generates mission (AI-generated plan)
await update_project_mission(
    project_id="proj-456",
    mission="Implement JWT-based authentication system:\n1. Create auth endpoints...\n2. Add bcrypt hashing..."  # AI plan
)
```

**Why**: `description` = human input, `mission` = AI-generated plan. See [SERVICES.md](../SERVICES.md#database-field-naming-conventions).

---

## Testing Patterns

### Testing MESSAGES

**Service Layer Test**:
```python
@pytest.mark.asyncio
async def test_send_message_creates_message_and_updates_jsonb():
    service = MessageService(session, tenant_key="test_tenant")

    # Send message
    result = await service.send_message(
        to_agents=["tester"],
        content="Ready for testing",
        project_id="proj-456",
        message_type="direct",
        from_agent="implementer-1"
    )

    # Verify message created
    assert result["success"] is True
    message = result["data"]
    assert message.content == "Ready for testing"

    # Verify JSONB mirror updated
    implementer_job = await get_job_by_agent_id("implementer-1")
    tester_job = await get_job_by_agent_id("tester-1")

    assert implementer_job.messages[-1]["status"] == "sent"
    assert tester_job.messages[-1]["status"] == "waiting"
```

**MCP Tool Test**:
```python
@pytest.mark.asyncio
async def test_send_message_mcp_tool():
    # Call MCP tool (Handover 0366: Uses agent_id routing)
    result = await send_message(
        to_agent_id="agent-tester-123",  # Agent executor UUID
        content="Ready for testing",
        project_id="proj-456",
        tenant_key="test_tenant",
        message_type="direct"
    )

    # Verify response
    assert result["success"] is True

    # Verify message persisted
    messages = await list_messages(
        project_id="proj-456",
        tenant_key="test_tenant"
    )
    assert len(messages) == 1
    assert messages[0]["content"] == "Ready for testing"
    assert messages[0]["recipient_agent_id"] == "agent-tester-123"
```

---

### Testing SIGNALS

**Job Lifecycle Test**:
```python
@pytest.mark.asyncio
async def test_job_lifecycle_signals():
    manager = AgentJobManager(session, tenant_key="test_tenant")

    # Create job (waiting)
    job = await manager.create_job(
        agent_role="implementer",
        mission="Test mission",
        parent_job_id=None
    )
    assert job.status == "waiting"

    # Acknowledge (working)
    await manager.acknowledge_job(job.id)
    assert job.status == "working"

    # Report progress
    await manager.report_progress(job.id, {"percent": 50})
    assert job.progress == 50

    # Complete (complete)
    await manager.complete_job(job.id, {"status": "success"})
    assert job.status == "complete"
```

**Workflow Status Test**:
```python
@pytest.mark.asyncio
async def test_workflow_status_aggregation():
    # Create 10 jobs (8 complete, 2 working)
    for i in range(8):
        await create_job_and_complete(...)
    for i in range(2):
        await create_job_working(...)

    # Check workflow status
    status = await get_workflow_status(
        project_id="proj-456",
        tenant_key="test_tenant"
    )

    assert status["completed_agents"] == 8
    assert status["active_agents"] == 2
    assert status["progress_percent"] == 80  # 8/10 * 100
```

---

### Testing INSTRUCTIONS

**Mission Fetch Test**:
```python
@pytest.mark.asyncio
async def test_get_agent_mission():
    # Create job with mission
    job = await create_job(
        mission="Implement authentication system",
        agent_type="implementer"
    )

    # Fetch mission
    result = await get_agent_mission(
        job_id=job.id,
        tenant_key="test_tenant"
    )

    # Verify response
    assert result["success"] is True
    assert "Implement authentication system" in result["mission"]
    assert result["context"]["agent_type"] == "implementer"
```

---

## Related Documentation

### Core Documentation
- **Service Layer**: [SERVICES.md](../SERVICES.md) - `MessageService` API and patterns
- **Orchestrator**: [ORCHESTRATOR.md](../ORCHESTRATOR.md) - Context tracking, succession
- **Testing**: [TESTING.md](../TESTING.md) - Unit/integration test patterns

### Architecture Documentation
- **Database Schema**: [migration-strategy.md](migration-strategy.md) - Tables and constraints
- **WebSocket Events**: [SERVER_ARCHITECTURE_TECH_STACK.md](../SERVER_ARCHITECTURE_TECH_STACK.md) - Real-time updates

### Handover Documentation
- **Handover 0295**: [0295_MESSAGING_CONTRACT_AND_CATEGORIES.md](../../handovers/0295_MESSAGING_CONTRACT_AND_CATEGORIES.md) - This handover's implementation details
- **Handover 0294**: [0294_COMPLETE_RESOLUTION_FINAL_REPORT.md](../../handovers/0294_COMPLETE_RESOLUTION_FINAL_REPORT.md) - Message counter implementation

### Developer Guides
- **Field Naming**: [SERVICES.md - Database Field Naming Conventions](../SERVICES.md#database-field-naming-conventions)
- **Quick Start**: [../CLAUDE.md](../CLAUDE.md) - Quick reference for developers

---

## Summary: Which Tool When?

| Scenario | Category | Tool to Use | Store | Identity |
|----------|----------|-------------|-------|----------|
| Discover team members | MESSAGES | `get_team_agents()` | `AgentJob` query | Uses `job_id` |
| Agent notifies another agent | MESSAGES | `send_message()` | `messages` table | Uses `agent_id` (executor) |
| User sends instruction to agent | MESSAGES | `send_message()` | `messages` table | Uses `agent_id` (executor) |
| Agent receives messages | MESSAGES | `receive_messages()` | `messages` table | Uses `agent_id` (executor) |
| Agent reports progress | SIGNALS | `report_progress()` | `MCPAgentJob.progress` | Uses `job_id` (work order) |
| Agent changes status | SIGNALS | `complete_job()`, `report_error()` | `MCPAgentJob.status` | Uses `job_id` (work order) |
| Agent fetches work assignment | INSTRUCTIONS | `get_agent_mission()` | `MCPAgentJob.mission` | Uses `job_id` (work order) |
| Orchestrator fetches context | INSTRUCTIONS | `get_orchestrator_instructions()` | `Project.mission` | Uses `orchestrator_id` (work order) |
| Check workflow completion | SIGNALS | `get_workflow_status()` | `MCPAgentJob` aggregation | Uses `project_id` |

**Golden Rule**: If you're unsure which category, ask:
1. Is this **communication** between entities? → MESSAGES (use `agent_id` for routing)
2. Is this **status or progress** tracking? → SIGNALS (use `job_id` for work orders)
3. Is this **mission or configuration** delivery? → INSTRUCTIONS (use `job_id` for work orders)

**Identity Model Quick Reference (Handover 0366)**:
- **job_id**: Work order UUID (AgentJob) - the WHAT (task definition)
- **agent_id**: Executor UUID (AgentExecution) - the WHO (running instance)
- **Message routing**: Always use `agent_id` (executor), never `job_id`
- **Job signals**: Always use `job_id` (work order)
- **Team discovery**: Input `job_id` → Output list of `agent_id` values

---

**Last Updated**: 2025-12-21 (Handovers 0295, 0360, 0366)
