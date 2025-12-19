# Session Memory: 0363 – Agent Instruction Slimming & Team-Aware Missions

> **NOTE:** This was originally numbered 0353 but renumbered to 0363 to avoid conflict with `0353_agent_team_awareness_and_mission_context.md`. This is a session memory/support document for the 0353 implementation work.

**Date:** 2025-12-19  
**Session Type:** Backend/Prompt Architecture (Execution Layer + WebSockets)  
**Related Handovers:** 0349_agent_execution_context_refactor, 0353_agent_team_awareness_and_mission_context

---

## 1. Context & Goals

- 0349 was implemented to cleanly separate agent instructions into three layers:
  - **Template layer** – wiring + identity (how to talk to MCP, who you are).
  - **Protocol layer** – `_generate_agent_protocol()` + `get_agent_mission()` → `full_protocol` (behavior).
  - **Mission layer** – `mission` text per job (what to do, project-specific context).
- Templates and thin prompts were simplified to **delegate behavior to `full_protocol`** and reduce duplication.
- 0353 is the follow-on project to:
  - **Slim seeded/exported templates**: role + wiring only, no full lifecycle.
  - **Add team awareness** into missions: each agent knows its role, teammates, dependencies, and coordination rules.

---

## 2. Changes Already Implemented (Important Context)

### 2.1 Generic Agent Template

- File: `src/giljo_mcp/templates/generic_agent_template.py`
- Behavior:
  - Injects identity: `agent_id`, `job_id`, `product_id`, `project_id`, `tenant_key`.
  - Provides MCP wiring section (“MCP tools are native”, key tools by full name).
  - Delegates lifecycle:
    - First action: call `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)`.
    - Then follow `full_protocol` from `get_agent_mission()` for all behavior (startup, planning/TodoWrite, progress, messaging, completion, error handling).
- Tests: `tests/unit/test_generic_agent_template.py` updated accordingly; they pass when run alone (global coverage gate only fails when running partial tests).

### 2.2 Thin Spawn Prompts

- Files:
  - `src/giljo_mcp/services/orchestration_service.py` → `spawn_agent_job` thin prompt.
  - `src/giljo_mcp/tools/orchestration.py` → `_spawn_agent_job_impl`.
- Both now:
  - Keep a short identity line.
  - Include a concise “MCP tools are native” reminder.
  - Replace long “MANDATORY STARTUP SEQUENCE” with:
    - Step 1: call `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)`.
    - Step 2: follow `full_protocol` for lifecycle behavior.

### 2.3 Claude Code Task Instructions

- File: `src/giljo_mcp/thin_prompt_generator.py`, method `_build_claude_code_execution_prompt()`.
- Changes:
  - `Task(..., instructions="...")` now tells subagents to call `mcp__giljo-mcp__get_agent_mission` as a tool with `agent_job_id` + `tenant_key`.
  - Explicitly says this returns `mission` + `full_protocol` and that `full_protocol` governs lifecycle.

### 2.4 Seeder MCP Coordination Section

- File: `src/giljo_mcp/template_seeder.py`, `_get_mcp_coordination_section()`.
- Behavior:
  - Keeps CRITICAL “MCP tools are native” block.
  - Replaces detailed step-wise protocol with:
    - Tool summary.
    - Bootstrap sequence pointing to `get_agent_mission` + `full_protocol`.
    - Generic tool-call format + self-navigation notes.
  - This flows into DB templates and exported `.claude/agents/*.md`.

### 2.5 WebSocket Fixes (Jobs/Launch Tabs)

- Relevant files:
  - `api/websocket.py` → `WebSocketManager.broadcast_job_created`
  - `src/giljo_mcp/services/orchestration_service.py` → `spawn_agent_job`
  - `api/endpoints/agent_management.py` → `create_agent_job`
- Behavior now:
  - `broadcast_job_created` emits **two events** per tenant:
    - `agent_job:created` (internal job event – tests, dashboards).
    - `agent:created` (UI-facing event for Launch/Jobs tabs) with:
      - `tenant_key`, `project_id`, `agent_id`, `agent_job_id`, `agent_type`, `agent_name`, `status`.
  - `spawn_agent_job` and the manual job endpoint both pass `project_id`, `agent_name`, `status` into `broadcast_job_created` so UIs receive `agent:created` in real time.

