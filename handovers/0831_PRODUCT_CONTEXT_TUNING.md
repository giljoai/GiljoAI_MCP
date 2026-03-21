# Handover 0831: Product Context Tuning — On-Demand Scope Drift Detection

**Date:** 2026-03-21
**Edition Scope:** CE (SaaS inherits)
**From Agent:** Claude Opus 4.6 (design session with product owner)
**To Agent:** Next implementing session
**Priority:** Medium
**Estimated Complexity:** 3-4 days
**Status:** Not Started

---

## Task Summary

As a product evolves through successive projects, user-inserted product context (description, tech stack, architecture, features, quality standards, vision documents) drifts from what was actually built. This handover adds an **on-demand Product Context Tuning** feature that lets the user select which context sections to review, assembles a comparison prompt using existing fetch tools, sends it to their subscribed CLI tool for analysis, and receives structured proposals back via a new MCP tool. A passive notification reminds the user to tune after a configurable number of completed projects.

**Why it matters:** Stale product context means agents receive inaccurate instructions. An architecture field that still says "monolith" when the team migrated to microservices three projects ago causes every new agent to plan incorrectly. This feature keeps the product's self-description honest.

**Design philosophy:** This is developer self-service, not automation. The user decides when to tune, which sections to check, and what to do with the results. GiljoAI assembles context and generates the comparison prompt — the user's CLI tool does the reasoning. This is consistent with GiljoAI's passive orchestrator model.

---

## Context and Background

### What Exists Today

1. **Product context** — User-curated fields on the Product model:
   - `description` (Text) — free-form product description
   - `config_data` (JSONB) — architecture, tech_stack, features.core, codebase_structure, test_config, database_type, backend/frontend frameworks, deployment_modes
   - `quality_standards` (Text) — testing expectations
   - `target_platforms` (ARRAY) — OS targets
   - Vision documents (VisionDocument model) — uploaded .md/.txt files with SUMI summaries

2. **360 Memory** — `ProductMemoryEntry` table with per-project records:
   - `summary`, `key_outcomes`, `decisions_made`, `deliverables`, `tags`
   - `git_commits` (if git integration enabled)
   - Read via `get_360_memory()`, written via `write_360_memory()`

3. **Git integration** — `product_memory["git_integration"]` stores enabled/commit_limit/default_branch. Git commits captured in 360 memory entries at closeout.

4. **fetch_context** — Single MCP tool dispatching to 10 category tools. Already reads all context sources needed for comparison.

5. **User context settings** — Toggle Configuration (what to fetch: Product Description, Tech Stack, Architecture, Testing) and Depth Configuration (Vision Documents depth, 360 Memory lookback count, Git History commit count, Agent Templates depth). Located in My Settings → CONTEXT tab.

6. **Notification bell** — Top-right header, existing notification infrastructure with WebSocket events.

7. **Product views** — Product card (list view with stats), Product Details panel (read-only info view via ⓘ icon), Edit Product dialog (tabbed editor: Basic Info, Vision Docs, Tech Stack, Architecture, Testing).

8. **Existing MCP tools (23):** create_project, update_project_mission, update_agent_mission, get_orchestrator_instructions, send_message, receive_messages, list_messages, create_task, health_check, generate_download_token, get_pending_jobs, report_progress, complete_job, reactivate_job, dismiss_reactivation, report_error, get_agent_mission, spawn_agent_job, get_agent_result, get_workflow_status, fetch_context, close_project_and_update_memory, write_360_memory.

### What Does NOT Exist

- No mechanism to compare product context against 360 memory / git for drift
- No on-demand tuning prompt generation
- No MCP tool for agents to submit tuning proposals back
- No UI for reviewing and accepting/dismissing proposed context changes
- No staleness notification

---

## Design

### Core Principle: On-Demand, User-Initiated

