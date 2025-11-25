# Orchestrator Staging Workflow

**Version**: v3.2+
**Implementation**: Handovers 0246a, 0246b, 0246c
**Last Updated**: 2025-11-24

## Overview

The **Orchestrator Staging Workflow** is a 7-task validation sequence that prepares projects for multi-agent execution. This workflow ensures environment readiness, validates agent availability, and establishes proper execution context before spawning any agent jobs.

**Purpose**: Prevent execution failures through comprehensive pre-flight validation

**Token Budget**: 931 tokens (22% under 1200-token staging limit)

**Complete 0246 Series Integration**:
- **Handover 0246a**: 7-task staging workflow implementation (931 tokens)
- **Handover 0246b**: Generic agent template with 6-phase protocol (1,253 tokens per agent)
- **Handover 0246c**: Dynamic agent discovery via MCP tool (71% token savings, 420 tokens)
- **Total Impact**: 85% reduction in orchestrator prompts (~3,500 → ~450-550 tokens)

---

## Architecture Overview

### What Runs Where

**SERVER (F:\GiljoAI_MCP)**:
- **Database Storage**: PostgreSQL (agent templates, missions, projects, products, vision documents)
- **MCP HTTP Endpoint Provider**: FastAPI server at `POST /mcp` (port 7272)
- **Tool Implementations**: orchestration.py, agent_discovery.py, context_tools.py, etc.
- **WebSocket Server**: Real-time UI updates for dashboard
- **Vue Dashboard**: Frontend UI for product/project management
- **DOES NOT**: Execute orchestrators, execute agents, store project files

**CLIENT PC (Remote Developer Machine)**:
- **Claude Code Terminal**: Orchestrator execution environment
- **Separate Terminals**: Agent execution (multi-terminal mode)
- **Project Files**: Local filesystem at `/path/to/my-project/`
- **MCP HTTP Client**: Calls server endpoints via HTTP POST
- **DOES NOT**: Store missions, agent templates, product data

### Communication Flow

```
CLIENT PC                          SERVER (F:\GiljoAI_MCP)
─────────────────────────────────  ────────────────────────────────────

1. Orchestrator starts in
   Claude Code terminal

2. Calls get_orchestrator_     ──→  3. Receives HTTP POST /mcp
   instructions()                      {method: "tools/call",
   (HTTP POST)                          name: "get_orchestrator_instructions"}

                                    4. Fetches from PostgreSQL:
                                       - Project data
                                       - Product context
                                       - Vision documents
                                       - Git history
                                       - 360 memory

5. Receives mission data       ←──  6. Returns mission (~10K tokens)
   (~10K tokens)                       via JSON-RPC response

7. Orchestrator executes
   7-task staging workflow
   on CLIENT PC

8. Calls get_available_agents() ──→ 9. Queries agent_templates table

10. Receives agent list        ←── 11. Returns agents with versions

12. Spawns agent jobs              12. Creates MCPAgentJob records
    (database records only)    ──→     in PostgreSQL

13. Agent 1 starts in
    separate terminal

14. Calls get_agent_mission()  ──→ 15. Fetches agent-specific mission

16. Agent executes on          ←── 17. Returns mission + context
    CLIENT PC with project
    files from local filesystem
```

### Key Implications

1. **Project Files Location**: Client PC local filesystem (NOT server)
   - Orchestrator: `/path/to/my-project/src/`
   - Agent: `/path/to/my-project/tests/`
   - Server has zero access to project files

2. **Code Execution**: All orchestrator/agent code runs on CLIENT PC
   - Server only provides data via HTTP endpoints
   - No code execution on server side (only database queries)
   - Orchestrator and agents read/write files on client filesystem

3. **Multi-Tenant Isolation**: Enforced at database level
   - All MCP tools filter by `tenant_key`
   - Client authenticates via X-API-Key header
   - Session tied to tenant context
   - No cross-tenant data leakage possible

4. **Network Requirements**:
   - Client needs HTTP access to server (port 7272)
   - WebSocket connection optional (for real-time dashboard updates)
   - No VPN required (uses standard HTTP/HTTPS)
   - Can work across internet with proper firewall configuration

