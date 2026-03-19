# Handover Harmonization Map (0049–0087) + 0088 Preview

Author: Documentation Manager Agent
Date: 2025-11-02
Scope: handovers/completed (0049–0087), pending 0088

---

## Purpose

This document inventories completed handovers, records supersessions and retirements, and maps each to concrete documentation actions. It is designed for iterative harmonization: we will proceed from the lowest-numbered handover upward, applying focused updates to `/docs` after each pass.

Legend:
- Status: Completed | Superseded | Retired | Ready (unimplemented) | Pending (in-progress design)
- Action: Keep (document), Replace (document new source of truth), Archive (note history), Defer (blocked by pending work)

Key Cross-Cutting Themes:
- 0073 replaces earlier agent job/board approaches (0062/0066).
- 0086 establishes production-grade Stage Project; 0088 shifts it to thin-client prompts.
- 0074/0084b correct agent export/import flows.
- 0050/0050b codify single-active product/project constraints.

---

## Supersession Summary (High-Confidence)

- 0073 SUPERSEDES: 0062 (Project Launch Panel), 0066 (Agent Kanban Dashboard)
- 0064 RETIRED by architectural decision aligned to 0050 + 0050b + 0070–0073
- 0079 (Orchestrator Staging Prompt Generation) will be superseded by 0088 Thin Client
- 0086 (Stage Project production-grade) requires refactor alignment with 0088 Thin Client

---

## Mapping by Handover

0049 – Active Product Token Visualization & Field Priority Indicators (Completed)
- Interactions: ties directly to field priority UI/logic
- Docs impact: reinforce field priority behaviors
- Action: Keep; harmonize docs where priority flows are described

0050 – Single Active Product Architecture (Completed)
- Interactions: foundational constraint; informs UI states and job orchestration
- Docs impact: clarify single-active rules across UI and API
- Action: Keep; ensure constraint appears consistently in user and API guides

0050b – Single Active Project per Product (Completed)
- Interactions: tightens scoping; affects staging/launch flows
- Docs impact: reflect constraint in Launch/Jobs narratives
- Action: Keep; cross-link to 0050

0051 – Product Form Autosave UX (Ready)
- Interactions: quality-of-life; no known supersession
- Docs impact: note as planned behavior if UI implements
- Action: Defer (unimplemented)

0053 – ProjectsView v2.0 Redesign (Completed)
- Interactions: baseline for later visual updates (0073/0077)
- Docs impact: ensure screenshots/flows match V2 elements
- Action: Keep; verify visuals

0060 – Series Retirement Summary (Meta) → groups 0060/0061/0062
- Interactions: documents consolidation state pre‑0073
- Docs impact: historical note only
- Action: Archive; do not surface prominently

0060 – MCP Agent Coordination Tool Exposure (Completed)
- Interactions: surfaces tools, relates to 0073 grid
- Docs impact: API/events references
- Action: Keep; ensure consistent with 0073

0061 – Orchestrator Launch UI Workflow (Completed)
- Interactions: UI baseline, later refined by 0073/0077
- Docs impact: align UI flows with current grid/tab patterns
- Action: Keep; note refinements under 0073

0062 – Project Launch Panel & Database Foundation (Completed → Partially Superseded by 0073)
- Interactions: early job foundation, superseded in UI + orchestration patterns
- Docs impact: move details to historical appendix; front docs reflect 0073
- Action: Replace; archive specifics

0063 – Per‑Agent Tool Selection UI (Superseded by 0073)
- Action: Archive; reference under 0073 ADR

0064 – Project‑Product Association UI (Retired)
- Reason: conflicts with Single Active architecture
- Action: Archive; ensure docs discourage explicit selector

0065 – Token Estimation + Mission Launch Summary (Mixed)
- State: some UI variants superseded
- Docs impact: avoid deprecated summary UI
- Action: Keep core; Archive superseded components

0066 – Agent Kanban Dashboard (Superseded by 0073)
- Action: Archive; ensure grid model is canonical

0069 – Native MCP Config for Codex & Gemini CLI (Completed)
- Docs impact: update CLI integration references
- Action: Keep

0070 – Project Soft Delete with Recovery UI (Completed)
- Docs impact: user guide + API reference
- Action: Keep

0071 – Simplified Project State Management (Completed)
- Docs impact: reflect reduced state space, update flows
- Action: Keep

0072 – Task Management Integration Map (Completed)
- Docs impact: architecture/reference; ensure it aligns with 0076 scoping
- Action: Keep

0073 – Static Agent Grid with Enhanced Messaging (Completed; Canonical)
- Supersedes: 0062, 0066; updates event flows, UI, testing
- Docs impact: becomes source of truth for orchestration UI
- Action: Keep as canonical; add ADR link

0074 – Agent Export Auto‑Spawn Removal (Completed)
- Docs impact: update agent export instructions; remove auto‑spawn language
- Action: Replace doc references

0075 – Eight‑Agent Active Limit Enforcement (Retired/Consolidated)
- Docs impact: mention limit in 0073 grid as constraint if still enforced
- Action: Archive; capture constraint where applicable

