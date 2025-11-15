# GiljoAI MCP – Execution Plan (DB / Code / UI / UX, No Tests)

This plan lists remaining and reference handovers related to **database, backend code, and UI/UX** (no pure test work), and maps each to the recommended execution environment using the **CCW vs CLI guide**.

Legend:

- `CLI`  = Local dev (full DB + runtime access).
- `CCW`  = Claude Code Web (pure code / parallelizable).
- `Both` = Design in CCW, wire/test in CLI.

---

## 1. Core Backend / DB / Architecture Handovers

```
+--------+-----------------------------------------------+---------+------------------------------+----------------------+
| ID     | Title                                         | Status  | Scope                        | Recommended Mode     |
+--------+-----------------------------------------------+---------+------------------------------+----------------------+
| 0083   | Slash command harmonization (MCP patterns)    | REF     | MCP tools + routes           | Both (design CCW,    |
|        |                                               | ONLY    |                              | wire/test CLI)       |
| 0095   | Project streamable HTTP MCP architecture      | REF     | Architecture & streaming     | REF (design only)    |
| 0100   | One-liner installation system                 | PLAN    | install.py, bootstrap flow   | CLI                  |
| 0117   | Agent role refactor (8-role system)           | REF     | Roles, auth, templates       | Both (design CCW,    |
|        |                                               | ONLY    |                              | implement CLI)       |
| 0120–  | Backend refactor series (services/endpoints)  | DONE    | Message queue, services, API | -                    |
| 0128   |                                               |         |                              |                      |
| 0130   | Frontend WebSocket modernization (V2)         | DONE    | WebSocket stack              | -                    |
+--------+-----------------------------------------------+---------+------------------------------+----------------------+
```

Notes:

- 0083 / 0095 / 0117 are **reference design docs** now; use them only if you reopen those feature areas.
- 0100 is the **only active backend/DB item** here: simplifying `install.py` around the new baseline schema → **CLI**.

---

## 2. UI / UX & Frontend Structure Handovers (0130 / 0135 / 0515)

These are the key remaining UI/UX structural items to wrap up.

```
+--------+-----------------------------------------------+---------+------------------------------+----------------------+
| ID     | Title                                         | Status  | Scope                        | Recommended Mode     |
|--------+-----------------------------------------------+---------+------------------------------+----------------------|
| 0130c  | Consolidate duplicate components              | PLAN    | Vue components, layout       | CCW                  |
| 0130d  | Centralize API calls                          | PLAN    | Frontend API client usage    | CCW                  |
| 0135   | Jobs dynamic link fix                         | PLAN    | Jobs tab links/navigation    | CCW                  |
| 0507   | API client URL fixes                          | DONE    | Frontend API base URLs       | -                    |
| 0508   | Vision upload error handling                  | DONE    | Upload flow UX/errors        | -                    |
| 0509   | Succession UI components                      | DONE    | Succession UI                | -                    |
| 0515   | Frontend consolidation (components + API)     | PLAN    | Merge 0130c/0130d, clean-up   | CCW                  |
+--------+-----------------------------------------------+---------+------------------------------+----------------------+
```

Execution guidance:

- Treat **0515** as the umbrella project that **absorbs 0130c and 0130d**:
  - 0515a: merge/clean duplicate components (0130c).
  - 0515b: centralize API calls (0130d, plus verifying 0507–0509 behavior).
- **0135** can be done either before or alongside 0515; it is a focused CCW UI task.

---

## 3. Context / UX / Orchestration Experience Handovers

These touch both backend logic and UX around context and jobs; they are **not pure tests**, but some were planned alongside testing.

```
+--------+-----------------------------------------------+---------+------------------------------+----------------------+
| ID     | Title                                         | Status  | Scope                        | Recommended Mode     |
|--------+-----------------------------------------------+---------+------------------------------+----------------------|
| 0112   | Context prioritization UX enhancements        | PLAN    | Context manager + UX hints   | Both (backend CLI,   |
|        |                                               |         |                              | UI in CCW)           |
| 0114   | Jobs tab UI harmonization                     | PLAN    | Jobs list UX, states         | CCW                  |
| 0130e  | Inter-agent messaging fix                     | DONE    | Messaging behavior           | -                    |
+--------+-----------------------------------------------+---------+------------------------------+----------------------+
```

Execution guidance:

- For **0112**: design the prioritization rules and UX in CCW (docs + wireflows), then implement the backend logic and verify behavior in **CLI**.
- For **0114**: pure UI/UX harmonization of the jobs tab → **CCW**.

---

## 4. 0500 Series – Backend / API / UI Remediation (Status & Reference)

Most of the 0500 remediation work is already implemented. These entries are here to help reconcile backend and frontend behavior, not to redo tests.

