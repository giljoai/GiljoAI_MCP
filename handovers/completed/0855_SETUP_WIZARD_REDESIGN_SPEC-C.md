# Setup Wizard Redesign — Handoff Brief

**Priority:** High — CE Launch Blocker  
**Scope:** Home screen button behavior, new overlay wizard, removal of product explainer from setup flow  
**Decision Authority:** Patrik Gil  
**Date:** 2026-03-25

---

## Problem Statement

The current "Setup Quick Start" button on the Home screen navigates to My Settings → Startup Tab, which opens with a "What is GiljoAI MCP" product explainer — architecture diagrams, feature descriptions, platform explanations. This is wrong. A user who has installed the application, created an account, and logged in does not need a product pitch. They need to connect their tools and start working.

The entire explainer-first flow must be removed from the setup path. The setup must become an action-oriented checklist that gets the user from first login to a working system as fast as possible.

---

## What Changes

### 1. Home Screen — Button Redesign

**Current:** "SETUP QUICK START" button sits in a row below Dashboard / Products / Projects buttons.

**New:** Reposition the Setup Quick Start button directly below the GiljoAI logo/icon, above the greeting text. Make it visually prominent — this is the primary action for a new user. Keep the same button label: **"Setup Quick Start"**.

**First-login behavior:** On first login (user flag `setup_complete: false`), the overlay should auto-launch. The user does not need to find and click the button on their first visit.

**Subsequent incomplete visits:** If `setup_complete` is still `false`, show the button prominently with label **"Resume Setup"**. Do not auto-launch on subsequent visits — let the user choose when.

**After setup complete:** Replace the button with **"How to Use GiljoAI MCP"** — this is where the current product explainer content (architecture overview, how agents work, how slash commands fit in) should live permanently. It becomes a learning resource, not a gate.

### 2. Overlay Wizard — New Component

The button launches a **full-screen overlay** on top of the Home screen. Not a navigation to My Settings. Not a modal dialog. A dedicated overlay that:

- Covers the main content area (dashboard visible but dimmed behind it)
- Survives browser tab switches (state persisted via `setup_complete` flag and per-step completion tracking on the user record)
- Has a "Do this later" dismiss option (X or button) at all times
- Shows a stepped checklist with visual progress

**Route:** No route change needed. The overlay is a component rendered on the Home view, controlled by state. The user stays on `/home` throughout.

### 3. Remove Explainer from Setup Path

**Delete from setup flow:** The "What is GiljoAI MCP" content, the architecture diagram walkthrough, and any product explanation screens that currently appear when navigating from Setup Quick Start. None of this belongs in the setup path.

**Relocate to:** The "How to Use GiljoAI MCP" button that appears on the Home screen after setup is complete. This content has value — just not during onboarding.

---

## Wizard Steps — Detailed Specification

The overlay contains a **4-step checklist** displayed as a vertical stepper or horizontal progress bar. Each step expands when active. Completed steps show a green checkmark. The user can click back to review completed steps but cannot skip ahead.

### Step 1: Select Your AI Tool

**Purpose:** Prerequisite acknowledgment + tool selection that carries forward into all subsequent steps.

**UI:**
- Heading: "Which AI coding tool(s) do you use?"
- Subtext: "You need an active subscription to at least one of these tools. GiljoAI connects to them — it does not replace them."
- Three selectable cards (multi-select enabled):
  - **Claude Code** — logo + "Anthropic" subtitle
  - **Codex CLI** — logo + "OpenAI" subtitle
  - **Gemini CLI** — logo + "Google" subtitle
- Each card is a toggle (outline when unselected, filled/highlighted when selected)
- Below cards: "Don't have one yet? [Install Claude Code](link) · [Install Codex CLI](link) · [Install Gemini CLI](link)"
- **"Next" button** enables when at least one tool is selected

**Data stored:** `selected_tools: ["claude_code", "codex_cli", "gemini_cli"]` — persisted on user record so the wizard remembers on re-entry.

**No OpenClaw.** Remove from this flow. If added later, it can be included here.

---

### Step 2: Connect to GiljoAI

**Purpose:** Install MCP configuration into the user's selected AI tool(s) so the tool can communicate with the GiljoAI server.

**UI:**
- Heading: "Connect your tool to GiljoAI"
- If multiple tools selected in Step 1: show as **tabs** (one tab per tool). If single tool: no tabs, show directly.
- Each tool tab contains the **existing MCP Configuration Tool component** — but rendered inline, not as a modal popup.
  - Server URL field (pre-filled with `https://localhost:7272`, editable)
  - **"Generate Configuration"** button
  - PowerShell / Linux+macOS toggle
  - Environment Variable field with copy button (Codex, Gemini)
  - Configuration Command field with copy button
  - HTTPS certificate warning (Gemini only — existing yellow alert)
