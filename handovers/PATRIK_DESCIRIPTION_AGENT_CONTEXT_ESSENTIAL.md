---
**Document Type:** Essential Context for AI Coding Agents
**Purpose:** Mandatory reading for all agents working on GiljoAI MCP
**Last Updated:** 2025-11-07
**Status:** ✅ Required Context
---

# GiljoAI MCP: Essential Agent Context

## What Is This System?

**GiljoAI MCP** is a web-based orchestration server that helps developers using **terminal-based AI coding tools** (Claude Code, Codex, Gemini) manage complex software projects through intelligent context management, agent coordination, and visual workflow tracking.

**Think of it as:** A control tower for AI-assisted development. You build on your laptop using CLI tools, but GiljoAI MCP running as a web server helps you organize context, coordinate multiple agents, and track progress without losing your place.

---

## The Core Problem Being Solved

When developers use AI coding tools in terminals, they face three major challenges:

1. **Context Chaos**: Tracking product vision, tech stack, dependencies, architectural decisions across multiple conversations
2. **Idea Loss**: Good ideas pop up during coding but get lost when you're in flow state
3. **Agent Coordination**: When using multiple specialized agents (implementer, tester, documenter), coordinating their work becomes manual and error-prone

**GiljoAI MCP solves this** by providing structured context management with a visual dashboard while keeping your actual development work in familiar terminal tools.

---

## Architecture: Local Development + Remote Coordination

```
YOUR LAPTOP (Local)              REMOTE SERVER (or localhost)
─────────────────────            ────────────────────────────
Claude Code Terminal    ←HTTP→   GiljoAI MCP Server :7272
(paste prompts)                      │
(write code)                         ├─► PostgreSQL Database
(uses MCP tools)                     ├─► Web Dashboard (Vue.js)
                                     └─► Agent Job Tracking
```

**Key Insight**: You code locally in your terminal. The MCP server runs remotely (or on localhost) and provides:
- Context organization via web forms
- Pre-generated prompts you copy/paste
- Agent coordination via MCP tools
- Visual progress tracking
- Communication hub between agents

**Tennancy**
All users accounts operate as tennants separated from other users, MCP server connections are API token enabled to ensure Agentic coding tool only communiates in the context of a tennnat.

s
---

## Core Concepts (The Hierarchy)

### 1. **Product** (Top Level)
The software product you're building. Think: "E-commerce Platform" or "Task Management App"

**Contains:**
- Product vision documents (architecture, specs, standards)
- Tech stack definitions
- Dependencies and tools
- Multiple projects (work initiatives)
- Tasks (quick ideas to address later)

**Rule:** Only ONE active product per developer at a time (enforced at database level)

---

### 2. **Project** (Work Initiative)
A specific chunk of work under a product. Think: "Add user authentication" or "Implement shopping cart"

**Two Critical Fields:**
- **`description`** (human-written): What YOU want to accomplish in your own words
- **`mission`** (AI-generated): What the ORCHESTRATOR creates after analyzing context

**Rule:** Only ONE active project per product at a time

**States:** draft → active → paused → completed → cancelled

---

### 3. **Orchestrator** (The Coordinator)
A special agent that acts as project manager. When you activate a project:

1. Reads product vision, tech stack, your project description
2. Applies field priorities to optimize tokens (up to 25% reduction achieved)
3. Creates a condensed mission plan
4. Selects appropriate agents from your template pool (max 8 roles)
5. Spawns agent jobs with specific assignments
6. Coordinates agent communication during execution

**Think of it as:** Your AI project manager that translates high-level goals into actionable agent assignments.

---

### 4. **Agents** (Specialized Workers)
Pre-configured AI assistants with specific roles. Six defaults seeded per user:

- **Orchestrator**: Coordinates the team - Highly restricted to modification, can break application if edited!!
- **Implementer**: Writes code
- **Tester**: Validates functionality
- **Analyzer**: Reviews architecture
- **Reviewer**: Code quality checks
- **Documenter**: Creates documentation

