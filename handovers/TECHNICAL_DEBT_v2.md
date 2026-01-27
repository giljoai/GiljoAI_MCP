# Technical Debt v2.0 - GiljoAI MCP
**Created**: 2025-10-27
**Purpose**: Updated prioritization of implementation gaps for production release
**Previous Version**: TECHNICAL_DEBT.md (2025-10-22)

---

## Executive Summary

This document reconciles the original technical debt assessment with:
- Completed projects in `handovers/completed/`
- Current codebase state (verified by exploration agents)
- Planned projects 0060-0068 for release readiness

**Key Changes from v1**:
- MCP Slash Commands (Gap 2) marked as RESOLVED (functional with different pattern)
- Dashboard Agent Monitoring (Gap 1) remains CRITICAL blocker
- **NEW: Task-Agent Integration Gap identified** - Tasks can't execute via agents
- Added release-critical items from projects 0060-0062
- Reorganized by implementation difficulty (simplest → most difficult)
- Grouped related items together

**Release Status**:
- **Backend Orchestration**: 90% complete, production-ready
- **Frontend Visibility**: 0% complete, BLOCKS release
- **Task-Agent Integration**: Missing - tasks can't execute via agents
- **Multi-Tool Support**: Configured but not integrated
- **Developer Experience**: Needs documentation

---

## Critical Release Blockers

### Priority: CRITICAL (Must Complete Before Release)

These items block core user workflows and must be implemented before v3.0 release.

---

### 🚨 BLOCKER 1: Dashboard Agent Monitoring UI
**Status**: Backend Complete (90%) | Frontend Missing (0%)
**Impact**: HIGH - Users cannot see what agents are doing
**Complexity**: MEDIUM
**Effort**: 2-3 days (16-24 hours)
**Dependencies**: None (backend exists)

#### What Exists (Backend):
- ✅ `AgentJobManager` - Full job lifecycle management
- ✅ `JobCoordinator` - Multi-agent orchestration
- ✅ `AgentCommunicationQueue` - Inter-agent messaging
- ✅ 13 REST API endpoints in `api/endpoints/agent_jobs.py`
- ✅ WebSocket events (`job:status_changed`, `job:completed`, `job:failed`)
- ✅ 90%+ test coverage (80 core + 30 API + 9 WebSocket tests)

#### What's Missing (Frontend):
- ❌ `AgentMonitor.vue` component - Main monitoring interface
- ❌ `AgentJobCard.vue` component - Individual job cards
- ❌ Real-time job status updates in UI
- ❌ Message flow visualization
- ❌ Token usage tracking display per job
- ❌ Agent control buttons (terminate, message)
- ❌ WebSocket listeners for job events
- ❌ Frontend store for agent jobs (`useAgentJobStore`)
- ❌ API service methods (`api.agentJobs.*`)

#### Current Gaps:
```
DashboardView.vue       - Shows stats only, no active jobs
AgentsView.vue          - Shows agent status, not job details
MessagesView.vue        - Orphaned messages, no job context
AgentMetrics.vue        - High-level metrics, no real-time tracking
```

#### Implementation Breakdown:
- Create Pinia store for agent jobs: 2 hours
- Add API service methods: 2 hours
- Create AgentMonitor.vue component: 4 hours
- Create AgentJobCard.vue component: 3 hours
- WebSocket integration: 2 hours
- Message-Job linking in MessagesView: 3 hours
- Testing and polish: 3 hours

**Files to Create**:
- `frontend/src/stores/useAgentJobStore.js`
- `frontend/src/components/agents/AgentMonitor.vue`
- `frontend/src/components/agents/AgentJobCard.vue`

**Files to Modify**:
- `frontend/src/services/api.js` - Add agentJobs methods
- `frontend/src/views/DashboardView.vue` - Integrate AgentMonitor
- `frontend/src/views/MessagesView.vue` - Link messages to jobs
- `frontend/src/services/websocket.js` - Add job event listeners

**Related Handover**: See `handovers/TECHNICAL_DEBT.md` Section 1

---

### 🔄 ENHANCEMENT: Dashboard Scope Selector with Per-Product/Project Views
**Status**: Not Started
**Impact**: HIGH - Better statistics visibility and context
**Complexity**: MEDIUM
**Effort**: 8-12 hours
**Dependencies**: Dashboard Agent Monitoring UI (BLOCKER 1)

#### What This Enables:
- Dropdown to select dashboard view scope:
  - **All Products & Projects** (aggregate top-level view)
  - **Per Product** (product-specific statistics)
  - **Per Project** (project-specific statistics)
- Statistics board tailored for developers
- Message history between agents displayed in dashboard context
- Merger of dashboard and message windows

#### Current State:
- Dashboard shows aggregate statistics only
- No scope filtering or context switching
- Messages in separate view with no dashboard integration

#### What This Creates:
**Unified Dashboard with Scope Selector**:
```
┌─────────────────────────────────────────────┐
│ Dashboard                    [Scope: ▼]     │
│                              ├─ All         │
│                              ├─ Product A   │
│                              ├─ Product B   │
│                              └─ Project X   │
├─────────────────────────────────────────────┤
│ Statistics (filtered by scope)              │
│ - Active Jobs: 5                            │
│ - Completed Tasks: 42                       │
│ - Token Usage: 125k                         │
├─────────────────────────────────────────────┤
│ Agent Messages (in scope)                   │
│ - [12:45] Implementer → Tester             │
│ - [12:48] Orchestrator → All               │
└─────────────────────────────────────────────┘
```

#### Implementation Breakdown:

**Phase 1: Scope Selector Component (2-3 hours)**
- Create `DashboardScopeSelector.vue` component
- Dropdown with hierarchy:
  - Top level: "All Products & Projects"
  - Second level: List of products
  - Third level: Projects within selected product
- Persist selection in localStorage
- Vuex/Pinia state management

**Phase 2: Scoped Statistics API (3-4 hours)**
- Backend endpoints:
  - `GET /api/v1/dashboard/stats` (aggregate)
  - `GET /api/v1/dashboard/stats/product/{id}` (product scope)
  - `GET /api/v1/dashboard/stats/project/{id}` (project scope)
- Statistics filtered by scope:
  - Active jobs count
  - Completed tasks count
  - Token usage aggregation
  - Agent activity metrics
  - Project/product progress

**Phase 3: Dashboard Integration (2-3 hours)**
- Update `DashboardView.vue`:
  - Add scope selector to header
  - Reload statistics on scope change
  - Show scope-specific agent jobs
  - Display relevant messages in context
- Merge message display into dashboard:
  - Agent-to-agent messages
  - Filtered by current scope
  - Expandable message panel

**Phase 4: Message Context Integration (1-2 hours)**
- Link messages to dashboard scope
- Filter message history by:
  - All (when scope = all)
  - Product ID (when product selected)
  - Project ID (when project selected)
- Real-time updates via WebSocket

#### Files to Create:
- `frontend/src/components/dashboard/DashboardScopeSelector.vue` (~150 lines)
- `api/endpoints/dashboard_stats.py` (~250 lines)

#### Files to Modify:
- `frontend/src/views/DashboardView.vue` (~100 lines added)
  - Add scope selector integration
  - Add message history panel
  - Update statistics display logic
- `frontend/src/stores/useDashboardStore.js` (~50 lines)
  - Add scope state management
  - Add scope persistence
- `frontend/src/services/api.js` (~30 lines)
  - Add scoped statistics methods

#### Context from User:
> "The dashboard needs to have a drop down to select dashboard view on a per product basis, then per project basis for statistics. Should also have a top aggregate view of all products and projects."
>
> "Its a statistics board for the developer."
>
> "More integrations to be defined in future, no need to populate with data in this specific project, leave what is there already, also message history between agents should show here. its a merger of dashboard and message windows in some capacity, to be defined more"

#### Design Considerations:
1. **Leave Existing Data**: Don't remove current dashboard stats
2. **Future Integrations**: Design for extensibility (more integrations coming)
3. **Message Merger**: Combine dashboard + messages in unified view
4. **To Be Defined**: Some aspects intentionally left open for future refinement

#### Success Criteria:
- ✅ Dropdown selector with 3 levels (all/product/project)
- ✅ Statistics filtered by selected scope
- ✅ Message history visible in dashboard context
- ✅ Existing dashboard functionality preserved
- ✅ Extensible for future integrations
- ✅ Real-time updates via WebSocket

#### Priority Justification:
**Why HIGH Priority**:
- Improves developer visibility into specific contexts
- Reduces context switching (dashboard + messages)
- Better UX for multi-product/project setups
- Foundation for future integrations

**Why Not CRITICAL**:
- Dashboard currently functional (aggregate view works)
- Can be completed after core monitoring UI (BLOCKER 1)
- Enhancement rather than blocker

**Recommended Sequence**: Implement after BLOCKER 1 (Dashboard Agent Monitoring UI) as this builds on that foundation.

---

### 🚨 BLOCKER 2: MCP Agent Coordination Tool Exposure (Handover 0060)
**Status**: Not Started
**Impact**: CRITICAL - External agents can't coordinate
**Complexity**: LOW
**Effort**: 4-6 hours
**Dependencies**: None (wraps existing APIs)

#### What This Enables:
- Claude Code, Codex, Gemini can use agent coordination tools
- Create jobs, send messages, check status, acknowledge/complete work
- Multi-agent workflows with external tools

#### Implementation:
- Create `src/giljo_mcp/tools/agent_coordination.py` (~250 lines)
- Expose 7 MCP tools wrapping REST API endpoints
- Register tools in `src/giljo_mcp/tools/__init__.py`
- Add tests

**Related Handover**: `handovers/0060_mcp_agent_coordination_tool_exposure.md`

---

### 🚨 BLOCKER 3: Orchestrator Launch UI Workflow (Handover 0061)
**Status**: Not Started
**Impact**: CRITICAL - No UI to launch orchestrator
**Complexity**: MEDIUM
**Effort**: 6-8 hours
**Dependencies**: Handover 0060 (MCP tools)

#### What This Enables:
- "Launch Orchestrator" button in ProductsView
- Real-time progress tracking with WebSocket updates
- Preview mode before execution
- Error feedback and status tracking

#### Implementation:
- Backend: `api/endpoints/orchestrator.py` (~200 lines)
  - Launch endpoint with preview mode
  - WebSocket progress updates
- Frontend: `OrchestratorLaunchButton.vue` (~180 lines)
  - Launch button component
  - Progress dialog with timeline
  - WebSocket integration
- Integration with ProductsView

**Related Handover**: `handovers/0061_orchestrator_launch_ui_workflow.md`

---

