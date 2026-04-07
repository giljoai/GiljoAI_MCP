# GiljoAI MCP: User Guide

*Last updated: 2026-04-07*

This guide covers every page and UI element in GiljoAI MCP. Read from top to bottom on first use, or jump to the section you need.

---

## Home Page

The Home page is the entry point after login. It shows a personalized greeting, your Quick Launch cards, your agent team roster, and either a setup prompt or your recent projects.

### Quick Launch Cards

Three cards appear at the top of the page. Their content adapts based on your onboarding state:

| Condition | Cards shown |
|---|---|
| Setup not complete | Quick Setup, Learn, New Product (as needed) |
| No product created | New Product (with attention animation) |
| Product exists, no projects | Dashboard, New Project, Task Board |
| Active projects running | Active Projects, Dashboard, Task Board |

Each card shows a title, description, and optional badge. Cards with a slash command badge (e.g. `/gil_add project`) indicate that operation is also available from your CLI tool. Clicking a card navigates to the relevant page or opens the relevant overlay.

### Your Team

Below the Quick Launch cards, a team roster shows the orchestrator plus your active agent templates. Each agent shows a tinted initial badge, display name, and description. Empty slots are shown with a plus icon. The slot count (e.g. "3 / 8 slots") appears in the header. Click "Manage" to go directly to Agent Template settings.

### Onboarding Flow

The page detects your setup state on mount and opens the appropriate overlay:

- First login with setup incomplete: the Setup Wizard opens automatically.
- Setup complete, learning guide not yet seen: the "How to Use GiljoAI MCP" guide opens after the wizard closes.
- Returning to Home with `?openSetup=true` in the URL: the Setup Wizard opens in re-run mode.
- Returning to Home with `?openGuide=true` in the URL: the learning guide opens directly.

The learning guide is also accessible any time from User Settings under the Startup tab.

#### Setup Wizard Steps

The wizard has four steps shown in a progress bar:

| Step | Label | What happens |
|---|---|---|
| 0 | Choose Tools | Select one or more AI coding tools (Claude Code, Codex CLI, Gemini CLI) |
| 1 | Connect | Generate API keys and configure each selected tool |
| 2 | Install | Install the slash command skills on your machine |
| 3 | Launch | Confirm setup and get your first bootstrap prompt |

The wizard can be restarted from User Settings.

---

## Dashboard

The Dashboard shows system-wide statistics for the active product.

### Stat Pills

Three stat pills appear at the top. Each pill shows a count, a mini bar chart, and a color-coded legend:

- **Status Distribution:** Total projects broken down by status (active, completed, staged, cancelled, terminated).
- **Taxonomy:** Projects broken down by project type (e.g. Backend, Frontend, API).
- **Agent Roles:** Total agents spawned, broken down by role type.

### Mini Stats Row

Six compact counters appear below the stat pills:

| Counter | Description |
|---|---|
| Active | Projects currently in active status |
| Tasks | Total tasks across all statuses |
| API Calls | Total FastAPI calls recorded |
| MCP Calls | Total MCP tool calls recorded |
| Exec: Auto | Projects run in automatic execution modes (multi-terminal, CLI tools) |
| Exec: Supervised | Projects run in supervised execution mode |

### Projects Panel

A full-width panel shows recent projects with their status, taxonomy badge, and completion date. Click "All Projects" to go to the Projects page. Click any project row to open the Project Review modal.

### 360 Memories and Recent Commits

Two side-by-side panels appear at the bottom:

- **360 Memories:** Recent memory entries written at project completion, with links back to their source projects.
- **Recent Commits:** Git commits extracted from 360 Memory entries, shown as SHA + message + author.

---

## Products

Products sit at the top of the hierarchy: Product - Projects - Jobs - Agents. A product represents the software you are building. All projects, tasks, agents, and memories belong to a product.

### Creating a Product

Click "New Product" to open the product form. Required field: **Name**. The form also supports uploading vision documents (`.md` or `.txt`, max 10 MB each) before saving. Vision documents are chunked and embedded automatically.

If you upload a vision document before filling in context fields, GiljoAI creates the product silently to get a UUID, then uploads the files. If you close the form without saving, that temporary product is deleted.

### Context Fields

The product form is organized into four tabs. Fields that are toggled on in User Settings > Context become part of agent context at session start:

**Product Info tab:**
- **Description:** What the product does and who it is for.
- **Core Features:** Main functionality and capabilities.
- **Brand & Design Guidelines:** Visual style, colors, and fonts for frontend work.
- **Codebase Folder:** Local path to the codebase (used during tuning).

**Tech Stack tab:** Programming languages, frontend frameworks, backend frameworks, databases and storage, infrastructure and DevOps, target platforms.

**Architecture tab:** Primary architecture pattern, design patterns and principles, API style and communication, architecture notes, coding conventions and standards.

