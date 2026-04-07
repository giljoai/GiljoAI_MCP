# Handover 0962: Database & Code Harmonization Cleanup

**Date:** 2026-04-07
**Edition Scope:** CE
**From Agent:** Claude Opus 4.6 (audit session with product owner)
**To Agent:** Next implementing session
**Priority:** High
**Estimated Complexity:** 3-4 days (4 phases)
**Status:** Not Started

---

## Task Summary

The 0840 harmonization normalized free-text JSON into typed relation tables. Since then, new features (tuning v2, vision analysis, templates) have introduced parallel write paths, missing validators, and raw `setattr` from agent input. This handover cleans every finding from the 2026-04-07 audit and establishes guardrails (CLAUDE.md + HANDOVER_INSTRUCTIONS.md rules already committed) so drift cannot recur silently.

**Why it matters:** Agent-provided strings currently reach DB columns with no type checking, no length caps, and no membership validation. The `ProductService.update_product()` method — the intended single gate — uses `hasattr` instead of an allowlist, meaning any ORM attribute (including `tenant_key`, `deleted_at`) is writable. A second complete write path in `vision_analysis.py` bypasses the service entirely.

**What changes:** Backend service/tool code only. No frontend changes. No new DB columns or migrations. One potential column removal (duplicate `quality_standards`).

---

## Audit Findings Reference

Full audit was performed 2026-04-07 with 5 parallel investigation agents. Commit `3d03c35e` (0961 refactor) partially addressed the tuning service — it now routes through `ProductService.update_product()` and converts `target_platforms` strings to lists. The remaining findings are below.

---

## Phase 0962a: ProductService Allowlist + Tuning Validation (~1 day)

**Goal:** Close the `hasattr` hole in `update_product()` and add input validation to tuning proposals.

### Files to Modify

**`src/giljo_mcp/services/product_service.py`** (~lines 525-540)

Current code:
```python
for field, value in updates.items():
    if hasattr(product, field):
        setattr(product, field, value)
```

Fix: Replace with explicit allowlist:
```python
_ALLOWED_PRODUCT_FIELDS = {
    "name", "description", "project_path", "core_features",
    "brand_guidelines", "extraction_custom_instructions",
    "target_platforms", "quality_standards",
}

for field, value in updates.items():
    if field in _ALLOWED_PRODUCT_FIELDS:
        setattr(product, field, value)
```

Note: `tech_stack`, `architecture`, `test_config` are already handled by `_update_config_relations()` before this loop. Confirm that path is clean.

**`src/giljo_mcp/tools/submit_tuning_review.py`** (~lines 37-61)

Current `_validate_proposals()` checks `section`, `drift_detected`, `confidence` but never touches `proposed_value`.

Fix:
1. Add type validation: `proposed_value` must be `str | dict | None`
2. Add length cap: strings max 10000 chars
3. For `target_platforms` section: validate list items against `VALID_TARGET_PLATFORMS`
4. Consider replacing the manual validation with a `TuningProposal` Pydantic model

**`src/giljo_mcp/tools/submit_tuning_review.py`** (~lines 20-32)

`VALID_SECTIONS` has 11 keys but `SECTION_FIELD_MAP` has 7. Fix:
- Remove dead sections: `codebase_structure`, `database_type`, `backend_framework`, `frontend_framework`, `vision_documents`
- Add missing section: `brand_guidelines` (present in `SECTION_FIELD_MAP` but rejected by `VALID_SECTIONS`)

**`src/giljo_mcp/services/product_tuning_service.py`** (~line 441)

`_build_update_kwargs` still does `dict.fromkeys(mapping["fields"], value)` for string values on relation sections — writes the same string to every column. Fix: reject non-dict values for relation sections, or require the agent to provide a per-field dict. Log a warning and skip the section.

**`src/giljo_mcp/services/product_tuning_service.py`** (~line 482)

Dead write: `tuning_state["pending_proposals"] = None`. The `pending_proposals` field was removed from `ProductTuningState` in 0961. Remove this line.

