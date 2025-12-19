# Handover 0349: Agent Execution Context & Instruction Refactor

**Date**: 2025-12-19  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: High  
**Type**: Architectural Refactor + Execution-Phase Behavior Cleanup  
**Estimated Time**: 4–6 hours  
**Builds Upon**: 0246b (Generic Agent Template), 0254 (Three-Layer Instruction Architecture Cleanup), 0260 (Claude Code CLI Mode), 0332/0333/0334 (Staging + HTTP-only MCP), 0335/0337/0351/0361 (Agent workflow and template fixes)

---

## Executive Summary

**Problem**

Individual agents (implementer/tester/reviewer/analyzer/documenter) receive overlapping and sometimes duplicated instructions from multiple places:
- Claude Code CLI agent templates in `.claude/agents/*.md`
- Multi-terminal `GenericAgentTemplate` text
- Thin prompts from `spawn_agent_job()` (execution phase)
- Mission + `full_protocol` returned from `get_agent_mission()`

This creates a support burden and increases the risk of drift between:
- Tool usage instructions (how to call MCP tools)
- Behavioral protocol (how to behave across lifecycle phases)
- Job-specific mission/context (what to actually do)

**Goal**

Create a clean three-layer execution architecture for **individual agents only** (orchestrator staging behavior remains as-is):
1. **Template Layer (Tool Wiring + Identity)** – Teach tools and IDs; bootstrap to server.
2. **Protocol Layer (Behavior/Lifecycle)** – Single shared protocol returned from the server.
3. **Mission Layer (Job Content + Context)** – Per-job mission and context, stored in DB.

**Outcome**

- Single, server-owned behavior specification for all agents via `_generate_agent_protocol()` and `get_agent_mission()`.
- Templates (Claude CLI + multi-terminal) focus on role, MCP tool wiring, and identity only.
- Execution-phase thin prompts stop duplicating lifecycle instructions and instead point to the protocol.
- Exported templates for Claude Code remain user-tunable for style, but cannot override protocol behavior.

---

## Scope

### In Scope

- **Execution phase of individual agents only** (implementer/tester/reviewer/analyzer/documenter):
  - Multi-terminal mode (generic agent template).
  - Claude Code CLI Task-tool subagents (via orchestrator instructions).
- Refactoring **where execution instructions live**, not changing the overall orchestration pipeline.
- Aligning:
  - `get_agent_mission()` + `_generate_agent_protocol()` (behavioral authority).
  - `spawn_agent_job()` thin prompt (execution-phase bootstrap).
  - `GenericAgentTemplate` (multi-terminal).
  - Seeded agent templates and export behavior (`template_seeder.py` → DB templates → Claude `.claude/agents/*.md`).

### Out of Scope

- Changes to **staging** behavior or the orchestrator’s mission-generation logic.
- Changes to `get_orchestrator_instructions()` beyond minor wording if needed.
- UI changes or workflow dashboard changes (covered by 0361 and related handovers).

---

## Current Architecture (Execution Phase)

**Key Execution-Phase Components**

- `src/giljo_mcp/services/orchestration_service.py`
  - `spawn_agent_job()` – Creates `MCPAgentJob` and returns a ~10-line thin prompt that:
    - Provides identity (agent_name/type, project name).
    - Includes a full 6-step “MANDATORY STARTUP SEQUENCE” (get_agent_mission, acknowledge_job, receive_messages, report_progress, complete_job).
    - Reinforces “MCP tools are native; do not use HTTP”.
  - `get_agent_mission()` – Returns:
    - `mission` (job-specific instructions).
    - `full_protocol = _generate_agent_protocol(...)` (multi-phase behavior spec).
    - Status transitions and WebSocket emissions.

- `src/giljo_mcp/templates/generic_agent_template.py`
  - `GenericAgentTemplate.render()` – Large prompt containing:
    - 6-phase lifecycle (initialization, mission fetch, work, progress, communication, completion).
    - MCP tool usage details.
    - GiljoAI code/testing/tenancy standards and success criteria.

- `F:\TinyContacts\.claude\agents\*.md` (exported agent templates)
  - Each role file (implementer/tester/analyzer/reviewer/documenter) contains:
    - “MCP tools are native” and “no HTTP” guidance.
    - Startup, progress, completion instructions.
    - Check-in protocol and context-request behavior.