### ENHANCEMENT: Orchestrator Message Loop Automation (Toggleable)
**Status**: Manual available (tools added); automation not wired
**Impact**: MEDIUM-HIGH – Smoother runs, fewer manual steps
**Complexity**: LOW-MEDIUM (bounded polling in background task)
**Effort**: 3–5 hours
**Dependencies**: Messaging infra complete (`AgentCommunicationQueue`, MCP tools)

#### Current State
- Orchestrator can send welcome/status and poll/handle messages using MCP tools:
  - `orchestrate_project()` auto-sends a welcome after spawn
  - Manual helpers: `send_welcome`, `broadcast_status`, `coordinate_messages(iterations, interval)`
- Polling is manual/on‑demand to aid debugging.

#### Problem
- Developers must remember to trigger `coordinate_messages` during execution to process progress/errors in real time.

#### Proposed Improvement
- Add an automation toggle to run the message loop automatically during the workflow window:
  - Option A (default off): Background polling when orchestrator starts; respects project lifecycle.
  - Option B: Keep manual default; add a “Run message coordination automatically” toggle when starting an orchestrator.

#### Implementation Outline
- Add config/flag: `auto_message_coordination: bool` (CLI param and server config)
- If enabled: start a background task that calls `poll_and_handle_messages(project_id, iterations=∞, interval=3s)` until completion.
- Surface toggle in UI when launching orchestrator; persist per run.

#### Success Criteria
- Toggle present in UI and/or CLI; default = manual (current behavior).
- When enabled, messages (progress/errors) get acknowledged and basic replies are sent automatically.
- No impact on SQLAlchemy 2.0 compliance or DB schema.

#### Notes
- Keep automation conservative; avoid spamming status messages (rate-limit broadcasts).
- Log actions for traceability; allow turning off mid-run.

---

### 🚨 BLOCKER 4: Enhanced Agent Cards with Project Context (Handover 0062)
**Status**: Not Started
**Impact**: CRITICAL - Can't see what agents are working on
**Complexity**: MEDIUM
**Effort**: 8-10 hours
**Dependencies**: Handover 0060 (MCP tools)

#### What This Enables:
- Agent cards show project-specific jobs
- Copyable project instructions for manual coordination
- Real-time job status updates
- Agent workload visibility

#### Implementation:
- Backend: Add 2 new endpoints
  - `GET /agent-jobs/by-agent-and-project` (~60 lines)
  - `GET /projects/{id}/instructions` (~80 lines)
- Frontend: Enhance `EnhancedAgentCard.vue` (~250 lines)
  - Project jobs section with expandable jobs
  - Copy instructions button
  - WebSocket integration
- API service integration

**Related Handover**: `handovers/0062_enhanced_agent_cards_project_context.md`

---

## High-Priority Release Enhancements

### Priority: HIGH (Significantly Improves UX)

These items greatly improve usability and should be completed before release if time permits.

---

### ⭐ HIGH-0: Task-Agent Integration & Orchestration (NEW - Critical Gap Identified)
**Status**: Not Started
**Impact**: HIGH - Can't execute tasks via agents directly
**Complexity**: MEDIUM
**Effort**: 12-16 hours
**Dependencies**: Handover 0060 (MCP tools), Agent Job system

**Grouped with**: Core orchestration workflows

#### Problem Statement

**What Exists**:
- ✅ 10 MCP tools for task CRUD operations (`create_task`, `list_tasks`, `update_task`, etc.)
- ✅ Task-to-project conversion with 3 strategies
- ✅ Project orchestration workflow (vision → agents → jobs)
- ✅ Agent job management system (complete backend)

