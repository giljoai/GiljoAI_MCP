# GiljoAI MCP -- Messaging & Positioning Research Report
**Date:** 2026-03-13
**Purpose:** Inform messaging strategy for giljoai.com landing page
**Prepared for:** Discussion in Claude AI (cloud) -- contains codebase findings not visible there

---

## PART 1: WHAT THE PRODUCT ACTUALLY DOES (From the Codebase)

### The Three Core Functions

**1. Product Management ("Define your product in great detail")**

GiljoAI MCP lets you create a **Product** -- a rich, structured definition of the software you're building. This is NOT a Jira-style project tracker. It is a knowledge base that AI agents consume. A Product includes:

- **Vision Documents**: Upload `.md`/`.txt` files describing your product (vision, architecture, features, API, testing, deployment). Auto-chunked for large files, with multi-level summarization (LSA algorithm creates 33% and 66% summaries).
- **Structured Config Data**: Tech stack (languages, frameworks, database, infra), architecture (patterns, design decisions, API style), features, test config (strategy, coverage target, frameworks, quality standards), target platforms, project path.
- **360 Memory**: Cumulative knowledge that grows across projects. Every completed project writes a memory entry (summary, key outcomes, decisions, git commits, deliverables, metrics, significance score). New sessions start with accumulated intelligence from all past work.
- **Quality Standards**: Testing expectations in text form.
- **One active product at a time** -- enforced at the database level. Forces focus.

**2. Project Execution ("Run projects against those products")**

Projects are work initiatives under a Product -- the unit of execution:

- Developer writes a **human description** of what they want done.
- System generates a **mission** -- a detailed AI-generated work plan based on the full product context.
- **Project Taxonomy**: Structured naming with type codes (BE, FE, API) and serial numbers (BE-0001a).
- **Staging Workflow**: Context compiled, mission generated, agents selected before execution begins.
- **Two execution modes**: Multi-Terminal (each agent in separate terminal -- Codex/Gemini) or Claude Code CLI (single terminal with sub-agent spawning).
- **Closeout System**: Orchestrator summaries, closeout checklists, git commit tracking, automatic 360 memory writing.
- **Agent Team**: Six specialized roles: Orchestrator (team lead), Implementer, Tester, Analyzer, Reviewer, Documenter. Each receives role-specific missions.
- **Inter-agent messaging**: Message queues with structured handoffs and acknowledgments.
- **Health monitoring**: Agent status tracking (waiting/working/blocked/complete/silent/decommissioned), progress percentages, health checks.
- **Real-time dashboard**: WebSocket-driven live monitoring of all agent activity.

**3. Prompt/Agent Coordination ("Create prompts for LLM tools to coordinate agents")**

This is the engine that makes orchestration possible:

- **Agent Template System**: 6 default templates per tenant, each with dual-field instructions (system + user-customizable), tool assignment (claude/codex/gemini), model selection, behavioral rules. Editable via Monaco editor. Three-layer caching (Memory < 1ms -> Redis < 2ms -> Database < 10ms).
- **Thin Client Prompt Generator**: Creates ~450-token "thin prompts" that instruct the orchestrator to fetch context on-demand via `fetch_context` MCP tool, rather than embedding all context inline. **This achieves 70-85% token reduction** compared to single-agent approaches.
- **Mission Planner**: Builds tiered fetch instructions (CRITICAL/RECOMMENDED/OPTIONAL) based on user-configured field priorities.
- **Protocol Builder**: Generates 5-chapter orchestrator protocol (Mission, Startup, Spawning Rules, Error Handling, Reference).
- **30+ MCP Tools**: The full interface agents use -- spawn jobs, get missions, report progress, send messages, fetch context (10 categories: product_core, vision_documents, tech_stack, architecture, testing, memory_360, git_history, agent_templates, project, self_identity).
- **Template Export**: Generated agent templates can be exported directly to Claude Code's configuration.

### Technical Architecture
```
Developer's CLI Tool (Claude Code / Codex / Gemini)
        |
        | MCP-over-HTTP (API key auth, JSON-RPC 2.0)
        v
  FastAPI Server (port 7272)
  +--> REST API (auth, products, projects, tasks, agents, messages)
  +--> MCP HTTP Endpoint (30+ tools for AI agents)
  +--> WebSocket (real-time updates to frontend)
        |
        v
  PostgreSQL 18 (tenant-isolated, every query filtered by tenant_key)

  Vue 3 + Vuetify 3 Frontend (port 7274)
  +--> 19 views, 67+ components, 14 Pinia stores
  +--> WebSocket live updates with auto-reconnect
```

### Frontend -- What Users Actually See

**Dashboard**: 7 stats cards (projects, tasks, API calls, MCP calls, agents spawned, jobs done, projects finished).

