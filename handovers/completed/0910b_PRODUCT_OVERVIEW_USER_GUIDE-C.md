# Handover 0910b: Write PRODUCT_OVERVIEW.md and USER_GUIDE.md

**Edition Scope:** CE
**Date:** 2026-04-06
**From Agent:** Orchestrator (0910 kickoff)
**To Agent:** documentation-manager
**Priority:** High
**Estimated Effort:** 3-4 hours
**Status:** Not Started
**Series:** 0910 Documentation Overhaul (subagent 2 of 4, runs after 0910a)

---

## Task Summary

Write the two user-facing documents: PRODUCT_OVERVIEW.md and USER_GUIDE.md. These ship with CE and are the first things a new user reads. Content must come from reading actual frontend components and stores, not from stale docs. Heavy effort.

---

## Critical Rules (read before touching anything)

1. No em dashes anywhere. Use colons, semicolons, and periods. Not "this -- that". Use "this: that".
2. No emoji in any document body.
3. Read actual code and components for current behavior. Do not copy from anything in /docs (it is stale).
4. Do not reference handover numbers in output documents. Users do not know what handovers are.
5. Do not reference internal architecture decisions or history. Write for users and contributors.
6. Active voice. Direct sentences. No filler.
7. Prefer tables and bullet lists over long paragraphs.
8. No document exceeds 1000 lines.
9. Activate venv before any code inspection: `source /media/patrik/Work/GiljoAI_MCP/venv/bin/activate && export PYTHONPATH=.`
10. Use absolute paths for all bash commands. The working directory resets between bash calls.

---

## Context

0910a has already archived all stale docs and created scaffold files with section headers. This subagent fills in PRODUCT_OVERVIEW.md and USER_GUIDE.md from scratch by reading source code.

The learning content lives in `SetupWizardOverlay.vue` as `LEARNING_SECTIONS` (six collapsible sections rendered when `mode === 'learning'`). Read that file directly for the six section titles and content. Do not paraphrase from memory.

---

## Dependencies

**Requires:** 0910a complete (scaffold files exist at /docs/PRODUCT_OVERVIEW.md and /docs/USER_GUIDE.md).

**Runs in parallel with:** 0910c (different output files, no conflict).

---

## Source Files to Read

Read these files before writing anything. Extract current behavior from the source, not from any doc.

| File | What to Extract |
|------|-----------------|
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/components/setup/SetupWizardOverlay.vue` | LEARNING_SECTIONS constant (6 sections with titles and content arrays) and STEPS constant (4 setup steps) |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/views/WelcomeView.vue` | Quick launch card logic, greeting, onboarding flow, what triggers the setup wizard vs learning modal |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/views/DashboardView.vue` | Stats shown, recent projects, recent memories |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/views/ProductsView.vue` | Products page structure |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/views/ProjectsView.vue` | Projects page structure, staging/activation flow |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/components/projects/JobsTab.vue` | Job monitoring, status badges, phase tracking |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/views/TasksView.vue` | Task board, categories, priorities, filtering |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/views/UserSettings.vue` | User settings tabs |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/views/SystemSettings.vue` | Admin settings tabs |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/components/ConnectionStatus.vue` | WebSocket connection icon behavior |
| `/media/patrik/Work/GiljoAI_MCP/frontend/src/components/navigation/` (list and read nav components) | Notification bell, nav structure |

---

## Implementation Plan

### Phase 1: Read source files

Read each source file listed above. Extract:

- Section titles and exact content from `LEARNING_SECTIONS` in SetupWizardOverlay.vue
- The 4 wizard STEPS names
- What the WelcomeView renders: cards, greeting text, what quick launch cards are shown and when
- Dashboard stats
- Products, Projects, Jobs, Tasks page structure and key UI elements
- Settings tab names (both User and Admin)
- ConnectionStatus component behavior
- Notification bell component name and behavior

Use grep to find component names efficiently:

