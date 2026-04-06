# GiljoAI MCP - Complete Vision Document
**Product Name**: GiljoAI MCP
**Short Name**: GiljoAI_MCP
**Last Updated**: 2025-01-05
**Status**: Living Document
**Harmonization Status**: ✅ Aligned with codebase

> **Licensing Note (2026-03-07):** This project uses the **GiljoAI Community License v1.1** (single-user free, multi-user requires commercial license). This is NOT an OSI open-source license. Do not reference MIT, open source, or open core. See `LICENSING_AND_COMMERCIALIZATION_PHILOSOPHY.md`.
>
> **Edition Note (2026-03-08):** Two editions — Community Edition (CE, public, `main` branch) and SaaS Edition (private, `saas` branch). Enterprise is a deployment mode of SaaS, not a separate edition. SaaS-only code is physically isolated in `saas/` directories. See `docs/EDITION_ISOLATION_GUIDE.md`.

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../../handovers/Simple_Vision.md)** - User journey & product vision (harmonized with codebase)
- **[start_to_finish_agent_FLOW.md](../../handovers/start_to_finish_agent_FLOW.md)** - Technical verification & agent flow (code-verified)

**Key Handover References**:
- Handover 0088: context prioritization and orchestration architecture
- Handover 0102: Agent template export system (15-minute token TTL)
- Handover 0073: Project closeout workflow

---

## Quick Navigation

This is the **executive summary** of GiljoAI MCP's vision. For detailed technical information, see:

- **[Agentic Project Management Vision](AGENTIC_PROJECT_MANAGEMENT_VISION.md)** - Strategic vision for multi-agent orchestration with context prioritization and orchestration
- **[Multi-Agent Coordination Patterns](MULTI_AGENT_COORDINATION_PATTERNS.md)** - Proven patterns for orchestrating specialized AI agent teams
- **[Project Roadmap](../../handovers/completed/HANDOVER_0012_PROJECT_ROADMAP-C.md)** - 5-project implementation plan (Handovers 0017-0021)

### Role-Based Reading Paths

**For Executives & Product Managers**:
1. This document (Complete Vision) - Overall product vision and capabilities
2. [Agentic Project Management Vision](AGENTIC_PROJECT_MANAGEMENT_VISION.md) - Strategic vision and business value
3. [Project Roadmap](../../handovers/completed/HANDOVER_0012_PROJECT_ROADMAP-C.md) - Implementation timeline

**For Architects & Technical Leaders**:
1. This document (Complete Vision) - High-level architecture overview
2. [Multi-Agent Coordination Patterns](MULTI_AGENT_COORDINATION_PATTERNS.md) - Architectural patterns
3. [Server Architecture](../SERVER_ARCHITECTURE_TECH_STACK.md) - v3.0 unified architecture details

**For Developers & Implementers**:
1. [Multi-Agent Coordination Patterns](MULTI_AGENT_COORDINATION_PATTERNS.md) - Code-level patterns
2. Implementation handovers: [0017](../../handovers/0017_HANDOVER_20251014_DATABASE_SCHEMA_ENHANCEMENT.md), [0018](../../handovers/0018_HANDOVER_20251014_CONTEXT_MANAGEMENT_SYSTEM.md), [0019](../../handovers/0019_HANDOVER_20251014_AGENT_JOB_MANAGEMENT.md), [0020](../../handovers/0020_HANDOVER_20251014_ORCHESTRATOR_ENHANCEMENT.md), [0021](../../handovers/0021_HANDOVER_20251014_DASHBOARD_INTEGRATION.md)

**For New Team Members**:
1. This document (Complete Vision) - Start here
2. All three detailed vision documents
3. [Installation Guide](../INSTALLATION_FLOW_PROCESS.md)
4. [First Launch Experience](../FIRST_LAUNCH_EXPERIENCE.md)
5. Implementation handovers (0017-0021)

---

## Latest Update (Architecture V3 - 2025-10-14)
- Why: Deliver a secure, simple, and fast local-first coding orchestrator with clear APIs and reliable setup.
- How: FastAPI backend with explicit CORS and setup-mode gating; PostgreSQL + SQLAlchemy; JWT/API keys; Vue 3 UI; LAN-safe WebSockets.
- What: REST endpoints under `/api`, WebSocket at `/ws/{client_id}`, simplified setup wizard, and adapter IP detection to support LAN access.