**Products View**: Card grid with product management. Rich form with tabs (Basic, Tech Stack, Architecture, Features, Test Config). Vision document upload with auto-chunking. Soft delete with 10-day recovery.

**Projects View**: Filterable data table with taxonomy chips. Status lifecycle management. Search by name, mission, ID, or taxonomy alias.

**Project Launch View** (the primary workspace): Two tabs -- STAGING (description, generated mission, agent cards) and IMPLEMENTATION (full agent monitoring table with status, duration, TODO progress, messages). Real-time WebSocket updates. "Stage Project" generates and copies the orchestrator prompt to clipboard.

**Tasks View**: Inline-editable task table. Task-to-project conversion. Priority, category, due dates.

**Settings**: Template Manager (Monaco editor), Context Priority Configuration (3-tier system), API key management, Git/MCP/Serena integration cards.

---

## PART 2: WHAT THE CURRENT WEBSITE SAYS

### Current Messaging Structure

The website is organized into three tabs: **Product**, **Products**, **About**.

**Hero Section:**
- Badge: "Open Source MCP Server"
- Headline: "Define Once. Orchestrate Everything."
- Subheadline: "Centralized context turns isolated AI tools into coordinated development teams. Your agents already know the plan."
- Trust row: "MIT Licensed | Self-Hosted | Privacy First"

**Problem-Solution Section:**
- Header: "AI Tools Are Powerful. But Isolated."
- Three cards: Persistent Project Memory, Coordinated Agent Teams, Deploy Your Way

**How It Works:**
- "From Install to Orchestration in Minutes"
- 4 steps: Install, Connect, Describe, Orchestrate

**Capabilities:**
- "Built for Serious Development"
- 6 cards: Multi-Agent Orchestration, Smart Context Loading, Real-Time Dashboard, Build Agent Templates, Multi-Tenant Isolation, MCP-over-HTTP

**Integrations:**
- Built-in: 360 Memory, Context Configurator, Agent Template Manager
- Optional: Serena MCP, GitHub Context Query

**Editions:**
- Community (Free Forever) vs SaaS (Contact for Pricing)

**About Tab:**
- "What We're Building" origin story
- The Problem / Our Approach
- Beyond Developer Tools (Personal Memory Assistant, PM Appliance)
- Principles: Open Source First, Production Grade, Privacy Matters
- Founder's Note

### Observations About Current Messaging

1. **Leads with WHAT, not WHY**: The page opens with "Define Once. Orchestrate Everything." -- a technically accurate tagline, but it assumes the reader already understands why multi-agent orchestration matters.

2. **No persona identification**: The page never says "If you are X..." or "Built for..." It doesn't acknowledge the different user types who might land here.

3. **Technical language first**: "MCP Server", "JSON-RPC 2.0", "MCP-over-HTTP" -- this is engineer-speak that lands well with experienced devs but alienates the "novice starter with a vision" you mentioned.

4. **The problem statement is buried**: "AI Tools Are Powerful. But Isolated." appears below the fold, after the hero and the "works with" strip. But this is arguably the most important message on the page.

5. **Missing the industry shift narrative**: The page doesn't acknowledge the fundamental shift happening -- that AI coding tools are changing what it means to be a developer, and that this creates a new competency gap.

6. **"MIT Licensed" inconsistency**: The hero says "MIT Licensed" but the actual license is "GiljoAI Community License v1.0" (single user free, 2+ users need commercial license). The CLAUDE.md explicitly says: "Never use terms 'MIT', 'open source', or 'open core'".

7. **Doesn't mention the three core functions clearly**: Product definition, project execution, and prompt coordination are the three pillars, but they're scattered across multiple sections rather than presented as a clear value proposition.

---

## PART 3: GAP ANALYSIS -- WEBSITE vs. PRODUCT REALITY

### What the Website Undersells

1. **Product Definition as Knowledge Management**: The website barely mentions that you define a complete software product specification. This is arguably the killer feature -- it's closer to what Confluence does than what Jira does, but AI-native.

2. **70-85% Token Reduction**: This is buried in no section of the website. The thin-prompt architecture is a genuine technical innovation that saves real money and time. It should be a headline number.

3. **360 Memory**: Mentioned but not explained. The fact that your project knowledge compounds over time -- that your 10th project starts smarter than your 1st -- is a powerful differentiator.

4. **Task-to-Project Pipeline**: Not mentioned at all. The ability to capture ideas (tasks) and promote them to full projects is a workflow that resonates with how developers actually work.

5. **Vision Document Summarization**: Not mentioned. Multi-level automatic summarization of product specs is a feature that directly addresses the "how do I fit my project context into an LLM" problem.