The tuning feature is **not automatic.** It does not trigger after closeout, it does not run on a schedule. The user decides when to tune and which sections to check. GiljoAI provides two things: (1) a tool to make tuning easy, and (2) a gentle reminder when it's been a while.

Rationale:
- **Developer responsibility** — The developer knows their product. They know when they pivoted intentionally vs. drifted accidentally. Automatic drift detection cannot distinguish between the two.
- **Token cost transparency** — Each tuning run costs tokens on the user's CLI tool. The user should choose when to spend them, not be surprised by background consumption.
- **Passive orchestrator compliance** — GiljoAI assembles context and generates prompts. The user's CLI tool does the reasoning. On-demand initiation means the CLI tool is always actively connected when the analysis runs.

### Selectable Section Menu

The user does not have to tune everything at once. The tuning UI presents selectable sections that mirror the Edit Product tabs and respect the user's context toggle settings (My Settings → CONTEXT). Only sections the user has toggled ON in their context settings are eligible for tuning — if Architecture is toggled off, it doesn't appear in the tuning menu.

**Tuning targets (when toggled on):**

| Section | Maps to Product Field | Evidence Sources |
|---------|----------------------|------------------|
| Product Description | `description` | 360 memory summaries, key_outcomes |
| Tech Stack | `config_data.tech_stack` | 360 memory deliverables, decisions_made, git commits |
| Architecture | `config_data.architecture` | 360 memory decisions_made |
| Core Features | `config_data.features.core` | 360 memory key_outcomes, deliverables |
| Codebase Structure | `config_data.codebase_structure` | 360 memory deliverables (file paths) |
| Database | `config_data.database_type` | 360 memory decisions_made |
| Backend Framework | `config_data.backend_framework` | 360 memory deliverables, decisions_made |
| Frontend Framework | `config_data.frontend_framework` | 360 memory deliverables, decisions_made |
| Quality Standards | `quality_standards` | 360 memory metrics, decisions_made |
| Target Platforms | `target_platforms` | 360 memory decisions_made, deliverables |
| Vision Documents | VisionDocument entries | 360 memory summaries vs. vision content |

The user can select individual sections, multiple sections, or "Select All" for a full sweep.

### Depth Settings: Reuse Existing Configuration

The tuning comparison prompt respects the user's existing depth settings from My Settings → CONTEXT:
- **360 Memory lookback** — uses the configured project count (e.g., "3 projects")
- **Git History depth** — uses the configured commit count (e.g., "5 commits")
- **Vision Documents depth** — uses the configured level (Light/Medium/Full)

No separate "tuning lookback" setting is needed. The user's existing depth preferences already express how much history they consider relevant.

### Execution Flow

```
1. User clicks "Tune Context" on the Product Details panel
2. Selectable section menu appears (filtered by context toggle settings)
3. User picks sections → clicks "Generate Tuning Prompt"
4. Backend assembles comparison payload:
   - Current product context for selected sections (via ProductService)
   - Recent 360 memory entries at configured depth (via ProductMemoryRepository)
   - Git commit data at configured depth if git integration enabled
   - Structured comparison instructions with required output format
5. Prompt is displayed for user to copy to their CLI tool
   (same pattern as existing orchestrator prompt copy)
6. User pastes prompt in their CLI tool (Claude Code / Codex / Gemini)
7. CLI tool analyzes the comparison and calls submit_tuning_review MCP tool
8. GiljoAI receives structured proposals, stores them on the Product
9. WebSocket event fires → UI shows diff/review view
10. User reviews each proposal: Accept / Edit / Dismiss
11. Accepted changes save through existing ProductService update methods
```

### New MCP Tool: `submit_tuning_review` (Tool #24)

The agent calls this tool after completing the comparison analysis. This follows the established pattern where agents write results back to GiljoAI (same as `write_360_memory`, `complete_job`, `report_progress`).

