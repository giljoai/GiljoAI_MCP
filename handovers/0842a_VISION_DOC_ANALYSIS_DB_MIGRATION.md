# Handover 0842a: Vision Document Analysis — DB Migration & Sumy Wiring

**Date:** 2026-03-27
**Edition Scope:** CE
**From Agent:** Planning Session
**To Agent:** database-expert + tdd-implementor
**Priority:** High
**Estimated Complexity:** 1.5 hours
**Status:** Not Started
**Series:** 0842a-e (Vision Document Analysis Feature)
**Spec:** `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md`

---

## Task Summary

Create the `vision_document_summaries` table and add `extraction_custom_instructions` to products. Wire Sumy output to write into the new summaries table instead of (or in addition to) the VisionDocument columns.

This is the foundation — all other 0842 handovers depend on this.

---

## Context and Background

Currently Sumy summaries are stored as columns directly on the `VisionDocument` model (`summary_light`, `summary_medium`, `summary_light_tokens`, `summary_medium_tokens`). The new architecture introduces a dedicated summaries table that tracks **source** (sumy vs ai) and **ratio** (0.33 vs 0.66), enabling the Context Manager to prefer AI summaries over Sumy when both exist.

Additionally, consolidated summaries on the `Product` model (`consolidated_vision_light`, `consolidated_vision_medium`, etc.) aggregate across multiple documents — this consolidation logic will need updating in 0842b.

---

## Technical Details

### Database Changes

**New table: `vision_document_summaries`**

```sql
CREATE TABLE vision_document_summaries (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(255) NOT NULL,
    document_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    source VARCHAR(20) NOT NULL,            -- "sumy" | "ai"
    ratio DECIMAL(3,2) NOT NULL,            -- 0.33 | 0.66
    summary TEXT NOT NULL,
    tokens_original INTEGER NOT NULL,
    tokens_summary INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    FOREIGN KEY (document_id) REFERENCES vision_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);
CREATE INDEX idx_vds_lookup ON vision_document_summaries (tenant_key, document_id, source, ratio);
```

**Products table addition:**
```sql
ALTER TABLE products ADD COLUMN extraction_custom_instructions TEXT;
```

### Files to Modify

| File | Change |
|------|--------|
| `src/giljo_mcp/models/products.py` | Add `VisionDocumentSummary` SQLAlchemy model (~line 649+). Add `extraction_custom_instructions` column to `Product` model. |
| `src/giljo_mcp/repositories/vision_document_repository.py` | Add methods: `create_summary()`, `get_summaries()`, `get_best_summary(document_id, ratio)` — returns AI-preferred summary. Also add `get_product_summaries(product_id, ratio)` for multi-doc aggregation (used by 0842b). |
| `api/endpoints/vision_documents.py` | Wire new table writes at **3 injection points** (see below). |
| `migrations/versions/` | New incremental Alembic migration with idempotency guards. |

### Injection Points — All 3 Must Be Wired

Sumy summary writes currently happen inline in the endpoint, directly on ORM columns, bypassing the repository. All 3 must be updated:

1. **`create_vision_document()`** (lines ~237-243) — after Sumy runs on new upload
2. **`update_vision_document()`** (lines ~433-440) — after Sumy re-runs on content update
3. **`regenerate_summaries()`** (lines ~656-662) — manual re-summarize endpoint. **Note:** this endpoint does NOT trigger consolidation (pre-existing gap) — fix it while we're here.

**Pattern**: After each Sumy call, persist via `vision_document_repo.create_summary()` (upsert — delete existing sumy rows for this doc+ratio first, then insert fresh).

### Key Existing Code

- **VisionDocument model**: `src/giljo_mcp/models/products.py:424-649` — has `summary_light`, `summary_medium` columns
- **Upload endpoint**: `api/endpoints/vision_documents.py:110-288` — calls `VisionDocumentSummarizer.summarize_multi_level()`
- **Update endpoint**: `api/endpoints/vision_documents.py:378-469` — same Sumy pattern, 2nd injection point
- **Regenerate endpoint**: `api/endpoints/vision_documents.py:601-687` — 3rd injection point, missing consolidation trigger
- **Sumy service**: `src/giljo_mcp/services/vision_summarizer.py` — `VisionDocumentSummarizer` class with LSA algorithm
- **Vision repo**: `src/giljo_mcp/repositories/vision_document_repository.py` — CRUD operations (currently zero summary logic)
- **Consolidation service**: `src/giljo_mcp/services/consolidation_service.py` — `ConsolidatedVisionService.consolidate_vision_documents()` re-summarizes full text aggregate, writes to Product columns

