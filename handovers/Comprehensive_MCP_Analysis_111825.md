---
**Document Type:** MCP Tool Architecture Analysis & Deprecation Plan
**Date:** 2025-11-18
**Related Documents:** 
- [MCP_TOOL_DEEP_AUDIT_2025-11-07.md](./MCP_TOOL_DEEP_AUDIT_2025-11-07.md)
- [start_to_finish_agent_FLOW.md](./start_to_finish_agent_FLOW.md)
- [Handover 0116 - Agent Model Migration](./0116_agent_model_migration.md)
**Status:** ✅ Architecture Clarified, Deprecation Plan Ready
---

# Comprehensive MCP Tool Analysis

## Executive Summary

**Problem Statement (updated):** The HTTP MCP server now exposes **40 tools** via JSON-RPC 2.0 (tools/list aligns with tools/call). Earlier drafts cited 106 tools; that catalog has been consolidated. We validated removals and service-layer extraction and still identify **6 admin/dashboard tools** that should ultimately migrate to REST, leaving ~34 core MCP tools aligned with the thin‑client architecture. Legacy Agent‑model tools are no longer exposed via the HTTP MCP path.

**Root Cause:** Confusion between:
1. **Terminal-initiated MCP tools** (called from laptop Claude Code/Codex/Gemini via HTTP)
2. **Backend dashboard functions** (should be REST API endpoints)
3. **Legacy Agent model** vs **New MCPAgentJob model** (Handover 0116)

**Recommendation (updated):** Keep 34 core MCP tools for terminal agents; migrate 6 dashboard/admin tools (projects/templates admin) to REST API. Confirm legacy Agent‑model tools remain removed from HTTP MCP and retire any residual legacy providers to avoid confusion.

---

## Since Last Update (code + git)

- tools/list now enumerates 40 tools and matches tools/call mapping
  - Evidence: api/endpoints/mcp_http.py: handle_tools_list() (40 names) and handle_tools_call() map
  - Changelog note: “2025-11-03: Fixed tool catalog mismatch” (file now lists 40)
- Service extraction completed for core domains (Projects, Templates, Tasks, Messages, Orchestration)
  - Commits: Handover 0123 Phase 2, Handover 0121 Phase 1
- Deprecated stubs removed; unified migration applied
  - Commits: “Remove deprecated method stubs”, “Complete Handover 0116 & 0113 unified migration”
- Legacy Agent‑model MCP tools are not exposed by HTTP MCP
  - tool_accessor has no spawn_agent/list_agents/etc.
  - Legacy Agent utilities exist under src/giljo_mcp/tools/agent.py (stdio/historical) – recommend retire/mark internal

---

## Table of Contents

