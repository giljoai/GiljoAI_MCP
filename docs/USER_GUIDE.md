# GiljoAI MCP: User Guide

*Last updated: 2026-06-04*

This guide covers every page and UI element in GiljoAI MCP. Read from top to bottom on first use, or jump to the section you need.

> **Self-hosting (Community Edition)?** The setup, optional HTTPS, and server-startup instructions are gathered at the end under **Self-Hosting & Network Setup**. Hosted (SaaS) users can skip that section entirely — your server and certificates are managed for you.

---

## Home Page

The Home page is the entry point after login. It shows a personalized greeting, your Quick Launch cards, your agent team roster, and either a setup prompt or your recent projects. Activating any product automatically returns you here, so Home is the per-product starting point.

### Quick Launch Cards

Cards appear at the top of the page. Their content adapts based on your onboarding state:

| Condition | Cards shown |
|---|---|
| Setup not complete | Quick Setup, Learn, New Product (as needed) |
| No product created | New Product (with attention animation) |
| Product exists, no projects | New Project + two starter templates (see below) |
| Active projects running | Active Projects, Dashboard, Task Board, Look Up |

Each card shows a title, description, and optional badge. Cards with a slash command badge (e.g. `/giljo add project`, `/giljo`) indicate that operation is also available from your AI coding tool. Clicking a card navigates to the relevant page or opens the relevant overlay.

The **Look Up** card (green, magnifier icon, `/giljo` badge) is a read-only lookup — it lets your AI tool find existing projects and tasks without write access.

### Starter Templates

When you have an active product but have not created any projects under it yet, two preset starter template cards appear next to **+ Create your first project**:

- **Bootstrap a new product** — scaffolds folders, README, and `requirements.txt`, and proposes follow-up development projects.
- **Import an existing product** — analyzes an existing codebase and seeds 360 Memory.

Clicking a template auto-creates a pre-filled project and takes you to the Projects page. Once a product has had its first project created, these cards do not reappear for that product (even if you later delete all its projects).

### Onboarding Hint Cards

Below the hero, up to two hint cards remind you to enable integrations (Git, Serena MCP) and to customize your agent templates. They greet you by name and are signed "-Gil." The integration hint disappears once both Git and Serena are enabled, so you are not nagged about things already done.

### Your Team

A team roster shows the orchestrator plus your active agent templates. Each agent shows a tinted initial badge, display name, and description. Empty slots show a plus icon. The slot count (e.g. "3 / 8 slots") appears in the header. Click "Manage" to go to Agent Template settings.

### Onboarding Flow

The page detects your setup state on mount and opens the appropriate overlay:

- First login with setup incomplete: the Setup Wizard opens automatically.
- Setup complete, learning guide not yet seen: the "How to Use GiljoAI MCP" guide opens after the wizard closes.
- Returning to Home with `?openSetup=true` in the URL: the Setup Wizard opens in re-run mode.
- Returning to Home with `?openGuide=true` in the URL: the learning guide opens directly.

The learning guide is also accessible any time from Tools, under the Startup tab.

#### Setup Wizard Steps

The wizard has four steps shown in a progress bar:

| Step | Label | What happens |
|---|---|---|
| 0 | Choose Tools | Select one or more AI coding tools (Claude Code CLI, Claude.ai / Desktop, Codex CLI / ChatGPT.com, Gemini CLI, Antigravity CLI) |
| 1 | Connect | Generate API keys and configure each selected tool |
| 2 | Install | Install the slash command skills on your machine |
| 3 | Launch | Confirm setup and get your first bootstrap prompt |

The wizard can be restarted any time from Tools > Startup.

### System Banners

Status banners may appear at the top of the page. They are now backed by the notification system, so a banner's state (including a dismissal) persists across page refreshes and browser sessions. Dismissible banners have an X; some banners (such as a lapsed subscription) clear only when the underlying condition is resolved. Community Edition system banners (pending migrations, update available, skills drift) link to the **Tools** page.

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

A full-width panel shows recent projects with their status, taxonomy badge, and completion date. Click "All Projects" to go to the Projects page. Click a project's Serial badge to open the Project Review modal.

### 360 Memories and Recent Commits

Two side-by-side panels appear at the bottom:

