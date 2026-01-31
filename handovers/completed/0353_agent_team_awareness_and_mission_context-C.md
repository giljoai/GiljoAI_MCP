# Handover 0353: Agent Team Awareness & Mission Context

**Date**: 2025-12-19
**Status**: ✅ COMPLETED
**Completed**: 2026-01-30
**Priority**: High
**Type**: Mission/Prompt Architecture Enhancement
**Builds Upon**: 0246b (Generic Agent Template), 0254 (Three-Layer Instruction Cleanup), 0332/0333 (Staging & Execution Prompting), 0349 (Agent Execution Context Refactor)

---

## Completion Summary

### What Was Implemented

**Core Feature (Already Done)**:
- ✅ `_generate_team_context_header()` function in `orchestration_service.py` (lines 68-196)
- ✅ Integrated into `get_agent_mission()` MCP tool
- ✅ Generates 4 sections: YOUR IDENTITY, YOUR TEAM, YOUR DEPENDENCIES, COORDINATION

**Tests Fixed (This Session)**:
- ✅ Rewrote `tests/services/test_orchestration_service_team_awareness.py`
- ✅ 11 unit tests now pass (were ALL SKIPPED)
- ✅ Tests verify behavior of `_generate_team_context_header()` directly
- ✅ Tests cover: identity section, team roster, dependency inference, coordination guidance

**Template Slimming Decision**:
- ❌ **NOT NEEDED** - Templates already lean and correctly structured
- Templates contain role-specific guidance (TDD, documentation patterns, etc.)
- Team context is dynamically injected via `_generate_team_context_header()`
- This separation is correct: templates = role guidance, mission = team context

### Key Files

- `src/giljo_mcp/services/orchestration_service.py:68-196` - `_generate_team_context_header()`
- `src/giljo_mcp/services/orchestration_service.py:920-1166` - `get_agent_mission()` (calls team header)
- `tests/services/test_orchestration_service_team_awareness.py` - 11 passing tests

### Test Results

```
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_your_identity_section_contains_role_and_ids PASSED
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_your_team_section_lists_all_agents PASSED
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_your_dependencies_section_analyzer_has_downstream PASSED
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_your_dependencies_section_documenter_has_upstream PASSED
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_your_dependencies_section_implementer_has_both PASSED
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_coordination_section_mentions_messaging_tools PASSED
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_single_agent_project_still_gets_all_sections PASSED
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_mission_lookup_dict_used_when_provided PASSED
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_multi_agent_team_roster_completeness PASSED
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_dependency_inference_tester_depends_on_implementer PASSED
tests/services/test_orchestration_service_team_awareness.py::TestTeamContextHeader::test_unknown_role_has_no_dependencies PASSED

11 passed in 0.82s
```

---

---

## Executive Summary

**Problem**

Individual agents (analyzer, documenter, implementer, etc.) currently:
- Know their *role type* loosely from the template (e.g., "Implementation specialist for production-grade code")
- Receive a mission string from `get_agent_mission()`
- Receive a generic `full_protocol` describing lifecycle behavior

But they **do not** receive explicit:
- Identity framing within the team (e.g., “You are ANALYZER on this project”)
- Team composition (who the other agents are and what they’re doing)
- Dependency information (who depends on whom, and on what)
- Coordination guidance (when and who to message)

Result: agents behave as if they’re working alone, even when they are part of a multi-agent plan. In the TinyContacts example:
- Analyzer and Documenter were both spawned but were not told about each other.
- Documenter wrote `docs/index.md` without knowing whether analyzer had finished the folder structure.
- No explicit dependency signaling took place (no clear “folder structure ready, documenter can proceed” moment).

**Goal**

Introduce a **team-aware mission structure** so that each agent’s mission includes:
1. **Your Identity** – role + job_id in this project.
2. **Your Team** – a compact roster of other agents, their roles, and deliverables.
3. **Dependencies** – what this agent depends on and what others depend on from this agent.
4. **Coordination Hints** – who to message and when, using existing MCP tools.

This should be done without stuffing role templates with team details (templates stay generic); the orchestrator becomes the single source of team context via mission text.

---

## Scope

### In Scope

- **Mission generation** for spawned agents:
  - Orchestrator staging/mission-plan structures (`orchestrate_project`, `spawn_agent_job`) for execution phase.
  - `MCPAgentJob.mission` content at spawn time.
