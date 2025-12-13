# Handover 0332: Agent Staging & Job Execution Prompting Overview

**Date:** 2025-12-07  
**From Agent:** Architecture / Orchestration Planner  
**To Agent:** Backend implementors, frontend/dashboard owners, prompt/template authors  
**Status:** Reference / Planning (no direct code changes)  
**Depends On:** 0260, 0261, 0262, 0297, 0331  

---

## 1. Purpose

Provide a single, high-level reference for how **agent staging**, **job execution**, and **agent prompting** are supposed to work together across:

- Project staging (orchestrator creates mission and agent jobs).
- Jobs/Implementation dashboard (status, acknowledgment, steps, messaging).
- Execution modes (Claude Code CLI vs multi-terminal).
- Thin prompts + MCP tools over HTTP.

This document explains *why* we are making the current set of changes (0260/0261/0262/0297/0331) and how they fit into one coherent workflow, so future changes don’t accidentally break the contract.

---

## 2. Context & Problem Statement

We have several partially overlapping handovers:

- **0260 / 0261** – Claude Code CLI toggle, mode-aware prompts, agent spawning rules.
- **0262** – `get_agent_mission` vs GenericAgentTemplate protocol mismatch.
- **0297** – Message counters + job acknowledgment signaling on the dashboard.
- **0331** – Message Audit Modal for inspecting agent communication.

Individually, they solve specific issues (toggle persistence, naming, signaling), but together they define the **end-to-end agent experience**:

1. Orchestrator stages a project and spawns agent jobs (Type 1 spawning).
2. User sees jobs on the Dashboard (Jobs/Implementation tab) with accurate status and counters.
3. User launches orchestrator and agents (Type 2 spawning) either:
   - As Claude Code subagents in a single terminal (CLI mode), or
   - As independent agents in multiple terminals (multi-terminal mode).
4. Agents fetch missions + context from the MCP server and report their work.

Historically, we had:

- Confusion about **which MCP tools** agents should call and in what order (`acknowledge_job` vs `get_agent_mission`).
- Unclear visual signals on the dashboard (acknowledged vs working vs complete).
- No obvious place for agents to declare their **plan/TODOs** or for humans to review the story of what happened.
- Multiple execution modes without a single reference explaining how they share the same underlying protocol.

This overview reconciles these pieces into one mental model.

---

## 3. Design Pillars

1. **Thin Prompts, Thick MCP**
   - Prompts (for orchestrator and agents) are **lean instructions** that tell the agent *how to talk to the MCP server*, not full missions.
   - Real content (mission, context, plan, history) lives on the **MCP server over HTTP** and is fetched on demand via MCP tools.

2. **Single Source of Truth for Jobs**
   - Every agent instance corresponds to an `MCPAgentJob` row with:
     - `mission`, `status`, `mission_acknowledged_at`, `messages`, and now `steps` metadata.
   - Both execution modes (CLI and multi-terminal) work against the **same job records**; execution mode only affects *how* the agent is launched, not how jobs are represented.

3. **Explicit MCP Protocol for Agents**
   - Agents use a small, well-defined set of MCP tools:
     - `health_check` (optional sanity check).
     - `get_agent_mission` (atomic job start + mission fetch in CLI mode).
     - `send_message` / `receive_messages` / `get_next_instruction` for coordination.
     - `report_progress` (optional TODO-style steps).
     - `complete_job` / `report_error` for completion/failure.
   - `acknowledge_job` is reserved for queue/worker and admin flows, not standard CLI subagents.

4. **Dashboard as Real-Time Flight Deck**
   - Jobs tab shows, per agent:
     - **Job Acknowledged**: mission read at least once.
     - **Agent Status**: waiting, working, blocked, complete, failed, cancelled, decommissioned.
     - **Steps**: numeric progress through agent-declared TODOs (e.g., `3/5`).
     - **Messages Sent / Waiting / Read**: live counters from the message hub.
   - Behind every numeric signal there is a **narrative** visible in the Message Audit Modal.

5. **No New WebSocket Methodology**
   - All real-time updates must reuse the existing WebSocket pipeline and events (`message:*`, `job:mission_acknowledged`, `agent:status_changed`, etc.).
   - It is acceptable to add new handlers/listeners, but not new event types or protocols for these changes.

---

## 4. End-to-End Flow (Staging → Dashboard → Execution)

### 4.1 Project Staging (Launch Tab)

1. User clicks **[Stage Project]** on the Launch tab.
2. Orchestrator:
   - Fetches context via `get_orchestrator_instructions(orchestrator_id, tenant_key)`.
   - Writes `Project.mission` (orchestrator plan).
   - Spawns `MCPAgentJob` records via `spawn_agent_job(...)` using **strict agent_type discipline** (names matching agent templates).
3. Result:
   - Orchestrator + agents appear as cards/jobs in the UI, all in `waiting` (or API alias `pending`) state.

### 4.2 Jobs / Implementation Dashboard

The Jobs tab (Implementation) shows each `MCPAgentJob` with:

- `Job Acknowledged`: derived from `mission_acknowledged_at` (checkmark when non-null).
- `Agent Status`: driven by `agent:status_changed` and job life cycle.
- `Steps`: derived from the latest `report_progress(job_id, {"mode": "todo", ...})` payload (if any).
- Message counters: derived from `messages` JSONB and WebSocket message events.

The dashboard does **not** infer anything from raw text; it uses structured fields and events only.

