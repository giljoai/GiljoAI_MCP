# CodexContext Review — Phase 2 Plan

Date: 2025-10-08

---

## Objectives

- Harden hierarchical, role-aware context delivery for all agents.
- Finalize large-vision document handling with reliable indexing and retrieval.
- Remove duplication across context tools, ensuring a single source of truth.
- Fix minor inconsistencies discovered during Phase 1.
- Add validation, tests, metrics, and docs to make the system verifiable and maintainable.

---

## Summary of Phase 1 State (Verified)

- `Product.config_data` JSONB exists with GIN index and is used throughout discovery.
- Role-based config filtering implemented (full for orchestrator, filtered for workers).
- Vision document chunking and indexing implemented; MCP tools exposed.
- Orchestrator template enforces discovery-first, 30-80-10, and 3-tool rule.
- Seeding pipeline for `config_data` exists.

Key files referenced:
- src/giljo_mcp/models.py:58 — `config_data` JSONB + indexes
- src/giljo_mcp/context_manager.py:84 — `get_filtered_config`
- src/giljo_mcp/discovery.py:212 — `discover_context` pipeline
- src/giljo_mcp/tools/context.py:1339 — `get_vision` tool (DB + FS, chunk + index)
- src/giljo_mcp/tools/context.py:1415 — `get_vision_index` tool (DB + FS)
- src/giljo_mcp/tools/chunking.py:196 — `chunk_content` API
- src/giljo_mcp/template_manager.py:150 — Orchestrator template (discovery, vision, guardrails)
- scripts/seed_config_data.py:1 — Seeding `config_data` from detection

---

## Phase 2 Scope

In Scope
- Role-aware context for all access paths (MCP and API), including proper `agent_name` propagation.
- Vision tooling reliability: indexing lifecycle, hashing, reindex triggers, endpoint parity.
- Context tool deduplication and cleanup.
- Tests (unit, integration, performance) and minimal dashboard/API visibility for context status.
- Fixes for identified inconsistencies.

Out of Scope
- New agent types or major template redesigns.
- Non-PostgreSQL database support.
- Broad UI redesign.

---

## Deliverables

0) Native Subagent Roles (Catalog + Mission Overlays)
- Establish a catalog of native coding subagent role templates (Implementer, Tester, Researcher, Documenter, Reviewer), stored via `AgentTemplate` with `category: role_template`.
- Missions become overlays that augment these stable role templates (objectives, scope boundaries, constraints, success criteria), rather than redefining skills per mission.
- Agent assignment selects a role template and attaches the mission overlay; do not restate duties/skills in the mission.
- Persist selected `role_template_id` in `Agent.meta_data` (initially; consider a dedicated column later) and store mission overlay in `Job.meta_data`.
- Ensure discovery passes filtered role-aware context to the spawned worker (implementer/tester/etc.).

1) Role-Aware Context Hardening
- Add `agent_name` (and optional `agent_role`) to the MCP `discover_context` tool and pass through to `DiscoveryManager` so workers consistently receive filtered `product_config`.
  - Files:
    - src/giljo_mcp/tools/context.py:376 — add parameters and forward `agent_name`/`agent_role` to `discovery_manager.discover_context(...)`.
    - src/giljo_mcp/discovery.py:212 — ensure role filtering path is exercised when `agent_name` is present.
  - Behavior:
    - Orchestrator: full `product_config`.
    - Workers: filtered `product_config` aligned with `ROLE_CONFIG_FILTERS`.

2) Vision Endpoint Parity Fix
- Align endpoint call with chunker API: rename `source_name` → `document_name` in vision chunking calls.
  - Files:
    - api/endpoints/products.py:413, api/endpoints/products.py:479 — use `document_name=...` for `chunk_content(...)`.

3) Context Tool Deduplication
- Consolidate duplicate wrappers in `src/giljo_mcp/tools/context.py` to a single implementation for:
  - `get_vision`, `get_vision_index`, `discover_context`, and `get_context_index`.
  - Ensure MCP registration happens once and all call paths use the same internal functions.

4) Vision Index Lifecycle & Reindexing
- Content-hash–based change detection is present; add reindex triggers and TTL safeguards:
  - Reindex on file hash change or `force_reindex=True` (keep param on `get_vision`).
  - Optional TTL for index invalidation (configurable via env / config).
  - Ensure index entries map chunks to files deterministically.
  - Files:
    - src/giljo_mcp/tools/context.py — ensure index rebuild path is robust.
    - src/giljo_mcp/discovery.py — align any cached path/metadata with TTL.