**Tool definition:**
```
Tool: submit_tuning_review
Description: Submit product context tuning proposals after comparing
             current product context against recent project history.

Parameters:
  product_id: string (required) — Target product ID
  proposals: array (required) — Per-section proposals:
    - section: string — Context section key (e.g., "tech_stack", "architecture")
    - drift_detected: boolean — Whether drift was found
    - current_summary: string — Brief description of current value
    - evidence: string — What 360 memory / git shows
    - proposed_value: string — Suggested replacement text
    - confidence: string — "high" | "medium" | "low"
    - reasoning: string — Why the change is recommended
  overall_summary: string (optional) — High-level drift assessment

Returns:
  success: boolean
  review_id: string — Reference for the stored review
  message: string
```

**Alternative considered:** Extending `write_360_memory` with an `entry_type: "tuning_review"` to avoid adding tool #24. Rejected because 360 memory is persistent institutional knowledge while tuning proposals are ephemeral suggestions. Mixing them pollutes the memory data model and forces backend branching on entry_type for fundamentally different storage paths. A dedicated tool is cleaner.

### Tuning Prompt Template

The prompt assembled by the backend must be prescriptive about the expected MCP tool call. The agent needs explicit instructions to call `submit_tuning_review` with the correct payload structure.

```
You are reviewing a product's context for accuracy after recent development work.

## Your Task
Compare the CURRENT PRODUCT CONTEXT against RECENT PROJECT HISTORY below.
For each section, determine if the current description is still accurate.

## Current Product Context
{serialized selected sections only}

## Recent Project History (360 Memory — last N projects)
{serialized 360 memory entries: summary, key_outcomes, decisions_made, deliverables}

## Git Activity (if available)
{recent commit summaries from 360 memory git_commits fields}

## Instructions
1. For each section, compare what the product context claims against
   what actually happened in recent projects.
2. Flag sections where the context is stale, incomplete, or contradicted
   by project outcomes.
3. Distinguish between intentional product evolution (update the context)
   and temporary project-specific details (don't update).
4. When proposing changes, write the COMPLETE replacement value for
   the section, not a diff or partial edit.

## Required Action
When your analysis is complete, call the submit_tuning_review MCP tool with
your findings. Use this exact structure:

- product_id: "{product_id}"
- proposals: array with one entry per section analyzed
  - section: the section key (tech_stack, architecture, description, etc.)
  - drift_detected: true/false
  - current_summary: brief note on what the current context says
  - evidence: what the project history/git shows that differs
  - proposed_value: the full replacement text (or current text if no drift)
  - confidence: "high" / "medium" / "low"
  - reasoning: one-sentence explanation
- overall_summary: one-paragraph summary of the product's context health

Do NOT output the analysis as text. Call the MCP tool with structured results.
```

### Notification: Blue Bell After N Completed Projects

A passive reminder surfaces in the notification bell when the user hasn't tuned in a while. This is informational, not blocking.

**Trigger logic (backend, no LLM required):**
- Track `last_tuned_at_sequence` on the Product (the 360 memory sequence number at last tune)
- Count completed project closeouts since that sequence number
- When count reaches the configured threshold → create a notification

**Notification appearance:**
- Blue indicator on the bell icon (new color — red = error, amber = warning, blue = informational)
- Notification text: "N projects completed since your last context review. Tune your product context?"
- Links directly to the Product Details panel with the tuning menu

**Configuration (My Settings → NOTIFICATIONS tab):**
- `context_tuning_reminder`: toggle on/off (default: on)
- `tuning_reminder_threshold`: number of completed projects (default: 10, minimum: 3, no maximum)

**Dismissal behavior:** Clicking the notification and running a tune (even on one section) resets the counter. Dismissing the notification without tuning does NOT resurface it — the counter continues from where it is, and the next notification fires at the next threshold crossing (e.g., at 6 if threshold is 3 and user dismissed at 3).

### Data Model

