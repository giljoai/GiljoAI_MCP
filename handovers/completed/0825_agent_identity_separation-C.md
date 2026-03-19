# Handover 0825: Agent Identity Separation from Mission Response

**Date:** 2026-03-18
**From Agent:** Research session (architecture analysis)
**To Agent:** Next Session
**Priority:** High
**Status:** Completed
**Edition Scope:** CE

---

## Task Summary

`get_agent_mission()` returns a single `mission` field that concatenates four semantic concerns into one text blob: team context, MCP bootstrap (system_instructions), role identity (user_instructions), and work order. These are separated only by Unicode box-drawing characters -- no semantic boundary. LLMs process this as one undifferentiated string with no reliable way to distinguish "who I am" from "what to do."

Separate the `MissionResponse` into distinct semantically labeled fields. One MCP tool call, structured response. No new tools, no new DB columns, no new round trips.

**Additionally:** Strip all token estimation code from `MissionResponse` and `SpawnResult` -- this is dead weight we no longer use.

---

## Context and Background

### Current flow (multi-terminal mode)

1. Orchestrator calls `spawn_agent_job()` which calls `_resolve_spawn_template()` (~line 804 in `orchestration_service.py`)
2. `_resolve_spawn_template()` looks up `AgentTemplate`, concatenates `system_instructions` + `user_instructions`, wraps them in box-art frames, and bakes ALL of it into `AgentJob.mission`
3. Agent calls `get_agent_mission()` (~line 955), which prepends the team context header to the already-bloated mission
4. Agent receives ONE massive string mixing identity, bootstrap, team roster, and work order

### Problems identified

1. **No semantic boundary** -- role identity and work order separated only by decorative Unicode frames
2. **Team table data bleed** -- `mission_lookup` dict contains template prose, so other agents' 80-char preview starts with `"...AGENT EXPERTISE..."` box art
3. **Redundant bootstrap** -- `system_instructions` tells agent to call `get_agent_mission()` but the agent already did that to get here
4. **Token waste** -- `estimated_tokens` fields in MissionResponse and SpawnResult are calculated but never consumed

### Key files

- `src/giljo_mcp/schemas/service_responses.py` -- MissionResponse + SpawnResult models
- `src/giljo_mcp/services/orchestration_service.py` -- `_resolve_spawn_template()` + `get_agent_mission()` + `spawn_agent_job()`
- `src/giljo_mcp/services/protocol_builder.py` -- `_generate_team_context_header()` + `_generate_agent_protocol()`
- `src/giljo_mcp/models/templates.py` -- AgentTemplate model (reference only, no changes)

---

## Implementation Plan

### Phase 1: Strip dead token estimation code

**Files:** `service_responses.py`, `orchestration_service.py`

**Step 1a -- MissionResponse** (`service_responses.py` ~line 374):
Remove the `estimated_tokens: int = 0` field entirely.

**Step 1b -- SpawnResult** (`service_responses.py` ~lines 349-352):
Remove these three fields:
```
prompt_tokens: int = 0
mission_tokens: int = 0
total_tokens: int = 0
```

**Step 1c -- get_agent_mission()** (`orchestration_service.py` ~line 1162):
Remove the `estimated_tokens = len(full_mission) // 4` calculation and remove `estimated_tokens=estimated_tokens` from the MissionResponse return kwargs.

**Step 1d -- spawn_agent_job()** (`orchestration_service.py`):
Remove the two calculation lines:
```python
prompt_tokens = len(thin_agent_prompt) // 4
mission_tokens = len(mission) // 4
```
Remove `prompt_tokens=prompt_tokens`, `mission_tokens=mission_tokens`, `total_tokens=prompt_tokens + mission_tokens` from the SpawnResult return kwargs.

**Step 1e -- Tests:** Find and fix any tests asserting on these removed fields.

### Phase 2: Add `agent_identity` field to MissionResponse

**File:** `service_responses.py` (~line 371 area)

Add a new optional field to MissionResponse:
```python
agent_identity: Optional[str] = None  # Template-derived role identity (who I am)
```

This field is `Optional` because blocked responses and error states don't include it, and CLI mode agents don't use it (they get identity from `.claude/agents/*.md`).

### Phase 3: Simplify `_resolve_spawn_template()`

**File:** `orchestration_service.py` (~line 804-894)