5) Metrics & Visibility
- Emit metrics for context/vision loads (tokens used, chunk counts, filtered field counts).
  - Files:
    - src/giljo_mcp/discovery.py — attach counts into `context["metadata"]`.
    - api/websocket.py — include context usage deltas where appropriate.

6) Tests
- Unit tests:
  - `get_product_config(filtered=True, agent_name=...)` returns role-appropriate fields.
  - `discover_context(agent_name, agent_role)` returns filtered config for workers, full for orchestrator.
  - Vision endpoint correctly passes `document_name` and returns chunked content.
  - Index rebuild on `force_reindex=True`.
- Integration/perf tests:
  - Reuse `tests/test_vision_chunking.py`, `tests/test_vision_chunking_comprehensive.py` and add small targeted cases.

7) Docs
- Update README and CLAUDE docs to reflect role-aware discovery usage and the `discover_context` parameters.
- Add a short troubleshooting note for vision indexing.

8) Seed Role Templates (Initial Catalog)
- Provide a small seeding script to create baseline role templates with formal duties/skills/guardrails.
- Example fields per template: `name`, `category: role_template`, `role`, `template_content` (duties + skills + tool usage), `behavioral_rules`, `success_criteria`, `variables`.
- Include at least: Implementer, Tester, Researcher, Documenter, Reviewer.

---

## Implementation Steps

1. Wire `agent_name` through discovery
- Update MCP tool signature and pass along to `DiscoveryManager`.
- Default behavior: if `agent_name` not provided, fall back to existing behavior.
- Reference: src/giljo_mcp/tools/context.py:376, src/giljo_mcp/discovery.py:212.

2. Fix vision endpoint parameter name
- Rename `source_name` to `document_name` in calls to `chunk_content`.
- Reference: api/endpoints/products.py:413, api/endpoints/products.py:479; src/giljo_mcp/tools/chunking.py:196.

3. Remove duplicates and register once
- Normalize `get_vision`, `get_vision_index`, `discover_context`, `get_context_index` to a single code path.
- Ensure MCP registration is singular.
- Reference: src/giljo_mcp/tools/context.py:235, src/giljo_mcp/tools/context.py:1415.

4. Index lifecycle and TTL
- Add a TTL knob (env/config) to invalidate cached paths and indices.
- Respect `force_reindex` and file hash changes.
- Reference: src/giljo_mcp/tools/context.py:1339 (get_vision), src/giljo_mcp/discovery.py:150 (PathResolver cache).

5. Metrics
- Add token counts and field counts to discovery metadata.
- Surface key deltas over WebSocket for dashboards.
- Reference: src/giljo_mcp/discovery.py:212, api/websocket.py:501.

6. Tests
- New: tests/test_discover_context_filters.py — worker vs orchestrator assertions.
- Extend: tests/unit/test_tools_context.py — reindex, endpoint param coverage.
- Perf: validate chunking under large content (reuse existing perf suites).

7. Docs
- README and CLAUDE updates on discovery usage; quick “vision index troubleshooting”.

8. Subagent Role Catalog & Overlays
- Add `scripts/seed_role_templates.py` (optional) to seed baseline role templates.
- Update orchestrator guidance: “select role template + attach mission overlay”; explicitly prohibit redefining skills in missions.
- Extend assignment path to accept `role_template_id` and mission overlay payload; store overlay in `Job.meta_data`.

---

## Acceptance Criteria

- Workers always receive filtered `product_config` via MCP `discover_context` when `agent_name` is provided.
- Orchestrator continues to receive full `product_config`.
- Vision endpoints return chunked results and no longer raise parameter mismatch errors.
- No duplicate registrations or diverging implementations of context tools.
- Tests pass locally with `pytest tests` and coverage for context paths increases (target +5%).
- Token usage and context metadata visible in discovery results and optionally over WebSockets.
- Agent missions reference a role template (ID) and carry only overlay content; worker guardrails derive from the role template.

---

## Rollout Plan

1) Branch & PR
- Implement changes behind a short-lived feature branch; open PR with test results.