**See Also**: [Server Architecture](../SERVER_ARCHITECTURE_TECH_STACK.md#client-server-execution-model) for complete system architecture.

---

## The 7 Staging Tasks

### Task 1: Identity & Context Verification

**Purpose**: Establish project identity and confirm isolation boundaries

**Actions**:
1. Verify project ID is valid UUID
2. Confirm project name matches database record
3. Validate scope and objectives are well-defined
4. Confirm tenant isolation (tenant_key)
5. Validate orchestrator connection to MCP server
6. Include Product ID for context tracking
7. Check WebSocket connectivity

**Validation Criteria**:
- Project ID exists in database
- Tenant key matches authenticated user
- Product ID is associated with project
- WebSocket connection established

**Failure Modes**:
- Project not found → Error: Invalid project ID
- Tenant mismatch → Error: Access denied (cross-tenant violation)
- Product not found → Error: Orphaned project (no parent product)
- WebSocket unavailable → Warning: Real-time updates disabled

**Example Output**:
```
✓ Project ID verified: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d
✓ Project name: "User Authentication System"
✓ Product ID: f47ac10b-58cc-4372-a567-0e02b2c3d479
✓ Tenant key: user_alice_tenant_001
✓ Orchestrator ID: 7e57d004-2b97-0e7a-b45f-5387367791cd
✓ WebSocket: Connected (ws://localhost:7272/ws)
```

---

### Task 2: MCP Health Check

**Purpose**: Verify MCP server is healthy and all required tools are available

**Actions**:
1. Call `health_check()` MCP tool
2. Verify response time < 2 seconds
3. Check authentication token validity
4. List all available MCP tools
5. Validate required tools present:
   - `get_available_agents()`
   - `fetch_product_context()`
   - `fetch_vision_document()`
   - `fetch_git_history()`
   - `fetch_360_memory()`
6. Report status to project coordination queue
7. Proceed to Task 3 on success
8. Pause on failure (requires intervention)

**Validation Criteria**:
- MCP server responds within 2 seconds
- Authentication token valid (not expired)
- All 5 required tools available
- No connection errors

**Failure Modes**:
- Timeout (>2s) → Error: MCP server unresponsive
- Invalid token → Error: Authentication failed (re-authenticate)
- Missing tools → Error: MCP server incomplete (reinstall/update)

**Example Output**:
```
✓ MCP health check: PASS
✓ Response time: 347ms
✓ Authentication: Valid (expires in 23h 45m)
✓ Required tools available: 5/5
  - get_available_agents() ✓
  - fetch_product_context() ✓
  - fetch_vision_document() ✓
  - fetch_git_history() ✓
  - fetch_360_memory() ✓
```

---

### Task 3: Environment Understanding

**Purpose**: Understand project environment, tech stack, and coding standards

**Actions**:
1. Read CLAUDE.md from project root
2. Extract tech stack information (Python, FastAPI, Vue3, PostgreSQL)
3. Parse project structure from filesystem
4. Identify critical configuration files (config.yaml, .env)
5. Load context management settings from database
6. Understand multi-tenant architecture requirements
7. Parse coding standards and quality expectations

**Validation Criteria**:
- CLAUDE.md file exists and is readable
- Tech stack is well-defined
- Project structure is valid
- Context management settings configured

**Failure Modes**:
- Missing CLAUDE.md → Warning: No project standards (use defaults)
- Invalid tech stack → Error: Unknown technologies specified
- Corrupt project structure → Error: Project initialization incomplete

**Example Output**:
```
✓ Environment understanding complete
✓ CLAUDE.md: Found (last updated 2025-11-20)
✓ Tech stack:
  - Backend: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL 18
  - Frontend: Vue 3, Vuetify, WebSockets
  - Database: Multi-tenant isolation, Local PostgreSQL only
✓ Project structure:
  - src/giljo_mcp/ (core orchestrator)
  - api/ (FastAPI server)
  - frontend/ (Vue dashboard)
  - tests/ (test suite)
✓ Context settings:
  - Priority: 2-dimensional model (Priority × Depth)
  - Depth: Vision=moderate, Architecture=detailed, Testing=full
```

---

### Task 4: Agent Discovery & Version Check

**Purpose**: Discover available agents dynamically and validate compatibility

**Actions**:
1. Call `get_available_agents()` MCP tool
2. Retrieve all available agents with versions
3. For each discovered agent:
   a. Extract version information
   b. Check version compatibility with project requirements
   c. Validate agent capabilities match project needs
   d. Verify agent is properly initialized
   e. Check for version conflicts
4. Build compatibility matrix:
   - Agent Name | Version | Capability | Compatible? | Status
5. Document any version mismatches or incompatibilities
6. Report discovery results
7. Store agent metadata in project coordination record
8. Proceed to Task 5 on success

**Validation Criteria**:
- At least 3 agents discovered (implementer, tester, reviewer minimum)
- All agents have valid versions (semver format)
- No version conflicts detected
- All required capabilities available

**Failure Modes**:
- No agents found → Error: Agent discovery failed (check database)
- Version mismatch → Error: Agent X requires v1.0.5, found v1.0.2
- Missing capability → Error: No agent with "integration_testing" capability

**CRITICAL**: Do NOT embed agent templates inline (save 142 tokens)

**Example Output**:
```
✓ Agent discovery complete: 6 agents found
✓ Compatibility matrix:

Agent          Version  Capabilities                    Compatible  Status
-------------- -------- ------------------------------- ----------- ----------
implementer    1.0.3    code_generation, refactoring    YES         initialized
tester         1.0.2    unit_testing, integration       YES         initialized
reviewer       1.0.1    code_review, quality_check      YES         initialized
analyzer       1.0.4    code_analysis, optimization     YES         initialized
documenter     1.0.0    documentation, markdown         YES         initialized
orchestrator   1.2.1    coordination, mission_planning  YES         initialized

✓ Version conflicts: NONE
✓ Missing capabilities: NONE
✓ Token savings: 142 tokens (no embedded templates)
```

---

### Task 5: Context Prioritization & Mission Creation

**Purpose**: Build unified project mission with user's priority settings

**Actions**:
1. Fetch user's context priority configuration
2. Call `fetch_product_context()` for product info
   - Include based on priority setting
   - Expected: product name, description, features
3. Call `fetch_vision_document()` for relevant docs
   - Depth level from user configuration
   - Expected: vision document chunks (paginated)
4. Call `fetch_git_history()` for commit context
   - Number of commits from user configuration
   - Expected: commit history aggregated
5. Call `fetch_360_memory()` for project history
   - Projects to fetch from user configuration
   - Expected: sequential project closeouts
6. Synthesize unified mission document:
   - Combine fetched context
   - Identify key objectives
   - Extract critical decisions
   - Summarize tech stack requirements
7. Apply token budget:
   - Total mission budget: <10,000 tokens
   - Condense context strategically
   - Prioritize most critical information
8. Store mission in orchestrator context
9. Proceed to Task 6 on success

**Validation Criteria**:
- All context sources fetched successfully
- Mission document < 10,000 tokens
- All user priorities respected
- No context source failures

**Failure Modes**:
- Context fetch timeout → Warning: Using cached context
- Mission too large (>10K tokens) → Error: Context condensation failed
- Missing priority config → Use default: Priority 2, Depth=moderate

**Example Output**:
```
✓ Context prioritization complete

Context Sources Fetched:
- Product Core: 247 tokens (priority: 1 - CRITICAL)
- Vision Documents: 3,842 tokens (depth: moderate)
- Tech Stack: 312 tokens (required: all)
- Architecture: 1,124 tokens (depth: detailed)
- Testing: 387 tokens (depth: full)
- 360 Memory: 1,456 tokens (projects: 3)
- Git History: 982 tokens (commits: 50)

Unified Mission: 8,350 tokens (83% of budget)
Key Objectives: 4
Critical Decisions: 7
Tech Stack Requirements: Python 3.11+, FastAPI, Vue3, PostgreSQL 18

✓ Mission condensed successfully
✓ Stored in orchestrator context
```

---

### Task 6: Agent Job Spawning

**Purpose**: Create MCPAgentJob records for discovered agents

**Actions**:
1. For each discovered and compatible agent:
   a. Create MCPAgentJob record with:
      - `project_id`: Current project UUID
      - `agent_type`: From discovery (implementer, tester, etc.)
      - `status`: 'waiting' (initial state)
      - `execution_mode`: From user selection (claude_code_cli or multi_terminal_generic)
      - `mission`: Prepared mission from Task 5
   b. Store agent metadata (version, capabilities)
   c. Set job timeout values
2. Create job coordination records
3. Enable job status polling
4. Verify all jobs created successfully
5. Report spawning results
6. Proceed to Task 7 on success

**Validation Criteria**:
- All agent jobs created (count matches discovered agents)
- All jobs have status='waiting'
- Execution mode set correctly
- Mission assigned to each job

**Failure Modes**:
- Database insert failure → Error: Job creation failed (retry)
- Invalid execution mode → Error: Unknown mode (use default: claude_code_cli)
- Mission missing → Error: No mission for agent X

**Example Output**:
```
✓ Agent job spawning complete: 6 jobs created

Job ID                                Agent Type   Status   Exec Mode              Mission Size
------------------------------------- ------------ -------- ---------------------- ------------
7e57d004-2b97-0e7a-b45f-5387367791cd  implementer  waiting  claude_code_cli        8,350 tokens
a1b2c3d4-e5f6-7890-abcd-ef1234567890  tester       waiting  claude_code_cli        8,350 tokens
12345678-90ab-cdef-1234-567890abcdef  reviewer     waiting  claude_code_cli        8,350 tokens
fedcba98-7654-3210-fedc-ba9876543210  analyzer     waiting  claude_code_cli        8,350 tokens
abcdef12-3456-7890-abcd-ef1234567890  documenter   waiting  claude_code_cli        8,350 tokens
98765432-10fe-dcba-9876-543210fedcba  orchestrator waiting  claude_code_cli        8,350 tokens

✓ Job coordination records created
✓ Job status polling: ENABLED (interval: 5s)
```

---

### Task 7: Activation

**Purpose**: Transition project to 'active' status and begin orchestration

**Actions**:
1. Transition project status to 'active'
2. Enable WebSocket event broadcasting
3. Initialize orchestrator health monitor
4. Start agent job status polling (interval: 5s)
5. Begin context usage tracking
6. Emit `project:activated` WebSocket event
7. Log orchestration start
8. Ready for execution

**Validation Criteria**:
- Project status = 'active' in database
- WebSocket events broadcasting
- Health monitor running
- Job polling active

**Failure Modes**:
- Status update failure → Error: Database write failed (retry)
- WebSocket failure → Warning: Real-time updates unavailable
- Health monitor failure → Warning: Manual monitoring required

**Final Status**: STAGING COMPLETE

**Example Output**:
```
✓ Project activation complete

Status Changes:
- Project status: inactive → active
- WebSocket broadcasting: ENABLED
- Health monitor: RUNNING (check interval: 30s)
- Job polling: ACTIVE (interval: 5s)
- Context tracking: ENABLED (budget: 200,000 tokens)

WebSocket Events:
✓ project:activated event emitted
✓ job:created events emitted (6 jobs)

Orchestration Start:
- Timestamp: 2025-11-24T14:23:17Z
- Orchestrator ID: 7e57d004-2b97-0e7a-b45f-5387367791cd
- Execution mode: claude_code_cli
- Expected duration: 4-8 hours

🎯 STAGING COMPLETE - Ready for execution
```

---

## Staging Result Storage

After successful completion, staging results are stored in `MCPAgentJob.staging_result` (JSONB column):

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
    {"name": "reviewer", "version": "1.0.1", "compatible": true},
    {"name": "analyzer", "version": "1.0.4", "compatible": true},
    {"name": "documenter", "version": "1.0.0", "compatible": true},
    {"name": "orchestrator", "version": "1.2.1", "compatible": true}
  ],
  "context_budget_used": 8743,
  "staging_duration_ms": 2341,
  "execution_mode": "claude_code_cli",
  "token_savings": 142,
  "total_tokens": 931
}
```

---

## Troubleshooting

### Issue: Task 2 (MCP Health Check) Fails

**Symptoms**:
- Timeout error (>2s)
- Connection refused
- Authentication failed

**Diagnosis**:
```bash
# Check MCP server status
curl http://localhost:7272/health