### Tests

- `tests/services/test_product_tuning_service.py` — update test at ~line 671 that asserts `target_platforms == "windows, linux, macos"` (documents broken behavior). After fix, should assert a list.
- Add test: `update_product` rejects fields not in allowlist (e.g., `tenant_key`, `deleted_at`)
- Add test: `_validate_proposals` rejects non-string/non-dict `proposed_value`
- Add test: `_validate_proposals` rejects strings over 10000 chars
- Add test: relation sections reject string values (require dict)

### Success Criteria

- `update_product(**{"tenant_key": "evil"})` silently ignores the field
- `_validate_proposals` returns errors for invalid `proposed_value` types
- `VALID_SECTIONS` matches `SECTION_FIELD_MAP` keys exactly
- No dead `pending_proposals` write

---

## Phase 0962b: Vision Analysis Consolidation (~1 day)

**Goal:** Eliminate the parallel write path in `gil_write_product` — route through `ProductService.update_product()`.

### Files to Modify

**`src/giljo_mcp/tools/vision_analysis.py`** (~lines 300-440)

Current: `gil_write_product` opens its own session via `_session_scope`, constructs `ProductTechStack`, `ProductArchitecture`, `ProductTestConfig` rows directly, and writes via `setattr`. Only `target_platforms` is validated.

Fix: Refactor `_write_product_fields`, `_write_tech_stack_fields`, `_write_architecture_fields`, `_write_test_config_fields` to build a kwargs dict (same pattern as `_build_update_kwargs` in tuning service), then call `ProductService.update_product(product_id, **kwargs)`.

Key concerns during refactor:
- The current code does `session.flush()` — the new code must commit via ProductService
- `_session_scope` context manager lifecycle must be removed (ProductService owns the session)
- Verify the `target_platforms` validation in the current code (~lines 344-350) is covered by ProductService's `_validate_target_platforms`
- The cross-reference comment at lines 36-40 can be removed once there's a single write path
- `testing_strategy` should be validated against its documented enum before reaching the service
- `coverage_target` (Integer column) should be range-checked (0-100)

### Tests

- Existing vision analysis tests should continue to pass (behavior unchanged, path changed)
- Add test: `gil_write_product` with invalid `testing_strategy` raises error
- Add test: `gil_write_product` with `coverage_target > 100` raises error

### Success Criteria

- `vision_analysis.py` has zero direct SQLAlchemy session management for product writes
- All product writes go through `ProductService.update_product()`
- The `_session_scope` / `session.flush()` pattern is removed from product write functions

---

## Phase 0962c: JSONB Validator Coverage (~1 day)

**Goal:** Add missing validators and fix mismatched ones.

### Missing Validators to Add (in `src/giljo_mcp/schemas/jsonb_validators.py`)

| Column | Table | Validator to Add |
|--------|-------|-----------------|
| `result` | `agent_executions` | `AgentExecutionResult` — fields: `summary: str`, `artifacts: list[str] \| None`, `commits: list[str] \| None` |
| `closeout_checklist` | `projects` | `CloseoutChecklistItem` — fields: `task: str`, `completed: bool`, plus list validator |
| `behavioral_rules` | `agent_templates` | `validate_behavioral_rules(data) -> list[str]` — simple string list validator |
| `success_criteria` | `agent_templates` | `validate_success_criteria(data) -> list[str]` — simple string list validator |
| `variables` | `agent_templates` | `validate_template_variables(data) -> list[dict]` — validate variable structure |

### Validators to Fix

**`ProductMemoryConfig`** (~lines 109-116)
- Declares fields `git_integration`, `context_metadata`
- Actual keys in DB/code: `github`, `context`
- Fix: rename fields to match actual keys, OR rename code to match validator. Check all callers of `get_memory_field()` and the server_default to determine which is canonical.

**`AgentJobMetadata`** (~line 26)
- Still declares `todo_steps: list | None`
- `todo_steps` was normalized to `agent_todo_items` table in Handover 0402
- Fix: remove `todo_steps` from the Pydantic model