```
+--------+-----------------------------------------------+---------+------------------------------+----------------------+
| ID     | Title                                         | Status  | Scope                        | Recommended Mode     |
|--------+-----------------------------------------------+---------+------------------------------+----------------------|
| 0500   | ProductService enhancement                    | DONE    | Backend service (products)   | - (CLI only if       |
|        |                                               |         |                              | troubleshooting)     |
| 0501   | ProjectService implementation                 | DONE    | Backend service (projects)   | -                    |
| 0502   | OrchestrationService integration              | DONE    | Backend orchestration        | -                    |
| 0503   | Product endpoints                             | DONE    | FastAPI routes               | -                    |
| 0504   | Project endpoints                             | DONE    | FastAPI routes               | -                    |
| 0505   | Orchestrator succession endpoint              | DONE    | FastAPI route                | -                    |
| 0506   | Settings endpoints                            | DONE    | FastAPI routes               | -                    |
| 0507   | API client URL fixes                          | DONE    | Frontend API config          | -                    |
| 0508   | Vision upload error handling                  | DONE    | Frontend + backend UX        | -                    |
| 0509   | Succession UI components                      | DONE    | Frontend UX                  | -                    |
+--------+-----------------------------------------------+---------+------------------------------+----------------------+
```

Notes:

- If any regressions or missing behaviors appear in these areas, treat them as **small, targeted follow-up handovers**:
  - Backend or DB adjustments → **CLI**.
  - Frontend/UX tweaks → **CCW**.

---

## 5. 500-Series Reference Projects (Tests / Docs) – Marked as Reference Only

These are **not to be executed as “test projects” anymore** after the test purge, but they remain useful as design/reference material.

```
+--------+-----------------------------------------------+---------+---------------------------+----------------------+
| ID     | Title                                         | Status  | Scope                     | Recommended Mode     |
|--------+-----------------------------------------------+---------+---------------------------+----------------------|
| 0510   | Fix broken test suite                        | REF     | Old test infra plan       | REF ONLY (no action) |
|        |                                               | ONLY    |                           |                      |
| 0511   | E2E integration tests                         | REF     | Old E2E plan              | REF ONLY             |
| 0511a  | Smoke tests for critical workflows            | REF     | Smoke test spec           | REF ONLY             |
| 0512   | CLAUDE.md update & cleanup                    | PLAN    | Docs / instructions       | CCW                  |
| 0513   | Handover 0132 documentation                   | PLAN    | Docs for prompt features  | CCW (when 0132 done) |
| 0514   | Roadmap rewrites                              | PLAN    | Strategy / roadmap        | CCW                  |
| 0515   | Frontend consolidation                        | PLAN    | Components + API calls    | CCW                  |
+--------+-----------------------------------------------+---------+---------------------------+----------------------+
```

Execution guidance:

- **Do not** resurrect 0510/0511/0511a as “fix all tests” projects. Instead:
  - Add **small, focused tests** as you implement/adjust each feature.
  - Use these docs only as inspiration for which flows to cover (auth, projects, jobs, templates, downloads).
- **0512–0514** should be done **after** you’re satisfied with the DB/Code/UI state, to align docs and roadmaps with reality.

---

## 6. Recommended Execution Order (Non‑Test Work Only)

Suggested order to wrap up product‑facing work:

1. **0100 – One-liner installation system** (CLI)  
   - Align `install.py` with the new baseline schema and self-healing data rules.
2. **0135 – Jobs dynamic link fix** (CCW)  
   - Clean up Jobs tab navigation and links.
3. **0114 – Jobs tab UI harmonization** (CCW)  
   - Harmonize Jobs UI state/labels with backend job states.
4. **0112 – Context prioritization UX enhancements** (Both)  
   - Implement context prioritization rules + any UI affordances.
5. **0515 – Frontend consolidation** (CCW)  
   - Consolidate duplicate components and centralize API calls (absorbing 0130c/0130d).
6. **0512 / 0514 – Docs & roadmap updates** (CCW)  
   - Update CLAUDE.md and rewrite roadmaps to reflect the simplified DB/install and consolidated frontend.

All other 0120–0128 and 0500 remediation items are **already implemented**; use their `-C` / `-COMPLETE` handovers in `handovers/completed` and `handovers/completed/reference/500` as background when touching those areas again.



---
# INTEGRATION NOTE
**Date**: 2025-11-15
**Status**: MERGED INTO claude_order_projects.md

This execution plan has been merged into:
- **claude_order_projects.md** - The unified execution plan

Key insights integrated:
- 0100 needs quick polish (not fully complete)
- 0112, 0114, 0135 are optional v3.1 items (not obsolete)
- 0515 must include WebSocket V2 completion

See: /handovers/claude_order_projects.md