**Current behavior:** Looks up AgentTemplate, concatenates `system_instructions` + `user_instructions`, wraps them in Unicode box-art frames, and bakes the result into the `mission` string stored in AgentJob.

**New behavior:** Look up AgentTemplate, capture `template_id` only, return mission UNTOUCHED. No concatenation, no box art, no template content in the mission string.

Replace the method body:

```python
async def _resolve_spawn_template(
    self,
    session: AsyncSession,
    project: Any,
    agent_name: str,
    mission: str,
    tenant_key: str,
    agent_display_name: str,
) -> tuple[str, Optional[str]]:
    """
    Resolve template ID for multi-terminal mode.

    Handover 0825: In multi_terminal execution mode, look up the agent template
    and capture its ID for later identity resolution at read time (get_agent_mission).
    Template content is NO LONGER baked into the mission at spawn time.
    """
    resolved_template_id = None

    if project.execution_mode == "multi_terminal":
        template_result = await session.execute(
            select(AgentTemplate).where(
                and_(
                    AgentTemplate.name == agent_name,
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.is_active,
                )
            )
        )
        template = template_result.scalar_one_or_none()

        if template:
            resolved_template_id = template.id
            self._logger.info(
                "[TEMPLATE_RESOLVE] Captured template_id for read-time identity resolution",
                extra={
                    "agent_name": agent_name,
                    "template_id": template.id,
                    "execution_mode": project.execution_mode,
                },
            )
        else:
            self._logger.warning(
                f"[TEMPLATE_RESOLVE] No template found for agent_name={agent_name} "
                f"in multi-terminal mode. Agent will have no identity context.",
                extra={
                    "agent_name": agent_name,
                    "execution_mode": project.execution_mode,
                    "tenant_key": tenant_key,
                },
            )

    return mission, resolved_template_id
```

### Phase 4: Add identity resolution + framing directives to `get_agent_mission()`

**File:** `orchestration_service.py` (~line 955-1199)

This phase adds three things inside the existing `get_agent_mission()` method.

**Step 4a -- Identity resolution block.** Place this INSIDE the existing `async with self._get_session() as session:` block (before the session closes), after the team context header work but before the return. This avoids opening a second DB session.

```python
# --- Agent Identity Resolution (Handover 0825: read-time, not baked at spawn) ---
agent_identity = None
if job.template_id:
    template_result = await session.execute(
        select(AgentTemplate).where(
            and_(
                AgentTemplate.id == job.template_id,
                AgentTemplate.tenant_key == tenant_key,
            )
        )
    )
    identity_template = template_result.scalar_one_or_none()

    if identity_template:
        identity_parts = []

        # Framing directive -- tells the LLM how to process this field
        role_label = (identity_template.role or agent_name or "agent").upper()
        identity_parts.append(
            f"You are {role_label}. The following defines your expertise, "
            f"behavioral constraints, and success criteria. "
            f"Internalize these as your operating identity.\n"
        )

        # Role prose (user_instructions only -- system_instructions excluded
        # because the thin prompt already handles MCP bootstrap)
        if identity_template.user_instructions:
            identity_parts.append(identity_template.user_instructions)

        # Behavioral rules (structured list from template)
        if identity_template.behavioral_rules:
            rules = identity_template.behavioral_rules
            if isinstance(rules, list) and len(rules) > 0:
                rules_text = "\n".join(f"- {r}" for r in rules)
                identity_parts.append(f"\n## Behavioral Rules\n{rules_text}")

        # Success criteria (structured list from template)
        if identity_template.success_criteria:
            criteria = identity_template.success_criteria
            if isinstance(criteria, list) and len(criteria) > 0:
                criteria_text = "\n".join(f"- {c}" for c in criteria)
                identity_parts.append(f"\n## Success Criteria\n{criteria_text}")

        agent_identity = "\n\n".join(identity_parts)

        self._logger.info(
            "[AGENT_IDENTITY] Resolved identity from template at read time",
            extra={"job_id": job_id, "template_id": job.template_id},
        )
```

**IMPORTANT SESSION PLACEMENT NOTE:** The `get_agent_mission()` method has a main `async with self._get_session() as session:` block. The identity lookup MUST go inside this block (before it exits) to reuse the existing session. The implementor must trace the method flow to find the correct insertion point -- after `all_project_executions` and `mission_lookup` are built, but before the session context closes. The `AgentTemplate` import may need to be added at the top of the file if not already present.

**Step 4b -- Mission framing directive.** Change the `full_mission` assembly from:

