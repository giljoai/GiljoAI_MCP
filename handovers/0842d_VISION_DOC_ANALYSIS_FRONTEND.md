# Handover 0842d: Vision Document Analysis — Frontend UI

**Date:** 2026-03-27
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** ux-designer + frontend-tester
**Priority:** High
**Estimated Complexity:** 2 hours
**Status:** Not Started
**Series:** 0842a-e (Vision Document Analysis Feature)
**Spec:** `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md`
**Reference images:** `handovers/Reference_docs/FLow_vision_doc1.png`, `FLow_vision_doc2.png`, `FLow_vision_doc3.png`
**Depends on:** 0842a, 0842c

---

## Task Summary

Two frontend workstreams:

1. **Vision analysis UI**: Analysis prompt banner, "Stage Analysis" button, WebSocket notification on completion, custom instructions textarea.
2. **Tuning icon on product card**: Lift the buried "Tune Context" action to the product card action bar — always visible, notification dot when system recommends action.

---

## Context and Background

After a user uploads a vision document, Sumy runs immediately (existing behavior). The new feature adds a prompt: "Want AI to analyze this document and populate your product config?" with two options:

1. **YES, ANALYZE** — Stages a prompt for the user's connected CLI tool. The prompt text is something like: `"Analyze the vision document for product {name} and populate its configuration."` User copies this to their CLI, the agent calls the MCP tools (0842c), and a WebSocket notification confirms completion.
2. **NO THANKS** — Dismisses the banner. User fills fields manually. Sumy summaries are still available.

See `FLow_vision_doc3.png` for the exact UI wireframe.

---

## Technical Details

### UI Components (from wireframe FLow_vision_doc3.png)

**After upload — Vision Docs tab shows:**

```
┌─ product_vision_v2.md ──────────────────── × Remove ─┐
│  18,450 tokens · Uploaded just now                    │
│  Sumy summaries: ✅ 33% (6,089 tokens) · ✅ 66% (12,177) │
└───────────────────────────────────────────────────────┘

┌─ 🤖 Want AI to analyze this document? ───────────────┐
│                                                       │
│  Your AI coding tool will read the document and       │
│  populate your product configuration fields           │
│  (tech stack, architecture, testing, etc.)             │
│  plus generate improved summaries.                    │
│                                                       │
│  [ STAGE ANALYSIS ]        [ NO THANKS ]              │
│                                                       │
│  Requires a connected AI coding tool (Claude Code,    │
│  Codex CLI, Gemini CLI, or any MCP-compatible tool).  │
│                                                       │
│  Upload more: [Choose files] (.md, .txt)              │
└───────────────────────────────────────────────────────┘
```

**After AI analysis completes (WebSocket notification):**

```
┌─ product_vision_v2.md ──────────────────── × Remove ─┐
│  18,450 tokens · Uploaded 5 min ago                   │
│  Sumy summaries: ✅ 33% · ✅ 66%                      │
│  AI summaries:   ✅ 33% (4,200 tokens) · ✅ 66% (10,800) │
│  AI populated 14 product fields — review in Product Info │
└───────────────────────────────────────────────────────┘
```

### WebSocket Event

Listen for event type `vision_analysis_complete`:
```json
{
  "type": "vision_analysis_complete",
  "product_id": "abc-123",
  "fields_written": 14,
  "fields": ["product_description", "core_features", "programming_languages", ...]
}
```

On receiving this event:
1. Update the vision document card to show AI summary badges
2. Show inline notification: "AI populated N product fields — review in Product Info"
3. Optionally refresh product data to reflect new field values

### Staged Prompt

When user clicks "STAGE ANALYSIS", generate and display/copy a prompt:

```
Analyze the vision document for product "{product_name}" and populate its configuration.
Use the gil_get_vision_doc tool with product_id "{product_id}" to read the document and extraction instructions, then call gil_write_product with the extracted fields.
```

Implementation options (pick the simplest):
- Copy to clipboard with a toast "Prompt copied — paste in your CLI tool"
- Show in a dismissible text box the user can copy from

### Custom Instructions (Product Settings)

Add a text area in the product settings/configuration area:

**Label:** "Custom extraction instructions"
**Placeholder:** "Optional. Add domain-specific instructions for AI document analysis (e.g., 'This is a mobile-first app targeting iOS 17+')"
**Field:** `extraction_custom_instructions` on the product
**API:** Use existing product update endpoint — the column was added in 0842a

### Files to Create/Modify

| File | Change |
|------|--------|
| Vision document upload component | Add analysis prompt banner after upload completes. Add "Stage Analysis" + "No Thanks" buttons. |
| Vision document list/card component | Show AI summary badges when `vision_document_summaries` has AI entries. Show "AI populated N fields" notification line. |
| WebSocket store/handler | Listen for `vision_analysis_complete` event, update relevant state. |
| Product settings/form component | Add `extraction_custom_instructions` textarea field. |
| Product API composable/service | Add method to fetch AI summary status for display. |