- `src/giljo_mcp/thin_prompt_generator.py`
  - `_build_claude_code_execution_prompt()` – Orchestrator’s Claude Code execution prompt:
    - Teaches orchestrator how to call `Task(subagent_type=..., instructions=...)`.
    - Embeds subagent instructions: identity + “First action: call get_agent_mission(...)” + some behavioral hints.

**Issue:** These layers encode similar lifecycle and behavior rules in multiple places, causing drift and making support/debugging harder.

---

## Target Architecture (Three Layers)

### 1. Template Layer – Tool Wiring + Identity

**Responsibility**
- Explain MCP connection and tools.
- Provide agent identity (IDs + tenant key).
- Bootstrap the agent into the server-owned protocol/mission.

**Key Rules**
- All templates (Claude CLI `.md`, `GenericAgentTemplate.render`, `spawn_agent_job()` thin prompts, orchestrator Task instructions) should:
  - Show identity (job_id, agent_name/agent_id, project_id, product_id, tenant_key).
  - Instruct: “First action: call `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)`”.
  - Instruct: “Then follow the `full_protocol` returned by that tool for all lifecycle, messaging, and error handling.”
- Templates may contain **role flavor** (implementer vs tester style), but must **not re-specify** the full lifecycle protocol.

### 2. Protocol Layer – Behavior / Lifecycle

**Responsibility**
- Define how every agent behaves across:
  - Initialization and mission fetch.
  - Planning and TodoWrite behavior.
  - Progress checkpoints and reporting.
  - Messaging, context requests, and error handling.
  - Completion and closeout.

**Single Source of Truth**
- `_generate_agent_protocol(agent_job_id, tenant_key, agent_type)` in `orchestration_service.py`.
- Returned as `full_protocol` from `get_agent_mission()` for every agent job.

**Key Changes**
- Ensure `_generate_agent_protocol()` incorporates:
  - The check-in protocol, broader context request rules, and message-handling guidance currently embedded in `.claude/agents/*.md` and `GenericAgentTemplate`.
  - TodoWrite/planning requirements and progress-reporting expectations previously scattered across prompts.
- Make all templates explicitly **defer** to `full_protocol` instead of rephrasing lifecycle steps.

### 3. Mission Layer – Job Content + Context

**Responsibility**
- Provide the per-job work definition and context.

**Single Source of Truth**
- `get_agent_mission(agent_job_id, tenant_key)`:
  - `mission` text (what to do).
  - Any structured mission/context fields.
  - `full_protocol` (how to behave).

**Key Rules**
- Orchestrator’s Claude Code and multi-terminal execution prompts should only:
  - Include short mission summaries (if needed).
  - Rely on the mission stored in DB and fetched via `get_agent_mission()` for full details.

---

## Implementation Plan

### Step 1 – Audit and Centralize Protocol Content

1. Review:
   - `_generate_agent_protocol()` and current `full_protocol` output.
   - Lifecycle sections in `GenericAgentTemplate.render()`.
   - Workflow/Check-in/Context-request instructions in `.claude/agents/*.md`.
2. Consolidate all **behavioral rules** (phases, check-ins, error handling, context requests, message handling, TodoWrite) into `_generate_agent_protocol()`.
3. Ensure `get_agent_mission()` always returns `full_protocol` as the canonical behavior spec for agents.

### Step 2 – Simplify Agent Templates (Generic + Claude CLI)

1. **GenericAgentTemplate (`generic_agent_template.py`)**
   - Trim content to:
     - Identity (agent_id, job_id, product_id, project_id, tenant_key).
     - Short “Tool wiring” section (key MCP tools with names, no deep protocol).
     - Bootstrap: “Call `get_agent_mission(job_id, tenant_key)` and follow `full_protocol`.”
   - Remove duplicated multi-phase lifecycle and standards; those move to `full_protocol`.