2) Database & Config
- No schema changes expected (JSONB exists). Optionally add config for TTL (env-driven).

3) Validation
- Run: `pytest tests -k vision_chunking or context` and `pytest tests --cov=giljo_mcp`.
- Manual check: upload a large vision doc and retrieve chunks via API.

4) Release
- Merge after review; update minimal docs and changelog.

---

## Risks & Mitigations

- Risk: Backward compatibility for callers of `discover_context`.
  - Mitigation: Parameters optional; default behavior unchanged.
- Risk: Vision index drift if TTL too aggressive.
  - Mitigation: Content-hash check + explicit `force_reindex`.
- Risk: Deduplication regressions.
  - Mitigation: Unit and integration tests; feature flag if needed.
- Risk: Subagent role catalog divergence between platforms.
  - Mitigation: Define a common role schema and a platform adapter layer; validate parity in tests.

---

## Open Questions

- Should we auto-detect `agent_name` from session/DB to reduce caller burden?
- Preferred TTL defaults for path/index caching in LAN/Local modes?
- Do we want summarization fallback for workers when token limits are exceeded (beyond filtering)?
- Role catalog versioning: do we need a `role_template_version` to coordinate updates across missions in flight?

---

## Quick Task List (Phase 2)

- Add `agent_name` to MCP `discover_context` and forward into discovery.
- Fix `document_name` param in vision endpoint calls.
- Deduplicate context tools and MCP registration.
- Add TTL control and reinforce reindex triggers.
- Expand tests (filters, endpoint, reindex).
- Update docs (usage + troubleshooting).

---

## Notes for Serena MCP Usage

- To inspect context flows:
  - `find_symbol("discover_context")` in `src/giljo_mcp/discovery.py:212`.
  - `find_symbol("get_vision")` and `find_symbol("get_vision_index")` in `src/giljo_mcp/tools/context.py`.
  - `search_for_pattern("source_name=|document_name=")` to locate the endpoint mismatch.
- Validate end-to-end with:
  - MCP tools: `discover_context(agent_role, agent_name)`, `get_vision_index()`, `get_vision(part=N)`.
  - API: `/api/v1/context`, `/api/v1/products/{id}/vision-chunks`.

---

## Platform Considerations

### OpenAI Agents SDK (Codex)
- Tool schemas: mirror MCP tool signatures in Agents SDK tool definitions to keep a single mental model (inputs, outputs, error surfaces).
- Streaming and events: instrument run/step events and attach our `tenant_key`, `project_id`, and `role_template_id` for observability; persist run IDs in DB for traceability.
- Memory and context: inject filtered `product_config`, selected vision chunk(s), and mission overlay as structured inputs; keep token budgets explicit per role.
- Safety and policy: enable code execution safeguards, redaction, and allowlist tool invocation; align with repository security rules (no secrets, restricted paths).
- Idempotency: use `ensure_agent` semantics when spawning; de-duplicate on `(project_id, role_template_id, mission_hash)`.
- Error handling: implement retries with exponential backoff and capture structured failure reasons for the orchestrator to re-plan.
- Cost/latency controls: per-role max tokens, tool-call ceilings, and abort thresholds; surface costs via metrics.

### Anthropic Claude Agent SDK
- Tooling: expose the same MCP tool surface via Claude Agent SDK actions; keep parameter parity and structured returns.
- Context delivery: inject filtered config and vision overlays; use summaries for workers when near token limits.
- Streaming callbacks: capture tool-use events and intermediate thoughts where available; stream to dashboard via WebSocket.
- Safety: apply policy constraints and redaction; prefer read-only by default for workers unless overlay explicitly grants write scopes.
- Concurrency: orchestrator manages parallel workers with bounded concurrency; handoffs use `Job.meta_data` to carry overlay context.
- Observability: persist run/session IDs, step logs, and outcomes; correlate with `AgentInteraction` and `Job` records.

### Cross‑Platform Abstraction
- Adapter layer: define a `SubagentRunner` interface with methods `spawn(role_template_id, overlay, context)`, `status(run_id)`, `cancel(run_id)`.
- Mapping: role template → platform-specific prompt/guardrails; overlay → task instructions and success criteria; context → filtered config + vision selection.
- Fallbacks: if a platform is unavailable, degrade to local MCP-only execution while preserving mission overlay and logs.