6. **Prompt Generation**: The website doesn't emphasize enough that GiljoAI generates the prompts for you. This is the "magic moment" -- you click "Stage Project", a prompt appears on your clipboard, you paste it into your CLI tool, and orchestration begins.

### What the Website Oversells

1. **"Works with Any MCP Client"**: Technically true, but the prompt generation and template system are heavily optimized for Claude Code, Codex, and Gemini. A generic MCP client would get raw tool access but not the workflow.

2. **"Open Source" / "MIT Licensed"**: The actual license is more restrictive than MIT. Single user is free, but multi-user requires a commercial license.

---

## PART 4: POSITIONING ANALYSIS -- WHO ARE WE AND WHO DO WE COMPETE WITH?

### Competitive Landscape

| Tool | What it Does | Gap GiljoAI Fills |
|------|-------------|-------------------|
| **Jira** | Human-to-human project tracking | Doesn't speak to AI agents. No context delivery. No prompt generation. |
| **Confluence** | Human knowledge base | Documents sit static. No AI-native delivery. No summarization for token budgets. |
| **Linear** | Modern issue tracking | Same gap as Jira -- built for humans managing humans. |
| **Cursor / Windsurf** | AI-assisted code editor | Single-agent, no multi-agent coordination, no persistent memory across sessions. |
| **Claude Code / Codex / Gemini CLI** | AI coding agents | Powerful individually but isolated. No shared context. Every session starts from scratch. GiljoAI is the infrastructure layer beneath these tools. |
| **Devin / SWE-Agent** | Autonomous coding agents | Monolithic approach. GiljoAI's multi-agent approach is modular and composable. |
| **Anthropic's Claude Projects** | Context persistence for Claude | Limited to Claude ecosystem. No multi-agent. No structured product definition. |

### Positioning Options

**Option A: Developer Infrastructure** (current positioning)
"MCP server for multi-agent orchestration"
- Pros: Technically precise, resonates with infra engineers
- Cons: Narrow audience, doesn't capture the PM/EM value

**Option B: AI-Native Project Management** (your proposed direction)
"The project management layer for AI-assisted development"
- Pros: Broader appeal, positions against Jira/Confluence/Linear
- Cons: Might seem like "just another PM tool"

**Option C: The New Developer Competency** (your messaging draft refined)
"AI coding tools made every developer a storyteller. GiljoAI makes every storyteller an orchestra conductor."
- Pros: Captures the industry shift, aspirational, broad appeal
- Cons: Needs concrete follow-up quickly or feels like marketing fluff

**Option D: Hybrid -- Start with Why, then What**
Lead with the industry narrative, identify the persona, then describe the product.
- Pros: Best of all worlds
- Cons: Longer page, requires more careful information architecture

---

## PART 5: INITIAL TAKE ON YOUR MESSAGING DIRECTION

### Your Draft (Paraphrased)

> "With AI coding tools growing exponentially, developers are becoming storytellers. This creates a new hybrid competency: project management + engineering management + development. GiljoAI addresses this. Whether you're a novice with a vision or a veteran with a wider job description, GiljoAI MCP is for you."

### What I Think Works

1. **The "developer as storyteller" insight is powerful.** It captures something real -- that with AI tools, the developer's job shifts from writing code to describing intent. The bottleneck moves from implementation to specification and coordination.

2. **The two-persona framing is smart.** "Novice starter with a vision" and "seasoned veteran with a wider job description" captures the two ends of the spectrum without excluding anyone in between.

3. **The "new competency" angle differentiates from feature-listing.** Instead of "here are our 30 MCP tools", you're saying "the world changed, and you need a new kind of tool."

### What I Think Needs Work

1. **"Burden" is a negative frame.** Reframe from "burden on a new competency" to "opportunity" or "superpower." Developers aren't burdened -- they're empowered, but they need infrastructure.

2. **The hybrid role description needs sharpening.** "Project management + engineering management + development" is abstract. What does that actually look like? It looks like: defining products clearly enough for AI to execute, coordinating multiple AI agents, maintaining persistent knowledge across sessions, reviewing and directing AI output.

3. **Need concrete "what happens when" hooks.** The draft is all "why" without showing "what." After establishing the narrative, show the concrete moment: "You describe your product. GiljoAI generates the plan. Six specialized agents execute it. You monitor in real-time."

4. **"Regardless if you are..." is a weak connector.** The two personas need distinct value propositions, not a generic "it's for you."

### Suggested Messaging Architecture