**Modify Product model — add `tuning_state` JSONB field:**
```python
{
    "last_tuned_at": "2026-03-21T14:30:00Z",
    "last_tuned_at_sequence": 15,  # 360 memory sequence at last tune
    "pending_proposals": null | {   # populated by submit_tuning_review
        "review_id": "uuid",
        "submitted_at": "2026-03-21T14:35:00Z",
        "overall_summary": "...",
        "proposals": [
            {
                "section": "tech_stack",
                "drift_detected": true,
                "current_summary": "...",
                "evidence": "...",
                "proposed_value": "...",
                "confidence": "high",
                "reasoning": "..."
            }
        ]
    }
}
```

Pending proposals are cleared when the user completes review (all sections accepted/dismissed). This is Option A (lightweight, on the Product model). A separate table for review history can be added later if analytics are needed.

### UI Placement

**Primary entry point — Product Details panel (ⓘ info view):**
A "Tune Context" button near the top of the panel, below the product name and statistics. This is where users go to review their product's current state — natural place to question accuracy.

**Review/diff view — extends Edit Product dialog:**
When pending proposals exist, the Edit Product tabs show a comparison overlay: current value alongside proposed value with accept/edit/dismiss controls per section. Accepted changes save through existing ProductService methods.

**Secondary entry points:**
- My Settings → CONTEXT tab: "Review context accuracy" link that navigates to the Product Details tuning flow. Serves as a contextual shortcut since the user is already thinking about context configuration.
- Notification bell: blue notification links directly to Product Details with tuning menu.
- Future: MCP tool `tune_product_context` with optional `section` parameter for terminal-only users (out of scope for this handover, note for future).

---

## Implementation Plan

### Phase 1: Backend — Prompt Assembly & MCP Tool

**New file:** `src/giljo_mcp/services/product_tuning_service.py`
- `ProductTuningService` class
- `assemble_tuning_prompt(product_id, tenant_key, sections: list[str])` — gathers current context for selected sections + 360 memory at configured depth + git history if enabled. Returns formatted prompt string.
- `store_proposals(product_id, tenant_key, proposals: dict)` — writes to `Product.tuning_state.pending_proposals`. Emits `product:tuning:proposals_ready` WebSocket event.
- `apply_proposal(product_id, tenant_key, section, value)` — updates the relevant product field via existing ProductService.
- `dismiss_proposal(product_id, tenant_key, section)` — removes proposal from pending list.
- `clear_review(product_id, tenant_key)` — clears all pending proposals, updates `last_tuned_at` and `last_tuned_at_sequence`.
- Uses existing `ProductMemoryRepository.get_entries_by_product()` for 360 memory.
- Uses existing `ProductService.get_product()` for current context.
- Reads user's context toggle settings and depth configuration to filter sections and set lookback.

**New MCP tool registration:** `submit_tuning_review`
- Register in MCP tool handler (same pattern as other tools)
- Validates product_id exists and belongs to tenant
- Calls `ProductTuningService.store_proposals()`
- Returns success with review_id

**Modify:** `src/giljo_mcp/models/products.py`
- Add `tuning_state` JSONB column to Product model (nullable, default null)

**Migration:** Alembic migration adding `tuning_state` column to products table.

### Phase 2: Notification System

**New file:** `src/giljo_mcp/services/tuning_notification_service.py`
- `check_tuning_staleness(product_id, tenant_key)` — compares current 360 memory sequence count against `tuning_state.last_tuned_at_sequence`. Returns whether threshold is exceeded.
- Called after `write_360_memory` completes (lightweight check — count comparison, no LLM).
- If threshold exceeded and no existing unread tuning notification → create notification with blue severity.

**Modify:** `src/giljo_mcp/tools/write_360_memory.py`
- After successful memory write, call `TuningNotificationService.check_tuning_staleness()`.
- This is a cheap integer comparison, not an analysis. No token cost.

**Modify:** Notification model/service to support blue severity level alongside existing red/amber.

**Modify:** User settings to include `context_tuning_reminder` (boolean) and `tuning_reminder_threshold` (integer, min 3, default 10).