- **360 Memories:** Recent memory entries written at project completion, with links back to their source projects.
- **Recent Commits:** Git commits extracted from 360 Memory entries, shown as SHA + message + author.

---

## Products

Products sit at the top of the hierarchy: Product - Projects - Jobs - Agents. A product represents the software you are building. All projects, tasks, agents, and memories belong to a product.

### Creating a Product

Click "New Product" to open the product form. The Setup tab is **AI-first**:

1. Enter a **Name** (required).
2. Optionally attach one or more **vision documents** (`.md` or `.txt`, max 10 MB each).
3. If you attach a document, an optional **extraction-instructions** panel appears where you can steer what the AI pulls out.
4. The footer button moves through **Stage analysis → Analyzing… → Next** as the AI processes your document.

If a vision document is attached, the remaining tabs (Tech Stack, Architecture, Testing) and the **Next** button stay locked until analysis completes — a tooltip explains "Run analysis to unlock." Everything unlocks automatically when the AI finishes.

If you would rather fill in fields by hand, tick **Skip** (labeled "Not recommended") to bypass analysis and unlock all tabs immediately.

If you save a product with a name that duplicates an existing one, a blocking dialog appears ("Duplicate product name — pick a different name, or activate or rename the existing product"). Your typed fields are preserved behind the dialog.

> **Editing** an existing product never locks the tabs — the analysis gate applies only when creating a new product.

### Context Fields

The product form is organized into four tabs. Fields that are toggled on in Tools > Context become part of agent context at session start:

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

Upload your product proposal, architecture overview, or design spec as `.md` or `.txt` files. After upload, your AI coding tool analyzes the document and can populate the product fields automatically. The product card shows a "docs" badge and a "chunks" count once documents are processed.

In the Product Details dialog, the **Vision Context** section shows three context-depth tiers (33% / 66% / 100%) with token estimates, plus a per-document manifest listing each file's name, **Analyzed** status, size, and **Chunked** status.

If you do not have a vision document yet, start with a one-page brief: what the product does, who it is for, the core technical decisions, and what success looks like. That single page will improve every agent interaction that follows.

#### Keeping Vision Analysis Fresh

When you edit a product whose vision documents have changed since the last analysis, a warning banner appears on the Setup tab offering a one-click action to spawn a **Context Update (CTX)** project that re-analyzes the product. If analysis is already current, an "Already fresh" message appears instead.

### Tuning

Click the tune icon on a product card to open the Tuning dialog. Tuning lets you update product context fields when they have drifted from the actual codebase.

The workflow:

1. Select the sections you want to retune (description, tech stack, architecture, core features, codebase structure, etc.)
2. Click **Generate Tuning Prompt**. A structured prompt is produced; the view scrolls to it automatically so you can copy it to your clipboard.
3. Paste the prompt into your AI coding tool (Claude Code CLI, Claude Desktop, Codex CLI, Gemini CLI, or any MCP-compatible tool)
4. The agent scans the codebase, checks for drift between the stored context and the actual code, and presents findings section by section
5. Approve or reject each section's proposed changes in the tool's conversation
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
- **Series Number:** Sequential number within the type. When you pick a project type, this field auto-fills with the next available number for that type, so you do not have to look it up. The counter is scoped per product — a BE project in Product A and a BE project in Product B each have their own independent numbering.
- **Subseries:** Single-letter suffix for sub-tasks (e.g. BE-0001a).
- **Status:** Defaults to `inactive`.

Projects can also be created from your AI coding tool using `/giljo add project ...`.

### Opening a Project

In the Projects list, click a project's colored **Serial badge** (e.g. `BE-0042`) to open its Project Review. The rest of the row is selectable text, so you can copy a project's name or description without triggering navigation.

### Project Status and Protection

Projects move through several statuses as work progresses. Two statuses lock a project from further changes:

- **Completed:** Set automatically when the orchestrator closes out the project. A completed project cannot be edited or restarted. To re-do the work, duplicate the project from the project list.
- **Cancelled:** Set manually via the Cancel action on a project. Once cancelled, the project is locked and cannot be modified. Use this when you want to abandon a project while keeping its history.

Completed and cancelled projects are protected. Any attempt to change their fields (name, description, status, etc.) will be blocked with an error.