Key Changes
- Setup wizard redirect fix: axios interceptor checks `/api/setup/status` before redirecting to `/login` on 401.
- Network IP detection enhances CORS origins without introducing wildcards; keeps localhost defaults.
- WebSocket authentication hardened: credentials validated before `accept()`, with proper close codes for unauthorized clients.
- Installation flow clarified: environment validation, DB bootstrap, service start, and wizard steps streamlined.

Capabilities ** NEEDS VALIDATION **
- Multi-tenant isolation using `X-Tenant-Key`, enforced across API and WebSocket subscriptions.
- Extensible tool access via `ToolAccessor`, designed for per-tenant operations.
- Health monitoring via `/health` with API/DB/WebSocket status.

Next Milestones
- Expand role-based permissions and UI for tenant-aware admin operations.
- Increase test coverage for LAN flows (CORS/IP changes) and WebSocket Subscribe/Authorize paths.
- Formalize production hardening: rate limits, security headers, and Docker profiles.

### CRITICAL: Development Approach

### Our Vision

To revolutionize software development by creating an intelligent orchestration layer that transforms isolated AI coding assistants into coordinated development teams, enabling developers to tackle projects of unlimited complexity while maintaining full control and visibility.

---

## Agentic System Implementation

GiljoAI MCP is evolving from a multi-tenant task management system into a **sophisticated agentic project management platform** that automatically orchestrates teams of specialized AI agents.

### Key Agentic Capabilities

**Automated Agent Spawning**:
- Orchestrator analyzes project requirements and automatically spawns specialized sub-agents
- Each agent receives minimal, focused context relevant to its specific task
- Agents work in parallel on different aspects of the project
- See [Agentic Project Management Vision](AGENTIC_PROJECT_MANAGEMENT_VISION.md) for details

**Vision Document Processing**:
- Large vision documents (50K+ tokens) chunked into searchable 5K sections
- Semantic boundary detection preserves meaning
- Keyword-based context indexing enables dynamic retrieval
- Agents load only relevant chunks for focused context delivery

**Orchestrator Intelligence**:
- Orchestrator reads full context once, creates condensed missions for each agent
- context prioritization and orchestration through intelligent summarization (Handover 0088)
- Each agent gets exactly what they need, nothing more
- Role-based hierarchical context loading filters irrelevant information
- Implementation patterns in [Multi-Agent Coordination Patterns](MULTI_AGENT_COORDINATION_PATTERNS.md)

**Project Description vs Mission** (Database Schema):
- `Project.description`: Human-written project scope/intent (Text field, nullable=False)
- `Project.mission`: AI-generated orchestrator summary after context analysis (Text field, nullable=False)
- Mission is created by orchestrator after analyzing product vision, context, and user-defined project description
- Source: `src/giljo_mcp/models.py` (Project model, lines 415-550)

**Multi-Agent Coordination**:
- Message queue with acknowledgment tracking prevents communication loss
- Peer-to-peer handoffs between agents
- Broadcast communication for project-wide changes
- Context threshold handoffs when agents approach limits
- Proven coordination patterns from AKE-MCP

**Real-Time Monitoring**:
- Live dashboard showing all agent activities
- Message history and acknowledgments
- Performance metrics
- Interactive controls for manual intervention when needed

### Proven Results from AKE-MCP

The patterns implemented in GiljoAI MCP are based on proven results from AKE-MCP:
- **context prioritization and orchestration** vs traditional approaches
- **95% reliability** in agent coordination
- **4x faster** through parallel execution
- **Unlimited scale** through vision chunking and context management

### Implementation Roadmap

Five sequential projects (Handovers 0017-0021) will bring the agentic vision to life:

1. **Database Schema Enhancement** (Week 1) - Foundation tables for context indexing, agent jobs, message queue
2. **Context Management System** (Weeks 2-3) - Vision chunking, searchable index, dynamic retrieval
3. **Agent Job Management** (Weeks 2-3) - Agent lifecycle, job tracking, message acknowledgments
4. **Orchestrator Enhancement** (Weeks 4-5) - Context summarization, mission generation, intelligent coordination
5. **Dashboard Integration** (Week 6) - Real-time monitoring, interactive controls, performance visualization