```python
full_mission = team_context_header + raw_mission
```

to:

```python
mission_framing = (
    "This is your assigned work order. Execute the following tasks "
    "within the scope and team structure defined below.\n\n"
)
full_mission = mission_framing + team_context_header + raw_mission
```

**Step 4c -- Add `agent_identity` to MissionResponse return.** Find the existing return block and add `agent_identity=agent_identity,` to the constructor kwargs.

### Phase 5: Add framing directive to `full_protocol`

**File:** `protocol_builder.py` -- `_generate_agent_protocol()` function (~line 163)

Prepend a framing line to the returned protocol string. At the very end of the function, change the return to:

```python
protocol_framing = (
    "These are your lifecycle operating procedures. "
    "Follow them from startup through completion.\n\n"
)
return protocol_framing + f"""## Agent Lifecycle Protocol (5 Phases)
...existing content...
"""
```

### Phase 6: Fix broken tests

Tests that assert on removed fields or old injection behavior must be updated. **Do not skip tests -- make them work with the new design.**

#### HIGH priority (will fail immediately)

1. **`tests/schemas/test_service_responses_orchestration.py`**
   - `TestSpawnResult.test_creation_with_all_fields` (~lines 46-63): Remove `prompt_tokens=150`, `mission_tokens=80`, `total_tokens=230` from construction and their assertions (lines 60-62)
   - `TestMissionResponse.test_creation_with_all_fields` (~lines 106-126): Remove `estimated_tokens=500` from construction (line 114) and assertion (line 126). Add `agent_identity` field coverage.

2. **`tests/services/test_orchestration_service_agent_mission.py`**
   - `test_response_backward_compatible_with_existing_fields` (~line 216): Remove assertion `response.estimated_tokens is not None`. Add assertion for `agent_identity` field.

3. **`tests/unit/test_0813_template_context_separation.py`**
   - `TestResolveSpawnTemplateContent.test_concatenation_produces_role_focused_content` (~lines 390-428): **REWRITE entirely.** This test simulates the OLD concatenation behavior. Replace with a test that asserts mission is returned unchanged and only `template_id` is captured.

#### MEDIUM priority (fixtures used by other tests)

4. **`tests/fixtures/test_mock_agent_simulator.py`**
   - `mock_mission_response` fixture (~line 59): Remove `"estimated_tokens": 500` from mock MCP response payload.

5. **`tests/fixtures/orchestrator_simulator.py`**
   - Lines 267-283: Remove `mission_tokens = len(condensed_mission) // 4` calculation and its storage in `staging_result["context_prioritization"]["mission_tokens"]`.

6. **`tests/fixtures/test_orchestrator_simulator.py`**
   - `test_task5_context_and_mission` (~line 181): Remove assertion on `mission_tokens < 10000`
   - Cross-platform test (~line 386): Remove assertion on `mission_tokens <= 10000`

#### LOW priority (cosmetic -- tests still pass but reference dead field)

7. **`frontend/tests/stores/websocket.payload-normalization.spec.js`**
   - Lines 180, 193, 516, 551: Replace `estimated_tokens` with a different example field name (e.g., `agent_count`) in test payload data. These test WebSocket normalization mechanics, not the schema.

#### Files that do NOT need changes (confirmed false positives)

- `frontend/tests/components/projects/ProjectTabs.spec.js` -- uses `estimated_prompt_tokens` from staging API, unrelated
- `frontend/tests/unit/components/projects/LaunchTab.0243a.spec.js` -- same, different API
- `tests/schemas/test_service_responses_product.py` -- `total_tokens` belongs to `VisionUploadResult`, different model
- `tests/services/test_thin_client_prompt_generator_agent_templates_context.py` -- `estimated_prompt_tokens` from ThinClientPromptGenerator, unrelated
- `tests/schemas/test_service_responses_shared.py` -- uses only required SpawnResult fields, no token fields

---

## What NOT to Change

- **Thin prompt** in `spawn_agent_job()` -- unchanged, already correct
- **CLI mode** -- `_resolve_spawn_template()` already skips injection for CLI mode. This change only affects multi-terminal mode.
- **`_generate_team_context_header()`** -- unchanged, stays in `mission`
- **WebSocket `agent:created` payload** -- the `mission` field broadcast will now be cleaner (work order only). This is an improvement.
- **AgentJob.mission DB column** -- no schema change, just stores cleaner data
- **`update_agent_mission()`** -- unchanged
- **`get_orchestrator_instructions()`** -- unchanged, orchestrators have their own identity path
- **Context tools** `estimated_tokens` -- these are in fetch_context tools (get_testing, get_architecture, etc.) and are a SEPARATE concern. Do not touch them in this handover.