- **Seeded templates & export**:
  - Base agent templates in `template_seeder.py` (DB seed).
  - Agent Template Manager → export → `.claude/agents/*.md` pipeline.
- **Protocols and authority**:
  - Clarify that:
    - Behavior = `full_protocol` from `get_agent_mission()`.
    - Team context and identity = mission text from the orchestrator.
    - Templates = role + wiring, not team-specific behavior.

### Out of Scope

- Changes to MCP tools’ transport or schema (no changes to `get_agent_mission` response structure beyond mission text).
- Changes to WebSocket behavior (already fixed in 0286/0362).
- Any direct one-off modifications to `.claude/agents/*.md` files outside the seeder/DB/export pipeline.

---

## Current Behavior (Team Awareness)

**Templates (Seeded & Exported)**
- `template_seeder.py` seeds base templates for:
  - orchestrator, implementer, tester, analyzer, reviewer, documenter.
- Exported `.claude/agents/*.md`:
  - Contain a large MCP protocol section (startup, progress, completion).
  - Role descriptions.
  - Tool call examples with placeholders (`<AGENT_TYPE>`, `<TENANT_KEY>`, `<PROJECT_ID>`).
- *They do not know about specific teammates* for a given project/missions; they are generic profiles.

**Orchestrator Missions & Spawns**
- Orchestrator staging (via `get_orchestrator_instructions`) produces:
  - A list of agent jobs to spawn (agent_name, agent_type, mission, etc.).
- `spawn_agent_job` stores:
  - `MCPAgentJob` record with `mission` string (per-agent).
  - Each mission is focused on that agent’s slice of work with little/no explicit team context.

**Protocols**
- `get_agent_mission()` returns:
  - `mission` (string).
  - `full_protocol` (multi-phase lifecycle instructions).
- `full_protocol` assumes:
  - Agents will coordinate via `send_message`, `receive_messages`, etc.
  - But does not enumerate teammates or dependencies for this particular project; that information lives only in the orchestrator’s plan, not in per-agent missions.

---

## Target Behavior (Team-Aware Missions)

### 1. Mission Structure for Spawned Agents

For each agent job, the `mission` field should start with a standardized structure:

```markdown
## YOUR IDENTITY
You are **{ROLE_NAME}** (job_id: {job_id})
Role: {role_description}

## YOUR TEAM
This project has {N} agents working together:

| Agent       | Role         | Deliverables                              |
|------------|--------------|-------------------------------------------|
| analyzer   | Folder design| Directory tree + DESCRIPTION.md files     |
| documenter | Documentation| README.md, docs/index.md, requirements.txt|
| implementer| (if present) | Code changes / scripts                    |

## YOUR DEPENDENCIES
- You depend on: {list of upstream agents and what you need from them}
- Others depend on your work for: {list of downstream agents + artifacts}

## COORDINATION
- When you complete {X}, send a message to {downstream_agents}:
  `COMPLETE: {X} ready. {Downstream} can proceed with {Y}.`
- Use `mcp__giljo-mcp__send_message` and `mcp__giljo-mcp__receive_messages` as described in `full_protocol`.
```

Notes:
- Exact wording should be concise and token-aware but follow this shape.
- The **team table** is generated from the orchestrator’s staging plan (which already knows which agents exist and what their missions are).

### 2. Templates Stay Generic and Light

Seeded/exported templates (e.g., `.claude/agents/implementer.md`) should:
- Keep:
  - Front matter (name/description/model).
  - “MCP tools are native” CRITICAL section.
  - Role-specific guidance (e.g., implementer = TDD, tester = coverage, etc.).
  - A short startup block:
    - “Call `mcp__giljo-mcp__get_agent_mission(agent_job_id, tenant_key)`.”
    - “Follow `full_protocol` for lifecycle behavior.”
    - “Team information (if any) is in your mission text.”
- Remove:
  - Full Phase 1–6 lifecycle instructions (delegated to `full_protocol`).
  - CHECK-IN PROTOCOL Python pseudo-code.
  - Inter-agent messaging pseudo-code; instead, refer to mission + `full_protocol`.
  - Placeholder-heavy examples that could conflict with real IDs.

### 3. Authority Clarification