0076 – Task Field Cleanup and Product Scoping (Completed)
- Docs impact: data model and scoping rules
- Action: Keep; reflect in technical references

0077 – Launch/Jobs Dual‑Tab Interface (Completed/Retired)
- Interactions: interim UI; 0073 is canonical design
- Action: Archive; note lessons learned

0078 – Task Tenant & JWT Mismatch Diagnosis (Completed/Retired)
- Docs impact: troubleshooting appendix
- Action: Archive

0079 – Master Orchestrator Staging Prompt Generation (Completed → To be superseded by 0088)
- Docs impact: mark as legacy fat‑prompt approach
- Action: Replace after 0088 lands; keep historical note

0080 – Orchestrator Succession Architecture (Completed)
- Docs impact: orchestration lifecycle
- Action: Keep; integrate into orchestration docs

0080a – Orchestrator Succession Slash Command (Completed)
- Docs impact: slash command references
- Action: Keep

0081 – Hybrid Launch Route Architecture (Completed)
- Docs impact: API route design
- Action: Keep

0084b – Agent Import Slash Commands (Completed; fixes 0084)
- Docs impact: CLI/slash command guidance
- Action: Replace older 0084 references with 0084b

0085 – Serena MCP – Advanced Settings UI & Backend Config (Completed)
- Docs impact: settings UX + config reference
- Action: Keep

0086A/B – Production‑Grade Stage Project (+ WebSocket Visualization) (Completed)
- Docs impact: Stage Project feature page and test suite
- Action: Keep now; flag pending 0088 alignment work

0087 – Token Estimation Active Product Link (Completed/Retired)
- Docs impact: minor; ensure link behavior reflected where relevant
- Action: Archive note

0088 – Thin Client Stage Project Architecture Fix (Completed)
- Supersedes: legacy fat‑prompt pattern (affects 0079 and any fat‑prompt text)
- Introduces: MCP tools `get_orchestrator_instructions`, `get_agent_mission`; `ThinClientPromptGenerator`
- Docs impact: Stage Project flow, API schema, events, migration guide
- Action: Integrated; docs updated, legacy fat‑prompt marked
- Location: handovers/completed/harmonized/0088_thin_client_stage_project_fix-C.md

---

## Docs Impact Matrix (where to change)

- docs/STAGE_PROJECT_FEATURE.md
  - Add Thin Client architecture overview (post‑0088), keep 0086 content as baseline until migrated
  - Token estimation and field priorities remain central (0049/0065/0076)

- docs/guides/thin_client_migration_guide.md
  - Canonical migration steps for 0088 (already present); link from Stage Project feature

- docs/AGENT_JOBS_API_REFERENCE.md, docs/developer_guides/websocket_events_guide.md
  - Align events and job flows to 0073 grid model; de‑emphasize 0062/0066 patterns

- docs/AGENT_TEMPLATES_REFERENCE.md
  - Reflect 0074 (no auto‑spawn) and 0084b (import slash commands)

- docs/CONTEXT_API_GUIDE.md
  - Ensure context field priority references match current behavior

- docs/index.md and docs/README_FIRST.md
  - Update narrative to reference 0073 as canonical UI and 0088 migration path

---

## Iterative Harmonization Plan

We will proceed lowest‑number first. For each handover:
1) Verify scope/state (Completed/Superseded/Retired/Ready)
2) Update or archive relevant sections in `/docs`
3) Add cross‑references (ADR/supersession notes)
4) Validate links and impacted guides

Batch 1 (0049 → 0053)
- 0049: Add priority notes to user + API guides
- 0050/0050b: Document single‑active constraints consistently
- 0051: Defer (unimplemented)
- 0053: Verify ProjectsView V2 is the current baseline (pre‑0073 visuals)

Batch 2 (0060 → 0066)
- Move 0062/0066 details to historical appendix; assert 0073 as canonical
- Keep 0061/0060 context where still accurate
- 0064: add “Retired by Design” notice in any conflicting UI doc

Batch 3 (0069 → 0074)
- 0069: update CLI/MCP configuration references
- 0070/0071/0072: reinforce data model + flows
- 0073: elevate as canonical orchestration UI
- 0074: remove auto‑export text; update export steps

Batch 4 (0075 → 0081)
- 0075: consolidate limit note; archive spec
- 0076: reflect task field cleanup & scoping
- 0077: archive as interim UI
- 0078: troubleshooting appendix
- 0079: mark fat‑prompt as legacy; 0080/0080a/0081 keep

Batch 5 (0084b → 0087) + 0088 preview
- 0084b: finalize slash command docs
- 0085: settings + config references
- 0086A/B: confirm Stage Project feature page is aligned (pre‑0088)
- 0087: finalize link behavior notes
- 0088: prepare thin‑client edits; execute after implementation

---

## Immediate Next Step (requesting approval)

Start with 0049 harmonization:
- Update `docs/README_FIRST.md` and `docs/CONTEXT_API_GUIDE.md` to explicitly tie Active Product Token Visualization and field priorities to token estimates and UI elements; ensure examples match current behavior.
- Outcome: clearer token flow narrative, consistent terminology, cross‑links to Stage Project.

Once approved, we will patch these docs, then move to 0050/0050b.
