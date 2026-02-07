# Dependency Visualization Methodology

**Generated:** 2026-02-06
**Source Analysis:** Deep Researcher Agent investigating discrepancy between 314 vs 101 dependents for models/__init__.py

## Executive Summary

The discrepancy between the two dependent counts (314 in HTML visualization vs 101 in handover analysis) is due to **different file scopes** being analyzed. The visualization includes test files and documentation, while the handover analysis focused on production code only.

## Data Source Comparison

| Source | Total Nodes | Includes Tests | Includes Docs | models/__init__.py Dependents |
|--------|-------------|----------------|---------------|-------------------------------|
| `docs/cleanup/dependency_graph.json` | 2,748 | Yes (782 files) | Yes (1,321 files) | **314** |
| `handovers/0700_series/dependency_graph_data.json` | 448 | No | No | **101** |

## What Each Script Counts

### Build Script (`scripts/build_dep_graph_part1.py`)

The visualization script counts as a "dependent" any file that contains an import statement matching the target module. It:

1. **Scans all file types:**
   - Python files (`.py`)
   - Frontend files (`.vue`, `.js`, `.ts`)
   - Documentation files (`.md`)

2. **Includes all directories:**
   - `src/giljo_mcp/` (core code)
   - `api/` (API endpoints)
   - `frontend/src/` (frontend components)
   - `tests/` (test files)
   - `frontend/__tests__/` (frontend tests)
   - `docs/` (documentation)
   - `handovers/` (handover documents)

3. **Uses regex matching for imports:**
   - Python: `^from\s+([\w.]+)\s+import` and `^import\s+([\w.]+)`
   - Vue/JS/TS: `import\s+.*?\s+from\s+["']([^"']+)["']`

4. **Layer classification:**
   - Files with `/tests/` or `__tests__` = test
   - Files with `.spec.js` or `.spec.ts` = test
   - Files with `test_` prefix = test
   - Files with `/docs/` or `/handovers/` = docs
   - Files ending in `.md` (outside src/api) = docs
   - Files in `frontend/src/` = frontend
   - Files in `src/giljo_mcp/models/` = model
   - Files in `src/giljo_mcp/services/` = service
   - Files in `src/giljo_mcp/repositories/` = model
   - Files in `src/giljo_mcp/config/` = config
   - Files in `/api/` = api
   - Everything else in `src/giljo_mcp/` = api

### Handover Analysis (`handovers/0700_series/dependency_graph_data.json`)

The handover analysis appears to have been generated with a different scope, counting only production code:

- **No test files** (test layer = 0 files)
- **No documentation files** (docs layer = 0 files)
- Focused on: model, service, api, frontend, config layers only

## Reconciliation: Why 314 vs 101?

The 213 additional dependents in the visualization (314 - 101 = 213) come from:

| File Type | Estimated Count | Example |
|-----------|-----------------|---------|
| Test files | ~160-180 | `tests/services/test_auth_service.py` imports models |
| Frontend test specs | ~20-30 | `frontend/__tests__/*.spec.js` |
| Documentation | ~0-5 | Docs rarely have code imports |

**Key Insight:** Test files legitimately import `models/__init__.py` to create test fixtures and verify model behavior. This is expected and correct.

## Which Methodology is More Accurate for Architecture Assessment?

**For refactoring impact analysis: Use 101 (production-only)**
- Test files will update automatically when models change
- Tests are not "coupled" in the architectural sense
- Refactoring effort estimates should focus on production code

**For understanding actual usage: Use 314 (all files)**
- Shows true breadth of model usage
- Helps identify which models have most test coverage
- Useful for migration planning (tests must also be updated)

## Recommendation

For the 0700 Code Cleanup Series, the **101 dependents** figure from `dependency_analysis.json` is the appropriate metric because:

1. It measures production code coupling (what matters for refactoring)
2. It excludes tests which will be updated as a consequence of changes
3. It excludes docs which don't execute code
4. It aligns with the architecture analysis conclusions

However, the **314 dependents** visualization is valuable for:
- Understanding total refactoring scope (including test updates)
- Identifying heavily-tested modules
- Planning migration timelines

## Files Analyzed

| File | Purpose |
|------|---------|
| `scripts/build_dep_graph_part1.py` | Full graph builder (all files) |
| `scripts/update_dependency_graph.py` | Updates HTML with new JSON data |
| `docs/cleanup/dependency_graph.json` | Data for HTML visualization (2,748 nodes) |
| `handovers/0700_series/dependency_graph_data.json` | Handover analysis data (448 nodes) |
| `handovers/0700_series/dependency_analysis.json` | High-risk file report |
| `docs/cleanup/HUB_FILES_ANALYSIS.md` | Generated hub analysis (uses 314 figure) |

## Layer Distribution Comparison

### Visualization Data (2,748 nodes)
| Layer | Count |
|-------|-------|
| api | 442 |
| config | 1 |
| docs | 1,321 |
| frontend | 159 |
| model | 24 |
| service | 19 |
| test | 782 |

### Handover Data (448 nodes)
| Layer | Count |
|-------|-------|
| api | 107 |
| config | 3 |
| frontend | 180 |
| model | 20 |
| service | 138 |

**Note:** The handover data has more "service" layer files because some files classified as "api" in the visualization are classified as "service" in the handover analysis.

---

## Conclusion

Both methodologies are valid for different purposes:
- **314 dependents** = Total usage including tests and docs
- **101 dependents** = Production code coupling only

For architecture decisions and refactoring planning, the **101 dependents** figure is more actionable because it represents the code that actually needs to change for a production deployment.