### Staging and Activation

Projects have two preparation states before they run:

- **Staged:** A bootstrap prompt has been generated and is ready to paste into your AI coding tool. The staged indicator shows a green checkmark in the project table.
- **Active:** The project is currently running. Only one project per product can be active at a time.

To activate and launch a project, click the play button in the project table row. If the project is already staged, activation resumes from the staged state. If it is not staged, the bootstrap prompt is generated first.

The bootstrap prompt includes: your product context, 360 Memory entries, project description, and agent template definitions. Paste this into your AI coding tool to start the orchestrator.

If a staging orchestrator finishes without spawning any specialist agents, staging is blocked and the project stays re-stageable (the Implement button stays disabled) so you can stage it again — it will not be left in a broken state.

### Project Phases

**Implementation Phase:** Agents execute the plan. In multi-terminal mode, phases run sequentially; within a phase, agents run in parallel. In CLI subagent modes (Claude Code CLI, Codex CLI, Gemini CLI), the orchestrator spawns all agents simultaneously.

**Closeout Phase:** When implementation is complete, the orchestrator requests your approval before closing the project. You review what was done, then approve. Once you approve, the orchestrator writes the 360 Memory entry and marks the project complete. The memory entry captures what was built, key decisions, patterns discovered, and what worked. This data flows into the next project automatically.

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
| Duration | Elapsed time since the agent started; for active agents this ticks live every second |
| Steps | Completed and skipped steps out of total (e.g. 3(1) / 8) |
| Messages Waiting | Count of unread messages from this agent |

Click the agent badge to open the Agent Details modal (shows role and template). Click the agent name to open the Job modal (shows assigned mission). Click the message count badge to open the Message Audit modal, whose waiting/read counts update live as messages arrive.

### Status Badges

Each agent displays one of the following statuses (this table doubles as the on-screen badge legend):

| Status value | Display label | Style |
|---|---|---|
| `waiting` | Waiting. | Yellow, italic |
| `working` | Working... | White, italic, animated dots |
| `blocked` | Needs Input | Orange, upright |
| `awaiting_user` | Needs Decision | Amber, upright (an approval is pending — see Agent Approvals) |
| `idle` | Monitoring | Steel blue, italic |
| `sleeping` | Sleeping | Soft purple, italic |
| `silent` | Silent | Orange, upright (agent stopped communicating) |
| `complete` | Complete | Green, upright |
| `handed_over` | Handed Over | Muted grey, upright |
| `decommissioned` | Decommissioned | Dark grey, upright |

An agent with `working` status shows a breathing glow animation on its badge and an expanding pulse ring.

At the moment staging finishes but before you click Implement, the orchestrator row shows **Waiting** rather than Complete, so it is clear the project is paused for you to launch implementation — not finished.

### Agent Display Names

When you spawn more than one agent of the same type in a project (for example, two implementer agents), GiljoAI MCP automatically assigns a numeric suffix to each one: the first is "implementer", the second is "implementer-2", the third is "implementer-3", and so on. You do not need to name them manually.

### Agent Approvals (Human-in-the-Loop)

When an agent needs a decision from you mid-work, it requests an approval. A clickable **approval banner** appears at the top of every page — one band per waiting agent, tinted with the agent's color and showing a preview of the request. (This is separate from project closeout.)

1. Click the banner to open the **Decision dialog**, a focused window showing the agent's reason and the available options (e.g. Approve / Reject / Defer). Read the agent's full reasoning in your AI chat before choosing.
2. Pick an option. Your decision is delivered to the orchestrator's inbox automatically.
3. The banner turns green: *"Orchestrator unlocked — Tell the orchestrator to read its message and proceed."* Nudge the orchestrator in your AI chat to check its inbox. The green band clears on its own once it does.

Multiple pending approvals stack as multiple banners.

### Auto Check-In

In multi-terminal execution mode, an Auto Check-In slider appears after staging. Drag the slider to set an interval (Off, 5, 10, 15, 20, 30, 40, or 60 minutes). When set to any interval other than Off, the orchestrator automatically checks in on sleeping agents at that cadence.

You can change the interval while the orchestrator is already running — the new value takes effect at the next check-in cycle. A hint ("Applies at next check-in.") appears below the slider in that case. Auto check-in does not appear in CLI subagent modes (Claude Code CLI, Codex CLI, Gemini CLI), where the orchestrator manages agent communication directly.

