# Plan: 0390 - 360 Memory JSONB to Normalized Table Migration

**Planning Date:** 2026-01-18
**Model:** 0387 Series (JSONB Normalization Pattern)
**Estimated Complexity:** 16-22 hours across 4 sub-handovers
**Risk Level:** MEDIUM (Dev mode - no production users)
**Execution Mode:** Multi-Terminal Chain (see prompts/0390_chain/)

---

## Executive Summary

Migrate `Product.product_memory.sequential_history[]` JSONB array to a normalized `product_memory_entries` table with proper foreign key constraints, enabling:

1. **Referential integrity** - ON DELETE CASCADE/SET NULL for products/projects
2. **Query performance** - Proper indexes vs JSONB array iteration
3. **Multi-tenant isolation** - tenant_key column with FK constraints
4. **Production-grade commercialization** - No more JSONB array manipulation

**Key Simplifications (Dev Mode):**
- No dual-write phase (no production users to protect)
- No backward compatibility fallback
- Direct table-only from Phase 2
- JSONB deprecated immediately after Phase 3

---

## Current State Analysis

### WRITE Locations (5 files, 7 call sites)

| File | Lines | Function | Writes |
|------|-------|----------|--------|
| `tools/write_360_memory.py` | 200-218 | `write_360_memory()` | sequential_history entry |
| `tools/project_closeout.py` | 148-170 | `close_project_and_update_memory()` | sequential_history entry |
| `services/product_service.py` | 975-992 | `update_git_integration()` | git_integration config |
| `services/product_service.py` | 1328-1332 | `_ensure_product_memory_initialized()` | default structure |
| `services/project_service.py` | 2179-2192 | `nuclear_delete_project()` | deleted_by_user flag |
| `services/project_service.py` | 2265-2275 | `_purge_project_records()` | deleted_by_user flag |

### READ Locations (12 files)

| File | Function | Reads |
|------|----------|-------|
| `tools/context_tools/get_360_memory.py` | `get_360_memory()` | sequential_history with pagination |
| `tools/context_tools/get_git_history.py` | `get_git_history()` | git_commits from all entries |
| `mission_planner.py` | `_get_360_memory_summary()` | last N entries |
| `thin_prompt_generator.py` | `_build_360_memory_section()` | sequential_history |
| `services/product_service.py` | Multiple methods | product_memory fields |
| `services/project_service.py` | Delete methods | sequential_history for marking |
| `frontend/stores/products.js` | `handleProductMemoryUpdated()` | WebSocket updates |
| `frontend/components/CloseoutModal.vue` | `loadMemoryEntries()` | Filter by project_id |
| `prompt_generation/memory_instructions.py` | `generate_context()` | History length |
| `tools/context_tools/framing_helpers.py` | `apply_rich_entry_framing()` | Entry formatting |
| `tools/context_tools/fetch_context.py` | Category dispatcher | Calls get_360_memory |
| `models/products.py` | Helper methods | product_memory access |

### API/Frontend Exposure

- **REST**: GET/PUT /products/{id}, POST /git-integration, POST /complete
- **Schemas**: ProductCreate, ProductUpdate, ProductResponse
- **WebSocket**: product:memory:updated, product:learning:added
- **Components**: CloseoutModal.vue, ManualCloseoutModal.vue, GitIntegrationCard.vue

---

## Target State: Normalized Schema

### Table: `product_memory_entries`

```sql
CREATE TABLE product_memory_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_key VARCHAR(36) NOT NULL,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- Core fields (from both write_360_memory and close_project)
    sequence INTEGER NOT NULL,
    entry_type VARCHAR(50) NOT NULL,  -- 'project_closeout', 'project_completion', 'handover_closeout'
    source VARCHAR(50) NOT NULL,       -- 'closeout_v1', 'write_360_memory_v1', 'migration_backfill'
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Content
    project_name VARCHAR(255),
    summary TEXT,
    key_outcomes JSONB DEFAULT '[]',
    decisions_made JSONB DEFAULT '[]',
    git_commits JSONB DEFAULT '[]',

    -- Extended metadata (project_closeout only)
    deliverables JSONB DEFAULT '[]',
    metrics JSONB DEFAULT '{}',
    priority INTEGER DEFAULT 3,
    significance_score FLOAT DEFAULT 0.5,
    token_estimate INTEGER,
    tags JSONB DEFAULT '[]',

    -- Author tracking (write_360_memory only)
    author_job_id UUID,
    author_name VARCHAR(255),
    author_type VARCHAR(50),

    -- Soft-delete tracking (project deletion marks, not removes)
    deleted_by_user BOOLEAN DEFAULT FALSE,
    user_deleted_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    UNIQUE (product_id, sequence)
);

-- Indexes
CREATE INDEX idx_pme_tenant_product ON product_memory_entries(tenant_key, product_id);
CREATE INDEX idx_pme_project ON product_memory_entries(project_id) WHERE project_id IS NOT NULL;
CREATE INDEX idx_pme_sequence ON product_memory_entries(product_id, sequence DESC);
CREATE INDEX idx_pme_type ON product_memory_entries(entry_type);
CREATE INDEX idx_pme_deleted ON product_memory_entries(deleted_by_user) WHERE deleted_by_user = TRUE;
```

