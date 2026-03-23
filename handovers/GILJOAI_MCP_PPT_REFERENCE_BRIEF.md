# GiljoAI MCP — PowerPoint Reference Brief

**Purpose:** This document gives you everything you need to review and update the GiljoAI MCP workflow/architecture PowerPoint. It consolidates branding rules, product architecture, user workflows, and the current state of the application into one reference. Use this as your source of truth when modifying slides.

**Date:** 2026-03-22

---

## 1. BRANDING & LICENSING (Non-Negotiable)

### Identity
- **Product name:** GiljoAI MCP Coding Orchestrator
- **Product tagline:** "Break through AI context limits. Orchestrate teams of specialized AI agents."
- **Edition:** Community Edition (CE) — free, single-user, self-hosted
- **License:** GiljoAI Community License v1.1
- **Classification:** Source-available (NEVER "open source," "MIT," or "open core")
- **Company:** GiljoAI LLC, Nashua, NH
- **Company tagline:** "Imagine having a conversation with everything you know."
- **Website:** giljo.ai (giljoai.com redirects — always use giljo.ai)
- **Contact:** sales@giljo.ai (licensing), infoteam@giljo.ai (general), security@giljo.ai (security)

### Terminology Rules
| Always Use | Never Use |
|------------|-----------|
| Source-available | Open source |
| GiljoAI Community License v1.1 | MIT License |
| Community Edition + SaaS Edition | Enterprise Edition (as separate tier) |
| Context engineering platform | Orchestration layer |
| Passive orchestrator | AI engine / AI platform |
| Agents standing by | Agents orchestrating |
| giljo.ai | giljoai.com |

### Passive Orchestrator Framing (Critical)
GiljoAI does NOT have AI inference capabilities. It assembles context and generates structured prompts. The user's AI tool (Claude Code, Codex, Gemini) does the thinking. All messaging must reflect this:
- "Receives" not "sends"
- "Agents standing by" not "orchestrating"
- "Bring Your Own AI" — users supply their own AI tool subscription

### Two-Edition Model
| | Community Edition | SaaS Edition |
|---|---|---|
| **Status** | Launching April 2026 | Coming later (25-35 weeks post-CE) |
| **Users** | Single user | Multi-user, multi-org |
| **Deployment** | Self-hosted | Hosted by GiljoAI |
| **License** | GiljoAI Community License v1.1 | Subscription |
| **Auth** | Login/password, JWT | OAuth/SSO/MFA |
| **Features** | Full orchestration engine | Everything in CE + org management, billing, roles, audit trails |

Enterprise is a deployment mode of SaaS (self-hosted by corporate IT), NOT a separate edition. Never show three editions.

### Memberships (for footer/badges if needed)
- Nvidia Inception Program
- Open Invention Network
- LOT Network

---

## 2. TECH STACK

### Backend
- Python 3.11+ / FastAPI 0.104+
- PostgreSQL 18 (required)
- SQLAlchemy 2.0 (async)
- JWT authentication, bcrypt password hashing
- WebSocket for real-time dashboard updates

### Frontend
- Vue 3 (Composition API) / Vuetify 3 (Material Design 3)
- Pinia state management
- Node.js 20+, Vite build tool

### Protocols
- MCP-over-HTTP (JSON-RPC 2.0, standard MCP protocol)
- WebSocket for real-time UI updates
- REST API (209 endpoints)

### Key Numbers
- 209 API endpoints
- 33 database models
- 90+ Vue components
- 380+ tests
- 61 tenant isolation regression tests
- Sub-100ms response times
- 6 built-in agent templates
- Up to 8 active agents per project
- 30+ MCP tools

### Ports
- API Server: 7272
- Frontend: 7274 (production) / 5173 (dev)
- Database: 5432 (localhost only, never exposed)

---

## 3. ENTITY HIERARCHY

This is the core data model. Every diagram showing data relationships should match this exactly.

```
Organization
  └── User (admin or member of org)
        └── Product (belongs to user)
              ├── Project (belongs to product)
              │     └── Job (belongs to project)
              │           └── Agent (belongs to assigned job)
              └── Task (belongs to product)
```