**Testing tab:** Quality standards, testing strategy, coverage target, testing frameworks and tools.

### Vision Documents

Vision documents are the most impactful input you can give GiljoAI. A well-written product proposal, architecture spec, or feature brief gives every agent session a shared understanding of what you are building and why. Without one, agents work from field-level context alone. With one, they understand scope, constraints, trade-offs, and intent.

Think of the vision document as the bridge between deciding what to build and building it. Upload your product proposal, architecture overview, or design spec as `.md` or `.txt` files (max 10 MB each). After upload, the server chunks and optionally summarizes the document. The product card shows a "docs" badge and a "chunks" count when documents are processed.

You can then use the "Use AI coding agent" option on the Product Setup tab to have your AI tool analyze the document and populate product fields automatically. This is the fastest way to go from a written spec to a fully configured product context.

If you do not have a vision document yet, start with a one-page brief: what the product does, who it is for, the core technical decisions, and what success looks like. That single page will improve every agent interaction that follows.

### Tuning

Click the tune icon on a product card to open the Tuning dialog. Tuning lets you update product context fields when they have drifted from the actual codebase.

The workflow:

1. Select the sections you want to retune (description, tech stack, architecture, core features, codebase structure, etc.)
2. Click **Generate Tuning Prompt**. A structured prompt is produced and can be copied to your clipboard
3. Paste the prompt into your CLI tool (Claude Code, Codex CLI, Gemini CLI, or any MCP-compatible tool)
4. The agent scans the codebase, checks for drift between the stored context and the actual code, and presents findings section by section
5. Approve or reject each section's proposed changes in the CLI conversation
6. Approved changes are applied directly to the product fields in GiljoAI MCP. There is no separate review step in the dashboard

The `context_tuning` notification in the bell menu appears after a tuning pass applies changes to a product.

Only one product can be active at a time. Activating a new product while another is active shows a confirmation dialog.

---

## Projects

### Creating a Project

Click "New Project" to open the project form. Each project belongs to the active product. Fields:

- **Name (required):** Free text description of the work.
- **Description:** What this project delivers.
- **Project Type:** Taxonomy category (e.g. BE for Backend, FE for Frontend, API). Determines the taxonomy alias badge (e.g. BE-0001).
- **Series Number:** Sequential number within the type.
- **Subseries:** Single-letter suffix for sub-tasks (e.g. BE-0001a).
- **Status:** Defaults to `inactive`.

Projects can also be created from your CLI tool using `/gil_add add project ...`.

### Staging and Activation

Projects have two preparation states before they run:

- **Staged:** A bootstrap prompt has been generated and is ready to paste into your CLI tool. The staged indicator shows a green checkmark in the project table.
- **Active:** The project is currently running. Only one project per product can be active at a time.

To activate and launch a project, click the play button in the project table row. If the project is already staged, activation resumes from the staged state. If it is not staged, the bootstrap prompt is generated first.

The bootstrap prompt includes: your product context, 360 Memory entries, project description, and agent template definitions. Paste this into your CLI tool to start the orchestrator.

### Project Phases

**Implementation Phase:** Agents execute the plan. The orchestrator assigns work to agents by phase. In multi-terminal mode, phases run sequentially; within a phase, agents run in parallel. In CLI subagent modes (Claude Code CLI, Codex CLI, Gemini CLI), the orchestrator spawns all agents simultaneously.

**Closeout Phase:** When implementation is complete, the orchestrator writes the 360 Memory entry and marks the project complete. The memory entry includes what was built, key decisions, patterns discovered, and what worked. This data flows into the next project automatically.

---

## Jobs

The Jobs page (accessed via a project detail view or the navigation) shows the real-time agent monitoring table for a running project.

### Agent Monitoring

The agent table shows one row per agent:

| Column | Description |
|---|---|
| Phase | Orchestrator shows "Start"; subagents show their phase number (P1, P2, etc.); subagent-mode agents show "All" |
| Play button | Copy the agent's launch prompt to the clipboard |
| Agent Name | Tinted initial badge + display name + skill template name |
| Agent Status | Current status with color coding (see Status Badges below) |
| Duration | Elapsed time since the agent started |
| Steps | Completed and skipped steps out of total (e.g. 3(1) / 8) |
| Messages Waiting | Count of unread messages from this agent |

Click the agent badge to open the Agent Details modal (shows role and template). Click the agent name to open the Job modal (shows assigned mission). Click the message count badge to open the Message Audit modal.

### Status Badges

Each agent displays one of the following statuses:

| Status value | Display label | Style |
|---|---|---|
| `waiting` | Waiting. | Yellow, italic |
| `working` | Working... | White, italic, animated dots |
| `blocked` | Needs Input | Orange, upright |
| `idle` | Monitoring | Steel blue, italic |
| `sleeping` | Sleeping | Soft purple, italic |
| `silent` | Silent | Orange, upright (agent stopped communicating) |
| `complete` | Complete | Green, upright |
| `handed_over` | Handed Over | Muted grey, upright |
| `decommissioned` | Decommissioned | Dark grey, upright |

