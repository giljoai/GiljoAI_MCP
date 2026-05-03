# Toast Verbiage Rollback Reference — UI-0002

**Date:** 2026-05-03
**Project:** UI-0002 "Websockets to more clearly explain what is going to happen"
**Scope:** Frontend toast/snackbar messages and one button label that fire when a user copies a prompt to clipboard.

This file is the single rollback reference for the rename pass. Old text → new text, per call site. To revert, find the file:line and restore the "Old" string verbatim.

---

## Phase 1 — Product Creation & Vision Analysis

| File:Line | Trigger | Old | New |
|---|---|---|---|
| `frontend/src/composables/useVisionAnalysis.js:42` | Stage Analysis (success toast) | `Analysis prompt copied — paste into your AI coding agent` | `Discovery prompt copied. Paste into your AI agent to analyze your vision doc.` |
| `frontend/src/composables/useVisionAnalysis.js:46` | Stage Analysis (clipboard fallback) | `Clipboard unavailable — copy the prompt manually below` | `Clipboard blocked. Select the prompt below and press Ctrl+C.` |
| `frontend/src/components/products/ProductForm.vue:182` | Stage Analysis button label (post-click) | `Prompt Copied!` | `Copied ✓` |

## Phase 2 — Product Tuning

| File:Line | Trigger | Old | New |
|---|---|---|---|
| `frontend/src/components/products/ProductTuningMenu.vue:317` | Copy tuning prompt (success) | `Tuning prompt copied to clipboard` | `Tuning prompt copied. Paste so your agent can refine the selected sections.` |
| `frontend/src/components/products/ProductTuningMenu.vue:319` | Copy tuning prompt (fallback) | `Failed to copy to clipboard — select the text and press Ctrl+C` | `Clipboard blocked. Select the prompt and press Ctrl+C to copy manually.` |

## Phase 3 — Project Staging (Orchestrator Onboarding)

| File:Line | Trigger | Old | New |
|---|---|---|---|
| `frontend/src/components/projects/ProjectTabs.vue:825` | Stage Project (multi_terminal) | `Orchestrator prompt copied - paste into ANY terminal (fresh or existing)` | `Orchestrator brief copied. Paste into any terminal to stage the project.` |
| `frontend/src/components/projects/ProjectTabs.vue:826` | Stage Project (claude_code_cli) | `Orchestrator prompt copied - paste into Claude Code CLI` | `Orchestrator brief copied. Paste into Claude Code CLI to stage the project.` |
| `frontend/src/components/projects/ProjectTabs.vue:827` | Stage Project (codex_cli) | `Orchestrator prompt copied - paste into Codex CLI` | `Orchestrator brief copied. Paste into Codex CLI to stage the project.` |
| `frontend/src/components/projects/ProjectTabs.vue:828` | Stage Project (gemini_cli) | `Orchestrator prompt copied - paste into Gemini CLI` | `Orchestrator brief copied. Paste into Gemini CLI to stage the project.` |
| `frontend/src/components/projects/ProjectTabs.vue:832` | Stage Project (clipboard fallback) | `Copy failed — select the prompt text and press Ctrl+C` | `Copy failed. Check your browser's clipboard permissions and try again.` |

> Note (832): No fallback textarea is rendered for Stage Project, so the old "select the text" message was misleading. Reworded to permission-language.

## Phase 4a — Implementation Launch (Orchestrator)

| File:Line | Trigger | Old | New |
|---|---|---|---|
| `frontend/src/composables/usePlayButton.js:67` | Play orchestrator (subagent CLI modes) | `Implementation prompt copied! ${n+1} jobs ready (1 orchestrator, ${n} agents)` | `Implementation prompt copied. ${n+1} jobs ready to launch (1 orchestrator, ${n} specialists).` |
| `frontend/src/composables/usePlayButton.js:91` | Play orchestrator (multi_terminal) | `Orchestrator prompt copied! ${n} agents ready for launch.` | `Orchestrator prompt copied. ${n} specialists ready to launch.` |

## Phase 4b — Specialist Activation

| File:Line | Trigger | Old | New |
|---|---|---|---|
| `frontend/src/composables/usePlayButton.js:111` | Play specialist | `Launch prompt copied to clipboard` | `${Role} prompt copied. Paste in a fresh terminal to bring this specialist online.` |
| `frontend/src/components/orchestration/AgentTableView.vue:225` | Copy specialist (row icon) | `Prompt copied to clipboard` | `${Role} prompt copied. Paste to hand off this specialist's mission.` |
| `frontend/src/components/orchestration/AgentTableView.vue:231` | Copy specialist (fallback) | `Failed to copy prompt — select the text and press Ctrl+C` | `Copy failed. Check your browser's clipboard permissions and try again.` |

> `${Role}` is `agent.agent_display_name` title-cased per word. Backend guarantees non-null `String(100)` (`AgentJobExecution.agent_display_name`, Pydantic `min_length=1`). Helper `_titleCaseRole()` was added to `usePlayButton.js`. Inline title-case in `AgentTableView.vue:225`.