---

## Sub-Handover Series

| Handover | Scope | Hours | Prerequisite | Tab Color |
|----------|-------|-------|--------------|-----------|
| **0390a** | Add table + model + repository + backfill | 6-8h | None | Green `#4CAF50` |
| **0390b** | Switch ALL reads to table | 6-8h | 0390a complete | Blue `#2196F3` |
| **0390c** | Stop JSONB writes, use table only | 6-8h | 0390b complete | Purple `#9C27B0` |
| **0390d** | Deprecate JSONB column + cleanup + docs | 3-4h | 0390c complete | Orange `#FF9800` |

**Total: 21-28 hours across 4 handovers**

---

## Phase 0: Safety Net (FIRST ACTION IN 0390a)

**CRITICAL - Do this before ANY code changes:**

```bash
# 1. Create feature branch
git checkout -b 0390-360-memory-normalization

# 2. Database backup
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/pg_dump.exe -U postgres giljo_mcp > backup_pre_0390.sql

# 3. Document baseline
pytest tests/ --tb=no -q | grep -E "passed|failed"
# Record: Total test count
```

---

## Handover 0390a: Add Table + Backfill (6-8 hours)

### Scope
Create normalized table, SQLAlchemy model, repository with CRUD operations, and backfill existing JSONB data.

### TDD Approach
1. Write repository CRUD tests first (RED)
2. Implement model and repository (GREEN)
3. Create migration with backfill
4. Run tests (should all pass)

### Files to CREATE
| File | Purpose |
|------|---------|
| `src/giljo_mcp/models/product_memory_entry.py` | SQLAlchemy model |
| `src/giljo_mcp/repositories/product_memory_repository.py` | CRUD operations |
| `alembic/versions/xxxx_add_product_memory_entries.py` | Migration + backfill |
| `tests/repositories/test_product_memory_repository.py` | TDD tests |

### Success Criteria
- [ ] Table exists in database
- [ ] Model properly mapped
- [ ] Repository CRUD works
- [ ] Backfill migrates all existing JSONB entries
- [ ] COUNT(table entries) == COUNT(JSONB entries)
- [ ] All new tests pass (10+ tests)

---

## Handover 0390b: Switch Reads to Table (6-8 hours)

### Scope
Modify all 12 READ locations to query `product_memory_entries` table instead of JSONB.

### Files to MODIFY
| File | Changes |
|------|---------|
| `tools/context_tools/get_360_memory.py` | Query table with pagination |
| `tools/context_tools/get_git_history.py` | Query table for git_commits |
| `mission_planner.py` | Query table for last N entries |
| `thin_prompt_generator.py` | Query table for 360 memory section |
| `services/product_service.py` | Update memory access methods |
| `services/project_service.py` | Query table for deletion marking |
| `frontend/stores/products.js` | Parse new WebSocket payload |
| `frontend/components/CloseoutModal.vue` | API response format |
| `prompt_generation/memory_instructions.py` | Query table |
| `tools/context_tools/framing_helpers.py` | Entry formatting |
| `tools/context_tools/fetch_context.py` | Category dispatcher |
| API response serializers | Include table data |

### Success Criteria
- [ ] All API responses use table data
- [ ] Query performance equal or better
- [ ] WebSocket events work correctly
- [ ] Frontend displays data correctly
- [ ] All existing E2E tests pass

---

## Handover 0390c: Stop JSONB Writes (6-8 hours)

### Scope
Modify all 7 WRITE locations to insert into table instead of JSONB array.

### Files to MODIFY
| File | Changes |
|------|---------|
| `tools/write_360_memory.py` | Insert into table |
| `tools/project_closeout.py` | Insert into table |
| `services/product_service.py` | Remove git config JSONB writes |
| `services/project_service.py` | Update table rows for deletion marking |

### Success Criteria
- [ ] Zero JSONB writes for 360 memory entries
- [ ] Table contains all new entries
- [ ] Soft-delete marking works via table UPDATE
- [ ] All tests pass

---