**`OrganizationSettings`** (~line 78-82)
- Empty passthrough with `extra="allow"` and no fields
- If the settings blob has known keys, declare them. If it's genuinely schema-less, add a code comment explaining why.

### Wire Up Missing `validate_*` Calls

**`src/giljo_mcp/tools/write_360_memory.py`** (~line 493)
- `git_commits` from agents bypass `validate_git_commits()` — the validator exists but isn't called on the agent-supplied path
- Fix: call `validate_git_commits(git_commits)` before passing to `repo.create_entry()`

**`src/giljo_mcp/services/template_service.py`** (~lines 899-921)
- `behavioral_rules` and `success_criteria` written without validation
- Fix: call the new validators before writing

### Tests

- Add test per new validator: valid input passes, invalid input raises `ValidationError`
- Add test: `write_360_memory` with malformed `git_commits` raises error
- Add test: template service with non-string `behavioral_rules` items raises error

### Success Criteria

- Every actively-written JSONB column has a validator in `jsonb_validators.py`
- Every validator is called at the service/tool write boundary
- `ProductMemoryConfig` field names match actual DB keys
- `AgentJobMetadata` no longer references `todo_steps`

---

## Phase 0962d: Schema Redundancy + Enum Validation (~0.5 day)

**Goal:** Resolve the two known schema redundancies and add enum validation to Pydantic request schemas.

### Schema Redundancy

**`quality_standards` duplication:**
- `products.quality_standards` (Text, nullable) — on the parent table
- `product_test_configs.quality_standards` (Text, nullable) — on the child table
- Decision needed: which is canonical? The normalized model says `product_test_configs`. If so, deprecate the `products` column (remove from allowlist, stop writing to it, add migration to drop it in next baseline squash). If both are needed, document why.

**`target_platforms` duplication:**
- `products.target_platforms` — `ARRAY(String)` with check constraints
- `product_tech_stacks.target_*` — 6 boolean columns
- Additionally: `target_cross_platform` has no equivalent in the array; `web` in the array has no equivalent boolean
- Decision needed: the ARRAY is the validated path (check constraints, `_validate_target_platforms`). The booleans appear to be the legacy representation. If so, stop writing the booleans and mark them for removal in next baseline squash. If both are needed, add a sync mechanism.

### Enum Validation

**`api/schemas/task.py`** — `TaskCreate`, `TaskUpdate`, `StatusUpdate`:
- `status` and `priority` are `Optional[str]` — change to `Literal` types matching the valid DB values

**`api/endpoints/messages.py`** — `MessageSend`, `MessageSendRequest`:
- `message_type: str` → `Literal["direct", "broadcast"]`
- `priority: str` → `Literal["low", "normal", "high"]`

### Tests

- Add test: `TaskCreate` with invalid status returns 422
- Add test: `MessageSend` with invalid `message_type` returns 422

### Success Criteria

- `quality_standards` ownership decided and documented (one source of truth)
- `target_platforms` ownership decided and documented
- Task and message enum fields reject invalid values at the API layer

---

## Dependencies

- **0962a must complete before 0962b** — `update_product()` needs the allowlist before vision analysis routes through it
- **0962c and 0962d are independent** — can run in parallel, or after a+b
- **No dependency on 0950 series** — this is orthogonal to the pre-release quality sprint
- **No frontend changes required**
- **No new migrations required** (column removals in 0962d deferred to next baseline squash)

---

## Rollback Plan

All changes are backend code refactors with no schema changes. Revert via `git revert` on the phase commit. No data migration needed.

---

## DB Column Comment Update (Housekeeping)

After all phases complete, update the `tuning_state` column comment to remove `pending_proposals`:
```sql
COMMENT ON COLUMN products.tuning_state IS 'Context tuning state: last_tuned_at, last_tuned_at_sequence';
```
This can go in the next baseline squash or as a standalone incremental migration.
