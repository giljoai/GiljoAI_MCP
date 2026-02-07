# Kickoff: Handover 0703-REVISED - Auth & Middleware Consolidation

**Series:** 0700 Code Cleanup Series
**Risk Level:** MEDIUM
**Estimated Effort:** 2-3 hours
**Date:** 2026-02-06

---

## Mission Statement

Consolidate duplicate auth/middleware code. Original 0703 only deleted 1 file. This addresses the full scope.

---

## Required Reads

1. **Your Spec**: `handovers/0700_series/0703_REVISED.md`
2. **Communications**: `handovers/0700_series/comms_log.json`
3. **Protocol**: `handovers/0700_series/WORKER_PROTOCOL.md`

---

## PHASE 0: VALIDATION RESEARCH (MANDATORY)

### Launch Validation Subagent

```
"Validate 0703-REVISED scope for auth/middleware cleanup.

CHECK 1: RateLimiter duplication
```bash
grep -rn "class.*RateLimiter" api/ --include="*.py"
grep -rn "get_rate_limiter\|RateLimitMiddleware" api/ --include="*.py"
```

CHECK 2: Pydantic model duplication
```bash
for model in PinPasswordResetRequest CheckFirstLoginRequest CompleteFirstLoginRequest; do
  echo "$model: $(grep -rn "class $model" api/endpoints/ | wc -l)"
done
```

CHECK 3: Logging patterns
```bash
echo "Standard: $(grep -rn 'import logging' src/ api/ --include='*.py' | wc -l)"
echo "Structured: $(grep -rn 'from.*logging import get_logger' src/ api/ --include='*.py' | wc -l)"
```

CHECK 4: Type hints in dependencies.py
```bash
grep -n "def get_db\|def get_current\|def get_async" api/dependencies.py
```

REPORT: Confirm or expand each gap."
```

### Document Results

```
## VALIDATION COMPLETE
- RateLimiter: [X classes, consolidate/differentiate decision]
- Pydantic duplicates: [X models × Y files]
- Logging: [X standard, Y structured]
- Type hints needed: [list functions]
```

---

## PHASE 1: EXECUTION

### Task 1: RateLimiter Resolution

Based on validation, either:
- **Consolidate**: Keep one, delete other, update imports
- **Differentiate**: Rename for clarity, document when to use each

### Task 2: Extract Pydantic Models

Create `api/endpoints/auth_models.py` with shared models:
- PinPasswordResetRequest/Response
- CheckFirstLoginRequest/Response
- CompleteFirstLoginRequest/Response

Update auth.py and auth_pin_recovery.py to import from auth_models.py.

### Task 3: Document Logging in CLAUDE.md

Add logging standards section explaining when to use standard vs structured.

### Task 4: Type Hints in dependencies.py

Add return type annotations to get_db, get_async_db, etc.

### Task 5: Fix Middleware Exports

Update `api/middleware/__init__.py` to export all public APIs.

---

## PHASE 2: VERIFICATION

```bash
# Single Pydantic model location
grep -rn "class PinPasswordResetRequest" api/endpoints/ | wc -l  # Expected: 1

# Auth works
python -c "from api.endpoints.auth import router; print('OK')"
python -c "from api.endpoints.auth_pin_recovery import router; print('OK')"

# Middleware imports
python -c "from api.middleware import RateLimitMiddleware; print('OK')"

# CLAUDE.md updated
grep "Logging Standards" CLAUDE.md
```

---

## Communication

```json
{
  "id": "0703-revised-complete-001",
  "timestamp": "[ISO]",
  "from_handover": "0703-REVISED",
  "to_handovers": ["orchestrator"],
  "type": "info",
  "subject": "Auth/middleware consolidation complete",
  "message": "[Summary]",
  "files_affected": ["api/endpoints/auth_models.py", "api/endpoints/auth.py", "api/endpoints/auth_pin_recovery.py", "api/middleware/__init__.py", "api/dependencies.py", "CLAUDE.md"],
  "action_required": false,
  "context": {
    "pydantic_models_extracted": 6,
    "rate_limiter_resolution": "[consolidated/differentiated]",
    "type_hints_added": "[count]",
    "logging_documented": true
  }
}
```

---

## Success Criteria

- [ ] Phase 0 validation complete
- [ ] RateLimiter resolved
- [ ] Pydantic models in auth_models.py
- [ ] Logging documented
- [ ] Type hints added
- [ ] All auth endpoints work
- [ ] Committed