---

## Testing Requirements

### Unit/Integration Tests (TDD)

Write tests FIRST, then implement:

1. **`test_mission_response_has_agent_identity_field`** -- MissionResponse schema accepts `agent_identity`
2. **`test_resolve_spawn_template_returns_mission_unchanged`** -- multi-terminal spawn does NOT inject template into mission
3. **`test_get_agent_mission_returns_identity_from_template`** -- when `job.template_id` is set, `agent_identity` is populated with user_instructions prose
4. **`test_get_agent_mission_identity_none_when_no_template`** -- when `job.template_id` is None, `agent_identity` is None
5. **`test_get_agent_mission_identity_none_when_cli_mode`** -- CLI mode returns no identity (template_id not resolved)
6. **`test_mission_field_contains_no_template_content`** -- mission field does NOT contain box-art frames or template user_instructions
7. **`test_mission_field_has_framing_directive`** -- mission starts with work order framing text
8. **`test_full_protocol_has_framing_directive`** -- full_protocol starts with lifecycle framing text
9. **`test_team_table_preview_shows_work_order`** -- deliverables column shows work order preview, not template content
10. **`test_mission_response_no_estimated_tokens`** -- MissionResponse has no estimated_tokens field
11. **`test_spawn_result_no_token_fields`** -- SpawnResult has no prompt_tokens/mission_tokens/total_tokens fields

### Verification Checklist

After implementation, verify:
- [ ] Multi-terminal mode: `get_agent_mission()` returns three distinct fields (`agent_identity`, `mission`, `full_protocol`)
- [ ] `agent_identity` contains user_instructions prose with framing directive, NO system_instructions
- [ ] `mission` contains team header + work order, NO template content, NO box-art frames
- [ ] `full_protocol` starts with lifecycle framing directive
- [ ] Team table deliverables preview shows work order text, not template prose
- [ ] CLI mode: `agent_identity` is None
- [ ] Blocked response: `agent_identity` is None
- [ ] No template found: `agent_identity` is None with warning logged
- [ ] All existing tests pass (with fixes for removed token fields and template injection assertions)
- [ ] `ruff check src/ api/` passes clean
- [ ] No `estimated_tokens`, `prompt_tokens`, `mission_tokens`, or `total_tokens` remain in MissionResponse or SpawnResult

---

## No Migration Needed

Product is in dev mode with no deployments. Any existing test data in the local DB can be wiped with a fresh seed. No backward compatibility concerns for stored `AgentJob.mission` content.

---

## Success Criteria

- Agent receives its role identity as a labeled, separate field -- not buried in a text wall
- Work order is clean: team context + task only
- Zero token estimation dead code in mission/spawn response models
- All tests green -- legacy assertions updated to match new design
- No new files created (modifications to existing files only)

---

## Progress Updates

### 2026-03-18 - Implementation Session
**Status:** Completed
**Commit:** `1aebbcd8` — feat: Separate agent identity from mission response (0825)

**Work Done:**
- Phase 1: Stripped dead token estimation fields (`estimated_tokens` from MissionResponse, `prompt_tokens`/`mission_tokens`/`total_tokens` from SpawnResult)
- Phase 2: Added `agent_identity: Optional[str] = None` field to MissionResponse
- Phase 3: Simplified `_resolve_spawn_template()` to capture `template_id` only — no more template content baked into mission at spawn time
- Phase 4: Added identity resolution in `get_agent_mission()` at read time from AgentTemplate, plus mission framing directive
- Phase 5: Added lifecycle framing directive to `full_protocol` in `protocol_builder.py`
- Phase 6: Updated 7 test/fixture files — removed dead token field assertions, rewrote template concatenation test, added agent_identity coverage
- 13 files changed, 1478 tests passing, 0 regressions

**Key Files Modified:**
- `src/giljo_mcp/schemas/service_responses.py` (schema changes)
- `src/giljo_mcp/services/orchestration_service.py` (spawn + mission logic)
- `src/giljo_mcp/services/protocol_builder.py` (framing directive)
- 7 test/fixture files updated for new design

**All success criteria met.**