### Tuning Icon on Product Card (Lift from Details Dialog)

Currently tuning is **invisible at card level** — buried 3 clicks deep inside ProductDetailsDialog. The only signal is the notification bell (which fires on staleness threshold). Users scanning the product grid have no idea which products need attention.

**Add `mdi-tune` icon button to the product card action bar** in `ProductsView.vue` (lines 173-246). Place it second, between the info button and the activate toggle:

```
   (i)      🎛️       ▶/■       ✏️       🗑️
  details  tune    activate   edit    delete
```

**Three visual states:**

| State | Icon | Color | Badge | Tooltip |
|-------|------|-------|-------|---------|
| **Normal** | `mdi-tune` | default (no color) | none | "Tune Context" |
| **Stale** (system recommends) | `mdi-tune` | default | notification dot (`v-badge dot color="info"`) | "Context tuning recommended" |
| **Proposals pending** | `mdi-tune` | default | notification dot (`v-badge dot color="warning"`) | "Tuning proposals ready for review" |

The notification dot matches the pattern used by the notification bell — same visual language, same trigger. The staleness check already runs after every `write_360_memory` call and emits `notification:new` with `type: "context_tuning"`. The proposals-pending state is driven by `product.tuning_state?.pending_proposals` being non-null.

**Click behavior**: Opens ProductDetailsDialog scrolled to tuning section (pass a prop or emit to auto-expand tuning).

**Data source for states**: The product object from the API already includes `tuning_state` (which has `pending_proposals` and `last_tuned_at_sequence`). For staleness, either:
- Compute client-side: compare `tuning_state.last_tuned_at_sequence` against product's memory sequence (if available in the product response)
- Or rely on the existing `context_tuning` notification in the notification store — check if an unread notification exists for this product_id

**CSS note**: Use `smooth-border` class on any rounded badge elements per CLAUDE.md convention. No hardcoded `border` on rounded elements.

### Key Existing Code

- **Product cards (inline)**: `frontend/src/views/ProductsView.vue:94-247` — cards rendered in `v-for` loop, action buttons at lines 173-246
- **Product detail dialog**: `frontend/src/components/products/ProductDetailsDialog.vue` — tuning menu + review components inside
- **Tuning menu**: `frontend/src/components/products/ProductTuningMenu.vue` — section picker + prompt generator
- **Tuning review**: `frontend/src/components/products/ProductTuningReview.vue` — accept/edit/dismiss proposals
- **Staleness trigger**: `src/giljo_mcp/tools/write_360_memory.py:442` — checks after every memory write
- **Staleness logic**: `src/giljo_mcp/services/product_tuning_service.py:569` — project-count-based threshold
- **Notification store**: `frontend/src/stores/notifications.js` — `context_tuning` type, info priority
- **WebSocket event router**: `frontend/src/stores/websocketEventRouter.js` — `product:tuning:proposals_ready` event + `notification:new` routing
- **Vision upload progress**: Fixed in 0816 (`2c8c921e`) — progress bar already wired
- **Vuetify 3**: Use `v-alert`, `v-btn`, `v-textarea`, `v-badge` components. Follow existing design tokens (no hardcoded hex colors per 0765c).

---

## Implementation Plan

### Phase 1: Tuning Icon on Product Card

1. Add `mdi-tune` icon button to action bar in `ProductsView.vue` (between info and activate)
2. Compute tuning state per product: normal / stale / proposals-pending
3. Wrap icon in `v-badge` with `dot` prop, conditionally visible when stale or proposals pending
4. Badge color: `info` for stale, `warning` for proposals pending
5. Click opens ProductDetailsDialog with tuning section focused
6. Test: icon renders for all products, dot appears when `tuning_state.pending_proposals` is non-null

### Phase 2: Analysis Prompt Banner

1. After vision document upload completes (Sumy done), show the analysis prompt card
2. "STAGE ANALYSIS" button copies prompt to clipboard + shows toast
3. "NO THANKS" dismisses the banner (store dismissal in component state, not persisted)
4. Banner reappears on new document upload

### Phase 3: WebSocket Integration

1. Add `vision:analysis_complete` event handler to `EVENT_MAP` in `websocketEventRouter.js`
2. On event: update vision document display to show AI summary info
3. Show inline success message with field count

### Phase 4: AI Summary Display

1. Add API call to check if AI summaries exist for a document
2. Display AI summary badges (similar to Sumy badges in wireframe)
3. Show "AI populated N fields — review in Product Info" link

### Phase 5: Custom Instructions

1. Add `v-textarea` for `extraction_custom_instructions` in product settings
2. Wire to product update API
3. Field persists across sessions

---

## Testing Requirements