**Critical Gap**:
- ❌ No foreign key relationship between Task and MCPAgentJob
- ❌ No automatic agent job spawning when task assigned to agent
- ❌ No task-driven orchestration (can't orchestrate from task list)
- ❌ No status synchronization (job completes, task stays "in_progress")
- ❌ No slash commands for task execution workflows

**Current Broken Workflow**:
```
User: create_task("Build API endpoint") → Task created in database
User: update_task(assigned_agent_id="backend-dev") → Agent assigned
                            ↓
                    [GAP - NO CONNECTION]
                            ↓
User: Must manually spawn agent job ← No automatic execution
User: Job completes successfully
                            ↓
Task status="in_progress" forever ← No auto-sync (state divergence)
```

#### What This Enables

**Direct Task Execution**:
```python
# NEW: Execute task with single command
result = await execute_task_with_agent(
    task_id="task-123",
    agent_id="backend-dev",
    tenant_key="tenant-1"
)
# → Automatically spawns job, links task↔job, returns job_id
```

**Task-Driven Orchestration**:
```python
# NEW: Orchestrate from task list
result = await orchestrate_from_product_tasks(
    product_id="prod-456",
    task_filter={"status": "pending", "priority": "high"},
    tenant_key="tenant-1"
)
# → Loads tasks, selects agents, spawns coordinated jobs
```

**Automatic Status Sync**:
```python
# NEW: Background job syncs task status
await sync_task_from_job(task_id="task-123")
# → Checks linked job, updates task status (completed/failed/blocked)
```

#### Implementation Breakdown

**Phase 1: Database Schema (2 hours)**

Add foreign key to Task model:

```python
# src/giljo_mcp/models.py - Task model
agent_job_id = Column(String(36), ForeignKey("mcp_agent_jobs.job_id"), nullable=True)
agent_job = relationship("MCPAgentJob", backref="task", foreign_keys=[agent_job_id])
```

Create migration:
```bash
# Database migration
alembic revision --autogenerate -m "add_task_agent_job_relationship"
alembic upgrade head
```

**Phase 2: Task Execution MCP Tool (3-4 hours)**

Create `src/giljo_mcp/tools/task_execution.py`:

```python
@mcp.tool()
async def execute_task_with_agent(
    task_id: str,
    agent_id: str,
    tenant_key: str,
    auto_start: bool = True
) -> dict:
    """
    Assign task to agent and spawn agent job automatically.

    Workflow:
    1. Validate task exists and belongs to tenant
    2. Validate agent exists and is available
    3. Update task.assigned_agent_id
    4. Create MCPAgentJob with task context
    5. Link task.agent_job_id → job.job_id
    6. Set task.status = "in_progress"
    7. Optionally start job immediately

    Returns:
        {
            "success": True,
            "task_id": "task-123",
            "agent_job_id": "job-456",
            "agent_id": "agent-789",
            "status": "in_progress",
            "auto_started": True
        }
    """
    # Implementation loads task, spawns job, links them
```

**Phase 3: Task-Driven Orchestration (4-5 hours)**

Create `src/giljo_mcp/tools/task_orchestration.py`:

```python
@mcp.tool()
async def orchestrate_from_product_tasks(
    product_id: str,
    task_filter: Optional[dict] = None,
    workflow_type: str = "waterfall",
    tenant_key: str = None
) -> dict:
    """
    Orchestrate agent execution based on product tasks.

    Workflow:
    1. Load tasks matching filter (status, priority, category)
    2. Analyze task requirements and dependencies
    3. Select appropriate agents for each task type
    4. Create coordinated mission plan
    5. Spawn agent jobs with proper sequencing
    6. Link tasks to jobs
    7. Return orchestration summary

    Args:
        product_id: Product UUID
        task_filter: {"status": "pending", "priority": "high"}
        workflow_type: "waterfall" or "parallel"
        tenant_key: Tenant isolation key

    Returns:
        {
            "success": True,
            "product_id": "prod-123",
            "tasks_orchestrated": 5,
            "agents_assigned": ["backend-dev", "test-engineer"],
            "jobs_spawned": ["job-1", "job-2", "job-3"],
            "workflow_type": "waterfall",
            "task_job_mappings": [
                {"task_id": "task-1", "job_id": "job-1"},
                {"task_id": "task-2", "job_id": "job-2"}
            ]
        }
    """
    # Implementation orchestrates task execution
```

**Phase 4: Status Synchronization (2-3 hours)**

Create background sync mechanism:

```python
@mcp.tool()
async def sync_task_from_job(
    task_id: str,
    tenant_key: str
) -> dict:
    """
    Synchronize task status from linked agent job.

    Status mapping:
    - job.completed → task.completed (with completion timestamp)
    - job.failed → task.blocked (with error details)
    - job.in_progress → task.in_progress
    - job.acknowledged → task.in_progress

    Returns:
        {
            "success": True,
            "task_id": "task-123",
            "previous_status": "in_progress",
            "new_status": "completed",
            "job_id": "job-456",
            "job_status": "completed",
            "synced_at": "2025-10-27T12:34:56Z"
        }
    """
```

Create scheduled background job (runs every 2 minutes):

```python
# src/giljo_mcp/background_jobs/task_sync.py
async def sync_all_active_tasks():
    """
    Background job that syncs all in-progress tasks with their jobs.
    Runs every 2 minutes via scheduler.
    """
    # Query all tasks with status="in_progress" and agent_job_id not null
    # Check each linked job status
    # Update task status if job completed/failed
```

**Phase 5: API Integration (2 hours)**

Add REST endpoints:

```python
# api/endpoints/task_execution.py

@router.post("/tasks/{task_id}/execute")
async def execute_task(
    task_id: str,
    agent_id: str,
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user)
):
    """Execute task with assigned agent"""

@router.post("/products/{product_id}/orchestrate-tasks")
async def orchestrate_product_tasks(
    product_id: str,
    task_filter: dict,
    tenant_key: str = Depends(get_tenant_key)
):
    """Orchestrate tasks for product"""

@router.post("/tasks/{task_id}/sync")
async def sync_task_status(task_id: str):
    """Manually trigger task-job status sync"""
```

**Phase 6: Testing (2 hours)**

Create comprehensive tests:
- Unit tests for task-job linking
- Integration tests for orchestration flow
- Status sync tests (various job states)
- Multi-tenant isolation tests
- Error handling tests

#### Files to Create

**New Files**:
1. `src/giljo_mcp/tools/task_execution.py` (~200 lines)
   - `execute_task_with_agent()` tool

2. `src/giljo_mcp/tools/task_orchestration.py` (~300 lines)
   - `orchestrate_from_product_tasks()` tool
   - Task analysis and agent selection logic

3. `src/giljo_mcp/background_jobs/task_sync.py` (~150 lines)
   - Background synchronization job
   - Scheduled via APScheduler

4. `api/endpoints/task_execution.py` (~180 lines)
   - REST API for task execution
   - 3 endpoints

5. `migrations/versions/add_task_agent_job_fk.py` (~40 lines)
   - Database migration

6. `tests/tools/test_task_execution.py` (~200 lines)
   - Comprehensive test suite

**Modified Files**:
1. `src/giljo_mcp/models.py` (+3 lines)
   - Add agent_job_id foreign key to Task

2. `src/giljo_mcp/tools/__init__.py` (+5 lines)
   - Register new tools

3. `api/app.py` (+2 lines)
   - Register task_execution router

4. `src/giljo_mcp/tools/task.py` (+20 lines)
   - Add helper methods for job linking

**Total**: ~1070 lines across 10 files (6 new, 4 modified)

#### Success Criteria

**Functional Requirements**:
- Task-to-job foreign key relationship enforced
- Automatic job spawning when task assigned to agent
- Task-driven orchestration from product task list
- Automatic status sync every 2 minutes
- Manual sync available via API
- Multi-tenant isolation maintained
- Task dependencies respected in orchestration

**Integration Requirements**:
- Compatible with existing agent job system
- Works with all 3 task-to-project conversion strategies
- Supports both waterfall and parallel workflows
- Integrates with Dashboard Agent Monitoring (BLOCKER 1)

**User Experience Requirements**:
- Single command executes task via agent
- Task status updates automatically (no manual sync needed)
- Clear error messages when validation fails
- Task cards show linked agent job ID
- Job cards show originating task ID

#### Related Handovers

- **Agent Job Management (Handover 0019)**: Existing job infrastructure
- **MCP Agent Coordination (Handover 0060)**: Tool exposure for agents
- **Dashboard Agent Monitoring (Gap 1)**: Will display task-job relationships
- **Task Management Tools**: Existing tools in `src/giljo_mcp/tools/task.py`

#### Migration Strategy

**Phase 1 - Database Migration** (No downtime):
1. Add nullable `agent_job_id` column to tasks table
2. Existing tasks continue working (column is null)
3. New task execution flow populates column

**Phase 2 - Gradual Rollout**:
1. Deploy new MCP tools
2. Update documentation
3. Existing workflows unaffected
4. New workflows available immediately

**Phase 3 - Background Sync Activation**:
1. Enable scheduled job (2-minute interval)
2. Monitor logs for sync operations
3. Adjust interval if needed

#### Risk Assessment

**Complexity**: MEDIUM
- Database migration straightforward
- MCP tools wrap existing functionality
- Background job is independent service

**Risk**: LOW
- Additive changes only (no breaking changes)
- Existing workflows continue working
- New column is nullable (backward compatible)
- Background sync can be disabled if issues arise

**Performance Impact**: MINIMAL
- Background sync queries only in-progress tasks (small subset)
- Job spawning reuses existing infrastructure
- No new database indexes needed initially

#### Effort Estimate

- Database migration: 2 hours
- Task execution tool: 3-4 hours
- Task orchestration tool: 4-5 hours
- Status sync background job: 2-3 hours
- API endpoints: 2 hours
- Testing: 2 hours

**Total**: 12-16 hours for experienced developer

#### Priority Justification

**Why HIGH Priority**:
1. **User Expectation**: Users expect tasks to execute via agents
2. **Workflow Completion**: Closes the gap between task management and orchestration
3. **State Consistency**: Prevents task/job status divergence
4. **UX Impact**: Makes task system feel "complete" and integrated
5. **Enables Dashboard**: Task-job relationships needed for monitoring UI

**Why Not CRITICAL**:
- Users can work around this using project orchestration
- Task-to-project conversion provides alternative workflow
- Not blocking core orchestration functionality
- Can be completed after dashboard monitoring UI

---

### ⭐ HIGH-1: Per-Agent Tool Selection UI (Handover 0063)
**Status**: Not Started
**Impact**: HIGH - Can't assign tools to agents
**Complexity**: LOW
**Effort**: 6-8 hours
**Dependencies**: Handover 0027 (Integrations tab exists)

**Grouped with**: Multi-tool support features

#### What This Enables:
- Dropdown to select Claude/Codex/Gemini for each agent
- Validation against configured tools
- Tool badges on agent cards

#### Implementation:
- Backend: Modify agent endpoints (~120 lines)
  - Add `tool_config` to Agent model (uses existing metadata JSON)
  - Add `GET /agents/available-tools` endpoint
  - Validation helper
- Frontend: New `AgentToolSelector.vue` component (~100 lines)
  - Tool dropdown with icons
  - Configuration notice
- Integration with AgentFormDialog and EnhancedAgentCard

**Related Handover**: `handovers/0063_per_agent_tool_selection_ui.md`

---

### ⭐ HIGH-2: Project-Product Association UI (Handover 0064)
**Status**: Not Started
**Impact**: HIGH - Confusing project creation
**Complexity**: LOW
**Effort**: 3-4 hours
**Dependencies**: None

**Grouped with**: UI/UX improvements

#### What This Enables:
- Product selector dropdown in project creation
- Clear product-project relationship
- Validation (can't create under inactive product)

#### Implementation:
- Backend: Enhance validation (~40 lines)
  - Require product_id
  - Add product active warning
- Frontend: Update `ProjectFormDialog.vue` (~80 lines)
  - Add product selector
  - Show active/inactive status
  - Warning for inactive products
- Display product in ProjectsView

**Related Handover**: `handovers/0064_project_product_association_ui.md`

---

### ⭐ HIGH-3: Mission Launch Summary Component (Handover 0065)
**Status**: Not Started
**Impact**: HIGH - No preview before launch
**Complexity**: MEDIUM
**Effort**: 6-8 hours
**Dependencies**: Handover 0061 (Launch workflow)

**Grouped with**: Orchestrator UI workflows

#### What This Enables:
- Preview mission plan before execution
- Token budget visualization
- Agent assignments review
- Workflow structure timeline
- Cancel option before launch

#### Implementation:
- Backend: Add preview mode to orchestrator endpoint (~80 lines)
  - `preview_only` parameter
  - Token estimate calculation
- Frontend: New `MissionLaunchSummaryDialog.vue` (~300 lines)
  - Mission list display
  - Agent assignments
  - Token budget progress bar
  - Workflow timeline
- Integration with OrchestratorLaunchButton (preview-then-execute flow)

**Related Handover**: `handovers/0065_mission_launch_summary_component.md`

---

## Medium-Priority Post-Release Work

### Priority: MEDIUM (Adds Value, Not Critical)

These items add significant value but can be completed after initial release.

---

### 🤖 MEDIUM-0: Local LLM Stack Recommendation System
**Status**: Not Started
**Impact**: MEDIUM-HIGH - Improves UX, privacy-preserving, reduces API costs
**Complexity**: MEDIUM
**Effort**: 16-20 hours
**Dependencies**: LM Studio installed (optional), Product vision upload system

**Grouped with**: AI-powered UX improvements

#### What This Enables

**Privacy-Preserving Tech Stack Recommendations**:
- "Recommend Configuration" button in product creation/edit flow
- Local micro LLM (DeepSeek Coder 1.3B recommended) analyzes uploaded vision documents
- Proposes appropriate tech stacks based on product requirements
- Auto-fills fields: frontend_stack, backend_stack, database_type, testing_framework
- User reviews and edits suggestions (not autonomous)
- Zero API costs for this feature
- Vision docs never leave local machine

#### Problem Statement

**Current User Pain**:
- Users face blank fields when creating products
- No guidance on appropriate tech stack choices
- Vision documents uploaded but not leveraged for initial setup
- Friction at product creation (requires tech expertise)

**Proposed Solution**:
- Analyze uploaded vision document chunks with local LLM
- Generate structured recommendations from vision content
- Auto-populate stack fields with sensible defaults
- Graceful fallback if LM Studio not running

#### Use Case Example

```
User uploads vision: "Real-time dashboard for IoT metrics,
                      needs WebSocket support, time-series data"

LM Studio (DeepSeek Coder 1.3B) analyzes chunks:
↓
Recommendations:
  Frontend:  Vue 3 + Vuetify (component library for dashboards)
  Backend:   Python FastAPI (async support for real-time WebSocket)
  Database:  PostgreSQL + TimescaleDB (time-series optimized)
  Testing:   pytest + Vitest
  Reasoning: Real-time requirements suggest WebSocket stack,
             TimescaleDB for efficient metric storage
↓
User reviews, accepts or modifies suggestions
```

#### Implementation Breakdown

**Phase 1: Backend Stack Recommender (4-5 hours)**

Create `src/giljo_mcp/stack_recommender.py`:

```python
class StackRecommender:
    """Uses local LM Studio to recommend tech stack from vision docs"""

    async def recommend_stack(
        vision_chunks: List[str],
        product_name: str,
        tenant_id: int
    ) -> Dict[str, str]:
        """
        Returns:
            {
                'frontend_stack': 'Vue 3 + Vuetify',
                'backend_stack': 'Python FastAPI',
                'database_type': 'PostgreSQL',
                'testing_framework': 'pytest + Vitest',
                'reasoning': 'Based on real-time requirements...'
            }
        """
```

**Key Features**:
- LM Studio HTTP client (OpenAI-compatible API)
- Smart chunk selection (prioritize stack-related keywords)
- Context window management (2K token limit for micro LLMs)
- Structured output parsing with validation
- Fuzzy matching to canonical stack options

**Phase 2: API Endpoint (2-3 hours)**

Create `api/endpoints/stack_recommendation.py`:

```python
@router.post("/products/{product_id}/recommend-stack")
async def recommend_tech_stack(product_id: int):
    """
    Generate stack recommendations from vision documents.

    Workflow:
    1. Load product + vision chunks
    2. Check LM Studio availability (fast health check)
    3. Call StackRecommender with relevant chunks
    4. Validate and sanitize output
    5. Return recommendations + fallback on error
    """
```

**Error Handling**:
- Health check before attempting (2s timeout)
- Graceful fallback if LM Studio not running
- Validation of LLM output (no hallucinated frameworks)
- Timeout protection (45s hard cutoff)

**Phase 3: Frontend Component (3-4 hours)**

Create `frontend/src/components/products/StackRecommendationButton.vue`:

**Features**:
- "Recommend Configuration" button with loading state
- Elapsed time indicator during CPU inference (30-60s typical)
- Auto-fill form fields with recommendations
- Display AI reasoning below fields
- Warning if vision docs not uploaded yet
- Fallback message if LM Studio unavailable

**Phase 4: Configuration & Integration (2-3 hours)**

**config.yaml**:
```yaml
lmstudio:
  enabled: true  # User toggles in Admin Settings
  base_url: "http://localhost:1234/v1"
  model: "deepseek-coder-1.3b"  # User-selected model
  timeout: 45
  fallback_to_defaults: true
```

**Admin Settings → Integrations Tab**:
- Toggle LM Studio integration
- Model selection dropdown
- Test connection button
- Installation instructions link

**Phase 5: Testing & Polish (2-3 hours)**

**Unit Tests**:
- Stack recommender prompt generation
- Chunk selection logic (keyword scoring)
- Output parsing and validation
- Fuzzy matching for framework names

**Integration Tests**:
- Full workflow (vision → recommendation → form fill)
- LM Studio unavailable scenario
- Timeout handling
- Multi-tenant isolation

**Phase 6: Documentation (2 hours)**

**User Guide** (`docs/user_guides/stack_recommendation_guide.md`):
- How to install LM Studio
- Recommended models (DeepSeek Coder 1.3B, StarCoder2 3B)
- Expected inference times on CPU
- Configuration steps
- Troubleshooting common issues

**Developer Guide**:
- Adding new stack options
- Customizing prompts
- Model selection criteria

#### Recommended Model: DeepSeek Coder 1.3B

**Why This Model**:
- ✅ **Code-Specialized**: Trained on code + tech documentation
- ✅ **Stack Knowledge**: Understands framework ecosystems
- ✅ **CPU Speed**: 20-40 tokens/sec on typical CPUs
- ✅ **Small Footprint**: 0.9GB (Q4_K_M quantization)
- ✅ **Structured Output**: Better format adherence than general models

**Alternatives**:
- **StarCoder2 3B**: Excellent structured output (12-25 tok/s)
- **CodeLlama 7B**: Higher quality but slower (5-12 tok/s)
- **Phi-2 2.7B**: General model fallback (adequate but less stack-aware)

**Model Download** (via LM Studio UI):
```
deepseek-coder-1.3b-instruct.Q4_K_M.gguf
```

#### Risk Mitigation Strategies

**Risk 1: LM Studio Not Running** (HIGH PROBABILITY)

**Mitigation**:
```python
async def check_lmstudio_available() -> bool:
    try:
        response = await client.get(f"{base_url}/models", timeout=2.0)
        return response.status_code == 200
    except:
        return False

# Fast fail with helpful message
if not await check_lmstudio_available():
    return {
        "success": False,
        "error": "LM Studio not running",
        "instructions": "Start LM Studio: lms server start",
        "fallback_recommendations": {...}  # GiljoAI defaults
    }
```

**Risk 2: Slow CPU Inference** (HIGH PROBABILITY)

**Mitigation**:
- Loading UX with elapsed time counter
- Progress indicator: "Analyzing vision docs... (34s)"
- Set expectations: "This may take 30-60 seconds on CPU"
- Timeout after 45 seconds (hard cutoff)
- Concurrency limit: max 2 simultaneous inferences

**Risk 3: Hallucinated Output** (MEDIUM PROBABILITY)

**Mitigation**:
```python
VALID_FRONTENDS = ['Vue 3', 'React', 'Angular', 'Svelte', 'Next.js']
VALID_BACKENDS = ['Python FastAPI', 'Node.js', 'Django', 'Ruby on Rails']
VALID_DATABASES = ['PostgreSQL', 'MySQL', 'MongoDB', 'SQLite']

def fuzzy_match(value: str, valid_list: List[str]) -> str:
    """Map LLM output to canonical options"""
    # "reactjs" → "React"
    # "fastapi" → "Python FastAPI"
    # "postgres" → "PostgreSQL"
```

**Risk 4: Context Window Overflow** (MEDIUM PROBABILITY)

**Mitigation**:
- Smart chunk selection (prioritize stack-related keywords)
- Limit to ~1500 tokens (safe for 2K context window)
- Score chunks by relevance before selection
- Keywords: frontend, backend, database, api, real-time, scalability

**Risk 5: Multi-Tenant Concurrency** (LOW PROBABILITY, HIGH IMPACT)

**Mitigation**:
```python
_semaphore = Semaphore(2)  # Max 2 concurrent LLM calls

async with self._semaphore:
    # Only 2 requests execute simultaneously
    # Others queue (with timeout protection)
```

**Risk 6: Model Not Loaded** (MEDIUM PROBABILITY)

**Mitigation**:
```python
async def check_lmstudio_ready() -> tuple[bool, str]:
    models = await client.get(f"{base_url}/models")
    if not models['data']:
        return False, "No model loaded. Load a model in LM Studio first."
    return True, models['data'][0]['id']
```

#### Files to Create

**New Files**:
1. `src/giljo_mcp/stack_recommender.py` (~280 lines)
   - StackRecommender class
   - Smart chunk selection
   - Prompt generation
   - Output parsing and validation
   - Fuzzy matching logic

2. `api/endpoints/stack_recommendation.py` (~180 lines)
   - POST /products/{id}/recommend-stack endpoint
   - Health checks and error handling
   - Fallback logic

3. `frontend/src/components/products/StackRecommendationButton.vue` (~220 lines)
   - Recommendation button with loading UX
   - Form field auto-fill
   - Reasoning display
   - Error messaging

4. `tests/unit/test_stack_recommender.py` (~200 lines)
   - Prompt generation tests
   - Chunk selection tests
   - Output parsing tests
   - Validation tests

5. `tests/integration/test_stack_recommendation_api.py` (~150 lines)
   - End-to-end workflow tests
   - Error scenario tests

6. `docs/user_guides/stack_recommendation_guide.md` (~800 words)
   - Installation guide
   - Model recommendations
   - Usage tutorial

**Modified Files**:
1. `config.yaml` (+8 lines)
   - LM Studio configuration section

2. `frontend/src/views/ProductsView.vue` (~50 lines added)
   - Integrate StackRecommendationButton
   - Wire up recommendations to form

3. `api/app.py` (+2 lines)
   - Register stack_recommendation router

4. `frontend/src/components/AdminSettings.vue` (~60 lines added)
   - LM Studio integration toggle
   - Configuration UI in Integrations tab

**Total**: ~1030 lines across 10 files (6 new, 4 modified)

#### Success Criteria

**Functional Requirements**:
- ✅ Button triggers recommendation workflow
- ✅ Vision chunks analyzed by local LLM
- ✅ Structured recommendations returned
- ✅ Form fields auto-populated (user can edit)
- ✅ Graceful fallback if LM Studio unavailable
- ✅ Loading UX shows elapsed time
- ✅ Multi-tenant isolation maintained

**Performance Requirements**:
- ✅ Health check completes in <2 seconds
- ✅ Recommendation completes in <45 seconds
- ✅ Timeout protection prevents hanging
- ✅ Concurrent request limit prevents CPU overload

**UX Requirements**:
- ✅ Clear loading indicators with time estimates
- ✅ Helpful error messages with instructions
- ✅ Recommendations displayed with reasoning
- ✅ All fields remain editable after auto-fill
- ✅ Fallback recommendations always provided

**Security Requirements**:
- ✅ Vision docs stay local (no cloud upload)
- ✅ LM Studio runs on localhost only
- ✅ Tenant isolation for recommendations
- ✅ No sensitive data in prompts

#### Benefits

**Privacy**:
- Vision documents analyzed locally (no cloud API)
- No data leaves user's machine
- GDPR/compliance-friendly

**Cost**:
- Zero API costs for this feature
- One-time setup (LM Studio + model download)
- Unlimited recommendations at no cost

**User Experience**:
- Reduces friction at product creation
- Helps non-technical users choose appropriate stacks
- Learns from their own vision documents
- Provides educational reasoning for choices

**Quality**:
- DeepSeek Coder understands tech stacks better than general models
- Context-aware recommendations (real-time → WebSocket, etc.)
- Structured output more reliable than general LLMs

**Flexibility**:
- Works offline (no internet required after setup)
- User can swap models (StarCoder, CodeLlama, etc.)
- Recommendations editable (not autonomous)
- Optional feature (graceful degradation)

#### Effort Estimate

| Phase | Task | Effort |
|-------|------|--------|
| 1 | Backend StackRecommender | 4-5h |
| 2 | API Endpoint | 2-3h |
| 3 | Frontend Component | 3-4h |
| 4 | Configuration & Integration | 2-3h |
| 5 | Testing & Polish | 2-3h |
| 6 | Documentation | 2h |
| **Total** | **Complete Implementation** | **16-20h** |

#### Priority Justification

**Why MEDIUM Priority**:
- Improves UX significantly (reduces setup friction)
- Privacy win (local-first AI)
- Cost reduction (zero API spend)
- Educational benefit (reasoning displayed)
- Good use case for micro LLMs (structured task, small context)

**Why Not HIGH Priority**:
- Users can manually fill stack fields (workaround exists)
- Optional feature (requires LM Studio installed)
- Not blocking core orchestration workflows
- Can be completed post-release

**Recommended Timeline**: v3.1 or v3.2 (after core monitoring UI complete)

#### Related Handovers

- **Product Vision Upload System**: Existing infrastructure for vision docs
- **Agent Template Management (0041)**: Similar pattern (AI-powered configuration)
- **Admin Settings Integrations Tab (0027)**: LM Studio config UI location

#### Comparison to Cloud-Based Alternative

| Aspect | Local LLM (This Proposal) | Cloud API (e.g., GPT-4) |
|--------|---------------------------|-------------------------|
| **Privacy** | ✅ Vision docs stay local | ❌ Docs sent to cloud |
| **Cost** | ✅ Zero (after setup) | ❌ $0.01-0.05 per request |
| **Speed** | ⚠️ 30-60s on CPU | ✅ 3-5s cloud latency |
| **Quality** | ⭐⭐⭐⭐ (code-focused model) | ⭐⭐⭐⭐⭐ (GPT-4 better) |
| **Offline** | ✅ Works offline | ❌ Internet required |
| **Setup** | ⚠️ LM Studio + model download | ✅ API key only |
| **Compliance** | ✅ GDPR-friendly | ⚠️ Depends on vendor |

**Verdict**: Local LLM is better fit for this use case (privacy, cost, good-enough quality)

---

### 📝 MEDIUM-1: Developer Workflow Guide (Handover 0068)
**Status**: Not Started
**Impact**: MEDIUM - Improves onboarding
**Complexity**: LOW (documentation only)
**Effort**: 8-10 hours
**Dependencies**: None

**Grouped with**: Documentation improvements

#### What This Provides:
- Complete end-to-end workflow guide
- 30-minute quick start tutorial
- Code snippets and examples
- Best practices and patterns

#### Implementation:
- Create `docs/DEVELOPER_WORKFLOW_GUIDE.md` (~4000 words)
- Create `docs/guides/QUICK_START_TUTORIAL.md` (~1500 words)
- Create `docs/guides/COMMON_PATTERNS.md` (~500 words)
- Update `docs/README_FIRST.md` and `CLAUDE.md` with links

**Related Handover**: `handovers/0068_developer_workflow_guide.md`

---

### 📝 MEDIUM-2: Codex MCP Integration (Handover 0066)
**Status**: Not Started
**Impact**: MEDIUM - Adds tool option
**Complexity**: HIGH
**Effort**: 12-16 hours
**Dependencies**: Handover 0060 (MCP tools), Handover 0063 (Tool selection UI)

**Grouped with**: Multi-tool support features

#### What This Enables:
- OpenAI Codex as alternative agent tool
- Full MCP coordination tool access
- Feature parity with Claude Code

#### Implementation:
- Backend: Python integration (~800 lines across 8 files)
  - `CodexClient` - Wrapper for Codex CLI
  - `CodexMCPAdapter` - Bridges Codex to GiljoAI
  - Authentication and job execution
  - Configuration in Integrations tab
  - Agent runner script
- Testing and documentation

**Related Handover**: `handovers/0066_codex_mcp_integration.md`

---

### 📝 MEDIUM-3: Gemini MCP Integration (Handover 0067)
**Status**: Not Started
**Impact**: MEDIUM - Adds multimodal capabilities
**Complexity**: VERY HIGH (cross-language bridge required)
**Effort**: 16-20 hours
**Dependencies**: Handover 0060 (MCP tools), Handover 0063 (Tool selection UI), Node.js runtime

**Grouped with**: Multi-tool support features

#### What This Enables:
- Google Gemini 2.0 Flash as agent tool
- Multimodal capabilities (vision, audio)
- Competitive alternative to Claude/Codex

#### Implementation:
- Node.js wrapper server (~1100 lines across 12 files)
  - MCP wrapper using Gemini JavaScript SDK
  - HTTP/WebSocket bridge to Python backend
  - Process lifecycle management
- Python bridge
  - `GeminiClient` - Communicates with Node.js wrapper
  - `GeminiMCPAdapter` - Job execution
  - Process manager
- Configuration, testing, documentation

**Note**: Most complex integration due to cross-language requirements.

**Related Handover**: `handovers/0067_gemini_mcp_integration.md`

---

## Resolved Items

### ✅ RESOLVED: MCP Slash Commands (Original Gap 2)
**Status**: FUNCTIONALLY COMPLETE (Different Pattern)
**Original Status**: "NOT IMPLEMENTED despite completion docs"
**Date Verified**: 2025-10-27

#### What Was Expected:
- `.claude/commands/` directory with markdown files
- `project-setup.md`, `agent-spawn.md`, `workflow-run.md`
- Traditional slash command files

#### What Was Actually Implemented:
- **8 MCP tools** in `src/giljo_mcp/tools/orchestration.py`
- MCP tools return formatted instructions instead of stored command files
- Functional workflow reduction: 12+ steps → 3 commands
- Project alias system (6-char codes)
- Template HTTP endpoints

#### Why Different Pattern:
- FastMCP doesn't support `@mcp.prompt()` in HTTP adapter mode
- MCP tools returning instruction strings is the functional equivalent
- Works as intended, just not file-based

#### MCP Tools Implemented:
1. `orchestrate_project()` - Complete orchestration workflow
2. `get_agent_mission()` - Retrieve agent missions
3. `get_workflow_status()` - Workflow status tracking
4. `get_project_by_alias()` - Project lookup by alias
5. `activate_project_mission()` - Activate and plan
6. `get_launch_prompt()` - Launch instructions
7. `get_fetch_agents_instructions()` - Agent installation
8. `get_update_agents_instructions()` - Agent updates

#### Remaining Work:
- Frontend UI wizard components (documented but not implemented)
- `.claude/commands/` directory structure for documentation purposes

**Verdict**: Marked as RESOLVED - functional requirements met with different architectural pattern.

---

## Architectural Concerns & Code Review Findings

### 🔧 ARCHITECTURAL DEBT: MCP HTTP Tool Catalog Scalability (Handover 0089 Review)

**Status**: PRODUCTION APPROVED | ARCHITECTURE CONCERNS FOR FUTURE
**Impact**: MEDIUM - Growing maintenance burden as tool count increases
**Complexity**: MEDIUM - Moderate refactoring required
**Effort**: 34 hours (1 week) - Non-critical but recommended for v4.0
**Dependencies**: None - Refactoring doesn't block current features
**Date Identified**: 2025-11-03 (Code Review - Handover 0089)

#### Executive Summary

The MCP HTTP tool catalog fix (Handover 0089) is **correctly implemented and production-ready**, exposing all 45 tools properly via JSON-RPC 2.0. However, the implementation pattern will become a maintenance burden as the tool catalog grows beyond 60+ tools. Current architecture lacks scalability safeguards.

**Current State**: Functional, no bugs, production-grade
**Future State Risk**: Critical maintenance burden at 60+ tools
**Recommendation**: Plan refactoring for v4.0, not blocking v3.0 release

#### The Problem

**Tool Registration Mismatch Pattern** in `api/endpoints/mcp_http.py`:

```
❌ CURRENT ARCHITECTURE:
- Tool definitions exist in TWO separate locations:
  1. Lines 142-708: Inline tool catalog (567 lines of JSON schemas)
  2. Lines 747-816: Tool mapping dictionary
- NO single source of truth
- Adding new tool requires updates in BOTH locations
- Risk of schema-to-handler mismatch increases with each new tool

Growing Codebase Projection:
- Current: 40 tools → 979 lines total
- v4.0: ~60-80 tools → 1500+ lines (unmaintainable)
- Per-tool overhead: ~14 lines of inline schema definition
```

#### Current Implementation Details

**File**: `api/endpoints/mcp_http.py` (979 lines)

**Tool Catalog Structure**:
```python
# Lines 142-708: INLINE tool definitions (567 lines)
async def handle_tools_list() -> Dict[str, Any]:
    tools = [
        {
            "name": "create_project",
            "description": "...",
            "inputSchema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        },
        # ... 39 more tools defined inline
    ]
    return {"tools": tools}

# Lines 747-816: SEPARATE tool mapping
async def handle_tools_call() -> Dict[str, Any]:
    tool_map = {
        "create_project": tool_accessor.create_project,
        "list_projects": tool_accessor.list_projects,
        # ... 39 more mappings
    }
    # Execute tool from tool_map[tool_name]
```

**Actual Tools Exposed**: 45 (exceeds 29 target from handover)
- 5 Project Management tools
- 1 Orchestrator tool
- 5 Agent Management tools
- 4 Message Communication tools
- 5 Task Management tools
- 4 Template Management tools
- 4 Context Discovery tools
- 1 Health & Status tool
- 6 Agent Coordination tools
- 4 Orchestration tools
- 2 Orchestrator Succession tools
- 4 Slash Commands tools

**Schema Completeness**: 100%
- All 45 tools have proper JSON-RPC 2.0 inputSchema
- All required fields properly marked
- All property types correctly defined
- Backward compatibility maintained

#### Identified Architectural Issues

**Issue 1: No Single Source of Truth** (HIGH IMPACT)
- Tool catalog and tool routing are separate code blocks
- Requires manual synchronization on tool additions
- **Risk**: Schema definitions can diverge from actual handlers
- **Example**: Add tool to catalog but forget to add to tool_map → Silent failure

**Issue 2: Schema Definition Sprawl** (MEDIUM IMPACT)
- 567 lines (58%) of file is inline JSON schemas
- Difficult to maintain consistency
- No reusable schema components
- Duplicated property definitions (e.g., "project_id" defined 30+ times)

**Issue 3: Tight Coupling** (MEDIUM IMPACT)
- Tool catalog hardcoded into HTTP endpoint handler
- Cannot be reused for:
  - WebSocket MCP transport
  - stdio MCP transport
  - API documentation generation
  - Test fixtures
  - Client SDK generation

**Issue 4: No Validation Layer** (LOW IMPACT)
- No automated check that schema matches method signature
- No compile-time verification of parameter types
- Runtime errors only if schema-signature mismatch
- Risk increases with team size (harder to catch during code review)

**Issue 5: Scalability Ceiling** (MEDIUM-HIGH IMPACT)
- Adding new tool: ~6 hours (write code + schema + test)
- At 10 new tools/release: 60 hours per cycle of schema/routing maintenance
- File will exceed 1500 lines at 60+ tools
- Merge conflicts inevitable on every tool-related PR

#### Testing & Verification Results

**Code Review Verdict**: ✅ APPROVED FOR PRODUCTION

**Verification Summary**:
- ✅ All 45 tools properly exposed via tools/list endpoint
- ✅ Tool schemas match execution signatures (100% validated)
- ✅ JSON-RPC 2.0 protocol compliance verified
- ✅ Error handling comprehensive and correct
- ✅ Backward compatibility maintained (6 original tools unchanged)
- ✅ Security isolation proper (API key + tenant context)
- ✅ No breaking changes from original 6-tool implementation
- ⚠️ Manual testing with Claude Code recommended (for performance validation)

**Test Results**:
```
Tool Discovery Test:      PASS ✅
Tool Execution Test:      PASS ✅
Schema Validation:        PASS ✅ (100% JSON-Schema compliant)
Error Handling:           PASS ✅
Backward Compatibility:   PASS ✅
Performance:              LIKELY PASS ⚠️ (static definitions, <50ms expected)
```

#### Recommended Refactoring Strategy (v4.0)

**Phase 1: Extract Tool Registry** (Priority 1 - CRITICAL)
**Effort**: 8 hours | **Risk**: LOW

Create centralized tool registration system:

```python
# NEW FILE: api/mcp/tool_registry.py
class MCPToolRegistry:
    """Centralized tool registration and schema management"""

    def __init__(self):
        self._tools: Dict[str, MCPToolDefinition] = {}

    def register(self, name: str, schema: Dict, handler: Callable):
        """Register tool with validation"""
        self._validate_schema(schema)
        self._tools[name] = MCPToolDefinition(name, schema, handler)

    def get_tools_list(self) -> List[Dict]:
        """Generate tools/list response (single source of truth)"""
        return [tool.to_mcp_schema() for tool in self._tools.values()]

    def execute_tool(self, name: str, args: Dict, context) -> Any:
        """Execute tool with context"""
        tool = self._tools[name]
        return await tool.handler(**args)
```

**Phase 2: Implement Schema Components** (Priority 1 - CRITICAL)
**Effort**: 4 hours | **Risk**: LOW

Create reusable schema fragments:

```python
# NEW FILE: api/mcp/schemas.py
# Reusable schema components
PROJECT_ID_SCHEMA = {"type": "string", "description": "Project UUID"}
TENANT_KEY_SCHEMA = {"type": "string", "description": "Tenant isolation key"}
AGENT_ID_SCHEMA = {"type": "string", "description": "Agent identifier"}

def build_tool_schema(
    name: str,
    props: Dict[str, Dict],
    required: List[str]
) -> Dict:
    """Build consistent tool schemas from components"""
```

**Phase 3: Separate Concerns** (Priority 2)
**Effort**: 12 hours | **Risk**: MEDIUM

Reorganize `api/endpoints/mcp_http.py`:

```
api/mcp/
├── protocol.py        # JSON-RPC 2.0 protocol handling (extract lines 34-140)
├── registry.py        # Tool registration (new)
├── router.py          # Tool dispatch (extract lines 747-867)
├── schemas.py         # Reusable schema components (new)
└── handlers.py        # Request handlers (extract lines 910-970)

api/endpoints/
└── mcp_http.py        # Thin wrapper orchestrating above modules
```

**Phase 4: Type Safety** (Priority 3 - ENHANCEMENT)
**Effort**: 8 hours | **Risk**: MEDIUM

Add Pydantic models for tool arguments:

```python
# NEW: Tool args modeled as Pydantic BaseModel
class CreateProjectArgs(BaseModel):
    name: str
    mission: str
    tenant_key: Optional[str] = None

# Schema auto-generated from type hints
@tool_registry.register(args_model=CreateProjectArgs)
async def create_project(args: CreateProjectArgs) -> Dict:
    """Type-safe with auto-schema"""
```

**Phase 5: Auto-Documentation** (Priority 4 - ENHANCEMENT)
**Effort**: 4 hours | **Risk**: LOW

Generate MCP tool docs from registry:

```python
def generate_tool_docs(registry: MCPToolRegistry) -> str:
    """Auto-generate markdown from registry
    Output: docs/api/mcp_tools.md
    """
```

#### Implementation Roadmap (v4.0)

| Phase | Task | Effort | Risk | Timeline |
|-------|------|--------|------|----------|
| 1 | Extract registry class | 8h | LOW | Week 1 |
| 2 | Schema components | 4h | LOW | Week 1 |
| 3 | Separate concerns | 12h | MEDIUM | Week 2 |
| 4 | Type safety (optional) | 8h | MEDIUM | Week 2 |
| 5 | Auto-documentation | 4h | LOW | Week 3 |
| **Total** | **Refactoring complete** | **34h** | **LOW** | **3 weeks** |

**Migration Strategy**:
1. **Shadow Implementation** (Day 1-2): New registry runs parallel
2. **Gradual Migration** (Day 3-4): Switch endpoints one by one
3. **Cleanup** (Day 5): Remove old code, validate

#### Benefits of Refactoring

| Metric | Current | After Refactoring | Improvement |
|--------|---------|-------------------|-------------|
| File size | 979 lines | ~300 lines | -69% |
| Schema definition effort | 14 lines/tool | 2 lines/tool | -86% |
| Maintenance per new tool | 6 hours | 1 hour | -83% |
| Break-even point | N/A | ~10 tools | ROI immediate |
| Scalability ceiling | 60+ tools | 1000+ tools | Unlimited |
| Code duplication | HIGH | NONE | Eliminated |
| Testability | MEDIUM | HIGH | +40% easier |

#### Risk Assessment

**Technical Risk**: LOW
- Changes isolated to endpoint layer
- No API contract changes
- Backward compatible refactoring
- Can be done incrementally with parallel running

**Project Risk**: MEDIUM
- Requires experienced developer
- Moderate complexity (not trivial)
- Good documentation helps

**Timeline Risk**: LOW
- 1 week effort is manageable
- Can extend if needed
- No external dependencies

#### Success Criteria

**Functional Requirements**:
- ✅ All 45 tools still exposed
- ✅ No breaking changes to tool signatures
- ✅ JSON-RPC 2.0 protocol unchanged
- ✅ Error handling identical

**Code Quality Requirements**:
- ✅ Single source of truth for tool definitions
- ✅ No code duplication (schema reuse)
- ✅ <300 lines in main endpoint file
- ✅ Each new tool requires <2 lines of new code

**Documentation Requirements**:
- ✅ "How to Add a New Tool" guide updated
- ✅ Schema component library documented
- ✅ Registry usage examples provided

#### Post-Refactoring Use Case

After refactoring, adding a new tool becomes simple:

```python
# CURRENT (Handover 0089): 14 lines + 1 line routing
{
    "name": "my_tool",
    "description": "Does something useful",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "number"}
        },
        "required": ["param1"]
    }
}
# Plus one line in tool_map

# AFTER REFACTORING: 2 lines
registry.register(
    name="my_tool",
    model=MyToolArgs,  # Pydantic model (already written for handler)
    handler=my_tool_handler
)
```

#### Why This Matters for v4.0

**Planning Context**:
- v3.0: Core orchestration + UI monitoring (BLOCKER 1-4)
- v4.0: Advanced features (more agents, more tools, AI-to-AI workflows)
- **Problem**: v4.0 roadmap includes 15+ new tools
- **Solution Required**: Clean architecture to handle growth

**v4.0 Planned Tools**:
- Dynamic workflow generation (2 tools)
- Advanced agent coordination (4 tools)
- Token budget management (3 tools)
- Real-time collaboration (2 tools)
- Analytics and insights (3 tools)
- Custom integrations (variable)

**Impact**: At current rate (14 lines/tool), v4.0 adds ~560 lines
With refactoring (2 lines/tool), v4.0 adds ~30 lines (**95% reduction**)

#### Related Files

**Current Implementation**:
- `api/endpoints/mcp_http.py` (979 lines) - Main HTTP endpoint
- `src/giljo_mcp/tools/tool_accessor.py` (2247 lines) - Tool implementations

**Handover Documentation**:
- `handovers/0089_mcp_http_tool_catalog_fix.md` - Tool catalog fix details
- `handovers/0060_mcp_agent_coordination_tool_exposure.md` - Related tool exposure

**Test Files** (Created during review):
- `tests/integration/test_mcp_http_tool_catalog.py` - 16 tests, 890 lines
- `tests/integration/MCP_HTTP_TOOL_CATALOG_TEST_REPORT.md` - Detailed test report

#### Decision & Next Steps

**Immediate (v3.0)**: NO CHANGES REQUIRED
- Current implementation approved for production
- Refactoring scheduled for v4.0
- No blocking issues

**v4.0 Planning (START SOON)**:
- Add refactoring task to v4.0 roadmap (top priority)
- Plan 1 week for implementation
- Begin registry design during current sprint
- Have prototype ready before v4.0 alpha

**Communication**:
- Document this assessment in architecture guide
- Brief team on v4.0 refactoring plan
- Establish code review checklist for new tools (temporary)

---

## Existing Workarounds Still Needed

### ⚠️ WORKAROUND: Nested v-window Theme Inheritance
**Status**: PARTIAL WORKAROUND IN PLACE
**Impact**: MEDIUM - Visual inconsistency
**Complexity**: MEDIUM
**Effort**: 2-3 days for proper fix
**Priority**: LOW (cosmetic issue)

#### Current State:
- **UserSettings.vue**: Has `:theme` prop workaround applied (line 438)
- **SystemSettings.vue**: Multiple nested v-windows WITHOUT workaround
  - Claude Code config modal
  - Codex config modal
  - Gemini config modal

#### Root Cause:
Vuetify limitation - nested v-windows don't inherit theme properly.

#### Proper Solutions (From Original Tech Debt):
1. **Route-based rendering** (Recommended)
   - Split Settings into separate routes
   - No nesting, clean URLs

2. **Conditional rendering with v-show**
   - Replace v-window with v-show cards
   - All content in DOM

3. **Component-based rendering**
   - Dynamic component loading
   - `<component :is="currentSubTabComponent" />`

#### Recommendation:
- **Immediate**: Apply `:theme` workaround to SystemSettings.vue modals
- **Post-release**: Implement route-based rendering for cleaner architecture

**Related**: TECHNICAL_DEBT.md Section 9 (lines 246-318)

---

### ⚠️ PARTIAL: Agent Core Behavior Field
**Status**: DATABASE FIELD EXISTS | UI/INJECTION MISSING
**Impact**: MEDIUM - Can't tune agent behavior
**Complexity**: LOW
**Effort**: 1-2 days
**Priority**: MEDIUM

#### What Exists:
- ✅ `AgentTemplate.behavioral_rules` (JSON column in database)
- ✅ `template_manager.get_behavioral_rules()` method
- ✅ Template system supports variables and rules

#### What's Missing:
- ❌ UI form fields in TemplateManager.vue
- ❌ Agent-specific behavior field (currently only template-level)
- ❌ API endpoint to update agent behavior
- ❌ Injection of behavior into agent missions at runtime
- ❌ Agent edit form for individual behavior configuration

#### Implementation Needed:
1. Add `behavior_philosophy` (Text) field to Agent model
2. Add API endpoint: `PATCH /api/v1/agents/{id}/behavior`
3. Modify template processing to inject agent behavior
4. Add UI textarea in agent edit form
5. Add behavior preview showing injection

**Related**: TECHNICAL_DEBT.md Section 9 (lines 320-324)

---

### ⚠️ CONSIDERATION: Agent Type Limits Per Project

**Context**: Handover 0072 completion raised question about optimal max agent types per project

**Current State**:
- No limit on agent types per project
- 6 default agent templates seeded per tenant:
  1. **orchestrator** - Coordinates multi-agent workflows
  2. **analyzer** - Code analysis and architecture review
  3. **implementer** - Feature implementation and coding
  4. **tester** - Test creation and quality assurance
  5. **reviewer** - Code review and feedback
  6. **documenter** - Documentation generation
- Users can create unlimited custom agent types
- Multiple agents of SAME type allowed (horizontal scaling)

**Recommendation**: Limit to **6-8 Agent Types Maximum** Per Project

**Rationale**:
1. **Cognitive Load**: Matches human working memory capacity (7±2 items)
2. **Coordination Overhead**: Each additional agent type increases communication complexity (N*(N-1)/2 connections)
3. **Default Coverage**: 6 default types cover 90% of software development workflows
4. **Proven Pattern**: 6 templates used successfully in production

**Implementation Options**:

**Option A - Soft Limit (Recommended)**:
- UI warning when exceeding 6-8 types
- Allow override with confirmation dialog
- Dashboard shows "Agent Type Density" metric
- **Effort**: 2-3 hours

**Option B - Hard Limit**:
- Database constraint preventing &gt;8 types per project
- Clear error message with guidance
- Admin override capability
- **Effort**: 4-6 hours

**Option C - UI Nudge Only**:
- Visual indicator showing type count
- Suggest reusing existing types
- No enforcement
- **Effort**: 1-2 hours

**Benefits**:
- Reduces orchestrator complexity
- Improves agent coordination efficiency
- Encourages type reuse over type proliferation
- Maintains flexibility via multiple agents of same type

**Type Reuse Patterns**:
```
Instead of:
- backend-implementer (1 agent)
- frontend-implementer (1 agent)
- api-implementer (1 agent)

Use:
- implementer (3 agents with different contexts)
```

**Related Handovers**:
- Handover 0072: Task-to-Agent Job Integration
- Handover 0041: Agent Template Management
- Handover 0020: Orchestrator Enhancement

**Decision Needed**: Choose implementation option (A/B/C)

**Estimated Effort**: 4-6 hours (Option B - Hard Limit with validation)

**Priority**: MEDIUM (post-release consideration)

---

## Harmonization Status: TECHNICAL_DEBT.md v1 → v2

**Analysis Date**: 2025-10-29

**Status**: ⚠️ **PARTIALLY HARMONIZED**

**What's In v2**:
- ✅ Section 9: Nested v-window theme preservation (lines 793-827)
- ✅ Agent behavior field enhancement (lines 831-858)
- ✅ Dashboard agent monitoring (lines 68-105)
- ✅ Enhanced agent cards (lines 187-217)
- ✅ MCP tool exposure (lines 140-167)

**What's Missing from v1**:
- ⚠️ Some implementation details from nested v-window section
- ⚠️ Original timestamps and context from v1 entries

**Recommendation**: 
- v2 is PRIMARY document (more comprehensive)
- v1 can be archived/deprecated
- No critical items missing from v2

**Action**: Update README to mark v1 as deprecated, v2 as active

---

## Release Readiness Checklist

### Pre-Release (Must Complete)
- [ ] Dashboard Agent Monitoring UI (BLOCKER 1) - 16-24 hours
- [ ] MCP Agent Coordination Tool Exposure (BLOCKER 2) - 4-6 hours
- [ ] Orchestrator Launch UI Workflow (BLOCKER 3) - 6-8 hours
- [ ] Enhanced Agent Cards (BLOCKER 4) - 8-10 hours

**Subtotal**: 34-48 hours (4-6 days)

### Pre-Release (High Priority)
- [ ] Task-Agent Integration & Orchestration (HIGH-0) - 12-16 hours
- [ ] Per-Agent Tool Selection UI (HIGH-1) - 6-8 hours
- [ ] Project-Product Association UI (HIGH-2) - 3-4 hours
- [ ] Mission Launch Summary (HIGH-3) - 6-8 hours

**Subtotal**: 27-36 hours (3-5 days)

### Post-Release (Medium Priority)
- [ ] Developer Workflow Guide (MEDIUM-1) - 8-10 hours
- [ ] Codex Integration (MEDIUM-2) - 12-16 hours
- [ ] Gemini Integration (MEDIUM-3) - 16-20 hours

**Subtotal**: 36-46 hours (5-6 days)

### Technical Debt Cleanup
- [ ] Apply v-window theme workaround to all modals - 2 hours
- [ ] Agent behavior UI and injection - 8-16 hours
- [ ] Route-based rendering refactor (post-release) - 16-24 hours

**Total Pre-Release Work**: 61-84 hours (8-11 days)
**Total Post-Release Work**: 36-46 hours (5-6 days)
**Total Technical Debt**: 26-42 hours (3-5 days)

---

## Implementation Priority Matrix

### By Difficulty (Simplest → Most Difficult)

#### 🟢 Simple (< 1 day each)
1. MCP Agent Coordination Tools (Handover 0060) - 4-6 hours
2. Project-Product Association UI (Handover 0064) - 3-4 hours
3. v-window theme workaround application - 2 hours
4. Agent behavior UI fields - 4-6 hours

#### 🟡 Medium (1-2 days each)
5. Per-Agent Tool Selection UI (Handover 0063) - 6-8 hours
6. Mission Launch Summary (Handover 0065) - 6-8 hours
7. Orchestrator Launch UI (Handover 0061) - 6-8 hours
8. Enhanced Agent Cards (Handover 0062) - 8-10 hours
9. Agent behavior injection logic - 8-12 hours
10. Developer Workflow Guide (Handover 0068) - 8-10 hours
11. Task-Agent Integration (HIGH-0) - 12-16 hours
12. Dashboard Agent Monitoring UI (Gap 1) - 16-24 hours

#### 🔴 Complex (2+ days each)
12. Codex MCP Integration (Handover 0066) - 12-16 hours
13. Gemini MCP Integration (Handover 0067) - 16-20 hours
14. Route-based rendering refactor - 16-24 hours

---

## Grouped Implementation Packages

### Package A: Core Orchestration UI (CRITICAL)
**Goal**: Make orchestration visible and usable
**Effort**: 34-48 hours (4-6 days)

1. MCP Agent Coordination Tools (0060) - Foundation
2. Orchestrator Launch UI (0061) - Entry point
3. Enhanced Agent Cards (0062) - Job visibility
4. Dashboard Agent Monitoring (Gap 1) - Complete monitoring

**Result**: Users can launch orchestrator, see jobs, monitor progress

---

### Package B: UX Improvements (HIGH)
**Goal**: Polish user experience and complete task integration
**Effort**: 27-36 hours (3-5 days)

1. Task-Agent Integration (HIGH-0) - Task execution workflows
2. Per-Agent Tool Selection (0063) - Tool assignment
3. Project-Product Association (0064) - Clear relationships
4. Mission Launch Summary (0065) - Preview before launch

**Result**: Intuitive workflows, complete task-agent integration, no confusion about relationships

---

### Package C: Multi-Tool Support (MEDIUM)
**Goal**: Enable Claude/Codex/Gemini options
**Effort**: 18-24 hours (2-3 days for first tool)

1. Per-Agent Tool Selection UI (0063) - Already in Package B
2. Codex Integration (0066) - First alternative tool
3. Gemini Integration (0067) - Second alternative tool (post-release)

**Result**: Users can choose best tool for each agent type

---

### Package D: Documentation & DX (MEDIUM)
**Goal**: Improve developer experience
**Effort**: 8-10 hours (1-2 days)

1. Developer Workflow Guide (0068) - Complete guide
2. Update README_FIRST.md - Navigation improvements
3. Code examples and snippets - Quick reference

**Result**: Fast onboarding, clear workflows, reduced support burden

---

### Package E: Technical Debt Cleanup (LOW)
**Goal**: Remove workarounds, proper solutions
**Effort**: 26-42 hours (3-5 days)

1. v-window theme workaround - Immediate fix (2 hours)
2. Agent behavior UI/injection - Medium-term (8-16 hours)
3. Route-based rendering - Long-term (16-24 hours)

**Result**: Clean architecture, no workarounds, maintainable code

---

## Risk Assessment

### High Risk Items
| Item | Risk | Mitigation |
|------|------|------------|
| **Dashboard Agent Monitoring** | Backend works but complex UI integration | Break into smaller components, test incrementally |
| **Gemini Integration** | Cross-language complexity, process management | Start with Codex (simpler), learn patterns |
| **Release Timeline** | 49-68 hours of critical work remaining | Focus on Packages A & B only for v3.0 |

### Medium Risk Items
| Item | Risk | Mitigation |
|------|------|------------|
| **Orchestrator Launch** | WebSocket coordination, multi-stage workflow | Reuse existing WebSocket infrastructure |
| **Enhanced Agent Cards** | Real-time updates, message linking | Leverage existing MessagesView patterns |

### Low Risk Items
| Item | Risk | Mitigation |
|------|------|------------|
| **MCP Tools** | API wrapper only | No risk - wraps existing APIs |
| **Tool Selection UI** | Simple dropdown | Standard Vuetify component |
| **Project-Product UI** | Form enhancement | Minimal changes |

---

## Success Metrics

### Must Have (v3.0 Release)
- ✅ Users can launch orchestrator from UI
- ✅ Users can see active agent jobs in real-time
- ✅ Users can monitor job progress with WebSocket updates
- ✅ Users can assign tools (Claude/Codex/Gemini) to agents
- ✅ Users understand product-project relationships
- ✅ Users can preview mission plans before execution

### Should Have (v3.1 Release)
- ✅ Codex fully integrated as alternative tool
- ✅ Complete developer workflow documentation
- ✅ Agent behavior customization UI
- ✅ Clean architecture (no workarounds)

### Nice to Have (v3.2+ Release)
- ✅ Gemini integrated with multimodal support
- ✅ Route-based rendering (no nested v-windows)
- ✅ Advanced agent template management
- ✅ Real-time token budget tracking

---

## Recommended Release Strategy

### Phase 1: v3.0 Beta (Implement Packages A & B)
**Scope**: Core orchestration + UX improvements + Task integration
**Effort**: 61-84 hours (8-11 days)
**Deliverables**:
- Dashboard agent monitoring working
- Orchestrator launch workflow complete
- Enhanced agent cards with job context
- Task-agent execution integration
- Tool selection and product association UIs
- Mission preview before launch

**Result**: **Fully functional orchestration with complete UI visibility and task execution**

---

### Phase 2: v3.0 Production (Add Package D)
**Scope**: Documentation
**Effort**: 8-10 hours (1-2 days)
**Deliverables**:
- Complete developer workflow guide
- Quick start tutorial (30 minutes)
- Code examples and patterns

**Result**: **Production-ready with excellent documentation**

---

### Phase 3: v3.1 (Add Package C - First Alternative Tool)
**Scope**: Codex integration
**Effort**: 12-16 hours (2 days)
**Deliverables**:
- Codex fully integrated
- Multi-tool workflows enabled
- Per-agent tool assignment working

**Result**: **Claude Code + Codex support**

---

### Phase 4: v3.2+ (Complete Packages C & E)
**Scope**: Gemini + Technical debt cleanup
**Effort**: 42-66 hours (5-8 days)
**Deliverables**:
- Gemini integration (multimodal)
- Route-based rendering
- Agent behavior customization
- All workarounds removed

**Result**: **Three AI tools + clean architecture**

---

## Appendix: File Locations

### Backend (Working - Production Ready)
- `src/giljo_mcp/agent_job_manager.py` - Job lifecycle
- `src/giljo_mcp/job_coordinator.py` - Orchestration
- `src/giljo_mcp/agent_communication_queue.py` - Messaging
- `api/endpoints/agent_jobs.py` - 13 REST endpoints
- `api/websockets.py` - WebSocket events
- `src/giljo_mcp/tools/orchestration.py` - 8 MCP tools

### Frontend (Needs Implementation)
- `frontend/src/components/agents/AgentMonitor.vue` - MISSING
- `frontend/src/components/agents/AgentJobCard.vue` - MISSING
- `frontend/src/stores/useAgentJobStore.js` - MISSING
- `frontend/src/views/DashboardView.vue` - NEEDS ENHANCEMENT
- `frontend/src/views/MessagesView.vue` - NEEDS JOB LINKING
- `frontend/src/services/api.js` - NEEDS AGENT JOB METHODS
- `frontend/src/services/websocket.js` - NEEDS JOB EVENT LISTENERS

### Documentation
- `handovers/TECHNICAL_DEBT.md` - Original v1.0 assessment
- `handovers/0060-0068_*.md` - Planned release features
- `handovers/completed/` - Completed project records
- `docs/DEVELOPER_WORKFLOW_GUIDE.md` - TO BE CREATED
- `docs/guides/QUICK_START_TUTORIAL.md` - TO BE CREATED

## add model query to agent template manager
need to be able to update models for agent tempalte manager for all coding tools

## serena advanced settings
  Advanced Serena Parameters (From SerenaAdvancedSettingsDialog.vue)

  1. use_in_prompts (bool) - Include Serena usage guidance in agent prompts
  2. tailor_by_mission (bool) - Adjust guidance to mission type (bugfix, feature, tests)
  3. dynamic_catalog (bool) - Recommend only Serena tools detected as available
  4. prefer_ranges (bool) - Prefer reading only relevant line ranges before full-file
  5. max_range_lines (int) - Largest recommended range before full-file (default 180)
  6. context_halo (int) - Extra lines around target ranges for context (default 12)

  Note: These advanced parameters are stored in config.yaml but not yet implemented in _fetch_serena_codebase_context(). That
  method currently returns placeholder/empty string (line 442).


## Developer panel
Local host based,
See all non modifiable fields such as agent tempaltes to tune it manually.
See a visualization of the architecture in various views like this, F:\GiljoAI_MCP\handovers\start_to_finish_agent_FLOW.md but graphically well represented.
INdex of all MCP commands with search fields and descriptions
Index of all api's with search fields and descriptions
Cataloge of agents and their functions
Database architecture
Intallation flow visualized like a ppt slide
search for a function, see its cascading dependancies
A depenancy catalog
A tech stack document
with versions and known depreciations
Show it at x.x.x.x\developer
will be removed after shipping as a branch perhaps

---

## 🎯 Recommended Next Steps (Post-0135-0139 Completion)

### 360 Memory Management - Enhancement Recommendations

**Context**: Handovers 0135-0139 (360 Memory Management) completed successfully on 2025-11-16. The following recommendations build on this foundation.

#### **ENHANCEMENT 1: Frontend UI for 360 Memory** (HIGH Priority)
**Handover**: 0137 Frontend (Deferred)
**Status**: Backend complete, UI missing
**Effort**: 8-12 hours
**Impact**: HIGH - Users can't manage GitHub settings without UI

**What's Needed**:
- GitHub settings form in My Settings → Integrations
- Product memory viewer in ProductsView
- Learning history timeline component
- Context summary display

**Files to Create**:
- `frontend/src/components/products/GitHubSettingsCard.vue` (~180 lines)
- `frontend/src/components/products/ProductMemoryPanel.vue` (~250 lines)
- `frontend/src/components/products/LearningTimeline.vue` (~200 lines)

**Files to Modify**:
- `frontend/src/views/ProductsView.vue` - Integrate memory panel
- `frontend/src/stores/products.js` - Already has WebSocket listeners (complete)

**Success Criteria**:
- ✅ Users can enable/disable GitHub integration
- ✅ Users can view product learning history
- ✅ UI updates in real-time via WebSocket
- ✅ Context summaries visible in product details

---

#### **ENHANCEMENT 2: Context Summary Population** (MEDIUM Priority)
**Status**: Schema exists, logic missing
**Effort**: 6-8 hours
**Impact**: MEDIUM - product_memory.context field unused

**What's Needed**:
- Populate `product_memory.context` with product summaries
- Summarize product state (active projects, key decisions, token usage)
- Update context on major events (project close, vision upload)
- MCP tool: `update_product_context(product_id, summary, token_count)`

**Implementation**:
- Service method: `ProductService.update_context_summary()`
- Trigger on: project closeout, vision document upload, manual refresh
- WebSocket event: `product:context:updated`

**Success Criteria**:
- ✅ Context field populated with meaningful summaries
- ✅ Token count tracked and updated
- ✅ Context refreshes on major events
- ✅ Accessible via MCP tool for orchestrators

---

#### **ENHANCEMENT 3: Memory Search & Export** (MEDIUM Priority)
**Status**: Not started
**Effort**: 12-16 hours
**Impact**: MEDIUM - Improves memory discoverability

**What's Needed**:
- Search across all learnings using GIN index
- Filter by project, date range, tags
- Export memory as markdown/PDF report
- Memory analytics (most common decisions, patterns)

**API Endpoints**:
- `POST /api/v1/products/{id}/memory/search` - Search learnings
- `GET /api/v1/products/{id}/memory/export` - Export report
- `GET /api/v1/products/{id}/memory/analytics` - Memory insights

**Success Criteria**:
- ✅ Fast search using GIN index (< 100ms)
- ✅ Export includes all sections (GitHub, learnings, context)
- ✅ Analytics show trends over time
- ✅ Multi-tenant isolation preserved

---

#### **ENHANCEMENT 4: GitHub Commit Display** (LOW Priority)
**Status**: Backend fetches commits, UI doesn't display
**Effort**: 4-6 hours
**Impact**: LOW - Nice to have for commit history

**What's Needed**:
- Component to display commit history per project
- Filter commits by date range
- Link commits to learning entries
- GitHub avatar/author display

**Files to Create**:
- `frontend/src/components/products/GitHubCommitHistory.vue` (~180 lines)

**Success Criteria**:
- ✅ Commit history visible in learning timeline
- ✅ Commits linked to projects
- ✅ GitHub metadata displayed (author, SHA, message)

---

#### **ENHANCEMENT 5: Memory Import/Migration** (LOW Priority)
**Status**: Not started
**Effort**: 8-10 hours
**Impact**: LOW - Helps users migrate from other systems

**What's Needed**:
- Import learnings from JSON file
- Import GitHub history in bulk
- Validate imported data structure
- Merge with existing memory (no duplicates)

**API Endpoints**:
- `POST /api/v1/products/{id}/memory/import` - Import learnings
- `POST /api/v1/products/{id}/memory/validate` - Validate import file

**Success Criteria**:
- ✅ Import supports JSON format
- ✅ Sequence numbers auto-adjusted
- ✅ Duplicate detection works
- ✅ Import preview before commit

---

### Implementation Priority Order

**Phase 1 (v3.1)**: Essential UX
1. **ENHANCEMENT 1**: Frontend UI (8-12h) - **CRITICAL**
2. **ENHANCEMENT 2**: Context Summary Population (6-8h) - **HIGH**

**Phase 2 (v3.2)**: Advanced Features
3. **ENHANCEMENT 3**: Memory Search & Export (12-16h) - **MEDIUM**
4. **ENHANCEMENT 4**: GitHub Commit Display (4-6h) - **LOW**

**Phase 3 (v4.0)**: Migration Tools
5. **ENHANCEMENT 5**: Memory Import/Migration (8-10h) - **LOW**

---

### Total Effort Estimates

| Phase | Enhancements | Effort | Timeline |
|-------|--------------|--------|----------|
| v3.1 | UI + Context | 14-20h | 2-3 days |
| v3.2 | Search + Commits | 16-22h | 2-3 days |
| v4.0 | Import/Migration | 8-10h | 1-2 days |
| **Total** | **5 Enhancements** | **38-52h** | **5-8 days** |

---

### Related Handovers

**Completed (Foundation)**:
- ✅ Handover 0135: Database Schema (COMPLETE)
- ✅ Handover 0136: Memory Initialization (COMPLETE)
- ✅ Handover 0137: GitHub Integration Backend (COMPLETE)
- ✅ Handover 0138: Project Closeout MCP Tool (COMPLETE)
- ✅ Handover 0139a: WebSocket Backend Events (COMPLETE)
- ✅ Handover 0139b: WebSocket Frontend Listeners (COMPLETE)

**Next**:
- 🔜 Handover 0140: GitHub Settings UI (ENHANCEMENT 1)
- 🔜 Handover 0141: Context Summary Populator (ENHANCEMENT 2)
- 🔜 Handover 0142: Memory Search & Export (ENHANCEMENT 3)

---

**Last Updated**: 2025-11-16
**Next Review**: After v3.1 (360 Memory UI complete)
**Owner**: Development Team
**Priority**: CRITICAL - Blocks v3.0 release until Packages A & B complete

---




---

## 🔧 FRONTEND API PATTERN DEBT: Broken api.post()/api.get() Calls

**Status**: NEEDS FIX
**Impact**: MEDIUM - These calls will fail at runtime
**Complexity**: LOW
**Effort**: 2-3 hours total
**Date Identified**: 2025-01-27

### Root Cause

The API service (`frontend/src/services/api.js`) uses a namespaced structure (e.g., `api.agentJobs.*`, `api.products.*`) rather than exposing raw axios methods like `api.post()` or `api.get()`. Several components use the incorrect pattern.

### Affected Files

| File | Line | Broken Pattern | Fix Required |
|------|------|----------------|--------------|
| `OrchestratorCard.vue` | 154 | `api.get('/api/v1/prompts/orchestrator/...')` | Add `api.prompts.getOrchestrator()` method |
| `AgentExecutionModal.vue` | 108 | `api.get('/jobs/...')` | Add `api.jobs.get()` method or use existing |
| `TemplateArchive.vue` | 248 | `api.get('/api/templates/.../history')` | Add `api.templates.getHistory()` method |
| `TemplateArchive.vue` | 312 | `api.post('/api/templates/.../restore')` | Add `api.templates.restore()` method |

### Implementation Pattern

Each broken call requires:
1. Add method to appropriate namespace in `api.js`
2. Update component to use namespaced method
3. Test the functionality

**Example Fix** (from ActionIcons.vue handover fix):
```javascript
// api.js - Add to agentJobs namespace
simpleHandover: (jobId) => apiClient.post(`/api/agent-jobs/${jobId}/simple-handover`),

// Component - Use namespaced method
const response = await api.agentJobs.simpleHandover(props.job.job_id)
```

### Priority

**MEDIUM** - These features will fail when used, but may be infrequently accessed paths. Fix when touching these files or before v4.0 release.

---

**End of Technical Debt v2.0**