---

## Project Review

Clicking a project's Serial badge (from the Dashboard or Projects page) opens the Project Review modal. This modal gives a full breakdown of how the project was executed.

The modal is organized into expandable sections:

- **Agent Jobs:** Each agent job is shown as a collapsible card. Expand it to see its assigned mission, todo list, and step progress.
- **Agent Messages:** The message traffic between agents during the project — useful for understanding why decisions were made.
- **Git Commits:** Commits recorded during the project (requires git integration to be enabled in Tools > Connect).
- **360 Memory:** The memory entry written at closeout.

Closeout and agent approvals are separate flows. If an agent has a pending approval when you open the Close Out dialog, the dialog directs you to resolve it in the Decision dialog first (see Agent Approvals above).

---

## Tasks

The Tasks page is a board for tracking technical debt, scope captures, and development notes. Tasks are separate from projects: they represent work that has been identified but not yet scheduled.

### Task Board

Tasks display in a filterable table. The first column is a colored **Type+Serial badge** (e.g. `BE-0042`); a task with no type assigned shows an em-dash badge. Remaining columns include Title (with description), Status, Priority, and Created date. Click any task row to open the edit dialog.

Each row's overflow menu includes an **Archive/Unarchive** action. Archived tasks are removed from the default board view but reappear when you search or toggle **Show archived** in the action bar (they carry an **Archived** badge), and they remain available to your AI tool via `/giljo`.

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

**Statuses:** `pending`, `in_progress`, `completed`, `blocked`, `cancelled`

Status badges use brand colors from the server's canonical status registry.

### Creating and Editing Tasks

The Create Task dialog includes an optional **Serial** number field (placeholder "auto"); leave it blank to have the next number assigned automatically. In the Edit dialog, the Serial field shows just the number (e.g. `42`), not the full alias.

Promoting a task to a project (Convert to Project) creates a new **inactive** project and does **not** deactivate the product's currently-active project — you activate the new project yourself when you are ready.

### Filtering

The filter bar provides search by title, filter by status, and filter by priority. Search matches a task's title, description, **and** serial (e.g. searching `FE-0047` finds that task). All filters combine. Click "Clear Filters" to reset. Filters persist within the session but reset on page reload.

Tasks can also be created from your AI coding tool using `/giljo add task ...`. To look up tasks or projects without leaving your session, use `/giljo` — e.g. `/giljo what BE tasks are open?` or `/giljo show project BE-5040`.

---

## Tools

Navigate to **Tools** via the left navigation. Five tabs are available:

| Tab | Contents |
|---|---|
| **Connect** | External integrations (git repositories, MCP clients, API keys) that enrich 360 Memory and let coding agents connect to GiljoAI |
| **Agents** | Agent Template Manager: browse, create, edit, and activate agent templates |
| **Context** | Context priority configuration: toggle context fields, set depth per source, configure 360 Memory depth and git integration |
| **Notifications** | Toast position (top/bottom, left/center/right), display-duration slider, and (Community Edition) the agent silence threshold in minutes |
| **Startup** | Two cards: "Setup Wizard" (reopens the wizard) and "Learning" (reopens the "How to Use" guide) |

API keys are managed inside the **Connect** tab alongside the integrations they unlock.

### AI Tool Configuration (Connect)

The Connect tab's configuration wizard generates the exact connection snippet for each supported tool: **Claude Code CLI**, **Claude.ai / Desktop**, **Codex CLI / ChatGPT.com**, **Gemini CLI**, **Antigravity CLI**, and **Generic MCP**. Selecting Claude.ai / Desktop produces a `claude_desktop_config.json` snippet with an accordion showing the config-file location for Windows, macOS, and Linux.

The MCP server URL in the copied snippet adapts to your deployment: self-hosted (CE) installs include the explicit `:7272` port; hosted (SaaS) deployments omit it. On hosted deployments the certificate-trust step is hidden, because those certificates are already trusted.

### Git Integration

The Git integration card (Connect tab) works with any local git repository, not just GitHub. Its "Git Setup Guide" button links to git-scm.com. Enabling it lets GiljoAI record commit history into 360 Memory.

