# 0750 Final Scrub Roadmap

**Date**: 2026-02-11
**Series**: 0750a-c (3 sessions)
**Parent**: Post-0745 audit + cleanup/post-0745-audit-fixes branch (commit 7f0cdf33)
**Branch**: `cleanup/post-0745-audit-fixes` (continue existing branch)
**Goal**: Achieve "clean product" status - zero redundant code, zero stale patterns

---

## Status Tracker

| Session | Theme | Status | Color |
|---------|-------|--------|-------|
| 0750a | Remaining Backend Cleanup | PENDING | Green #4CAF50 |
| 0750b | Remaining Frontend + Dep Cleanup | PENDING | Blue #2196F3 |
| 0750c | Final Comprehensive Audit & Report | PENDING | Red #F44336 |

---

## What Was Already Done (commit 7f0cdf33)

- 78 files changed, -12,417 lines
- products/crud.py: redundant except blocks REMOVED (was 25, now 3 comment lines)
- vision_documents.py, configuration.py: partially cleaned
- 7 orphan modules deleted, 3 unused services deleted, 5 dead ConfigManager methods removed
- 41 dead API methods removed from frontend api.js
- 75 console.log removed from top 10 files
- 83 MCPAgentJob refs fixed across 14 doc files
- 17 dead test files deleted

## What Remains

### 0750a: Remaining Backend Endpoint Cleanup
- `api/endpoints/products/lifecycle.py`: 38 except blocks (redundant with global handler)
- `api/endpoints/products/vision.py`: 27 except blocks
- `api/endpoints/products/git_integration.py`: 6 except blocks
- Total: ~71 redundant except blocks across 3 files

### 0750b: Remaining Frontend Console.log + npm audit
- ~100 console.log across remaining 35 files (top 10 already cleaned)
- Run `npm audit fix` for any remaining vulnerabilities
- Verify frontend build after all removals

### 0750c: Final Comprehensive Audit
- Full codebase scan: orphans, dead functions, stale refs, zombie code
- Review all comments for TODO/FIXME/HACK markers
- Verify all v-html sanitized
- Generate final architecture score
- Archive all addressed 0700/0740 report docs

---

## Archive These Reports After All Work Done (0750c)

Move to `handovers/completed/reference/0700-0745/`:
- `handovers/0740_*.md` (all 11 files - audit is fully addressed)
- `handovers/0745_*.md` (both files - series completed)
- `handovers/0700_series/dead_code_audit.md` (addressed)
- `handovers/0700_series/cleanup_index.json` (addressed)

---

**Created**: 2026-02-11
**Owner**: Multi-terminal chain execution