An agent with `working` status shows a breathing glow animation on its badge and an expanding pulse ring.

### Auto Check-In

In multi-terminal execution mode, an Auto Check-In slider appears after staging. Drag the slider to set an interval (Off, 5, 10, 15, 20, 30, 40, or 60 minutes). When set to any interval other than Off, the orchestrator automatically checks in on sleeping agents at that cadence. Set it to Off to disable. Auto check-in does not appear in CLI subagent modes (Claude Code CLI, Codex CLI, Gemini CLI), where the orchestrator manages agent communication directly.

---

## Tasks

The Tasks page is a board for tracking technical debt, scope captures, and development notes. Tasks are separate from projects: they represent work that has been identified but not yet scheduled.

### Task Board

Tasks display in a filterable table with these columns: Status, Priority, Title (with description), Category, and Created date. Click any task row to open the edit dialog.

### Categories and Priorities

**Categories:**

| Value | Purpose |
|---|---|
| `general` | Uncategorized work |
| `feature` | New functionality |
| `bug` | Defect or regression |
| `improvement` | Refactor or enhancement |
| `docs` | Documentation work |
| `testing` | Test coverage or test tooling |

**Priorities:** `low`, `medium`, `high`, `critical`

**Statuses:** `pending`, `in_progress`, `completed`, `blocked`, `cancelled`, `converted`

### Filtering

The filter bar provides search by title, filter by status, and filter by priority. All filters combine. Click "Clear Filters" to reset. Filters persist within the session but reset on page reload.

Tasks can also be created from your CLI tool using `/gil_add add task ...`. The tool passes title, description, status, priority, and category.

---

## User Settings

Navigate to User Settings via the top navigation. The page title is "My Settings." Six tabs are available:

| Tab | Contents |
|---|---|
| **Startup** | Two cards: "Setup Wizard" (reopens the wizard) and "Learning" (reopens the "How to Use" guide) |
| **Notifications** | Position (top/bottom, left/center/right), display duration slider, and agent silence threshold in minutes |
| **Agents** | Agent Template Manager: browse, create, edit, and activate agent templates |
| **Context** | Context priority configuration: toggle context fields, set depth per source, configure 360 Memory depth and git integration |
| **API Keys** | Manage API keys for connecting your CLI tools to GiljoAI |
| **Integrations** | External integrations (git repositories and other sources that enrich 360 Memory) |

---

## Admin Settings

Navigate to Admin Settings via the top navigation (admin users only). The page title is "Admin Settings." Five tabs are available:

| Tab | Contents |
|---|---|
| **Identity** | Workspace name and member management |
| **Network** | External host, API port, frontend port, CORS origins, and SSL configuration |
| **Database** | Read-only view of PostgreSQL connection settings; includes a "Test Connection" button |
| **Security** | Cookie domain whitelist for multi-domain deployments |
| **Prompts** | Orchestrator system prompt editor |

---

## UI Elements

### WebSocket Connection Icon

A status chip appears in the top navigation bar showing the real-time WebSocket connection state:

| State | Label | Color | Icon |
|---|---|---|---|
| Connected | Connected | Green | wifi |
| Connecting | Connecting... | Amber | wifi-sync (animated) |
| Reconnecting | Reconnecting (N/M) | Amber | wifi-sync (animated, pulsing) |
| Disconnected | Disconnected | Red | wifi-off |

Click the chip to open the WebSocket Debug Panel. The panel shows:

- Connection state, client ID, WebSocket URL, and timestamps.
- Message statistics (sent, received, queued, connection attempts).
- Active subscriptions list.
- Recent event history (last 10 events).
- Actions: Force Reconnect, Simulate Drop, Send Test, Clear Queue.
- Debug Mode toggle for verbose logging.

On screens narrower than 1024 pixels, only the icon is shown; the text label is hidden.

### Notification Bell

The notification bell appears in the top navigation bar. A badge count appears when there are unread notifications. The badge color indicates priority: amber for warnings, red for errors.

Click the bell to open the notification dropdown. Notification types include:

| Type | When it appears |
|---|---|
| `agent_health` | An agent has been silent past the configured threshold |
| `agent_status` | An agent changed to a significant status |
| `project_update` | A project was updated or completed |
| `system_alert` | A system-level error or warning |
| `message_received` | An agent sent a message requiring attention |
| `connection_lost` | WebSocket connection was lost |
| `connection_restored` | WebSocket connection was restored |
| `context_tuning` | Context fields were updated after a tuning pass |
| `vision_analysis` | A vision document was processed |

Click "Mark all read" to clear the unread badge. Click a notification to navigate to the related project if one is linked. Click the message body to expand or collapse long notification text.
