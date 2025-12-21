# Orchestrator Context Tracking & Succession

**Version**: v3.2+ (Handover 0080, 0246a, 0246b, 0334)
**Last Updated**: 2025-12-07

## Overview

GiljoAI MCP orchestrators have **automatic context tracking**, **staging workflows**, and **succession mechanisms** to handle complex multi-agent execution.

**Key Features (v3.2)**:
- **7-Task Staging Workflow**: Validates environment before agent execution (Handover 0246a)
- **Dynamic Agent Discovery**: Discovers agents via MCP tools (no embedded templates, 71% token reduction)
- **Generic Agent Template**: Unified protocol for multi-terminal mode (Handover 0246b)
- **Automatic Succession**: Spawns successor at 90% context capacity
- **Context Prioritization**: Condenses missions to <10K tokens for handover
- **Token Optimization**: 85% reduction in orchestrator prompts (~3,500 → ~450-550 tokens)

**Key Benefit**: **context prioritization and orchestration** through mission condensation + **unlimited project duration** through graceful succession + **environment validation** through comprehensive staging.

### Complete Orchestrator Workflow Pipeline (v3.2)

**Implementation**: Handovers 0246a, 0246b, 0246c
**Total Token Savings**: 85% reduction (3,000+ tokens per orchestrator instance)

The orchestrator workflow consists of four key phases:

```
User Action: "Launch Project"
        ↓
┌─────────────────────────────────────────────────────┐
│ PHASE 1: STAGING (7 Tasks)                         │
│ - Identity & Context Verification                   │
│ - MCP Health Check                                  │
│ - Environment Understanding                         │
│ - Agent Discovery (get_available_agents)            │
│ - Context Prioritization (unified fetch_context())  │
│ - Agent Job Spawning (MCPAgentJob records)          │
│ - Activation (project → active status)              │
│ Token Budget: 931 tokens (22% under 1200 limit)     │
└────────────┬────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────┐
│ PHASE 2: DISCOVERY                                  │
│ - Call get_available_agents() MCP tool              │
│ - Receives agent metadata (name, version, type)     │
│ - Validates version compatibility                   │
│ - NO EMBEDDED TEMPLATES (71% token savings)         │
│ Token Savings: 420 tokens (dynamic vs embedded)     │
└────────────┬────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────┐
│ PHASE 3: SPAWNING                                   │
│ - Claude Code CLI Mode: Task tool spawns sub-agents │
│ - Multi-Terminal Mode: get_generic_agent_template() │
│ - Agent calls get_agent_mission(job_id)             │
│ - Agent receives mission-specific context           │
│ Token Budget: ~1,253 tokens per agent (generic)     │
└────────────┬────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────┐
│ PHASE 4: EXECUTION                                  │
│ - Agents execute 6-phase protocol                   │
│ - Real-time coordination via messaging              │
│ - Context tracking (90% → auto succession)          │
│ - Progress reporting via WebSocket                  │
└─────────────────────────────────────────────────────┘
```

**Token Optimization Breakdown**:
- **Baseline (pre-0246)**: ~3,500 tokens per orchestrator (fat prompt)
- **After 0246a (staging)**: ~931 tokens (staging workflow)
- **After 0246b (generic template)**: +1,253 tokens per agent
- **After 0246c (dynamic discovery)**: -420 tokens (removed embedded templates)
- **Final Result**: ~450-550 tokens per orchestrator prompt
- **Total Savings**: ~3,000 tokens (85% reduction)

---

## Orchestrator Staging Workflow (v3.2)

### Overview

**Implementation**: Handover 0246a
**Purpose**: Prepare project for multi-agent execution through comprehensive validation

Before spawning any agents, the orchestrator executes a **7-task staging workflow** that validates:
- MCP server health and connectivity
- Environment understanding (CLAUDE.md, tech stack)
- Available agents (via dynamic discovery)
- Context prioritization settings
- Agent job spawning readiness

### The 7 Staging Tasks