**Tuning icon:**
- Tune icon renders on every product card (1 test)
- No dot badge when tuning state is normal (1 test)
- Dot badge appears when `pending_proposals` is non-null (1 test)
- Dot badge appears when product is stale (1 test)
- Click opens ProductDetailsDialog (1 test)

**Vision analysis UI:**
- Banner renders after upload (1 test)
- "Stage Analysis" copies correct prompt to clipboard (1 test)
- "No Thanks" dismisses banner (1 test)
- WebSocket event updates UI (1 test)
- AI summary badges render when data exists (1 test)
- Custom instructions textarea saves and loads (1 test)
- Accessibility: sufficient contrast, keyboard navigable buttons (manual check)

## Success Criteria

- [ ] `mdi-tune` icon visible on every product card in action bar
- [ ] Notification dot (info color) appears when staleness threshold reached
- [ ] Notification dot (warning color) appears when proposals pending
- [ ] No dot when tuning state is normal
- [ ] Click opens ProductDetailsDialog focused on tuning
- [ ] Analysis banner appears after vision doc upload with Sumy summaries
- [ ] "Stage Analysis" copies prompt to clipboard
- [ ] "No Thanks" dismisses banner
- [ ] WebSocket `vision:analysis_complete` updates vision doc card
- [ ] AI summary badges visible when AI summaries exist
- [ ] Custom instructions textarea in product settings
- [ ] WCAG AA contrast ratios met
- [ ] No `!important` CSS overrides, `smooth-border` class on rounded elements
- [ ] ~11 frontend tests

## Edge Cases

- **No CLI tool connected**: Banner still shows — it's informational. Helper text already says "Requires a connected AI coding tool."
- **Multiple documents**: Each document gets its own analysis banner independently
- **Re-upload**: New document replaces old, banner reappears, old AI summaries are orphaned (cascade delete handles cleanup)
- **Tuning icon + inactive product**: Icon still shows (tuning is valid for inactive products too)
- **No tuning_state on product**: Treat as normal state (no dot)

## Rollback Plan

- Revert Vue component changes
- Tuning icon is additive — existing tuning flow in details dialog is unchanged
- Banner is purely additive — no existing UI is modified

---

## MANDATORY: Pre-Work Reading

Before writing ANY code, you MUST read these documents:

1. `handovers/HANDOVER_INSTRUCTIONS.md` — quality gates, TDD protocol, code discipline, frontend code discipline section
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — system architecture overview
3. `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` — agent flow
4. `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md` — the feature specification (Sections 1, 6, 7)
5. `handovers/Reference_docs/FLow_vision_doc1.png` — user journey flowchart
6. `handovers/Reference_docs/FLow_vision_doc2.png` — AI analysis sequence diagram
7. `handovers/Reference_docs/FLow_vision_doc3.png` — upload UI wireframe

**CRITICAL: Use the `ux-designer` subagent for ALL implementation work in this handover.** Use `frontend-tester` subagent for test validation after implementation.

---

## Chain Execution Instructions

This is handover **4 of 5** in the 0842 Vision Document Analysis chain.

### Step 1: Read Chain Log
Read `prompts/0842_chain/chain_log.json`.
- Check `orchestrator_directives` for any STOP instructions — if STOP, halt immediately
- Review ALL previous sessions' `notes_for_next` — you need:
  - From 0842a: model/table names for summary data
  - From 0842c: exact WebSocket event type, MCP tool names as registered, any field mapping deviations
- Verify 0842a AND 0842c status are both `complete` (direct dependencies) — if either blocked/failed, STOP and report to user

### Step 2: Mark Session Started
Update your session entry in the chain log:
```json
"status": "in_progress",
"started_at": "<current ISO timestamp>"
```

### Step 3: Execute Handover Tasks
Complete all phases above. Use `ux-designer` subagent for implementation, `frontend-tester` for validation. Commit after each phase passes.

### Step 4: Update Chain Log
Before spawning next terminal, update your session in `prompts/0842_chain/chain_log.json`:
- `tasks_completed`: List what you actually did
- `deviations`: Any changes from plan
- `blockers_encountered`: Issues hit
- `notes_for_next`: Critical info for 0842e agent
- `cascading_impacts`: Any backend assumptions that turned out wrong
- `summary`: 2-3 sentence summary
- `status`: "complete"
- `completed_at`: "<current ISO timestamp>"

### Step 5: Spawn Next Terminal
**Use Bash tool to EXECUTE (don't just print!):**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0842e - E2E Test\" --tabColor \"#F44336\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0842e. READ FIRST: F:\GiljoAI_MCP\handovers\0842e_VISION_DOC_ANALYSIS_E2E_TEST.md — Read the ENTIRE document including Chain Execution Instructions at the bottom. You are session 5 of 5 (FINAL) in the 0842 chain. Use backend-tester subagent.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS.** Only ONE agent should spawn the next terminal.
