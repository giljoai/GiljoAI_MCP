> **Note (2026-03-07):** References to SaaS timelines in this document predate the GiljoAI Community License adoption. Current strategy: Community Edition first, SaaS fork later (timing TBD). See LICENSING_AND_COMMERCIALIZATION_PHILOSOPHY.md.

---
**Document Type:** Product Vision & User Journey
**Last Updated:** 2025-01-05
**Related Documents:** [start_to_finish_agent_FLOW.md](./start_to_finish_agent_FLOW.md) (technical verification), [dynamiccontext_patrik.md](./dynamiccontext_patrik.md) (dynamic agent discovery & context modes)
**Harmonization Status:** ✅ Aligned with codebase (Handovers 0088, 0102, 0073)
---

[Developer note] I need to harmonize terminology in this document: **"product"** refers to the top-level organizational unit (a software product being built), **"project"** refers to work initiatives under a product, **"tasks"** are work items that can exist standalone or under a product, and **"jobs"** are the execution phases when agents work on a project. This document describes both the **GiljoAI application itself** and the **products/projects/tasks/jobs as features within the application**. I may have used these terms inconsistently throughout - keeping this note as a clarification.

### Product vision realized?

This MCP server is intended to help developers using CLI coding tools terminal based in Windows or Linux or Mac such as claude codex and gemini. One of the major problems is the tracking of context the tracking of technology stack the tools the dependency and everything else when vibe and context coders are building products particularly as a singular developer where you have to track a lot of these things.

The purpose was to create a form and field based documentation of a product to make sure that all bases are covered but that the developer doesn't always have to remember them when they vibe and context code.

So the very first thing that this product does is allows a developer to create a product under that product is project and then these projects get executed with some aggregation of context and preparation of agents and summarization of a mission etc I will go into more of those details later in this post/

The other thing I'm trying to solve with this product is that while you're interacting with the agentic CLI coding tools ideas pop up and it's very easy to get sidetracked and distracted and in order to stay disciplined and not lose good ideas when they happen is to be able to quickly punt them over or flip them over into a task list to be addressed later. And that's where the task list comes in in this product.

Much of this worked in my earlier MCP Lab Develop application and now I decided to build it more commercial friendly.

Meaning I want it to be shared and hopefully get some traction on Github where people can keep building on it But I also wanted a downloadable from our business web page to show show that we like to share in our progress as a company particularly around tools and our openness and showing the commitments to the AI development community.

I also wanted to build a product to be ready to be a potential SaaS in the future if somebody did not want to run it on their laptop or on a LAN server but rather have it hosted because this is MCP over HTTP.

So I'm hoping that the foundations for all what I've described is there and now I will go into some more detail.

## Tennancy and Heirachy

For the product to support initial multi user functions as a server we created tenancies the tenancies are built around a user.  This I believe is going to serve as a foundation should we make a Saas application out of this.

In the future I see expanding the product where multiple developers can use AI agentic coding tools and collaborate on the same product sharing projects for accelerated development.  But for right now we've isolated it to one developer with his or her multiple products.

From a hierarchy perspective a product is the top of the hierarchy and under that falls projects, also within the product are tasks. Once a product is activated all the projects created belong to that product and tasks that the developer flips into the task list also belong to that product. Tasks can be converted to **projects** at any time (Tasks cannot become products - they remain under the current active product).

- All projects are tennanted per product
- All tasks , when a product is active, belong to the product
- Tasks can be added with no active product, and if so have a NULL value and appear under all products until assigned.

Customized agents are also under each user tenant, When the user account is created a default set of six agents are created but the user can add and customize more agents.

**Note on agent templates**: Six default agent templates are seeded per tenant (**orchestrator**, **implementer**, **tester**, **analyzer**, **reviewer**, **documenter**). This is a recommended starting set, **not a technical limitation**. The codebase supports unlimited agent templates - users can create, customize, and activate as many agent types as needed for their workflow.

**Technical Reference**: See `src/giljo_mcp/template_seeder.py` for complete template definitions and seeding logic. For technical verification of the full agent flow, see `handovers/start_to_finish_agent_FLOW.md`.

