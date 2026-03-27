# Handover 0842b: Vision Document Analysis — Context Manager Summary Reads

**Date:** 2026-03-27
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** tdd-implementor
**Priority:** High
**Estimated Complexity:** 1 hour
**Status:** Not Started
**Series:** 0842a-e (Vision Document Analysis Feature)
**Spec:** `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md`
**Depends on:** 0842a

---

## Task Summary

Update the Context Manager and vision document depth handler to read summaries from the new `vision_document_summaries` table, preferring AI summaries over Sumy when both exist. This replaces direct reads from VisionDocument columns.

---

## Context and Background

Currently, the context depth handler reads summaries from two places:

1. **Per-document**: `VisionDocument.summary_light` / `VisionDocument.summary_medium` columns
2. **Consolidated**: `Product.consolidated_vision_light` / `Product.consolidated_vision_medium` (aggregated across all docs for a product, built by Handover 0377)

The new flow:
- depth `"full"` → unchanged (reads from `vision_documents` / chunks)
- depth `"medium"` → `SELECT summary FROM vision_document_summaries WHERE ratio=0.66 ORDER BY (source='ai') DESC, created_at DESC LIMIT 1`
- depth `"light"` → same but `ratio=0.33`

AI summaries are preferred over Sumy. If only Sumy exists (no AI analysis done yet), Sumy is served.

---

## Technical Details

### Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/tools/context_tools/get_vision_document.py` | Lines 231-552. Update `_get_summary_response()` (lines 83-229) — currently reads `product.consolidated_vision_light`/`product.consolidated_vision_medium` at lines 107-113. Replace with new table query + fallback to old columns. |
| `src/giljo_mcp/repositories/vision_document_repository.py` | Use `get_best_summary()` from 0842a. Add `get_product_summaries(product_id, ratio)` that fetches best summary per active document, ordered by AI-first. |

### Key Existing Code

- **Vision depth handler**: `src/giljo_mcp/tools/context_tools/get_vision_document.py:231-552`
  - `"light"` branch reads `Product.consolidated_vision_light`
  - `"medium"` branch reads `Product.consolidated_vision_medium`
  - `"full"` branch paginates `MCPContextIndex` chunks
- **Consolidation**: Product model has `consolidated_vision_light`, `consolidated_vision_medium`, `consolidated_vision_hash`, `consolidated_at`
- **fetch_context router**: `src/giljo_mcp/tools/context_tools/fetch_context.py` — dispatches `"vision_documents"` category to `get_vision_document`

### Query Logic (from spec)

```sql
-- depth_config: "full"  → serve from vision_documents (unchanged)
-- depth_config: "medium" → SELECT summary WHERE ratio = 0.66
--                          ORDER BY (source = 'ai') DESC, created_at DESC LIMIT 1
-- depth_config: "light"  → same but ratio = 0.33
-- AI summaries preferred over Sumy when both exist.
```

### Multi-Document Aggregation Strategy

The current `ConsolidatedVisionService` aggregates ALL active vision documents by concatenating their full text with `# {doc_name}` headers, then re-summarizing the whole thing. The new per-document summaries table stores summaries **per document**.

**Strategy for multi-doc products:** For each active document, fetch the best summary (AI preferred, then Sumy) at the requested ratio. Concatenate with document name headers:

```
# {doc_1.document_name}
{best_summary_for_doc_1}

# {doc_2.document_name}
{best_summary_for_doc_2}
```

This is simpler than re-summarizing and preserves per-document AI preference. Token count is the sum of all per-doc summaries.

### Fallback Strategy

Try the new `vision_document_summaries` table first. If no rows exist for any document (e.g., product created before this feature), fall back to `Product.consolidated_vision_light` / `Product.consolidated_vision_medium`. This is a zero-breakage migration path.

### Consolidation Service: Keep Running

Do NOT stop `ConsolidatedVisionService` from writing to Product columns — the frontend `ProductDetailsDialog.vue` (lines 166-195, 601-611) reads them directly for summary chip display. Both paths coexist during transition. Removal of consolidated columns is a future cleanup task.

### context_manager.py: No Changes Needed

Confirmed: `src/giljo_mcp/context_manager.py` has zero vision-related logic. It deals exclusively with role-based config filtering. No changes needed there.

---

## Implementation Plan

### Phase 1: Repository Method (TDD)

1. Write test: `get_product_summaries(product_id, ratio)` returns all summaries for a product's documents at given ratio, ordered AI-first
2. Implement the method — joins `vision_document_summaries` with `vision_documents` (active only), filters by tenant + product + ratio

### Phase 2: Context Tool Update (TDD)

1. Write test: depth="light" returns AI summary when both AI and Sumy exist
2. Write test: depth="light" returns Sumy summary when only Sumy exists
3. Write test: depth="medium" same preference behavior
4. Write test: depth="full" unchanged behavior
5. Update `get_vision_document.py` light/medium branches to use new repository method
6. Concatenate summaries from multiple documents if needed (matching current consolidation behavior)

---

## Testing Requirements

- Repository test: AI-preferred multi-document aggregation (2 tests)
- Context tool tests: depth preference behavior (4 tests)
- All existing context/vision tests must still pass

## Success Criteria

- [ ] depth="light" serves from `vision_document_summaries` with AI preference
- [ ] depth="medium" same behavior
- [ ] depth="full" unchanged
- [ ] Multi-document products aggregate correctly
- [ ] All existing tests pass

## Rollback Plan

- Revert to reading from Product consolidated columns (the old columns still exist)

---

## MANDATORY: Pre-Work Reading

Before writing ANY code, you MUST read these documents:

1. `handovers/HANDOVER_INSTRUCTIONS.md` — quality gates, TDD protocol, code discipline
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — system architecture overview
3. `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` — agent flow and MCP tool patterns
4. `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md` — the feature specification (Sections 4.3 and 5)

**Use subagent**: Spawn `tdd-implementor` for all implementation work.

---

## Chain Execution Instructions

This is handover **2 of 5** in the 0842 Vision Document Analysis chain.

### Step 1: Read Chain Log
Read `prompts/0842_chain/chain_log.json`.
- Check `orchestrator_directives` for any STOP instructions — if STOP, halt immediately
- Review 0842a session's `notes_for_next` — it will tell you exact model class names, repo method signatures
- Verify 0842a status is `complete` — if blocked/failed, STOP and report to user

### Step 2: Mark Session Started
Update your session entry in the chain log:
```json
"status": "in_progress",
"started_at": "<current ISO timestamp>"
```

### Step 3: Execute Handover Tasks
Complete all phases above using TDD. Commit after each phase passes.

### Step 4: Update Chain Log
Before spawning next terminal, update your session in `prompts/0842_chain/chain_log.json`:
- `tasks_completed`: List what you actually did
- `deviations`: Any changes from plan
- `blockers_encountered`: Issues hit
- `notes_for_next`: Critical info for 0842c agent
- `cascading_impacts`: Changes that affect 0842c/d/e
- `summary`: 2-3 sentence summary
- `status`: "complete"
- `completed_at`: "<current ISO timestamp>"

### Step 5: Spawn Next Terminal
**Use Bash tool to EXECUTE (don't just print!):**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0842c - MCP Tools\" --tabColor \"#9C27B0\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0842c. READ FIRST: F:\GiljoAI_MCP\handovers\0842c_VISION_DOC_ANALYSIS_MCP_TOOLS.md — Read the ENTIRE document including Chain Execution Instructions at the bottom. You are session 3 of 5 in the 0842 chain. Use tdd-implementor subagent.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS.** Only ONE agent should spawn the next terminal.