> Note (231): Row-icon copy has no visible prompt to select — old "select the text" message was misleading. Reworded to permission-language.

## Phase 5 — Session Handover

| File:Line | Trigger | Old | New |
|---|---|---|---|
| `frontend/src/components/projects/HandoverModal.vue:147` | Step 1 — Retire (success) | `Retirement prompt copied to clipboard` | `Retirement prompt copied. Paste so the orchestrator saves state and stands down.` |
| `frontend/src/components/projects/HandoverModal.vue:149` | Step 1 — Retire (fallback) | `Copy failed — select the text and press Ctrl+C` | `Clipboard blocked. Select the prompt and press Ctrl+C to copy manually.` |
| `frontend/src/components/projects/HandoverModal.vue:157` | Step 2 — Continue (success) | `Continuation prompt copied to clipboard` | `Continuation prompt copied. Paste in a fresh terminal to restore full context.` |
| `frontend/src/components/projects/HandoverModal.vue:159` | Step 2 — Continue (fallback) | `Copy failed — select the text and press Ctrl+C` | `Clipboard blocked. Select the prompt and press Ctrl+C to copy manually.` |
| `frontend/src/components/orchestration/AgentTableView.vue:200` | Handover icon result toast | `Session refreshed — continuation prompt copied to clipboard` | `Session refreshed. Paste the continuation prompt to resume the orchestrator.` |

## Phase 6 — Project Termination

| File:Line | Trigger | Old | New |
|---|---|---|---|
| `frontend/src/composables/useJobActions.js:86` | Stop Project | `Termination prompt copied! Paste into orchestrator terminal. (${n} agents)` | `Termination prompt copied. Paste to stop all ${n} agents and save progress.` |

## Phase 7 — Skill & Agent Installation

| File:Line | Trigger | Old | New |
|---|---|---|---|
| `frontend/src/components/AgentExport.vue:171` | Setup (per platform) | `${label} setup prompt copied to clipboard` | `Setup prompt copied. Paste into ${label} to install GiljoAI skills and agents.` |
| `frontend/src/components/AgentExport.vue:214` | Templates download | `Agent export downloaded successfully` | `Agent templates downloaded. Unzip into your project to register the specialist team.` |

## Phase 8 — MCP Server Configuration (AiToolConfigWizard)

| File:Line | Trigger | Old | New |
|---|---|---|---|
| `frontend/src/components/AiToolConfigWizard.vue:302` | Copy config (success) | `Configuration copied to clipboard` | `MCP config copied. Paste in your terminal to wire your AI tool to GiljoAI.` |
| `frontend/src/components/AiToolConfigWizard.vue:304` | Copy config (fallback) | `Copy failed — select the text and press Ctrl+C` | `Clipboard blocked. Select the prompt and press Ctrl+C to copy manually.` |
| `frontend/src/components/AiToolConfigWizard.vue:315` | Copy env var (success) | `Environment variable copied to clipboard` | `Env variable copied. Paste so Node.js trusts the GiljoAI HTTPS cert.` |
| `frontend/src/components/AiToolConfigWizard.vue:317` | Copy env var (fallback) | `Copy failed — select the text and press Ctrl+C` | `Clipboard blocked. Select the prompt and press Ctrl+C to copy manually.` |
| `frontend/src/components/AiToolConfigWizard.vue:327` | Copy cert trust (success) | `Certificate trust command copied to clipboard` | `Trust command copied. Paste to install the GiljoAI cert system-wide.` |
| `frontend/src/components/AiToolConfigWizard.vue:329` | Copy cert trust (fallback) | `Copy failed — select the text and press Ctrl+C` | `Clipboard blocked. Select the prompt and press Ctrl+C to copy manually.` |

---

## Design principles applied

1. **Period > em-dash.** Two short sentences scan faster than one compound clause at 5s default duration.
2. **Lead with the event** ("Prompt copied."), not anticipation ("Ready to ...").
3. **Then describe the outcome** ("Paste into X to do Y") so the user knows what the prompt actually triggers.
4. **Drop adjectives** the user didn't request (gracefully, cleanly, with full context standing by).
5. **Keep actionable destinations** (which CLI, fresh vs. existing terminal); drop everything else.
6. **Fallback messages must match the UI.** "Select the prompt and press Ctrl+C" only when a textarea is on screen; otherwise use permission-check language.
7. **Specialist toasts are role-aware** via title-cased `agent.agent_display_name` (backend-validated non-null).

## Out of scope (intentionally untouched)

- `CloseoutModal.vue:385` `Project closed out successfully` — outcome toast, not a copy event.
- `LaunchTab.vue:347/355` mission update/generated toasts — backend-driven outcomes.
- Error toasts that surface server `error.response?.data?.detail` strings — backend owns those.
- The `"implementor"` vs `"implementer"` spelling mismatch (backend column value vs. UI convention) — flagged as a separate cross-cutting cleanup; not part of this rename.

## Settings dependency

This rename pass also depends on commit `45cd811d8` ("fix(toasts): make notification duration slider actually control timeout") — that fix lets the user tune the 5s default if the new strings feel rushed at their reading pace.