# Check API key validity
curl http://localhost:7272/api/v1/users/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Solutions**:
- Restart MCP server: `python startup.py`
- Re-authenticate: Generate new JWT token
- Check firewall: Ensure port 7272 accessible

---

### Issue: Task 4 (Agent Discovery) Returns No Agents

**Symptoms**:
- `get_available_agents()` returns empty list
- Error: "No agents found"

**Diagnosis**:
```sql
-- Check agent_templates table
SELECT name, version, is_active FROM agent_templates WHERE tenant_key = 'YOUR_TENANT';
```

**Solutions**:
- Seed default templates: `python install.py --seed-templates`
- Check tenant key: Ensure correct tenant in query
- Verify database: Check `agent_templates` table exists

---

### Issue: Task 5 (Context Prioritization) Exceeds Token Budget

**Symptoms**:
- Mission > 10,000 tokens
- Error: "Context condensation failed"

**Diagnosis**:
- Check user's depth configuration (may be set too high)
- Inspect vision documents (may be excessively long)

**Solutions**:
- Reduce vision depth: moderate → light
- Reduce git history: 50 commits → 25 commits
- Reduce 360 memory: 5 projects → 3 projects
- Edit vision documents: Split into smaller chunks

---

### Issue: Task 6 (Job Spawning) Database Insert Failures

