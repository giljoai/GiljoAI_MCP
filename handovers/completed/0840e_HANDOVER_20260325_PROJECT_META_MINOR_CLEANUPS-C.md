# Handover 0840e: Project meta_data + Minor Cleanups

**Date:** 2026-03-25
**From Agent:** Orchestrator (JSONB Normalization Planning Session)
**To Agent:** Next Session (database-expert + tdd-implementor)
**Priority:** Medium
**Estimated Complexity:** 4-6 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Task Summary

Normalize `Project.meta_data` by extracting `cancellation_reason` and `deactivation_reason` into proper columns. Remove redundant closeout data from meta_data. Promote `DownloadToken.meta_data.filename` to a proper column. Bulk-convert remaining plain JSON columns to JSONB for consistency and performance.

**Prerequisite:** Handover 0840d (User Settings Normalization) must be complete. Check chain log.

## Context and Background

`Project.meta_data` is the last actively-used `meta_data` column (besides AgentTemplate which we're keeping). It stores cancellation/deactivation reasons that should be proper columns, plus closeout data that's redundant with `orchestrator_summary` and `closeout_executed_at`. It also has ghost reads for `path`, `git_branch`, `test_coverage` that nothing writes.

## Technical Details

### Project.meta_data Changes

**New columns on `projects`:**
```sql
ALTER TABLE projects ADD COLUMN cancellation_reason TEXT;
ALTER TABLE projects ADD COLUMN deactivation_reason TEXT;
```

**Backfill:**
```sql
UPDATE projects SET cancellation_reason = meta_data->>'cancellation_reason'
  WHERE meta_data->>'cancellation_reason' IS NOT NULL;
UPDATE projects SET deactivation_reason = meta_data->>'deactivation_reason'
  WHERE meta_data->>'deactivation_reason' IS NOT NULL;
```

**Drop:** `projects.meta_data` column after code updated.

**Redundant data in meta_data (safe to lose):**
- `closeout.summary` → already in `projects.orchestrator_summary`
- `closeout.completed_at` → already in `projects.closeout_executed_at`
- `closeout.key_outcomes`, `closeout.decisions_made` → already in `product_memory_entries`

**Ghost reads to clean up:**
- `project_service.py:1789-1791` reads `path` and `git_branch` from meta_data — nothing writes these. Remove the reads.
- `project_closeout.py:209,491` reads `test_coverage` — nothing writes this. Remove.

### DownloadToken.meta_data Changes

```sql
ALTER TABLE download_tokens ADD COLUMN filename VARCHAR(255);
```

Backfill from `meta_data->>'filename'`, then drop `meta_data`.

### JSON → JSONB Bulk Migration

Convert all remaining plain `JSON` columns to `JSONB` for binary storage efficiency and operator support. These are:

| Table | Column | Current Type |
|-------|--------|-------------|
| `agent_templates` | `variables` | JSON |
| `agent_templates` | `behavioral_rules` | JSON |
| `agent_templates` | `success_criteria` | JSON |
| `agent_templates` | `tags` | JSON |
| `agent_templates` | `meta_data` | JSON |
| `template_archives` | `variables` | JSON |
| `template_archives` | `behavioral_rules` | JSON |
| `template_archives` | `success_criteria` | JSON |
| `template_usage_stats` | `variables_used` | JSON |
| `template_usage_stats` | `augmentations_applied` | JSON |
| `agent_executions` | `result` | JSON |
| `configurations` | `value` | JSON |
| `discovery_config` | `settings` | JSON |
| `git_configs` | `webhook_events` | JSON |
| `git_configs` | `ignore_patterns` | JSON |
| `git_configs` | `git_config_options` | JSON |
| `git_commits` | `files_changed` | JSON |
| `git_commits` | `webhook_response` | JSON |
| `vision_documents` | `meta_data` | JSON |
| `mcp_context_index` | `keywords` | JSON |

**Migration:** `ALTER TABLE x ALTER COLUMN y TYPE JSONB USING y::jsonb;`

### Files That Must Change

**Models:**
- `src/giljo_mcp/models/projects.py` — Add `cancellation_reason`, `deactivation_reason` columns. Remove `meta_data`.
- `src/giljo_mcp/models/config.py` — Add `filename` to DownloadToken. Remove `meta_data`. Update JSON→JSONB types.
- `src/giljo_mcp/models/templates.py` — Update JSON→JSONB column types

**Services:**
- `src/giljo_mcp/services/project_service.py` — Use new columns instead of `meta_data["cancellation_reason"]` etc. Remove ghost reads for `path`, `git_branch`.
- `src/giljo_mcp/services/project_closeout.py` — Remove ghost read for `test_coverage`
- `src/giljo_mcp/services/service_responses.py` — Update ProjectDataResponse, ProjectMinimalResponse to use new columns

**Other:**
- `src/giljo_mcp/tools/tool_accessor.py` → `download_tokens.py` — Use `filename` column

## Implementation Plan

### Phase 1: Database Migration
1. Add new columns to projects and download_tokens
2. Backfill data
3. JSON→JSONB bulk conversion
4. Drop old meta_data columns

### Phase 2: Model + Service Updates
1. Update models
2. Update project_service.py
3. Update project_closeout.py
4. Update download_tokens.py
5. Update response schemas

### Phase 3: Test Updates
- `tests/unit/test_project_service_helpers.py` — References meta_data handling
- `tests/services/test_project_service_closeout_data.py`
- Any tests checking project meta_data in API responses

### Phase 4: Verify
1. Lint clean, all tests pass
2. Project cancellation/deactivation flows work
3. Download token flows work

## Success Criteria

- [ ] `cancellation_reason` and `deactivation_reason` columns on projects
- [ ] `filename` column on download_tokens
- [ ] `meta_data` dropped from projects and download_tokens
- [ ] All plain JSON columns converted to JSONB
- [ ] Ghost reads removed
- [ ] All tests pass
- [ ] `ruff check` clean
- [ ] Committed to `feature/0840-jsonb-normalization`

## Rollback Plan

`alembic downgrade -1`. Git revert.

## Coding Principles

- TDD, Clean Code, Tenant isolation, Exception-based errors
- Trace full chain: model → service → endpoint → frontend → test

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Verify 0840d is `complete`. Read `notes_for_next`. Also check if orchestrator left additional instructions.

### Step 2-4: Standard chain workflow

### Step 5: Commit Work
```bash
git add -A
git commit -m "feat: Normalize Project meta_data + JSON→JSONB bulk migration (0840e)"
```

### Step 6: Spawn Next Terminal
**Use Bash tool to EXECUTE (don't just print!):**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0840f - Validation + Schema Enforcement\" --tabColor \"#F44336\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0840f. READ FIRST: F:\GiljoAI_MCP\handovers\0840f_validation_schema_enforcement.md then READ: F:\GiljoAI_MCP\prompts\0840_chain\0840f_prompt.md for chain instructions. You are on branch feature/0840-jsonb-normalization. Use tdd-implementor and backend-tester subagents.\"' -Verb RunAs"
```

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