- **Organization** = top-level tenant boundary
- **User** = belongs to an organization
- **Product** = primary work container (tech stack, architecture, vision docs, guidelines defined here)
- **Project** = a unit of work within a product (has a human description that becomes a mission)
- **Job** = an assignment within a project, executed by an agent
- **Agent** = bound to a specific job for its lifecycle
- **Task** = belongs to a product (separate from the project→job chain)
- All database queries filter by `tenant_key` (defense in depth)

---

## 4. CLIENT-SERVER ARCHITECTURE

GiljoAI is a **distributed system**. The server provides data; the AI tools execute on the client.

```
CLIENT (Developer's Machine)              SERVER (GiljoAI MCP)
────────────────────────────              ────────────────────────
AI Tool (Claude/Codex/Gemini)             FastAPI API Server (0.0.0.0:7272)
Project source files (local)              PostgreSQL database (localhost:5432)
Orchestrator execution                    MCP HTTP endpoint (POST /mcp)
Agent execution                           WebSocket server (real-time UI)
Code reading/writing                      Vue 3 dashboard (port 7274)

         ──── HTTP (MCP JSON-RPC 2.0) ────→
         ←── Context, missions, templates ──
```

**Server does:** Store product definitions, agent templates, missions, context data. Serve MCP tools. Serve dashboard UI.
**Server does NOT:** Execute AI agents, access project files, run inference.