See [Project Roadmap](../../handovers/completed/HANDOVER_0012_PROJECT_ROADMAP-C.md) for complete implementation plan.

### Immediate Development Priorities

1. **Multi-Tenant Architecture**: Multiple users, with their own 'instance' and their own tasks handling, products with projects.  Their own configurations and settings. 
2. **Preserve Proven Features**: Vision chunking (50K+ docs), message acknowledgment arrays, dynamic discovery
3. **Serena MCP Integration**: Maintain and enhance Serena as an optionally enabled primary codebase discovery tool
4. **Progressive Setup**: A downloadable product, with proper installation, launch, first login experience and configuration in both Windows and linux/mac OS.
5. **Local-First Design**: PostgreSQL and Backend is a local on server orchestration, this is our primary focus.  Users interact anywhere on lan/wan via IP or can sit on same server if they want with localhost.  All the same experience.  Same codebase must scale to cloud in future. 
6. **UI/UX Design Requirements**:
   - Vue 3 + Vite with Vuetify 3 components
   - **MUST use color themes defined in /docs/color_themes.md**
   - **MUST use provided assets**:
     - System icons: `/frontend/public/icons/`
     - Animated mascot logo: `/frontend/public/mascot/`
     - Favicon: `/frontend/public/favicon.ico`
   - Support dark/light mode with smooth transitions
   - Custom button designs matching theme
   - Live data visualizations using theme colors
   - Accessibility compliant (WCAG 2.1 AA)

### Where We Are Today

### evolution from existing AKE-MCP
THis project builds on the competence of AKE-MCP, availabe as a git or on the developers workstations.  Ask questions if needed.

#### Current State (Oct 2025)

We have built a functional proof-of-concept that demonstrates the power of multi-agent orchestration:  But we are yet to test them against real AI agents.

**Working Components:**

- **FastMCP Server**: 20 essential tools for agent coordination
- **PostgreSQL Backend**: Robust state management and message queuing
- **Multi-Agent Orchestration**: Project Manager model with specialized agents
- **Dynamic Discovery**: Agents explore codebases on-demand using Serena MCP
- **Vision Document System**: Product principles guide all agent decisions, vision documents are same as a product definition document or a product proposal document.  This is what is being built or worked on.
- **Web Dashboard**: Real-time monitoring and control at localhost:7274
- **Task Management**: Capture and track technical debt during coding sessions

**Current Architecture:**

- Python code base
- Database-first design with PostgreSQL
- Singleton server pattern for resource efficiency
- Message acknowledgment system preventing communication loss
- Context-aware agent handoffs at threshold limits
- Agent profiles
- / (slash) commands for quick communications from AI agent tool to MCP server

**Proven Capabilities:**
**Originally from AKE-MCP need to be tested in GiljoAI MCP**
- Successfully orchestrates multiple agents on complex projects
- Maintains context across sessions through persistent storage
- Enables vision-driven development with chunked document handling
- Provides real-time visibility into agent activities and decisions

### Where We Are Going

#### Immediate Future (Q1-Q2 2025)

**Local-First Server Architecture**
We are rebuilding the system with a local-first philosophy that scales naturally:

- **Local Mode**: Zero-configuration setup for individual developers
- **WAN/LAN Mode**: Simple network sharing for small teams

NOTE: These are not profiles, the product fundamentally should work with several users using it at the same time in their tennant space.

#### Key Architectural Principles

**1. Network enabled and locally capable**
-  Works both as localhost and on LAN
-  Uses same authentication
-  code should be scalable to a future cloud hosting, potentially SaaS

**2. Database Agnostic**

- PostgreSQL for individuals and small teams
- PostgreSQL for concurrent scale
- Future: Distributed databases for global scale

**3. Multi-Tenant by Design**

- Project isolation via credentials JWT (ARE THERE KEYS TOO?)
- Concurrent project support
- 
**4. Deployment Flexibility**

-  Downloadable from git or Giljo.ai
-  Simple script based, '.py' for installation
-  Instructions for script injection to configure AI coding agents to connect to MCP
-  Easy on off serena integration
-  Admin configuration settings to change the servers evnironmentals

**5. Multi OS and path neutrality**

-  Built for multy OS, windows, Linux and Mac
-  path neutrality so users can choose install foder
-  Flexible installation with selecting IP address to bind to, databse location if not auto detected, dependancy instlalation, venv creation and transition to "First Setup" forcing admin password settings and continued to standard user onboarding steps.