### 4.3 Execution Modes

When the user clicks **[Launch Jobs]**, the execution path diverges by mode but uses the same underlying jobs.

#### Claude Code CLI Mode (Toggle ON)

- Orchestrator thin prompt (single terminal):
  - Reads its role and IDs from the prompt.
  - Calls `get_orchestrator_instructions(...)` to fetch mission + team.
  - Spawns subagents using Claude’s native Task tool with strict `subagent_type` names matching `agent_type`s.
- Subagents (hidden):
  - Each receives a thin prompt with its IDs.
  - First MCP action after optional `health_check()` is `get_agent_mission(agent_job_id, tenant_key)`:
    - Sets `mission_acknowledged_at` (drives Job Acknowledged).
    - Transitions `waiting → working` (drives Agent Status).
  - They then execute, coordinate (messages), optionally report TODO-style `Steps`, and complete or error.

#### Multi-Terminal Mode (Toggle OFF)

- All agents show `[Copy Prompt]` buttons.
- User opens multiple terminals and pastes per-agent thin prompts.
- Each agent connects to the same jobs and uses the same MCP protocol:
  - `get_agent_mission`, messaging, optional `report_progress`, `complete_job` / `report_error`.

In both modes, the difference is **how** agents are launched, not how they talk to MCP.

---

## 5. How Current Handovers Fit Together

### 5.1 0262 – Agent Mission Protocol Merge

- Defines `get_agent_mission(agent_job_id, tenant_key)` as the **atomic job start** for CLI subagents:
  - On first call: set `mission_acknowledged_at`, transition `waiting → working`, emit `job:mission_acknowledged` + `agent:status_changed`.
  - Later calls: idempotent re-reads only.
- Narrows `acknowledge_job` usage to queue and admin flows.
- Acts as the canonical spec for agent startup behavior.

### 5.2 0297 – UI Message Status & Job Signaling

- Implements:
  - Per-agent message counters via WebSocket-driven events.
  - Job Acknowledged column based on `mission_acknowledged_at` and `job:mission_acknowledged`.
- Extended design:
  - Adds a **Steps** column (between Agent Status and Messages Sent).
  - Reuses `report_progress(job_id, {"mode": "todo", "total_steps", "completed_steps", ...})` to drive a numeric `completed/total` indicator.
  - Keeps rich plan/progress narrative in `send_message` and completion result.

### 5.3 0331 – Message Audit Modal

- Provides a two-layer modal (list + detail) for reviewing messages per agent:
  - Tabs: `Sent`, `Waiting`, `Read`, `Plan / TODOs`.
  - Detail view shows full content, metadata, and broadcast recipient status.
- Integrates with Steps:
  - Clicking the folder icon opens the modal (default tab = usual behavior).
  - Clicking a **Steps** cell opens the same modal with the **Plan / TODOs** tab pre-selected and the `completed/total` summary visible.
  - Plan/TODO content comes from `message_type="plan"` messages; narrative progress from `message_type="progress" | "note"`.

### 5.4 0260 / 0261 – Claude Code CLI Mode & Implementation Prompt

- Persist the execution mode (`execution_mode`) per project/job.
- Generate mode-specific orchestrator prompts:
  - CLI mode: orchestrator spawns subagents via Task tool, agents are hidden.
  - Multi-terminal: user launches each agent manually.
- Update GenericAgentTemplate and agent templates to reflect:
  - Phase 1: `health_check()` → `get_agent_mission(...)` (no redundant `acknowledge_job` for CLI subagents).
  - Use of `report_progress` for numeric Steps and `send_message` for plans/progress.

---

## 6. Recommended Implementation Order (Recap)

1. **Implement 0262 protocol** (backend):
   - `get_agent_mission` atomic start semantics.
   - Ensure 0297 mission_acknowledged tests align.
2. **Extend 0297** (backend + frontend):
   - TODO-style `report_progress` handling and `steps` metadata.
   - Column reorder + Steps column in JobsTab/AgentTableView, wired via existing WebSocket events.
3. **Implement 0331 modal** (frontend):
   - MessageAuditModal + MessageDetailView.
   - Wire folder icon and Steps cell into the modal.
4. **Finalize 0260/0261 prompts & toggle**:
   - Mode-aware prompts that assume the finalized MCP protocol and dashboard signals.

This order ensures protocol stability first, then dashboard signals, then UX inspection tools, and finally prompt text that accurately describes the system behavior.

---

## 7. Non-Goals

- Introducing new WebSocket event types or a parallel WebSocket system.
- Changing the underlying message schema or adding new tables for Steps.
- Redesigning the entire dashboard; changes are limited to:
  - Column order,
  - Steps indicator,
  - Message audit access.
- Replacing existing closeout / 360 memory mechanisms; they may *read* from the richer completion data but are not being redesigned here.

---

## 8. How to Use This Document

- When creating or updating handovers that touch:
  - MCP tools (`get_agent_mission`, `report_progress`, messaging).
  - Jobs/Implementation UI.
  - Orchestrator/agent templates.
- Use this document to check:
  - Does the change respect the thin-prompt + MCP pattern?
  - Does it preserve the signaling contract (status, acknowledged, steps, message counters)?
  - Does it reuse existing WebSocket + JSONB infrastructure?

If the answer is “no” to any of these, the change likely needs to be redesigned or a separate architectural handover should be created before coding.