```bash
grep -n "LEARNING_SECTIONS\|STEPS\|section\|title\|content" \
  /media/patrik/Work/GiljoAI_MCP/frontend/src/components/setup/SetupWizardOverlay.vue | head -60
```

```bash
ls /media/patrik/Work/GiljoAI_MCP/frontend/src/components/navigation/
```

```bash
grep -n "tab\|Tab\|v-tab\|:text\|title" \
  /media/patrik/Work/GiljoAI_MCP/frontend/src/views/UserSettings.vue | head -40
```

```bash
grep -n "tab\|Tab\|v-tab\|:text\|title" \
  /media/patrik/Work/GiljoAI_MCP/frontend/src/views/SystemSettings.vue | head -40
```

```bash
grep -n "connected\|disconnected\|WebSocket\|ws\|socket" \
  /media/patrik/Work/GiljoAI_MCP/frontend/src/components/ConnectionStatus.vue | head -30
```

### Phase 2: Write PRODUCT_OVERVIEW.md

Write to `/media/patrik/Work/GiljoAI_MCP/docs/PRODUCT_OVERVIEW.md`.

Required sections (fill in from source readings):

**What Is GiljoAI MCP**
- GiljoAI MCP is a passive context server for AI coding tools.
- It stores product knowledge, generates focused prompts, and coordinates agents via the MCP protocol.
- The AI tool (Claude Code, Codex CLI, Gemini CLI) does all reasoning and coding using the user's own subscription. GiljoAI provides the orchestration layer.

**Who It Is For**
- Developers who use AI coding CLIs and want to manage multi-agent workflows across projects.
- Solo developers building production software with Claude Code, Codex CLI, or Gemini CLI.
- Teams that want persistent product context, 360 Memory, and agent coordination without managing infrastructure per project.

**Core Value Proposition**
- Write this from the LEARNING_SECTIONS content in SetupWizardOverlay.vue. The six sections are the authoritative product story. Use them as the basis.

**How It Works**
- Summarize the MCP connection model from the "How GiljoAI Works" learning section.
- Include the client CLI arrow diagram in plain text: `CLI tool --> MCP server (GiljoAI) --> FastAPI --> PostgreSQL`

**Supported AI Tools**
- Claude Code (Anthropic)
- Codex CLI (OpenAI)
- Gemini CLI (Google)
- Any MCP-compatible tool

**The Six Pillars** (derived from LEARNING_SECTIONS, one paragraph per section)
- Use the section titles and content arrays verbatim as the basis. Rewrite into prose paragraphs. Do not copy word-for-word; adapt for a docs style.

**How to Get Started**
- Two-sentence pointer: install via `python install.py`, then follow the setup wizard. Link to INSTALLATION_GUIDE.md.

Document length target: 300-500 lines.

### Phase 3: Write USER_GUIDE.md

Write to `/media/patrik/Work/GiljoAI_MCP/docs/USER_GUIDE.md`.

Work through each section systematically. For each page or UI element, read the actual component to get the correct field names, button labels, and behavior.

**Section: Home Page**

Read WelcomeView.vue for:
- Quick launch card logic (what cards appear and when)
- Greeting message
- What triggers the setup wizard overlay vs the learning modal

**Section: Dashboard**

Read DashboardView.vue for:
- Stat counters shown
- Recent projects list
- Recent memories section
- What the dashboard shows when empty

**Section: Products**

Read ProductsView.vue and ProductForm.vue for:
- How to create a product
- Context fields available (description, tech stack, architecture, testing strategy, constraints, etc.)
- Vision documents (what they are, how to use them)
- Tuning (what the tuning menu does)

**Section: Projects**

Read ProjectsView.vue for:
- How to create a project
- Staging vs activation
- What happens when a project is activated (bootstrap prompt)
- The three phases: staging, implementation, closeout

**Section: Jobs**