### 2.6 Template Download WebSocket Fix

- File: `src/giljo_mcp/tools/tool_accessor.py`, `get_agent_download_url`.
- Fix:
  - Switched from non-existent `broadcast_template_export` to `broadcast_templates_exported(tenant_key, template_ids, export_type="manual_zip")`.
  - This restores real-time template export notifications for the Template Manager.

---

## 3. Observations About Current Templates (.claude/agents)

From reviewing `F:\TinyContacts\.claude\agents\implementer.md` (and similar for other roles):

- **Too long (~600 lines)**:
  - Contains full Phase 1–3 lifecycle protocol, check-in protocol, and inter-agent messaging pseudo-code.
  - Duplicates behavior already encoded in `full_protocol`.

- **Conflicting instructions** vs `full_protocol`:
  - Template describes one startup/progress flow; `full_protocol` describes another (adds TodoWrite, clarifies message handling, etc.).
  - Confusion around:
    - `receive_messages` vs `list_messages`.
    - `agent_id` vs `job_id` vs `agent_job_id`.

- **Placeholder-heavy & pseudo-code**:
  - Uses `<AGENT_TYPE>`, `<TENANT_KEY>`, `<PROJECT_ID>`, Python loops, etc.
  - Risk: model may take placeholders literally instead of using real values from `get_agent_mission`.

Conclusion: Templates must be **slimmed** to role + wiring only, with all lifecycle behavior and IDs sourced from `get_agent_mission` + `full_protocol`.

---

## 4. Team-Aware Missions (0353) – Design Decisions

We agreed that:

- Agents should not operate in isolation; they should know:
  - Their own role on the project: “You are ANALYZER/DOCUMENTER/IMPLEMENTER…”
  - Who else is on the team and what they’re doing.
  - Simple dependency relationships (“Documenter depends on analyzer’s folder structure…”).
  - Basic coordination rules (“When X is done, message Y with Z.”).

- Templates are not the right place for teammate listings (they’re generic and reused across projects).
  - Team context belongs in the **mission** that `get_agent_mission` returns, which is project-specific and stored per job.

Therefore 0353 defines a **standard mission header** for each agent job:

- `YOUR IDENTITY` – role + job_id.
- `YOUR TEAM` – small table of agents with roles + deliverables.
- `YOUR DEPENDENCIES` – upstream/downstream relationships.
- `COORDINATION` – when/who to message (using MCP tools already documented).

This header is prepended to the agent-specific mission text during staging/spawn.

---

## 5. Implementation Strategy for 0353 (for Next Agent)

Follow TDD from QUICK_LAUNCH (`RED → GREEN → REFACTOR`, behavior-focused tests).

### 5.1 Suggested First Slice: Team-Aware Missions

**Tests first** (e.g., `tests/services/test_orchestration_service_agent_missions.py`):
- Set up a project with a staged plan that includes at least two roles (e.g., analyzer + documenter).
- When missions are spawned and `get_agent_mission` is called for each job:
  - Assert that `result["mission"]` contains:
    - `## YOUR IDENTITY` with the correct role + job_id.
    - `## YOUR TEAM` with entries for both agents (names/roles/deliverables).
    - `## YOUR DEPENDENCIES` text referencing the other agent appropriately.
    - `## COORDINATION` with at least one explicit messaging hint.
- These tests should focus on **mission content behavior**, not internal implementation.

**Implementation sketch**:
- Extend staging/orchestration logic to build a simple “team plan” per project:
  - A list of agents (name, role, deliverables, dependencies).
- Modify `spawn_agent_job` (or the staging code that calls it) to:
  - Construct a mission string by concatenating:
    - The standardized header (`YOUR IDENTITY / YOUR TEAM / YOUR DEPENDENCIES / COORDINATION`).
    - The role-specific mission body that already exists.
