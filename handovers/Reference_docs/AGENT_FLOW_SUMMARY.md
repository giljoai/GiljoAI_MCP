# GiljoAI Agent Flow - Quick Reference

**Last Verified: 2026-02-28**

**For full details, see:** `start_to_finish_agent_FLOW.md` (same directory)

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GiljoAI MCP Server                                │
│  ┌──────────────────────┐    ┌───────┐    ┌──────────────────────────────┐ │
│  │ Server Components    │◄──►│  MCP  │◄──►│ Orchestration Features       │ │
│  │ • Front end (Vue 3)  │    │ Core  │    │ • Project staging            │ │
│  │ • Back end (FastAPI) │    │       │    │ • Project launch             │ │
│  │ • PostgresDB         │    │       │    │ • Prompt templates           │ │
│  │ • Scripts            │    │       │    │ • Agent message hub          │ │
│  │ • MCP command host   │    │       │    │ • Job assignment             │ │
│  └──────────────────────┘    └───────┘    └──────────────────────────────┘ │
│             ▲                                          ▲                    │
│  ┌──────────┴──────────┐              ┌────────────────┴─────────────────┐ │
│  │ Management Features │              │ MCP Commands & Message Hub       │ │
│  │ • Product mgmt      │              │ • Send/receive messages          │ │
│  │ • Project mgmt      │              │ • Check status                   │ │
│  │ • Task mgmt         │              │ • Write documentation            │ │
│  │ • Agent templates   │              │ • Fetch instructions             │ │
│  │ • Context mgmt      │              │ • Inter-agent communications     │ │
│  └─────────────────────┘              └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
           │                                         │
           │ WebSocket/HTTP                          │ MCP JSON-RPC 2.0
           ▼                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client PC                                       │
│  ┌──────────────┐    ┌──────────────────────────────────────────────────┐  │
│  │   Browser    │    │              Terminal Agents                      │  │
│  │   (Web UI)   │    │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │  │
│  └──────┬───────┘    │  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │  ...  │  │
│         │            │  │(Orchestr)│  │(Implement)│  │(Tester)  │       │  │
│         │            │  └────┬─────┘  └────┬─────┘  └────┬─────┘       │  │
│         │            └───────┼─────────────┼─────────────┼─────────────┘  │
│         │                    │             │             │                 │
│         ▼                    ▼             ▼             ▼                 │
│  ┌──────────────┐    ┌─────────────────────────────────────────────────┐  │
│  │     User     │    │              Project Files / Repo                │  │
│  └──────────────┘    │         (Local filesystem agents work on)        │  │
│                      └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Architecture Components

**GiljoAI MCP Server** (Central Hub):
- **Server Components**: Vue 3 frontend, FastAPI backend, PostgreSQL database, MCP command host
- **Management Features**: Product/project/task management, agent templates, context configuration
- **Orchestration Features**: Project staging & launch, prompt templates, agent message hub, job assignment

**Communication Channels**:
- **Browser ↔ Server**: WebSocket for real-time UI updates, HTTP REST for CRUD operations
- **Agents ↔ Server**: MCP JSON-RPC 2.0 protocol for all agent commands and messaging

