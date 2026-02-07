# Handover 0705: Cleanup Models Core

**Date:** 2026-01-27
**From Agent:** orchestrator-coordinator
**To Agent:** database-expert / tdd-implementor
**Priority:** High
**Estimated Complexity:** 3-4 hours
**Status:** Not Started
**Depends On:** 0704 (Models Base)

---

## Task Summary

Clean up **core domain models**: Products and Projects. These are fundamental data structures with moderate-to-high dependent counts.

**Risk Level:** High (central domain models)

**Scope:** 4 files

---

## Files In Scope

| File | Est. Lines | Risk | Dependents |
|------|-----------|------|------------|
| `src/giljo_mcp/models/products.py` | ~200 | High | ~30 |
| `src/giljo_mcp/models/projects.py` | ~150 | High | ~40 |
| `src/giljo_mcp/models/product_memory_entry.py` | ~80 | Medium | ~10 |
| Related tests in `tests/models/` | - | - | - |

---

## Known Issues (From CLAUDE.md)

**Product Model:**
- `Product.product_memory.sequential_history` JSONB is DEPRECATED
- Use `product_memory_entries` table via `ProductMemoryRepository` instead

**Project Model:**
- `Project.description` = user input (requirements)
- `Project.mission` = AI-generated plan
- Ensure field naming conventions are followed

---

## Cleanup Checklist

### products.py

| Check | Action |
|-------|--------|
| DEPRECATED fields | Document deprecation in docstring; plan removal |
| product_memory JSONB | Verify migration to normalized table |
| Relationships | Verify FK cascades are correct |
| Column types | Ensure appropriate sizes |

### projects.py

| Check | Action |
|-------|--------|
| Soft delete fields | Verify `deleted_at` pattern |
| Field naming | `description` vs `mission` distinction |
| Status enum | Verify all statuses used |
| Relationships | Verify cascade behaviors |

### product_memory_entry.py

| Check | Action |
|-------|--------|
| Normalized structure | Verify FK to products |
| CASCADE behavior | Verify product delete cascades |
| SET NULL behavior | Verify project delete sets null |
| Indexes | Verify query performance indexes |

---

## Implementation Plan

### Phase 1: Pre-Analysis (30 min)
1. Review DEPRECATED markers in each file
2. Query for all usages of deprecated fields
3. Document migration status

### Phase 2: products.py Cleanup (1 hr)
1. Lint and format
2. Add deprecation notices to JSONB fields
3. Verify relationships
4. Run product tests

### Phase 3: projects.py Cleanup (1 hr)
1. Lint and format
2. Verify soft delete implementation
3. Check status enum completeness
4. Run project tests

### Phase 4: product_memory_entry.py Cleanup (45 min)
1. Lint and format
2. Verify normalized table structure
3. Test cascade behaviors
4. Run memory tests

### Phase 5: Update Index
```sql
UPDATE cleanup_index
SET status = 'cleaned', last_cleaned_at = NOW()
WHERE file_path LIKE 'src/giljo_mcp/models/products%'
   OR file_path LIKE 'src/giljo_mcp/models/projects%'
   OR file_path LIKE 'src/giljo_mcp/models/product_memory%';
```

---

## Testing Requirements

```bash
# Model-specific tests
pytest tests/models/test_products.py -v
pytest tests/models/test_projects.py -v
pytest tests/models/test_product_memory.py -v

# Service integration tests
pytest tests/services/test_product_service.py -v
pytest tests/services/test_project_service.py -v
```

---

## Success Criteria

- [ ] All DEPRECATED fields documented with removal timeline
- [ ] No TODO markers remaining
- [ ] Field naming conventions verified
- [ ] Cascade behaviors tested
- [ ] All model tests pass
- [ ] All service tests pass
- [ ] cleanup_index updated

---

## Next Handover

**0706_cleanup_models_agents.md** - CRITICAL: Clean up agent_identity.py (highest dependent count in models).