- Below the config section, a divider, then:
  - Instruction text: *"After pasting the config and restarting your tool, ask it to run a GiljoAI health check."*
  - **Connection status indicator** per tool:
    - Default state: `○ Not connected` (gray)
    - On first successful health check detected by server: `● Connected` (green) — update via WebSocket listener
- **"Next" button** enables when at least one tool shows "Connected"

**API Key behavior change (new):**
- The "Generate Configuration" button must **check for an existing active API key** for this user before creating a new one.
- If an active key exists: retrieve it, display the config using that key. Do NOT generate a new key.
- If no active key exists: generate one, store it, display the config.
- Button label changes after first generation: **"Generate Configuration"** → **"Show Configuration"**
- This prevents API key sprawl from repeated wizard visits.

**Backend requirement:** Endpoint or logic change in the API key generation flow. Before `INSERT`, query for existing active key for this user. Return existing if found.

**WebSocket requirement:** The wizard overlay must listen for MCP health check events. When the server detects a health check from a tool matching this user's API key, push an event that the overlay catches to flip the connection status indicator. Do not implement as page-refresh polling.

---

### Step 3: Install Commands & Agents

**Purpose:** Install slash commands/skills and agent templates into the user's AI tool(s) via the bootstrap prompt.

**UI:**
- Heading: "Set up slash commands and agents"
- Per connected tool (from Step 2), show:
  - **Bootstrap prompt** — copyable text block. This is the existing consolidated bootstrap prompt (Path B) that installs slash commands + skills in a single action.
  - Instruction: *"Paste this into your [tool name] terminal. It will install slash commands and skills, then ask you to restart."*
  - **Mini-checklist** (auto-updating via WebSocket when server detects these events):
    - `○ Slash commands installed` → flips to `● Slash commands installed` when server detects the fetch
    - `○ Agents downloaded` → flips to `● Agents downloaded` when server detects agent export fetch
  - After slash commands installed, show:
    - Reminder text: *"After restarting your terminal, run this command to install agents:"*
    - Command display: `/gil_get_agents` (copyable) — **this stays visible on screen so the user can copy it after a reboot without losing it**
  - Note below agent install: *"The agent installer will ask about model preferences. We recommend 'Use default model for all' for first-time setup. You can customize per-agent later from the dashboard."*
- For Codex specifically: the bootstrap installs skills first, then instructs the user to run `$gil-get-agents` skill. Reflect this two-step nature in the Codex-specific instructions.
- **"Next" button** enables when at least one tool shows both checkboxes green. Also allow a "Skip — I'll do this later" link for users who want to proceed without agents.

**WebSocket requirement:** Same pattern as Step 2. Server pushes events when it detects:
- Bootstrap prompt fetch (slash commands/skills downloaded) → check first box
- `/gil_get_agents` or `$gil-get-agents` fetch (agent templates downloaded) → check second box

---

### Step 4: You're Set Up — Next Steps

**Purpose:** Confirm setup is complete, teach the user the product hierarchy (Product → Project → Tasks), and give them a clear choice of what to do first. This is NOT a form — it's a launchpad.

**UI:**
- Heading: **"Congratulations! You're set up!"**
- Progress bar showing all 4 steps complete (green checkmarks)
- Divider, then subheading: **"NEXT STEPS"**
- Three cards in a row, matching the existing completion screen pattern:

**Card 1: Add a Product**
- Icon: Product icon (existing)
- Subtitle: "Your top-level container"
- Body: *"Create a product to hold your vision, architecture, context, and long-lived memory. This is what keeps agents focused and consistent."*
- Button: **"OPEN PRODUCTS"** → closes overlay, navigates to Products page

**Card 2: Add a Project**
- Icon: Project icon (existing)
- Subtitle: "Incremental work inside a product"
- Body: *"Create a project to describe the work you want to implement. Projects are incremental and historical 'units of work' inside a product."*
- Button: **"OPEN PROJECTS"** → closes overlay, navigates to Projects page

**Card 3: Add Tasks**
- Icon: Tasks icon (existing)
- Subtitle: "User-managed TODO tracking"
- Body: *"Add tasks to capture technical debt and ideas as you work, and keep your execution aligned without breaking focus."*
- Button: **"OPEN TASKS"** → closes overlay, navigates to Tasks page

- Below the cards: **"Go to Dashboard"** link — closes overlay, sets `setup_complete: true`, lands on Home/Dashboard without navigating to a specific page.

**Any action on this screen (clicking a card button OR "Go to Dashboard") sets `setup_complete: true` and closes the overlay.** The user has completed the technical setup; what they do next is their choice.