```
1. IDENTITY & CONTEXT VERIFICATION
   ├─ Verify project ID, name, scope
   ├─ Confirm tenant isolation
   ├─ Validate orchestrator connection
   └─ Include Product ID for context tracking

2. MCP HEALTH CHECK
   ├─ Verify MCP server responsive
   ├─ Check all required MCP tools available
   ├─ Validate authentication tokens
   └─ Test connection stability

3. ENVIRONMENT UNDERSTANDING
   ├─ Read CLAUDE.md configuration
   ├─ Understand tech stack (Python, FastAPI, Vue3)
   ├─ Parse project structure
   ├─ Identify critical paths
   └─ Load context management settings

4. AGENT DISCOVERY & VERSION CHECK
   ├─ Call get_available_agents() MCP tool
   ├─ Discover all available agents in system
   ├─ Check version compatibility for each agent
   ├─ Validate agent capabilities match project needs
   └─ NO EMBEDDED TEMPLATES (fetch dynamically)

5. CONTEXT PRIORITIZATION & MISSION
   ├─ Apply user's context priority settings (3-tier: CRITICAL/IMPORTANT/REFERENCE)
   ├─ Call fetch_context(categories=[...]) based on priority tier
   ├─ CRITICAL fields: MUST fetch (product_core, project)
   ├─ IMPORTANT fields: SHOULD fetch if budget allows (tech_stack, vision_documents)
   ├─ REFERENCE fields: MAY fetch if project requires (memory_360, git_history)
   ├─ Generate unified orchestrator mission
   └─ Condense into <10K tokens (See: docs/api/context_tools.md)

6. AGENT JOB SPAWNING
   ├─ Create MCPAgentJob records for each agent

> **Migration Note (Handover 0366a - Dec 2025)**
>
> The `MCPAgentJob` model is **deprecated** as of v3.3.0.
> Use `AgentJob` (work order) and `AgentExecution` (executor instance) instead.
>
> **Key Changes:**
> - `job_id` = The work to be done (persists across succession)
> - `agent_id` = The executor doing the work (changes on succession)
>
> See Handover 0366 series for migration details. Will be removed in v4.0.

   ├─ Assign execution mode (claude-code or multi-terminal)
   ├─ Set initial status to 'waiting'
   └─ Store staging result in database

7. ACTIVATION
   ├─ Transition project to 'active' status
   ├─ Enable WebSocket event broadcasts
   ├─ Start monitoring orchestrator health
   └─ Begin agent job polling
```

### Staging Prompt Generation

**Token Budget**: 931 tokens (22% under 1200-token limit)

**Implementation**:
```python
from src.giljo_mcp.prompts.thin_prompt_generator import ThinClientPromptGenerator

generator = ThinClientPromptGenerator(
    project_id=project_id,
    product_id=product_id,
    tenant_key=tenant_key
)

# Generate 7-task staging prompt
staging_prompt = generator._build_staging_prompt()

# Prompt includes:
# - Identity section (project_id, product_id, tenant_key)
# - MCP health check instructions
# - Environment understanding tasks
# - Agent discovery via get_available_agents() tool
# - Context prioritization guidance
# - Job spawning protocol
# - Activation checklist
```

**Code Reference**: `src/giljo_mcp/prompts/thin_prompt_generator.py::_build_staging_prompt()`