**⚠️ Context Budget Warning**: When using Claude Code, limit active agents to **8 maximum**. Each agent's template description consumes context budget, reducing available tokens for your project. The 6 default templates are designed to fit comfortably within this limit while covering most development scenarios.

# Agents

All agents are tenanted under each user and are spawned as 6 default templates as a user gets created.  The user can also create customized or modify the agent as they need.

## Agent Template System & Caching (Handover 0041)

The agent template system uses a three-layer caching architecture for performance:
- **Memory LRU cache** (<1ms lookups) - Fast in-process cache
- **Redis cache** (<2ms lookups) - Shared cache across processes
- **Database** (<10ms lookups) - Persistent storage with multi-tenant isolation

### Template Resolution Cascade

When an agent is spawned, the system resolves templates using this priority order:
1. **Product-specific template** (highest priority) - Custom templates for specific products
2. **Tenant-specific template** (user customizations) - User's modified templates
3. **System default template** - The 6 seeded defaults
4. **Legacy fallback** - Ensures operations always succeed

This allows users to customize agent behavior at different scopes: globally (tenant level) or per-product. The dashboard includes a Monaco editor for template customization with real-time preview and diff comparison against defaults.

We have one primary and important agent called the Orchestrator. The orchestrator is a well-prompted and templated staging agent in this application and as a project gets launched its job is to aggregate all contexts around the product and the project description, harmonize the mission, divide up the jobs and assign them to the proper agents. The orchestrator is also or should also be the primary interface for the developer and all other subagents should report to the orchestrator.

## Context Prioritization and Orchestration (Handover 0088)

The orchestrator achieves **strong context prioritization and orchestration** through intelligent context management:
- **Mission Planner** (`mission_planner.py`) - Generates condensed missions from vision docs, avoiding context duplication
- **Agent Selector** (`agent_selector.py`) - Smart agent selection based on capabilities, assigning only necessary agents
- **Workflow Engine** (`workflow_engine.py`) - Coordinates waterfall/parallel execution, preventing redundant context loading
- **Field Toggle System** - Only includes enabled fields in missions, with depth controls for token management (Handover 0048, 0049)
- **Template Resolution Cascade** - Efficient template loading without redundant database hits (Handover 0041)

Instead of flooding agents with ALL product context, the orchestrator intelligently extracts, condenses, and prioritizes information. This means agents get exactly what they need to do their work - nothing more, nothing less.

**Technical Reference**: For detailed verification of the token reduction architecture, see `handovers/start_to_finish_agent_FLOW.md`.

For the dynamic agent discovery design and how the same context stack (Product description, Vision documents, Tech Stack, Architecture, Testing notes, Agent templates, 360 Memory, Git history) is applied consistently across Claude Code subagent mode and general multi-terminal CLI mode, see `handovers/dynamiccontext_patrik.md`.

**Implementation Status**: Research and implementation sessions (documented in archived `handovers/completed/0246_series/`) confirmed that the execution-mode infrastructure was substantially complete: backend endpoint with `claude_code_mode` flag, functional Implementation-tab toggle, and comprehensive staging prompt workflow. The system successfully moved from a 600-token fat prompt to a ~450-token thin, dynamic-context prompt.

The key restriction we have in this application is the lack of automation The closest we have is the MCP message communications but that only works while the agents are active.  so there will always be in need for the developer to nudge agents along in their various terminal windows to read messagesi  In the future states it would be amazing if that could be automated and perhaps we build the terminal into the application or find ways to inject commands into active terminals.

Claude stands out in this because with Claude we can end one prompt launch the orchestrator and it could spawn subagents through its own internal communications protocol So this will always work a little bit smoother with Claude but there's nothing preventing the developer to even with Claude just like Codex and Gemini work in multiple CLI terminal windows copy prompts to trigger the agents and then regularly nudge them along to communicate and do the job.

The application includes agent template export for Claude Code via **My Settings → Integrations** only (manual user-triggered export). The export uses a secure download token system (Handover 0102) with 15-minute expiration. Users control when and which templates to export - no automatic export occurs during project workflows.