### Design Philosophy

#### For Developers, By Developers

Every decision prioritizes developer experience:

- **Immediate Value**: Works out of the box, no complex setup
- **Progressive Disclosure**: Simple for simple cases, powerful when needed
- **Tool Philosophy**: Does one thing exceptionally well
- **Community Edition**: Full product, free for single-user use (GiljoAI Community License v1.1)

### Two-Edition Architecture (Decided 2026-03-07)

GiljoAI MCP ships as two editions from a single codebase (split before public release):

**Community Edition** (public, free for single-user):
Core orchestration, agent management, single-user auth, tenant isolation (hidden), WebSocket/MCP, full dashboard, CE branding.

**SaaS Edition** (private, commercial license for multi-user):
Layers on top of Community with OAuth/SSO, billing, org/team management, multi-user admin, usage metering, enterprise deployment (Docker/K8s).

The private SaaS repo imports the Community repo as a dependency -- no forking, no merge debt. See `handovers/0770_SAAS_EDITION_PROPOSAL.md` for the full decision record.

#### Customizable User Experience

Recognizing that developers have different preferences:

- **Themeable Interface**: Dark mode, custom colors, layouts
- **Choice of CLI-based AI coding agents**: Add custom instructions for integration

#### AI-Agnostic Future


- **Claude**: First integration, uses your own Claude Code CLI; we provide MCP server injection instructions.
- **CODEX**: supported (native MCP commands)
- **Gemini CLI**: supported (native MCP commands)
- **Universal Protocol**: Any AI that speaks MCP

### Innovation Drivers

#### 1. Vision-Driven Development

The deveopers unique vision document system ensures AI agents always align with product principles, creating consistency across thousands of decisions.

#### 2. Simplified Discovery

Context fields for a product are filled out by the developer which the agents draw from to succeed in their assignments.

#### 3. Task Continuity

Seamlessly capture technical debt during coding, then orchestrate AI teams to address it systematically.

#### 4. Progressive Architecture

One codebase that scales from laptop to LAN?WAN  without rewrites, respecting the journey from individual to team.

#### 5. intuitive commands and interfaces

Live view dashboard with control over how the agents work.

CLI slash "/" commands to quickly communicate from the AI coding agent CLI interface to GiljoMCP

### Installation and Packaging Strategy

#### Zero-Friction Onboarding Vision

**Our Goal**: From download to running system in under 5 minutes, regardless of technical expertise.

**Installation Philosophy**:

- **Intelligent**: Automatically detect and install missing dependencies
- **Adaptive**: transitions to webpage to complete installation once the core functionality is implemented and backend and frontend launch successfully.
- **Complete**: One installer handles everything from binding IP, to detect database, setup database, install dependancies, and launches the web interface to finish installation.

**Advanced Installer Features**:

1. **Intelligent Quickstart Layer** (CRITICAL)

   - .\install.py for windows (with dependancies in .\installer)
   - F.\Linux_Installer\linux_install.py (with all dependancies in this folder)
   - initial pre requirements check in order to make the installers work, such as Python install.

2. **Smart Startup.py System**

   - Installation can auto launch or user can choose to contiue with singular script exectution by self launching startup.py
   - User can alternatively use individual commands to launch backend and front end from CLI.

3. **Dependency Management**

   - Automatic detection of Python, Node.js, PostgreSQL
   - Offers to install missing components
   - Platform-specific installation methods (winget, brew, apt, etc.)
   - Fallback to manual downloads if needed

4. **Post-Install Experience**
   - Desktop shortcuts and launcher creation
   - user needs to change admin passwrod on first install
   - All users go to a setup screen where they get instructions on how to configure the MCP server via cut and paste actions
   - Future is links to downloadable '.py' scripts to automate the injection into installed AI coding agents
   - Built-in example agents and templates, and option to activate those agents and inject them into the AI coding agent, such as subagents in Claude Code CLI.  Future CODEX.
   - Asks user to enable Serena durin setup
   - Immediate access to web dashboard to start documenting the first product.

**Distribution Channels**:

- **Direct Download**: ZIP/TAR packages from website
- **Package Managers**: pip, brew, winget, apt
- **Developer Platforms**: GitHub Releases, GitLab