- Ensure no changes to `full_protocol` structure; just the `mission` string.

### 5.2 Second Slice: Template Slimming via Seeder/DB/Export

**Tests first**:
- Add/extend tests around `template_seeder._get_mcp_coordination_section` and/or any export helper to assert:
  - The seeded template text includes:
    - MCP wiring block.
    - Role-specific text.
    - A short startup note that points to `get_agent_mission` + `full_protocol`.
  - The seeded template does **not** include:
    - Detailed lifecycle phases.
    - CHECK-IN PROTOCOL pseudo-code.
    - Heavy Python examples.

**Implementation sketch**:
- Update `template_seeder.py` to rewrite the base template bodies accordingly.
- Verify that the Agent Template Manager reflects the new content.
- Verify that the export to `.claude/agents/*.md` shows the slimmed templates.

---

## 6. Branching & Where to Work

- Current work has been committed on `master`; a fallback branch exists:
  - `0353_agent_instruction_slimming` was created from the current `master` as a safety snapshot.
- Per user guidance:
  - **All new implementation work for 0353 should continue on `master`.**
  - The `0353_agent_instruction_slimming` branch is just a backup reference point and should NOT be used as the primary dev branch.

---

## 7. Key Principles to Keep in Mind

- TDD is non-negotiable: write failing tests first, focus on behavior (mission content, protocol usage), not internal plumbing.
- Behavior authority:
  - `full_protocol` (server) > mission text > templates.
- Templates must be short and generic:
  - Role + MCP wiring only; no per-project team details, no full lifecycle duplication.
- Missions carry team context and dependencies:
  - This is where "you are ANALYZER, you work with DOCUMENTER" lives.

---

## 8. Implementation Summary (COMPLETED)

### 8.1 Team-Aware Missions (Backend)

**File:** `src/giljo_mcp/services/orchestration_service.py`

**Changes:**
- Added `_generate_team_context_header()` function that creates standardized mission headers
- Modified `get_agent_mission()` to:
  - Query all agent jobs for the same project (`stmt` now filters by `project_id`)
  - Generate and prepend team context header to mission text before returning

**Team Context Header Structure:**
```markdown
## YOUR IDENTITY
You are: {agent_name} (Role: {agent_type})
Your Job ID: {job_id} (use this for all MCP tool calls)

## YOUR TEAM
| Agent Name | Role | Deliverable |
|------------|------|-------------|
| analyzer   | analyzer | Folder structure analysis |
| documenter | documenter | Documentation updates |
...

## YOUR DEPENDENCIES
- If you are documenter: You depend on analyzer's folder structure analysis
- If you are implementer: You depend on analyzer's recommendations
...

## COORDINATION
Use these MCP tools for team coordination:
- send_message(to_agents=[...], content="...", project_id="{project_id}")
- receive_messages(agent_id="{agent_id}")
```

**Tests:** `tests/services/test_orchestration_service_team_awareness.py`
- 8 comprehensive tests covering:
  - Single agent missions (header still generated)
  - Multi-agent missions (full team table)
  - Dependency inference (upstream/downstream relationships)
  - Coordination messaging guidance
  - Team table formatting and content

### 8.2 Template Slimming

**File:** `src/giljo_mcp/template_seeder.py`

**Changes:**
- Slimmed `_get_check_in_protocol_section()`:
  - **Before:** ~2,500 chars (detailed CHECKPOINT 1-4 pseudo-code)
  - **After:** ~420 chars (brief reference to `full_protocol`)
  - Removed: Python while loops, import statements, detailed checkpoint logic
  - Added: Clear reference to `full_protocol` for detailed behavior

- Slimmed `_get_agent_messaging_protocol_section()`:
  - **Before:** ~4,500 chars (detailed Python examples, tool call format)
  - **After:** ~600 chars (concise tool summary with `full_protocol` reference)
  - Removed: Extensive Python pseudo-code, detailed call sequences
  - Kept: Essential tool names and when to use them

**Token Savings:**
- Total reduction: ~6,000 chars → ~1,020 chars
- **Token savings: ~1,495 tokens (~85% reduction)**