### Agent Silence Threshold

> [!CE]
> This setting is available in the self-hosted Community Edition only; it is hidden in hosted (SaaS) mode.

In the Notifications tab, the **Agent Silence Threshold (minutes)** input (1–60) controls how long an agent can go without communicating before it is marked "Silent." The value is saved to the database and persists across sessions.

### Installing Skills and Agents (`giljo_setup`)

The `giljo_setup` MCP tool — which you run from inside your AI coding tool, not the dashboard — installs the slash-command skills and agent templates onto your machine. It asks you to choose an install scope: **Both** (commands + agents), **commands/skills only**, or **agents only**. If agent files already exist, it asks once whether to overwrite or skip them; skills/commands are always refreshed.

---

## Admin Settings

Navigate to **Admin** via the left navigation (admin users only). The page title is "Admin Settings."

Runtime settings (git integration, Serena MCP, SSL mode) are stored in the database. Changes you make here take effect immediately without restarting the server.

Five tabs are available:

| Tab | Contents |
|---|---|
| **Identity** | Workspace name and member management |
| **Network** | External host, API port, frontend port, CORS origins, and SSL configuration |
| **Database** | Read-only view of PostgreSQL connection settings; includes a "Test Connection" button |
| **Security** | Cookie domain whitelist for multi-domain deployments |
| **Prompts** | Orchestrator system prompt editor |

If your session has a stale or missing organization record, the Identity tab shows a friendly empty state ("No organization found. Please contact your administrator.") rather than a raw error. Legacy URLs `/tools/identity` and `/settings/identity` redirect here automatically.

### User Profile

Your profile collects **First Name** and **Last Name** as separate fields; greetings throughout the app use your first name.

- **Community Edition:** Email changes apply immediately.
- **Hosted (SaaS):** Changing your email starts a verification flow — a banner shows the pending address with **Resend** and **Cancel** buttons, the email field is disabled until you confirm, and a confirmation link is emailed to the new address.

### Member Management

The User Manager kebab menu adapts by edition:

- **Community Edition:** "Change Password and PIN" for local credential management.
- **Hosted (SaaS):** "Send password reset email," which emails the user a reset link.

> [!CE]
> A recovery PIN is a Community Edition feature. On hosted GiljoAI you reset your password by email instead.

> The "Add User" button is currently hidden in all editions pending the future Team tier. First-install admin creation is unaffected.

### Account: Download My Data

On the Account > Danger Zone page, the **Download My Data** card exports a ZIP of all your products, projects, vision documents, agents, memory, tasks, and configuration (credentials redacted). Click **Generate Export**; a progress bar runs, and a download link valid for 15 minutes appears with a per-model record-count breakdown. Available to Community Edition users and to hosted (SaaS) organization admins.

> [!SAAS]
> **Hosted accounts include billing and subscriptions.** Plans, checkout, cancellation, resume, switching to annual, trial behavior, and how account deletion differs on a trial versus a paid plan are covered in the **Billing & Subscription** chapter, shown at the end of this guide on hosted accounts. The self-hosted Community Edition has no billing.

---

## 360 Memory and Follow-up Work

360 Memory entries are written by agents at project closeout. They capture what was built, decisions made, patterns found, and outcomes. Each subsequent project starts with this accumulated history available to the agent team.

### Reporting Follow-up Work

When an agent discovers a deferred item — technical debt, a known issue, or a decision that cannot be resolved in the current project — it creates an explicit follow-up using `mcp__giljo_mcp__create_task` (for single-step items) or `mcp__giljo_mcp__create_project` (for multi-step work). The returned ID is cited in `decisions_made` at closeout so the audit trail is intact.

Follow-up tasks and projects appear on your Task Board immediately and carry forward as first-class work items.

---

## UI Elements

### WebSocket Connection Icon

A status chip in the top navigation bar shows the real-time WebSocket connection state:

| State | Label | Color | Icon |
|---|---|---|---|
| Connected | Connected | Green | wifi |
| Connecting | Connecting... | Amber | wifi-sync (animated) |
| Reconnecting | Reconnecting (N/M) | Amber | wifi-sync (animated, pulsing) |
| Disconnected | Disconnected | Red | wifi-off |