**Related Documentation**:
- Complete technical details: [SERVER_ARCHITECTURE_TECH_STACK.md](SERVER_ARCHITECTURE_TECH_STACK.md#orchestrator-staging--agent-spawning-architecture-v32)
- Step-by-step workflow: [components/STAGING_WORKFLOW.md](components/STAGING_WORKFLOW.md)
- Quick reference: [CLAUDE.md](../CLAUDE.md#orchestrator-workflow-pipeline-v32-handovers-0246a-c)

### Dynamic Agent Discovery

**No Embedded Templates**: GiljoAI v3.2 eliminates hardcoded agent templates from staging prompts.

**Discovery Process**:
```python
# Orchestrator calls during Task 4
result = get_available_agents()

# Returns agent metadata:
{
  "agents": [
    {
      "name": "implementer",
      "version": "1.0.3",
      "type": "role",
      "required_context": ["tech_stack", "architecture"],
      "capabilities": ["code_generation", "refactoring"]
    },
    {
      "name": "tester",
      "version": "1.0.2",
      "type": "role",
      "required_context": ["tech_stack", "testing_config"],
      "capabilities": ["unit_testing", "integration_testing"]
    }
  ]
}
```

**Version Compatibility Validation**:
- Checks: `agent.version >= minimum_required_version`
- Validates: `required_capabilities ⊆ agent.capabilities`
- Verifies: `agent.status == 'initialized'`
- Reports: Version conflicts and incompatibilities

**Token Savings**: 420 tokens (71% reduction vs embedded templates)

**Implementation Details** (Handover 0246c):
- **New MCP Tool**: `src/giljo_mcp/tools/agent_discovery.py` (167 lines)
- **Function**: `get_available_agents(session, tenant_key, active_only=True)`
- **Features**:
  - Multi-tenant isolation (tenant_key filtering)
  - Version metadata tracking
  - Active-only filtering option
  - Graceful error handling
  - Production-grade logging

**Before (embedded templates in prompts)**:
- 5-8 agent templates fully embedded in staging prompt
- Each template: ~71-86 tokens
- Total overhead: ~430 tokens per orchestrator

**After (dynamic discovery)**:
- Single MCP call: `get_available_agents(tenant_key, active_only=True)`
- Overhead: ~10 tokens (just the function call)
- Agent metadata returned (name, version, type, capabilities)
- Templates fetched on-demand when needed

**Code References**:
- Discovery Tool: `src/giljo_mcp/tools/agent_discovery.py`
- Integration: `src/giljo_mcp/tools/orchestration.py::get_available_agents()`
- Tests: `tests/unit/test_agent_discovery.py` (11 tests, 100% passing)
- Integration Tests: `tests/integration/test_orchestrator_discovery.py` (6 tests)

### Staging Result Storage

After successful staging, results are stored in `MCPAgentJob.staging_result`:

```json
{
  "staging_tasks_completed": [
    "identity_verification",
    "mcp_health_check",
    "environment_understanding",
    "agent_discovery",
    "context_prioritization",
    "job_spawning",
    "activation"
  ],
  "agents_discovered": [
    {"name": "implementer", "version": "1.0.3", "compatible": true},
    {"name": "tester", "version": "1.0.2", "compatible": true},
    {"name": "reviewer", "version": "1.0.1", "compatible": true}
  ],
  "context_budget_used": 8743,
  "staging_duration_ms": 2341,
  "execution_mode": "claude_code_cli"
}
```

**Code Reference**: `src/giljo_mcp/models.py::MCPAgentJob.staging_result`

> **Migration Note (Handover 0366a - Dec 2025)**
>
> The `MCPAgentJob` model is **deprecated** as of v3.3.0.
> Use `AgentJob` (work order) and `AgentExecution` (executor instance) instead.
>
> See Handover 0366 series for migration details. Will be removed in v4.0.

---

## Agent Execution Modes (v3.2)

### Overview

**Implementation**: Handover 0246b
**Purpose**: Support both single-terminal (Claude Code) and multi-terminal (Generic) execution

GiljoAI v3.2 supports two distinct agent execution modes:

### Mode 1: Claude Code CLI (Single Terminal)

**When to Use**:
- Local development workflows
- Single developer working on project
- Rapid iteration with sub-agent spawning
- Real-time agent coordination

**Characteristics**:
- Orchestrator spawns sub-agents via Task tool
- All agents run in single Claude Code CLI session
- Mission-specific prompts generated per agent
- Direct message queue communication
- Optimized for developer productivity

**Implementation**:
```python
# Orchestrator uses Task tool
Task(
    agent_type="implementer",
    mission="Implement user authentication with JWT tokens",
    context=condensed_context
)

# Sub-agent executes in same terminal
# Reports completion back to orchestrator
```

**Code Reference**: Claude Code Task tool integration

### Mode 2: Manual Multi-Terminal (Generic Template)

**When to Use**:
- Distributed team execution
- Multiple terminals/sessions required
- Agent independence preferred
- Debugging specific agent behaviors

**Characteristics**:
- Each agent runs in separate terminal/session
- Generic unified template for all agent types
- Mission fetched from database at runtime
- Orchestrator coordinates via MCPAgentJob records
- Optimized for distributed execution

**Implementation**:
```python
# Terminal 1: Orchestrator spawns job
job = await spawn_agent_job(
    agent_type="implementer",
    execution_mode="multi_terminal_generic",
    mission="Implement authentication system",
    status="waiting"
)

# Terminal 2: Implementer agent
template = get_generic_agent_template(
    agent_id=agent_id,
    job_id=job.id,
    product_id=product_id,
    project_id=project_id,
    tenant_key=tenant_key
)

# Agent calls get_agent_mission() to fetch work
mission = get_agent_mission(job_id=job.id, tenant_key=tenant_key)

# Agent executes mission and reports completion
complete_job(job_id=job.id, result=result_summary)
```

**Code Reference**:
- Template: `src/giljo_mcp/templates/generic_agent_template.py`
- Tool: `src/giljo_mcp/tools/orchestration.py::get_generic_agent_template()`

---

## Generic Agent Template Protocol (v3.2)

### Overview

**Implementation**: Handover 0246b
**Purpose**: Unified protocol for all agents in multi-terminal mode

The Generic Agent Template provides a **single template** used by **all agent types** (implementer, tester, reviewer, analyzer, documenter).

### Variable Injection

**Orchestrator Injects**:
```python
{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "job_id": "7e57d004-2b97-0e7a-b45f-5387367791cd",
    "product_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "project_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "tenant_key": "user_alice_tenant_001"
}
```

**Agent Fetches at Runtime**:
```python
# Call MCP tool
mission_data = get_agent_mission(
    job_id="7e57d004-2b97-0e7a-b45f-5387367791cd",
    tenant_key="user_alice_tenant_001"
)

# Receives (Handover 0334 enhanced response):
{
    "success": true,
    "agent_job_id": "7e57d004-2b97-0e7a-b45f-5387367791cd",
    "agent_name": "implementer",
    "agent_type": "implementer",
    "mission": "Implement user authentication with JWT tokens...",
    "project_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "estimated_tokens": 250,
    "status": "working",
    "thin_client": true,
    "full_protocol": "## Agent Lifecycle Protocol (6 Phases)\\n\\n### Phase 1: STARTUP..."
}
```

**Note**: The `full_protocol` field (added in Handover 0334) contains the complete 6-phase lifecycle instructions with job-specific MCP tool call examples. This makes agents self-documenting - they receive both their mission AND how to execute it.

### Six-Phase Execution Protocol

All agents follow this standard protocol:

**Phase 1: Initialization**
- Verify identity (agent_id, job_id)
- Check MCP health via `health_check()`
- Read CLAUDE.md for project context and standards

**Phase 2: Mission Fetch**
- Call `get_agent_mission(job_id, tenant_key)`
- Parse received mission and requirements
- Understand scope and deliverables
- Identify dependencies

**Phase 3: Work Execution**
- Execute the mission as specified
- Follow GiljoAI standards (see CLAUDE.md)
- Track progress at 25%, 50%, 75%, 100%
- Collect all outputs (code, tests, documentation)

**Phase 4: Progress Reporting**
```python
# Report at each milestone
update_job_progress(
    job_id=job_id,
    percent_complete=25,
    status_message="Initialization phase complete"
)

update_job_progress(
    job_id=job_id,
    percent_complete=50,
    status_message="Core implementation complete"
)

# Continue at 75%, 100%
```

**Phase 5: Communication**
```python
# Send message to another agent
send_message(
    to_agent_id=tester_agent_id,
    message="Authentication implementation complete. Ready for testing."
)

# Receive messages
messages = receive_messages(agent_id=agent_id)

# Acknowledge receipt
for msg in messages:
    acknowledge_message(message_id=msg['id'])
```

**Phase 6: Completion**
```python
# Mark job complete with results
complete_job(
    job_id=job_id,
    result={
        "status": "success",
        "summary": "Implemented JWT-based authentication system",
        "deliverables": [
            "api/endpoints/auth.py",
            "tests/test_auth.py",
            "docs/AUTHENTICATION.md"
        ],
        "test_results": {"passed": 15, "failed": 0},
        "documentation_updated": true,
        "notes": "Ready for security review"
    }
)
```

### Template Token Budget

**Token Count**: ~2400 tokens per agent

**Breakdown**:
- Protocol phases: ~1200 tokens
- GiljoAI standards: ~800 tokens
- Communication examples: ~400 tokens

**Code Reference**: `src/giljo_mcp/templates/generic_agent_template.py::GenericAgentTemplate.render()`

---

## Execution Phase Monitoring (Handover 0355)

After completing the 7-task staging workflow (Tasks 1-7), orchestrators enter the **execution phase monitoring** stage. This is effectively Task 8 of the orchestrator workflow, where active coordination of spawned agents occurs.

### Step 7: EXECUTION PHASE MONITORING

**Purpose**: Actively monitor spawned agents, coordinate handoffs, and handle real-time issues during project execution.

**Implementation**: Handover 0355 (Protocol Message Handling Fix)

#### Sequential Execution Pattern

Use this pattern when agents must complete in a specific order (dependencies between tasks):

```
1. Spawn Agent A
2. Poll Agent A status every 2-3 minutes via receive_messages()
3. Wait for Agent A completion
4. Send handoff message to Agent B if needed
5. Spawn Agent B
6. Repeat polling pattern until all agents complete
```

**Example**:
```python
# Sequential: Analyzer must complete before Implementer starts

# 1. Spawn analyzer
spawn_agent_job(agent_type="analyzer", mission="Analyze requirements...")

# 2. Poll analyzer status
while True:
    messages = receive_messages(agent_id=orchestrator_id)
    if any(msg.get("type") == "agent_completed" and msg.get("agent") == "analyzer" for msg in messages):
        break
    time.sleep(180)  # Poll every 3 minutes

# 3. Send handoff message
send_message(
    to_agent=implementer_id,
    message="Analyzer complete. You may proceed with implementation."
)

# 4. Spawn implementer
spawn_agent_job(agent_type="implementer", mission="Implement features...")
```

#### Parallel Execution Pattern

Use this pattern when multiple agents can work simultaneously (no dependencies):

```
1. Spawn all agents (A, B, C) simultaneously
2. Poll ALL agent statuses every 2-3 minutes via receive_messages()
3. As agents finish, check results and send follow-up guidance
4. Continue polling until ALL agents complete
```

**Example**:
```python
# Parallel: Analyzer and Documenter work simultaneously

# 1. Spawn both agents
spawn_agent_job(agent_type="analyzer", mission="Analyze codebase...")
spawn_agent_job(agent_type="documenter", mission="Update documentation...")

# 2. Poll both agents
completed_agents = set()
while len(completed_agents) < 2:
    messages = receive_messages(agent_id=orchestrator_id)

    # Check for completions
    for msg in messages:
        if msg.get("type") == "agent_completed":
            agent_name = msg.get("agent")
            completed_agents.add(agent_name)

            # Send follow-up guidance if needed
            if agent_name == "analyzer":
                send_message(
                    to_agent=documenter_id,
                    message="Analysis complete. Focus on documenting new features."
                )

    time.sleep(180)  # Poll every 3 minutes
```

#### Mandatory Final Message Check

**CRITICAL**: Before calling `complete_job()`, orchestrators MUST call `receive_messages()` to process any blocking issues or agent error reports.

```python
# Before completion
final_messages = receive_messages(agent_id=orchestrator_id)

# Process any errors or blockers
for msg in final_messages:
    if msg.get("status") == "blocked":
        # Handle blocked agent
        send_message(to_agent=msg["from_agent"], message="Provide guidance...")
    elif msg.get("status") == "error":
        # Handle error condition
        log_error(f"Agent {msg['from_agent']} reported error: {msg['error']}")

# Only complete after all issues resolved
if all_agents_completed and no_blocking_issues:
    complete_job(job_id=orchestrator_id, result=final_summary)
```

#### Agent Coordination Patterns

**Dependency Handoff** (A must finish before B starts):
```python
# 1. Spawn Agent A
# 2. Poll A until status = COMPLETED
# 3. Send Agent B: "Agent A completed, you may proceed"
# 4. Spawn Agent B
```

**Parallel with Convergence** (A and B work independently, C waits for both):
```python
# 1. Spawn Agents A + B
# 2. Poll until BOTH complete
# 3. Send Agent C: "Prerequisites complete, proceed with integration"
# 4. Spawn Agent C
```

**Progress Broadcasting** (all agents need status updates):
```python
# After each agent milestone
send_message(to_agent="all", message="Milestone X completed, team status update...")
# This keeps team aligned without blocking individual agents
```

### Message Handling During Execution

**When to Check Messages**:
- Every 2-3 minutes during active execution
- After each agent reports completion
- Before spawning a new agent (check for blockers)
- Before calling `complete_job()` (final check)

**Tool Usage**:
- **ALWAYS** use `receive_messages()` for message checks (auto-acknowledges and removes from queue)
- **NEVER** use `list_messages()` during execution (read-only, messages stay pending - debugging only)

**Queue Management**:
- Empty queue = All agents progressing normally, safe to continue monitoring
- Non-empty queue = Process ALL messages before making coordination decisions
- Blocked messages = Pause execution, send guidance, wait for unblock confirmation

### Why Execution Phase Monitoring Matters

**Without active monitoring**:
- Orchestrator spawns agents and waits passively
- No opportunity for mid-flight corrections
- Agent blockers go undetected until timeout
- Missed opportunities for coordination and handoffs

**With active monitoring**:
- Real-time detection of agent completion/blockers
- Immediate guidance when agents need course correction
- Coordinated handoffs between dependent agents
- Faster overall project completion through active coordination

**Related Documentation**:
- Implementation Details: [Handover 0355](../handovers/0355_protocol_message_handling_fix.md)
- Staging Workflow: [STAGING_WORKFLOW.md](components/STAGING_WORKFLOW.md#task-8-execution-phase-monitoring)
- Message Tools API: [MCP Tools Manual](manuals/MCP_TOOLS_MANUAL.md)

---

## Context Tracking Architecture

### **How It Works**

1. **Context Budget**: Each orchestrator starts with a context budget (default: 200,000 tokens)
2. **Usage Tracking**: Every message sent/received updates `context_used` counter
3. **Auto-Succession Trigger**: At 90% capacity, successor spawned automatically
4. **Handover Summary**: Mission condensed to <10K tokens via MissionPlanner
5. **Lineage Preservation**: Full succession chain tracked via `spawned_by` links

### **Database Fields** (mcp_agent_jobs table)

```sql
-- Context tracking
context_used INTEGER DEFAULT 0,          -- Current token usage
context_budget INTEGER DEFAULT 200000,   -- Maximum tokens allowed

-- Succession
instance_number INTEGER DEFAULT 1,       -- Orchestrator instance in chain
spawned_by INTEGER REFERENCES mcp_agent_jobs(id),  -- Parent orchestrator
handover_to INTEGER REFERENCES mcp_agent_jobs(id), -- Successor orchestrator
handover_summary TEXT,                   -- Condensed context for successor
succession_reason VARCHAR(50),           -- Why succession triggered
handover_context_refs JSONB              -- References to full context
```

---

## Implementation: OrchestrationService

### **Creating Orchestrator with Context Tracking**

```python
from src.giljo_mcp.services.orchestration_service import OrchestrationService

service = OrchestrationService(session, tenant_key="user123")

# Create orchestrator with context budget
job = await service.create_orchestrator_job(
    project_id=project_id,
    mission=mission,
    context_budget=200000  # tokens (adjustable)
)

# Result:
# job.context_used = 0
# job.context_budget = 200000
# job.instance_number = 1
# job.spawned_by = None (first orchestrator)
```

### **Tracking Context Usage**

```python
# After each message send/receive
await service.update_context_usage(
    job_id=job.id,
    additional_tokens=1500  # Message size in tokens
)

# Check current status
status = await service.get_context_status(job.id)
# Returns:
# {
#   "context_used": 180000,
#   "context_budget": 200000,
#   "percentage_used": 0.90,
#   "tokens_remaining": 20000
# }
```

### **Auto-Succession Trigger** (90% Threshold)

```python
# Automatic succession when context reaches 90%
if status['percentage_used'] >= 0.9:
    successor = await service.trigger_succession(
        job_id=job.id,
        reason="context_limit"
    )

    # Successor details:
    # successor.instance_number = 2  (parent was 1)
    # successor.spawned_by = job.id  (lineage preserved)
    # successor.handover_summary = "<10K tokens condensed context>"
    # successor.context_used = 0  (fresh start)
    # successor.context_budget = 200000  (same as parent)
```

---

## Handover Summary Generation

### **Mission Condensation** (70% Token Reduction)

The handover summary is generated using **MissionPlanner** to condense the full project context:

```python
from src.giljo_mcp.mission_planner import MissionPlanner

planner = MissionPlanner()

# Original context: 180,000 tokens
full_context = {
    "vision_documents": [...],
    "completed_missions": [...],
    "agent_results": [...],
    "conversation_history": [...]
}

# Condensed summary: <10,000 tokens
handover_summary = await planner.generate_handover_summary(
    project_id=project_id,
    parent_job_id=job.id,
    full_context=full_context
)

# Summary includes:
# - Mission objectives (condensed)
# - Completed work (bullet points)
# - Blockers and pending items
# - Key decisions and rationale
# - References to full context (handover_context_refs JSONB)
```

### **Handover Summary Structure**

```markdown
# Orchestrator Handover Summary (Instance 1 → 2)

## Mission Objectives
- Build user authentication system with JWT tokens
- Implement password reset flow with email verification
- Add 2FA support (TOTP)

## Completed Work (Instance 1)
✅ User registration endpoint (POST /api/auth/register)
✅ Login endpoint with JWT generation (POST /api/auth/login)
✅ Password hashing with bcrypt
✅ Database schema (users, sessions tables)

## Pending Work
🔲 Password reset flow (email service integration needed)
🔲 2FA implementation (TOTP library selection)
🔲 Session management (refresh tokens)

## Key Decisions
- Use bcrypt for password hashing (strength: 12 rounds)
- JWT expiry: 1 hour (access), 7 days (refresh)
- Email service: SendGrid (API key in .env)

## Blockers
- SendGrid API key pending from client
- 2FA library undecided (pyotp vs duo_client)

## References
Full context available in:
- Vision document: product_123/vision_v1.md
- Agent results: jobs [456, 457, 458, 459, 460]
- Conversation history: project_789/messages (timestamp: 2025-11-15T10:30:00Z)
```

**Token Count**: ~1,200 tokens (vs 180,000 original)

---

## Manual Succession Triggers

### **1. Slash Command: `/gil_handover`**

Users can manually trigger succession via slash command (Handover 0080a):

```bash
# In Claude Code CLI or Codex CLI
/gil_handover
```

**Flow**:
1. User executes `/gil_handover` command
2. System checks if orchestrator is working status
3. Generates handover summary
4. Returns launch prompt for successor instance
5. User copies prompt and launches new Claude Code session

### **2. UI "Hand Over" Button**

Dashboard shows "Hand Over" button on working orchestrator cards:

**Location**: `frontend/src/components/projects/AgentCardEnhanced.vue`

**Flow**:
1. User clicks "Hand Over" button
2. LaunchSuccessorDialog opens with generated prompt
3. User copies prompt
4. Launches new Claude Code session with prompt
5. Successor orchestrator created with instance_number++

---

## Succession Timeline UI

### **SuccessionTimeline.vue Component**

Visual timeline showing orchestrator succession chain:

```
Instance 1              Instance 2              Instance 3
(Completed)             (Working)               (Pending)
[====================] [===========>          ] [                    ]
Context: 100%           Context: 55%            Context: 0%
Duration: 8h            Duration: 4h            Duration: -

Handover reason: context_limit
Handover reason: (pending)
```

**Key Features**:
- **Instance badges**: Show orchestrator number (1, 2, 3, ...)
- **Context bars**: Visual progress (green: <70%, yellow: 70-89%, red: 90%+)
- **Duration tracking**: Time spent per instance
- **Handover markers**: Show succession reason (context_limit, manual, error)
- **Lineage navigation**: Click to view parent/successor details

---

## Succession Reasons

| Reason | Description | Trigger |
|--------|-------------|---------|
| `context_limit` | Automatic at 90% context capacity | Auto (OrchestrationService) |
| `manual` | User-initiated via `/gil_handover` or UI | Manual (slash command or button) |
| `error` | Orchestrator encountered unrecoverable error | Auto (error handler) |
| `completion` | Project completed, new phase starting | Manual (project manager) |

---

## Benefits of Orchestrator Succession

### **1. Unlimited Project Duration**

**Before succession**:
- Orchestrator hits 200K token limit
- Project stalls (cannot continue)
- Manual restart required

**After succession**:
- Auto-spawn successor at 90%
- Seamless handover (<10K token summary)
- Project continues indefinitely

### **2. 70% Token Reduction**

**Mission condensation** reduces context size:
- Original: 180,000 tokens (full conversation history)
- Condensed: <10,000 tokens (mission summary)
- **Savings**: 170,000 tokens (94% reduction)

### **3. Graceful Context Management**

**Prevents context pollution**:
- Old conversations archived (handover_context_refs)
- Successor starts fresh with essential context
- No degradation in reasoning quality

### **4. Full Lineage Tracking**

**Audit trail preserved**:
- spawned_by chain shows full succession history
- Handover summaries preserved in database
- UI timeline visualizes entire project journey

---

## Testing Orchestrator Succession

### **Unit Test Example**

```python
@pytest.mark.asyncio
async def test_auto_succession_trigger(db_session, test_tenant):
    service = OrchestrationService(db_session, test_tenant)

    # Create orchestrator with small budget for testing
    job = await service.create_orchestrator_job(
        project_id=1,
        mission="Test mission",
        context_budget=10000  # Small budget
    )

    # Simulate context usage approaching 90%
    await service.update_context_usage(job.id, 9100)  # 91% used

    # Check succession triggered
    status = await service.get_context_status(job.id)
    assert status['percentage_used'] >= 0.9

    # Trigger succession
    successor = await service.trigger_succession(job.id, "context_limit")

    # Verify successor
    assert successor.instance_number == 2
    assert successor.spawned_by == job.id
    assert successor.handover_summary is not None
    assert len(successor.handover_summary) < 10000  # <10K tokens
```

### **Integration Test Example**

```python
@pytest.mark.asyncio
async def test_full_succession_workflow(db_session, test_tenant):
    service = OrchestrationService(db_session, test_tenant)

    # Create orchestrator
    job1 = await service.create_orchestrator_job(
        project_id=1,
        mission="Build authentication system",
        context_budget=200000
    )

    # Simulate work (context usage)
    await service.update_context_usage(job1.id, 180000)  # 90% used

    # Trigger succession
    job2 = await service.trigger_succession(job1.id, "context_limit")

    # Verify lineage
    assert job2.spawned_by == job1.id
    assert job2.instance_number == job1.instance_number + 1

    # Verify handover summary
    assert job2.handover_summary is not None
    assert "Build authentication system" in job2.handover_summary

    # Original job marked as succeeded
    await db_session.refresh(job1)
    assert job1.handover_to == job2.id
    assert job1.status == "succeeded"
```

---

## API Endpoints

### **GET /api/orchestrator/context-status/{job_id}**

Get current context usage for orchestrator:

```bash
curl http://localhost:7272/api/orchestrator/context-status/123
```

Response:
```json
{
  "job_id": 123,
  "context_used": 180000,
  "context_budget": 200000,
  "percentage_used": 0.90,
  "tokens_remaining": 20000,
  "auto_succession_threshold": 0.90
}
```

### **POST /api/orchestrator/trigger-succession**

Manually trigger succession:

```bash
curl -X POST http://localhost:7272/api/orchestrator/trigger-succession \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 123,
    "reason": "manual"
  }'
```

Response:
```json
{
  "successor": {
    "id": 124,
    "instance_number": 2,
    "spawned_by": 123,
    "handover_summary": "...",
    "launch_prompt": "Continue project with successor orchestrator..."
  }
}
```

---

## Best Practices

### **1. Monitor Context Usage Proactively**

Don't wait for 90% threshold:
```python
# Check context status regularly
status = await service.get_context_status(job.id)
if status['percentage_used'] > 0.75:
    logger.warning(f"Context at 75% for job {job.id}")
```

### **2. Configure Context Budget per Project**

Adjust budget based on project complexity:
```python
# Simple projects: smaller budget
job = await service.create_orchestrator_job(
    project_id=simple_project.id,
    context_budget=100000  # 100K tokens
)

# Complex projects: larger budget
job = await service.create_orchestrator_job(
    project_id=complex_project.id,
    context_budget=300000  # 300K tokens (requires tier upgrade)
)
```

### **3. Preserve Context References**

Always store references to full context:
```python
handover_context_refs = {
    "vision_doc_id": 456,
    "agent_job_ids": [789, 790, 791],
    "message_range": {
        "start_timestamp": "2025-11-15T10:00:00Z",
        "end_timestamp": "2025-11-15T18:00:00Z"
    }
}

await service.trigger_succession(
    job_id=job.id,
    reason="context_limit",
    context_refs=handover_context_refs
)
```

### **4. Test Succession Locally**

Simulate succession before production:
```bash
# Create orchestrator with small budget
pytest tests/integration/test_succession.py::test_small_budget_succession -v

# Verify handover summary quality
pytest tests/integration/test_succession.py::test_handover_summary_completeness -v
```

---

## Troubleshooting

### **Issue: Succession Not Triggering at 90%**

**Diagnosis**:
```python
# Check if context tracking is enabled
job = await session.get(AgentJob, job_id)
if job.context_budget is None:
    logger.error("Context budget not set!")

# Check if update_context_usage is being called
# Add logging to OrchestrationService.update_context_usage()
```

**Solution**: Ensure `create_orchestrator_job()` sets `context_budget` and `update_context_usage()` is called after every message.

### **Issue: Handover Summary Too Large (>10K tokens)**

**Diagnosis**:
```python
# Check handover summary size
summary_tokens = len(job.handover_summary.split()) * 1.3  # Rough estimate
if summary_tokens > 10000:
    logger.warning(f"Handover summary: {summary_tokens} tokens (too large!)")
```

**Solution**: Increase mission condensation ratio in MissionPlanner or exclude verbose agent outputs.

### **Issue: Successor Not Receiving Full Context**

**Diagnosis**:
```python
# Check handover_context_refs
if not job.handover_context_refs:
    logger.error("No context references in handover!")
```

**Solution**: Populate `handover_context_refs` with vision doc IDs, agent job IDs, and message timestamps for full context retrieval.

---

## Related Documentation

### Core Documentation
- **Architecture**: [SERVER_ARCHITECTURE_TECH_STACK.md](SERVER_ARCHITECTURE_TECH_STACK.md) - Complete system architecture
- **Context Tools API**: [api/context_tools.md](api/context_tools.md) - Unified fetch_context() tool reference
- **Staging Workflow**: [components/STAGING_WORKFLOW.md](components/STAGING_WORKFLOW.md) - 7-task staging details
- **Services**: [SERVICES.md](SERVICES.md) - OrchestrationService API
- **Testing**: [TESTING.md](TESTING.md) - Succession test patterns

### User Guides
- **Orchestrator Succession**: [user_guides/orchestrator_succession_guide.md](user_guides/orchestrator_succession_guide.md)
- **Agent Execution Modes**: [user_guides/AGENT_EXECUTION_MODES.md](user_guides/AGENT_EXECUTION_MODES.md)

### Developer Guides
- **Succession Developer Guide**: [developer_guides/orchestrator_succession_developer_guide.md](developer_guides/orchestrator_succession_developer_guide.md)
- **Quick Reference**: [../CLAUDE.md](../CLAUDE.md#orchestrator-workflow-pipeline-v32-handovers-0246a-c)

### Handover Documents (0246 Series)
- **Handover 0246a**: Staging Prompt Implementation (7-task workflow, 931 tokens)
- **Handover 0246b**: Generic Agent Template (6-phase protocol, 1,253 tokens)
- **Handover 0246c**: Dynamic Agent Discovery (71% token savings, 420 tokens)
- **Summary**: [../handovers/orchestrator_workflow_after246.md](../handovers/orchestrator_workflow_after246.md)

---

**Last Updated**: 2025-12-15 (v3.2 - Handovers 0246a-c, 0350a-c integrated)