### Agent Template Export System (Handover 0102)

The export process uses a token-based download system for security and efficiency:
1. **Generate Token**: User clicks "Export Agents" button in My Settings → Integrations
2. **Token Creation**: System creates one-time download token (15-minute TTL)
3. **ZIP Generation**: Backend packages active agent templates into ZIP file with YAML frontmatter
4. **Copy Command**: User copies CLI installation command with tokenized download URL
5. **CLI Installation**: User pastes command into terminal (Claude Code, Codex CLI, or Gemini CLI)
6. **Template Registration**: CLI tool downloads ZIP, extracts to `~/.claude/agents/`, registers in MCP

**8-Role Cap**: Export enforces maximum 8 distinct agent roles (unlimited agents per role type).

**Technical Reference**: For detailed verification of the export and download system, see `handovers/start_to_finish_agent_FLOW.md` (Steps 2-3).

Agents should have strict prompting to regularly check in and communicate via MCP and that should be in their agent profiles today.

* [Developer note] I don't think we have created an integration where the application reads the currently deployed agents that Claude has nor have we implemented how the user can modify agents we only have one time all agent integration function so we need to explore this.

# Products

There can only be one active product at any given time per tenant, and within each product only 1 active project at any given time. This is enforced at the database level with partial unique indexes (atomic, race-condition-proof). We do this for simplicity and focus, but technically all entities have unique IDs allowing for future expansion to support multiple concurrent active items if needed.

The developer should be motivated to fill out as much documentation as possible around the product it would help with the context.

## Vision Documents (Multi-Vision Support - Handover 0043)

Products support multiple vision documents, not just a single vision file. Each product can have architectural docs, feature specifications, API documentation, coding standards, and more. Vision documents support:
- **File-based storage** (upload files from disk)
- **Inline text storage** (write directly in the dashboard)
- **Hybrid mode** (both file + inline content)
- **Versioning** with semantic versioning (e.g., v1.0.0, v1.1.0)
- **Content integrity** via hash checking
- **Active/inactive states** for archiving old versions
- **Chunking for RAG** when feeding context to agents

This allows comprehensive product context without cramming everything into a single massive document.

# Projects 

As mentioned earlier projects could be created from tasks, The tasks could flipped from an active chat in the Agentic CLI tool or be a human entry.  It is important when it's converted into a project that it keeps its name and the text and the text field becomes a description.

Projects are also all human entered This is where the developer describes what they want to get done and gives it a title When the orchestrator first kicks off is when it merges all the context debth, Knowledge of the code the tech stack the formalities the dependencies etc and builds a mission and divides it up between agents.

## Project Description vs Mission (Handover 0062)

It's important to understand the distinction between two key project fields:
- **Description** (`Project.description`): Human-written project goal by the developer. This is what YOU want to accomplish, written in your own words. This field is user-editable and captures your intent.
- **Mission** (`Project.mission`): AI-generated by the orchestrator. After analyzing the product context, vision documents, tech stack, and your description, the orchestrator creates a detailed mission statement with specific tasks, context, and agent assignments. This is auto-populated and represents the orchestrator's interpretation and expansion of your description.

The description stays user-controlled; the mission is the orchestrator's work plan.

**Technical Note**: Both fields exist in the `projects` table. The UI displays the human `description` in the "Project Description" window and the AI-generated `mission` in the "Orchestrator Created Mission" window during project staging.

Projects can have various states like I mentioned earlier only one project may be active at any time If the user or developer creates multiple projects they will remain inactive They can have canceled projects they can have completed projects and they can delete the projects.

A deleted project should be a soft delete that firmly deletes after 10 days and can be restored until then.

Note when a user shifts from one product to the other all active projects under the previous product automatically cascade to paused state, as only one active product per tenant and only one active project per product can be valid at any given time.

When a project is activated a launch button appears this redirects the user to a project launch preview.

# Tasks

Tasks are the flexible work item management system within GiljoAI, designed to capture ideas and action items during active development sessions without losing focus or momentum.