Real-time updates recover automatically after a disconnect or server restart, so a manual refresh is rarely needed. Brief blips that recover within a couple of attempts no longer raise a toast — only a sustained outage (several consecutive failed reconnects) shows a "Connection lost" message, followed by "Connection restored" when it clears.

Click the chip to open the WebSocket panel, which shows the connection state and a **Force Reconnect** action for troubleshooting if the Jobs page ever stops updating. On screens narrower than 1024 pixels, only the icon is shown.

### Notification Bell

The notification bell appears in the top navigation bar. A badge count appears when there are unread notifications; its color indicates priority (amber for warnings, red for errors).

Notifications are stored server-side, so they persist across page refreshes and browser sessions. Each notification has its own **dismiss (X)** button that removes just that item; clicking the body of a notification marks it read and navigates to the related project (if one is linked) or page.

Notification types include:

| Type | When it appears |
|---|---|
| `api_key.expiring_soon` | An API key is within 7 days of expiring; clicking it opens Tools > Connect. Clears automatically when the key is revoked or regenerated |
| `agent_health` | An agent has been silent past the configured threshold |
| `agent_status` | An agent changed to a significant status |
| `project_update` | A project was updated or completed |
| `system_alert` | A system-level error or warning |
| `message_received` | An agent sent a message requiring attention |
| `connection_lost` / `connection_restored` | WebSocket connection was lost or restored |
| `context_tuning` | Context fields were updated after a tuning pass |
| `vision_analysis` | A vision document was processed |

Click "Mark all read" to clear the unread badge.

### Skills Drift Banner

When the slash-command skills installed on your machine are older than the version your server provides, an admin-only banner appears (brand yellow). To clear it, run `/giljo_setup` in your AI coding tool — this acknowledges the current skills version. On Community Edition the banner also reminds you to `git pull` and restart the server for the latest server build. The banner resurfaces if a newer version ships later.

### About Dialog

The About dialog (from the navigation drawer) shows the live running server version and the correct edition label (Community Edition or SaaS). The "Get a License" link appears only for unlicensed Community Edition installs.

---

## Self-Hosting & Network Setup

> [!CE]
> This entire section is for Community Edition (self-hosted) operators. Hosted (SaaS) users can skip it — your server, HTTPS certificates, and updates are managed for you.

### Starting and Restarting the Server

Run `python startup.py` to start the server. Restarting cleanly stops any previous instance first, so you will not end up with two servers running at once. The first request after a restart is pre-warmed to reduce cold-start latency.

Run `python startup.py --verbose` to open a live log-viewer window alongside the server. On Windows this is a separate PowerShell window with color-coded lines (errors red, warnings yellow, info cyan, debug grey); on macOS/Linux it opens in a terminal window. Closing the viewer does not stop the server.

### Unattended (Headless) Install — Windows

`install.ps1` supports a non-interactive install via environment variables, useful for CI or automated provisioning:

```
GILJO_UNATTENDED=1
GILJO_PG_PASSWORD=<required>
GILJO_DB_NAME=<optional, default: giljo_mcp>
GILJO_INSTALL_DIR=<optional>
```

When `GILJO_UNATTENDED` is not set, the installer runs interactively as before.

### HTTPS and Browser Configuration