```
SECTION 1: WHY (The Industry Shift)
"AI coding tools changed the game. The developer's job is no longer
just writing code -- it's describing what to build, coordinating AI
agents that build it, and maintaining the knowledge that makes each
session smarter than the last."

SECTION 2: WHO (The Audience)
Two distinct personas with specific pain points:

  For the new builder: "You have a vision but no dev team. AI tools
  are powerful but chaotic. You need structure: a way to define your
  product once and have AI agents understand it every time."

  For the experienced developer/lead: "Your job description just
  expanded. You're the PM, the architect, and the developer. You
  need infrastructure that handles multi-agent coordination so you
  can focus on direction, not repetition."

SECTION 3: WHAT (The Product)
"GiljoAI MCP is the orchestration layer for AI-assisted development."
Three pillars:
  1. Define your product (knowledge base AI agents consume)
  2. Execute projects (coordinate specialized agent teams)
  3. Accumulate intelligence (360 Memory -- every project makes the
     next one smarter)

SECTION 4: HOW (Differentiators)
- 70-85% token reduction via thin-prompt architecture
- 6 specialized agent roles with structured handoffs
- Works with Claude Code, Codex, Gemini (any MCP client)
- Real-time dashboard for monitoring
- Self-hosted, privacy-first
```

### Key Numbers From the Codebase (For Marketing Use)

- **30+ MCP tools** exposed to AI agents
- **6 specialized agent templates** (Orchestrator, Implementer, Tester, Analyzer, Reviewer, Documenter)
- **70-85% token reduction** vs single-agent approaches (documented in codebase)
- **10 context categories** with tiered depth control
- **61 tenant isolation regression tests** (production-grade security)
- **380+ total tests**
- **Sub-100ms performance**
- **3-layer caching** (memory < 1ms, Redis < 2ms, database < 10ms)
- **19 frontend views, 67+ components, 14 Pinia stores**

---

## PART 6: ISSUES TO FIX ON CURRENT WEBSITE

1. **License mismatch**: Hero says "MIT Licensed" -- must be changed to match the actual GiljoAI Community License v1.0. CLAUDE.md explicitly prohibits using "MIT", "open source", or "open core."

2. **Footer says "Open source under MIT License"** -- same issue.

3. **Principles section says "MIT licensed"** -- same issue.

4. **Product tab says "Open Source MCP Server"** in the hero badge -- this contradicts CLAUDE.md which says never use "open source."

5. **"sales@giljoai.com"** in SaaS edition CTA -- verify this email exists.

6. **Footer tagline**: "Imagine having a conversation with everything you know" -- this is a great line but has no connection to the rest of the messaging. Consider making it a theme.

---

## APPENDIX: DATA MODEL SUMMARY

| Model | Purpose |
|-------|---------|
| `Product` | Top-level software product definition |
| `VisionDocument` | Product specification documents (multiple per product) |
| `ProductMemoryEntry` | 360 Memory -- accumulated project knowledge |
| `Project` | Work initiatives under a product |
| `ProjectType` | Taxonomy categories (BE, FE, API, etc.) |
| `Task` | Flexible work items / idea capture |
| `AgentJob` | Persistent work orders (the WHAT) |
| `AgentExecution` | Agent instances (the WHO) |
| `AgentTemplate` | Reusable agent role templates |
| `Message` | Inter-agent communication |
| `Organization` | Multi-tenant organization entity |
| `User` | User accounts with JWT auth |

## APPENDIX: SERVICE LAYER SUMMARY

| Service | Purpose |
|---------|---------|
| `OrchestrationService` | Central agent coordination engine |
| `ProductService` | Product CRUD and lifecycle |
| `ProjectService` | Project lifecycle, staging, launch, closeout |
| `TaskService` | Task CRUD, task-to-project conversion |
| `AgentJobManager` | Agent spawning and team management |
| `MessageService` | Inter-agent messaging |
| `ContextService` | Context retrieval and delivery |
| `ConsolidatedVisionService` | Multi-document vision aggregation |
| `VisionDocumentSummarizer` | LSA-based multi-level summarization |
| `TemplateService` | Agent template management with 3-layer cache |
| `ThinClientPromptGenerator` | CLI prompt generation (thin prompts) |
| `MissionPlanner` | Fetch instruction generation |
| `SystemPromptService` | Customizable system prompts |

## APPENDIX: MCP TOOLS (30+)

**Orchestration**: get_orchestrator_instructions, spawn_agent_job, get_agent_mission, get_workflow_status, get_pending_jobs, report_progress, complete_job, report_error, get_agent_result

**Context (via fetch_context)**: product_core, vision_documents, tech_stack, architecture, testing, memory_360, git_history, agent_templates, project, self_identity

**Communication**: send_message, receive_messages, list_messages

**Project Management**: create_project, update_project_mission, update_agent_mission, create_task

**Lifecycle**: close_project_and_update_memory, write_360_memory

**Utility**: health_check, generate_download_token