Reinforce in `full_protocol` and mission text:
- If there is any conflict between:
  - Template instructions and `full_protocol` → follow `full_protocol`.
  - Template instructions and mission text → mission + `full_protocol` win.
- Team context (who you’re working with, dependencies) = mission.
- Behavior (when to report progress, how to handle errors, messaging cadence) = `full_protocol`.

---

## Implementation Plan

### Step 1 – Generate Team Context at Staging Time

1. Extend the orchestrator’s staging plan (where agent jobs are defined) to:
   - Capture for each agent:
     - `role_name` (implementer/tester/analyzer/documenter/etc.).
     - `deliverables` (short summary from its mission).
     - `dependencies_upstream` / `dependencies_downstream` (if known).
2. Store this information in a structure the orchestrator can access when calling `spawn_agent_job` (e.g., in the mission plan or a per-agent context field).

### Step 2 – Inject Team-Aware Mission Text in `spawn_agent_job`

1. In `OrchestrationService.spawn_agent_job` (or the higher-level staging logic that constructs missions):
   - Build a mission string that:
     - Begins with the standardized “YOUR IDENTITY / YOUR TEAM / YOUR DEPENDENCIES / COORDINATION” sections.
     - Appends the role-specific mission body (what this agent must do).
2. Ensure that for each agent:
   - `role_name` is explicit (`ANALYZER`, `DOCUMENTER`, etc.).
   - The team table lists all other active agents with roles + deliverables.
   - Dependencies are described in plain language (“Documenter depends on analyzer’s folder structure for docs/index.md”).

### Step 3 – Slim Seeded Templates (Seeder → DB → Export)

1. Update `template_seeder.py`:
   - Adjust base templates’ content to:
     - Keep the critical MCP wiring + role sections.
     - Remove embedded lifecycle phases, CHECK-IN PROTOCOL, and inter-agent messaging pseudo-code.
     - Add a simple note: “Your mission will describe your teammates and dependencies for each project.”
2. Verify that:
   - The Agent Template Manager shows the new, slimmer templates.
   - The export function that generates `.claude/agents/*.md` pulls from these updated DB templates.
3. Avoid hand-editing `.claude/agents/*.md` directly; treat the DB + seeder as the source of truth, export as the projection.

### Step 4 – Clarify ID Usage in Protocol Text

1. Update `_generate_agent_protocol` to:
   - Include a short ID mapping:
     - `job_id` / `agent_job_id` = UUID used in MCP tools.
     - `agent_name` = template role (implementer/tester/etc.).
   - Use these terms consistently across examples.
2. Ensure the mission text and templates use the same naming (no mixed `agent_id`/`job_id` placeholders).

### Step 5 – Testing and Validation

1. Add unit/integration tests for mission content:
   - For a multi-agent staging plan (analyzer + documenter):
     - `get_agent_mission` for each agent should return:
       - `mission` starting with “YOUR IDENTITY / YOUR TEAM / YOUR DEPENDENCIES / COORDINATION”.
       - A team table listing both agents with roles and deliverables.
2. Add a focused test for template export:
   - Export `.claude/agents/*.md` and assert:
     - Presence of MCP wiring and role-specific text.
     - Absence of full lifecycle protocol text (phases, check-in pseudo-code).
3. Manual test:
   - Re-run the TinyContacts scenario:
     - Confirm analyzer and documenter both see explicit team sections.
     - Confirm they coordinate via messages as described.

---

## Risks & Mitigations

- **Risk:** Missions become too verbose.
  - Mitigation: Keep the team sections compact (short table + 1–2 bullets per dependency).
- **Risk:** Template changes break user expectations.
  - Mitigation: Document in release notes that behavior is now driven by `full_protocol`/mission; templates are role-only. Existing workflows continue to work, just with less duplicated protocol text.
- **Risk:** Agents ignore team info.
  - Mitigation: In `full_protocol`, explicitly tell agents to read the team/dependency sections in their mission and use messaging tools to coordinate.

---

## Summary

This handover adds **team awareness** as a first-class concept in agent missions without bloating templates or conflicting with `full_protocol`. The orchestrator will:
- Tell each agent who they are, who they’re working with, how their work fits into the overall plan, and how to coordinate.
- Keep behavior rules centralized in `full_protocol`.

Seeded/exported templates will remain lean role profiles plus MCP wiring, relying on missions to describe the concrete team and dependencies for each project.