**Client PC** (User's Machine):
- **Browser**: Web UI for project management, monitoring, and agent launch
- **Terminal Agents**: Multiple CLI instances (orchestrator + specialist agents) executing work
- **Project Files/Repo**: Local codebase that agents read/modify

### Data Flow

1. **User** manages projects via **Browser** → **Web UI**
2. **Web UI** communicates with **MCP Server** (WebSocket + REST)
3. **User** copies agent prompts, launches **Terminal Agents**
4. **Terminal Agents** communicate with **MCP Server** via MCP protocol
5. **Terminal Agents** coordinate via **Message Hub** on server
6. **Terminal Agents** execute work on **Project Files/Repo**

---

## Key Terminology

| Term | Type | Description |
|------|------|-------------|
| `description` | User Input | Human-written requirements (Product.description, Project.description) |
| `mission` | AI Output | Orchestrator-generated plan (Project.mission, MCPAgentJob.mission) |

### Database Status Values (6 canonical states, post-0491)
```
waiting → working → complete/blocked/silent/decommissioned
```
**Note:** API accepts aliases (`pending`→`waiting`, `active`→`working`, `completed`→`complete`) for compatibility. The `failed` and `cancelled` statuses were removed in the 0491 migration.

---

## Two Types of Agent Spawning

### Type 1: MCP Server Spawning (Database Records)
- **When:** During staging (Task 5)
- **What:** Creates database record + UI agent card
- **Tool:** `spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key)`
- **Creates:** Job ticket with status="waiting"

### Type 2: CLI Native Subagent Spawning (Execution)
- **When:** Implementation phase (Claude Code Mode ON only)
- **What:** Invokes actual Claude Code subagent from `.md` template
- **How:** Orchestrator reads `~/.claude/agents/{role}.md`, spawns subagent
- **Agent Action:** Calls `get_agent_mission(job_id, tenant_key)` to fetch mission

**Relationship:** Type 1 creates the "digital twin" (database record). Type 2 creates the "real agent" (executing instance). Bridge: `job_id` + `get_agent_mission()`.

---

## Orchestrator 5-Task Staging Workflow

```
TASK 1: health_check()              → Verify MCP connection
TASK 2: get_orchestrator_instructions(orchestrator_id, tenant_key)
                                    → Fetch context + requirements
TASK 3: Create mission plan         → Synthesize from context
TASK 4: update_project_mission()    → Persist to Project.mission
TASK 5: spawn_agent_job() × N       → Create agent database records
```

---

## Core MCP Tools

### Orchestration Tools
| Tool | Purpose |
|------|---------|
| `health_check()` | Verify MCP server connectivity |
| `get_orchestrator_instructions(orch_id, tenant_key)` | Fetch staging context (~6K tokens) |
| `get_agent_mission(job_id, tenant_key)` | Fetch agent-specific mission |
| `spawn_agent_job(...)` | Create agent job (Type 1 spawn) |
| `update_project_mission(project_id, mission)` | Persist orchestrator's plan |
| `get_available_agents(tenant_key)` | Dynamic agent discovery |
| `get_workflow_status(project_id, tenant_key)` | Monitor all agents |

### Coordination Tools
| Tool | Purpose |
|------|---------|
| `get_pending_jobs(agent_type, tenant_key)` | Find assigned work |
| `update_job_status(job_id, status, tenant_key)` | Update job status |
| `report_progress(job_id, progress)` | Update progress % |
| `complete_job(job_id, result)` | Finish job (working→complete) |
| `report_error(job_id, error)` | Report blocking issues |
| `get_next_instruction(job_id, agent_type, tenant_key)` | Check for updates |

### Messaging, Signals & Instructions (Three Categories)

**See:** [Messaging Contract](../../docs/architecture/messaging_contract.md) for full documentation.

| Category | Purpose | Store | Tools |
|----------|---------|-------|-------|
| **MESSAGES** | Agent-to-agent communication | `messages` table + JSONB mirror | `send_message()`, `receive_messages()`, `acknowledge_message()` |
| **SIGNALS** | Job status & progress | `MCPAgentJob` table | `update_job_status()`, `report_progress()`, `complete_job()` |
| **INSTRUCTIONS** | Mission/config fetch | `MCPAgentJob.mission` | `get_agent_mission()`, `get_orchestrator_instructions()` |

**Counter Logic** (via WebSocket events):
- `message:sent` → Increment sender's "Sent" counter
- `message:received` → Increment recipient's "Waiting" counter
- `message:acknowledged` → Decrement "Waiting", increment "Read"

**Note:** JSONB (`MCPAgentJob.messages`) is a **cache/mirror** for counter persistence, not a separate messaging system.

---

## Execution Modes

### Claude Code Mode (Toggle ON)
- Single terminal
- Only orchestrator prompt active
- Orchestrator spawns native subagents from `.md` templates
- Subagents fetch mission via `get_agent_mission()`

### Multi-Terminal Mode (Toggle OFF - Default)
- Multiple terminals (one per agent)
- All Copy Prompt buttons active
- Each agent launched manually
- Each calls `get_agent_mission()` independently

---

## Agent Execution Protocol

1. **Claim Job:** `get_pending_jobs()` → `update_job_status(job_id, "working")`
2. **Fetch Mission:** `get_agent_mission(job_id, tenant_key)`
3. **Execute Work:** Perform role-specific tasks
4. **Report Progress:** `report_progress(job_id, progress%)`
5. **Complete:** `complete_job(job_id, result)`

---

## WebSocket Events (Real-time UI)

| Event | UI Update |
|-------|-----------|
| `job:status_changed` | Agent card badge |
| `job:progress_updated` | Progress bar |
| `message:new` | Message center count |
| `project:mission_updated` | Mission window |
| `agent:spawned` | New agent card |

---

## Thin Client Architecture

- **Before:** 3,500 token prompts embedded in requests
- **After:** 450-550 token thin prompts
- **How:** Mission stored in database, fetched via MCP tools
- **Result:** 70% token reduction

---

## Context Configuration

User configurable in: My Settings → Context Configuration
- Enabled (toggle: true): Category included with configured depth
- Disabled (toggle: false): Category excluded entirely

---

## Key Files & Locations

| Component | Location |
|-----------|----------|
| Tool Accessor (all MCP tools) | `src/giljo_mcp/tools/tool_accessor.py` |
| Agent Coordination | `src/giljo_mcp/tools/agent_coordination.py` |
| Agent Tools | `src/giljo_mcp/tools/agent.py` |
| Project Tools | `src/giljo_mcp/tools/project.py` |
| Thin Prompt Generator | `src/giljo_mcp/thin_prompt_generator.py` |
| Agent Templates | `~/.claude/agents/` or `.claude/agents/` |

---

## Quick Troubleshooting

| Issue | Check |
|-------|-------|
| Agent not receiving mission | Verify `job_id` passed correctly, call `get_agent_mission()` |
| Status not updating | Check WebSocket connection, verify status value is canonical |
| Orchestrator not spawning | Ensure project activated, check for existing active orchestrator |
| Template not found | Verify export completed, check `~/.claude/agents/` directory |

---

## Multi-Tenant Isolation

All queries filtered by `tenant_key` at 6 layers:
- Database
- MCP Tools
- API
- Job Manager
- Message Queue
- WebSocket

Zero cross-tenant data leakage possible.

---

## Visual Workflow Reference (Slide Descriptions)

*Source: GiljoAI MCP Server Workflows presentation*

### Slide 1: Title
- **GiljoAI MCP Server - Workflows**

### Slide 2: Overall Operational Architecture
- GiljoAI MCP Server can be deployed on LAN, WAN, or hosted
- Backend and Database connect to the MCP Server
- Server exposes two interfaces: Web Frontend Visualization + MCP over HTTP Server
- Developer PC connects via Browser (to Web Frontend) and MCP-enabled Agentic Coding tools via CLI/Terminal (to MCP Server)

### Slide 3: Multiuser Architecture
- Single GiljoAI MCP Server (LAN/WAN/Hosted) with Backend and Database
- Multiple Developer PCs can connect simultaneously
- Each Developer PC has: Browser + MCP-enabled Agentic Coding tools (CLI/Terminal)
- All connect to the same Web Frontend and MCP over HTTP Server

### Slide 4: Server Application Layers
**Left side (Infrastructure):**
- OS agnostic Server
- Public IP based application interaction, not localhost for users
- Localhost interaction only for system functions between Backend, Frontend and PostgreSQL
- MCP over HTTP, not STDIO
- PostgreSQL Database
- Single Org architecture
- Tenant management (Users, with an Admin)
- API key and bearer key tenant separation
- Task, Product and Project management
- Jobs management

**Right side (Features):**
- MCP integration setup tools (Claude CLI, Codex CLI, Gemini CLI)
- Slash Command Setup tools
- Agent Template import setup tools (Claude CLI subagent feature)
- Agent Template management, creation and activation/enablement
- Serena MCP integration for prompt modification and context injection
- Github integration
- MCP message center for working Agents with Developer visualization
- Product, Project and Jobs context management with priority assignment
- 360 memory management, mini git, lifecycle, github tracking

### Slide 5: Installation and Setup
1. Download Application from Github or website
2. Install via `python install.py`
3. OS agnostic
4. IP address binding configuration for frontend
5. Database check requires PostgreSQL
6. Developer provides credentials to DB
7. Dependency downloads from requirements.txt
8. Required Database configuration setup for first run
9. Agent default template creation
10. 360 memory default template creation
11. Instructions for application launch

### Slide 6: First Run Workflow
1. Browse to `http://{ip_address}:7274`
2. Set up Admin user
3. Creates Tenant for Admin user
4. Welcome page

### Slide 7: Application Setup Overview
1. Navigate to user settings
2. MCP tool prompt for attaching Terminal CLI tool (Claude, Codex, Gemini)
3. Prompt copy to install slash commands
4. Prompt copy for installing agents (Claude Code CLI)
5. Enable Serena MCP and custom configure
6. Github + 360 memory activate
7. Context toggle/depth settings if desired
8. Invite more users as individual tenants
9. Watch tutorial or instructions (not created yet)
10. Use application

### Slide 8: Application Workflow Overview
**Constraint:** Only one product can be activated in a tenant; Only one project can be activated per product

**Main Flow:**
1. Create Product (Used as Context Source) → Activate Product
2. Create Project (Used as Context Source) → Activate Project
3. Application Creates Job (Used as Context Source) → Stage Project in Job → Activate Job
4. Interact with Job and Agents
5. Complete and Close Job → Deactivate Project

**Alternative Task Flow:**
1. Create Tasks → Organize Tasks → Convert Task to Project
2. Project resides under currently active product

### Slide 9: Product Workflow Overview
**Note:** Journey is actively saved in cache during session; if user navigates back and forth during product Add, information repopulates. Only one product can be activated in a tenant.

**Flow:**
1. Create Product → Product name and description (Context Source)
2. Project path (optional, future use) → Vision Document Upload
3. Vision document chunking (Context Source) → Tech stack fields (Context Source)
4. Additional product fields (Context Source) → Agent Behavior such as test methodology (Context Source)
5. Agent execution methodologies (Context Source) → Save product (Creates Product ID)
6. Sets up 360 memory for lifecycle and initial first prompt
7. Product added in Inactive state / appears as product card in application

### Slide 10: Product Activation Workflow
**Constraint:** Only one product can be activated in a tenant

**Flow:**
1. Existing product and product card → Product gets activated
2. Check: Another product active?
   - **No:** New Product gets activated
   - **Yes:** Warning that other product will be deactivated → Deactivates other product → Deactivates any active projects → New Product gets activated
3. Badge appears on product card (Active)
4. Badge appears on Header bar in application

### Slide 11: Project Creation Workflow
**Constraint:** Only one project can be active under an activated product at any given time. Only one product can be activated in any tenant.

**Flow:**
1. Create Project → Project Name → Project Description (Context Source)
2. Orchestrator generated mission shows here (if exists) - *Note: Same Vue component for editing existing projects*
3. Context Budget → Save Project → Project appears on project list
4. Project is default inactive

**Note on Context Budget:** Value to be determined for its use - suggested as informative value inserted into orchestrator launch prompt as instructions to define context space in tokens before session expires.

### Slide 12: Project Modification Overview
**Constraint:** Only one project can be active under an activated product at any given time. Only one product can be activated in any tenant.

**Editing:**
- Project can be edited → Opens same Vue component as [+ Create Project] for editing

**Project States:**
- Project can be: inactive, deleted, canceled, activated, and completed
- Deleted projects are soft deleted with 10 days expiry
- Cancelled, Completed and Deactivated projects keep all data (Mission, Agents, Messages, etc.) for future activation or re-activation
- System keeps unique link created but de-couples from [Launch project] button and jobs navigation on left sidebar with any of these status changes

**Activation Flow:**
1. Project gets activated → Already active project?
   - **No:** Dynamic link is created for Jobs page → Navigation to jobs page from project list [Launch Project] button or sidebar jobs link
   - **Yes:** Current active project is deactivated → New Project gets activated → Dynamic link created

### Slide 13: Task Workflow Overview
**Note:** Tasks created with active product get NULL tag and show up for all products or no products active.

**Flow:**
1. Create Task from web application (unique to tenant) → Task name → Task Settings
2. Status / Priority / Description / Convert / date created
3. Tasks created with no active product get NULL tag
4. NULL tagged tasks show up when no product is activated or when any product is activated, but still unique to tenant
5. Tasks can only be converted to projects when a product is activated
6. Tasks converted to projects are inactive by default
7. Shows on Task List → Tasks can be Completed, deleted, and...

**Alternative Terminal Flow:**
- Create Task slash command in terminal → Dumps into task list with randomized Name and user written/pasted content → Default settings