### Session Handling Note

After the first `db.commit()` in the create flow, the `doc` ORM object is detached. The endpoint re-adds it via `db.add(doc)`. New `VisionDocumentSummary` ORM objects must also be added to the session before the second commit.

### Backward Compatibility

Keep writing to the old `summary_light`/`summary_medium` columns on VisionDocument for now. The old columns become redundant once 0842b migrates Context Manager reads to the new table. Removal of old columns is a future cleanup task (not in scope).

---

## Implementation Plan

### Phase 1: Migration (TDD)

1. Write test: assert `vision_document_summaries` table exists with correct columns
2. Write test: assert `products.extraction_custom_instructions` column exists
3. Create Alembic migration with idempotency guards (`op.execute("SELECT 1 FROM information_schema.tables WHERE table_name='vision_document_summaries'")` pattern)
4. Add `VisionDocumentSummary` model to `src/giljo_mcp/models/products.py`
5. Add `extraction_custom_instructions = Column(Text, nullable=True)` to Product model

### Phase 2: Repository Layer (TDD)

1. Write tests for `create_summary()` — tenant isolation, source/ratio stored correctly
2. Write tests for `get_summaries(document_id)` — filtered by tenant_key
3. Write tests for `get_best_summary(document_id, ratio)` — AI preferred over Sumy
4. Implement repository methods

### Phase 3: Wire Sumy Output (All 3 Injection Points)

1. Write test: uploading a vision document creates 2 rows in `vision_document_summaries` (33% + 66%, source=sumy)
2. Write test: updating a vision document replaces sumy rows in `vision_document_summaries`
3. Write test: regenerating summaries replaces sumy rows in `vision_document_summaries`
4. Modify `create_vision_document()` to persist summaries via new repository after Sumy runs
5. Modify `update_vision_document()` — same pattern (2nd injection point)
6. Modify `regenerate_summaries()` — same pattern + add missing `trigger_consolidation()` call (3rd injection point, pre-existing gap fix)
7. Verify old columns still written (backward compat)

---

## Testing Requirements

- Migration test: table and column exist
- Repository tests: CRUD with tenant isolation (3-4 tests)
- Integration test: upload flow creates summary rows (1 test)
- All existing vision document tests must still pass

## Success Criteria

- [ ] `vision_document_summaries` table created with indexes and FKs
- [ ] `extraction_custom_instructions` column on products
- [ ] Sumy output writes to new table on every vision doc upload
- [ ] AI-preferred lookup method exists (`get_best_summary`)
- [ ] All existing tests pass
- [ ] New tests pass (target: 8-10 tests)

## Dependencies

- None — this is the foundation

## Rollback Plan

- Drop migration: `alembic downgrade -1`
- No data loss risk (additive only)

---

## MANDATORY: Pre-Work Reading

Before writing ANY code, you MUST read these documents:

1. `handovers/HANDOVER_INSTRUCTIONS.md` — quality gates, TDD protocol, code discipline
2. `handovers/Reference_docs/QUICK_LAUNCH.txt` — system architecture overview
3. `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` — agent flow and MCP tool patterns
4. `handovers/VISION_DOC_ANALYSIS_SPEC_v2.md` — the feature specification

**Use subagents**: Spawn `database-expert` for migration + model work, `tdd-implementor` for repository + endpoint wiring.

---

## Chain Execution Instructions

This is handover **1 of 5** in the 0842 Vision Document Analysis chain.

### Step 1: Read Chain Log
Read `prompts/0842_chain/chain_log.json`.
- Check `orchestrator_directives` for any STOP instructions
- This is the first handover — no previous session to verify

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
- `notes_for_next`: Critical info for 0842b agent (e.g., exact model class name, repo method signatures, any schema deviations)
- `cascading_impacts`: Changes that affect 0842c/d/e
- `summary`: 2-3 sentence summary
- `status`: "complete"
- `completed_at`: "<current ISO timestamp>"

### Step 5: Spawn Next Terminal
**Use Bash tool to EXECUTE (don't just print!):**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0842b - Context Manager\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0842b. READ FIRST: F:\GiljoAI_MCP\handovers\0842b_VISION_DOC_ANALYSIS_CONTEXT_MANAGER.md — Read the ENTIRE document including Chain Execution Instructions at the bottom. You are session 2 of 5 in the 0842 chain. Use tdd-implementor subagent.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS.** Only ONE agent should spawn the next terminal.