**Key Features:**
- Customizable via template editor (Monaco editor in dashboard), except orhcestrator (only tunable via admin settings, at your risk!)
- Priority cascade: Product-specific → Tenant-specific → System default
- Exported to CLI tools (Claude Code, Codex, Gemini)
- Communicate via MCP message hub

**Context Budget Warning:** Limit active agents types to 8 maximum (each template consumes tokens), unlimited duplications if needed.

---

### 5. **Jobs** (Agent Execution)
When an agent starts working, it creates a job tracked by the system.

**Job Lifecycle:**
```
waiting → working → completed →  /failed/blocked
```

**Tracked Data:**
- Agent assignment
- Progress percentage
- Status updates
- Messages sent/received
- Execution results

**Communication:** Agents talk via MCP message hub (visible in dashboard)

---

### 6. **Tasks** (Quick Capture)
Lightweight notes for ideas that pop up during coding.

**Purpose:** Punt ideas to a list without losing focus, then convert to projects later.

**Two Creation Methods:**
- **MCP tools**: During terminal conversations: `create_task("Research Redis caching")`
- **Dashboard**: Manual entry via web interface

**Conversion:** Tasks can become projects (name → title, description → description)

**Scope:** Tasks belong to active product, or NULL if no product active (visible everywhere until assigned)

---

## The User Workflow (Simplified)

### Phase 1: Setup (One-Time)
1. **Install** GiljoAI MCP server (`python install.py`)
2. **Create account** → 6 default agent templates auto-seeded
3. **Export agents** → My Settings → Integrations → Copy command
4. **Attach MCP server** pre made copy commands for claude, codex and gemini, APIkey enabled for tennancy.
5. **Agents registered** → Templates available in `~/.claude/agents/`

---

### Phase 2: Create Context Structure
1. **Create Product** → Define vision, tech stack, dependencies
2. **Upload vision docs** → Architecture specs, API docs, coding standards
3.  **context loading** → Build out product with key data sets, coding language, front end, back end etc.
4. **Create Project** → Write what you want to accomplish (project description)

---

### Phase 3: Stage Project (Preparation)
1. **Activate Project** → Click "Stage Project" button
2. **Dashboard shows Launch Tab** with three windows:
   - **Project Description** (your human-written goals)
   - **Orchestrator Created Mission** (empty at start)
   - **Agent Team** Filled with only orchestrator at start.

3. **Copy orchestrator prompt** → Paste in terminal
4. **Orchestrator runs** (in your terminal):
   - Calls `get_orchestrator_instructions()` via MCP
   - Reads product vision, project description, context
   - complies with users context prioritization configurator in my settings(can be left at default)
   - Creates condensed mission (displayed in dashboard)
   - Selects agents (cards appear live in dashboard), selecting agents from active tempaltes in template manager.
   - Calls `spawn_agent_job()` for each agent (creates jobs on server)

5. **Review mission** → Check token estimates, agent selections
6. **Proceed or cancel** → If happy, move to Implementation Tab

---

### Phase 4: Execute Work (Implementation)
**Two modes:**

**A) Claude Code (Single Terminal):**
- Copy orchestrator execution prompt
- Paste in same terminal window
- Claude spawns sub-agents automatically via native capabilities
- All agents work in one terminal session, uses custom instructions in imported agent profile files.

**B) Codex/Gemini (Claude optional to work this way) (Multi-Terminal):**
- Copy each agent's launch prompt individually
- Paste in separate terminal windows (one per agent)
- Each agent runs independently
- User must nudge terminals to check messages

**What Agents Do:**
```
1. Call get_pending_jobs() → Find their assigned work
2. Call acknowledge_job() → Claim the job
3. Call get_agent_mission() → Fetch detailed instructions
4. Execute work locally → Write code, run tests, etc.
5. Call report_progress() → Update dashboard (live updates)
6. Call send_message() → Coordinate with other agents
7. Call complete_job() → Mark finished
```

**Communication:** Agents send messages via MCP hub, visible in dashboard message pane

---

