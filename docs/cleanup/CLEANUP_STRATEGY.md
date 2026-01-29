# GiljoAI MCP Code Cleanup Strategy

**Version:** 1.0
**Created:** 2026-01-27
**Status:** Planning Complete - Ready for Execution
**Source Plan:** `C:\Users\giljo\.claude\plans\delegated-pondering-cerf.md`

---

## Executive Summary

Systematic cleanup of the GiljoAI MCP codebase (~560 source files, ~665 test files) using an indexed, dependency-aware approach with incremental validation.

**Key Metrics to Address:**
| Metric | Current | Target |
|--------|---------|--------|
| Files with DEPRECATED markers | 45 | 0 |
| Files with TODO markers | 43 | 0 |
| Skip/xfail test markers | 168 | <50 |
| Test coverage | Unknown | >80% |

---

## Strategy Overview

### Guiding Principles

1. **Dependency-Aware Order**: Clean leaf nodes first, critical files last
2. **Incremental Validation**: Test after every file change
3. **Index-Driven Tracking**: Database tracks progress and dependencies
4. **Risk Classification**: Critical files get extra scrutiny

### Approach

```
Phase 1: Build Infrastructure (0700-0701)
    └── Create cleanup_index database
    └── Generate dependency visualization

Phase 2: Low-Risk Leaves (0702-0703)
    └── Utils, config, auth, logging

Phase 3: Models Bottom-Up (0704-0706)
    └── base.py → products/projects → agent_identity (CRITICAL)

Phase 4: Services Bottom-Up (0707-0708)
    └── Leaf services → Core services

Phase 5: API Endpoints (0709-0711)
    └── CRUD → Lifecycle → mcp_http (CRITICAL)

Phase 6: Frontend (0712-0714)
    └── UI components → Feature components → Core

Phase 7: Tests (Parallel Track)
    └── Fix infrastructure → Categorize skips → Resolve TODOs
```

---

## Handover Sequence

| # | Handover | Scope | Risk | Est. Hours |
|---|----------|-------|------|------------|
| 0700 | Index Creation | Database setup, scanner, indexer | Low | 4-6 |
| 0701 | Dependency Visualization | D3.js HTML graph | Low | 2-3 |
| 0702 | Utils & Config | 8 files | Low | 2-3 |
| 0703 | Auth & Logging | 6 files | Low | 2-3 |
| 0704 | Models Base | 4 files (base, enums, exceptions) | Medium | 3-4 |
| 0705 | Models Core | 4 files (products, projects) | High | 3-4 |
| 0706 | Models Agents | 2 files (agent_identity - CRITICAL) | Critical | 4-6 |
| 0707 | Services Leaf | ~5 files (git, serena, template) | Medium | 3-4 |
| 0708 | Services Core | ~5 files (orchestration, project) | High | 4-6 |
| 0709 | API Simple | ~10 CRUD endpoints | Medium | 3-4 |
| 0710 | API Lifecycle | ~10 lifecycle endpoints | High | 3-4 |
| 0711 | API MCP | mcp_http.py (CRITICAL) | Critical | 4-6 |
| 0712 | Frontend Common | icons, ui, common components | Low | 2-3 |
| 0713 | Frontend Components | feature components | Medium | 3-4 |
| 0714 | Frontend Core | api.js, stores | High | 3-4 |
| ... | Tests (Parallel) | Fix broken, categorize skips | Medium | 5-8 |

**Estimated Total:** 45-65 hours across 15-20 handovers

---

## Risk Classification

### Critical Files (50+ dependents)
- `src/giljo_mcp/models/agent_identity.py`
- `src/giljo_mcp/database.py`
- `api/mcp_http.py`

**Handling:** Extra review, backup branch, full test suite after changes.

### High-Risk Files (20-49 dependents)
- `src/giljo_mcp/services/orchestration_service.py`
- `frontend/src/api.js`

**Handling:** Layer-specific tests, manual verification.

### Medium-Risk Files (5-19 dependents)
- Most service files
- Most API endpoints

**Handling:** Standard cleanup + related tests.

### Low-Risk Files (<5 dependents)
- Utilities, config, leaf components

**Handling:** Lint, review, quick tests.

---

## Cleanup Operations (Per File)

### Automated Pass
```bash
# Python
ruff check <path> --fix
black <path>

# Frontend
npm run lint:fix
```

### Manual Review Checklist

| Check | Action |
|-------|--------|
| DEPRECATED markers | Remove code OR document removal timeline |
| TODO markers | Fix inline OR create GitHub issue |
| Unused imports | Remove (ruff catches most) |
| Unused functions | Remove if no external references |
| Hardcoded paths | Replace with `Path()` |
| Magic numbers | Extract to constants |
| Dead code | Remove unreachable branches |
| Excessive comments | Remove obvious ones |
| Proxy patterns | Eliminate unnecessary layers |
| Defensive over-checks | Remove redundant validations |

