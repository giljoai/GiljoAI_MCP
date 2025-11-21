# Launch & Implementation UI Refactor - Agentic Codex Plan

## Purpose
- Build a stepwise plan agents can execute to land the Launch/Implement visuals from `handovers/Launch-Jobs_panels2/Refactor visuals for launch and implementation.pdf` as the product template.
- Stay aligned with `handovers/013A_code_review_architecture_status.md`, `handovers/code_review_nov18.md`, `handovers/start_to_finish_agent_FLOW.md`, and `handovers/Simple_Vision.md`.
- Cover both GUI and the minimum backend wiring so the experience is real, not static.

## Guardrails for agent tools
- TDD only: write failing tests first, then minimal code, then refactor; assert behavior, not implementation; descriptive names (e.g., `test_status_board_updates_on_ack`).
- Service-layer only endpoints; keep `tenant_key` everywhere; MCP is HTTP-only.
- Preserve componentization momentum; no new monolith views; prefer extracted components and typed contracts.
- Avoid legacy spawn paths; add telemetry around `_spawn_generic_agent` before removal.
- Clipboard and messaging UIs must be testable with mocks (no brittle DOM hacks).

## Design anchors (deck map)
- Launch tab: 1a pre-staging empty, 1b navigable with empty implement layout, 1c implement faded before staging, 1d pre-stage with default orchestrator ready, 1e “stage project” copies prompt.
- Orchestrator run: 2a working spinner while mission fills, 2b mission done + agents assigned, Launch Jobs enabled, 2c Launch Jobs switches to filled Implement tab.
- Implement tab (Claude Code CLI): slides 3a-3i — single terminal prompt, status board, waiting → working → completed, message composer/broadcast, per-agent history. Requires new status reporting.
- Implement tab (General CLI): slides 4a-4h — toggle off, unique prompts per agent, reuse indicators, same status board/broadcast/history, staggered starts.
- Future slide 28 parked.

## Key risks & dependencies
- Need richer agent/job status enums (waiting/working/completed/ack/read counts) and message history feed (sent/received/ack/broadcast) exposed via services and typed client.
- Clipboard copying must be UX-safe; tests need mocks/spies.
- Legacy orchestrator paths exist; must confirm non-usage before removal.
- Existing component debt (Settings/Products) — ensure imports scoping to avoid regressions.

## Phased plan (agent-executable scopes)

### Phase 0 — Discovery & Contracts
- Map current Launch/Implement routing and components (ProjectLaunchView, Jobs/Message stream) to deck states; capture gaps.
- Define contracts: status board payload, per-agent prompt payloads, mission text, message history schema, broadcast vs direct send APIs.
- Add temporary logging around `_spawn_generic_agent` to detect legacy fallbacks.
- Tests (failing first): contract tests for status payload shape; placeholder component tests asserting state names/transitions exist.
- Artifacts: annotated state map, API gap list, test stubs.

### Phase 1 — Launch Tab UX Foundation
- Implement staged visuals for 1a–1e: empty → default orchestrator ready → staging spinner → mission filled, Launch Jobs enabled.
- Wire “Stage project” CTA to copy-to-clipboard prompt with reuse indicator; keep service calls in service layer.
- Ensure Implement tab shows faded/empty when accessed early.
- Tests: state renders per project status; clipboard handler invoked with expected prompt; Launch Jobs enablement toggles correctly.
- Deliverables: updated Launch tab components, passing unit tests for state control.

### Phase 2 — Implement Tab (Claude Code CLI mode)
- Add Claude Code toggle ON state with single orchestrator prompt; other agent buttons disabled.
- Build status board MVP (Agent Type, Subagents, Status, Messages Sent/Read, Job Read/Ack) per slides 3a–3i.
- Flows: copy orchestrator prompt; transition waiting → working → completed; message composer + broadcast; per-agent history view.
- Tests: state machine tests for statuses; buttons disabled/enabled per state; history lists sent/received/ack rows.
- Deliverables: Claude-mode UI variant and tests for transitions/history.

### Phase 3 — Implement Tab (General CLI mode)
- Toggle OFF exposes per-agent prompt buttons (unique text), reuse indicators, status board, broadcast/direct send, history.
- Model staggered starts (4e–4g) and reuse indicators after copy.
- Tests: uniqueness of prompts; reuse indicator toggles; status board updates per agent; broadcast vs direct send behavior.
- Deliverables: General-mode UI and tests for per-agent prompts and messaging behaviors.

### Phase 4 — Backend Status & Messaging Wiring
- Extend status enums/persistence for waiting/working/completed/ack/read counts; expose via orchestration service + endpoints (service-layer only, tenant-scoped).
- Implement message history feed with pagination/filter for sent/received/ack/broadcast; add typed client adapter.
- Add telemetry for legacy spawn fallbacks and keep MCP HTTP-only.
- Tests: service-level status transition tests; API tests for history filters; contract tests for status board payloads.
- Deliverables: backend surface + typed client ready for UI consumption, green tests.

### Phase 5 — Regression & Template Hardening
- Run cross-view regression (Projects, Products, Settings) to ensure no import or layout regressions.
- Story/state walkthroughs mirroring deck sequences (1a->1e, 2a->2c, 3a->3i, 4a->4h) with screenshots/notes.
- Tests: end-to-end happy path (stage -> launch jobs -> orchestrator working -> agents running), plus failure cases (clipboard blocked, status fetch error).
- Deliverables: final walkthrough notes in handovers, updated handover summary, all tests passing.

## Acceptance criteria
- Launch/Implement tabs match deck states (copy, layout, toggles, prompts, status counts) and serve as the product’s temporary visualization template.
- New backend touchpoints live in services, respect tenant_key, avoid legacy spawn paths, and are covered by tests written first.
- Unit/component/API/E2E tests are added and green; behavior-centric.
- No regressions in Projects/Products/Settings; builds clean.
