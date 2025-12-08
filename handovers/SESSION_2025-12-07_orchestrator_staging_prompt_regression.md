# Session Memory – Orchestrator Staging Prompt Regression (2025-12-07)

## Context

- Repo: `GiljoAI_MCP`
- Area: Orchestrator thin prompts, staging workflow, Claude Code CLI mode.
- Related handovers: `0260`, `0261`, `0262`, `0297`, `0331`, `0332`.
- User expectation: Staging prompt is **orchestrator-only**, **mode-agnostic**, and purely **MCP-over-HTTP**. Execution mode differences (CLI vs multi-terminal) belong in **Phase 2 implementation prompts**, not staging.

## What Was Working Before

- `ThinClientPromptGenerator.generate_staging_prompt` produced a 7-task **STAGING WORKFLOW** prompt:
  - Identity & context verification.
  - MCP health check.
  - Environment understanding.
  - Agent discovery & version check.
  - Context prioritization & mission.
  - Agent job spawning.
  - Project activation.
- This prompt worked well in practice: orchestrator followed the 7 tasks and stayed focused on MCP tools and the current project.
- 0262/0297 semantics (get_agent_mission = atomic start, mission_acknowledged_at driving “Job Acknowledged”, message counters, etc.) were conceptually aligned with dashboard behavior.

## What Changed / Broke

- As part of 0260/0261 work, `generate_staging_prompt` was extended with a **Claude Code CLI–specific block** after Task 6:
  - “CLAUDE CODE CLI MODE – STRICT TASK TOOL REQUIREMENTS”.
  - Detailed Task tool spawning instructions, `agent_type` vs `agent_name`, and full subagent protocol (health_check, get_agent_mission, report_progress, send_message, get_next_instruction, complete_job/report_error).
  - A hard requirement to “only spawn agents from the list returned by get_available_agents()” even though `get_available_agents` is **not** exposed in the HTTP MCP tool router.
- The staging prompt still contained older instructions that:
  - Told the orchestrator to call `get_available_agents(include_versions=true)`.
  - Told it to run `ls ~/.claude/agents/*.md` (or Windows equivalent).
  - Claimed it would “confirm” identity fields and WebSocket status even though there are no MCP tools to explicitly verify `product_id` or WebSocket health.
- Result in real runs:
  - Orchestrator started using generic filesystem and bash/Serena commands (e.g., exploring `F:\TinyContacts`) instead of staying within HTTP MCP tools.
  - It referenced MCP tools that do not exist (`get_available_agents`), causing the LLM to improvise behavior.
  - The staging prompt conflated **staging** and **execution-phase CLI subagent protocol**, violating the two-phase design from 0261/0332.

## Current Code State (After This Session)

- `src/giljo_mcp/thin_prompt_generator.py` has been **restored to the latest committed version on `master`** using `git restore`:
  - We are *not* carrying forward any experimental revert of `generate_staging_prompt`.
  - The file now matches the repo’s latest commit (including the CLI-specific block and the existing 7-task staging body).
- 0262 backend semantics (`get_agent_mission` atomic start, mission_acknowledged_at, WebSocket events) and 0297/0331 dashboard/message work remain in place; we did not revert those.
- There is an untracked handover note file in `handovers/` (`"This is now it all broke.md"`) created by the user for additional context.

## Key Design Decisions Reaffirmed

1. **Two-Phase Prompt Architecture (0261/0332)**
   - Phase 1 – **Staging Prompt** (Launch tab):
     - Orchestrator-only.
     - Mode-agnostic (CLI vs multi-terminal is just a label, not different logic).
     - Responsibilities: read context via `get_orchestrator_instructions`, create mission, choose agent types, spawn jobs.
   - Phase 2 – **Implementation Prompts** (Jobs tab):
     - Mode-dependent.
     - Multi-terminal: per-agent prompts.
     - CLI: orchestrator implementation prompt + CLI subagent templates using `get_agent_mission` as atomic start.

2. **Agent Mission Protocol (0262)**
   - `get_agent_mission(agent_job_id, tenant_key)`:
     - First call (for waiting job): set `mission_acknowledged_at`, transition `waiting → working`, emit `job:mission_acknowledged` + `agent:status_changed`.
     - Subsequent calls: idempotent re-reads, no status/timestamp changes.
   - `acknowledge_job`:
     - Reserved for queue/worker and admin flows; **not** part of CLI subagent Phase 1.

3. **Dashboard Signals (0297/0331) in CLI Mode**
   - “Job Acknowledged” column: driven solely by `mission_acknowledged_at` set by `get_agent_mission`.
   - Status chip: `waiting` → `working` when mission is first fetched; `complete`/`failed`/`blocked`/`cancelled` via `complete_job` / `report_error` / cancel.
   - Message counters: driven by `message:*` events; Message Audit Modal is the narrative window.

4. **Strict Agent Type Naming (0260)**
   - `agent_type` MUST match the server’s agent template name exactly (e.g., `"implementer"`, `"backend-tester"`).
   - `agent_name` is a human-friendly label only.
   - Validation should be enforced in `spawn_agent_job` using server-side template list, not by shelling into `~/.claude/agents`.

5. **HTTP-Only MCP Contract**
   - Orchestrator and agents should operate purely via HTTP MCP tools (`/mcp` JSON-RPC) and not explore the filesystem with `bash`, `ls`, or Serena’s file tools unless explicitly asked by the user for diagnostics.

## Outstanding Problems to Fix (Future Work)

1. **Staging Prompt vs Tools Available**
   - Task 1 currently claims to “confirm” identifiers and WebSocket status without dedicated MCP tools; wording should reflect what can actually be verified via `get_orchestrator_instructions` and `health_check`.
   - Tasks 2–4 reference `get_available_agents` and `ls ~/.claude/agents/*.md`, which do not match the HTTP MCP surface and push the LLM toward shell behavior.

2. **Staging Prompt Scope Creep**
   - The CLI-specific block in `generate_staging_prompt` currently mixes execution-phase subagent protocol into Phase 1; this conflicts with the two-phase design from 0261/0332.

3. **Agent Type Strictness Expression**
   - The prompt text talks about strictness and versioned filenames but does not clearly express hard stop conditions or user-facing guidance when template and installed agents don’t match.

## Agreed Direction Going Forward

- Do **not** revert further code; work forward from the current `master` state.
- Treat the existing 7-task staging prompt as the structural baseline, but:
  - Make it **mode-agnostic** in behavior (CLI vs multi-terminal differences belong in implementation prompts/templates).
  - Align each task with what is actually exposed as HTTP MCP tools.
  - Rephrase “verification” steps to describe what the orchestrator can truly check (and what it cannot).
- Keep 0262/0297/0331 behavior as the protocol and UI source of truth, and update prompts/docs/templates to describe that behavior rather than invent new semantics.

This session memory should be used as the reference when revisiting `generate_staging_prompt`, the CLI implementation prompt, and related handovers, so we don’t repeat the same regression. The user expects future work to start from this description and the current repo state, not from older, partially reverted snapshots.**