## Task Hierarchy & Scope

Tasks exist within the product hierarchy but have unique flexibility:
- **Product-scoped tasks**: When a product is active, all newly created tasks belong to that product
- **Unassigned tasks**: Tasks can be created with no active product, receiving a NULL value and appearing under all products until converted to a project.
- **Cross-product visibility**: Unassigned tasks remain visible across all products until explicitly converted to a project under a product and then subsequently attached to a product of which that project now belongs.

## Task Creation Methods

### MCP Integration for Real-Time Capture
The primary strength of the task system is **real-time capture during coding sessions**:
- **MCP task tools**: Add tasks directly from conversations with Claude Code, Codex CLI, or Gemini CLI
- **Instant capture**: When ideas pop up during active development, quickly punt them to the task list without losing focus
- **Context preservation**: Tasks capture the moment and context when the idea occurred

### Dashboard Interface
- **Manual entry**: Create tasks directly through the web interface
- **Structured input**: Add detailed descriptions, priorities, and categorization

## Task-to-Project Conversion

One of the most powerful features is the ability to **convert tasks into projects**:
- **Name preservation**: When converted, the task name becomes the project title
- **Description migration**: The task text field becomes the project description
- **Seamless workflow**: Ideas captured as tasks can mature into full projects without data loss
- **Constraint**: Tasks cannot become products - they remain under the current active product

## Task States & Management

Tasks support various lifecycle states:
- **Active**: Current work items requiring attention  
- **Completed**: Finished tasks for reference and history
- **Converted**: Tasks that have been promoted to projects
- **Archived**: Old or no longer relevant tasks

## Developer Workflow Integration

The task system addresses a common developer problem: **idea management during flow state**. Instead of:
- Losing good ideas when they occur
- Getting sidetracked from current work
- Forgetting important action items

Developers can:
- Quickly capture ideas via MCP during active coding
- Stay disciplined and focused on current project
- Review and prioritize tasks during planning sessions
- Convert promising tasks into full projects when ready

## MCP Function Details

The task MCP functions provide:
- **Multi-tenant isolation**: All task operations respect user tenancy
- **Real-time sync**: Tasks created via MCP immediately appear in dashboard
- **API key authentication**: Secure communication ensuring tasks route to correct tenant
- **Cross-tool compatibility**: Works with Claude Code, Codex CLI, and Gemini CLI

This system ensures that the creative and iterative nature of AI-assisted development doesn't result in lost ideas or broken focus, while providing a clear path for task maturation into full development projects.

# Project Launch Preview

The project launch preview is where the orchestrator agent is configured and the project is prepared for execution. This interface uses a dual-tab layout (**Launch** and **Implementation** tabs) accessible via the custom project link (e.g., `http://10.1.0.164:7274/projects/{project_id}?via=jobs`).

## Stage Project Flow

When you click the **"Stage Project"** button (which technically calls `POST /api/v1/projects/{id}/activate`), the orchestrator:
1. Reads the human-written project description from the database
2. Retrieves product context (vision documents, tech stack, dependencies)
3. Applies field toggle/depth settings from "My Settings" to optimize token usage
4. Generates a condensed mission statement (displayed in "Orchestrator Created Mission" window)
5. Selects appropriate agents from active templates (max 8 roles, unlimited per type)
6. Creates agent cards that appear live in the "Agent Team" window
7. Creates `MCPAgentJob` records with initial status `"waiting"`

**Technical Reference**: For detailed technical verification of the staging process, see `handovers/start_to_finish_agent_FLOW.md` (Phase 4: Project Orchestration).

The orchestrator can be activated by clicking the copy prompt button and pasting it into the CLI tool to get working. The mission populates on-screen for the user to see and review, and agent cards appear as they get selected.