**Client does:** Execute orchestrators and agents (in the user's AI tool), read/write project files.
**Client does NOT:** Store missions, agent templates, or product data.

---

## 5. USER WORKFLOWS

### 5A. Installation Flow
1. `git clone` the repo
2. `python install.py` — handles dependencies, database creation, setup wizard
3. `python startup.py` — launches API server + frontend
4. Dashboard at http://localhost:7274, MCP server at http://localhost:7272/mcp
5. First-run redirects to /welcome → /first-login (create admin account)

### 5B. Product Definition Flow
1. Create a Product in the dashboard
2. Define: product name, tech stack, architecture description, guidelines
3. Upload vision documents (strategic context for agents)
4. Configure context toggles and depth settings (what agents see and how much)
5. Product becomes the single source of truth for all projects under it

### 5C. Project Workflow (Define → Stage → Execute → Close)
1. **Define:** Create a Project under a Product. Write a human description of what you want built.
2. **Stage:** Click "Stage" — the system assembles context from the Product and generates a structured prompt. Prompt goes to clipboard.
3. **Paste:** Paste into your AI tool (Claude Code, Codex, Gemini). The AI reads the prompt, connects to GiljoAI via MCP.
4. **Mission Generation:** The AI tool calls MCP tools to generate a mission plan with agent assignments.
5. **Execute:** Agents execute their assigned work. Progress visible on the real-time dashboard.
6. **Close Out:** When complete, the system writes a closeout summary to 360 Memory. Next project starts with richer context.

### 5D. Staging Workflow (7 Internal Tasks)
When staging is triggered, the orchestrator runs this sequence:
1. **Identity & Context Verification** — verify project ID, tenant isolation, orchestrator connection
2. **MCP Health Check** — verify server responsive, tools available, auth tokens valid
3. **Environment Understanding** — read CLAUDE.md, understand tech stack, parse project structure
4. **Agent Discovery & Version Check** — call get_available_agents(), discover agents dynamically (no embedded templates)
5. **Context Configuration & Mission** — apply user's toggle/depth settings, fetch product context, vision docs, git history, 360 memory, generate mission (<10K tokens)
6. **Agent Job Spawning** — create AgentJob records, assign execution mode, set status to 'waiting'
7. **Activation** — transition project to 'active', enable WebSocket broadcasts, start monitoring

### 5E. Agent Template & Export Flow
- 6 built-in templates: Orchestrator, Analyzer, Implementer, Tester, Reviewer, Documenter
- Templates are platform-neutral in the database
- Server-side assembler formats at export time: YAML for Claude Code/Gemini, TOML for Codex
- Monaco editor in dashboard for customization
- Three-layer caching for sub-millisecond template resolution
- `/gil_get_agents` is the primary MCP tool for agent retrieval (replaces old `/gil_get_claude_agents`)
- 8-agent limit is per-server, not per-platform

### 5F. Context Depth Configuration
Users control what each agent sees and how detailed it is:

**Toggle Config (WHAT):** Field-level on/off per category
**Depth Config (HOW):** Token management, 8 depth controls

10 toggleable context categories:
- Product Context, Vision Documents, Tech Stack, Architecture, Testing Strategy, 360 Memory, Git History, Templates, Project details, Guidelines

**Lean context** = fast, focused agents. **Full context** = comprehensive understanding for complex work.

### 5G. 360 Memory
- Every completed project writes a memory entry automatically
- Captures: what was built, key decisions, patterns discovered, what worked
- Persistent, cumulative — project N starts with accumulated context from projects 1 through N-1
- Optionally enriched with git commit history
- Not an integration or plugin — core product behavior

### 5H. Multi-Platform Support
| Platform | Export Format | Subagent System |
|----------|--------------|-----------------|
| Claude Code CLI | YAML (.claude/agents/*.yaml) | Task tool (single terminal) |
| Codex CLI | TOML (config.toml + agent files) | spawn_agent / CSV batch |
| Gemini CLI | YAML (gemini/agents/*.yaml) | DelegateToAgentTool |
| Any MCP Client | Generic template (multi-terminal) | Manual per-terminal |

---

## 6. MCP TOOLS (30+)

### Staging Tools (Orchestrator Preparation)
- `get_available_agents()` — dynamic agent discovery
- `health_check()` — MCP server connectivity
- `fetch_product_context()` — product metadata
- `fetch_vision_document()` — vision docs (paginated)
- `fetch_git_history()` — commit history
- `fetch_360_memory()` — project closeout summaries

### Execution Tools (Agent Runtime)
- `get_generic_agent_template()` — renders platform-specific template
- `get_agent_mission()` — fetches mission from database
- `update_job_progress()` — reports progress
- `send_message()` / `receive_messages()` / `acknowledge_message()` — agent-to-agent communication
- `complete_job()` — marks job complete
- `report_error()` — error reporting

### Execution Modes
- **Claude Code CLI (single terminal):** Orchestrator spawns sub-agents via Task tool
- **Multi-terminal generic:** Each agent runs in its own terminal, coordinates via MCP message queue

---

## 7. NETWORK ARCHITECTURE

```
User Access (controlled by OS firewall):
┌──────────────────────────────────────────┐
│ Localhost:    http://127.0.0.1:7272      │
│ LAN (if fw):  http://<local-ip>:7272    │
│ WAN (if fw):  https://example.com:443   │
└───────────────────┬──────────────────────┘
                    │
                    ▼
       ┌────────────────────────┐
       │  API Server (FastAPI)  │
       │  Binds to: 0.0.0.0    │ ← ALWAYS all interfaces
       │  Port: 7272            │
       │  Auth: JWT Required    │
       └────────────┬───────────┘
                    │
                    │ ALWAYS localhost
                    ▼
       ┌────────────────────────┐
       │  PostgreSQL Database   │
       │  Host: localhost       │ ← NEVER exposed
       │  Port: 5432            │
       └────────────────────────┘
```

Defense in depth: OS Firewall → Application Auth (JWT) → Password Policy → Database Isolation → HTTPS/TLS for WAN.

---

## 8. INTEGRATIONS (Optional)

### Serena MCP (Optional)
Deep semantic code analysis. Agents explore codebases through symbol-level operations instead of loading entire files.

### GitHub Context Query (Optional)
Enriches project memory with git commit history during closeout. Not required — 360 Memory provides full project history independently.

---

## 9. SLIDES CLEANUP CHECKLIST

When reviewing/updating any slide, check for:
- [ ] "MIT" or "open source" or "open core" → replace per branding rules
- [ ] "v1.0" license references → "v1.1"
- [ ] "giljoai.com" → "giljo.ai"
- [ ] "GiljoAI MCP Server" → "GiljoAI MCP Coding Orchestrator"
- [ ] "Agent Orchestration MCP Server" → "GiljoAI MCP Coding Orchestrator"
- [ ] Three editions shown → must be two (CE + SaaS; Enterprise = deployment mode of SaaS)
- [ ] Active orchestration language → passive orchestrator language
- [ ] "licensing@giljoai.com" → "sales@giljo.ai"
- [ ] Node.js 18+ → Node.js 20+
- [ ] `master` branch → `main` branch
- [ ] Any reference to the server executing code or running inference → server provides data only
