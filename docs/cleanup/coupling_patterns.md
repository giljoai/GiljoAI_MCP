# Coupling Patterns Analysis: High-Dependency Hub Files

**Version:** 1.0
**Created:** 2026-02-06
**Status:** Research Complete
**Source:** Deep Researcher Agent - Serena symbolic analysis

---

## Executive Summary

This document analyzes the coupling patterns in GiljoAI MCP four highest-dependency hub files.

### Key Findings

| File | Dependents | Coupling Type | Refactor Priority |
|------|-----------|---------------|-------------------|
| models/__init__.py | 101 | Convenience (Barrel) | Low - Migration path exists |
| api/app.py | 72 | Necessary (Test infra) | None - Working as designed |
| database.py | 57 | Necessary (DI pattern) | None - Core architecture |
| auth/dependencies.py | 47 | Necessary (FastAPI DI) | None - Core architecture |

**Verdict:** All four hubs exhibit primarily **necessary architectural coupling**.

---

## 1. models/__init__.py (101 dependents)

**Pattern Type:** Barrel/Re-export Pattern
**Coupling Category:** Convenience Coupling

Re-exports 35+ symbols from 11 domain-specific modules with 427+ legacy imports.

**Migration Path:** Documented in file header (Handover 0128a):
- New files: Use modular imports
- Modified files: Update while editing
- Untouched: Leave as-is

**Recommendation:** No action needed - migration guidance exists.

---

## 2. api/app.py (72 dependents)

**Pattern Type:** Application Factory
**Coupling Category:** Necessary Architectural (Test Infrastructure)

All 72 references are **exclusively in test files** creating TestClient instances.

**Recommendation:** No action needed - correct pattern for testable FastAPI apps.

---

## 3. database.py (57 dependents)

**Pattern Type:** Database Manager Singleton
**Coupling Category:** Necessary Architectural (Database Layer)

| Category | Count |
|----------|-------|
| Scripts | 6 |
| MCP Tools | 1 |
| Test Fixtures | 3 |
| Integration Tests | 5 |

API endpoints use get_db_session via dependency injection, not direct access.

**Recommendation:** No action needed - clean DI/direct access separation.

---

## 4. auth/dependencies.py (47 dependents)

**Pattern Type:** FastAPI Dependency Injection
**Coupling Category:** Necessary Architectural (Auth Layer)

| Function | Dependents |
|----------|-----------|
| get_db_session | ~40 endpoints |
| get_current_active_user | ~40 endpoints |
| require_admin | ~10 endpoints |

**Recommendation:** No action needed - idiomatic FastAPI design.

---

## Coupling Categories Summary

### Necessary Architectural
- database.py - Core singleton
- auth/dependencies.py - FastAPI DI pattern
- api/app.py - Test infrastructure

### Convenience (Barrel Pattern)
- models/__init__.py - Migration guidance exists

### Accidental
- None identified in hub files

---

## Recommendations for 0700 Cleanup Series

1. **Do NOT refactor these hub files** - architectural necessity
2. **Focus cleanup efforts on:**
   - 271 orphan modules (zero dependents)
   - 45 DEPRECATED markers
   - 43 TODO markers
   - 49 circular dependencies
3. **models/__init__.py**: Gradual migration when editing files

---

| Version | Date | Author |
|---------|------|--------|
| 1.0 | 2026-02-06 | Deep Researcher Agent |