### Phase 3: API Endpoints

**New endpoints on existing `api/product_routes.py`:**

`POST /api/products/{product_id}/tuning/generate-prompt`
- Body: `{ "sections": ["tech_stack", "architecture", ...] }`
- Returns: `{ "prompt": "...", "sections_included": [...], "lookback_depth": 3, "git_enabled": true }`
- Auth: `get_current_active_user`, tenant-filtered

`GET /api/products/{product_id}/tuning/proposals`
- Returns current pending proposals from `tuning_state` (or empty if none)
- Auth: tenant-filtered

`POST /api/products/{product_id}/tuning/proposals/{section}/apply`
- Body: `{ "action": "accept" | "edit" | "dismiss", "value": "..." }`
- For "accept": applies `proposed_value` to product field
- For "edit": applies user-provided `value` to product field
- For "dismiss": removes proposal from pending list
- Auth: tenant-filtered

`POST /api/products/{product_id}/tuning/proposals/dismiss-all`
- Clears all pending proposals, updates `last_tuned_at`
- Auth: tenant-filtered

### Phase 4: Frontend — Tuning UI

**New component:** `frontend/src/components/products/ProductTuningMenu.vue`
- Appears in Product Details panel (ⓘ view)
- Checkbox list of eligible sections (filtered by user's context toggle settings)
- "Select All" option
- "Generate Tuning Prompt" button → calls generate-prompt endpoint → shows prompt in copyable text area (same UX pattern as existing orchestrator prompt copy)

**New component:** `frontend/src/components/products/ProductTuningReview.vue`
- Appears in Edit Product dialog when `tuning_state.pending_proposals` is non-null
- Per-section expandable rows showing: current value | evidence | proposed change
- Accept / Edit / Dismiss buttons per section
- "Dismiss All" button
- Listens for `product:tuning:proposals_ready` WebSocket event to auto-appear

**Modify:** Product Details panel — add "Tune Context" button
**Modify:** Edit Product dialog — integrate tuning review overlay when proposals exist
**Modify:** Notification bell component — support blue severity indicator
**Modify:** My Settings → NOTIFICATIONS — add tuning reminder toggle and threshold slider
**Modify:** My Settings → CONTEXT — add "Review context accuracy" shortcut link

---

## Key Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/services/product_tuning_service.py` | **NEW** — prompt assembly, proposal storage, apply/dismiss |
| `src/giljo_mcp/services/tuning_notification_service.py` | **NEW** — staleness check (project count comparison) |
| `src/giljo_mcp/models/products.py` | Add `tuning_state` JSONB column |
| `src/giljo_mcp/tools/write_360_memory.py` | Add post-write staleness check call |
| `api/product_routes.py` | Add tuning endpoints (generate-prompt, proposals, apply, dismiss) |
| `frontend/src/components/products/ProductTuningMenu.vue` | **NEW** — section selection + prompt generation UI |
| `frontend/src/components/products/ProductTuningReview.vue` | **NEW** — proposal diff/review UI |
| `frontend/src/components/products/ProductDetails.vue` | Add "Tune Context" button |
| `frontend/src/components/products/EditProduct.vue` | Integrate tuning review overlay |
| `frontend/src/components/notifications/NotificationBell.vue` | Support blue severity |
| `frontend/src/views/settings/NotificationsSettings.vue` | Add tuning reminder controls |
| `frontend/src/views/settings/ContextSettings.vue` | Add "Review context accuracy" link |
| `src/giljo_mcp/config/defaults.py` | Add tuning defaults |
| MCP tool registration file | Register `submit_tuning_review` tool |
| `install.py` / Alembic migration | Migration for `tuning_state` column |

---

## Testing Requirements

- **Unit tests:** Prompt assembly with various section selections and depth configs
- **Unit tests:** Staleness check with known sequence numbers and thresholds
- **Unit tests:** Proposal storage, retrieval, apply, dismiss operations
- **Integration tests:** Full flow — generate prompt → (simulate) submit_tuning_review → proposals appear → accept/dismiss
- **MCP tool tests:** `submit_tuning_review` with valid/invalid payloads, tenant isolation
- **API tests:** All tuning endpoints with auth, tenant filtering, edge cases
- **Frontend tests:** Tuning menu renders only toggled-on sections, review card accept/dismiss/edit, WebSocket event handling
- **Edge cases:** No 360 memory entries yet (graceful — "not enough project history for comparison"), git disabled (prompt omits git section), all sections match (proposals with `drift_detected: false`), user has all context toggles off (tuning menu shows empty state with guidance)

---

## Dependencies and Blockers

- **No blockers** — all required infrastructure exists (360 memory, fetch_context, WebSocket events, ProductService, notification system, MCP tool registration pattern)
- **Prerequisite knowledge:** Implementing agent should review existing MCP tool registration pattern (any existing tool file) and the write_360_memory flow for the post-write hook pattern

---

## Success Criteria

1. User can click "Tune Context" on Product Details and select specific sections to review
2. Generated prompt correctly includes only selected sections with current context and 360 memory at configured depth
3. Prompt instructs the agent to call `submit_tuning_review` with the correct payload structure
4. `submit_tuning_review` MCP tool correctly stores proposals and fires WebSocket event
5. UI displays proposals with current vs. proposed comparison when proposals exist
6. User can accept, edit, or dismiss each proposal independently
7. Accepted changes persist to product context immediately via existing ProductService
8. Blue notification appears in bell after configured number of completed projects (default: 10)
9. Notification links to Product Details tuning flow
10. Tuning reminder is configurable (on/off, threshold with minimum 3) in user settings
11. Only sections toggled ON in user's context settings appear in tuning menu
12. Depth settings from user's context config are respected (360 memory lookback, git commit count)
13. Feature degrades gracefully: no 360 memory = "not enough history" message, git off = git section omitted
14. All tests pass, tenant isolation maintained

---

## Rollback Plan

- `tuning_state` JSONB column is additive (no existing data modified)
- New MCP tool is additive (tool #24, no existing tools changed)
- Frontend components only render when explicitly invoked or when proposals exist
- Notification check is a lightweight integer comparison in the write_360_memory post-hook — removing it has zero impact
- Clean removal: delete service files, endpoints, components, MCP tool registration, and column migration

---

## Future Enhancements (Out of Scope)

- **MCP tool: `tune_product_context`** — Allow terminal-only users to initiate tuning from their CLI tool without opening the dashboard. Would call GiljoAI to get the comparison prompt, then self-execute analysis and submit results.
- **Local LLM integration (Ollama / vLLM)** — For users running a local model, route the tuning analysis through it instead of the CLI tool. Eliminates prompt copying, runs silently in the background, zero token cost. Recommended model: Phi-class (small, efficient for structured comparison tasks). In SaaS edition, this role would be filled by a platform-provided model (e.g., Haiku) included in subscription.
- **Review history analytics** — Separate `product_tuning_reviews` table tracking accept/dismiss patterns over time. Useful for understanding which context sections drift most.
- **Product card staleness indicator** — Subtle visual on the product card (e.g., the "Completed" counter shifts to blue) when the tuning threshold is exceeded, providing passive visibility before the bell notification.
- **Vision document re-upload suggestion** — When tuning detects the vision document is significantly out of sync with product reality, suggest the user upload an updated version rather than just editing context fields.

---

## Open Questions for Implementing Agent

1. **Prompt copy UX** — The existing orchestrator prompt copy pattern should be reused. Verify the current component name and location so the tuning prompt display is consistent.
2. **Notification model** — Verify whether the existing notification system supports a "blue" severity or if a new severity level needs to be added. Check current severity enum values.
3. **WebSocket event naming** — Proposed: `product:tuning:proposals_ready`. Verify this follows the existing event naming convention in the WebSocket handler.
4. **Context toggle field mapping** — **DECIDED:** Sub-fields (Core Features, Codebase Structure, Database, Backend/Frontend Framework) follow their parent toggle for v1. If Architecture is toggled off, all architecture sub-fields are excluded from the tuning menu. Independent sub-field toggles are not needed — add only if users request it post-launch.

---

## Implementation Summary

**Status:** Completed
**Date:** 2026-03-21
**Implementing Agent:** Claude Opus 4.6

### What Was Built

- **Data model:** `tuning_state` JSONB on Product, `notification_preferences` JSONB on User
- **Migration:** `i9j0k1l2m345_0831_product_context_tuning.py` (additive, safe for fresh + upgrade)
- **Backend service:** `ProductTuningService` (prompt assembly, proposal storage, apply/dismiss/clear, staleness check)
- **MCP tool #24:** `submit_tuning_review` (schema + allowlist + tool_map + accessor + implementation)
- **API endpoints:** 5 new endpoints under `/api/v1/products/{id}/tuning/` (sections, generate-prompt, proposals, apply, dismiss-all)
- **User settings:** notification-preferences GET/PUT endpoints on `/me/settings/`
- **Notification hook:** Post-write staleness check in `write_360_memory` (integer comparison, no LLM)
- **Frontend:** `ProductTuningMenu.vue` (section selection + prompt generation), `ProductTuningReview.vue` (proposal diff/review)
- **UI integrations:** ProductDetailsDialog (Tune Context button), NotificationDropdown (context_tuning type), notifications store (info badge), websocketEventRouter (proposals_ready event)
- **Tests:** 39 unit tests across 9 test classes covering all service methods, section mappings, tenant isolation, and edge cases
- **Defaults:** `DEFAULT_NOTIFICATION_PREFERENCES`, `TUNING_SECTION_TOGGLE_MAP` in config/defaults.py

### Key Files

| File | Change |
|------|--------|
| `src/giljo_mcp/services/product_tuning_service.py` | NEW (338 lines) |
| `src/giljo_mcp/tools/submit_tuning_review.py` | NEW (103 lines) |
| `api/endpoints/products/tuning.py` | NEW (203 lines) |
| `frontend/src/components/products/ProductTuningMenu.vue` | NEW (307 lines) |
| `frontend/src/components/products/ProductTuningReview.vue` | NEW (431 lines) |
| `tests/services/test_product_tuning_service.py` | NEW (1302 lines) |
| `migrations/versions/i9j0k1l2m345_0831_product_context_tuning.py` | NEW |
| `src/giljo_mcp/models/products.py` | Added tuning_state column |
| `src/giljo_mcp/models/auth.py` | Added notification_preferences column |
| `src/giljo_mcp/config/defaults.py` | Added notification + section toggle defaults |
| `api/endpoints/mcp_http.py` | Registered submit_tuning_review tool |
| `src/giljo_mcp/tools/tool_accessor.py` | Added submit_tuning_review proxy |
| `src/giljo_mcp/tools/write_360_memory.py` | Added staleness check hook |
| `api/endpoints/users.py` | Added notification preferences endpoints |

### Open Questions Resolved

1. **Prompt copy UX:** Reused `v-textarea` readonly + copy button pattern (same as existing prompt displays)
2. **Notification model:** No "blue" severity exists. Used `info` type with `context_tuning` notification type instead. Does not escalate badge color above info.
3. **WebSocket event naming:** `product:tuning:proposals_ready` follows existing `domain:sub:action` convention
4. **Context toggle mapping:** Sub-fields follow parent toggle as decided. TUNING_SECTION_TOGGLE_MAP maps each section to its parent toggle.

### Installation Impact

Migration runs automatically via `install.py run_database_migrations()`. Additive only (new nullable columns). Safe for both fresh installs and upgrades. No config.yaml changes needed.