GiljoAI MCP runs over plain HTTP by default (localhost and LAN). HTTPS is an opt-in upgrade you enable in **Settings → Network**, where you provide your own certificate (a real CA, your organisation's internal CA, or a local CA such as mkcert). The steps below apply when your certificate comes from a **local CA** (e.g. mkcert): its root certificate must be trusted on each client. Your AI coding tools trust it after following the setup instructions on the connection page. Web browsers on Linux, however, maintain their own certificate stores and require an extra step.

#### Obtaining a Certificate

GiljoAI does not create certificates — you bring your own, then provide it in **Settings → Network** (upload the PEM files, or reference them by path on the server). Pick whichever source your browsers and AI coding agents can trust:

**Option 1 — mkcert (recommended for local / LAN).** Creates a local certificate authority trusted by your own machine; works offline, no internet required:

```
# Install: winget install FiloSottile.mkcert  (Windows)
#          brew install mkcert                 (macOS)
#          sudo apt install mkcert             (Linux)
mkcert -install
mkcert -cert-file ssl_cert.pem -key-file ssl_key.pem localhost 127.0.0.1 ::1 your-server-ip
```

**Option 2 — Let's Encrypt (public-facing servers).** Free, globally trusted certificates; requires a public domain name and ports 80/443 reachable from the internet:

```
sudo certbot certonly --standalone -d yourdomain.com
```

**Option 3 — self-signed (quick, but every browser shows a warning until the cert is trusted).**

```
openssl req -x509 -newkey rsa:4096 -nodes -days 365 -keyout ssl_key.pem -out ssl_cert.pem -subj "/CN=localhost"
```

After providing the certificate, enable HTTPS from **Settings → Network** and restart the server. For mkcert and self-signed certificates, each client must then trust the root certificate — follow the steps below.

#### After Enabling HTTPS — Reconnect Your AI Tools

Switching between HTTP and HTTPS changes the server's URL (`http://…` becomes `https://…`), which invalidates your existing MCP connections. After you enable HTTPS in **Settings → Network**:

1. **Re-generate your connection commands** from the in-app Configurator (**Tools → Connect**) so each AI coding agent uses the new `https://` URL, then remove and re-add the connection in your tool.
2. **Trust the certificate in the agent's runtime** when it is self-signed or from a private CA. Node-based tools (Claude Code, Codex, Gemini CLI) keep their own trust store, so follow the Node.js trust step below — some agents (e.g. Gemini CLI) may need additional certificate-trust configuration for self-signed certificates.

#### First Connection

When you first navigate to your GiljoAI server from a workstation (e.g. `https://your-server-ip:7272`), your browser shows a "Your connection is not private" warning. This is expected. Click **Advanced** and then **Proceed**. The connection page provides a download link for the server's certificate and copy-paste commands to install it.

#### Installing the Certificate (Linux)

Follow the two commands provided on the connection page:

1. **System trust** (for curl, Node.js, and other system tools):

```
sudo cp ~/Downloads/rootCA.pem /usr/local/share/ca-certificates/giljoai.crt && sudo update-ca-certificates
```

2. **Node.js trust** (for AI coding tools):

```
mkdir -p ~/.giljo && cp ~/Downloads/rootCA.pem ~/.giljo/rootCA.pem && echo 'export NODE_EXTRA_CA_CERTS="$HOME/.giljo/rootCA.pem"' >> ~/.bashrc && source ~/.bashrc
```

These two commands are sufficient for MCP connections and CLI tools. Your browser will still show "not secure" until you complete the browser-specific step below.

#### Chrome / Chromium (Linux)

Chrome on Linux uses its own NSS database, not the system store. After installing the system certificate above, run:

```
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n "GiljoAI" -i ~/Downloads/rootCA.pem
```

If `certutil` is not installed:

```
sudo apt install libnss3-tools
```

After adding the certificate, clear Chrome's cached security state (it cached the "not trusted" result from your first visit):

1. Press `Ctrl+Shift+Delete` to open the Clear Browsing Data dialog
2. Check **Cached images and files**
3. Click **Clear data**
4. Navigate to your GiljoAI server again

The padlock icon should now show a secure connection.

#### Windows

Windows users do not need the extra browser step. The `certutil -addstore "ROOT"` command provided on the connection page trusts the certificate (your local-CA root) for both system tools and all browsers.

#### macOS

The `security add-trusted-cert` command provided on the connection page trusts the certificate system-wide, which covers Safari and Chrome. Firefox on macOS may still require the `security.enterprise_roots.enabled` setting (see below).

#### Firefox (all platforms)

Firefox uses its own certificate store on all operating systems and ignores both the system store and the NSS database used by Chrome. To trust the GiljoAI certificate in Firefox, choose one of these methods:

**Option A — Use the system store (recommended):**

1. Open `about:config` in the Firefox address bar
2. Search for `security.enterprise_roots.enabled`
3. Set it to `true`
4. Restart Firefox

**Option B — Manual import:**

1. Open `about:preferences#privacy`
2. Scroll to **Certificates** and click **View Certificates**
3. Go to the **Authorities** tab
4. Click **Import** and select the `rootCA.pem` file from your Downloads folder
5. Check **Trust this CA to identify websites** and click OK
