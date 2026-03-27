# Handover 0840a: Dead Column Cleanup

**Date:** 2026-03-25
**From Agent:** Orchestrator (JSONB Normalization Planning Session)
**To Agent:** Next Session (database-expert + tdd-implementor)
**Priority:** High
**Estimated Complexity:** 2-3 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Remove 7 completely dead `meta_data` columns and 6 ghost config keys from the codebase. These columns were added as boilerplate "every table gets meta_data" pattern in Sep-Oct 2025 but were never written to or read from in production code. This is zero-functional-impact cleanup that reduces schema noise before the larger normalization effort.

## Context and Background

A comprehensive JSONB audit (March 25, 2026) identified 48 JSON/JSONB columns across 24 tables. Seven `meta_data` columns are completely dead — never written, never meaningfully read. Additionally, 6 keys are referenced in `context_manager.py` ROLE_CONFIG_FILTERS but have no write path anywhere in the codebase.

This is Handover 1 of 6 in the JSONB Normalization Series (0840a-f). It must complete first as it establishes the clean baseline for subsequent handovers.

## Technical Details

### Dead Columns to Remove (7)

| Table | Model File | Column | Evidence |
|-------|-----------|--------|----------|
| `template_archives` | `src/giljo_mcp/models/templates.py` | `meta_data` (JSON) | 0 writes, 0 reads |
| `products` | `src/giljo_mcp/models/products.py` | `meta_data` (JSON) | 0 writes, 1 read returns `{}` always (`get_product_context.py:113`) |
| `tasks` | `src/giljo_mcp/models/tasks.py` | `meta_data` (JSONB) | 0 writes, 0 reads |
| `git_configs` | `src/giljo_mcp/models/config.py` | `meta_data` (JSON) | 0 writes, 0 reads |
| `git_commits` | `src/giljo_mcp/models/config.py` | `meta_data` (JSON) | 0 writes, 0 reads |
| `setup_state` | `src/giljo_mcp/models/config.py` | `meta_data` (JSONB) | Only writes `{}`, only reads `{}` |
| `optimization_metrics` | `src/giljo_mcp/models/config.py` | `meta_data` (JSON) | 0 writes, 0 reads |

### Ghost Config Keys to Remove (6)

In `src/giljo_mcp/context_manager.py` ROLE_CONFIG_FILTERS, these keys are referenced but NOTHING in the codebase ever writes them to `config_data`:
- `deployment_modes`
- `known_issues`
- `api_docs`
- `documentation_style`
- `critical_features`
- `test_commands`

### Code References to Clean Up

1. **`src/giljo_mcp/tools/context_tools/get_product_context.py:113`** — Remove `include_metadata` parameter and `product.meta_data` reference
2. **`src/giljo_mcp/setup/state_manager.py:190`** — Remove `"meta_data": {}` from default state template
3. **`src/giljo_mcp/models/config.py`** — `SetupState.to_dict()` — Remove `meta_data` from serialization
4. **`src/giljo_mcp/context_manager.py`** — ROLE_CONFIG_FILTERS — Remove 6 ghost keys
5. **`src/giljo_mcp/context_manager.py`** — `validate_config_data()` — Remove validation for ghost keys

### VisionDocument.meta_data (Separate Decision)

`VisionDocument.meta_data` is write-only (written in `vision_document_repository.py:112`, never read). Keep it for now — future vision doc enhancements may use it. If the agent finds it truly useless, remove it too.

## Implementation Plan

### Phase 1: Migration (Alembic)
1. Create incremental migration `0840a_drop_dead_meta_data_columns`
2. Include idempotency guards (check column exists before dropping)
3. Drop columns: `template_archives.meta_data`, `products.meta_data`, `tasks.meta_data`, `git_configs.meta_data`, `git_commits.meta_data`, `setup_state.meta_data`, `optimization_metrics.meta_data`

### Phase 2: Model Updates
1. Remove `meta_data` column definitions from all 7 model classes
2. Remove `meta_data` from any `to_dict()` or serialization methods on these models

### Phase 3: Code Cleanup
1. Remove ghost keys from `context_manager.py` ROLE_CONFIG_FILTERS
2. Remove ghost key validation from `validate_config_data()`
3. Remove `include_metadata` parameter from `get_product_context.py`
4. Remove `meta_data: {}` init from `state_manager.py`

### Phase 4: Test Updates
1. Search ALL test files for references to these dead columns
2. Remove any test assertions on dead `meta_data` fields
3. Run full test suite to verify nothing breaks

### Phase 5: Verify
1. `ruff check src/ api/` — zero lint issues
2. `pytest tests/ -x --timeout=30` — all tests pass
3. Grep for any remaining references to removed columns

## Testing Requirements

- Run `grep -r "meta_data" tests/` to find any test references to dead columns
- Expected: minimal test impact since these columns were never used
- `tests/unit/test_project_service_helpers.py` may reference Product.meta_data — update if needed

## Success Criteria

- [ ] 7 dead `meta_data` columns removed from models
- [ ] Alembic migration created with idempotency guards
- [ ] 6 ghost config keys removed from context_manager.py
- [ ] All code references to dead columns cleaned up
- [ ] `ruff check src/ api/` passes clean
- [ ] All tests pass
- [ ] Committed to `feature/0840-jsonb-normalization` branch

## Rollback Plan

Revert the migration: `alembic downgrade -1`. Revert git commit.

## Coding Principles (from HANDOVER_INSTRUCTIONS.md)

- TDD: Write test first if adding new behavior (this handover is removal-only, so verify existing tests pass)
- Clean Code: DELETE old code, don't comment out
- Tenant isolation: Not directly relevant (removing columns)
- No AI signatures in commits
- Pre-commit hooks: never bypass with --no-verify
- Search before you build: verify no hidden usages before deleting
- Trace full chain: model → repository → service → tool → endpoint → frontend → test

---

## Chain Execution Instructions

### Step 1: Create Chain Log
Create `prompts/0840_chain/chain_log.json` with the full 6-session structure (template provided in prompt file).

### Step 2: Mark Session Started
Update session 0840a: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Complete all phases above using subagents (database-expert for migration, tdd-implementor for test verification).

### Step 4: Update Chain Log
Before spawning next terminal, update your session:
- `tasks_completed`: List what you actually did
- `deviations`: Any changes from plan
- `blockers_encountered`: Issues hit
- `notes_for_next`: Critical info for next agent
- `summary`: 2-3 sentence summary
- `status`: "complete"
- `completed_at`: "<timestamp>"

### Step 5: Commit Work
```bash
git add -A
git commit -m "chore: Drop 7 dead meta_data columns and 6 ghost config keys (0840a)"
```

### Step 6: Spawn Next Terminal
**Use Bash tool to EXECUTE (don't just print!):**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0840b - Message Normalization\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0840b. READ FIRST: F:\GiljoAI_MCP\handovers\0840b_message_normalization.md then READ: F:\GiljoAI_MCP\prompts\0840_chain\0840b_prompt.md for chain instructions. You are on branch feature/0840-jsonb-normalization. Use database-expert and tdd-implementor subagents.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS! Only ONE agent should spawn the next terminal.**