### Phase 5: Close Out Project
1. **All agents complete** → Orchestrator detects completion
2. **Closeout workflow** → Git commits, documentation, cleanup
3. **Project summary** → Final report generated
4. **Agents decommissioned** → Jobs marked complete
5. **Historical record** → Full audit trail preserved

---

## Tasks: The "Punt" Feature

**Problem:** You're coding and a great idea pops up, but addressing it now would derail your focus.

**Solution:** Punt it to the task list.

**From Terminal (Recommended):**
```python
# During conversation with Claude Code:
"Can you create a task for researching Redis caching?"
# Agent calls: create_task(title="Research Redis", description="...")
```

**From Dashboard:**
Click "+ New Task" button, enter details, save.

**Later:**
- Review task list during planning sessions
- Convert promising tasks to full projects
- Tasks mature into projects without data loss

**Workflow:** Idea → Task → (Review) → Project → Execution

---

## Technical Details for Agents

### MCP Tools You'll Use

**Orchestrator Tools:**
- `get_orchestrator_instructions(orchestrator_id, tenant_key)` → Fetch staging context
- `spawn_agent_job(agent_type, mission, project_id, tenant_key)` → Create sub-agent jobs
- `update_project_mission(project_id, mission, tenant_key)` → Save mission to database

**Agent Execution Tools:**
- `get_pending_jobs(agent_type, tenant_key)` → Find your work
- `acknowledge_job(job_id, tenant_key)` → Claim job
- `get_agent_mission(job_id, tenant_key)` → Fetch detailed mission (~10 line prompt, ~2000 token mission)
- `report_progress(job_id, percent, message, tenant_key)` → Update dashboard
- `complete_job(job_id, output, tenant_key)` → Mark finished
- `report_error(job_id, error, severity, tenant_key)` → Report failures

**Communication Tools:**
- `send_message(from_agent, to_agent, content, tenant_key)` → Inter-agent messaging
- `receive_messages(agent_id, tenant_key)` → Check inbox
- `list_messages(agent_id, tenant_key)` → Message history

**Health Check:**
- `health_check()` → Verify MCP connection (always call first)

---

### Database Field Naming (CRITICAL)

**User Input = "description"**
**AI Output = "mission"**

| Field | Who Fills It | Example |
|-------|--------------|---------|
| `Product.description` | Human (form) | "Multi-tenant MCP server for agent orchestration" |
| `Project.description` | Human (form) | "Add JWT authentication" |
| `Project.mission` | Orchestrator (AI) | "Implement JWT auth with RS256, protect 8 endpoints, add rate limiting..." |
| `MCPAgentJob.mission` | Orchestrator (AI) | "backend-tester: Test authentication endpoints with invalid tokens..." |
| `Task.description` | Human (form/MCP) | "Research Redis caching strategies" |

