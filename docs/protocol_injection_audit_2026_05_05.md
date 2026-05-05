# Protocol Injection Audit — `set_agent_status` Touch Points

**Date:** 2026-05-05
**Project:** BE-staging-lock (server-lock + downstream + protocol rewrites)
**Audit scope:** every site that mentions `set_agent_status`, or describes the `blocked`/`idle`/`waiting` status transitions in user-facing protocol text or templates.

**Classification:**
- **REWRITE** — instructs the orchestrator to call `set_agent_status` during staging; will now produce a 403 STAGING_LOCK and so must be replaced with the inline-ask + `report_progress` pattern.
- **REFRAME** — describes valid status transitions (including the staging window) and should be split into "Staging phase (orchestrator only)" vs "Implementation phase (all agents)" so the staging lock is documented, not contradicted.
- **ADD LOCK NOTE** — tooling description / catalogue; safe to keep but must mention the staging-window 403 so callers aren't surprised.
- **SAFE** — references that talk about the implementation phase, post-staging coordination, or post-completion reactivation. No change needed.

---

## REWRITE

| File | Line(s) | Current text | Why it needs rewrite |
|---|---|---|---|
| `src/giljo_mcp/template_seeder.py` | 283-291 | `## If Requirements Are Unclear` block instructs the orchestrator: `1. Call set_agent_status(job_id, status="blocked", reason="BLOCKED: <reason>")` during staging. | This is the primary instruction site that triggered the BE-staging-lock project. Calling `set_agent_status` during staging now returns 403 STAGING_LOCK. Replace with inline-ask + `report_progress` pattern. |
| `src/giljo_mcp/services/protocol_sections/chapters_reference.py` | 232 | `── MCP Connection Lost ──` action: `Notify: Call set_agent_status(...status="blocked"...)`. | This sits in CH4 ERROR HANDLING which is rendered into the orchestrator protocol. During staging, this instruction will be locked out. |
| `src/giljo_mcp/services/protocol_sections/chapters_reference.py` | 243 | `── Spawn Failure ──` action: `Log via set_agent_status(status="blocked")`. | Same — orchestrator-only error path that would 403 during staging. |
| `src/giljo_mcp/services/protocol_sections/chapters_reference.py` | 277-283 | `GENERAL ERROR PROTOCOL` step 2: `Call set_agent_status(status="blocked", reason="...") to persist error state`. | Generic error advice rendered to the orchestrator; same problem. |

---

## REFRAME

| File | Line(s) | Current text | Why it needs reframe |
|---|---|---|---|
| `src/giljo_mcp/services/protocol_sections/chapters_reference.py` | 259-275 | `STATUS TRANSITIONS` ASCII diagram includes `working ─[set_agent_status("blocked")]──→ blocked` without distinguishing staging vs implementation. | The `working → blocked` transition is locked for the orchestrator during staging. Diagram should split into a "Staging (orchestrator only)" subset (no `set_agent_status` arrows for orchestrator) and an "Implementation (all agents)" subset (full diagram). |

---

## ADD LOCK NOTE

| File | Line(s) | Current text | Why it needs the note |
|---|---|---|---|
| `api/endpoints/mcp_sdk_server.py` | 868-874 | `@mcp.tool(description="Set agent resting or blocked status. Valid statuses: ...")` | This is the `mcp_tools_available` description rendering for `set_agent_status` (visible to every agent). Add: "During staging, this tool is server-locked for the orchestrator (returns 403 STAGING_LOCK). Use `report_progress` to log conversation state." |

---

## SAFE (no change)

| File | Line(s) | Why no change |
|---|---|---|
| `src/giljo_mcp/services/protocol_sections/agent_protocol.py` | 192-275 | Phase 5 ERROR HANDLING & BLOCKED STATUS is rendered to **non-orchestrator** agents (spawned implementers/testers/etc.). Spawned agents bypass the staging lock. |
| `src/giljo_mcp/services/protocol_sections/chapters_reference.py` | 354-355 | `set_agent_status(idle/sleeping)` is for **after agents are dispatched** — i.e. post-staging-complete (`staging_status == "staging_complete"`). Lock does not apply. |
| `src/giljo_mcp/services/protocol_sections/chapters_reference.py` | 557-638 | Reactivation, dismissal, complete→blocked transitions — all post-implementation; lock window is closed. |
| `src/giljo_mcp/services/protocol_sections/agent_lifecycle.py` | 215-232 | `RESTING STATES` block: orchestrator post-dispatch (idle / sleeping). By construction this is post-staging-complete; lock does not apply. |
| `src/giljo_mcp/services/protocol_sections/agent_lifecycle.py` | 122 | Describes `waiting → working` server-side auto-transition (not an agent-callable tool). |
| `src/giljo_mcp/services/protocol_sections/agent_lifecycle.py` | 262 | `set status blocked with reason "Closeout: awaiting user review"` — closeout phase, post-implementation; lock window long closed. |
| `src/giljo_mcp/template_seeder.py` | 860-871 | `## If Blocked or Unclear` block in the **non-orchestrator** template (workers). Spawned agents bypass the lock. |
| `src/giljo_mcp/services/orchestration_service.py` | 312-314 | Service-layer thin delegate; not user-facing protocol text. |
| `src/giljo_mcp/services/message_service.py` | 515 | Internal comment about completion-on-message vs mid-work block — not rendered to agents. |
| `src/giljo_mcp/services/mission_orchestration_service.py` | 421-442 | Mentions tool name in the `mcp_tools_available` catalogue / job_id usage hint. Tool naming, not protocol guidance. (The dedicated tool description at `api/endpoints/mcp_sdk_server.py:868` is where the staging-lock note belongs — single source of truth.) |
| `src/giljo_mcp/validation/rules.py` | 257-284 | Template validation rule that checks templates *mention* `set_agent_status`. Doesn't itself instruct anyone — and the rewritten orchestrator template still mentions the tool. |
| `src/giljo_mcp/template_renderer.py` | 354 | Tool-name list in the rendered tool catalogue. Naming, not guidance. |
| `src/giljo_mcp/schemas/responses/orchestration.py` | 184 | Docstring of `ErrorReportResult` Pydantic model. Internal API doc. |
| `src/giljo_mcp/schemas/responses/orchestration.py` | 429 | Closeout-time advice — post-staging; lock window closed. |
| `src/giljo_mcp/tools/write_360_memory.py` | 96 | Comment string referencing the agent-state tool family for Handover 0950j. Internal comment. |
| `src/giljo_mcp/tools/tool_accessor.py` | 641-653 | Thin tool-accessor delegate; not user-facing. |
| `src/giljo_mcp/services/orchestration_agent_state_service.py` | 504+ | The service implementation itself (now contains the lock). Not protocol text. |
| `src/giljo_mcp/system_prompts/`, `src/giljo_mcp/mission_planner.py`, `src/giljo_mcp/template_manager.py`, `src/giljo_mcp/prompts/` | — | Grep returned **zero hits**. No protocol injection from these subsystems mentions `set_agent_status`. Nothing to fix. |

---

## Outcome

Layer 3 rewrites land in the four REWRITE rows + the one REFRAME row + the one ADD-LOCK-NOTE row above. Snapshot tests assert the old instructions are gone and the new ones are present. SAFE rows are documented here for future auditors so the next person knows we considered them and chose not to touch.