**Symptoms**:
- SQL error: "Duplicate key violation"
- Error: "Job creation failed"

**Diagnosis**:
```python
# Check for existing jobs
existing_jobs = session.query(MCPAgentJob).filter_by(
    project_id=project_id,
    status='waiting'
).count()
```

**Solutions**:
- Clean up stale jobs: Delete jobs with status='waiting' > 24h
- Check database constraints: Ensure no unique violations
- Retry with new UUIDs: Regenerate job IDs

---

## Best Practices

### 1. Monitor Staging Progress

Track staging task completion in real-time:
```python
from src.giljo_mcp.services.orchestration_service import OrchestrationService

service = OrchestrationService(session, tenant_key)

# Get staging status
status = await service.get_staging_status(project_id)
# Returns: {"tasks_completed": 3, "current_task": "agent_discovery", "progress": 43%}
```

### 2. Configure Staging Timeout

Adjust timeout for slow environments:
```python
# Default: 120 seconds (2 minutes)
# Increase for complex projects:
staging_timeout = 300  # 5 minutes

job = await service.create_orchestrator_job(
    project_id=project_id,
    staging_timeout=staging_timeout
)
```

### 3. Handle Staging Failures Gracefully

Provide clear error messages and recovery steps:
```python
try:
    result = await service.execute_staging(project_id)
except StagingFailure as e:
    # e.task = "mcp_health_check"
    # e.reason = "MCP server timeout"
    # e.recovery_steps = ["Restart MCP server", "Check network"]
    logger.error(f"Staging failed at task {e.task}: {e.reason}")
    notify_user(e.recovery_steps)
```