## Handover 0390d: Deprecate JSONB Column (3-4 hours)

### Scope
Mark column deprecated, update docs, prepare for v4.0 removal.

### Tasks
1. Add deprecation comment to `Product.product_memory` column
2. Update CLAUDE.md with deprecation notice
3. Remove unused JSONB access code
4. Run full regression test suite
5. Manual E2E testing
6. Update handover catalogue

### Success Criteria
- [ ] Column marked deprecated in code
- [ ] No code reads sequential_history from JSONB
- [ ] All tests pass
- [ ] CLAUDE.md updated
- [ ] Documentation complete

---

## Files Index (Complete)

### NEW Files to Create (4)
1. `src/giljo_mcp/models/product_memory_entry.py`
2. `src/giljo_mcp/repositories/product_memory_repository.py`
3. `alembic/versions/xxxx_add_product_memory_entries.py`
4. `tests/repositories/test_product_memory_repository.py`

### Backend Files to MODIFY (10)
1. `src/giljo_mcp/models/__init__.py` - Export new model
2. `src/giljo_mcp/tools/write_360_memory.py` - Table writes
3. `src/giljo_mcp/tools/project_closeout.py` - Table writes
4. `src/giljo_mcp/tools/context_tools/get_360_memory.py` - Table reads
5. `src/giljo_mcp/tools/context_tools/get_git_history.py` - Table reads
6. `src/giljo_mcp/tools/context_tools/fetch_context.py` - Updated dispatcher
7. `src/giljo_mcp/services/product_service.py` - Table operations
8. `src/giljo_mcp/services/project_service.py` - Table soft-delete
9. `src/giljo_mcp/mission_planner.py` - Table reads
10. `src/giljo_mcp/thin_prompt_generator.py` - Table reads

### Frontend Files to MODIFY (3)
1. `frontend/src/stores/products.js` - WebSocket handler
2. `frontend/src/components/CloseoutModal.vue` - API response
3. `frontend/src/components/ManualCloseoutModal.vue` - API response

### API Files to MODIFY (2)
1. `api/endpoints/products/crud.py` - Response serialization
2. `api/endpoints/products/git_integration.py` - Git config handling

### Test Files to CREATE/MODIFY (4+)
1. `tests/repositories/test_product_memory_repository.py` - NEW
2. `tests/tools/test_write_360_memory_table.py` - NEW
3. `tests/tools/test_get_360_memory_table.py` - NEW
4. `tests/integration/test_360_memory_e2e.py` - NEW

---

## Rollback Plan

### Pre-Work Safety Net
- Branch: `0390-360-memory-normalization`
- Backup: `backup_pre_0390.sql`

### Per-Phase Rollback
| Phase | Rollback |
|-------|----------|
| 0390a | Drop table, revert model/repo files |
| 0390b | Revert read files to JSONB access |
| 0390c | Re-enable JSONB writes |
| 0390d | No permanent changes to revert |

---

## Multi-Terminal Chain Execution

**To launch the chain, run this command:**

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0390a - Add Memory Table\" --tabColor \"#4CAF50\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0390a. Read F:\GiljoAI_MCP\prompts\0390_chain\0390a_prompt.md for instructions. Use Task subagents (database-expert, tdd-implementor) to complete all phases. When done, spawn next terminal per the prompt file.\"' -Verb RunAs"
```

### Chain Overview
```
0390a (Green) --> 0390b (Blue) --> 0390c (Purple) --> 0390d (Orange)
    |                  |                 |                  |
  Table            Read from         Write to          Deprecate
  + Model          Table Only        Table Only         JSONB
```

---

## Benefits After Completion

1. **Referential integrity** - FK constraints enforce data consistency
2. **Query performance** - Indexed table queries vs JSONB iteration
3. **Cascade behavior** - Product deletion cascades, project deletion soft-marks
4. **Multi-tenant security** - Proper tenant_key column isolation
5. **Production-grade** - Ready for commercialization

---

## Verification Checklist (Final)

### Functional
- [ ] 360 memory entries display correctly in dashboard
- [ ] Closeout creates new entry in table
- [ ] write_360_memory creates entry in table
- [ ] Project deletion marks entries (not deletes)
- [ ] Product deletion cascades entries

### Quality
- [ ] All tests pass (100% green)
- [ ] Coverage >80%
- [ ] No linting errors
- [ ] No TypeScript errors (frontend)

### Documentation
- [ ] CLAUDE.md updated
- [ ] Handover 0390 marked complete in catalogue
- [ ] All phase handovers archived to completed/

---

**Document Version**: 1.0
**Last Updated**: 2026-01-18
**Author**: Claude Opus 4.5
