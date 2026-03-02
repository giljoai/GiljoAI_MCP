# Handover 0765d: Exception Narrowing

**Date:** 2026-03-02
**Priority:** MEDIUM
**Estimated effort:** 6-8 hours
**Branch:** `0760-perfect-score`
**Chain:** `prompts/0765_chain/chain_log.json` (session 0765d)
**Depends on:** 0765a (dead code removed, clean baseline)
**Blocks:** None

---

## Objective

Narrow the safe subset of 121 `except Exception` catch-all patterns across 26 files. Research identified ~60% as intentional API boundary re-raises, ~20% as WebSocket resilience (annotated `noqa: BLE001`), and only ~20% (~20-25 instances) as genuinely safe to narrow.

**Score impact:** ~9.2 -> ~9.3
**Risk level:** MEDIUM — overly narrow catches could surface unhandled exceptions in production

---

## Pre-Conditions

1. 0765a complete — dead code removed (some catch-alls may have been in deleted code)
2. Read research findings: "~60% are API boundary re-raise patterns (intentional)"
3. Understand the project's error handling philosophy (post-0480): services raise exceptions, tools raise exceptions, endpoints catch and convert to HTTP responses

---

## Phase 1: Categorize All 121 Instances (~120 min)

### 1.1 Run Full Inventory

Search for all `except Exception` patterns:
```
grep -rn 'except Exception' src/ api/ --include='*.py'
```

### 1.2 Classify Each Instance

For EACH instance, assign one of these categories:

| Category | Description | Action | Count (expected) |
|----------|-------------|--------|-----------------|
| **A: API boundary** | Endpoint catches Exception to return HTTP 500 | KEEP — intentional pattern | ~40 |
| **B: WebSocket resilience** | Catch to prevent WS disconnection from crashing server | KEEP (has `noqa: BLE001`) | ~25 |
| **C: Logging-only** | Catches, logs, then continues. No retry/fallback | NARROW — safe to specify expected exceptions | ~20 |
| **D: Retry/fallback** | Catches to retry or use fallback value | INVESTIGATE — need to know what exceptions occur | ~15 |
| **E: Test code** | In test files | LEAVE — low priority | ~10 |
| **F: Dead code** | Should have been removed in 0765a | DELETE | ~5 |

### 1.3 Major Offender Files

| File | Instances | Primary Category |
|------|-----------|-----------------|
| `project_service.py` | 21 | Mix of A and C |
| `orchestration_service.py` | 16 | Mix of A and B |
| `product_service.py` | 16 | Mix of A and C |
| `task_service.py` | 8 | Mostly A |
| `auth_service.py` | 8 | Mostly A |
| Other (21 files) | 52 | Mixed |

---

## Phase 2: Narrow Safe Instances (~180 min)

### 2.1 Category C: Logging-Only (Target: ~20 instances)

For each logging-only catch:
1. Read the try block to identify what operations occur
2. Determine what specific exceptions can be raised (e.g., `ValueError`, `KeyError`, `SQLAlchemyError`, `httpx.HTTPError`)
3. Replace `except Exception` with the specific exception types
4. Keep the logging statement unchanged

**Example transformation:**
```python
# BEFORE
try:
    value = int(some_string)
    result = db.query(Model).filter(...).first()
except Exception as e:
    logger.error(f"Failed: {e}")

# AFTER
try:
    value = int(some_string)
    result = db.query(Model).filter(...).first()
except (ValueError, SQLAlchemyError) as e:
    logger.error(f"Failed: {e}")
```

### 2.2 Category D: Retry/Fallback (Target: ~5-10 instances)

For each retry/fallback catch:
1. Determine what exceptions the retry is meant to handle
2. If the retry handles a specific failure mode (e.g., network timeout), narrow to that
3. If the retry is truly meant for "anything", add a comment explaining why and leave as `except Exception`

### 2.3 Do NOT Narrow

- **Category A (API boundary):** These convert any exception to HTTP 500. This is the correct pattern — narrowing them risks leaking unhandled exceptions as stack traces to the client.
- **Category B (WebSocket):** These prevent server crashes from client-triggered errors. Keep broad.
- **Category E (Test code):** Low priority, skip.

---

## Phase 3: Annotate Intentional Catch-Alls (~60 min)

For every `except Exception` that is intentionally kept broad (Categories A, B, D-intentional), add an inline comment explaining WHY:

```python
except Exception as e:  # Broad catch: API boundary, converts to HTTP 500
    ...

except Exception as e:  # Broad catch: WebSocket resilience, prevents disconnect cascade  # noqa: BLE001
    ...

except Exception as e:  # Broad catch: retry on any transient failure
    ...
```

This prevents future developers (or audit tools) from flagging these as issues.

---

## Testing Requirements

### Per-File Testing

After narrowing catches in each file, run the file's associated tests:
- `project_service.py` -> `pytest tests/services/test_project_service*.py -v`
- `orchestration_service.py` -> `pytest tests/services/test_orchestration_service*.py -v`
- `product_service.py` -> `pytest tests/services/test_product_service*.py -v`
- etc.

### Full Suite

After all changes: `pytest tests/ -x -q` — must remain green.

### Edge Case Testing

For narrowed catches, verify that:
1. The expected exception types are actually caught (not silently swallowed)
2. Unexpected exception types propagate correctly (don't get caught by a too-narrow clause)

---

## Cascading Impact Analysis

- **Service layer:** Narrowed catches may allow new exception types to propagate to callers. Verify each service method's callers handle propagated exceptions.
- **API endpoints:** If a service catch is narrowed and a new exception type propagates, the endpoint's catch-all (Category A) will still handle it. Low risk.
- **WebSocket handlers:** Do NOT narrow WebSocket catches. A propagated exception in a WS handler crashes the connection.

---

## Success Criteria

- [ ] All 121 instances categorized (A/B/C/D/E/F)
- [ ] ~20 safe instances narrowed to specific exception types
- [ ] All intentional broad catches annotated with comments
- [ ] Zero new test failures after narrowing
- [ ] Full test suite green
- [ ] Chain log updated: 0765d = `complete`

---

## Completion Protocol

1. Run full test suite
2. Update chain log
3. Write completion summary (max 400 words) — include category breakdown and count of narrowed vs kept
4. Commit: `cleanup(0765d): Narrow 20 safe except-Exception catch-alls, annotate 100 intentional`