We also have a token counter based on the mission prompts and the agent prompts as a totality. The token estimation system (Handover 0048, 0049) helps keep context within AI tool limits (Claude Code's 25K token input limit being the primary target).

We also have a "Cancel" option during the launch phase which restores the project to a blank slate and returns it to the project list, removing any created mission and any assigned agents.

Once the developer is happy with the initial staging, they proceed to activate the actual work and move to the Implementation tab (Jobs pane).

# Jobs (Agent Job Management - Handovers 0019, 0020)

The Jobs system manages the full lifecycle of agent execution with multi-tenant isolation and real-time updates.

## Agent Job Lifecycle

Each agent job moves through these states during execution:
1. **Waiting** - Agent job created, waiting for agent to claim it (initial status after staging)
2. **Active** - Agent has acknowledged the job and begun coordination
3. **Working** - Agent actively executing tasks (can receive messages and report progress)
4. **Terminal States**:
   - **Complete** - Agent finished successfully
   - **Failed** - Agent encountered errors
   - **Blocked** - Agent cannot proceed (waiting for user input or dependency)

**Status Transitions**: `waiting → active → working → complete/failed/blocked`

The system tracks job metadata including assigned agents, prompts, start/end times, execution results, and progress percentage. WebSocket events (`job:status_changed`, `job:completed`, `job:failed`) provide real-time updates to the dashboard, allowing users to monitor agent activity in the Implementation tab.

**Technical Reference**: For MCP tool verification and job management details, see `handovers/start_to_finish_agent_FLOW.md` (Phase 5: Agent Execution).

## Agent Communication Queue

Agents communicate through the `agent_communication_queue` which stores JSONB messages for:
- **Agent-to-agent messages** - Direct communication between agents
- **Broadcast messages** - Messages sent to all agents
- **Orchestrator directives** - Commands from the orchestrator to sub-agents
- **User messages** - Developer instructions to agents

All messages are tenant-isolated and persisted for audit trails.

## Tool-Specific Workflows

**For Claude Code**: Only one prompt needs to be copied into the same window as the orchestrator. Claude Code's sub-agent spawning feature handles the rest automatically.

**For Codex/Gemini**: Multiple copy-pastes are required - each agent gets its own terminal window and prompt must be pasted individually to activate each agent.

At this stage the agents are communicating over the MCP message hub as needed and the user will be able to see this in the message pane.  As the agents finish or have questions or need more directions the user will have to in the application today go into each terminal window and nudge the agents along it should be encouraged to only speak to the orchestrator's terminal window for the orchestrator to create messages either as a broadcast or to a specific agent because this allows a clawed code user to again leverage the sub agent capability and the user of codecs and Gemini all they have to do is copy paste a quick message And I mean a hand type copy paste not a button in the app to read their message or say that they have a message pending as the communications for audit and history occurs through the MCP message center.

Once the user is satisfied there is a closeout function at the bottom of the jobs pane to decommission all the agents to wrap up the project to handle git commits documentation etc.

## Project Closeout Workflow (Handover 0073)

When all agents complete their work, the project closeout system activates. The orchestrator can generate:
- **Orchestrator Summary**: Final project completion report summarizing all work done, decisions made, and outcomes achieved
- **Closeout Checklist**: Automated checklist covering git commits, documentation updates, dependency updates, test runs, and cleanup tasks
- **Closeout Prompt**: Ready-to-execute bash commands for final project tasks (commits, pushes, tagging, etc.)
- **Execution Tracking**: Timestamp tracking when closeout was executed (`closeout_executed_at`)

This ensures projects don't just "end" - they close out properly with documentation, version control updates, and a clean audit trail. The static agent grid layout (Handover 0073) also ensures agent cards maintain consistent positions throughout the project lifecycle.

# Token Management & Field Toggles (Handovers 0048, 0049, 0820)

We have a comprehensive token management system to keep context within AI tool limits (Claude Code's 25K token input limit being the primary target).

## Token Estimation API

The system includes a real-time token estimation endpoint (`/api/products/{product_id}/token-estimate`) that calculates token usage for mission generation based on:
- Active product fields and their toggle/depth settings
- Vision documents (chunked with depth controls)
- Project descriptions
- Tech stack and dependencies
- Agent template content

This allows developers to see token estimates BEFORE launching the orchestrator, preventing context overload.

## Field Toggle Configuration

Users configure **which product fields** get included in missions via simple on/off toggles, plus depth controls for how much data to serve per category:
- **Enabled fields** (toggle: true): Included in missions with configured depth
- **Disabled fields** (toggle: false): Excluded from missions entirely

Depth controls (e.g., vision documents depth, 360 memory depth, git history commit count) give fine-grained control over how much data each enabled category provides.

This toggle-based approach keeps context within tool limits while giving users simple, clear control over what context agents receive.

# MCP Integration (Native Support - Handover 0069)

We have native MCP integration for three major AI coding tools:
- **Claude Code** - Full MCP support via `claude-code mcp add` command
- **Codex CLI** - Native MCP support via `codex mcp add` command
- **Gemini CLI** - Native MCP support via `gemini mcp add` command

Users configure MCP in **My Settings → MCP Configuration** with one-click copy commands. The system provides both the command-line integration method (recommended) and manual configuration instructions.

Agent templates include a `tool` field that specifies which CLI tool the agent is designed for (`claude`, `codex`, or `gemini`), allowing tool-specific optimizations and behaviors. Multi-tenant isolation is maintained through API keys, ensuring all MCP communications route to the correct tenant.

# API key

We have an API key function in the application for future integrations but it's primarily used today for integrating the MCP communications over HTTP and assuring that the communications go to the right tenant.

# Installation

The installation process uses `install.py` as the primary entry point and must work across Windows, Linux, and macOS environments. The installer handles:
1. PostgreSQL database setup and table creation
2. **Alembic migrations** (Step 6.5) - including migration `6adac1467121` which adds agent template columns
3. **First user creation** - triggers automatic seeding of 6 default agent templates per tenant
4. API server configuration and launch

**Installation Sequence**:
- Database tables created → Migrations applied → First user created → Templates seeded → API started

**Technical Reference**: For complete installation flow verification and database migration details, see `handovers/start_to_finish_agent_FLOW.md` (Phase 1: Installation & Setup).

# database

The database uses PostgreSQL with primary operation on the same machine as the application (localhost). The codebase supports remote PostgreSQL connections via connection string configuration in `config.yaml`, though local operation is recommended for security and performance.

# Dependancies

At some point we need to harmonize dependencies and make sure we're not installing and wasting time with dependencies that we do not need anymore.

# LAN/WAN/HOSTED

The application as such should work on the same machine as a developer with local host if they want and over land and Wan with IP address out the gate I'm not quite sure how it works with DNS and host name but we should investigate this in the future.  We will also begin building it as a SaaS Service in the next quarter or so.

# Mini LLM (FUTURE NOT HERE YET)

It would be wonderful to expand the orchestration portion to be ran as CPU or GPU micro LLM to trigger agents or activate agents on the user's workstation but we may have to end up in an Electron app or something similar in the future instead.

## 360 Memory Management

**Vision**: Products accumulate knowledge automatically, providing orchestrators with historical context and learned patterns.

**User Benefit**:
- No manual knowledge management required
- Orchestrators get smarter over time (learn from past projects)
- Project learnings never lost
- GitHub integration or manual summaries (user choice)

**Technical Implementation**:
- Product memory in JSONB column (flexible schema)
- Sequential history tracking (ordered timeline)
- Real-time updates via WebSocket
- MCP tool for orchestrator closeouts

**Example Use Case**:
1. Project 1: "Setup" - Orchestrator establishes architecture (FastAPI + React)
2. Project 2: "Features" - New orchestrator sees Project 1 decisions, builds on them
3. Project 3: "Optimization" - Orchestrator understands full history, optimizes accordingly

**Why This Matters**:
- Each orchestrator instance is stateless
- Without memory, every project starts from zero context
- With memory, projects build cumulative intelligence

# Integrations

Today we have a Serena MCP integration and is a wonderful tool and we must make sure we promote it properly in settings It really helps this application do its work and the agents do their work.  Another potential is to allow for local LLM potentially through climb or even through Ollama LMStudo Or other tools.

* [Developer note] 
We need to ensure that the Serena integration is built into the prompting of all the agents

# Automations (CONSIDERATION)

We have discussed and explored the possibility to run background bash jobs with clawed code to regularly have orchestrator paying for new messages and check and nudge agents along and to "go to sleep" Forcing the user to remind Claude that has messages waiting but I'm not quite 100 percent sure how this would be executed practically yet.

# Dev Control Panel (LOW PRIORITY)

The dev control panel has been a lifesaver and I'm not sure yet how to build that in to the application as administrator tool in some capacity that is something to be considered.

# How a user would work with the product

let's go through an entire user journey with the product.
The user creates an account and logs in
Agent templates are populated in their user settings
User finds their way to MCP integrations and copies the command for their agentic CLI tool of choice and that links and attaches itself to the MCP server

**Agent Export for Claude Code** (Manual Only):
- Users export agent templates via **My Settings → Integrations → Export Agents** button
- Exports ALL active templates to `.claude/agents/` directory
- Creates `.old.YYYYMMDD_HHMMSS` backup files before overwriting existing agents
- **⚠️ Recommendation**: Export no more than **8 agents maximum** - each agent description reduces available context budget for your project. Claude Code recommends 6-8 agents for optimal performance.
- User has full control over when to export and which templates to activate

The user creates a product and defines it and uploads division slash product description
The user now creates the first project perhaps Asking the tool to prepare the foundational layout for the overall product
Perhaps in their agentic CLI tool discussing options with the AI and using the MCP task tools to add tasks directly from their conversation, or adding tasks via the dashboard task interface. Tasks can be created either way - through MCP tools during coding sessions or manually through the web interface
 what decisions they want to make or how they want to use the things discussed what decisions they want to make or how they want to use the things discussed The user decides to activate the first project and gets a launch button
 This takes them to project launch dashboard or panel where they get a prompt for the orchestrator sees their handwritten project description and copy the prompt
 They paste the prompt in the CLI tool which has been started in the project folder and the orchestrator being the first agent begins building the mission by compiling the context and the project description
 The Mission field in the Project launch window populates with the mission and Agent cards start showing up which the orchestrator has started selecting
 The user reviews everything and can choose to cancel or to proceed
 When they proceed they get to the jobs pain and in the jobs pain they will see a prompt for orchestrator for Claude code which they will copy and paste into cloud code For clawed code this will spawn subagents and they will match they already displayed agent cards on the screen which show various status and information If the orchestrator is now communicating with these agents that will start showing up in the message center
 If he's using other agentic coding tools like Codex or CLI not only does the orchestrator have a copy prompt but all the agent cards also have copy prompts and the user copies all of them individually to CLI windows to activate the agents and as the agents start working and if they are communicating that shows up in the message pane
 The user can view the progress either in the terminal CLI windows or glance at the dashboard as it keeps updating while the agents are communicating and progressing with their work
 Should the user see messages in the message center that require attention or need to communicate with agents, the user can either broadcast a message to all agents using the message center or queue a message for a specific agent (especially the orchestrator). Naturally, the user can also just chat directly with the orchestrator in the terminal window. The benefit of routing communication through the MCP message center is that there's a complete audit trail and history log for the entire project
 At some point everybody will be finished and report in that they're finished and a user can choose to closeout the project which will follow a closeout protocol such as git commits git push documentation decommissioning agents etc
 Now the user can move on to the next project that they wish
 At anytime they can go to the dashboard and sort historically by product by projects or by everything Things have been happening and if they zoom in to a project they can even see the communications that occurred between the agents and have a link to the summary document and what happened during this session They get commit references etcetera

# Welcome and Tutorial (ONCE WE GET PAST BETA)

We need to create some sort of workflow tutorial with screenshots that takes the US through how to use the product in the welcome screen.

# Notificatoins (FUTURE, NOT SURE HOW TO USE)

We need to determine what type of notifications we need in the notifications bar we might even explore some sort of gamification if the user uses the product a lot that could be fun but that's just an extremely nice to have at some point messages could for when agents such as the orchestrator or other specifically wants the user's attention or if there is a in the product I'm not quite sure yet

# Password recovery

Password recovery is implemented via a 4-digit PIN system (Handover 0023). Users can generate recovery PINs with rate limiting and lockout protection (5 failed attempts = 15 minute lockout). The system includes PIN hash storage, expiration tracking, and secure validation. Email-based recovery could be a future enhancement for additional security options.

### clarification on slash commands and agent tempalte imports
we have in our frontend allready one "copy command" button for slash commands, this is the one working now, it gives the a working token folder (even if 102 proposes cleaning up the code) and it properly installs the slash commands. we also in the front end have an existing "copy command" for what we call product agents (claude terminlolgy is project agents) these agents reside in %projectfolder%/.cladue/agents folder. we also have a "copy command" button that is for personal agents, these are global agent profiles residing in %userprofile%/.claude/agents  we need to reuse these buttons as I want the user to use our applicationinterface to simply copy the commands, paste them into the CLI agentic coding tool of choice, and it should know for all three scenarios to go to a token based URL, fetch zip, install files in right folder. with agent back up, but slash commands files can be overwritten.  we also have in each section a "manual downlaod link" both for slash commands and one aggregated one for the agents.  This file for slash commands downloads the zip (tempalted as nothing changes dynamically here and slash_instructions.md) , for agents the click first compiles a ZIP of the active agents, and attaches agent_instructions.md and the dev can self install. one enhancement that can be made is, that as a user interfaces with the agent template manager and toggles agents on and off, we can allready then payload the zip file.  likewise if an agent is updated via edit tools in the agent template manager we can also payload when the uer clicks save, but perhaps its easier done at time of
link click for eother "copy command" or "manual download" as a trigger.  what are your thoughts based on all   you ave red and this input


## A simplified work flow description and relationships

BTW (our heigharcy is tennant user -> products -> projets and tasks) under Projects you have orhcestrator (team lead, comms lead, architect and project mannager ) -> Subagents (Spawned by orchestrator to do work in a project) , we also have "Project Description" a human written defined scope / instent and "misson" mission is a orchestrator created summary after analyzing all context, product documentation attached to the product what we call (vision), reviewing users context priority configurator in "My settings" context [TAB].  This mission gets then divided into work for the subagetns to deliver on, and if they need more context or information, they go to the orchestrator and it will fetch it.

## The integration interface

MCP integration
MCP configurator is a button [CONFIGURATOR] that launches a wizard which creates a copiable MCP installation command for CLI, unique for claude code , codex and Gemeni

Slash commands
Slash commands will grow in the server as exposed meny items inside the CLI tool.  The intent for this is to downlaod the slash command files and install them in a proper folder.  We acheive this through two paths.  [COPY COMMAND] Button, this button copies an MCP and natural language instruction to the CLI tool (of choice) to fetch from a URL pointing at a token time limited folder (as of the press of the button) the ZIP file witht he commands and instructs the CLI agent to install them.  Finally it tells the end user to reboot the application.  As an option we also have manual download link which direclty downlaods the zip + slash_instructions.md

Agent Export
Agent export is where we simplify agent export and import into claude code (only supported at time of writing).  There are two ways to installa gents.  One is per project folder (we call it product agents becuase a project folder is for a product in our narrative), the other is personal, These go to the users profile folder on the OS and work globally accross all their project folder.  The user choses how to do it.

[COPY COMMAND] is a button in line for personal
[COPY COMMAND] is a button inline for produt (project folder on PC)

Both upon click, create a token time limited folder, then fetches the agents which are toggled as active in the "Agent Template Manager", adds their individual files into a zip and places it in the tokenized folder.  Also when clicked the button copies to clip board the URL and natural langage instructions for the agent files.  Instructions say to backup existing agents into a folder MMDDYY_Agent_backup, and then extracts the newly downloaded agents from the zip.  Finally it tells the end user to reboot the application.  As an option we also have manual download link which triggers the server to add active agents to a zip file and add agent_instructions.md a static file on how to installe them in personal or product folder.

Finally we have a resolved Serena integration that is customizable and tells the user to install Serena MCP first.