2. **Claude CLI `.claude/agents/*.md` templates**
   - On the server side (via `template_seeder.py` and DB defaults), make sure base templates:
     - Emphasize tool usage and environment (MCP tools are native, no HTTP).
     - Emphasize role behavior (implementer vs tester, etc.) at a style level.
     - Explicitly tell agents to:
       - Call `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)` first.
       - Follow the `full_protocol` from that response for lifecycle.
   - Remove or drastically shorten lifecycle prose that duplicates `full_protocol`.
   - Preserve user-tunable role flavor, but not protocol semantics.

### Step 3 – Align `spawn_agent_job()` Thin Prompt

1. Update `spawn_agent_job()` (execution phase thin prompt) to:
   - Keep identity and MCP/native-tool reminder.
   - Replace the long 6-step “MANDATORY STARTUP SEQUENCE” with:
     - “First action: call `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)`.”
     - “Follow `full_protocol` in that response.”
   - Ensure tenant_key and job_id are clearly visible in the thin prompt for manual use if needed.

### Step 4 – Align Claude Code Orchestrator Task Instructions

1. In `_build_claude_code_execution_prompt()`:
   - Keep:
     - Agent list, job IDs, and `subagent_type` guidance (`agent_name` vs `agent_type`).
     - How to structure `Task(subagent_type=..., instructions=...)`.
   - For `Task.instructions` examples:
     - Keep identity and first call to `get_agent_mission(job_id, tenant_key)`.
     - Remove any detailed execution protocol; instruct subagents to follow `full_protocol` returned from the server.

### Step 5 – Seeder and Export Behavior

1. Update `template_seeder.py`:
   - Ensure seeded templates for implementer/tester/analyzer/reviewer/documenter follow the **Template Layer** rules above.
   - Confirm orchestrator template remains system-managed and cannot be edited via the regular Template Manager.
2. Verify the export function that generates Claude `.claude/agents/*.md`:
   - Exports only **template-layer content** (role flavor + tool wiring + bootstrap).
   - Does not expose or allow modification of `full_protocol` behavior.

### Step 6 – Documentation and Catalogue Update

1. Cross-link this handover with:
   - 0254_three_layer_instruction_cleanup.md (prior architecture cleanup).
   - 0260 (Claude Code CLI Mode) and 0332/0333/0334 (staging + HTTP-only MCP).
2. Add entry for 0349 to `HANDOVER_CATALOGUE.md` under “Active Handovers” once implementation begins.

---

## Testing Plan

- **Unit Tests**
  - `tests/services/test_orchestration_service_get_agent_mission.py`:
    - Validate `full_protocol` includes required lifecycle phases and key rules (check-in, context requests, error handling).
  - `tests/services/test_orchestration_service_spawn_agent_job.py`:
    - Assert thin prompt:
      - Contains identity and MCP/native tool reminder.
      - Mentions `get_agent_mission` and `full_protocol`.
      - No longer embeds full multi-step lifecycle.
  - `tests/templates/test_generic_agent_template.py`:
    - Validate `GenericAgentTemplate.render()` includes bootstrap + tool wiring but not full protocol.
  - Seeder tests:
    - Validate seeded templates contain required bootstrap lines and no embedded full protocol.

- **Manual / Integration Checks**
  - Multi-terminal session: start an agent, ensure it:
    - Calls `get_agent_mission` as first tool.
    - Follows `full_protocol` behavior (progress, messaging, completion).
  - Claude Code CLI Task mode:
    - Use exported templates, spawn subagents via Task, and confirm identical behavior to multi-terminal mode.

---

## Risks and Open Questions

- **Risk**: Existing agent templates customized by users may still contain outdated protocol text.
  - Mitigation: Provide clear release notes and a one-time migration hint in Template Manager, encouraging users to trim behavior sections and rely on `full_protocol`.

- **Risk**: Tests and docs referencing old prompt snippets may fail.
  - Mitigation: Systematically search tests and docs for old startup sequences and update them as part of this handover.

- **Open Question**: Do we need a small “protocol version” field in `full_protocol` for easier debugging across sessions?
  - Suggestion: Optional follow-up; not required to complete this handover.

---

## Progress Updates

> To be filled in by implementing agents.

- **[YYYY-MM-DD] – [Agent]**  
  Status: Not Started / In Progress / Blocked / Completed  
  Notes:
  - …