Read JobsTab.vue for:
- What a job represents (one agent assignment)
- Status badges (valid statuses: waiting, working, blocked, idle, sleeping, complete, silent, decommissioned)
- Phase tracking
- Auto check-in behavior
- How to send a message to an agent

**Section: Tasks**

Read TasksView.vue for:
- Task categories
- Priority levels
- Filtering options
- How tasks are created (manual and via /gil_add skill)

**Section: User Settings**

Read UserSettings.vue for the exact tab names and what each tab contains.

**Section: Admin Settings**

Read SystemSettings.vue for the exact tab names. Note: this is admin-only (network, database, certificates, users).

**Section: WebSocket Connection Icon**

Read ConnectionStatus.vue for:
- What the icon looks like in each state (connected vs disconnected)
- What happens when you click it
- When the connection drops and auto-reconnects

**Section: Notification Bell**

Find the notification bell component (likely in the navigation folder). Read it for:
- What types of notifications appear
- How to clear them
- Lifecycle of a notification

Document length target: 500-800 lines.

### Phase 4: Verify

Check both documents for:

```bash
grep -n " -- " /media/patrik/Work/GiljoAI_MCP/docs/PRODUCT_OVERVIEW.md
grep -n " -- " /media/patrik/Work/GiljoAI_MCP/docs/USER_GUIDE.md
```

Both commands must return no output (no em dashes).

Check for stale references:

```bash
grep -in "handover\|0910\|0855\|0846\|deprecated\|legacy" \
  /media/patrik/Work/GiljoAI_MCP/docs/PRODUCT_OVERVIEW.md \
  /media/patrik/Work/GiljoAI_MCP/docs/USER_GUIDE.md
```

No handover numbers or internal references should appear in user-facing docs.

Check line counts:

```bash
wc -l /media/patrik/Work/GiljoAI_MCP/docs/PRODUCT_OVERVIEW.md \
       /media/patrik/Work/GiljoAI_MCP/docs/USER_GUIDE.md
```

Neither may exceed 1000 lines.

### Phase 5: Commit

```bash
cd /media/patrik/Work/GiljoAI_MCP
git add docs/PRODUCT_OVERVIEW.md docs/USER_GUIDE.md
git commit -m "docs(0910b): write PRODUCT_OVERVIEW and USER_GUIDE from source inspection"
```

---

## Testing Requirements

**Spot checks:**

1. LEARNING_SECTIONS in SetupWizardOverlay.vue has exactly 6 sections. PRODUCT_OVERVIEW.md must reference all 6 pillars (how it works, product definition, projects, skills, memory, dashboard/monitoring).
2. USER_GUIDE.md must list all 8 valid agent statuses in the Jobs section (waiting, working, blocked, idle, sleeping, complete, silent, decommissioned).
3. Every tab name in User Settings and Admin Settings must match what the Vue component actually renders.
4. Quick launch cards section must describe what the WelcomeView actually shows.
5. No em dashes in either document.

---

## Success Criteria

- [ ] /docs/PRODUCT_OVERVIEW.md written and accurate (reads from source, not stale docs)
- [ ] /docs/USER_GUIDE.md written with all sections filled (Home, Dashboard, Products, Projects, Jobs, Tasks, User Settings, Admin Settings, WebSocket icon, Notification bell)
- [ ] Zero em dashes in either document
- [ ] Zero handover number references in either document
- [ ] Neither document exceeds 1000 lines
- [ ] Commit created with the specified message

---

## Rollback Plan

The scaffold files from 0910a remain in place. To roll back: revert to the scaffold (empty section headers) by checking out the 0910a commit.

---

## Chain Log

Update `/media/patrik/Work/GiljoAI_MCP/prompts/0910_chain/chain_log.json` when done:

```json
{
  "0910b": {
    "status": "complete",
    "commit": "<commit hash>",
    "notes": "Wrote PRODUCT_OVERVIEW (~N lines) and USER_GUIDE (~N lines) from source."
  }
}
```