### Validation Steps
```bash
# 1. Lint passes
ruff check <file>

# 2. Related tests pass
pytest tests/<related>/ -v

# 3. No import errors
python -c "from module import *"
```

---

## Progress Tracking

### Database Schema (Handover 0700)

```sql
-- Check overall progress
SELECT
    status,
    COUNT(*) as file_count,
    SUM(deprecation_markers) as total_deprecations,
    SUM(todo_markers) as total_todos
FROM cleanup_index
GROUP BY status;

-- Check progress by layer
SELECT
    layer,
    status,
    COUNT(*) as file_count
FROM cleanup_index
GROUP BY layer, status
ORDER BY layer, status;

-- Find remaining hotspots
SELECT file_path, deprecation_markers, todo_markers
FROM cleanup_index
WHERE deprecation_markers > 0 OR todo_markers > 0
ORDER BY (deprecation_markers + todo_markers) DESC
LIMIT 20;
```

### JSON Fallback (if DB not preferred)

`docs/cleanup/cleanup_status.json`:
```json
{
  "last_updated": "2026-01-27",
  "summary": {
    "total_files": 560,
    "cleaned": 0,
    "verified": 0,
    "pending": 560
  },
  "by_layer": {
    "models": {"total": 14, "cleaned": 0},
    "services": {"total": 17, "cleaned": 0},
    "api": {"total": 100, "cleaned": 0},
    "frontend": {"total": 170, "cleaned": 0},
    "tests": {"total": 665, "cleaned": 0}
  }
}
```

---

## Test Strategy (Parallel Track)

### Current Test Health

| Issue | Count | Priority |
|-------|-------|----------|
| Skip/xfail markers | 168 | Medium |
| TODO in tests | 48 | Medium |
| Broken infra tests | 11 | High |
| Coverage unknown | - | High |

### Test Cleanup Actions

1. **Fix Infrastructure First** (11 tests):
   - Cookie persistence in auth
   - /summary/ endpoint routing

2. **Categorize Skip Markers** (168):
   - Remove if obsolete test
   - Fix if valid but broken
   - Document if intentionally skipped

3. **Resolve TODO Markers** (48):
   - Convert to cleanup_index tasks
   - Remove if obsolete

4. **Regenerate Coverage**:
   ```bash
   pytest tests/ --cov=src/giljo_mcp --cov-report=html
   ```

---

## Success Criteria

- [ ] All files indexed with dependencies mapped
- [ ] 0 DEPRECATED markers (removed or with documented removal timeline)
- [ ] 0 TODO markers in source (converted to issues or resolved)
- [ ] <20 intentional skip markers in tests (documented)
- [ ] All tests passing
- [ ] Coverage >80%
- [ ] No ruff/eslint warnings
- [ ] No regression in functionality

---

## Key Decisions

1. **Index Storage**: PostgreSQL table (cleanup_index + file_dependencies)
2. **Visualization**: Interactive D3.js graph (Handover 0701)
3. **Starting Point**: Low-risk leaves first
4. **Test Strategy**: Clean in parallel with source

---

## Reference Documents

- [Handover 0700: Index Creation](../../handovers/0700_cleanup_index_creation.md)
- [Handover 0701: Dependency Visualization](../../handovers/0701_cleanup_dependency_visualization.md)
- [Handover 0702: Utils & Config](../../handovers/0702_cleanup_utils_config.md)
- [Handover 0703: Auth & Logging](../../handovers/0703_cleanup_auth_logging.md)
- [Handover 0704: Models Base](../../handovers/0704_cleanup_models_base.md)
- [Handover 0705: Models Core](../../handovers/0705_cleanup_models_core.md)
- [Handover 0706: Models Agents (CRITICAL)](../../handovers/0706_cleanup_models_agents.md)

---

## Rollback Strategy

Each handover creates a checkpoint. If issues arise:

```bash
# Revert specific handover
git log --oneline | grep "cleanup"
git revert <commit>

# Or restore from backup branch
git checkout backup/pre-cleanup-<handover> -- <path>
```

---

## Getting Started

1. **Read this document** - Understand the strategy
2. **Execute Handover 0700** - Build the cleanup infrastructure
3. **Execute Handover 0701** - Visualize dependencies
4. **Start with 0702** - Begin cleanup with low-risk files
5. **Track progress** - Update cleanup_index after each file
6. **Validate continuously** - Run tests after every change