**DO NOT:**
- ❌ Call `update_project_mission()` with user input (that's description)
- ❌ Confuse `Task.description` with `Project.mission`
- ❌ Use "mission" parameter when accepting user requirements

---

### Multi-Tenant Isolation

**Every operation is tenant-scoped.** All database queries filter by `tenant_key`:

```python
# Example: Finding agent jobs
jobs = session.query(MCPAgentJob).filter(
    MCPAgentJob.tenant_key == tenant_key,
    MCPAgentJob.agent_type == "implementer"
).all()
```

**Why:** Supports multi-user operation and future SaaS deployment.

---

### Context Prioritization and Orchestrator Efficiency

The orchestrator achieves massive token savings through:

1. **Field Priorities**: Only include high-priority product fields in missions
2. **Vision Chunking**: Break large docs into smaller chunks, use only relevant sections
3. **Smart Selection**: Select only necessary agents based on capabilities
4. **Thin Prompts**: Agents get 10-line prompts, fetch full mission via MCP (~2000 tokens)
5. **Template Cascade**: Efficient loading without redundant database hits

**Target:** Claude Code's 25K token input limit (prompts stay well within budget)

---

### Agent Communication Protocol

**Message Types:**
- **Direct**: Agent → Specific Agent
- **Broadcast**: Agent → All Agents
- **Orchestrator Directive**: Orchestrator → Sub-Agent

**Storage:** `agent_communication_queue` table (JSONB messages)

**Best Practice:** All coordination through orchestrator. Sub-agents report to orchestrator, orchestrator broadcasts instructions.

---

## Active Development Notes

### What Works Today ✅
- Product/project/task CRUD operations
- Agent template system with 3-tier caching
- Template export (Claude Code, Codex, Gemini)
- Project activation and orchestrator staging
- Agent job lifecycle management
- MCP tool suite (14 tools verified functional)
- WebSocket real-time updates
- Message communication hub
- Token estimation API
- Field priority configuration
- Project closeout workflow

### Known Limitations ⚠️
- **No automation**: User must manually nudge agent terminals to read messages
- **Claude Code advantage**: Native sub-agent spawning (single terminal)
- **Codex/Gemini**: Requires multi-terminal setup (manual prompt pasting)
- **Message checking**: Agents must be prompted to check MCP message hub

### Future Considerations 🔮
- **Slash commands**: Quick task creation from terminal (not implemented yet)
- **Terminal injection**: Automated message delivery to active terminals
- **Embedded terminal**: Build terminal into dashboard for full automation
- **Mini LLM orchestrator**: CPU/GPU micro-LLM to trigger agents automatically
- **Collaboration**: Multiple developers on same product (foundation exists, not implemented)

---

## File Locations (Critical Paths)

**Backend Core:**
- `src/giljo_mcp/tools/orchestration.py` → Orchestrator MCP tools
- `src/giljo_mcp/tools/agent_coordination.py` → Agent execution tools
- `src/giljo_mcp/mission_planner.py` → Mission generation (context prioritization and orchestration)
- `src/giljo_mcp/agent_selector.py` → Smart agent selection
- `src/giljo_mcp/template_seeder.py` → Default template definitions

**API Endpoints:**
- `api/endpoints/projects.py` → Project activation (line 702: activate endpoint)
- `api/endpoints/agent_jobs.py` → Job management REST API
- `api/endpoints/downloads.py` → Template export and download tokens
- `api/endpoints/auth.py` → User creation and template seeding (line 910)

**Database Models:**
- `src/giljo_mcp/models.py` → PostgreSQL schema definitions
- `MCPAgentJob` → New 7-state job model (correct)
- `Agent` → Legacy 4-state model (DEPRECATED - do not use)

**Frontend:**
- `frontend/src/components/LaunchTab.vue` → Project staging UI
- `frontend/src/components/JobsTab.vue` → Agent execution tracking
- `frontend/src/components/TemplateManager.vue` → Agent template editor

---

## Quick Reference: Terminology

| Term | Definition |
|------|------------|
| **Product** | Top-level organizational unit (the software you're building) |
| **Project** | Work initiative under a product (e.g., "Add auth system") |
| **Task** | Quick note/idea, can convert to project later |
| **Orchestrator** | Special agent that coordinates the team |
| **Agent** | Specialized AI assistant (implementer, tester, etc.) |
| **Job** | Agent execution instance tracked by system |
| **Mission** | AI-generated work plan (condensed, optimized) |
| **Description** | Human-written goals/requirements |
| **Template** | Agent configuration (prompt, behavior, tools) |
| **Tenant** | User isolation boundary (multi-tenant architecture) |
| **MCP** | Model Context Protocol (communication layer) |
| **Thin Client** | 10-line prompts + MCP mission fetch (efficient context usage) |

---

## For Agents Working on This Codebase

**When implementing features:**

1. **Always filter by tenant_key** → Multi-tenant isolation is non-negotiable
2. **Use MCPAgentJob model** → Not the legacy Agent model
3. **Respect field naming** → "description" (user) vs "mission" (AI)
4. **Token budget awareness** → Keep prompts under 2000 tokens default
5. **Test both modes** → Claude Code single-terminal AND Codex/Gemini multi-terminal
6. **WebSocket events** → Broadcast state changes for live dashboard updates
7. **Message hub integration** → All agent coordination via MCP message queue
8. **Error handling** → Graceful degradation, informative error messages

**When reading existing code:**

- `spawn_agent()` → LEGACY, use `spawn_agent_job()` instead
- `list_agents()` → LEGACY, use `get_pending_jobs()` instead
- `Agent` table → LEGACY 4-state model, use `MCPAgentJob` (7-state)
- References to "staging" → Means project activation endpoint
- Initial job status → "waiting" (not "pending")

---

## Common Workflows (Copy/Paste)

### Create a Task from Terminal
```python
# When idea pops up during coding:
await create_task(
    title="Research Redis caching",
    description="Look into Redis for session management",
    tenant_key=tenant_key
)
```

### Convert Task to Project
```python
# In dashboard: Click task → "Convert to Project"
# Result:
Project(
    name=task.title,  # Preserved
    description=task.description,  # Preserved
    mission="",  # Empty, orchestrator fills later
    product_id=active_product_id
)
```

### Orchestrator Staging Flow
```python
# 1. Get context
context = await get_orchestrator_instructions(orchestrator_id, tenant_key)

# 2. Analyze and create mission (AI processing)
mission = analyze_and_plan(context)

# 3. Persist mission
await update_project_mission(project_id, mission, tenant_key)

# 4. Select and spawn agents
for agent_spec in selected_agents:
    await spawn_agent_job(
        agent_type=agent_spec.type,
        mission=agent_spec.mission_fragment,
        project_id=project_id,
        tenant_key=tenant_key
    )
```

### Agent Execution Flow
```python
# 1. Find work
jobs = await get_pending_jobs(agent_type="implementer", tenant_key=tenant_key)

# 2. Claim job
await acknowledge_job(job_id=jobs[0].id, tenant_key=tenant_key)

# 3. Get mission
mission = await get_agent_mission(job_id=jobs[0].id, tenant_key=tenant_key)

# 4. Do work locally (write code, test, etc.)
result = execute_implementation(mission)

# 5. Report progress
await report_progress(job_id=jobs[0].id, percent=50, message="Half done", tenant_key=tenant_key)

# 6. Complete
await complete_job(job_id=jobs[0].id, output=result, tenant_key=tenant_key)
```

---

## Installation & Setup Reference

**Quick Start:**
```bash
# 1. Install server
python install.py

# 2. Create first user (browser)
# Navigate to http://localhost:7272/welcome

# 3. Export agents (browser)
# Settings → Integrations → Export Agents → Copy command

# 4. Install in CLI (terminal)
claude-code mcp add http://localhost:7272/mcp --api-key YOUR_KEY

# 5. Verify
claude-code mcp list  # Should show giljo-mcp with agents
```

**Database:** PostgreSQL (localhost recommended, remote supported via config)

**Port:** 7272 (API + WebSocket + MCP HTTP endpoint)

**Logs:** `logs/` directory (check for troubleshooting)

---

## Summary: The Big Picture

GiljoAI MCP is a **control tower** for AI-assisted development:

- **You code locally** in familiar terminal tools
- **Server manages context** via web forms and database
- **Orchestrator coordinates** multi-agent workflows
- **Dashboard tracks progress** with live updates
- **Agents communicate** via MCP message hub
- **Everything is organized** in Product → Project → Job hierarchy

**Result:** You stay in flow state, focused on coding, while the system handles context management, agent coordination, and progress tracking.

**Philosophy:** Structured context + visual workflow + terminal development = productive AI-assisted coding.

---

**Next Steps:**
1. Read `start_to_finish_agent_FLOW.md` for technical verification
2. Read `Simple_Vision.md` for product vision and user journey
3. Read `Comprehensive_MCP_Analysis.md` for architecture deep dive
4. Start coding with this context loaded

---

**Remember:** This document is mandatory context for all agents. When in doubt, refer back here for terminology, workflows, and architectural decisions.

**Version:** 1.0
**Last Updated:** 2025-11-07
**Maintained By:** GiljoAI Development Team