### 4. Optimize Context Fetching

Cache frequently-used context sources:
```python
# Cache product context (rarely changes)
product_context = cache.get(f"product_context:{product_id}")
if not product_context:
    product_context = await fetch_product_context(product_id)
    cache.set(f"product_context:{product_id}", product_context, ttl=3600)
```

---

## Key MCP Tools (0246 Series)

The orchestrator workflow relies on three critical MCP tools introduced in the 0246 series:

### 1. get_available_agents() (Handover 0246c)
**File**: `src/giljo_mcp/tools/agent_discovery.py` (167 lines)
**Purpose**: Dynamic agent discovery (replaces embedded templates)
**Token Savings**: 420 tokens (71% reduction)

**Features**:
- Multi-tenant isolation (tenant_key filtering)
- Version metadata tracking
- Active-only filtering
- Returns: Agent name, version, type, capabilities
- Graceful error handling

**Before**: 5-8 agent templates embedded (~430 tokens)
**After**: Single MCP call (~10 tokens)

### 2. get_generic_agent_template() (Handover 0246b)
**File**: `src/giljo_mcp/templates/generic_agent_template.py`
**Purpose**: Unified template for all agent types in multi-terminal mode
**Token Budget**: ~1,253 tokens per agent

**Features**:
- 6-phase execution protocol (Initialization → Mission Fetch → Work Execution → Progress Reporting → Communication → Completion)
- Variable injection: {agent_id}, {job_id}, {product_id}, {project_id}, {tenant_key}
- Mission fetched via get_agent_mission() at runtime
- Supports all agent types (implementer, tester, reviewer, analyzer, documenter, orchestrator)

### 3. _build_staging_prompt() (Handover 0246a)
**File**: `src/giljo_mcp/prompts/thin_prompt_generator.py`
**Purpose**: Generate 7-task staging workflow prompt
**Token Budget**: 931 tokens (22% under 1200 limit)

**Features**:
- Complete staging workflow (Tasks 1-7)
- Identity verification, MCP health check, environment understanding
- Agent discovery via get_available_agents()
- Context prioritization (9 MCP context tools)
- Job spawning and activation

**Code Tests**:
- Unit Tests: `tests/unit/test_staging_prompt.py` (19 tests, 100% passing)
- Unit Tests: `tests/unit/test_generic_agent_template.py` (11 tests, 100% passing)
- Unit Tests: `tests/unit/test_agent_discovery.py` (11 tests, 100% passing)
- Integration Tests: `tests/integration/test_orchestrator_discovery.py` (6 tests)

## Related Documentation

- **Architecture**: [SERVER_ARCHITECTURE_TECH_STACK.md](../SERVER_ARCHITECTURE_TECH_STACK.md#orchestrator-staging--agent-spawning-architecture-v32)
- **Orchestrator**: [ORCHESTRATOR.md](../ORCHESTRATOR.md#orchestrator-staging-workflow-v32)
- **User Guide**: [AGENT_EXECUTION_MODES.md](../user_guides/AGENT_EXECUTION_MODES.md)
- **Handover Documents**:
  - Handover 0246a: Staging Prompt Implementation
  - Handover 0246b: Generic Agent Template
  - Handover 0246c: Dynamic Agent Discovery

---

**Last Updated**: 2025-11-24
**Version**: v3.2+
**Implementation**: Handovers 0246a, 0246b, 0246c