**Note:** The existing completion screen (shown in My Settings → Startup Tab) has a 6-step progress bar: "Installed AI coding agents → Attach MCP server → Install slash commands → Reviewed agents → Tuned context → Configure integrations." This must be updated to match the new 4-step wizard: "Select AI tool → Connect to GiljoAI → Install commands & agents → Done." Remove "Reviewed agents," "Tuned context," and "Configure integrations" — these are post-setup configuration activities, not onboarding steps.

---

## State Management

### User Record Fields (new or modified)

| Field | Type | Purpose |
|---|---|---|
| `setup_complete` | boolean, default `false` | Controls overlay auto-launch on first login, button label on Home |
| `setup_selected_tools` | JSON array, nullable | Persists tool selection across wizard sessions |
| `setup_step_completed` | integer, default `0` | Tracks highest completed step (1-4) for resume behavior |

### Overlay Resume Behavior

When the overlay opens and `setup_step_completed > 0`:
- Show all completed steps as collapsed with green checkmarks
- Auto-expand the first incomplete step
- Re-check live connection status (tools may have connected while overlay was closed)

---

## What NOT to Build

- **No product explainer in the setup flow.** No "What is GiljoAI MCP" screens. No architecture diagrams. No feature walkthroughs.
- **No navigation to My Settings.** The overlay is self-contained. My Settings retains its Startup Tab for post-setup configuration access, but the first-run wizard never sends the user there.
- **No Serena MCP, Git integration, or custom agent creation in the wizard.** These are configuration activities for later. The wizard gets the user to a working baseline.
- **No OpenClaw in tool selection.** Add when supported.

---

## Implementation Notes

### Alembic Migration Required
The new user record fields (`setup_complete`, `setup_selected_tools`, `setup_step_completed`) require an Alembic migration. Create a proper migration file — do not rely on `Base.metadata.create_all()` for schema changes to an existing table.

### WebSocket Events — Verify Before Building
The wizard depends on real-time WebSocket events for three server-side detections:
1. MCP health check received (Step 2 — connection status)
2. Slash command/skill bootstrap fetch (Step 3 — first checkbox)
3. Agent template export fetch (Step 3 — second checkbox)

**Check whether these events already exist in the WebSocket event system.** The backend currently emits 6 event types for job management. The health check, bootstrap fetch, and agent export fetch may NOT have corresponding WebSocket events today. If they do not exist, this is net-new backend work — add event emission at the relevant endpoint handlers and register new event types. Do not skip this; the auto-updating checklist is a core UX requirement, not a nice-to-have.

---

## Files Likely Affected

- `frontend/src/views/Home.vue` — button repositioning, overlay trigger, first-login auto-launch
- `frontend/src/components/setup/` — new overlay wizard component with stepper
- `frontend/src/components/setup/WelcomePasswordStep.vue` — may need refactoring or removal from setup flow
- `frontend/src/components/AIToolSetup.vue` — refactor to render inline (not modal-only), add API key existence check
- `frontend/src/utils/websocket.js` — listen for health check and bootstrap fetch events
- `backend: API key generation endpoint` — add existing key check before creation
- `backend: user model` — add `setup_complete`, `setup_selected_tools`, `setup_step_completed` fields
- `backend: WebSocket events` — emit events on MCP health check, slash command fetch, agent export fetch

---

## Acceptance Criteria

1. First login auto-launches the setup overlay on top of Home screen
2. Overlay persists across tab switches (state-driven, not DOM-driven)
3. "Do this later" dismisses overlay; Home screen shows "Resume Setup" button
4. Step 1 allows multi-select of AI tools, persists selection
5. Step 2 shows per-tool MCP config inline (not as modal), respects existing per-tool differences (Codex two-step, Gemini cert warning, Claude single command)
6. Step 2 "Generate Configuration" checks for existing API key before creating new one
7. Step 2 connection status updates automatically via WebSocket on health check
8. Step 3 shows bootstrap prompt with persistent command display (survives reboots/tab switches)
9. Step 3 mini-checklist auto-updates via WebSocket on slash command and agent fetch events
10. Step 3 recommends "default model for all" during first-time agent import
11. Step 4 shows completion message with three Next Steps cards: Add Product, Add Project, Add Tasks — each linking to the relevant page
12. Clicking any card button or "Go to Dashboard" sets `setup_complete: true` and closes overlay
13. Progress bar on completion screen shows 4 steps (not the old 6-step bar) — "Select AI tool → Connect to GiljoAI → Install commands & agents → Done"
14. After setup complete, Home screen button changes to "How to Use GiljoAI MCP"
15. No product explainer, architecture diagram, or "What is GiljoAI MCP" content appears anywhere in the setup flow