1. [Architecture Clarification](#architecture-clarification)
2. [The Actual Flow (ASCII)](#the-actual-flow-ascii)
3. [Tool Categorization](#tool-categorization)
4. [Obsolete Tools Analysis](#obsolete-tools-analysis)
5. [Tools to Keep](#tools-to-keep)
6. [Implementation Plan](#implementation-plan)
7. [Technical Evidence](#technical-evidence)

---

## Architecture Clarification

### The Critical Misunderstanding

**Initial Assumption (WRONG):**
```
Backend orchestrator → spawns agents → dashboard displays results
```

**Actual Architecture (CORRECT):**
```
Laptop terminal (Claude Code) → HTTP MCP → Remote server → Database
                ↓                                              ↓
         User copies prompts                          Dashboard shows cards
                ↓
         Pastes in terminal
                ↓
         Agent calls MCP tools via HTTP
```

### The Key Insight

**ALL MCP TOOLS ARE CALLED FROM LAPTOP TERMINAL AGENTS VIA HTTP, NOT FROM BACKEND PROCESSES.**

This fundamentally changes which tools are needed:
- ✅ Tools terminal agents need to coordinate work
- ❌ Tools for backend dashboard operations (should be REST API)
- ❌ Tools using legacy Agent model (should use MCPAgentJob)
- ❌ Stub tools with no implementation

---

## The Actual Flow (ASCII)

### Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GILJOAI MCP ARCHITECTURE                              │
│                    (Terminal Agents ↔ Remote Server)                         │
└─────────────────────────────────────────────────────────────────────────────┘

LAPTOP (Local Environment)                    REMOTE SERVER (Port 7272)
══════════════════════════                    ═══════════════════════════

┌─────────────────────────┐                   ┌──────────────────────────┐
│  Claude Code Terminal   │                   │   MCP HTTP Server        │
│  (or Codex/Gemini)      │                   │   (FastAPI + JSON-RPC)   │
└───────────┬─────────────┘                   └──────────┬───────────────┘
            │                                            │
            │  HTTP POST /mcp                            │
            │  JSON-RPC 2.0 Request                      │
            ├───────────────────────────────────────────>│
            │                                            │
            │  {                                         │
            │    "method": "tools/call",                 │
            │    "params": {                             │
            │      "name": "spawn_agent_job",            ├──────> PostgreSQL
            │      "arguments": {...}                    │        ┌──────────┐
            │    }                                       │        │ Database │
            │  }                                         │        ├──────────┤
            │                                            │        │ Projects │
            │  <─────────────────────────────────────────┤        │ Products │
            │  Response: {                               │        │ MCPAgentJob
            │    "result": {                             │        │ Agent (legacy)
            │      "agent_job_id": "abc-123",            │        │ Templates│
            │      "prompt": "..."                       │        └──────────┘
            │    }                                       │              │
            │  }                                         │              │
            │                                            │              │
            │                                            │         ┌────v──────┐
┌───────────┴─────────────┐                   ┌────────┴─────────┤  Dashboard │
│ User copies prompt from │<───────────────────┤   Vue.js UI      │    UI      │
│ dashboard, pastes in    │    WebSocket       │                  │            │
│ terminal, agent runs    │    Events          │  - Launch Tab    │            │
│ code, calls MCP tools   │                    │  - Jobs Tab      │            │
└─────────────────────────┘                    │  - Agent Cards   │            │
                                               └──────────────────┘
```

### Phase-by-Phase Flow

```
PHASE 1: STAGING (Launch Tab)
════════════════════════════════════════════════════════════════════════

┌─────────────┐
│ DASHBOARD   │  1. User creates project with requirements
│ (Launch Tab)│  2. User clicks "Stage Project"
└──────┬──────┘
       │
       │  3. Dashboard generates orchestrator staging prompt
       │     ┌────────────────────────────────────────────────────┐
       │     │ "You are Orchestrator #abc-123                     │
       │     │  Read project: get_orchestrator_instructions()     │
       │     │  Analyze requirements, create mission plan         │
       │     │  Spawn agent jobs via spawn_agent_job()            │
       │     │  Report status to dashboard"                       │
       │     └────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│ USER LAPTOP      │  4. User copies prompt
│ Terminal Window  │  5. User pastes in Claude Code terminal
└────────┬─────────┘
         │
         │  6. Claude Code executes:
         ▼
   ┌─────────────────────────────────────────────┐
   │ HTTP MCP Tools Called by Orchestrator:      │
   │                                              │
   │ ✅ get_orchestrator_instructions()          │────> Fetch project.description
   │    └─> Returns: product vision, project     │      product vision, context
   │        requirements, agent templates        │
   │                                              │
   │ ✅ spawn_agent_job(type="implementer", ...) │────> Create MCPAgentJob
   │    └─> Creates: MCPAgentJob record          │      status="waiting"
   │        status="waiting" in database         │
   │                                              │
   │ ✅ spawn_agent_job(type="tester", ...)      │────> Create MCPAgentJob
   │ ✅ spawn_agent_job(type="documenter", ...)  │────> Create MCPAgentJob
   │                                              │
   │ ✅ update_project_mission(mission_plan)     │────> Persist mission
   │    └─> Saves: Project.mission field         │      to database
   │                                              │
   └──────────────────────────────────────────────┘
                          │
                          │  7. WebSocket events fire
                          ▼
                   ┌──────────────┐
                   │  DASHBOARD   │  8. Agent cards appear live
                   │  (Launch Tab)│     - Implementer card
                   │              │     - Tester card
                   │  Agent Cards │     - Documenter card
                   │  Displayed   │     - Each shows agent_job_id
                   └──────────────┘


PHASE 2: EXECUTION (Implementation Tab)
════════════════════════════════════════════════════════════════════════

┌─────────────────┐
│ DASHBOARD       │  1. User switches to Implementation tab
│ (Jobs Tab)      │  2. Agent cards show "Launch Agent" buttons
└────────┬────────┘
         │
         │  3. User copies each agent's launch prompt:
         │     ┌──────────────────────────────────────────────┐
         │     │ "You are Implementer agent                   │
         │     │  Agent ID: agent-xyz                         │
         │     │  Get your mission: get_agent_mission(...)    │
         │     │  Execute work, report progress               │
         │     │  Complete via complete_job()"                │
         │     └──────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────┐
│ USER LAPTOP          │  4. MULTI-TERMINAL MODE:
│ Terminal Windows     │     - Paste prompt in Terminal 1 (Implementer)
│ (Multiple)           │     - Paste prompt in Terminal 2 (Tester)
└──────────┬───────────┘     - Paste prompt in Terminal 3 (Documenter)
           │
           │  OR CLAUDE CODE MODE:
           │     - Paste ONLY orchestrator prompt in single terminal
           │     - Claude spawns sub-agents automatically
           │
           │  5. Each agent terminal executes:
           ▼
   ┌──────────────────────────────────────────────┐
   │ HTTP MCP Tools Called by Agents:             │
   │                                               │
   │ ✅ get_pending_jobs(agent_type="implementer")│────> Find my work
   │    └─> Returns: MCPAgentJob records          │      from database
   │        status="waiting"                       │
   │                                               │
   │ ✅ acknowledge_job(job_id)                    │────> Claim job
   │    └─> Updates: status="waiting"→"active"    │      Update status
   │                                               │
   │ ✅ get_agent_mission(agent_job_id)           │────> Fetch mission
   │    └─> Returns: Thin mission (~10 lines)     │      (~2000 tokens)
   │                                               │
   │ [Agent performs work: writes code, etc.]      │
   │                                               │
   │ ✅ report_progress(job_id, percent, message) │────> Update progress
   │    └─> Updates: progress_percentage          │      Dashboard shows
   │                                               │      live updates
   │                                               │
   │ ✅ send_message(to_agent, content)           │────> Coordinate
   │    └─> Creates: Message record               │      with team
   │                                               │
   │ ✅ complete_job(job_id, output)              │────> Mark done
   │    └─> Updates: status="completed"           │      Final status
   │                                               │
   └───────────────────────────────────────────────┘
                          │
                          │  6. WebSocket events fire
                          ▼
                   ┌──────────────┐
                   │  DASHBOARD   │  7. Agent cards update live:
                   │  (Jobs Tab)  │     - Progress bars move
                   │              │     - Status changes color
                   │  Live Status │     - Completion checkmarks
                   │  Updates     │     - Message notifications
                   └──────────────┘
```

### Data Model Flow

```
DATABASE TABLES USED BY MCP TOOLS
════════════════════════════════════════════════════════════════════

┌──────────────────────────────────────────────────────────────────┐
│ STAGING PHASE (Launch Tab)                                       │
└──────────────────────────────────────────────────────────────────┘

[Terminal Agent] ──> get_orchestrator_instructions() ──> READS:
                                                          ├─> projects (description)
                                                          ├─> products (vision)
                                                          └─> agent_templates (active)

[Terminal Agent] ──> spawn_agent_job() ──────────────> WRITES:
                                                          └─> mcp_agent_jobs (NEW record)
                                                              - status = "waiting"
                                                              - agent_type
                                                              - mission
                                                              - tenant_key

[Terminal Agent] ──> update_project_mission() ────────> WRITES:
                                                          └─> projects.mission
                                                              (AI-generated plan)

┌──────────────────────────────────────────────────────────────────┐
│ EXECUTION PHASE (Jobs Tab)                                       │
└──────────────────────────────────────────────────────────────────┘

[Terminal Agent] ──> get_pending_jobs() ──────────────> READS:
                                                          └─> mcp_agent_jobs
                                                              WHERE status="waiting"

[Terminal Agent] ──> acknowledge_job() ───────────────> WRITES:
                                                          └─> mcp_agent_jobs.status
                                                              "waiting" → "active"

[Terminal Agent] ──> get_agent_mission() ─────────────> READS:
                                                          └─> mcp_agent_jobs.mission

[Terminal Agent] ──> report_progress() ───────────────> WRITES:
                                                          └─> mcp_agent_jobs.progress_percentage

[Terminal Agent] ──> complete_job() ──────────────────> WRITES:
                                                          └─> mcp_agent_jobs.status
                                                              "active" → "completed"

┌──────────────────────────────────────────────────────────────────┐
│ LEGACY TOOLS (OBSOLETE) - Using Wrong Table                      │
└──────────────────────────────────────────────────────────────────┘

❌ spawn_agent() ───────────────────────────────────> WRITES:
                                                          └─> agents (LEGACY 4-state model)
                                                              ❌ WRONG TABLE!

❌ list_agents() ───────────────────────────────────> READS:
                                                          └─> agents (LEGACY)
                                                              ❌ Should read mcp_agent_jobs!

❌ get_agent_status() ──────────────────────────────> READS:
                                                          └─> agents (LEGACY)
                                                              ❌ Should read mcp_agent_jobs!
```

---

## Tool Categorization

### Category Breakdown

```
TOTAL MCP TOOLS: 106
═══════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────┐
│ ✅ KEEP: Terminal Agent Essentials (35 tools)          │
├─────────────────────────────────────────────────────────┤
│ - Core workflow (orchestration, jobs, missions)        │
│ - Communication (messages, coordination)               │
│ - Project context (create, switch, update)             │
│ - Slash commands (template downloads)                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ❌ REMOVE: Obsolete Tools (11 tools)                   │
├─────────────────────────────────────────────────────────┤
│ - Legacy Agent model tools (7 tools)                   │
│ - Context discovery stubs (4 tools)                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ ⚠️  MIGRATE: Dashboard Functions (6 tools)             │
├─────────────────────────────────────────────────────────┤
│ - Project management (list, get, close)                │
│ - Template management (list, create, update)           │
│ → Should be REST API endpoints, not MCP tools          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 🔍 REVIEW: Remaining Tools (~54 tools)                 │
├─────────────────────────────────────────────────────────┤
│ - Task management, vision processing, etc.             │
│ - Needs further analysis for terminal relevance        │
└─────────────────────────────────────────────────────────┘
```

---

## Obsolete Tools Analysis

Update 2025-11-18: The HTTP MCP endpoint no longer exposes legacy Agent‑model tools. Any remaining legacy Agent utilities live under `src/giljo_mcp/tools/agent.py` and are not mapped via `api/endpoints/mcp_http.py`. The detailed items below are retained for historical traceability; recommendations remain to retire these legacy paths or clearly mark them as internal-only.

### 1. Legacy Agent Model Tools (7 Tools) ❌

**Problem:** These tools interact with the `agents` table (legacy 4-state model) instead of `mcp_agent_jobs` table (new 7-state model). Handover 0116 aims to eliminate this dual-model confusion.

#### Tool: `spawn_agent`

**Status:** Not exposed via HTTP MCP
**Location (legacy):** `src/giljo_mcp/tools/agent.py`

**What it does:**
```python
async def spawn_agent(self, name: str, role: str, mission: str) -> dict[str, Any]:
    """Spawn a new agent (alias for ensure_agent with role parameter)"""
    # Creates Agent record in legacy 'agents' table
    result = await self.ensure_agent(str(project.id), name, mission)
```

**Why obsolete:**
- Creates records in `agents` table (4-state: idle, active, completed, failed)
- Should use `spawn_agent_job()` which creates `mcp_agent_jobs` records (7-state)
- Dashboard reads from `mcp_agent_jobs`, not `agents` (creates data disconnect)

**Replacement:**
```python
# ❌ OLD (obsolete)
await spawn_agent(name="impl-1", role="implementer", mission="...")

# ✅ NEW (correct)
await spawn_agent_job(
    agent_type="implementer",
    agent_name="impl-1", 
    mission="...",
    project_id=project_id,
    tenant_key=tenant_key
)
```

**Evidence:**
```
api/endpoints/mcp_http.py:720: "spawn_agent": state.tool_accessor.spawn_agent
api/endpoints/mcp_http.py:226: Tool definition for spawn_agent
src/giljo_mcp/tools/tool_accessor.py:577: Implementation using Agent model
```

---

#### Tool: `list_agents`

**Status:** Not exposed via HTTP MCP
**Location (legacy):** `src/giljo_mcp/tools/agent.py`

**What it does:**
```python
async def list_agents(self, status: Optional[str] = None) -> dict[str, Any]:
    """List agents in current project"""
    # Queries 'agents' table
    query = select(Agent).where(Agent.project_id == project.id)
```

**Why obsolete:**
- Queries legacy `agents` table
- Dashboard agent cards read from `mcp_agent_jobs` table
- Returns data that doesn't match what user sees in UI

**Replacement:**
```python
# ❌ OLD (obsolete)
agents = await list_agents(status="active")

# ✅ NEW (correct)
jobs = await get_pending_jobs(agent_type=None)  # All agent types
# Or use dashboard REST API: GET /api/agent-jobs?project_id=...
```

---

#### Tool: `get_agent_status`

**Status:** Not exposed via HTTP MCP
**Location (legacy):** `src/giljo_mcp/tools/agent.py`

**What it does:**
```python
async def get_agent_status(self, agent_name: str) -> dict[str, Any]:
    """Get detailed status of a specific agent"""
    return await self.agent_health(agent_name)  # Queries Agent table
```

**Why obsolete:**
- Queries legacy `agents` table
- Status values don't align with MCPAgentJob 7-state model
- Replacement tool `get_workflow_status()` provides better team-level visibility

**Replacement:**
```python
# ❌ OLD (obsolete)
status = await get_agent_status(agent_name="impl-1")

# ✅ NEW (correct)
status = await get_workflow_status(project_id=project_id, tenant_key=tenant_key)
# Returns: active_agents, completed_agents, failed_agents, progress_percent
```

---

#### Tool: `update_agent`

**Status:** Not exposed via HTTP MCP
**Location (legacy):** `src/giljo_mcp/tools/agent.py`

**What it does:**
```python
async def update_agent(self, agent_name: str, **kwargs) -> dict[str, Any]:
    """Update agent properties"""
    # Finds and updates Agent record in legacy table
    agent = await session.execute(
        select(Agent).where(Agent.name == agent_name)
    )
    for key, value in kwargs.items():
        setattr(agent, key, value)
```

**Why obsolete:**
- Updates legacy `agents` table
- Doesn't update dashboard-visible MCPAgentJob records
- Replaced by specific tools: `report_progress()`, `complete_job()`

**Replacement:**
```python
# ❌ OLD (obsolete)
await update_agent(agent_name="impl-1", status="completed")

# ✅ NEW (correct)
await complete_job(agent_job_id=job_id, output=results)
# Or: await report_progress(job_id, percent=50, message="...")
```

---

#### Tool: `retire_agent`

**Status:** Not exposed via HTTP MCP
**Location (legacy):** `src/giljo_mcp/tools/agent.py`

**Why obsolete:**
- Updates legacy `agents` table status to "retired"
- MCPAgentJob uses "decommissioned" state (Handover 0113)
- Handover 0073 closeout workflow handles agent cleanup

**Replacement:**
```python
# ❌ OLD (obsolete)
await retire_agent(agent_name="impl-1")

# ✅ NEW (correct)
# Agent job lifecycle handles decommissioning automatically
# Or explicit: UPDATE mcp_agent_jobs SET status='decommissioned'
```

---

#### Tool: `ensure_agent`

**Status:** Not exposed via HTTP MCP
**Location (legacy):** `src/giljo_mcp/tools/agent.py`

**Why obsolete:**
- Internal helper function, shouldn't be exposed as MCP tool
- Creates/updates legacy `agents` table
- Used by `spawn_agent()` which is also obsolete

**Replacement:**
```python
# ❌ OLD (internal helper, shouldn't be MCP tool)
await ensure_agent(project_id, name, mission)

# ✅ NEW (use public tool)
await spawn_agent_job(...)
```

---

#### Tool: `agent_health`

**Location:** `src/giljo_mcp/tools/tool_accessor.py`

**Why obsolete:**
- Duplicate of `get_agent_status()`
- Queries legacy `agents` table
- Replaced by `get_workflow_status()`

**Replacement:**
```python
# ❌ OLD (duplicate)
health = await agent_health(agent_name="impl-1")

# ✅ NEW (use workflow status)
status = await get_workflow_status(project_id, tenant_key)
```

---

### 2. Context Discovery Stubs (4 Tools) ❌

**Problem:** These tools have no real implementation. They return hardcoded stub responses saying "Not yet implemented". Thin client architecture (Handover 0088) eliminated the need for these tools.

#### Tool: `discover_context`

**Evidence from MCP_TOOL_DEEP_AUDIT_2025-11-07.md:445**

**What it returns:**
```python
{
    "files": [],
    "dependencies": [],
    "message": "Context discovery not yet fully implemented"
}
```

**Why obsolete:**
- No implementation (stub)
- Thin client agents fetch mission via `get_agent_mission()`, not context tools
- Mission already contains necessary context (~2000 tokens)

---

#### Tool: `get_file_context`

**Evidence from MCP_TOOL_DEEP_AUDIT_2025-11-07.md:458**

**What it returns:**
```python
{
    "content": "",
    "message": "File context retrieval not yet implemented"
}
```

**Why obsolete:**
- No implementation (stub)
- Agents access files directly via filesystem in their terminal environment
- Not needed for MCP coordination

---

#### Tool: `search_context`

**Evidence from MCP_TOOL_DEEP_AUDIT_2025-11-07.md:471**

**What it returns:**
```python
{
    "results": [],
    "message": "Context search not yet implemented"
}
```

**Why obsolete:**
- No implementation (stub)
- Agents use their own IDE/editor search capabilities
- Not needed for MCP coordination

---

#### Tool: `get_context_summary`

**Evidence from MCP_TOOL_DEEP_AUDIT_2025-11-07.md:484**

**What it returns:**
```python
{
    "summary": "",
    "message": "Context summary not yet implemented"
}
```

**Why obsolete:**
- No implementation (stub)
- Mission from `get_agent_mission()` already provides summarized context
- Redundant with thin client architecture

---

### 3. Misplaced Dashboard Functions (6 Tools) ⚠️

**Problem:** These tools expose backend admin/dashboard operations that terminal agents don't need. They work fine but belong in REST API endpoints, not MCP tools.

#### Tool: `list_projects`

**Why misplaced:**
- Dashboard UI lists projects, not terminal agents
- User selects project in browser, then launches terminal agent
- Terminal agent receives `project_id` in launch prompt, doesn't need to list

**Better location:**
```
❌ MCP Tool: mcp__giljo-mcp__list_projects
✅ REST API: GET /api/projects?tenant_key=...
```

---

#### Tool: `get_project`

**Why misplaced:**
- Dashboard fetches project details to display in UI
- Terminal agent receives context via `get_orchestrator_instructions()`
- Doesn't need to fetch project separately

**Better location:**
```
❌ MCP Tool: mcp__giljo-mcp__get_project
✅ REST API: GET /api/projects/{id}
```

---

#### Tool: `close_project`

**Why misplaced:**
- User closes project from dashboard button
- Terminal agent completes job but doesn't close project
- Admin operation, not agent coordination

**Better location:**
```
❌ MCP Tool: mcp__giljo-mcp__close_project
✅ REST API: PATCH /api/projects/{id} { "status": "closed" }
```

---

#### Tool: `list_templates`

**Why misplaced:**
- Dashboard shows Agent Template Manager UI
- User browses/selects templates in browser
- Terminal agent doesn't manage templates

**Better location:**
```
❌ MCP Tool: mcp__giljo-mcp__list_templates
✅ REST API: GET /api/agent-templates?tenant_key=...
```

---

#### Tool: `create_template`

**Why misplaced:**
- User creates templates via dashboard form
- Admin operation, not agent coordination
- Terminal agent uses templates, doesn't create them

**Better location:**
```
❌ MCP Tool: mcp__giljo-mcp__create_template
✅ REST API: POST /api/agent-templates { ... }
```

---

#### Tool: `update_template`

**Why misplaced:**
- User edits templates via dashboard form
- Admin operation, not agent coordination
- Terminal agent doesn't modify templates

**Better location:**
```
❌ MCP Tool: mcp__giljo-mcp__update_template
✅ REST API: PATCH /api/agent-templates/{id} { ... }
```

---

## Tools to Keep

### Core Workflow Tools (Essential) ✅

#### Orchestration Phase Tools

```
┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR STAGING TOOLS (Launch Tab)                     │
└─────────────────────────────────────────────────────────────┘

✅ get_orchestrator_instructions(orchestrator_id, tenant_key)
   Purpose: Fetch condensed context for mission creation
   Returns: Project.description (user requirements), Product vision,
            Agent templates (available talent pool)
   Used by: Orchestrator terminal agent during staging
   Evidence: src/giljo_mcp/tools/orchestration.py:850+

✅ spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key)
   Purpose: Create MCPAgentJob record on server
   Returns: agent_job_id, thin_prompt (~10 lines)
   Used by: Orchestrator to register specialized agents
   Evidence: src/giljo_mcp/tools/tool_accessor.py:1611

✅ update_project_mission(project_id, mission, tenant_key)
   Purpose: Persist AI-generated mission plan to database
   Used by: Orchestrator after analyzing requirements
   Evidence: Project.mission field stores condensed plan

✅ orchestrate_project(project_id, tenant_key)
   Purpose: Full orchestration pipeline (vision → mission → agents)
   Returns: project_id, mission_plan, selected_agents, spawned_jobs
   Used by: Orchestrator for complete workflow execution
   Evidence: src/giljo_mcp/tools/orchestration.py:40
```

#### Agent Execution Tools

```
┌─────────────────────────────────────────────────────────────┐
│ AGENT EXECUTION TOOLS (Jobs Tab)                            │
└─────────────────────────────────────────────────────────────┘

✅ get_pending_jobs(agent_type, tenant_key)
   Purpose: Find agent's assigned work
   Returns: List of MCPAgentJob records with status="waiting"
   Used by: Terminal agents to discover their jobs
   Evidence: src/giljo_mcp/tools/tool_accessor.py (agent coordination)

✅ acknowledge_job(agent_job_id, tenant_key)
   Purpose: Claim job and transition state
   Updates: status "waiting" → "active" → "working"
   Used by: Agent when starting work
   Evidence: MCPAgentJob state machine (Handover 0113)

✅ get_agent_mission(agent_job_id, tenant_key)
   Purpose: Fetch thin client mission (~10 lines)
   Returns: Mission text (~2000 tokens), agent identity
   Used by: Agent immediately after launch
   Evidence: Handover 0088 thin client architecture

✅ report_progress(agent_job_id, progress_percentage, message, tenant_key)
   Purpose: Update job progress for dashboard visibility
   Updates: MCPAgentJob.progress_percentage, last_updated timestamp
   Used by: Agent periodically during work execution
   Evidence: Dashboard shows live progress bars

✅ complete_job(agent_job_id, output, tenant_key)
   Purpose: Mark job finished with results
   Updates: status "working" → "completed", store output
   Used by: Agent when work is done
   Evidence: Triggers dashboard updates, workflow progression

✅ report_error(agent_job_id, error_message, severity, tenant_key)
   Purpose: Report failures or blocks
   Updates: status → "failed", store failure_reason
   Used by: Agent when encountering errors
   Evidence: Handover 0113 error handling

✅ get_workflow_status(project_id, tenant_key)
   Purpose: Check team-level progress
   Returns: active_agents, completed_agents, failed_agents, progress_percent
   Used by: Orchestrator to monitor team coordination
   Evidence: src/giljo_mcp/tools/orchestration.py:370+
```

### Communication Tools ✅

```
┌─────────────────────────────────────────────────────────────┐
│ INTER-AGENT COMMUNICATION                                   │
└─────────────────────────────────────────────────────────────┘

✅ send_message(from_agent_id, to_agent_id, content, tenant_key)
   Purpose: Coordinate between agents
   Creates: Message record in database
   Used by: Agents to request info, report status, coordinate
   Evidence: Message hub for agent collaboration

✅ receive_messages(agent_id, tenant_key, limit)
   Purpose: Fetch agent's inbox
   Returns: List of unread messages
   Used by: Agents to check for coordination requests
   Evidence: Polling for inter-agent communication

✅ acknowledge_message(message_id, tenant_key)
   Purpose: Mark message as read
   Updates: Message.acknowledged = True
   Used by: Agent after processing message
   Evidence: Message read receipts

✅ list_messages(agent_id, tenant_key, status)
   Purpose: Get message history
   Returns: All messages (read/unread)
   Used by: Agents to review communication thread
   Evidence: Message persistence for debugging
```

### Project Context Tools ✅

```
┌─────────────────────────────────────────────────────────────┐
│ PROJECT CONTEXT MANAGEMENT                                  │
└─────────────────────────────────────────────────────────────┘

✅ create_project(name, description, tenant_key, product_id)
   Purpose: Orchestrator may create projects programmatically
   Returns: project_id, project object
   Used by: Advanced orchestration workflows
   Evidence: src/giljo_mcp/tools/tool_accessor.py project tools

✅ switch_project(project_id, tenant_key)
   Purpose: Change agent's active project context
   Updates: TenantManager current project
   Used by: Agents working across multiple projects
   Evidence: Multi-project tenant isolation

✅ health_check()
   Purpose: Verify MCP server connection
   Returns: {"status": "healthy", "server": "giljo-mcp", "version": "3.1.0"}
   Used by: Agents first action to confirm MCP availability
   Evidence: src/giljo_mcp/tools/orchestration.py:850
```

### Succession Tools ✅

```
┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR SUCCESSION (Handover 0080)                     │
└─────────────────────────────────────────────────────────────┘

✅ create_successor_orchestrator(current_orchestrator_id, reason, tenant_key)
   Purpose: Spawn replacement orchestrator when current one fails
   Returns: new_orchestrator_id, handover_context
   Used by: Failing orchestrator to ensure continuity
   Evidence: Handover 0080 succession mechanism

✅ check_succession_status(orchestrator_id, tenant_key)
   Purpose: Verify succession state
   Returns: successor_id, handover_complete, status
   Used by: Monitoring orchestrator health
   Evidence: Succession tracking
```

### Slash Command Tools ✅

```
┌─────────────────────────────────────────────────────────────┐
│ AGENT TEMPLATE DOWNLOADS (Slash Commands)                   │
└─────────────────────────────────────────────────────────────┘

✅ setup_slash_commands(tenant_key, api_key)
   Purpose: Download agent templates for Claude Code
   Returns: ZIP file with .md templates
   Used by: Initial setup, agent template updates
   Evidence: Handover 0093 slash command infrastructure

✅ gil_import_productagents(product_id, tenant_key, api_key)
   Purpose: Import product-specific agent templates
   Returns: Download token for template ZIP
   Used by: Product-specific agent setup
   Evidence: Multi-product template isolation

✅ gil_import_personalagents(tenant_key, api_key)
   Purpose: Import user's personal agent templates
   Returns: Download token for template ZIP
   Used by: Personal customization
   Evidence: User-level template management

✅ gil_handover(handover_number, tenant_key)
   Purpose: Generate handover documentation
   Returns: Handover markdown file
   Used by: Agent knowledge sharing
   Evidence: Handover creation workflow
```

---

## Implementation Plan

### Phase 1: Immediate Deprecation (Handover 0116 Alignment)

**Goal:** Remove 11 obsolete tools that use wrong data models or have no implementation.

**Timeline:** 1-2 days

**Steps:**

1. **Update `api/endpoints/mcp_http.py`** - Remove tool registrations

```python
# File: api/endpoints/mcp_http.py
# Lines: 707-780 (tool_map dictionary)

# REMOVE these lines:
❌ "spawn_agent": state.tool_accessor.spawn_agent,
❌ "list_agents": state.tool_accessor.list_agents,
❌ "get_agent_status": state.tool_accessor.get_agent_status,
❌ "update_agent": state.tool_accessor.update_agent,
❌ "retire_agent": state.tool_accessor.retire_agent,
❌ "ensure_agent": state.tool_accessor.ensure_agent,
❌ "agent_health": state.tool_accessor.agent_health,
❌ "discover_context": state.tool_accessor.discover_context,
❌ "get_file_context": state.tool_accessor.get_file_context,
❌ "search_context": state.tool_accessor.search_context,
❌ "get_context_summary": state.tool_accessor.get_context_summary,
```

2. **Update `api/endpoints/mcp_http.py`** - Remove tool descriptions

```python
# File: api/endpoints/mcp_http.py
# Lines: 133-675 (handle_tools_list function)

# REMOVE tool definitions for all 11 obsolete tools
```

3. **Mark methods as deprecated in `tool_accessor.py`**

```python
# File: src/giljo_mcp/tools/tool_accessor.py

async def spawn_agent(self, name: str, role: str, mission: str) -> dict[str, Any]:
    """
    DEPRECATED: Use spawn_agent_job() instead.
    
    This tool creates legacy Agent records. Handover 0116 migrates
    to MCPAgentJob model. This method will be removed in v3.2.0.
    """
    return {
        "error": "DEPRECATED",
        "message": "Use spawn_agent_job() instead. This tool creates legacy Agent records.",
        "replacement": "mcp__giljo-mcp__spawn_agent_job"
    }
```

4. **Update tests** - Mark as deprecated, add migration tests

```python
# File: tests/test_tool_accessor.py

@pytest.mark.deprecated
async def test_spawn_agent_deprecated():
    """Verify spawn_agent returns deprecation error"""
    result = await tool_accessor.spawn_agent("test", "implementer", "mission")
    assert result["error"] == "DEPRECATED"
    assert "spawn_agent_job" in result["replacement"]
```

5. **Update documentation**

Create `handovers/MCP_TOOL_DEPRECATION_0116.md`:

```markdown
# MCP Tool Deprecation Plan (Handover 0116 Alignment)

## Deprecated Tools (Removed in v3.2.0)

### Legacy Agent Model Tools
- spawn_agent → USE spawn_agent_job
- list_agents → USE get_pending_jobs
- get_agent_status → USE get_workflow_status
- update_agent → USE report_progress / complete_job
- retire_agent → Automatic via job lifecycle
- ensure_agent → Internal only
- agent_health → USE get_workflow_status

### Context Discovery Stubs
- discover_context → No replacement (not needed)
- get_file_context → No replacement (not needed)
- search_context → No replacement (not needed)
- get_context_summary → No replacement (not needed)

## Migration Guide

[Include code examples for each replacement]
```

### Phase 2: REST API Migration (2-3 days)

**Goal:** Move dashboard admin functions from MCP tools to REST API endpoints.

**Steps:**

1. **Create new REST endpoints** in `api/endpoints/admin.py`

```python
# File: api/endpoints/admin.py (NEW)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/projects")
async def list_projects_admin(
    tenant_key: str,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    """List projects (dashboard UI)"""
    # Move logic from tool_accessor.list_projects()
    ...

@router.get("/projects/{project_id}")
async def get_project_admin(
    project_id: str,
    tenant_key: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Get project details (dashboard UI)"""
    # Move logic from tool_accessor.get_project()
    ...

@router.patch("/projects/{project_id}/close")
async def close_project_admin(
    project_id: str,
    tenant_key: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Close project (dashboard UI)"""
    # Move logic from tool_accessor.close_project()
    ...

@router.get("/agent-templates")
async def list_templates_admin(
    tenant_key: str,
    session: AsyncSession = Depends(get_db_session)
):
    """List agent templates (template manager UI)"""
    # Move logic from tool_accessor.list_templates()
    ...

@router.post("/agent-templates")
async def create_template_admin(
    template_data: AgentTemplateCreate,
    tenant_key: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Create agent template (template manager UI)"""
    # Move logic from tool_accessor.create_template()
    ...

@router.patch("/agent-templates/{template_id}")
async def update_template_admin(
    template_id: str,
    template_data: AgentTemplateUpdate,
    tenant_key: str,
    session: AsyncSession = Depends(get_db_session)
):
    """Update agent template (template manager UI)"""
    # Move logic from tool_accessor.update_template()
    ...
```

2. **Update Vue.js frontend** to use REST API

```typescript
// File: frontend/src/api/projects.ts

export async function listProjects(tenantKey: string): Promise<Project[]> {
  // ❌ OLD: Call MCP tool via tool_accessor
  // const response = await callMCPTool('list_projects', { tenant_key: tenantKey })
  
  // ✅ NEW: Call REST API
  const response = await axios.get('/api/admin/projects', {
    params: { tenant_key: tenantKey }
  })
  return response.data
}
```

3. **Deprecate MCP tools** (same process as Phase 1)

4. **Update tests** for REST API endpoints

### Phase 3: Final Cleanup (1 day)

**Goal:** Remove deprecated code, finalize documentation.

**Steps:**

1. **Remove deprecated methods** from `tool_accessor.py`
2. **Remove tests** for deprecated tools
3. **Update MCP tool count** in README (40 → ~34 post-migration)
4. **Create migration guide** for any external integrations
5. **Announce changes** in CHANGELOG.md

---

## Technical Evidence

### File Locations

```
MCP Tool Registration:
══════════════════════════════════════════════════════════
api/endpoints/mcp_http.py            handle_tools_call() tool_map (40 tools)
api/endpoints/mcp_http.py            handle_tools_list() (40 tools, matches map)
api/endpoints/mcp_tools.py           HTTP wrapper (counts vary; use mcp_http as source of truth)

Tool Implementations:
══════════════════════════════════════════════════════════
src/giljo_mcp/tools/tool_accessor.py:577      spawn_agent (LEGACY)
src/giljo_mcp/tools/tool_accessor.py:603      list_agents (LEGACY)
src/giljo_mcp/tools/tool_accessor.py:660      get_agent_status (LEGACY)
src/giljo_mcp/tools/tool_accessor.py:1611     spawn_agent_job (CORRECT)
src/giljo_mcp/tools/orchestration.py          Orchestration tools

Database Models:
══════════════════════════════════════════════════════════
src/giljo_mcp/models.py                Agent (LEGACY 4-state)
src/giljo_mcp/models.py                MCPAgentJob (NEW 7-state)

Related Handovers:
══════════════════════════════════════════════════════════
handovers/0088_thin_client_architecture.md     context prioritization and orchestration
handovers/0113_unified_agent_state_system.md   7-state model
handovers/0116_agent_model_migration.md        Eliminate dual models
handovers/start_to_finish_agent_FLOW.md        Complete workflow
```

### Tool Catalog Evidence (current)

- tools/list returns 40 tools; matches tools/call mapping
- Current names:
  - `create_project`, `list_projects`, `get_project`, `switch_project`, `close_project`, `update_project_mission`
  - `get_orchestrator_instructions`
  - `send_message`, `receive_messages`, `acknowledge_message`, `list_messages`
  - `create_task`, `list_tasks`, `update_task`, `assign_task`, `complete_task`
  - `list_templates`, `get_template`, `create_template`, `update_template`
  - `health_check`
  - `get_pending_jobs`, `acknowledge_job`, `report_progress`, `get_next_instruction`, `complete_job`, `report_error`
  - `orchestrate_project`, `get_agent_mission`, `spawn_agent_job`, `get_workflow_status`
  - `create_successor_orchestrator`, `check_succession_status`
  - `setup_slash_commands`, `gil_import_productagents`, `gil_import_personalagents`, `gil_handover`
  - `gil_fetch`, `gil_activate`, `gil_launch`

### Database Schema Evidence

```sql
-- LEGACY TABLE (4-state model) - Used by obsolete tools
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('idle', 'active', 'completed', 'failed')),
    project_id UUID REFERENCES projects(id),
    mission TEXT,
    context_used INTEGER,
    created_at TIMESTAMP
);

-- NEW TABLE (7-state model) - Used by correct tools
CREATE TABLE mcp_agent_jobs (
    id UUID PRIMARY KEY,
    agent_type VARCHAR NOT NULL,
    agent_name VARCHAR,
    status VARCHAR NOT NULL CHECK (status IN (
        'waiting',      -- Created, not claimed
        'active',       -- Claimed, preparing
        'working',      -- Executing mission
        'completed',    -- Finished successfully
        'failed',       -- Encountered error
        'cancelled',    -- User cancelled
        'decommissioned' -- Cleaned up (Handover 0073)
    )),
    mission TEXT NOT NULL,
    project_id UUID REFERENCES projects(id),
    spawned_by UUID REFERENCES mcp_agent_jobs(id),  -- Orchestrator tracking
    progress_percentage INTEGER DEFAULT 0,
    failure_reason TEXT,
    output TEXT,
    tenant_key VARCHAR NOT NULL,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    decommissioned_at TIMESTAMP
);
```

### Tool Call Flow Evidence

```python
# STAGING PHASE - Orchestrator terminal calls:
# ════════════════════════════════════════════════════════

# 1. Health check
response = await mcp_call("health_check")
# Returns: {"status": "healthy", "server": "giljo-mcp", "version": "3.1.0"}

# 2. Get context for mission creation
context = await mcp_call("get_orchestrator_instructions", {
    "orchestrator_id": "orch-abc-123",
    "tenant_key": "tenant_xyz"
})
# Returns: {
#   "project_description": "User requirements...",
#   "product_vision": "Product docs...",
#   "agent_templates": [...],
#   "condensed": True,
#   "token_count": 2000
# }

# 3. Create mission plan (local AI processing)
mission_plan = analyze_and_create_mission(context)

# 4. Persist mission to database
await mcp_call("update_project_mission", {
    "project_id": "proj-456",
    "mission": mission_plan,
    "tenant_key": "tenant_xyz"
})

# 5. Spawn agent jobs
for agent_spec in selected_agents:
    result = await mcp_call("spawn_agent_job", {
        "agent_type": agent_spec.type,
        "agent_name": agent_spec.name,
        "mission": agent_spec.mission_fragment,
        "project_id": "proj-456",
        "tenant_key": "tenant_xyz"
    })
    # Returns: {
    #   "agent_job_id": "job-789",
    #   "thin_prompt": "You are Implementer #job-789...",
    #   "prompt_tokens": 50,
    #   "mission_tokens": 2000
    # }

# EXECUTION PHASE - Individual agent terminal calls:
# ════════════════════════════════════════════════════════

# 1. Find my job
jobs = await mcp_call("get_pending_jobs", {
    "agent_type": "implementer",
    "tenant_key": "tenant_xyz"
})

# 2. Claim job
await mcp_call("acknowledge_job", {
    "agent_job_id": "job-789",
    "tenant_key": "tenant_xyz"
})

# 3. Fetch mission
mission = await mcp_call("get_agent_mission", {
    "agent_job_id": "job-789",
    "tenant_key": "tenant_xyz"
})

# 4. Execute work (local file operations, code changes, etc.)
perform_implementation(mission)

# 5. Report progress
await mcp_call("report_progress", {
    "agent_job_id": "job-789",
    "progress_percentage": 50,
    "message": "Implemented 3 of 6 endpoints",
    "tenant_key": "tenant_xyz"
})

# 6. Complete job
await mcp_call("complete_job", {
    "agent_job_id": "job-789",
    "output": "Implemented auth endpoints...",
    "tenant_key": "tenant_xyz"
})
```

---

## Appendix: Complete Tool Inventory (current)

### Tools to REMOVE (legacy HTTP exposure already removed)

```
❌ Legacy Agent Model (7):
   - spawn_agent
   - list_agents
   - get_agent_status
   - update_agent
   - retire_agent
   - ensure_agent
   - agent_health

❌ Context Discovery Stubs (4):
   - discover_context
   - get_file_context
   - search_context
   - get_context_summary
```

### Tools to MIGRATE to REST API (6 total)

```
⚠️  Dashboard Admin Functions:
   - list_projects
   - get_project
   - close_project
   - list_templates
   - create_template
   - update_template
```

### Tools to KEEP (target ~34 core tools after migration)

```
✅ Core Workflow (10):
   - get_orchestrator_instructions
   - spawn_agent_job
   - update_project_mission
   - orchestrate_project
   - get_pending_jobs
   - acknowledge_job
   - get_agent_mission
   - report_progress
   - complete_job
   - report_error

✅ Communication (4):
   - send_message
   - receive_messages
   - acknowledge_message
   - list_messages

✅ Project Context (4):
   - create_project
   - switch_project
   - get_workflow_status
   - health_check

✅ Succession (2):
   - create_successor_orchestrator
   - check_succession_status

✅ Slash Commands (4):
   - setup_slash_commands
   - gil_import_productagents
   - gil_import_personalagents
   - gil_handover

✅ Task Management (5):
   - create_task
   - list_tasks
   - update_task
   - assign_task
   - complete_task

✅ Template Access (2):
   - get_template (read-only for agents)
   - [Note: create/update should migrate to REST API]

✅ Other Essential (4):
   - get_next_instruction (if still used)
   - [Additional tools pending review]
```

---

## Conclusion (updated)

**Summary:**
- HTTP MCP currently exposes 40 tools (validated via tools/list)
- Legacy Agent‑model tools are not exposed via HTTP MCP; retire remaining legacy code paths
- 6 admin/dashboard tools should migrate to REST API
- Target steady state: ~34 core MCP tools for terminal agent coordination

**Alignment with Handovers:**
- ✅ Handover 0116: Eliminate dual-model confusion (Agent vs MCPAgentJob)
- ✅ Handover 0088: Thin client architecture (mission via MCP, not context discovery)
- ✅ Handover 0113: 7-state MCPAgentJob lifecycle
- ✅ Handover 0073: Agent decommissioning and closeout

**Next Steps:**
1. Confirm retirement of legacy agent provider (src/giljo_mcp/tools/agent.py) or mark internal-only
2. Migrate 6 admin tools to REST API and remove from MCP catalog
3. Update tests and docs to reflect 34 core MCP tools
4. Keep mcp_http tool list and map in lockstep (already fixed)

---

**Document End**