**Impact:**
- Seeded templates now focus on role + wiring
- All lifecycle behavior delegated to `full_protocol`
- No duplication between template and protocol
- Exported `.claude/agents/*.md` files are significantly leaner

**Tests:** `tests/services/test_template_seeder_slimming.py`
- 16 comprehensive tests covering:
  - Check-in protocol length constraints (<500 chars)
  - Messaging protocol length constraints (<700 chars)
  - Presence of `full_protocol` references
  - Absence of pseudo-code patterns (while, import, CHECKPOINT)
  - Content verification (essential tools preserved)
  - Integration with seeded templates

### 8.3 Additional Test Updates

**File:** `tests/unit/test_orchestration_service.py`

**Changes:**
- Updated `test_get_agent_mission_not_found` to account for new query pattern
- Added `project_id` to test job creation to match new team awareness logic
- Verified backward compatibility with existing orchestration service tests

---

## 9. Completion Summary

### What Was Delivered

✅ **Team-Aware Missions:**
- Agents now receive standardized team context in every mission
- Identity, team roster, dependencies, and coordination guidance all included
- Project-specific team information cleanly separated from generic templates
- 8 comprehensive tests ensuring behavior correctness

✅ **Template Slimming:**
- ~85% reduction in template bloat (1,495 tokens saved)
- Eliminated duplication between templates and `full_protocol`
- Templates now focus on role + MCP wiring only
- All lifecycle behavior delegated to server-side `full_protocol`
- 16 comprehensive tests ensuring slimming constraints

✅ **Test Coverage:**
- 24 new tests added across 2 new test files
- All tests passing with >80% coverage
- Behavior-focused TDD approach followed throughout

### Architecture Impact

**Layering Now Crystal Clear:**
1. **Template Layer** (minimal, generic):
   - Role description + MCP wiring
   - Points to `get_agent_mission()` for everything else
   - No lifecycle details, no team context

2. **Protocol Layer** (`full_protocol` from server):
   - Complete 6-phase lifecycle behavior
   - Check-in protocol, messaging protocol, error handling
   - Source of truth for all agent behavior

3. **Mission Layer** (project-specific):
   - Team context header (identity, roster, dependencies, coordination)
   - Agent-specific mission text
   - All project context and team awareness

**Benefits:**
- No more conflicting instructions between template and protocol
- Team awareness scales naturally (no template editing per project)
- Single source of truth for behavior (`full_protocol`)
- Massive token savings without loss of functionality

### Files Modified

**Backend Services:**
- `src/giljo_mcp/services/orchestration_service.py` (team context generation)
- `src/giljo_mcp/template_seeder.py` (template slimming)

**Tests:**
- `tests/services/test_orchestration_service_team_awareness.py` (new)
- `tests/services/test_template_seeder_slimming.py` (new)
- `tests/unit/test_orchestration_service.py` (updated)

**Documentation:**
- `handovers/0363_session_agent_instruction_slimming.md` (this file)
- `docs/CLAUDE.md` (to be updated with Handover 0353 reference)

### Next Steps

1. **Documentation Update:**
   - Add Handover 0353 to CLAUDE.md recent updates section
   - Document team-aware mission format in ORCHESTRATOR.md
   - Add template slimming strategy to architecture docs

2. **User Verification:**
   - Test exported `.claude/agents/*.md` files in real Claude Code sessions
   - Verify agents correctly parse team context headers
   - Confirm no regression in agent coordination behavior

3. **Future Enhancements:**
   - Consider adding visual dependency graph to UI
   - Explore auto-generating coordination rules from agent types
   - Add team context validation in `spawn_agent_job()`

### Success Criteria

✅ All tests passing (24 new tests, 100% pass rate)
✅ Token savings achieved (1,495 tokens, 85% reduction)
✅ Team awareness working (verified via integration tests)
✅ No breaking changes (backward compatibility preserved)
✅ TDD followed (RED → GREEN → REFACTOR cycle)
✅ Code quality maintained (>80% coverage, clean architecture)

**Status:** COMPLETE ✨

