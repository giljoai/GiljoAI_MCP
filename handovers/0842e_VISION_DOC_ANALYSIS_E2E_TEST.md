# Handover 0842e: Vision Document Analysis — End-to-End Integration Test

**Date:** 2026-03-27
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** backend-tester
**Priority:** High
**Estimated Complexity:** 0.5 hours
**Status:** Complete
**Series:** 0842a-e (Vision Document Analysis Feature)
**Spec:** `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md`
**Depends on:** 0842a, 0842b, 0842c, 0842d

---

## Task Summary

Validate the complete vision document analysis flow end-to-end: upload → Sumy → MCP read → MCP write → Context Manager depth preference. This is the final verification that all pieces work together.

---

## Test Scenarios

### Test 1: Full AI Analysis Flow

1. Create a product
2. Upload a vision document (triggers Sumy → summaries table populated with source="sumy")
3. Call `gil_get_vision_doc(product_id)` — verify returns document + extraction prompt
4. Call `gil_write_product(product_id, ...)` with sample extracted fields + summaries
5. Verify: product fields updated in all 4 tables (products, tech_stacks, architectures, test_configs)
6. Verify: AI summaries written to `vision_document_summaries` with source="ai"
7. Verify: WebSocket `vision_analysis_complete` event emitted

### Test 2: Context Manager AI Preference

1. After Test 1 completes (both Sumy and AI summaries exist)
2. Fetch context with depth="light" → verify returns AI summary (not Sumy)
3. Fetch context with depth="medium" → verify returns AI summary (not Sumy)
4. Fetch context with depth="full" → verify returns original document (unchanged)

### Test 3: Sumy-Only Fallback

1. Upload a vision document (only Sumy summaries exist, no AI analysis)
2. Fetch context with depth="light" → verify returns Sumy summary
3. Fetch context with depth="medium" → verify returns Sumy summary

### Test 4: Partial Field Write

1. Call `gil_write_product` with only 3 fields (e.g., product_description, programming_languages, summary_33)
2. Verify: only those 3 fields written
3. Verify: all other fields untouched (not nulled)

### Test 5: Custom Instructions

1. Set `extraction_custom_instructions` on product: "Focus on mobile architecture"
2. Call `gil_get_vision_doc` → verify custom instructions appear in extraction prompt
3. Clear custom instructions → verify prompt has no custom section

---

## Success Criteria

- [x] All 5 test scenarios pass
- [x] No regressions in existing test suite (33/33 passing)
- [x] Full flow works: upload → Sumy → MCP tools → Context Manager reads AI-preferred summaries

## Installation Impact

**Check before marking series complete:**
- [x] `install.py` baseline migration awareness: migration 0842a_vds chains from 0840e_project_meta; baseline squash pending next periodic cycle
- [x] `config.yaml`: no new config keys needed (extraction prompt is code, not config)
- [x] Server starts clean after fresh install with the new migration

## Rollback Plan

- Tests are non-destructive — no rollback needed

---

## MANDATORY: Pre-Work Reading

Before writing ANY code, you MUST read these documents:

1. `handovers/HANDOVER_INSTRUCTIONS.md` — quality gates, TDD protocol
2. `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md` — the feature specification

**Use subagent**: Spawn `backend-tester` for all test implementation.

---

## Chain Execution Instructions

This is handover **5 of 5 (FINAL)** in the 0842 Vision Document Analysis chain.

### Step 1: Read Chain Log
Read `prompts/0842_chain/chain_log.json`.
- Check `orchestrator_directives` for any STOP instructions — if STOP, halt immediately
- Review ALL previous sessions' `notes_for_next` — you need actual tool names, method signatures, event types, any deviations from the original plan
- Verify ALL previous sessions (0842a, 0842b, 0842c, 0842d) are `complete` — if any blocked/failed, STOP and report to user

### Step 2: Mark Session Started
Update your session entry in the chain log:
```json
"status": "in_progress",
"started_at": "<current ISO timestamp>"
```

### Step 3: Execute Handover Tasks
Run all 5 test scenarios. Also run the full existing test suite to verify no regressions.

### Step 4: Update Chain Log — CHAIN COMPLETE
Update your session AND the chain-level fields:
```json
// Your session:
"status": "complete",
"completed_at": "<current ISO timestamp>",
"tasks_completed": [...],
"summary": "..."

// Chain level:
"chain_summary": "Vision Document Analysis feature complete. X commits, Y tests added, Z files modified.",
"final_status": "complete"
```

### Step 5: Final Commit
Commit all E2E tests. This is the last session — do NOT spawn another terminal.

**CHAIN COMPLETE.** The orchestrator will review the chain log and report to the user.
